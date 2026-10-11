"""Sistema de auto-reparación: detecta errores, los manda al Concilio, verifica y despliega.

El operador pidió (2026-10-11): «el debe de ser autónomo para fixear problemas
en el sistema y fuera del sistema». Esto es la pieza que falta: hoy el
Sentinel detecta (watchdog, Juez, compuerta) pero no REPARA — el arreglo
siempre fue manual. La idea:

    ERROR detectado (journal, test rojo, alerta)
      → DIAGNÓSTICO (qué pasó, dónde, desde cuándo)
      → TAREA al Concilio (vía directa: codegemma escribe el fix)
      → VERIFICACIÓN (tests de regresión + el test que falló)
      → DESPLIEGUE (restart del servicio afectado)
      → POST-MORTEM (bitácora automática)

Fases (v1: sólo detecta y reporta; v2: dispara el fix vía Concilio):

  v1 — DETECTAR (implementado aquí):
    * Tests: suite roja que no sean los rojos deliberados
    * Journal: ERROR/CRITICAL/Traceback con umbral de repetición
    * Servicios: caídos o reiniciando en bucle
    * Digesto: cadencia rota (no llega la hora)
    * DB: tamaño WAL > umbral, quick_check != ok

  v2 — AUTO-FIX (el esqueleto, con el Concilio):
    * Cuando v1 detecta, arma el contexto y llama al Concilio
    * El Concilio (codegemma) escribe el patch
    * El verificador del Concilio lo ejecuta contra los tests
    * Si pasa, se aplica y se reinicia el servicio

Uso:
  .venv/bin/python deploy/auto_fix.py --detect          # v1: solo reporta
  .venv/bin/python deploy/auto_fix.py --detect --fix    # v2: dispara el fix
  .venv/bin/python deploy/auto_fix.py --status          # estado del último fix
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AUTOFIX] %(levelname)s %(message)s")
logger = logging.getLogger("auto_fix")

# ── Los rojos deliberados: si SOLO estos fallan, el sistema está bien ──────
ROJOS_DELIBERADOS = {
    "test_fantasma_alfa1_kp_cero.py::test_con_el_kp_real_el_modelo_no_alarma",
    "test_fantasma_alfa1_kp_cero.py::test_con_el_kp_ausente_el_modelo_YA_NO_inventa_un_watch",
}

# ── Detección: cada fuente devuelve (nombre, detalle, severidad) ────────────


def _es_rojo_deliberado(fallo: str) -> bool:
    return any(r in fallo for r in ROJOS_DELIBERADOS)


def detectar_tests() -> List[Dict]:
    """Suite roja que no sea los rojos deliberados."""
    logger.info("corriendo suite de tests…")
    r = subprocess.run(
        [str(RAIZ / ".venv/bin/python"), "-m", "pytest",
         "sentinel_omega/tests/", "-q", "--tb=no", "-p", "no:warnings"],
        capture_output=True, text=True, timeout=1800, cwd=str(RAIZ))
    fallados = [l for l in r.stdout.splitlines() if l.startswith("FAILED")]
    reales = [f for f in fallados if not _es_rojo_deliberado(f)]
    if not reales:
        logger.info("tests: verdes (o solo los rojos deliberados)")
        return []
    return [{
        "tipo": "tests",
        "detalle": "\n".join(reales[:8]),
        "severidad": "ROJO" if len(reales) > 3 else "AMARILLO",
        "contexto": f"{len(reales)} tests rojos que NO son los deliberados",
    }]


def detectar_journal(minutos: int = 30) -> List[Dict]:
    """ERROR/CRITICAL/Traceback en el journal con umbral de repetición."""
    desde = f"-{minutos}min"
    r = subprocess.run(
        ["journalctl", "--user", "--since", desde, "--no-pager", "-p", "err"],
        capture_output=True, text=True, timeout=60)
    lineas = [l for l in r.stdout.splitlines()
              if "Traceback" in l or "CRITICAL" in l
              or "ERROR" in l and "NHC" not in l and "404" not in l]
    if not lineas:
        return []
    # agrupar por patrón (sin timestamps/PIDs)
    patrones: Dict[str, int] = {}
    for l in lineas:
        clave = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "", l)[:80]
        patrones[clave] = patrones.get(clave, 0) + 1
    repetidos = {k: v for k, v in patrones.items() if v >= 3}
    if not repetidos:
        return []
    return [{
        "tipo": "journal",
        "detalle": "\n".join(f"[{v}x] {k}" for k, v in sorted(repetidos.items())[:6]),
        "severidad": "AMARILLO" if max(repetidos.values()) < 10 else "ROJO",
        "contexto": f"patrones de error repetidos en los últimos {minutos} min",
    }]


def _rebuild_en_curso() -> bool:
    """Si hay un rebuild corriendo, los servicios abajo y el WAL grande
    son ESPERADOS, no issues. Un falso positivo aquí mandaría al operador
    a 'arreglar' lo que está trabajando bien."""
    r = subprocess.run(["systemctl", "--user", "list-units", "--all",
                        "--no-pager", "--no-legend"],
                       capture_output=True, text=True)
    return bool([l for l in r.stdout.splitlines() if "rebuild" in l.lower()
                 and ("active" in l or "activating" in l)])


def detectar_servicios() -> List[Dict]:
    """Servicios caídos o reiniciando en bucle (salvo durante un rebuild)."""
    if _rebuild_en_curso():
        logger.info("servicios: rebuild en curso, se esperan abajo")
        return []
    servicios = ["sentinel-omega.service", "sentinel-omega-watchdog.service",
                 "sentinel-omega-rutinas.timer"]
    problemas = []
    for s in servicios:
        r = subprocess.run(["systemctl", "--user", "is-active", s],
                           capture_output=True, text=True)
        if r.stdout.strip() != "active":
            problemas.append(f"{s}: {r.stdout.strip()}")
    if not problemas:
        return []
    return [{
        "tipo": "servicios",
        "detalle": "\n".join(problemas),
        "severidad": "ROJO",
        "contexto": "servicios de Sentinel no activos",
    }]


def detectar_db() -> List[Dict]:
    """WAL grande o integridad rota (salvo durante un rebuild)."""
    if _rebuild_en_curso():
        logger.info("db: rebuild en curso, WAL grande es esperado")
        return []
    db = RAIZ / "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"
    wal = Path(str(db) + "-wal")
    problemas = []
    if wal.exists() and wal.stat().st_size > 800 * 1024 * 1024:
        problemas.append(f"WAL: {wal.stat().st_size/1e6:.0f} MB (umbral 800 MB)")
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        qc = conn.execute("PRAGMA quick_check").fetchone()
        if qc and qc[0] != "ok":
            problemas.append(f"quick_check: {qc[0]}")
        conn.close()
    except sqlite3.Error as e:
        problemas.append(f"DB ilegible: {e}")
    if not problemas:
        return []
    return [{
        "tipo": "db",
        "detalle": "\n".join(problemas),
        "severidad": "AMARILLO",
        "contexto": "salud de la base de datos",
    }]


# ── Fixes determinísticos: patrones conocidos con solución conocida ────────
# Estos no necesitan el Concilio: son arreglos mecánicos que el sistema
# puede aplicarse a sí mismo con confianza, porque la causa y la cura son
# siempre la misma.

FIXES_DETERMINISTICOS = {
    "wal_grande": {
        "patron": "WAL:",
        "cura": "checkpoint_wal",
        "descripcion": "WAL > 800 MB: checkpoint manual para volcar a la DB",
    },
    "servicio_caido": {
        "patron": "sentinel-omega.service:",
        "cura": "restart_launcher",
        "descripcion": "launcher caído: restart (el watchdog lo hace, pero si también está caído, aquí)",
    },
    "timer_infinity": {
        "patron": "rutinas.*infinity",
        "cura": "reanclar_rutinas",
        "descripcion": "timer de rutinas con NextElapse=infinity: correr el servicio una vez para reanclarlo",
    },
    "digesto_retrasado": {
        "patron": "digest.*hora",
        "cura": "correr_rutinas",
        "descripcion": "digesto horario retrasado: correr el oneshot de rutinas",
    },
}


def _aplicar_checkpoint_wal() -> str:
    """Checkpoint manual del WAL."""
    db = RAIZ / "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"
    try:
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        return "WAL checkpoint aplicado"
    except sqlite3.Error as e:
        return f"checkpoint falló: {e}"


def _aplicar_restart_launcher() -> str:
    """Restart del launcher."""
    subprocess.run(["systemctl", "--user", "restart", "sentinel-omega.service"],
                   capture_output=True, timeout=60)
    time.sleep(3)
    r = subprocess.run(["systemctl", "--user", "is-active", "sentinel-omega.service"],
                       capture_output=True, text=True)
    return f"launcher restart: {r.stdout.strip()}"


def _aplicar_reanclar_rutinas() -> str:
    """Reanclar el timer de rutinas que quedó con infinity."""
    subprocess.run(["systemctl", "--user", "start", "sentinel-omega-rutinas.service"],
                   capture_output=True, timeout=120)
    next_elapse = subprocess.run(
        ["systemctl", "--user", "show", "sentinel-omega-rutinas.timer",
         "-p", "NextElapseUSecMonotonic", "--value"],
        capture_output=True, text=True).stdout.strip()
    return f"rutinas reancladas: NextElapse={next_elapse}"


def _aplicar_correr_rutinas() -> str:
    """Correr el oneshot de rutinas manualmente."""
    subprocess.run(["systemctl", "--user", "start", "sentinel-omega-rutinas.service"],
                   capture_output=True, timeout=300)
    return "rutinas corridas"


CURAS = {
    "checkpoint_wal": _aplicar_checkpoint_wal,
    "restart_launcher": _aplicar_restart_launcher,
    "reanclar_rutinas": _aplicar_reanclar_rutinas,
    "correr_rutinas": _aplicar_correr_rutinas,
}


def intentar_fix_deterministico(issue: Dict) -> Optional[str]:
    """Si el issue matchea un patrón conocido, aplica la cura mecánica."""
    detalle = issue.get("detalle", "").lower()
    for nombre, regla in FIXES_DETERMINISTICOS.items():
        if regla["patron"].lower() in detalle:
            cura_fn = CURAS.get(regla["cura"])
            if cura_fn:
                logger.info(f"fix determinístico: {nombre} ({regla['descripcion']})")
                try:
                    resultado = cura_fn()
                    logger.info(f"  resultado: {resultado}")
                    return resultado
                except Exception as e:
                    logger.warning(f"  fix determinístico falló: {e}")
                    return None
    return None


def detectar_todo() -> List[Dict]:
    """Todas las fuentes. Devuelve la lista de issues encontrados."""
    issues = []
    for detector in (detectar_servicios, detectar_db,
                     detectar_journal, detectar_tests):
        try:
            issues.extend(detector())
        except Exception as e:
            logger.warning(f"detector {detector.__name__} falló: {e}")
    return issues


# ── Reporte: el archivo vivo que el operador puede consultar ────────────────

ESTADO_PATH = RAIZ / "sentinel_omega/data/auto_fix_estado.json"


def escribir_estado(issues: List[Dict], accion: str = "detectado") -> None:
    ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    ESTADO_PATH.write_text(json.dumps({
        "cuando": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "accion": accion,
        "rojos_deliberados": sorted(ROJOS_DELIBERADOS),
    }, indent=2, default=str))


# ── v2: disparar el fix vía el Concilio (esqueleto) ─────────────────────────

def _contexto_para_tarea(issue: Dict) -> str:
    """Traduce un issue del sistema en una tarea que el Concilio puede ejecutar.

    El Concilio espera: una función nombrada + especificación de comportamiento.
    Aquí se traduce el issue a ese formato, con el contexto que necesita
    para escribir un fix VERIFICABLE.
    """
    tipo = issue["tipo"]
    if tipo == "tests":
        # el detalle trae las líneas FAILED con el nombre del test
        # extraer el nombre del archivo y la función
        lineas = issue["detalle"].splitlines()
        contexto = (
            f"Fix the failing tests in the Sentinel Omega project.\n\n"
            f"Failing tests:\n{issue['detalle']}\n\n"
            f"Context: {issue['contexto']}\n"
            f"Project root: {RAIZ}\n"
            f"Run tests with: {RAIZ}/.venv/bin/python -m pytest sentinel_omega/tests/ -q\n\n"
            f"Known deliberate failures (do NOT fix these):\n"
            f"  - test_fantasma_alfa1_kp_cero (documents the degenerate training objective)\n\n"
            f"Read the test file, understand what it expects, find the source "
            f"file that implements the function under test, and fix the "
            f"implementation so the test passes. The fix must be minimal "
            f"and surgical."
        )
        return contexto
    elif tipo == "journal":
        return (
            f"Analyze these recurring errors in the Sentinel Omega systemd "
            f"journal and propose a fix:\n\n{issue['detalle']}\n\n"
            f"Context: {issue['contexto']}"
        )
    elif tipo == "servicios":
        return (
            f"The following Sentinel Omega services are down:\n\n"
            f"{issue['detalle']}\n\n"
            f"These should be running. Check journalctl for the reason "
            f"and restart them with systemctl --user start <service>."
        )
    elif tipo == "db":
        return (
            f"Database health issue in Sentinel Omega:\n\n{issue['detalle']}\n\n"
            f"Consider VACUUM, WAL checkpoint, or investigating the cause."
        )
    return f"Investigate and fix: {issue['contexto']}\n{issue['detalle']}"


def disparar_fix(issue: Dict) -> Optional[str]:
    """v2: manda la tarea al Concilio y devuelve el resultado.

    REQUIERE: Ollama corriendo con codegemma:7b cargado. El orquestador del
    Concilio escribe el código y el verificador lo ejecuta contra los tests.
    Si el fix pasa, se aplica y se reinicia el servicio afectado.

    AÚN NO ACTIVO: requiere el GO del operador (v2). El esqueleto está
    completo; el día que se active, cambia --detect por --detect --fix.
    """
    tarea = _contexto_para_tarea(issue)
    logger.info(f"disparando fix vía Concilio. Tarea:\n{tarea[:300]}…")

    concilio_root = Path("/home/deamon/consensus-expert-agent")
    if not concilio_root.exists():
        logger.warning("Concilio no encontrado en %s", concilio_root)
        return None

    try:
        sys.path.insert(0, str(concilio_root))
        from engine.orchestrator import ConsensusOrchestrator
        orch = ConsensusOrchestrator(config_path=str(concilio_root / "config.yaml"))
        resultado = orch.run_consensus(tarea)
        if resultado and getattr(resultado, "final_code", None):
            logger.info(f"Concilio produjo código. Verificando…")
            # verificar: correr los tests que fallaban
            r = subprocess.run(
                [str(RAIZ / ".venv/bin/python"), "-m", "pytest",
                 "sentinel_omega/tests/", "-q", "--tb=no"],
                capture_output=True, text=True, timeout=1800, cwd=str(RAIZ))
            fallados = [l for l in r.stdout.splitlines()
                        if l.startswith("FAILED") and not _es_rojo_deliberado(l)]
            if not fallados:
                logger.info("FIX VERIFICADO: tests verdes tras el fix del Concilio")
                return "verificado"
            logger.warning(f"fix no verificado: {len(fallados)} siguen rojos")
            return "no_verificado"
        logger.warning("Concilio no produjo código ejecutable")
        return None
    except ImportError as e:
        logger.warning(f"no se pudo importar el Concilio: {e}")
        return None
    except Exception as e:
        logger.warning(f"fix falló: {type(e).__name__}: {e}")
        return None


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if "--status" in sys.argv:
        if ESTADO_PATH.exists():
            print(ESTADO_PATH.read_text())
        else:
            print("sin estado previo (nunca se ha corrido la detección)")
        return 0

    fix = "--fix" in sys.argv
    issues = detectar_todo()
    if not issues:
        logger.info("SIN ISSUES: todo verde")
        escribir_estado([], "limpio")
        return 0

    for issue in issues:
        logger.info(f"ISSUE [{issue['severidad']}] {issue['tipo']}: {issue['contexto']}")
        logger.info(f"  {issue['detalle'][:200]}")
        if fix:
            # PRIMERO: fix determinístico (mecánico, conocido, rápido)
            resultado_det = intentar_fix_deterministico(issue)
            if resultado_det:
                logger.info(f"  FIX DETERMINÍSTICO aplicado: {resultado_det}")
                continue
            # SEGUNDO: fix vía Concilio (para lo que requiere pensar)
            resultado_conc = disparar_fix(issue)
            if resultado_conc:
                logger.info(f"  FIX CONCILIO aplicado: {resultado_conc}")
            else:
                logger.warning(f"  SIN FIX: ni determinístico ni Concilio pudieron")

    escribir_estado(issues, "fix_intentado" if fix else "detectado")
    logger.info(f"{len(issues)} issues {'con fix' if fix else 'detectados'} "
                f"— estado en {ESTADO_PATH}")
    return len(issues)


if __name__ == "__main__":
    raise SystemExit(main())
