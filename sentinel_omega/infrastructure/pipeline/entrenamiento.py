"""
Entrenamiento de firmas — two-phase training over the 30-year backcast.

Fase 1 (reconocimiento, sin castigo):
  For every significant event in the historical catalog, extract the
  pre-event window (14 days, 1H blocks) and register it as a firma for
  each bot over its own feature domain. Recurrence promotes signatures:
  nueva -> observada -> recurrente -> consolidada.

Fase 2 (backtest disciplinario):
  Re-present the member events of consolidated signatures. If the firma
  no longer recognizes the window that formed it (similarity below the
  alert threshold), the Juez records a FALLO — the bot forgot enforceable
  knowledge. New signatures are never punished.

Run via: python sentinel_omega/launcher.py --entrenar
"""

import logging
import sqlite3
from typing import Dict, List, Optional

from sentinel_omega.core.firmas.signature_engine import (
    SIMILARITY_ALERT,
    FirmaMemoria,
    extraer_features_ventana,
)
from sentinel_omega.core.juez.juez import Juez

logger = logging.getLogger(__name__)

# Los bots OBSERVAN todas las magnitudes (hasta el mínimo movimiento es un
# gatillo precursor), pero el sistema solo ALERTA y CASTIGA desde 4.5 para
# arriba: ese es el piso de firmas exigibles y de disciplina del Juez.
MIN_MAGNITUD_FIRMA = 4.5

# Feature domain per bot — each bot only remembers what it measures.
# Padre keeps the full cross-domain vector (patterns within patterns).
BOT_FEATURES: Dict[str, Optional[List[str]]] = {
    "alfa1": ["bz_mean", "bz_min", "bz_deriv_std", "viento_avg", "viento_max",
              "proton_max", "bz_mean_72h"],
    "beta1": ["kp_mean", "kp_max", "schumann_mean", "schumann_std",
              "sismo_count_win", "sismo_max_mag_win", "fase_lunar",
              "es_sicigia", "kp_max_72h", "sismo_count_72h"],
    "beta2": ["so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d"],
    "delta": ["btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h"],
    "padre": None,  # full vector
}

MIN_FEATURES_POR_BOT = {"alfa1": 3, "beta1": 3, "beta2": 4, "delta": 4,
                        "padre": 5}

# Each bot only trains inside its own historical window (data availability):
# alfa2/beta2 = 14 years (Sentinel era), delta = 10 years (trends/crypto).
BOT_DESDE: Dict[str, str] = {
    "beta2": "2012-01-01",
    "delta": "2016-01-01",
}


def _event_class(mag: float) -> str:
    if mag >= 7.0:
        return "SISMO_M7"
    if mag >= 6.0:
        return "SISMO_M6"
    if mag >= 5.0:
        return "SISMO_M5"
    return "SISMO_M4"  # 4.5–4.99: piso de alerta/castigo


def entrenar_reconocimiento(
    db_path: str,
    max_eventos: Optional[int] = None,
    bots: Optional[List[str]] = None,
) -> Dict:
    """Fase 1 — learn signatures from every significant historical event.

    bots: restrict registration to these bots (e.g. ["beta2", "delta"] for
    an incremental training pass without inflating other bots' recurrence).
    """
    conn = sqlite3.connect(db_path)
    memoria = FirmaMemoria(conn)
    bots_activos = {
        b: k for b, k in BOT_FEATURES.items() if bots is None or b in bots
    }

    # If every active bot has a bounded window, skip events before the
    # earliest one (no bot would register them anyway).
    desde_global = None
    if bots is not None and all(b in BOT_DESDE for b in bots_activos):
        desde_global = min(BOT_DESDE[b] for b in bots_activos)

    query = (
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= ? "
    )
    params: tuple = (MIN_MAGNITUD_FIRMA,)
    if desde_global:
        query += "AND timestamp_blk >= ? "
        params = (MIN_MAGNITUD_FIRMA, desde_global)
    query += "ORDER BY timestamp_blk"
    eventos = conn.execute(query, params).fetchall()
    if max_eventos:
        eventos = eventos[:max_eventos]

    logger.info(
        f"=== FASE 1 RECONOCIMIENTO: {len(eventos)} eventos M{MIN_MAGNITUD_FIRMA}+ ==="
    )

    stats = {"eventos": len(eventos), "firmas_nuevas": 0, "recurrencias": 0,
             "sin_datos": 0}

    for idx, (ts_evento, id_nodo, mag) in enumerate(eventos):
        if idx % 1000 == 0 and idx > 0:
            logger.info(
                f"  Fase 1 progreso: {idx}/{len(eventos)} eventos "
                f"({stats['firmas_nuevas']} firmas, "
                f"{stats['recurrencias']} recurrencias)"
            )
        features = extraer_features_ventana(conn, ts_evento, id_nodo)
        if features is None:
            stats["sin_datos"] += 1
            continue

        clase = _event_class(mag)
        evento_ref = f"{ts_evento}|nodo{id_nodo}|M{mag:.1f}"

        for bot, keys in bots_activos.items():
            desde = BOT_DESDE.get(bot)
            if desde and ts_evento < desde:
                continue  # event predates this bot's historical window
            sub = (
                features if keys is None
                else {k: v for k, v in features.items() if k in keys}
            )
            if len(sub) < MIN_FEATURES_POR_BOT[bot]:
                continue
            _, _, es_nueva = memoria.registrar(
                bot, clase, id_nodo, sub, evento_ref, ts_evento
            )
            if es_nueva:
                stats["firmas_nuevas"] += 1
            else:
                stats["recurrencias"] += 1

    stats["memoria"] = memoria.stats()
    logger.info(f"Fase 1 completa: {stats}")
    conn.close()
    return stats


