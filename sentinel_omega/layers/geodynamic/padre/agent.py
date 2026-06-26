"""
Padre / Árbitro — Geodynamic Consensus Layer
Asymmetric Loss: missed events penalized 10× more than false alarms.
VETO power: no alert without full mathematical consensus across all 3 layers.

Layers required for consensus:
  1. Historical (Alfa-1 + Beta-1)
  2. Real-time cortical stress (Alfa-2 + Beta-2)
  3. Topological alignment (Delta)
"""

import time
from typing import Any, Dict, List

from sentinel_omega.core.shared.agent_base import (
    PadreAgent, AgentSignal, ConsensusResult, SignalType
)


class GeodynamicPadre(PadreAgent):

    LAYER_MAPPING = {
        "alfa1": "historical",
        "beta1": "historical",
        "alfa2": "realtime",
        "beta2": "realtime",
        "delta": "topological",
    }

    REQUIRED_LAYERS = {"historical", "realtime", "topological"}

    def __init__(self):
        super().__init__(name="padre_geo", domain="geodynamic")
        self.miss_penalty = 10.0
        self.false_alarm_penalty = 1.0

    def evaluate_consensus(self, signals: List[AgentSignal]) -> ConsensusResult:
        layer_signals: Dict[str, List[AgentSignal]] = {
            "historical": [], "realtime": [], "topological": []
        }

        for sig in signals:
            layer = self.LAYER_MAPPING.get(sig.agent_name)
            if layer:
                layer_signals[layer].append(sig)

        missing = self.REQUIRED_LAYERS - {
            k for k, v in layer_signals.items() if v
        }
        if missing:
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.NO_SIGNAL,
                confidence=0.0,
                agent_signals=signals,
                veto_active=True,
                veto_reason=f"Missing layers: {missing}"
            )

        layer_verdicts = {}
        for layer_name, layer_sigs in layer_signals.items():
            alerts = [s for s in layer_sigs if s.signal_type == SignalType.ALERT]
            layer_verdicts[layer_name] = len(alerts) > 0

        all_agree = all(layer_verdicts.values())

        if all_agree:
            avg_confidence = sum(s.confidence for s in signals) / len(signals)
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.ALERT,
                confidence=avg_confidence,
                agent_signals=signals,
            )

        if self.veto_check(signals):
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.NO_SIGNAL,
                confidence=0.0,
                agent_signals=signals,
                veto_active=True,
                veto_reason="Insufficient cross-layer agreement"
            )

        return ConsensusResult(
            consensus_reached=False,
            final_signal=SignalType.NEUTRAL,
            confidence=0.3,
            agent_signals=signals,
        )
