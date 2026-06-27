"""
Delta-Bolsa Agent — Market Regime & Geopolitical Topology
Sources: VIX, geopolitical risk indices, news NLP
Variables: Volatility regime, geopolitical risk, sector rotation
Method: SNT N-Body matrix on sector ETFs + regime HMM

SNT Application:
  - Sector ETFs as N-Body system with S&P500 as Hub
  - Regime changes = friction phase transitions
  - Geopolitical events = abrupt triggers (5.9× velocity)
"""

import numpy as np
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import NBodyMatrix


class DeltaBolsaAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="delta_bolsa", layer="bolsa")
        self._nbody = NBodyMatrix()
        self._vix: float = 20.0
        self._sector_values: Dict[str, float] = {}
        self._geopolitical_risk: float = 0.0

    def ingest(self, data: Dict[str, Any]) -> None:
        self._vix = data.get("vix", 20.0)
        self._sector_values = data.get("sector_market_caps", {})
        self._geopolitical_risk = data.get("geopolitical_risk_index", 0.0)
        self.logger.info(f"Delta-Bolsa: VIX={self._vix:.1f}, sectors={len(self._sector_values)}")

    def analyze(self) -> AgentSignal:
        vix_extreme_fear = self._vix > 35
        vix_complacency = self._vix < 12

        topology_data = {}
        if self._sector_values and len(self._sector_values) >= 3:
            hub = max(self._sector_values, key=self._sector_values.get)
            result = self._nbody.analyze(self._sector_values, hub)
            topology_data = {
                "power_law_b": result.power_law_b,
                "r_squared": result.r_squared,
                "concentration": result.composite_gradient,
            }

        if vix_extreme_fear:
            return self.emit_signal(
                SignalType.BULLISH, 0.7,
                data={"vix": self._vix, **topology_data},
                reasoning=f"VIX extreme fear ({self._vix:.1f}) — contrarian opportunity"
            )
        elif vix_complacency and self._geopolitical_risk > 0.7:
            return self.emit_signal(
                SignalType.BEARISH, 0.6,
                data={"vix": self._vix, "geo_risk": self._geopolitical_risk, **topology_data},
                reasoning=f"VIX complacency ({self._vix:.1f}) with high geo risk — danger"
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data={"vix": self._vix, **topology_data},
        )

    def health_check(self) -> bool:
        return self._vix > 0
