#!/usr/bin/env python3
"""Medición limpia de la Fase 1: serial contra paralela por bot.

Reconstruido el 2026-09-26 (Agente-T) desde la bitácora (§6d/§6e), porque el
original vivía en el scratchpad de una sesión y se perdió.

Por qué existe: el 1,76× y el reparto 60–66 % del padre se midieron con un
proceso fugado de 2 h 17 min comiéndose la máquina. Todo lo de velocidad de esa
tarde quedó bajo sospecha. Lo que sí se sostiene es que las firmas salen
idénticas byte a byte. Este script remide sólo el tiempo, con la máquina limpia,
y vuelve a comprobar la identidad.

Reglas:
  * NUNCA toca la base de producción: copia con `sqlite3.backup` a un
    directorio de trabajo, una copia fresca por modo.
  * Se NIEGA a arrancar si detecta otra medición, otro entrenamiento o un
    rebuild corriendo, o si la carga, la memoria o el disco no dan.
  * Sin `max_eventos`: con recorte, serial y paralelo ven tramos distintos
    (ver docstring de `entrenar_paralelo.py`) y la comparación no vale.
  * Mismos bots en los dos modos (los de `BOT_FEATURES` sin alfa2, que es
    live-only), para que el serial no cargue con un bot que el paralelo no
    entrena.

Uso (desde /home/deamon/workspaces/sentinel_omega, con el .venv):
    ../.venv/bin/python scripts/medicion_limpia.py serial
    ../.venv/bin/python scripts/medicion_limpia.py paralelo [--workers N]
    ../.venv/bin/python scripts/medicion_limpia.py ambos      # serial y luego paralelo
    ../.venv/bin/python scripts/medicion_limpia.py comparar   # sólo compara lo ya medido
Opciones: --dir DIR (trabajo, por defecto data/medicion_limpia/),
          --db RUTA (origen, por defecto data/SENTINEL_OMEGA_PRO.db),
          --carga-max 1.5  --mem-min-gb 4  --disco-min-gb 12
          --conservar-copias (no borra la copia al terminar la comparación)
Duración esperada: ~77 min la Fase 1 serial (proyección previa, sin validar).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import socket
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]          # .../sentinel_omega
sys.path.insert(0, str(RAIZ.parent))                 # para `import sentinel_omega`

DB_PROD = RAIZ / "data" / "SENTINEL_OMEGA_PRO.db"
DIR_TRABAJO = RAIZ / "data" / "medicion_limpia"

# Marcas de procesos que invalidan la medición si están vivos.
MARCAS_RIVALES = (
    "medicion_limpia", "entrenar_reconocimiento", "entrenar_paralelo",
    "entrenamiento.py", "rebuild", "pytest",
)

log = logging.getLogger("medicion_limpia")


# ── guardas ──────────────────────────────────────────────────────────

def _procesos_rivales() -> list[str]:
    yo = {os.getpid(), os.getppid()}
    rivales = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit() or int(d.name) in yo:
            continue
        try:
            cmd = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", "ignore").strip()
        except OSError:
            continue
        if cmd and any(m in cmd for m in MARCAS_RIVALES):
            rivales.append(f"{d.name}: {cmd[:160]}")
    return rivales


def _mem_disponible_gb() -> float:
    for linea in Path("/proc/meminfo").read_text().splitlines():
        if linea.startswith("MemAvailable:"):
            return int(linea.split()[1]) / 1024 / 1024
    return 0.0


def comprobar_maquina(args, dir_trabajo: Path) -> dict:
    carga = os.getloadavg()
    mem = _mem_disponible_gb()
    dir_trabajo.mkdir(parents=True, exist_ok=True)
    disco = shutil.disk_usage(dir_trabajo).free / 1024 ** 3
    rivales = _procesos_rivales()
    estado = {"carga_1_5_15": carga, "mem_disponible_gb": round(mem, 2),
              "disco_libre_gb": round(disco, 2), "cpus": os.cpu_count(),
              "rivales": rivales}
    problemas = []
    if rivales:
        problemas.append("procesos rivales vivos:\n    " + "\n    ".join(rivales))
    if carga[0] > args.carga_max:
        problemas.append(f"carga 1 min {carga[0]:.2f} > {args.carga_max}")
    if mem < args.mem_min_gb:
        problemas.append(f"memoria disponible {mem:.1f} GB < {args.mem_min_gb}")
    if disco < args.disco_min_gb:
        problemas.append(f"disco libre {disco:.1f} GB < {args.disco_min_gb} "
                         "(el paralelo hace una copia de la base por bot)")
    if problemas:
        log.error("Máquina NO limpia; no se mide:\n  - %s", "\n  - ".join(problemas))
        raise SystemExit(2)
    log.info("Máquina limpia: %s", estado)
    return estado


# ── base de trabajo ──────────────────────────────────────────────────

def copiar_base(origen: Path, destino: Path) -> float:
    if destino.exists():
        destino.unlink()
    for suf in ("-wal", "-shm"):
        Path(str(destino) + suf).unlink(missing_ok=True)
    t0 = time.perf_counter()
    src = sqlite3.connect(f"file:{origen}?mode=ro", uri=True)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    src.close()
    dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    dst.close()
    dt = time.perf_counter() - t0
    log.info("copia %s -> %s en %.1f s", origen.name, destino.name, dt)
    return dt


def _bots_comparables() -> list[str]:
    from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES
    return [b for b in BOT_FEATURES if b != "alfa2"]


def huella_firmas(db: Path, bots: list[str]) -> dict:
    """Huella de TBL_FIRMAS para esos bots: SHA-256 de todas las filas
    ordenadas por todas las columnas (menos la PK autoincremental, que depende
    del orden de inserción y no del contenido)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    info = con.execute("PRAGMA table_info(TBL_FIRMAS)").fetchall()
    cols = [c[1] for c in info if not (c[5] and c[2].upper() == "INTEGER")]
    marcas = ",".join("?" * len(bots))
    orden = ", ".join(f'"{c}"' for c in cols)
    h = hashlib.sha256()
    n = 0
    por_bot: dict[str, int] = {}
    cur = con.execute(
        f"SELECT {orden} FROM TBL_FIRMAS WHERE bot_name IN ({marcas}) "
        f"ORDER BY {orden}", bots)
    idx_bot = cols.index("bot_name")
    for fila in cur:
        h.update(repr(fila).encode("utf-8"))
        n += 1
        por_bot[fila[idx_bot]] = por_bot.get(fila[idx_bot], 0) + 1
    con.close()
    return {"sha256": h.hexdigest(), "filas": n, "por_bot": por_bot,
            "columnas": cols}