def backtest_disciplinario(db_path: str, bots: Optional[List[str]] = None) -> Dict:
    """Fase 2 — el Padre castiga.

    Re-presents the member events of every consolidated signature:
      - Bot fails to recognize enforceable knowledge -> castigo hijo (x1):
        its credibility weight drops and the Juez records the FALLO.
      - The Padre's own meta-signature fails -> castigo Padre (x2): double
        weight decay and double Juez severity (base_geo protocol).
      - Recognition earns mild weight reinforcement.
    The adjusted weights persist in TBL_PESOS_BOTS and the Padre uses them
    to weigh each bot's vote in live consensus.
    """
    conn = sqlite3.connect(db_path)
    memoria = FirmaMemoria(conn)
    juez = Juez(conn)

    consolidadas = memoria.consolidadas()
    if bots is not None:
        consolidadas = [f for f in consolidadas if f["bot_name"] in bots]
    logger.info(
        f"=== FASE 2 DISCIPLINA: {len(consolidadas)} firmas consolidadas ==="
    )

    stats = {"firmas_evaluadas": 0, "reconocidas": 0, "fallos": 0,
             "castigos_hijo": 0, "castigos_padre": 0,
             "atencion_redistribuida": 0}

    import json as _json
    from sentinel_omega.core.firmas.signature_engine import similitud
    from sentinel_omega.core.juez.pesos import (
        PESO_MAX, castigar, reforzar, cargar_pesos,
    )

    # evento_ref -> {bot: reconoció} — needed for attention redistribution
    resultados_por_evento: Dict[str, Dict[str, bool]] = {}

    for firma in consolidadas:
        bot = firma["bot_name"]
        es_padre = bot == "padre"

        row = conn.execute(
            "SELECT eventos_json FROM TBL_FIRMAS WHERE firma_id = ?",
            (firma["firma_id"],),
        ).fetchone()
        eventos = _json.loads(row[0]) if row else []

        for ref in eventos:
            try:
                ts_evento, nodo_part, mag_part = ref.split("|")
                id_nodo = int(nodo_part.replace("nodo", ""))
                magnitud = float(mag_part.replace("M", ""))
            except ValueError:
                continue

            # base_geo: gravity of the error scales with event size
            # (M5 -> 1, M6 -> 2, M7 -> 3)
            gravedad = 1.0 + max(0.0, magnitud - MIN_MAGNITUD_FIRMA)

            features = extraer_features_ventana(conn, ts_evento, id_nodo)
            if features is None:
                continue

            keys = BOT_FEATURES.get(bot)
            sub = (
                features if keys is None
                else {k: v for k, v in features.items() if k in keys}
            )
            sim = similitud(sub, firma["features"])
            stats["firmas_evaluadas"] += 1
            reconocio = sim >= SIMILARITY_ALERT
            resultados_por_evento.setdefault(ref, {})[bot] = reconocio

            if reconocio:
                stats["reconocidas"] += 1
                reforzar(conn, bot)
            else:
                stats["fallos"] += 1
                castigar(conn, bot, es_padre=es_padre, gravedad=gravedad)
                if es_padre:
                    stats["castigos_padre"] += 1
                else:
                    stats["castigos_hijo"] += 1

                juez.registrar_prediccion(
                    bot_name=bot,
                    prediccion="no_signal",
                    confianza=0.0,
                    ventana_h=0,
                    detalles={
                        "fase": "backtest",
                        "firma_id": firma["firma_id"],
                        "evento": ref,
                        "similitud": round(sim, 3),
                        "gravedad": round(gravedad, 2),
                    },
                )
                juez.evaluar_pendientes(
                    evento_ocurrido=True,
                    verdad=ref,
                    firma_conocida=True,
                    multiplicador=2.0 if es_padre else 1.0,
                    gravedad=gravedad,
                )

    # base_geo: when the Padre missed an event that a subordinate DID see,
    # the punished Padre is forced to give more attention weight to the bot
    # that was right — extra reinforcement for that bot.
    for ref, resultados in resultados_por_evento.items():
        if resultados.get("padre") is False:
            for bot, reconocio in resultados.items():
                if bot != "padre" and reconocio:
                    reforzar(conn, bot, hasta=PESO_MAX)
                    stats["atencion_redistribuida"] += 1
                    logger.info(
                        f"ATENCIÓN REDISTRIBUIDA: {bot} vio {ref} que el "
                        f"Padre ignoró — refuerzo extra"
                    )

    stats["auditoria"] = juez.resumen_por_bot()
    stats["pesos"] = cargar_pesos(conn)
    logger.info(f"Fase 2 completa: {stats}")
    conn.close()
    return stats


