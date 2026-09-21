#!/usr/bin/env python3
"""Backfill de tbl_astronomia_cinematica.lod_ms desde el histórico del IERS.

Contexto (auditoría 2026-09-21): la columna tenía 0.0 en sus 280.352 filas —
cero sintético, no medición. El backcast solo sembraba `timestamp_blk` y
`fetch_lod_series` apuntaba al archivo .daily del IERS (~90 días), insuficiente
para el rango 1994-2025.

El LOD (exceso de duración del día sobre 86400 s) es una MEDICIÓN del IERS, no
derivable: se toma del archivo finals2000A.all (1973→2027). Es un valor diario,
así que se aplica a las 24 horas de su día. Los días sin medición quedan en
NULL, nunca en cero.

Uso:
    python scripts/db_backfill_lod.py --dry-run
    python scripts/db_backfill_lod.py
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DB = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from sentinel_omega.infrastructure.api.geophysical import fetch_lod_series

    df = fetch_lod_series(days=40000, historico=True)
    if df is None or not len(df):
        print("IERS no devolvió datos — abortado (no se inventa nada)", file=sys.stderr)
        return 1
    print(f"IERS: {len(df):,} días  ({df['date'].min()} … {df['date'].max()})")

    por_dia = {
        d.strftime("%Y-%m-%d"): float(v)
        for d, v in zip(df["date"], df["lod_ms"])
        if v is not None and v == v            # descarta NaN
    }
    print(f"días con LOD medido: {len(por_dia):,}")

    con = sqlite3.connect(str(DB), timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    cur = con.cursor()

    dias_tabla = [r[0] for r in cur.execute(
        "SELECT DISTINCT substr(timestamp_blk,1,10) FROM tbl_astronomia_cinematica"
    )]
    cruce = [(por_dia[d], d) for d in dias_tabla if d in por_dia]
    print(f"días en la tabla: {len(dias_tabla):,}  con medición IERS: {len(cruce):,}")

    if args.dry_run:
        m = cruce[len(cruce)//2] if cruce else None
        if m:
            print(f"  muestra: {m[1]} → lod_ms={m[0]:.3f}")
        print("\n--dry-run: no se escribió nada")
        return 0

    # primero limpiar el cero sintético: faltante = NULL
    cur.execute("UPDATE tbl_astronomia_cinematica SET lod_ms = NULL WHERE lod_ms = 0")
    cur.executemany(
        "UPDATE tbl_astronomia_cinematica SET lod_ms = ? "
        "WHERE substr(timestamp_blk,1,10) = ?",
        cruce,
    )
    con.commit()
    n_ok, n_null = cur.execute(
        "SELECT COUNT(lod_ms), SUM(lod_ms IS NULL) FROM tbl_astronomia_cinematica"
    ).fetchone()
    rango = cur.execute(
        "SELECT ROUND(MIN(lod_ms),3), ROUND(MAX(lod_ms),3) FROM tbl_astronomia_cinematica"
    ).fetchone()
    con.close()
    print(f"\nfilas con lod_ms medido: {n_ok:,}   sin medición (NULL): {n_null:,}")
    print(f"rango lod_ms: {rango[0]} … {rango[1]} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
