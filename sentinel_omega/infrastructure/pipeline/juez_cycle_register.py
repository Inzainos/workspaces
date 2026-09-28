"""
Register Juez predictions for Padre + every agent in agent_signals.

Called from launcher after consensus. Ventana adaptativa (2h floor, lag empírica, tope 90d).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def register_cycle_predictions(
    juez: Any,
    geo: Any,
    matches: Optional[List[Dict]] = None,
    conn: Any = None,
    muro_lags: Optional[Dict] = None,
    nodos_pred: Optional[List[Dict]] = None,
    features: Optional[Dict] = None,
) -> int:
    """
    Registers padre + per-bot predictions. Returns number of bot rows registered.

    `features` (fix 2026-08-20): snapshot de telemetría general del ciclo
    (mismo dict que produce _build_live_features() — bz_mean, kp_mean,
    fase_lunar, schumann_mean, so2_kt_win, btc_volatilidad, etc.). Se
    guarda bajo la clave "features_generales" en detalles_json de CADA
    predicción registrada (padre + cada bot). Sin esto, el reentrenamiento
    ONNX (train_onnx_from_db.py::load_juez_feedback) no tenía forma de
    reconstruir vectores de features reales desde el feedback historico
    del Juez — en particular, el feedback de "padre" (remapeado a "omega"
    para entrenamiento, porque Omega aprende de telemetría general/
    consenso, no de un dominio especifico) caía casi siempre en un vector
    vacío. Retrocompatible: filas registradas ANTES de este fix
    simplemente no tendran "features_generales" en su detalles_json.
    """
    matches = matches or []
    muro_lags = muro_lags or {}
    nodos_pred = nodos_pred or []
    features = features or {}

    ventana_h = 2

    juez.registrar_prediccion(
        bot_name="padre",
        prediccion=geo.final_signal.value,
        confianza=geo.confidence,
        ventana_h=ventana_h,
        detalles={
            "firma_matches": matches[:5],
            "muro_lags": muro_lags,
            "nodos": nodos_pred,
            "ventana_h": ventana_h,
            "features_generales": features,
        },
        fase="viva",
    )

    n_bots = 0
    for sig in (getattr(geo, "agent_signals", None) or []):
        try:
            name = getattr(sig, "agent_name", None)
            st = getattr(sig, "signal_type", None)
            conf = float(getattr(sig, "confidence", 0) or 0)
            if not name or st is None:
                continue
            pred = st.value if hasattr(st, "value") else str(st)
            detalles = {
                "nodos": nodos_pred,
                "padre_signal": geo.final_signal.value,
                "reasoning": (getattr(sig, "reasoning", "") or "")[:500],
                "features_generales": features,
            }
            # Quién decidió: el modelo o la regla.
            #
            # `layer_runners._aplicar_modelos` calcula estos cinco campos y los
            # deja en `sig.data` diciendo, en su propio docstring, «para que el
            # Juez pueda comparar después quién acertaba». Este registrador
            # armaba el `detalles` con cuatro claves fijas y **nunca leía
            # `sig.data`**, así que se calculaban y se tiraban: medido el
            # 2026-09-27, **0 filas** de `TBL_JUEZ_AUDITORIA` tenían
            # `onnx_senal`. En todo el histórico no hay forma estructurada de
            # saber si un veredicto lo dio el modelo o la regla --- el único
            # rastro era la prosa del `reasoning`, que además describía la
            # REGLA aunque mandara el modelo (arreglado el mismo día).
            #
            # La señal medida y no conectada, en el camino de auditoría.
            #
            # Con esto la comparación es consultable en vez de parseable:
            #
            #   SELECT bot_name, resultado, COUNT(*) FROM TBL_JUEZ_AUDITORIA
            #   WHERE json_extract(detalles_json,'$.onnx_senal') IS NOT NULL
            #     AND json_extract(detalles_json,'$.onnx_senal')
            #      != json_extract(detalles_json,'$.regla_senal')
            #   GROUP BY 1,2;
            #
            # Solo se copian las claves que `_aplicar_modelos` produce; no se
            # volcó `sig.data` entero a propósito, para que el `detalles_json`
            # no crezca con lo que cada agente decida meter en su `data`.
            datos = getattr(sig, "data", None)
            if isinstance(datos, dict):
                # `gano` se añade el 2026-09-27 con la regla del empate por
                # confianza: sin él, saber QUIÉN decidió volvería a requerir
                # recalcular la comparación en vez de leerla --- el mismo defecto
                # que este bloque arregla.
                for clave in ("onnx", "onnx_senal", "onnx_conf",
                              "regla_senal", "regla_conf", "gano"):
                    if clave in datos:
                        detalles[clave] = datos[clave]
            juez.registrar_prediccion(
                bot_name=str(name).lower(),
                prediccion=pred,
                confianza=conf,
                ventana_h=ventana_h,
                detalles=detalles,
                fase="viva",
            )
            n_bots += 1
        except Exception as e:
            logger.warning("No se registró predicción de bot: %s", e)
    return n_bots
