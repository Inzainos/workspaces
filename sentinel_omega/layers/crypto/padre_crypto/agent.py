"""
Padre-Crypto — Crypto Market Consensus & Position Management
Asymmetric loss: missed profitable trades penalized less than losing trades.
Risk management: position sizing based on consensus confidence.

Integration: Bitso HMAC-SHA256 API for MXN/crypto execution.
"""

import time
from typing import Any, Dict, List

from sentinel_omega.core.shared.agent_base import (
    PadreAgent, AgentSignal, ConsensusResult, SignalType
)


class CryptoPadre(PadreAgent):

    LAYER_MAPPING = {
        "alfa_crypto": "historical",
        "beta_crypto": "onchain",
        "delta_crypto": "sentiment",
    }

    REQUIRED_LAYERS = {"historical", "onchain", "sentiment"}

    MAX_POSITION_PCT = 0.05

    def __init__(self):
        super().__init__(name="padre_crypto", domain="crypto")
        self.miss_penalty = 3.0
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
                veto_reason=f"Only {len(active_layers)} layers active, need ≥2"
            )

        bullish = sum(1 for s in signals if s.signal_type == SignalType.BULLISH)
        bearish = sum(1 for s in signals if s.signal_type == SignalType.BEARISH)
        total_directional = bullish + bearish

        if total_directional == 0:
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.NEUTRAL,
                confidence=0.3,
                agent_signals=signals,
            )

        if bullish > bearish and bullish >= 2:
            avg_conf = sum(s.confidence for s in signals if s.signal_type == SignalType.BULLISH) / bullish
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.BULLISH,
                confidence=avg_conf,
                agent_signals=signals,
            )
        elif bearish > bullish and bearish >= 2:
            avg_conf = sum(s.confidence for s in signals if s.signal_type == SignalType.BEARISH) / bearish
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.BEARISH,
                confidence=avg_conf,
                agent_signals=signals,
            )

        return ConsensusResult(
            consensus_reached=False,
            final_signal=SignalType.NEUTRAL,
            confidence=0.2,
            agent_signals=signals,
            veto_active=True,
            veto_reason="Conflicting signals across layers"
        )

    def position_size(self, consensus: ConsensusResult, portfolio_value: float) -> float:
        if not consensus.consensus_reached:
            return 0.0
        return portfolio_value * self.MAX_POSITION_PCT * consensus.confidence
