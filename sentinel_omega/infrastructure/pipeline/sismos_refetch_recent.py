#!/usr/bin/env python3
"""Incremental USGS refetch for tbl_eventos_sismicos_fuente (safe, no wipe)."""
from __future__ import annotations
import argparse, logging, sqlite3
from datetime import datetime, timedelta, timezone

from sentinel_omega.infrastructure.pipeline.usgs_catalogo import (
    asegurar_columnas,
    descargar_anio,
    descargar_rango,
    pedir_http,
    upsert_fila,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sismos_refetch")
MIN_MAG = 2.5

def fetch_recent(days: int):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return descargar_rango(start, end, MIN_MAG, pedir_http)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--days", type=int)
    ap.add_argument("--year", type=int, help="un ano M4.5+, solo upsert, sin purgar")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.year is not None and args.days is not None:
        ap.error("usa --year o --days, no los dos")
    if args.year is not None:
        filas = descargar_anio(args.year, 4.5, pedir_http)
    else:
        filas = fetch_recent(14 if args.days is None else args.days)
    logger.info("USGS rows=%s", len(filas))
    if not filas:
        return
    try:
        from sentinel_omega.core.shared.geometria_uvg import nodo_mas_cercano
    except Exception:
        from core.shared.geometria_uvg import nodo_mas_cercano
    con = sqlite3.connect(args.db)
    if not args.dry_run:
        asegurar_columnas(con)
    n = 0
    for fila in filas:
        nodo = nodo_mas_cercano(float(fila["lat"]), float(fila["lon"]))
        if not args.dry_run:
            upsert_fila(con, fila, nodo["id"], "incremental")
        n += 1
    if not args.dry_run:
        con.commit()
    mx = con.execute("SELECT MAX(time_utc), COUNT(*) FROM tbl_eventos_sismicos_fuente").fetchone()
    con.close()
    logger.info("upserted=%s max_time=%s total=%s", n, mx[0], mx[1])

if __name__ == "__main__":
    main()
