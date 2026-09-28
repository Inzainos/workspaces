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


# El ayudante vive en `core/shared/agent_base.py`: omega y delta caían en el
# mismo patrón y no conviene tener dos copias que luego divergan.
from sentinel_omega.core.shared.agent_base import valor_medido as _primero


# ─── Los nombres con los que llega cada magnitud ─────────────────────────────
#
# Medido el 2026-09-27 (Juez, 44 de 44 ciclos desde las 13:59 CST): la regla
# escribía «Bz=sin dato; Kp=sin dato» con el ciclo trayendo Bz −0,93 y Kp 1.
# Buscaba `bz`/`bz_nT` y `kp`/`kp_max`, y el runner le pasaba el `alfa1_data`
# crudo (un `omni_dataframe` con la columna `bz_gsm`, ningún escalar). Ahora el
# runner fusiona los rasgos CANÓNICOS del ciclo (`_rasgos_del_ciclo`, los mismos
# que ve `_aplicar_modelos` y que guarda el Juez) y aquí se aceptan los alias.
# El primer nombre de cada tupla es el canónico.
CLAVES_BZ = ("bz_mean", "bz_gsm", "bz", "bz_nT")
CLAVES_KP_REGLA = ("kp_max", "kp", "kp_mean")   # umbral de tormenta: el máximo
CLAVES_KP_MEDIA = ("kp_mean", "kp")
CLAVES_VIENTO = ("viento_avg", "plasma_speed", "viento", "wind_kms")
CLAVES_FASE = ("fase_lunar", "moon_phase")
CLAVES_SICIGIA = ("es_sicigia", "syzygy")
CLAVES_SCHUMANN = ("schumann_hz", "schumann_mean")


class OmegaAgent(BaseAgent):
    """Bot de correlación espacial independiente."""

    def __init__(self):
        super().__init__(name="omega", layer="geodynamic")
        self._data: Dict[str, Any] = {}
        self._beta_signal: Optional[AgentSignal] = None
        # Ya no se carga un modelo aquí: el de omega habla SOLO en
        # `layer_runners._aplicar_modelos` (ver el bloque de `analyze`).
        self._onnx = None

    def ingest(self, data: Dict[str, Any]) -> None:
        self._data = dict(data or {})

    def set_beta_context(self, beta_signal: Optional[AgentSignal]) -> None:
        """Consulta a Beta: qué patrón / forma de energía ve."""
        self._beta_signal = beta_signal

    def health_check(self) -> bool:
        return True

    def _feature_vector(self) -> list:
        """El vector canónico de omega con lo que trae `ingest`.

        Ya no lo usa `analyze` (no infiere); queda para diagnóstico y para
        comparar con el que arma `_aplicar_modelos`: con los rasgos del ciclo
        fusionados, los dos tienen que salir iguales.
        """
        d = self._data
        # `_primero` en vez de `or`: el `or` se dispara con un 0 LEGÍTIMO
        # (Bz cruzando cero, Kp en calma) y salta a la clave siguiente o al
        # respaldo. Y donde no hay dato, la clave NO entra: `vector_para` deja
        # 0.0 ahí. Meter 7.83 sería preguntarle con un valor que nunca vio en
        # ese hueco.
        bz = _primero(d, *CLAVES_BZ)
        kp_media = _primero(d, *CLAVES_KP_MEDIA)
        kp_regla = _primero(d, *CLAVES_KP_REGLA)
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
        from sentinel_omega.core.features_onnx import vector_para
        bz_min = _primero(d, "bz_min")
        kp_max = _primero(d, "kp_max")
        kp_72 = _primero(d, "kp_max_72h", "kp_max")
        candidatos = {
            "fase_lunar": _primero(d, *CLAVES_FASE),
            "es_sicigia": _primero(d, *CLAVES_SICIGIA),
            "schumann_mean": _primero(d, "schumann_mean", "schumann_hz"),
            "schumann_std": _primero(d, "schumann_std"),
            "bz_mean": bz,
            "kp_mean": kp_media,
            "viento_avg": _primero(d, *CLAVES_VIENTO),
            "bz_min": bz_min if bz_min is not None else bz,
            "kp_max": kp_max if kp_max is not None else kp_regla,
            "kp_max_72h": kp_72 if kp_72 is not None else kp_regla,
        }
        rasgos = {k: v for k, v in candidatos.items() if v is not None}
        self._ultimo_beta = (beta_conf, beta_alert)   # para la rama de reglas
        return list(vector_para("omega", rasgos))

    # ─── Por qué omega ya NO pregunta a su modelo desde aquí ──────────────
    #
    # Lo mismo que se hizo con alfa1 el 2026-09-27. Hasta hoy `analyze` corría
    # su propio ONNX con `pad_vector(self._feature_vector())` y
    # `_aplicar_modelos` volvía a correr EL MISMO modelo con el vector canónico
    # del ciclo. En la fila del Juez 8583612 (18:11 CST) quedaron las dos
    # lecturas en el mismo registro:
    #
    #     analyze()          NEUTRAL 0,42   ← vector TODO CEROS (claves que el
    #                                          runner no mandaba)
    #     _aplicar_modelos   WATCH   0,72   ← vector canónico, el que se guarda
    #
    # Un veredicto que sale de un vector que no se registra no se puede
    # reproducir ni calificar. El modelo habla en un solo sitio.

    def analyze(self) -> AgentSignal:
        d = self._data
        bz = _primero(d, *CLAVES_BZ)
        kp = _primero(d, *CLAVES_KP_REGLA)
        sch = _primero(d, *CLAVES_SCHUMANN)
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
        else:
            # Medido y en calma: se dice, para que el parte distinga «normal»
            # de «no lo sé».
            reasoning_parts.append(f"Bz={bz:.2f}")
        if kp is None:
            reasoning_parts.append("Kp=sin dato")
        elif kp >= 6:
            stress += 0.35
            reasoning_parts.append(f"Kp={kp:.1f}")
        elif kp >= 5:
            stress += 0.2
            reasoning_parts.append(f"Kp={kp:.1f}")
        else:
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

        # Solo la regla. El modelo habla en `_aplicar_modelos` (ver arriba).
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
