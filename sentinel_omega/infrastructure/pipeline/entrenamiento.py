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

MIN_MAGNITUD_FIRMA = 5.0

# Feature domain per bot — each bot only remembers what it measures.
# Padre keeps the full cross-domain vector (patterns within patterns).
BOT_FEATURES: Dict[str, Optional[List[str]]] = {
    "alfa1": ["bz_mean", "bz_min", "bz_deriv_std", "viento_avg", "viento_max",
              "proton_max", "bz_mean_72h"],
    "beta1": ["kp_mean", "kp_max", "schumann_mean", "schumann_std",
              "sismo_count_win", "sismo_max_mag_win", "fase_lunar",
              "es_sicigia", "kp_max_72h", "sismo_count_72h"],
    "delta": ["btc_volatilidad"],
    "padre": None,  # full vector
}

MIN_FEATURES_POR_BOT = {"alfa1": 3, "beta1": 3, "delta": 1, "padre": 5}


def _event_class(mag: float) -> str:
    if mag >= 7.0:
        return "SISMO_M7"
    if mag >= 6.0:
        return "SISMO_M6"
    return "SISMO_M5"


def entrenar_reconocimiento(db_path: str, max_eventos: Optional[int] = None) -> Dict:
    """Fase 1 — learn signatures from every significant historical event."""
    conn = sqlite3.connect(db_path)
    memoria = FirmaMemoria(conn)

    eventos = conn.execute(
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= ? ORDER BY timestamp_blk",
        (MIN_MAGNITUD_FIRMA,),
    ).fetchall()
    if max_eventos:
        eventos = eventos[:max_eventos]

    logger.info(
        f"=== FASE 1 RECONOCIMIENTO: {len(eventos)} eventos M{MIN_MAGNITUD_FIRMA}+ ==="
    )

    stats = {"eventos": len(eventos), "firmas_nuevas": 0, "recurrencias": 0,
             "sin_datos": 0}

    for ts_evento, id_nodo, mag in eventos:
        features = extraer_features_ventana(conn, ts_evento, id_nodo)
        if features is None:
            stats["sin_datos"] += 1
            continue

        clase = _event_class(mag)
        evento_ref = f"{ts_evento}|nodo{id_nodo}|M{mag:.1f}"

        for bot, keys in BOT_FEATURES.items():
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


def backtest_disciplinario(db_path: str) -> Dict:
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
    logger.info(
        f"=== FASE 2 DISCIPLINA: {len(consolidadas)} firmas consolidadas ==="
    )

    stats = {"firmas_evaluadas": 0, "reconocidas": 0, "fallos": 0,
             "castigos_hijo": 0, "castigos_padre": 0}

    import json as _json
    from sentinel_omega.core.firmas.signature_engine import similitud
    from sentinel_omega.core.juez.pesos import castigar, reforzar, cargar_pesos

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
                ts_evento, nodo_part, _ = ref.split("|")
                id_nodo = int(nodo_part.replace("nodo", ""))
            except ValueError:
                continue

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

            if sim >= SIMILARITY_ALERT:
                stats["reconocidas"] += 1
                reforzar(conn, bot)
            else:
                stats["fallos"] += 1
                castigar(conn, bot, es_padre=es_padre)
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
                    },
                )
                juez.evaluar_pendientes(
                    evento_ocurrido=True,
                    verdad=ref,
                    firma_conocida=True,
                    multiplicador=2.0 if es_padre else 1.0,
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
    return {"fase1": fase1, "fase2": fase2}