# ── modos ────────────────────────────────────────────────────────────

def medir(modo: str, args, dir_trabajo: Path) -> dict:
    estado = comprobar_maquina(args, dir_trabajo)
    bots = _bots_comparables()
    copia = dir_trabajo / f"fase1_{modo}.db"
    t_copia = copiar_base(Path(args.db), copia)

    log.info("=== %s: %d bots (%s) sin max_eventos ===", modo.upper(),
             len(bots), ", ".join(bots))
    t0 = time.perf_counter()
    cpu0 = os.times()
    if modo == "serial":
        from sentinel_omega.infrastructure.pipeline.entrenamiento import (
            entrenar_reconocimiento)
        stats = entrenar_reconocimiento(str(copia), bots=bots)
    else:
        from sentinel_omega.infrastructure.pipeline.entrenar_paralelo import (
            entrenar_reconocimiento_paralelo)
        stats = entrenar_reconocimiento_paralelo(
            str(copia), bots=bots, n_workers=args.workers,
            dir_trabajo=str(dir_trabajo / "par_tmp"))
    muro = time.perf_counter() - t0
    cpu1 = os.times()
    log.info("%s terminado en %.1f s (%.1f min)", modo, muro, muro / 60)

    res = {
        "modo": modo,
        "inicio_utc": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "maquina_antes": estado,
        "carga_despues": os.getloadavg(),
        "segundos_copia": round(t_copia, 2),
        "segundos_muro": round(muro, 2),
        "cpu_user_padre": round(cpu1.user - cpu0.user, 2),
        "cpu_user_hijos": round(cpu1.children_user - cpu0.children_user, 2),
        "workers": args.workers if modo == "paralelo" else 1,
        "bots": bots,
        "firmas": huella_firmas(copia, bots),
        "stats": stats,
    }
    salida = dir_trabajo / f"resultado_{modo}.json"
    salida.write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    log.info("resultado en %s", salida)
    return res


