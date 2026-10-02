#!/usr/bin/env python3
"""Rellena los huecos de Kp de `tbl_clima_espacial_raw` desde GFZ Potsdam.

Por qué hace falta una fuente distinta
--------------------------------------
`clima_gapfill_2026.py` usa los mismos feeds cortos de NOAA que el ciclo vivo
--- Kp de ~6 h, RTSW de ~24 h --- y su propio comentario ya lo dice: «huecos
más viejos necesitan otra fuente». GFZ Potsdam sirve 90 días.

Qué se rellena y con qué, exactamente
-------------------------------------
El Kp **es por definición un índice 3-horario**. El que guarda el ciclo vivo es
el Kp *estimado* de NOAA a 1 minuto, promediado por hora; el de GFZ es el Kp
*definitivo* de su bloque de 3 h. Asignar el valor definitivo a las tres horas
que ese bloque cubre **no es interpolar ni arrastrar**: es el índice de ese
periodo. `kp_promedio` y `kp_max` quedan iguales entre sí para esas horas,
que es lo correcto para un índice de bloque.

No es LOCF, no es relleno sintético y no se inventa nada: cada hora escrita
tiene detrás una medición real de GFZ que cubre ese instante. Las horas sin
bloque que las cubra se quedan en NULL.

Procedencia: la columna no puede decir de dónde vino cada valor, así que cada
hora rellenada se anota en `tbl_clima_relleno_auditoria` con su fuente y la
hora del relleno. Sin eso, el valor de GFZ sería indistinguible del de NOAA
dentro de un mes --- y la regla 2 pide que lo derivado se pueda reconocer.

Solo rellena NULL. Nunca pisa un valor ya medido.

    python -m sentinel_omega.infrastructure.pipeline.clima_relleno_gfz --db <ruta>
    python -m sentinel_omega.infrastructure.pipeline.clima_relleno_gfz --db <ruta> --escribir
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("clima_relleno_gfz")

FUENTE = "GFZ_Potsdam_Kp_3h"

SQL_AUDITORIA = """
CREATE TABLE IF NOT EXISTS tbl_clima_relleno_auditoria (
    timestamp_blk TEXT NOT NULL,
    columna       TEXT NOT NULL,
    valor         REAL NOT NULL,
    fuente        TEXT NOT NULL,
    rellenado_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (timestamp_blk, columna)
)
"""


def huecos_de_kp(conn: sqlite3.Connection) -> List[str]:
    """Horas con telemetría real y Kp ausente, más antiguas primero."""
    return [r[0] for r in conn.execute(
        "SELECT timestamp_blk FROM tbl_clima_espacial_raw "
        "WHERE (kp_promedio IS NULL OR kp_max IS NULL) "
        "  AND bz_promedio IS NOT NULL "
        "ORDER BY timestamp_blk"
    ).fetchall()]


def kp_por_hora(dias: int = 90) -> Dict[str, float]:
    """{'AAAA-MM-DD HH:00': kp} --- cada bloque de 3 h cubre sus tres horas."""
    import pandas as pd

    from sentinel_omega.infrastructure.api.gfz_kp import fetch_kp_history
    df = fetch_kp_history(days=dias)
    if df is None or not len(df):
        log.error("GFZ no devolvió datos: no se rellena nada")
        return {}
    t = pd.to_datetime(df["time_tag"], utc=True)
    por_hora: Dict[str, float] = {}
    for ts, kp in zip(t, df["kp_index"]):
        if pd.isna(kp):
            continue
        for h in range(3):  # el bloque de 3 h cubre sus tres horas
            clave = (ts + pd.Timedelta(hours=h)).strftime("%Y-%m-%d %H:00")
            por_hora[clave] = float(kp)
    log.info("GFZ: %d bloques -> %d horas cubiertas", len(df), len(por_hora))
    return por_hora


def rellenar(conn: sqlite3.Connection, escribir: bool) -> Tuple[int, int]:
    """Devuelve (horas rellenadas, horas sin cobertura)."""
    pendientes = huecos_de_kp(conn)
    if not pendientes:
        log.info("No hay huecos de Kp con telemetría real: nada que hacer")
        return 0, 0
    log.info("Huecos de Kp a cubrir: %d (de %s a %s)",
             len(pendientes), pendientes[0], pendientes[-1])

    tabla = kp_por_hora()
    if not tabla:
        return 0, len(pendientes)

    conn.execute(SQL_AUDITORIA)
    puestos, sin_cobertura = 0, 0
    for blk in pendientes:
        kp = tabla.get(blk)
        if kp is None:
            sin_cobertura += 1
            log.warning("%s sin bloque de GFZ que lo cubra: se queda NULL", blk)
            continue
        log.info("%s  kp = %.3f  (%s)", blk, kp, FUENTE)
        if escribir:
            # COALESCE: jamás pisa un valor ya medido, ni en una segunda pasada.
            conn.execute(
                "UPDATE tbl_clima_espacial_raw SET "
                "  kp_promedio = COALESCE(kp_promedio, ?), "
                "  kp_max      = COALESCE(kp_max, ?) "
                "WHERE timestamp_blk = ?", (kp, kp, blk))
            conn.executemany(
                "INSERT OR IGNORE INTO tbl_clima_relleno_auditoria "
                "(timestamp_blk, columna, valor, fuente) VALUES (?,?,?,?)",
                [(blk, "kp_promedio", kp, FUENTE),
                 (blk, "kp_max", kp, FUENTE)])
        puestos += 1
    if escribir:
        conn.commit()
    return puestos, sin_cobertura


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--escribir", action="store_true",
                    help="sin este flag solo informa (dry-run de verdad)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db, timeout=120)
    conn.execute("PRAGMA busy_timeout=120000")
    try:
        puestos, sin_cobertura = rellenar(conn, escribir=args.escribir)
    finally:
        conn.close()

    modo = "ESCRITO" if args.escribir else "DRY-RUN (no se escribió nada)"
    log.info("%s --- %d horas rellenadas, %d sin cobertura de GFZ",
             modo, puestos, sin_cobertura)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
