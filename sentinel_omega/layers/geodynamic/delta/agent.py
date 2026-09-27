"""
Delta Agent — Financial Cross-Correlation & Earth Sentiment
Sources: Crypto (Binance, CoinGecko), Bolsa (Yahoo, VIX), Fear & Greed
Variables: BTC dominance, VIX, yield spread, Fear & Greed, sector topology
Training window: 10 years
Role: CONTEXT provider — never a seismic-alert vote

The "humor de la tierra" — market fear, social sentiment, and financial stress
often shift before or during major natural events. Delta captures these signals
for cross-correlation against the Schumann baseline (via Padre).

Honestidad de rol (v2.5.1):
  - Delta NUNCA emite ALERT al consenso: su techo es WATCH. El estrés
    financiero es contexto correlacionable, no evidencia sísmica directa —
    un VIX en 45 no vota por un sismo, solo enriquece la firma del Padre.
  - Se eliminó el "friction" institucional hardcodeado (0.4/0.3/0.5): eran
    constantes inventadas que inflaban el score compuesto sin dato real
    detrás. El score compuesto ahora sale solo de entradas medidas
    (Fear&Greed, VIX, curva de rendimientos, topología cripto/sectorial).
"""

import numpy as np
from typing import Any, Dict, Optional

import logging

from sentinel_omega.core.shared.agent_base import (
    AgentSignal,
    BaseAgent,
    SignalType,
    valor_medido,
)
from sentinel_omega.core.snt_engine import SatellizationEngine, NBodyMatrix


logger = logging.getLogger(__name__)


def _n(v, dec: int) -> str:
    """Formatea un número que puede ser None, sin fingir un cero."""
    return "sin dato" if v is None else f"{float(v):.{dec}f}"


