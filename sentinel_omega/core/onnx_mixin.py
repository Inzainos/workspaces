"""Shared ONNX load + predict helpers for geodynamic agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType

logger = logging.getLogger(__name__)

_SIGNAL_MAP = {
    "NO_SIGNAL": SignalType.NO_SIGNAL,
    "NEUTRAL": SignalType.NEUTRAL,
    "WATCH": SignalType.WATCH,
    "ALERT": SignalType.ALERT,
    "BULLISH": SignalType.BULLISH,
    "BEARISH": SignalType.BEARISH,
}


def try_load_onnx(bot_name: str) -> Tuple[Any, Any]:
    """Load ONNX session + inference wrapper. Returns (session, inference) or (None, None)."""
    try:
        from sentinel_omega.config.onnx_config import onnx_config
        from sentinel_omega.core.onnx_engine import ONNXBotInference, ONNXModelLoader

        cfg = getattr(onnx_config, bot_name, None)
        if cfg is None or not cfg.enabled:
            logger.info(f"{bot_name}: ONNX config missing/disabled")
            return None, None
        loader = ONNXModelLoader(onnx_config.runtime, models_dir=onnx_config.models_dir)
        session = loader.load_model(cfg)
        if session is None:
            logger.info(f"{bot_name}: sin modelo ONNX — rama de reglas activa")
            return None, None
        inference = ONNXBotInference(bot_name, cfg, session)
        logger.info(f"{bot_name}: modelo ONNX cargado — rama ML activa")
        return session, inference
    except Exception as exc:
        logger.info(f"{bot_name}: ONNX no disponible ({exc}) — rama de reglas")
        return None, None


def predict_signal(
    inference: Any,
    vector: np.ndarray,
    *,
    allow_alert: bool = True,
    allow_bullish_bearish: bool = False,
) -> Optional[Tuple[SignalType, float, str]]:
    """Run ONNX predict; map to SignalType. None → caller uses rule branch."""
    if inference is None:
        return None
    try:
        vec = np.asarray(vector, dtype=np.float32).reshape(-1)
        conf, name = inference.predict(vec)
        if conf <= 0.0 or name in ("NO_SIGNAL", "UNKNOWN"):
            return None
        tipo = _SIGNAL_MAP.get(name)
        if tipo is None:
            return None
        if not allow_alert and tipo == SignalType.ALERT:
            tipo = SignalType.WATCH
            name = "WATCH"
        if not allow_bullish_bearish and tipo in (SignalType.BULLISH, SignalType.BEARISH):
            tipo = SignalType.WATCH
            name = "WATCH"
        return tipo, float(min(conf, 0.95)), name
    except Exception as exc:
        logger.warning(f"ONNX predict failed: {exc}")
        return None


def pad_vector(values: list, n: int) -> np.ndarray:
    """Fixed-length float32 vector; missing dims → 0."""
    out = np.zeros(n, dtype=np.float32)
    for i, v in enumerate(values[:n]):
        if v is None:
            continue
        try:
            fv = float(v)
            if np.isfinite(fv):
                out[i] = fv
        except (TypeError, ValueError):
            pass
    return out


# ─── Inferencia con el vector canónico, para cualquier bot ────────────────────
#
# Hasta el 2026-09-26 solo alfa1 y omega inferían con ONNX: el reentrenamiento
# semanal producía OCHO modelos y seis no se usaban nunca. Y eso tenía un efecto
# que no era obvio --- lo vio el operador: los bots que no alarman **no pueden
# ser castigados por alarmar**, así que el Juez hundía al que participa (alfa1,
# 669 alarmas, peso 0.300) y dejaba en el techo a los que callan (loki, delta,
# alfa2: 0 alarmas, 0 castigos, peso 1.000, y los 37 eventos perdidos).
#
# `senal_desde_rasgos` arma el vector con el orden canónico (core/features_onnx)
# y devuelve la señal del modelo, o None si no hay modelo o la salida es
# degenerada --- en cuyo caso el agente usa su rama de reglas, como siempre.

_SESIONES: Dict[str, Any] = {}


def dimension_de_entrada(session: Any) -> Optional[int]:
    """Cuántos rasgos espera el `.onnx`, o None si la forma es dinámica."""
    try:
        forma = session.get_inputs()[0].shape
    except Exception:  # noqa: BLE001 — una sesión sin forma declarada no bloquea
        return None
    if not forma:
        return None
    ultimo = forma[-1]
    return int(ultimo) if isinstance(ultimo, int) else None


def inferencia_de(bot: str):
    """La sesión ONNX del bot, cargada una vez y reutilizada.

    **Se NIEGA a usar un modelo cuya entrada no coincida con `BOT_DIMS[bot]`**
    (condición de Agente-T, 2026-09-27). `vector_para` construye siempre
    `BOT_DIMS[bot]` posiciones: si el `.onnx` cargado espera otro número, o
    `pad_vector` lo recorta, o `onnxruntime` lanza y `predict_signal` devuelve
    None --- las dos cosas en silencio, y la segunda indistinguible de «no hay
    modelo». El caso concreto que hay que evitar: cambiar el vector y reiniciar
    con los modelos viejos todavía en disco. Preferimos la rama de reglas a un
    modelo que responde a columnas que no son las que aprendió.
    """
    if bot not in _SESIONES:
        session, inferencia = try_load_onnx(bot)
        if session is not None and inferencia is not None:
            from sentinel_omega.core.features_onnx import BOT_DIMS
            esperadas = BOT_DIMS.get(bot)
            reales = dimension_de_entrada(session)
            if esperadas is not None and reales is not None and reales != esperadas:
                logger.error(
                    "%s: el modelo ONNX espera %d rasgos y el vector canónico "
                    "tiene %d --- se DESCARTA y manda la rama de reglas. "
                    "Reentrena el modelo con el vector vigente (BOT_DIMS[%r]=%d).",
                    bot, reales, esperadas, bot, esperadas)
                inferencia = None
        _SESIONES[bot] = inferencia
    return _SESIONES[bot]


def senal_desde_rasgos(
    bot: str,
    rasgos: Dict[str, Any],
    *,
    permitir_alerta: bool = True,
) -> Optional[Tuple[SignalType, float, str]]:
    """Señal del modelo del bot a partir de rasgos POR NOMBRE.

    Devuelve None cuando no hay modelo, cuando el vector sale vacío --- pedir
    una predicción sobre todo ceros es pedir ruido --- o cuando la salida es
    degenerada. El agente decide qué hacer con el None; lo normal es su rama
    de reglas.
    """
    inferencia = inferencia_de(bot)
    if inferencia is None:
        return None
    try:
        from sentinel_omega.core.features_onnx import vector_para
        vec = vector_para(bot, rasgos)
    except (KeyError, ValueError) as e:
        logger.debug("%s: no se pudo armar el vector (%s)", bot, e)
        return None
    if not np.any(np.abs(vec) > 1e-12):
        logger.debug("%s: vector vacío, no se infiere", bot)
        return None
    return predict_signal(inferencia, vec, allow_alert=permitir_alerta)
