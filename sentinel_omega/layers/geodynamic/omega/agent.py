"""
Omega — lectura espacial independiente (sin sesgo fijo Shadow DOM).

Vota en el ciclo; el Padre puede no contarlo en el córum hasta que su
asertividad viva supere a la del consenso. Lee telemetría espacial y
consulta el veredicto de Beta-1 (patrones / cimática Schumann).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType

logger = logging.getLogger(__name__)


# La fundamental de Schumann. Es una REFERENCIA física --- contra ella se mide
# la desviación ---, NO un valor de relleno.
#
# Hasta el 2026-09-26 cumplía los dos papeles a la vez: `float(d.get(...) or
# 7.83)`. Sin lectura, `sch` valía 7.83, `abs(sch - SCHUMANN_FUNDAMENTAL_HZ)`
# daba 0 y omega concluía «Schumann normal» sin haber medido nada. Con Tomsk
# caído desde el 11 de septiembre, eso es lo que venía pasando cada ciclo.
#
# Faltante es faltante: ahora `sch` es None y las dos ramas que lo usan lo
# tratan como «no lo sé».
SCHUMANN_FUNDAMENTAL_HZ = 7.83
SCHUMANN_DESVIACION_MINIMA_HZ = 0.4


def _primero(d, *claves):
    """El primer valor REAL entre varias claves, o None si ninguna lo trae.

    Sustituye a `float(d.get("a") or d.get("b") or 0.0)`. Ese `or` trataba un
    **0 medido** como ausencia --- Bz cruzando cero, Kp en calma --- y saltaba a
    la clave siguiente o al respaldo. Aquí sólo None y NaN son ausencia.
    """
    for k in claves:
        v = d.get(k)
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv == fv:          # descarta NaN
            return fv
    return None


class OmegaAgent(BaseAgent):
    """Bot de correlación espacial independiente."""

    def __init__(self):
        super().__init__(name="omega", layer="geodynamic")
        self._data: Dict[str, Any] = {}
        self._beta_signal: Optional[AgentSignal] = None
        self._onnx = None  # ONNXBotInference
        try:
            from sentinel_omega.core.onnx_mixin import try_load_onnx
            _sess, self._onnx = try_load_onnx("omega")
        except Exception as e:
            logger.debug(f"Omega ONNX no cargado: {e}")
            self._onnx = None

    def ingest(self, data: Dict[str, Any]) -> None:
        self._data = dict(data or {})

    def set_beta_context(self, beta_signal: Optional[AgentSignal]) -> None:
        """Consulta a Beta: qué patrón / forma de energía ve."""
        self._beta_signal = beta_signal

    def health_check(self) -> bool:
        return True

    def _feature_vector(self) -> list:
        d = self._data
        # `_primero` en vez de `or`: el `or` se dispara con un 0 LEGÍTIMO
        # (Bz cruzando cero, Kp en calma) y salta a la clave siguiente o al
        # respaldo. Y donde no hay dato, la clave NO entra: `vector_para` deja
        # 0.0 ahí, que es exactamente con lo que se entrenó el modelo. Meter
        # 7.83 sería preguntarle con un valor que nunca vio en ese hueco.
        fase = _primero(d, "fase_lunar", "moon_phase")
        sicigia = 1.0 if d.get("es_sicigia") or d.get("syzygy") else 0.0
        sch_mean = _primero(d, "schumann_mean", "schumann_hz")
        sch_std = _primero(d, "schumann_std")
        bz = _primero(d, "bz", "bz_nT")
        kp = _primero(d, "kp", "kp_max")
        wind = _primero(d, "viento", "wind_kms")
        beta_conf = float(self._beta_signal.confidence) if self._beta_signal else 0.0
        beta_alert = 0.0
        if self._beta_signal and self._beta_signal.signal_type in (
            SignalType.ALERT, SignalType.WATCH
        ):
            beta_alert = 1.0
        # Las posiciones las manda el orden canónico del modelo
        # (core/features_onnx.py), no este return. Medido el 2026-09-25: esta
        # lista ponía beta_conf y beta_alert en las posiciones 7 y 8, donde el
        # modelo espera `bz_min` y `kp_max`, y dejaba las tres últimas en cero.
        # La señal de beta no está en el vector del modelo: se usa en la rama de
        # reglas de `analyze`, que es donde tiene sentido.
        from sentinel_omega.core.features_onnx import vector_para
        candidatos = {
            "fase_lunar": fase,
            "es_sicigia": sicigia,
            "schumann_mean": sch_mean,
            "schumann_std": sch_std,
            "bz_mean": bz,
            "kp_mean": kp,
            "viento_avg": wind,
            "bz_min": _primero(d, "bz_min") if _primero(d, "bz_min") is not None else bz,
            "kp_max": _primero(d, "kp_max") if _primero(d, "kp_max") is not None else kp,
            "kp_max_72h": _primero(d, "kp_max_72h", "kp_max") if
                          _primero(d, "kp_max_72h", "kp_max") is not None else kp,
        }
        rasgos = {k: v for k, v in candidatos.items() if v is not None}
        self._ultimo_beta = (beta_conf, beta_alert)   # para la rama de reglas
        return list(vector_para("omega", rasgos))

    def analyze(self) -> AgentSignal:
        d = self._data
        bz = _primero(d, "bz", "bz_nT")
        kp = _primero(d, "kp", "kp_max")
        sch = _primero(d, "schumann_hz", "schumann_mean")
        reasoning_parts = []

        signal = SignalType.NEUTRAL
        conf = 0.2

        stress = 0.0
        if bz is None:
            reasoning_parts.append("Bz=sin dato")
        elif bz <= -8:
            stress += 0.35
            reasoning_parts.append(f"Bz={bz:.1f} (sur fuerte)")
        elif bz <= -5:
            stress += 0.2
            reasoning_parts.append(f"Bz={bz:.1f}")
        if kp is None:
            reasoning_parts.append("Kp=sin dato")
        elif kp >= 6:
            stress += 0.35
            reasoning_parts.append(f"Kp={kp:.1f}")
        elif kp >= 5:
            stress += 0.2
            reasoning_parts.append(f"Kp={kp:.1f}")
        if sch is None:
            # Sin lectura no se suma estrés NI se dice que está normal: la
            # ausencia se nombra, para que el parte no parezca una medición.
            reasoning_parts.append("Schumann=sin dato")
        elif abs(sch - SCHUMANN_FUNDAMENTAL_HZ) >= SCHUMANN_DESVIACION_MINIMA_HZ:
            stress += 0.15
            reasoning_parts.append(f"Schumann={sch:.2f} Hz")

        if self._beta_signal is not None:
            if self._beta_signal.signal_type == SignalType.ALERT:
                stress += 0.25 * float(self._beta_signal.confidence)
                reasoning_parts.append(
                    f"Beta ve {self._beta_signal.signal_type.value} "
                    f"({self._beta_signal.confidence:.0%})"
                )
            elif self._beta_signal.signal_type == SignalType.WATCH:
                stress += 0.12 * float(self._beta_signal.confidence)
                reasoning_parts.append("Beta en WATCH")

        try:
            if self._onnx is not None:
                from sentinel_omega.core.onnx_mixin import pad_vector, predict_signal
                n_feat = getattr(self._onnx, "n_features", None)
                if n_feat is None:
                    cfg = getattr(self._onnx, "config", None)
                    n_feat = getattr(cfg, "input_features", 12) if cfg else 12
                vec = pad_vector(self._feature_vector(), int(n_feat))
                pred = predict_signal(self._onnx, vec)
                if pred is not None:
                    onnx_sig, onnx_conf, onnx_name = pred
                    conf = max(conf, float(onnx_conf or 0))
                    if onnx_sig in (SignalType.ALERT, SignalType.WATCH):
                        signal = onnx_sig
                        stress = max(stress, conf)
                    reasoning_parts.append(
                        f"ONNX={onnx_name}@{onnx_conf:.2f}"
                    )
        except Exception as e:
            logger.debug(f"Omega ONNX infer: {e}")

        if signal == SignalType.NEUTRAL:
            if stress >= 0.55:
                signal = SignalType.ALERT
                conf = min(0.5 + stress * 0.4, 0.92)
            elif stress >= 0.30:
                signal = SignalType.WATCH
                conf = min(0.35 + stress * 0.4, 0.75)
            else:
                signal = SignalType.NEUTRAL
                conf = max(0.15, 0.4 - stress)

        reasoning = "Omega espacial: " + (
            "; ".join(reasoning_parts) if reasoning_parts else "sin anomalía"
        )
        return self.emit_signal(
            signal, conf,
            data={
                "bz": bz, "kp": kp, "schumann": sch,
                "stress": stress,
                "beta_asked": self._beta_signal is not None,
            },
            reasoning=reasoning,
        )