def entrenar(db_path: str, max_eventos: Optional[int] = None) -> Dict:
    """Full training run: Fase 1 then Fase 2."""
    fase1 = entrenar_reconocimiento(db_path, max_eventos=max_eventos)
    fase2 = backtest_disciplinario(db_path)
    lags = calcular_lags_anticipacion(db_path)
    return {"fase1": fase1, "fase2": fase2, "lags": lags}


# Offsets probados: la ventana de la firma termina N horas ANTES del evento.
# El lag de un evento es el offset MÁS TEMPRANO donde la firma ya se reconocía.
LAG_OFFSETS_H = [336, 240, 168, 120, 72, 24]
LAG_MUESTRA_POR_CLASE = 150


def calcular_lags_anticipacion(db_path: str) -> Dict:
    """Average anticipation lead time per event class (in-sample).

    For consolidated Padre signatures, re-test each member event with the
    window shifted back in time: if the signature already matched 7 days
    before the event, the system had ~7 days of warning. Persisted to
    tbl_lag_anticipacion for the report.
    """
    import json as _json
    from datetime import datetime as _dt, timedelta as _td
    from sentinel_omega.core.firmas.signature_engine import similitud

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_lag_anticipacion ("
        "event_class TEXT PRIMARY KEY, lag_promedio_h REAL, lag_max_h REAL, "
        "lag_min_h REAL, n_eventos INTEGER, "
        "updated_at TEXT DEFAULT (datetime('now')))"
    )

    memoria = FirmaMemoria(conn)
    consolidadas = [
        f for f in memoria.consolidadas() if f["bot_name"] == "padre"
    ]

    lags_por_clase: Dict[str, List[float]] = {}
    evaluados_por_clase: Dict[str, int] = {}

    for firma in consolidadas:
        clase = firma["event_class"]
        if evaluados_por_clase.get(clase, 0) >= LAG_MUESTRA_POR_CLASE:
            continue
        row = conn.execute(
            "SELECT eventos_json FROM TBL_FIRMAS WHERE firma_id = ?",
            (firma["firma_id"],),
        ).fetchone()
        eventos = _json.loads(row[0]) if row else []

        lags_firma: List[float] = []
        for ref in eventos[:3]:  # sample per firma
            if evaluados_por_clase.get(clase, 0) >= LAG_MUESTRA_POR_CLASE:
                break
            try:
                ts_evento, nodo_part, _ = ref.split("|")
                id_nodo = int(nodo_part.replace("nodo", ""))
                t0 = _dt.strptime(ts_evento, "%Y-%m-%d %H:%M")
            except ValueError:
                continue

            evaluados_por_clase[clase] = evaluados_por_clase.get(clase, 0) + 1
            lag_detectado = None
            for offset_h in LAG_OFFSETS_H:  # earliest first
                ts_shift = (t0 - _td(hours=offset_h)).strftime("%Y-%m-%d %H:%M")
                features = extraer_features_ventana(conn, ts_shift, id_nodo)
                if features is None:
                    continue
                if similitud(features, firma["features"]) >= SIMILARITY_ALERT:
                    lag_detectado = float(offset_h)
                    break  # earliest matching offset = max anticipation
            if lag_detectado is not None:
                lags_por_clase.setdefault(clase, []).append(lag_detectado)
                lags_firma.append(lag_detectado)

        # Per-signature lead time: THIS firma's own typical window
        if lags_firma:
            conn.execute(
                "UPDATE TBL_FIRMAS SET lag_promedio_h = ?, lag_n = ? "
                "WHERE firma_id = ?",
                (sum(lags_firma) / len(lags_firma), len(lags_firma),
                 firma["firma_id"]),
            )

    resultado = {}
    for clase, lags in lags_por_clase.items():
        prom = sum(lags) / len(lags)
        conn.execute(
            "INSERT OR REPLACE INTO tbl_lag_anticipacion "
            "(event_class, lag_promedio_h, lag_max_h, lag_min_h, n_eventos, "
            " updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (clase, prom, max(lags), min(lags), len(lags)),
        )
        resultado[clase] = {
            "lag_promedio_dias": round(prom / 24, 1),
            "lag_max_dias": round(max(lags) / 24, 1),
            "n": len(lags),
        }
    conn.commit()
    conn.close()
    logger.info(f"Lags de anticipación: {resultado}")

    factores = analizar_factores_lag(db_path)
    resultado["factores"] = factores
    return resultado


