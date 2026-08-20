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
) -> int:
    """
    Registers padre + per-bot predictions. Returns number of bot rows registered.
    """
    matches = matches or []
    muro_lags = muro_lags or {}
    nodos_pred = nodos_pred or []

    ventana_h = 2
    for m in matches[:5]:
        dias = m.get("ventana_tipica_dias")
        if dias is not None:
            try:
                ventana_h = max(ventana_h, int(float(dias) * 24))
            except (TypeError, ValueError):
                pass
    if matches and ventana_h == 2 and conn is not None:
        try:
            row = conn.execute(
                "SELECT MAX(lag_promedio_h), MAX(lag_max_h) "
                "FROM tbl_lag_anticipacion"
            ).fetchone()
            if row and row[0]:
                ventana_h = max(ventana_h, int(row[0]))
            if row and row[1]:
                ventana_h = max(ventana_h, int(row[1]))
        except Exception:
            pass
    ventana_h = min(max(2, ventana_h), 90 * 24)

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
            juez.registrar_prediccion(
                bot_name=str(name).lower(),
                prediccion=pred,
                confianza=conf,
                ventana_h=ventana_h,
                detalles={
                    "nodos": nodos_pred,
                    "padre_signal": geo.final_signal.value,
                    "reasoning": (getattr(sig, "reasoning", "") or "")[:500],
                },
                fase="viva",
            )
            n_bots += 1
        except Exception as e:
            logger.warning("No se registró predicción de bot: %s", e)
    return n_bots
