"""
Register Juez predictions for Padre + every agent in agent_signals.

Called from launcher after consensus. Ventana adaptativa (2h floor, lag empírica, tope 90d).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Umbral de «es el mismo evento», calibrado contra datos reales el 2026-09-28.
#
# Idea del operador: *«si te da la misma telemetría, es el mismo evento; si ya
# cambia algún detalle, ahí es otro distinto. Si es la misma que ya habías
# detectado, omites hasta que pase su ventana»*.
#
# Por qué hacía falta: el Juez registraba una predicción POR CICLO, así que un
# solo sismo M4.7 producía 23 filas por bot --- una cada ~5 min mientras el
# evento estuviera en la ventana de 2 h --- y el castigo se aplicaba a las 23.
# Medido ese día: 184 FALLO en 4 h eran **8 episodios**; factor de sobrecastigo
# **23x**. Los pesos de los nueve bots cayeron de 1,425 al suelo de 0,300 en esas
# cuatro horas, y con peso <0,6 el consenso degrada todo a WATCH.
#
# El sistema YA había aceptado contar por episodios --- `merito_relativo` usa
# `evaluar_episodios` y su docstring dice «37 ventanas-ciclo con evento eran 3
# episodios reales» --- pero solo en el refuerzo. Premiaba por episodio y
# castigaba por ciclo: la mitad corregida y la mitad sin corregir, en el mismo
# Juez.
#
# El umbral NO es numerología (regla dura 8). Medido sobre el episodio real:
#
#     ciclos consecutivos del mismo episodio   0,9883 - 0,9994
#     extremos del episodio contra su inicio   0,9775 - 0,9802
#     contra un ciclo de hace un día           0,8017
#
# 0,95 cae limpio entre 0,9775 y 0,8017. Advertencia: calibrado sobre UN
# episodio; revisar cuando haya más casos.
#
# Se compara contra el INICIO del episodio, no contra el ciclo anterior: por
# pasos la similitud es 0,999 y la deriva se acumularía hasta no cerrar nunca.
# Como la continuación no inserta fila, la fila abierta ES el inicio.
SIMILITUD_MISMO_EVENTO = 0.95


def _episodio_abierto(conn, bot_name: str, features: dict, ventana_h: int):
    """`id` de la prediccion del episodio ya abierto para ese bot, o None.

    Abierto = registrada dentro de su ventana y con telemetria equivalente.
    Sin conexion o sin telemetria devuelve None: ante la duda se registra, que
    es el comportamiento de antes.
    """
    if conn is None or not features:
        return None
    try:
        fila = conn.execute(
            "SELECT id, detalles_json FROM TBL_JUEZ_AUDITORIA "
            "WHERE fase='viva' AND bot_name=? "
            "AND timestamp >= strftime('%s','now') - ? "
            "ORDER BY timestamp DESC LIMIT 1",
            (bot_name, int(ventana_h) * 3600),
        ).fetchone()
    except Exception as e:  # noqa: BLE001 --- nunca bloquea el ciclo
        logger.warning("No se pudo buscar episodio abierto de %s: %s", bot_name, e)
        return None
    if not fila:
        return None
    try:
        previas = json.loads(fila[1] or "{}").get("features_generales") or {}
    except (ValueError, TypeError):
        return None
    if not previas:
        return None
    from sentinel_omega.core.firmas.signature_engine import similitud
    s = similitud(features, previas)
    return fila[0] if s >= SIMILITUD_MISMO_EVENTO else None


def _sumar_ciclo(conn, fila_id: int) -> None:
    """Un ciclo mas en el episodio abierto. Contar, no anotar --- igual que
    `tbl_cimatica_patrones`, que suma +1 a la frecuencia en vez de crear fila."""
    try:
        conn.execute(
            "UPDATE TBL_JUEZ_AUDITORIA SET detalles_json = json_set("
            "  COALESCE(detalles_json,'{}'), '$.ciclos',"
            "  COALESCE(json_extract(detalles_json,'$.ciclos'), 1) + 1)"
            " WHERE id = ?", (fila_id,))
        conn.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo sumar ciclo al episodio %s: %s", fila_id, e)


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
                # `onnx_callado` (2026-09-27): el modelo no se consultó por una
                # fuga medida (p. ej. "fuga:kp_mean"); sin guardarlo, un
                # `onnx: False` no distingue «callado a propósito» de «sin modelo».
                for clave in ("onnx", "onnx_senal", "onnx_conf",
                              "regla_senal", "regla_conf", "gano",
                              "onnx_callado"):
                    if clave in datos:
                        detalles[clave] = datos[clave]
            bot_l = str(name).lower()
            abierto = _episodio_abierto(conn, bot_l, features, ventana_h)
            if abierto is not None:
                # Misma telemetria dentro de la ventana: es el MISMO evento.
                # Se suma un ciclo al episodio y no se abre fila nueva.
                _sumar_ciclo(conn, abierto)
                continue
            juez.registrar_prediccion(
                bot_name=bot_l,
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
