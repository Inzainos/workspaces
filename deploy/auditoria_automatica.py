#!/usr/bin/env python3
"""Auditoría automática: los chequeos que hoy dependen de que alguien mire.

Por qué existe
--------------
El 2026-09-28 el operador escribió: *«beta1 se refresca pero repite el mismo
valor: la fuente no está midiendo»*. Tenía razón, y debajo había DOS defectos
que llevaban horas comiéndose datos sin que una sola alerta dijera nada:

  * seis escrituras por ciclo fallaban con «database is locked», todas
    fail-soft, así que el ciclo terminaba «bien»;
  * el mantenimiento diario fallaba con exit 1 desde hacía días.

Ninguno de los dos necesitaba inteligencia para detectarse. **Necesitaban que
alguien contara.** Eso es esto: chequeos deterministas, sin modelo, que emiten
EVIDENCIA (conteos, fechas, valores) y no opiniones.

El criterio de diseño, aprendido a golpes ese mismo día: un número que mejora no
prueba nada. Cada hallazgo sale con la medición que lo sostiene, para que quien
lo lea --- persona o modelo --- pueda discrepar con el dato delante.

Es SOLO LECTURA. No escribe en la base, no toca servicios, no arregla nada.

Uso
---
    python deploy/auditoria_automatica.py                # informe en texto
    python deploy/auditoria_automatica.py --json         # para consumirlo
    python deploy/auditoria_automatica.py --ciclos 30    # ventana de varianza

Salida: código 0 si no hay hallazgos, 1 si hay alguno. Así un timer puede
disparar el aviso solo cuando haya algo que decir.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"

# Cuántos ciclos mirar para decidir que un bot «no se mueve». Con ciclos de
# ~5 min, 12 son una hora --- que es lo que el operador notó a ojo.
CICLOS_VARIANZA = 12

# Horas de atraso a partir de las cuales una fuente se considera parada.
# 6 h es holgado para tablas que se escriben cada hora; las que se alimentan por
# volcado diario se declaran aparte.
FRESCURA_H = {
    "tbl_clima_espacial_raw": 6,
    "tbl_historico_sismico_raw": 24,
    "tbl_xray_vivo": 6,
    "tbl_trends_vivo": 48,
    "TBL_PRECURSORES_COSMICOS": 1,
}

# Fuentes que YA se saben paradas, con la fecha en que se supo. No se vuelven a
# reportar como novedad; aparecen en el informe como deuda conocida. Sacar una
# de aquí exige la medición de que volvió a alimentarse.
PARADAS_CONOCIDAS = {
    "tbl_psique_financiera": "2026-01-01 (BTC/VIX)",
    "tbl_desgasificacion_raw": "2026-07-31 (SO2 volcánico)",
    "tbl_astronomia_cinematica": "2025-12-31 (LOD, fase lunar)",
}


@dataclass
class Hallazgo:
    chequeo: str
    gravedad: str          # "alto" | "medio" | "info"
    titulo: str
    evidencia: Dict[str, Any] = field(default_factory=dict)
    porque_importa: str = ""

    def texto(self) -> str:
        lineas = [f"[{self.gravedad.upper()}] {self.titulo}"]
        for k, v in self.evidencia.items():
            lineas.append(f"      {k}: {v}")
        if self.porque_importa:
            lineas.append(f"      → {self.porque_importa}")
        return "\n".join(lineas)


def _conn() -> Optional[sqlite3.Connection]:
    """Conexión de SOLO LECTURA. Si la base no está, no hay auditoría."""
    if not DB.exists():
        return None
    try:
        return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    except sqlite3.Error:
        return None


# ── 1. Un bot que repite el mismo valor ──────────────────────────────────────
#
# CALIBRADO Y DEGRADADO el 2026-09-28, aplicándose la regla dura 8 a sí mismo.
#
# La primera versión disparaba con «12 ciclos con la misma confianza». Medido
# sobre 229 ciclos reales: los bots se quedan en su valor de suelo el 66-86 % del
# tiempo, así que doce iguales ocurren POR AZAR varias veces al día sin que nada
# esté roto. Un detector que dispara solo no discrimina nada.
#
#     bot      conf. distintas en 24 h    % en su valor más repetido
#     alfa2               2                        85,6 %
#     beta2               5                        69,9 %
#     alfa1              16                        71,2 %
#     beta1              43                        21,8 %
#     delta / loki       50                        22 % / 72 %
#
# Segundo intento: comparar a cada bot CONSIGO MISMO --- racha actual contra su
# racha máxima de 7 días. Medido: ninguna racha actual se acerca a su máximo
# (alfa2 llegó a 664 ciclos planos, beta1 a 310), porque la semana de referencia
# incluye los días en que el sistema estaba roto. **La línea base está
# contaminada**, así que el umbral que sale de ella es inútil.
#
# Conclusión: «repite el mismo valor» es un SÍNTOMA bueno para un humano que
# conoce el sistema --- así lo cazó el operador --- y un detector malo. Se deja
# como informativo, nunca como alarma, y la causa se busca en los dos chequeos
# que sí son deterministas: frescura de fuentes y escrituras perdidas. Los dos
# cazaron lo de esa noche sin calibración ninguna.
#
# Se podrá promover a alarma cuando exista una semana de operación LIMPIA de la
# que sacar la línea base. No antes.
def chequeo_varianza(c: sqlite3.Connection, ciclos: int) -> List[Hallazgo]:
    """Informativo: cuánto lleva cada bot sin cambiar, contra su propia historia."""
    import itertools

    fuera: List[Hallazgo] = []
    bots = [r[0] for r in c.execute(
        "SELECT DISTINCT bot_name FROM TBL_JUEZ_AUDITORIA WHERE fase='viva'")]
    for bot in sorted(bots):
        serie = [r[0] for r in c.execute(
            "SELECT ROUND(confianza,6) FROM TBL_JUEZ_AUDITORIA "
            "WHERE fase='viva' AND bot_name=? "
            "AND timestamp>=strftime('%s','now')-604800 "
            "ORDER BY timestamp DESC", (bot,)) if r[0] is not None]
        if len(serie) < 50:
            continue
        rachas = [len(list(g)) for _, g in itertools.groupby(serie)]
        if len(rachas) < 2:
            # Toda la ventana es un solo valor: el bot no CAMBIÓ de estado, es
            # que nunca tuvo otro. Eso no es una novedad que avisar cada noche
            # --- es una constante, y las constantes las mira
            # `chequeo_constantes` al nivel del dato, que es donde se pueden
            # distinguir de una calma real. Sin racha previa no hay con qué
            # comparar, y comparar contra cero hace que dispare siempre.
            continue
        actual, historica = rachas[0], max(rachas[1:])
        if actual < ciclos or actual <= historica:
            continue
        fuera.append(Hallazgo(
            chequeo="varianza",
            gravedad="info",
            titulo=f"{bot}: {actual} ciclos con la misma confianza",
            evidencia={
                "valor": serie[0],
                "racha máxima previa (7 d)": historica,
            },
            porque_importa=(
                "es más larga que cualquiera de su última semana. NO es alarma "
                "por sí sola --- las rachas largas son comunes aquí ---, pero "
                "vale mirar frescura y escrituras de este bot"),
        ))
    return fuera


# ── 2. Fuentes que dejaron de llegar ─────────────────────────────────────────
def chequeo_frescura(c: sqlite3.Connection) -> List[Hallazgo]:
    fuera: List[Hallazgo] = []
    for tabla, limite_h in FRESCURA_H.items():
        col = "timestamp_blk"
        try:
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({tabla})")]
        except sqlite3.Error:
            continue
        if not cols:
            continue
        if col not in cols:
            col = "timestamp" if "timestamp" in cols else cols[0]
        try:
            if col == "timestamp":   # epoch Unix en varias tablas de este repo
                fila = c.execute(
                    f"SELECT (strftime('%s','now') - MAX({col}))/3600.0 FROM {tabla}"
                ).fetchone()
            else:
                fila = c.execute(
                    f"SELECT (julianday('now') - julianday(MAX({col})))*24 FROM {tabla}"
                ).fetchone()
        except sqlite3.Error:
            continue
        if not fila or fila[0] is None:
            continue
        atraso = float(fila[0])
        if atraso > limite_h:
            fuera.append(Hallazgo(
                chequeo="frescura",
                gravedad="alto" if atraso > limite_h * 4 else "medio",
                titulo=f"{tabla}: sin datos nuevos desde hace {atraso:.1f} h",
                evidencia={"límite": f"{limite_h} h", "columna": col},
                porque_importa=(
                    "las ventanas del vector se congelan en ese borde y el "
                    "modelo infiere sobre un pasado fijo"),
            ))
    return fuera


# ── 3. Escrituras que se pierden en silencio ─────────────────────────────────
def chequeo_escrituras_perdidas(horas: int = 2) -> List[Hallazgo]:
    """Cuenta los fallos fail-soft del log. Son los que nadie ve.

    El patrón es siempre el mismo: un `except` que solo registra `warning` en
    una ruta de persistencia. El ciclo termina «bien» y el dato no está.
    """
    try:
        salida = subprocess.run(
            ["journalctl", "--user", "-u", "sentinel-omega",
             "--since", f"-{horas}h", "--no-pager"],
            capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    marcas = {
        "database is locked": "candado de SQLite",
        "no bloqueante": "persistencia fail-soft",
        "Persistencia": "persistencia fail-soft",
    }
    conteo: Dict[str, int] = {}
    for linea in salida.splitlines():
        for marca, etiqueta in marcas.items():
            if marca in linea:
                conteo[etiqueta] = conteo.get(etiqueta, 0) + 1
                break
    if not conteo:
        return []
    total = sum(conteo.values())
    return [Hallazgo(
        chequeo="escrituras",
        gravedad="alto" if total > 5 else "medio",
        titulo=f"{total} escrituras perdidas en {horas} h",
        evidencia=conteo,
        porque_importa=(
            "son fail-soft: el ciclo reporta éxito y el dato no está. Es la "
            "regla dura 10 --- un descarte silencioso esconde el fallo"),
    )]


# ── 4. Rasgos que el modelo pide y la firma no puede llenar ──────────────────
def chequeo_fugas() -> List[Hallazgo]:
    """Fuga de etiqueta por procedencia, y su variante silenciosa."""
    try:
        from sentinel_omega.core.features_onnx import FEATURE_ORDER
        from sentinel_omega.core.firmas.signature_engine import FEATURE_KEYS
        from sentinel_omega.infrastructure.pipeline.entrenamiento import (
            BOT_FEATURES,
        )
    except ImportError:
        return []
    fuera: List[Hallazgo] = []
    for bot, orden in FEATURE_ORDER.items():
        declarados = BOT_FEATURES.get(bot)
        if declarados is None:
            continue
        fugas = sorted(set(orden) - set(declarados))
        if fugas:
            fuera.append(Hallazgo(
                chequeo="fuga_procedencia",
                gravedad="alto",
                titulo=f"{bot}: {len(fugas)} rasgos en el vector que la firma no llena",
                evidencia={"rasgos": fugas},
                porque_importa=(
                    "valen 0 en toda la mitad etiquetada como alarma: el modelo "
                    "aprende de qué tabla vino la fila, no el rasgo"),
            ))
        huerfanos = sorted(k for k in declarados if k not in FEATURE_KEYS)
        if huerfanos:
            fuera.append(Hallazgo(
                chequeo="descarte_silencioso",
                gravedad="alto",
                titulo=f"{bot}: {len(huerfanos)} rasgos declarados que no existen",
                evidencia={"rasgos": huerfanos},
                porque_importa=(
                    "el filtro por FEATURE_KEYS los descarta sin decir nada, "
                    "así que el rasgo vale 0 igual que si no se hubiera declarado"),
            ))
    return fuera


# ── 5. Una columna con un solo valor no es una medición ──────────────────────
def chequeo_constantes(c: sqlite3.Connection, filas: int = 200) -> List[Hallazgo]:
    """El patrón del 8.26: un valor de libro repetido hasta el infinito."""
    objetivos = [
        ("TBL_PRECURSORES_COSMICOS", "schumann_hz"),
        ("TBL_PRECURSORES_COSMICOS", "schumann_activity"),
        ("TBL_PRECURSORES_COSMICOS", "kp_index"),
        ("tbl_xray_vivo", "flux_max"),
    ]
    fuera: List[Hallazgo] = []
    for tabla, col in objetivos:
        try:
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({tabla})")]
            if col not in cols:
                continue
            fila = c.execute(
                f"SELECT COUNT(DISTINCT {col}), COUNT({col}) FROM "
                f"(SELECT {col} FROM {tabla} ORDER BY rowid DESC LIMIT ?)",
                (filas,)).fetchone()
        except sqlite3.Error:
            continue
        if not fila or not fila[1]:
            continue
        distintos, total = fila
        if distintos == 1 and total >= 20:
            valor = c.execute(
                f"SELECT {col} FROM {tabla} ORDER BY rowid DESC LIMIT 1"
            ).fetchone()[0]
            fuera.append(Hallazgo(
                chequeo="constante",
                gravedad="alto",
                titulo=f"{tabla}.{col}: un solo valor en {total} filas",
                evidencia={"valor": valor, "filas miradas": total},
                porque_importa=(
                    "una columna sin variación no está midiendo; el modelo la "
                    "lee como si lo estuviera"),
            ))
    return fuera


# ── 6. Dos unidades para el mismo trabajo ────────────────────────────────────
def chequeo_unidades_duplicadas() -> List[Hallazgo]:
    """El defecto que costó un día entero: dos launchers sobre la misma base."""
    unidades = ["sentinel-omega", "sentinel-omega-watchdog",
                "sentinel-omega-rutinas", "sentinel-omega-mantenimiento"]
    fuera: List[Hallazgo] = []
    for u in unidades:
        estados = {}
        for ambito, cmd in (("sistema", ["systemctl"]), ("usuario", ["systemctl", "--user"])):
            for sufijo in (".service", ".timer"):
                try:
                    r = subprocess.run(cmd + ["is-active", u + sufijo],
                                       capture_output=True, text=True, timeout=10)
                    if r.stdout.strip() == "active":
                        estados[f"{ambito}{sufijo}"] = "active"
                except (OSError, subprocess.SubprocessError):
                    continue
        sistema = any(k.startswith("sistema") for k in estados)
        usuario = any(k.startswith("usuario") for k in estados)
        if sistema and usuario:
            fuera.append(Hallazgo(
                chequeo="unidad_duplicada",
                gravedad="alto",
                titulo=f"{u}: activa en sistema Y en usuario a la vez",
                evidencia=estados,
                porque_importa=(
                    "dos procesos haciendo el mismo trabajo sobre la misma "
                    "base: duplica escrituras y falsea los conteos por ciclo"),
            ))
    return fuera


def auditar(ciclos: int = CICLOS_VARIANZA) -> Dict[str, Any]:
    hallazgos: List[Hallazgo] = []
    c = _conn()
    if c is not None:
        hallazgos += chequeo_varianza(c, ciclos)
        hallazgos += chequeo_frescura(c)
        hallazgos += chequeo_constantes(c)
        c.close()
    hallazgos += chequeo_escrituras_perdidas()
    hallazgos += chequeo_fugas()
    hallazgos += chequeo_unidades_duplicadas()
    return {
        "hallazgos": [h.__dict__ for h in hallazgos],
        "total": len(hallazgos),
        "altos": sum(1 for h in hallazgos if h.gravedad == "alto"),
        "paradas_conocidas": PARADAS_CONOCIDAS,
        "_lista": hallazgos,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="salida para consumir")
    ap.add_argument("--ciclos", type=int, default=CICLOS_VARIANZA)
    args = ap.parse_args()

    res = auditar(args.ciclos)
    lista: List[Hallazgo] = res.pop("_lista")

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
        return 1 if lista else 0

    if not lista:
        print("Auditoría automática: sin hallazgos.")
        print("\nDeuda conocida (no es novedad, no se reporta como hallazgo):")
        for t, d in PARADAS_CONOCIDAS.items():
            print(f"  · {t}: parada desde {d}")
        return 0

    print(f"Auditoría automática: {len(lista)} hallazgos "
          f"({res['altos']} de gravedad alta)\n")
    for h in lista:
        print(h.texto())
        print()
    print("Deuda conocida (no se reporta como hallazgo):")
    for t, d in PARADAS_CONOCIDAS.items():
        print(f"  · {t}: parada desde {d}")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    sys.exit(main())
