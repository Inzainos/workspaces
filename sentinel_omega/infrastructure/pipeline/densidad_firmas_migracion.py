#!/usr/bin/env python3
"""Añade `densidad_prot_mean` / `densidad_prot_max` a las firmas YA creadas.

Por qué hace falta
------------------
La columna `densidad_protones` se pobló el 2026-10-02 (275.241 de 286.951 horas,
95,9 %) y el extractor ya la lee, pero las firmas del rebuild se formaron antes:
sus `features_json` no la tienen. Reentrenar el modelo así repetiría el defecto
que se está arreglando --- el rasgo valdría 0 en todo el entrenamiento y real en
el ciclo vivo, que es el espejo de la fuga de procedencia.

Rehacer la Fase 1 cuesta 3 h medidas. Esto cuesta segundos: solo alfa1 declara
la densidad en `BOT_FEATURES`, así que solo sus firmas la necesitan, y cada una
guarda su propio ancla --- `primera_vista` y `id_nodo` --- que es justo lo que
`extraer_features_ventana` pide.

Qué toca y qué no
-----------------
**Solo** mezcla las dos claves de densidad. El resto de `features_json` se deja
intacto: se calculó en el rebuild y es correcto, y recalcularlo entero cambiaría
firmas que nadie pidió cambiar.

Cero sintético: si la ventana de esa firma no tiene densidad, no se escribe
nada --- la clave simplemente no aparece, igual que cualquier otro rasgo sin
dato.

    python -m sentinel_omega.infrastructure.pipeline.densidad_firmas_migracion \
        --db <ruta> [--bot alfa1] [--escribir]
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("densidad_firmas")

CLAVES = ("densidad_prot_mean", "densidad_prot_max")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--bot", default="alfa1")
    ap.add_argument("--escribir", action="store_true")
    args = ap.parse_args()

    from sentinel_omega.core.firmas.signature_engine import (
        extraer_features_ventana,
    )
    from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES

    permitidas = set(BOT_FEATURES.get(args.bot) or [])
    objetivo = [k for k in CLAVES if k in permitidas]
    if not objetivo:
        log.error("%s no declara la densidad en BOT_FEATURES: nada que hacer "
                  "(declararla primero, o la firma la descartaría en silencio)",
                  args.bot)
        return 1
    log.info("claves a añadir en %s: %s", args.bot, objetivo)

    conn = sqlite3.connect(args.db, timeout=600)
    conn.execute("PRAGMA busy_timeout=600000")

    filas = conn.execute(
        "SELECT firma_id, id_nodo, primera_vista, features_json "
        "FROM TBL_FIRMAS WHERE bot_name = ? ORDER BY firma_id",
        (args.bot,)).fetchall()
    log.info("firmas de %s: %s", args.bot, f"{len(filas):,}")

    puestas = ya_tenian = sin_dato = sin_ancla = 0
    lote = []
    for fid, nodo, ts, fj in filas:
        try:
            actual = json.loads(fj or "{}") or {}
        except (ValueError, TypeError):
            actual = {}
        if all(k in actual for k in objetivo):
            ya_tenian += 1
            continue
        if not ts or nodo is None:
            sin_ancla += 1
            continue
        try:
            feats = extraer_features_ventana(conn, ts, int(nodo))
        except Exception as e:  # noqa: BLE001
            log.warning("firma %s: extracción falló (%s)", fid, e)
            sin_dato += 1
            continue
        nuevas = {k: feats[k] for k in objetivo
                  if feats and k in feats} if feats else {}
        if not nuevas:
            sin_dato += 1
            continue
        actual.update(nuevas)
        lote.append((json.dumps(actual), fid))
        puestas += 1

    if args.escribir and lote:
        conn.executemany(
            "UPDATE TBL_FIRMAS SET features_json = ? WHERE firma_id = ?", lote)
        conn.commit()
    conn.close()

    modo = "ESCRITO" if args.escribir else "DRY-RUN (no se escribió nada)"
    log.info("%s --- %s firmas con densidad añadida, %s ya la tenían, "
             "%s sin dato en su ventana, %s sin ancla",
             modo, f"{puestas:,}", f"{ya_tenian:,}", f"{sin_dato:,}",
             f"{sin_ancla:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