def analizar_factores_lag(db_path: str) -> Dict:
    """What do slow-warning firmas share vs fast-warning ones?

    Splits per-firma lags into terciles (rápidas = shortest lead, lentas =
    longest lead) and compares each feature's mean between groups. The top
    differentiating factors reveal WHY some events announce themselves
    earlier — persisted to tbl_factores_lag for the report and, in time,
    for predicting a match's expected delay from its own features.
    """
    import json as _json

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_factores_lag ("
        "feature TEXT PRIMARY KEY, media_rapidas REAL, media_lentas REAL, "
        "diferencia_norm REAL, updated_at TEXT DEFAULT (datetime('now')))"
    )

    rows = conn.execute(
        "SELECT features_json, lag_promedio_h FROM TBL_FIRMAS "
        "WHERE bot_name = 'padre' AND estado = 'consolidada' "
        "AND lag_promedio_h IS NOT NULL ORDER BY lag_promedio_h"
    ).fetchall()
    if len(rows) < 9:  # need enough firmas for terciles to mean anything
        conn.close()
        return {}

    tercio = len(rows) // 3
    rapidas = [_json.loads(r[0]) for r in rows[:tercio]]
    lentas = [_json.loads(r[0]) for r in rows[-tercio:]]

    def _media(grupo: List[Dict], key: str) -> Optional[float]:
        vals = [g[key] for g in grupo if key in g]
        return sum(vals) / len(vals) if len(vals) >= max(3, len(grupo) // 3) else None

    from sentinel_omega.core.firmas.signature_engine import FEATURE_KEYS

    factores = []
    for key in FEATURE_KEYS:
        mr, ml = _media(rapidas, key), _media(lentas, key)
        if mr is None or ml is None:
            continue
        escala = (abs(mr) + abs(ml)) / 2
        if escala < 1e-9:
            continue
        diff = (ml - mr) / escala  # >0: higher in slow-warning firmas
        factores.append((key, mr, ml, diff))

    factores.sort(key=lambda f: -abs(f[3]))
    for key, mr, ml, diff in factores:
        conn.execute(
            "INSERT OR REPLACE INTO tbl_factores_lag "
            "(feature, media_rapidas, media_lentas, diferencia_norm, "
            " updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (key, mr, ml, diff),
        )
    conn.commit()

    lag_stats = conn.execute(
        "SELECT MIN(lag_promedio_h), AVG(lag_promedio_h), MAX(lag_promedio_h), "
        "COUNT(*) FROM TBL_FIRMAS WHERE bot_name='padre' "
        "AND lag_promedio_h IS NOT NULL"
    ).fetchone()
    conn.close()

    top = {
        f[0]: {"rapidas": round(f[1], 2), "lentas": round(f[2], 2),
               "dif": round(f[3], 2)}
        for f in factores[:6]
    }
    logger.info(f"Factores de lag (top): {top}")
    return {
        "firmas_con_lag": lag_stats[3],
        "lag_dias": {
            "min": round(lag_stats[0] / 24, 1),
            "prom": round(lag_stats[1] / 24, 1),
            "max": round(lag_stats[2] / 24, 1),
        },
        "top_factores": top,
    }
