"""
Beta-Bolsa Agent — Fundamental & Macro Analysis
Sources: Financial statements, Fed/Banxico rates, yield curves
Variables: P/E, interest rates, yield spread, GDP growth
Method: Fundamental scoring + institutional friction

SNT Application:
  - Central banks = macro Hubs, national economies = Shadow Nodes
  - Interest rate differentials drive satellization velocity
  - Yield curve inversion = friction collapse signal
"""

from typing import Any, Dict

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import InstitutionalFrictionCalculator


class BetaBolsaAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="beta_bolsa", layer="bolsa")
        self._friction_calc = InstitutionalFrictionCalculator()
        self._interest_rate: float = 0.0
        self._yield_spread: float = 0.0
        self._pe_ratio: float = 0.0

    def ingest(self, data: Dict[str, Any]) -> None:
        self._interest_rate = data.get("interest_rate", 0.0)
        self._yield_spread = data.get("yield_spread_10y_2y", 0.0)
        self._pe_ratio = data.get("pe_ratio", 0.0)
        self.logger.info(f"Beta-Bolsa: rate={self._interest_rate:.2%}, spread={self._yield_spread:.2f}")

    def analyze(self) -> AgentSignal:
        friction = self._friction_calc.calculate(
            regulatory_density=0.6,
            structural_barriers=0.5,
            temporal_inertia=0.7,
            domain="stock_market"
        )

        yield_inverted = self._yield_spread < 0
        pe_extreme = self._pe_ratio > 30 or self._pe_ratio < 10

        risk_score = 0.0
        if yield_inverted:
            risk_score += 0.5
        if self._pe_ratio > 30:
            risk_score += 0.3
        if self._interest_rate > 0.06:
            risk_score += 0.2

        if risk_score > 0.6:
            return self.emit_signal(
                SignalType.BEARISH, risk_score,
                data={
                    "yield_spread": self._yield_spread,
                    "pe_ratio": self._pe_ratio,
                    "interest_rate": self._interest_rate,
                    "friction": friction.score,
                },
                reasoning=f"Macro stress: yield_spread={self._yield_spread:.2f}, P/E={self._pe_ratio:.1f}"
            )
        elif self._yield_spread > 1.0 and self._pe_ratio < 18:
            return self.emit_signal(
                SignalType.BULLISH, 0.65,
                data={"yield_spread": self._yield_spread, "pe_ratio": self._pe_ratio},
                reasoning="Favorable macro: positive yield spread, reasonable valuations"
            )

        return self.emit_signal(SignalType.NEUTRAL, 0.3)

    def health_check(self) -> bool:
        return self._interest_rate > 0 or self._pe_ratio > 0
