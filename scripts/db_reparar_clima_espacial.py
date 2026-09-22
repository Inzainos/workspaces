#!/usr/bin/env python3
"""Re-deriva tbl_clima_espacial_raw desde OMNI2 con los índices corregidos.

POR QUÉ EXISTE
--------------
`extraer_nasa_omni_real` leía cuatro columnas equivocadas del formato OMNI2.
La tabla quedó con:

  - bz_promedio/bz_min/bz_max/bz_derivada = sigma|B| (una desviación típica,
    nunca negativa) en vez del Bz GSM, que es la magnitud con significado
    físico: el Bz sur es lo que abre el acoplamiento geomagnético.
  - viento_solar_* contaminado con el centinela 9999 tratado como medición
    (13.550 filas; duplicaba la media de 469 a 930 km/s).
  - proton_flux_10mev = índice DST (47% de valores negativos; un flujo de
    partículas no puede serlo).
  - Kp leído de una columna que es 100% centinela.

Este script NO inventa nada: vuelve a bajar OMNI2 y reescribe solo lo que
la fuente respalda. Lo que OMNI no publica queda NULL.

IDEMPOTENTE: correrlo dos veces deja el mismo resultado.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, "/home/deamon/workspaces")
from sentinel_omega.infrastructure.pipeline.backcast import (  # noqa: E402
    LOCF_MAX_HORAS,
    extraer_nasa_omni_real,
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reparar_clima")

COLUMNAS = ("bz_promedio", "bz_derivada", "bz_min", "bz_max",
            "viento_solar_avg", "viento_solar_max",
            "kp_max", "kp_promedio", "proton_flux_10mev")


def _f(v):
    """None para NaN: la ausencia se guarda como NULL, no como número."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return float(v)


def agregar_horario(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa OMNI a bloques de 1 h, igual que el backcast original."""
    d = df.set_index("fecha").sort_index()
    agg = d.resample("1h").agg(
        bz_promedio=("bz_promed", "mean"),
        bz_min=("bz_promed", "min"),
        bz_max=("bz_promed", "max"),
        viento_solar_avg=("sw_speed", "mean"),
        viento_solar_max=("sw_speed", "max"),
        kp_max=("kp_val", "max"),
        kp_promedio=("kp_val", "mean"),
        proton_flux_10mev=("p_flux", "max"),
    ).reset_index()
    agg["bz_derivada"] = agg["bz_promedio"].diff()
    agg = agg.ffill(limit=LOCF_MAX_HORAS)
    agg["timestamp_blk"] = agg["fecha"].dt.strftime("%Y-%m-%d %H:%M")
    return agg


def reparar_anio(conn: sqlite3.Connection, year: int, dry: bool) -> dict:
    df = extraer_nasa_omni_real(year)
    if df.empty:
        log.warning("  %s: OMNI no devolvió datos — se deja intacto", year)
        return {"year": year, "omni": 0, "actualizadas": 0, "insertadas": 0}

    agg = agregar_horario(df)
    # Filas que OMNI no respalda en absoluto: no se escriben (ni NULL masivo).
    con_dato = agg.dropna(subset=["bz_promedio", "viento_solar_avg", "kp_promedio"],
                          how="all")

    existentes = {
        r[0] for r in conn.execute(
            "SELECT timestamp_blk FROM tbl_clima_espacial_raw "
            "WHERE timestamp_blk LIKE ?", (f"{year}-%",)
        )
    }

    upd, ins = [], []
    for _, r in con_dato.iterrows():
        vals = [_f(r[c]) for c in COLUMNAS]
        if r["timestamp_blk"] in existentes:
            upd.append(vals + [r["timestamp_blk"]])
        else:
            ins.append([r["timestamp_blk"]] + vals)

    if not dry:
        if upd:
            conn.executemany(
                "UPDATE tbl_clima_espacial_raw SET "
                + ", ".join(f"{c}=?" for c in COLUMNAS)
                + " WHERE timestamp_blk=?", upd)
        if ins:
            conn.executemany(
                "INSERT OR IGNORE INTO tbl_clima_espacial_raw "
                "(timestamp_blk, " + ", ".join(COLUMNAS) + ") "
                "VALUES (" + ",".join("?" * (len(COLUMNAS) + 1)) + ")", ins)
        conn.commit()

    log.info("  %s: OMNI %d h -> %d actualizadas, %d insertadas",
             year, len(con_dato), len(upd), len(ins))
    return {"year": year, "omni": len(con_dato),
            "actualizadas": len(upd), "insertadas": len(ins)}


def diagnostico(conn: sqlite3.Connection, etiqueta: str) -> None:
    q = """SELECT COUNT(*),
                  SUM(bz_promedio < 0),
                  ROUND(AVG(viento_solar_max), 1),
                  SUM(viento_solar_max >= 9999),
                  SUM(proton_flux_10mev < 0)
           FROM tbl_clima_espacial_raw"""
    n, bz_neg, v_med, v_cent, p_neg = conn.execute(q).fetchone()
    log.info("[%s] filas=%s | bz negativos=%s (%.1f%%) | viento medio=%s | "
             "centinelas 9999=%s | protones negativos=%s",
             etiqueta, n, bz_neg, 100.0 * (bz_neg or 0) / max(n, 1),
             v_med, v_cent, p_neg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--desde", type=int, default=1994)
    ap.add_argument("--hasta", type=int, default=2026)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db, timeout=60)
    diagnostico(conn, "ANTES")

    total = {"actualizadas": 0, "insertadas": 0, "omni": 0}
    for year in range(args.desde, args.hasta + 1):
        try:
            r = reparar_anio(conn, year, args.dry_run)
            for k in total:
                total[k] += r[k]
        except Exception as e:  # noqa: BLE001
            log.error("  %s falló: %s: %s — se continúa", year, type(e).__name__, e)

    if not args.dry_run:
        diagnostico(conn, "DESPUÉS")
    log.info("TOTAL: %d horas de OMNI | %d actualizadas | %d insertadas%s",
             total["omni"], total["actualizadas"], total["insertadas"],
             "  (DRY-RUN: nada escrito)" if args.dry_run else "")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
