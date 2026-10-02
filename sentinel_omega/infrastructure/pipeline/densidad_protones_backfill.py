#!/usr/bin/env python3
"""Rellena `tbl_clima_espacial_raw.densidad_protones` desde OMNI2 (1994→hoy).

Por qué existe
--------------
El operador recordó el 2026-10-02 que «la densidad de protones la traíamos de
una API de la NASA», y la documentación lo confirmaba --- bitácora del 20-sep,
líneas 101-103: *«`fetch_solar_wind()` sí baja `proton_speed`/`proton_density`,
pero `fetch_alfa1_data` renombra `proton_speed → plasma_speed`»*. La densidad se
bajaba y se tiraba, y `alfa1/agent.py:24` la declara entre sus tres variables.

El arreglo del 20-sep cableó el **flujo >10 MeV**, que es otra magnitud y está
muerta en los dos lados: OMNI2 publica sus columnas 42-47 todas en centinela y
NOAA sirve 6 h, así que la tabla lo tenía en 178 de 286.932 horas (0,062 %).

La densidad no. Verificado contra `omni2_2024.dat` (regla dura 9 --- el índice se
comprueba contra el dato, no contra el manual):

    col 23   min 0,40   max 87,40   MEDIANA 5,70 n/cc   cobertura 97,7 %
             cero negativos · cero centinelas colados
    col 24   velocidad, mediana 387 km/s, MISMO 2,3 % de huecos
             (salen del mismo instrumento de plasma)

Qué hace
--------
Un `UPDATE` por bloque horario que **solo escribe donde hay NULL**
(`COALESCE`), así que no pisa nada y se puede correr dos veces. No inserta
filas: si una hora no está en la tabla, no se inventa --- eso lo decide el
backcast, no un relleno.

Cero sintético: una hora sin dato en OMNI2 se queda en NULL. Sin interpolar,
sin arrastrar.

    python -m sentinel_omega.infrastructure.pipeline.densidad_protones_backfill \
        --db <ruta> [--desde 1994] [--hasta 2026] [--escribir]
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from typing import List, Tuple

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("densidad_backfill")


def filas_del_anio(anio: int) -> List[Tuple[float, str]]:
    """[(densidad, 'AAAA-MM-DD HH:00'), ...] de OMNI2 para ese año."""
    import pandas as pd

    from sentinel_omega.infrastructure.pipeline.backcast import (
        extraer_nasa_omni_real,
    )
    df = extraer_nasa_omni_real(anio)
    if df is None or not len(df) or "p_density" not in df.columns:
        return []
    d = df[["fecha", "p_density"]].dropna()
    if not len(d):
        return []
    # Media horaria, igual que el backcast y que la ventana de la firma.
    porhora = (d.set_index("fecha").sort_index()
                .resample("1h")["p_density"].mean().dropna())
    return [(float(v), ts.strftime("%Y-%m-%d %H:00"))
            for ts, v in porhora.items()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--desde", type=int, default=1994)
    ap.add_argument("--hasta", type=int, default=2026)
    ap.add_argument("--escribir", action="store_true",
                    help="sin este flag solo informa (dry-run de verdad)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db, timeout=600)
    conn.execute("PRAGMA busy_timeout=600000")

    antes = conn.execute(
        "SELECT COUNT(*), SUM(densidad_protones IS NOT NULL) "
        "FROM tbl_clima_espacial_raw").fetchone()
    log.info("tabla: %s horas, %s con densidad antes", f"{antes[0]:,}",
             f"{antes[1] or 0:,}")

    total_vistas = total_escritas = 0
    for anio in range(args.desde, args.hasta + 1):
        try:
            filas = filas_del_anio(anio)
        except Exception as e:  # noqa: BLE001 --- un año malo no corta el resto
            log.warning("%s: OMNI2 falló (%s): se salta", anio, e)
            continue
        if not filas:
            log.warning("%s: sin densidad en OMNI2", anio)
            continue
        total_vistas += len(filas)
        if args.escribir:
            cur = conn.executemany(
                "UPDATE tbl_clima_espacial_raw "
                "SET densidad_protones = COALESCE(densidad_protones, ?) "
                "WHERE timestamp_blk = ?", filas)
            conn.commit()
            escritas = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            total_escritas += escritas
            log.info("%s: %s horas de OMNI2, %s filas tocadas",
                     anio, f"{len(filas):,}", f"{escritas:,}")
        else:
            log.info("%s: %s horas de OMNI2 (dry-run)", anio, f"{len(filas):,}")

    despues = conn.execute(
        "SELECT COUNT(*), SUM(densidad_protones IS NOT NULL) "
        "FROM tbl_clima_espacial_raw").fetchone()
    conn.close()

    modo = "ESCRITO" if args.escribir else "DRY-RUN (no se escribió nada)"
    log.info("%s --- %s horas vistas en OMNI2", modo, f"{total_vistas:,}")
    log.info("con densidad: %s -> %s de %s horas",
             f"{antes[1] or 0:,}", f"{despues[1] or 0:,}", f"{despues[0]:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
