"""
Padre-Bolsa — Stock Market Consensus & Risk Control
Asymmetric loss: capital preservation over profit maximization.
Position management: Kelly criterion scaled by consensus confidence.
"""

from typing import Any, Dict, List
from sentinel_omega.core.shared.agent_base import (
    PadreAgent, AgentSignal, ConsensusResult, SignalType
)


class BolsaPadre(PadreAgent):

    LAYER_MAPPING = {
        "alfa_bolsa": "technical",
        "beta_bolsa": "fundamental",
        "delta_bolsa": "regime",
    }

    REQUIRED_LAYERS = {"technical", "fundamental", "regime"}
    MAX_POSITION_PCT = 0.03

    def __init__(self):
        super().__init__(name="padre_bolsa", domain="bolsa")
        self.miss_penalty = 2.0
        self.false_alarm_penalty = 5.0

    def evaluate_consensus(self, signals: List[AgentSignal]) -> ConsensusResult:
        layer_signals: Dict[str, List[AgentSignal]] = {
            layer: [] for layer in self.REQUIRED_LAYERS
        }

        for sig in signals:
            layer = self.LAYER_MAPPING.get(sig.agent_name)
            if layer:
                layer_signals[layer].append(sig)

        active_layers = {k for k, v in layer_signals.items() if v}
        if len(active_layers) < 2:
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.NO_SIGNAL,
                confidence=0.0,
                agent_signals=signals,
                veto_active=True,
                veto_reason=f"Only {len(active_layers)} layers reporting"
            )

        bullish = sum(1 for s in signals if s.signal_type == SignalType.BULLISH)
        bearish = sum(1 for s in signals if s.signal_type == SignalType.BEARISH)

        if bullish >= 2 and bearish == 0:
            avg_conf = sum(s.confidence for s in signals if s.signal_type == SignalType.BULLISH) / bullish
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.BULLISH,
                confidence=avg_conf * 0.9,
                agent_signals=signals,
            )
        elif bearish >= 2 and bullish == 0:
            avg_conf = sum(s.confidence for s in signals if s.signal_type == SignalType.BEARISH) / bearish
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.BEARISH,
                confidence=avg_conf * 0.9,
                agent_signals=signals,
            )

        return ConsensusResult(
            consensus_reached=False,
            final_signal=SignalType.NEUTRAL,
            confidence=0.2,
            agent_signals=signals,
            veto_active=True,
            veto_reason="Mixed signals — capital preservation mode"
        )