class DeltaAgent(BaseAgent):

    TRAINING_YEARS = 10

    def __init__(self):
        super().__init__(name="delta", layer="geodynamic")
        self._snt = SatellizationEngine()
        self._nbody = NBodyMatrix()

        self._ingested: bool = False
        self._fear_greed: Optional[float] = None
        self._vix: Optional[float] = None
        self._btc_dominance: Optional[float] = None
        self._yield_spread: Optional[float] = None
        self._sector_values: Dict[str, float] = {}
        self._crypto_ratios: Dict[str, float] = {}

    def ingest(self, data: Dict[str, Any]) -> None:
        # Sin respaldos fabricados (2026-09-26, auditoría). Los cuatro valores
        # por defecto describían un mercado NORMAL --- miedo 50, VIX 20,
        # dominancia 0,5 y spread 0,5 --- y la decisión los leía como medidos:
        # `if self._yield_spread < 0` con el 0,5 de relleno concluye «curva no
        # invertida» sin haber consultado nada. Delta no tiene fuente financiera
        # desde el 2026-01-01, así que venía decidiendo con los cuatro inventados.
        self._fear_greed = valor_medido(data, "fear_greed")
        self._vix = valor_medido(data, "vix")
        self._btc_dominance = valor_medido(data, "btc_dominance")
        self._yield_spread = valor_medido(data, "yield_spread")
        self._sector_values = data.get("sector_market_caps", {})
        self._crypto_ratios = data.get("crypto_ratios", {})
        self._ingested = True
        self.logger.info(
            f"Delta: FGI={_n(self._fear_greed, 0)}, VIX={_n(self._vix, 1)}, "
            f"BTC_dom={_n(self._btc_dominance, 3)}, "
            f"spread={_n(self._yield_spread, 2)}"
        )

    def _market_fear_score(self) -> float:
        score = 0.0
        if self._fear_greed is not None:
            if self._fear_greed < 20:
                score += 0.4
            elif self._fear_greed > 80:
                score += 0.3
        if self._vix is not None:
            if self._vix > 35:
                score += 0.4
            elif self._vix < 12:
                score += 0.2
        # Sin spread NO se suma ni se descarta: no medir no es «curva normal».
        if self._yield_spread is not None and self._yield_spread < 0:
            score += 0.2
        return min(1.0, score)

    def _crypto_topology(self) -> Dict[str, Any]:
        if not self._crypto_ratios or len(self._crypto_ratios) < 3:
            return {"signal": SignalType.NEUTRAL, "confidence": 0.3, "b": 0.0}

        hub = max(self._crypto_ratios, key=self._crypto_ratios.get)
        result = self._nbody.analyze(self._crypto_ratios, hub)

        if result.power_law_b > 0.5:
            return {"signal": SignalType.BEARISH, "confidence": 0.65, "b": result.power_law_b}
        elif result.power_law_b < -0.2:
            return {"signal": SignalType.BULLISH, "confidence": 0.6, "b": result.power_law_b}
        return {"signal": SignalType.NEUTRAL, "confidence": 0.3, "b": result.power_law_b}

    def _sector_topology(self) -> Dict[str, Any]:
        if not self._sector_values or len(self._sector_values) < 3:
            return {"concentration": 0.0}

        hub = max(self._sector_values, key=self._sector_values.get)
        result = self._nbody.analyze(self._sector_values, hub)
        return {
            "power_law_b": result.power_law_b,
            "concentration": result.composite_gradient,
        }

    def analyze(self) -> AgentSignal:
        fear_score = self._market_fear_score()
        crypto_topo = self._crypto_topology()
        sector_topo = self._sector_topology()

        # Score compuesto SOLO de entradas medidas — sin constantes inventadas
        combined = fear_score * 0.7
        if crypto_topo["signal"] != SignalType.NEUTRAL:
            combined += 0.15
        if sector_topo.get("concentration", 0) > 0.7:
            combined += 0.15

        signal_data = {
            "fear_greed": self._fear_greed,
            "vix": self._vix,
            "btc_dominance": self._btc_dominance,
            "yield_spread": self._yield_spread,
            "market_fear_score": fear_score,
            "crypto_b": crypto_topo.get("b", 0.0),
            "sector_concentration": sector_topo.get("concentration", 0.0),
        }

        # Diagnóstico: delta emitió NEUTRAL en 1.815 ciclos seguidos. Registra
        # el compuesto y sus entradas para ver si es calma real o señal rota.
        logger.info(
            "DELTA diag: combined=%.3f fear=%.3f vix=%s spread=%s | "
            "umbrales ALERT(>0.6) WATCH(>0.35)",
            combined, fear_score, _n(self._vix, 1), _n(self._yield_spread, 2),
        )

        if combined > 0.6:
            reasons = []
            if fear_score > 0.5:
                reasons.append(f"market fear ({fear_score:.2f})")
            if self._vix is not None and self._vix > 35:
                reasons.append(f"VIX extreme ({self._vix:.1f})")
            if self._yield_spread is not None and self._yield_spread < 0:
                reasons.append("yield curve inverted")
            sin_dato = [n for n, v in (("VIX", self._vix),
                                       ("spread", self._yield_spread),
                                       ("FGI", self._fear_greed))
                        if v is None]
            if sin_dato:
                reasons.append(f"sin dato: {', '.join(sin_dato)}")
            # Techo WATCH: el estrés financiero es CONTEXTO para el Padre, no
            # evidencia sísmica.
            #
            # Hasta el 2026-09-26 este comentario decía exactamente eso y la
            # línea siguiente emitía ALERT. Tres fuentes no concordaban:
            #
            #   este comentario        -> «nunca un voto de ALERT sísmico»
            #   layer_runners.py:303   -> SIN_ALERTA = {"delta"}
            #   CLAUDE.md              -> «ALERT si combined>0.6»
            #
            # Y el tope de `SIN_ALERTA` sólo capa la rama ONNX
            # (`permitir_alerta`), así que la regla podía emitir ALERT cuando el
            # modelo callaba --- es decir, el techo se caía justo cuando delta
            # tenía menos datos. Era un hueco latente: en fase viva delta nunca
            # alarmó (2.464 neutral, 0 alert), y los 65.232 «alert» de la fase
            # de reconocimiento son del arnés de entrenamiento, que registra
            # `alert` para los OCHO bots al reproducir eventos conocidos.
            #
            # La confianza se conserva: un estrés fuerte (combined > 0,6) sigue
            # valiendo más que el WATCH moderado de abajo, y esa diferencia es
            # información que el Padre usa.
            return self.emit_signal(
                SignalType.WATCH, min(0.5 + combined * 0.3, 0.8),
                data=signal_data,
                reasoning=(
                    f"Financial stress (contexto, techo WATCH): "
                    f"{', '.join(reasons) or 'elevated composite'}"
                ),
            )

        if combined > 0.35:
            return self.emit_signal(
                SignalType.WATCH, 0.4 + combined * 0.2,
                data=signal_data,
                reasoning=f"Moderate financial anomaly (score={combined:.2f})",
            )

        # «Normal bounds» solo si se midió algo. Sin una sola fuente ---
        # y delta no tiene fuente financiera desde el 2026-01-01 --- decir
        # «mercados dentro de lo normal» es afirmar lo que no se consultó.
        medidos = [v for v in (self._fear_greed, self._vix,
                               self._btc_dominance, self._yield_spread)
                   if v is not None]
        if not medidos:
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                data=signal_data,
                reasoning="Sin datos financieros: no se midió nada",
            )
        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data=signal_data,
            reasoning="Financial markets within normal bounds",
        )

    def health_check(self) -> bool:
        # Flag explícito: VIX==20.0 o FGI==50.0 exactos son valores válidos,
        # no evidencia de "sin datos".
        return self._ingested
