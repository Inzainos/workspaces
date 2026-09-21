#!/usr/bin/env python3
"""Backfill de tbl_psique_financiera.vix desde el histórico de Yahoo (^VIX).

Contexto (auditoría 2026-09-21): la columna estaba 100% NULL en sus 4.125
filas. El pipeline obtiene el VIX en vivo (fetch_vix), pero nadie lo
persistía en el histórico, así que la feature `vix` de Loki no tenía de dónde
salir y ese bot no podía entrenar.

^VIX en Yahoo cubre 1993→2026, de sobra para el rango de esta tabla
(2014-09-17 → 2026-01-01). Es un dato de mercado: los días sin cotización
(fines de semana, festivos) quedan en NULL, nunca rellenados.

Uso:
    python scripts/db_backfill_vix.py --dry-run
    python scripts/db_backfill_vix.py
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

    from sentinel_omega.infrastructure.api.bolsa import fetch_yahoo_quote

    df = fetch_yahoo_quote("^VIX", days=12000)
    if df is None or not len(df):
        print("Yahoo no devolvió ^VIX — abortado (no se inventa nada)", file=sys.stderr)
        return 1
    col_ts = "timestamp" if "timestamp" in df.columns else df.columns[0]
    print(f"^VIX: {len(df):,} sesiones ({df[col_ts].min()} … {df[col_ts].max()})")

    por_dia = {}
    for ts, cierre in zip(df[col_ts], df["close"]):
        if cierre is None or cierre != cierre:
            continue
        por_dia[str(ts)[:10]] = float(cierre)
    print(f"días con cotización: {len(por_dia):,}")

    con = sqlite3.connect(str(DB), timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    cur = con.cursor()

    dias = [r[0] for r in cur.execute(
        "SELECT DISTINCT substr(timestamp_blk,1,10) FROM tbl_psique_financiera")]
    cruce = [(por_dia[d], d) for d in dias if d in por_dia]
    print(f"días en la tabla: {len(dias):,}  con cotización: {len(cruce):,} "
          f"({100*len(cruce)/max(1,len(dias)):.1f}%)")

    if args.dry_run:
        if cruce:
            m = cruce[len(cruce)//2]
            print(f"  muestra: {m[1]} → vix={m[0]:.2f}")
        print("\n--dry-run: no se escribió nada")
        return 0

    cur.executemany(
        "UPDATE tbl_psique_financiera SET vix = ? "
        "WHERE substr(timestamp_blk,1,10) = ?",
        cruce,
    )
    con.commit()
    n, nulos, mn, mx = cur.execute(
        "SELECT COUNT(vix), SUM(vix IS NULL), ROUND(MIN(vix),2), ROUND(MAX(vix),2) "
        "FROM tbl_psique_financiera").fetchone()
    con.close()
    print(f"\nfilas con vix: {n:,}   sin cotización (NULL): {nulos:,}")
    print(f"rango vix: {mn} … {mx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
