#!/usr/bin/env python3
"""Backfill: promueve sismos de la tabla FUENTE a la OPERATIVA que lee el Juez.

Contexto (auditoría 2026-09-15): el ciclo vivo descartaba los sismos que bajaba
de USGS, así que `TBL_HISTORICO_SISMICO` (la que lee el Juez) quedó congelada en
2026-08-16 mientras `tbl_eventos_sismicos_fuente` tiene el catálogo completo. El
fix de código (data_pipeline/layer_runners) ya persiste el flujo VIVO; este
script inyecta de una vez el HISTÓRICO perdido para que el Juez pueda verificar
de inmediato, sin esperar a que el flujo vivo acumule.

Idempotente: INSERT OR IGNORE dedup por event_id (=usgs_id). Cero sintético:
solo copia datos reales de la fuente; depth_km no existe en la fuente → 0.0.

Uso:
    python scripts/db_backfill_sismos_operativa.py                 # desde 2026-08-01
    python scripts/db_backfill_sismos_operativa.py --desde 2026-07-01
    python scripts/db_backfill_sismos_operativa.py --todo          # catálogo completo (214k)

IMPORTANTE: escribe en la DB de producción. Correr idealmente con el launcher
detenido (o aceptar el reintento por busy_timeout). Requiere PYTHONPATH al repo.
"""
import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"


def iso_a_epoch(s: str) -> float | None:
    """'YYYY-MM-DD HH:MM:SS[.ffffff]' (UTC naive) → epoch float."""
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-08-01", help="fecha ISO mínima (time_utc)")
    ap.add_argument("--todo", action="store_true", help="ignorar --desde: catálogo completo")
    args = ap.parse_args()

    if not DB.exists():
        print(f"No existe la DB: {DB}", file=sys.stderr)
        return 1

    con = sqlite3.connect(str(DB), timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    cur = con.cursor()

    if args.todo:
        q = "SELECT usgs_id, time_utc, lat, lon, mag FROM tbl_eventos_sismicos_fuente"
        params: tuple = ()
    else:
        q = ("SELECT usgs_id, time_utc, lat, lon, mag FROM tbl_eventos_sismicos_fuente "
             "WHERE time_utc >= ?")
        params = (args.desde,)

    filas = cur.execute(q, params).fetchall()
    eventos, descartados = [], 0
    for usgs_id, time_utc, lat, lon, mag in filas:
        ts = iso_a_epoch(time_utc)
        if not usgs_id or ts is None or lat is None or lon is None or mag is None:
            descartados += 1
            continue
        eventos.append((str(usgs_id), float(ts), float(lat), float(lon),
                        0.0, float(mag), "", "", "USGS"))

    before = cur.execute("SELECT COUNT(*) FROM TBL_HISTORICO_SISMICO").fetchone()[0]
    cur.executemany(
        """INSERT OR IGNORE INTO TBL_HISTORICO_SISMICO
           (event_id, timestamp, lat, lon, depth_km, magnitude, mag_type, region, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        eventos,
    )
    con.commit()
    after = cur.execute("SELECT COUNT(*) FROM TBL_HISTORICO_SISMICO").fetchone()[0]
    rango = cur.execute(
        "SELECT datetime(MIN(timestamp),'unixepoch'), datetime(MAX(timestamp),'unixepoch') "
        "FROM TBL_HISTORICO_SISMICO"
    ).fetchone()
    con.close()

    print(f"candidatos={len(filas)}  válidos={len(eventos)}  descartados={descartados}")
    print(f"operativa: {before} → {after}  (+{after - before} nuevos)")
    print(f"rango operativa: {rango[0]} … {rango[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