def comparar(dir_trabajo: Path, conservar: bool) -> dict:
    s = json.loads((dir_trabajo / "resultado_serial.json").read_text())
    p = json.loads((dir_trabajo / "resultado_paralelo.json").read_text())
    identicas = s["firmas"]["sha256"] == p["firmas"]["sha256"]
    acel = s["segundos_muro"] / p["segundos_muro"] if p["segundos_muro"] else None
    comp = {
        "firmas_identicas": identicas,
        "filas_serial": s["firmas"]["filas"], "filas_paralelo": p["firmas"]["filas"],
        "diferencias_por_bot": {
            b: (s["firmas"]["por_bot"].get(b), p["firmas"]["por_bot"].get(b))
            for b in set(s["firmas"]["por_bot"]) | set(p["firmas"]["por_bot"])
            if s["firmas"]["por_bot"].get(b) != p["firmas"]["por_bot"].get(b)},
        "segundos_serial": s["segundos_muro"],
        "segundos_paralelo": p["segundos_muro"],
        "aceleracion": round(acel, 3) if acel else None,
        "workers_paralelo": p["workers"],
        "carga_antes": {"serial": s["maquina_antes"]["carga_1_5_15"],
                        "paralelo": p["maquina_antes"]["carga_1_5_15"]},
    }
    (dir_trabajo / "comparacion.json").write_text(
        json.dumps(comp, indent=2, ensure_ascii=False))
    log.info("COMPARACIÓN: %s", json.dumps(comp, ensure_ascii=False))
    if not identicas:
        log.error("¡Las firmas NO coinciden! No se borra nada; revisar a mano.")
    elif not conservar:
        for m in ("serial", "paralelo"):
            (dir_trabajo / f"fase1_{m}.db").unlink(missing_ok=True)
        log.info("copias borradas (usa --conservar-copias para dejarlas)")
    return comp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=("serial", "paralelo", "ambos", "comparar"))
    ap.add_argument("--db", default=str(DB_PROD))
    ap.add_argument("--dir", default=str(DIR_TRABAJO))
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--carga-max", type=float, default=1.5)
    ap.add_argument("--mem-min-gb", type=float, default=4.0)
    ap.add_argument("--disco-min-gb", type=float, default=12.0)
    ap.add_argument("--conservar-copias", action="store_true")
    args = ap.parse_args()

    dir_trabajo = Path(args.dir)
    dir_trabajo.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [MEDICION] %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(dir_trabajo / "medicion_limpia.log")])

    if Path(args.db).resolve() == Path(args.dir).resolve():
        raise SystemExit("--db y --dir no pueden coincidir")

    if args.modo == "comparar":
        comparar(dir_trabajo, args.conservar_copias)
        return
    modos = ("serial", "paralelo") if args.modo == "ambos" else (args.modo,)
    for m in modos:
        medir(m, args, dir_trabajo)
    if all((dir_trabajo / f"resultado_{m}.json").exists()
           for m in ("serial", "paralelo")):
        comparar(dir_trabajo, args.conservar_copias)


if __name__ == "__main__":
    main()
