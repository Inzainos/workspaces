"""
Delta Agent — Transdisciplinary Abstraction & Energetic Nodes
Variables: Psychosocial metrics, energetic node topology, behavioral patterns
Method: Stochastic weighting based on SNT N-Body principles
Role: Noise filtering, network topology ponderator

Core axiom: Mass behavioral alterations correlate with local EM field changes.
Maps planetary energetic nodes using distributed network principles.
"""

import numpy as np
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import NBodyMatrix


class DeltaAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="delta", layer="geodynamic")
        self._nbody = NBodyMatrix()
        self._node_data: Optional[Dict[str, float]] = None
        self._psychosocial_index: float = 0.0

    def ingest(self, data: Dict[str, Any]) -> None:
        self._node_data = data.get("energetic_nodes")
        self._psychosocial_index = data.get("psychosocial_index", 0.0)
        self.logger.info(f"Delta ingested: {len(self._node_data or {})} nodes, PSI={self._psychosocial_index:.2f}")

    def analyze(self) -> AgentSignal:
        if not self._node_data:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        hub_name = max(self._node_data, key=self._node_data.get)
        result = self._nbody.analyze(self._node_data, hub_name)

        extraction_mean = np.mean([n.extraction_vector for n in result.nodes])
        topology_stress = abs(result.power_law_b + 0.5)

        combined_score = (
            topology_stress * 0.4
            + self._psychosocial_index * 0.3
            + extraction_mean * 0.3
        )

        if combined_score > 0.7:
            return self.emit_signal(
                SignalType.ALERT, combined_score,
                data={
                    "power_law_b": result.power_law_b,
                    "r_squared": result.r_squared,
                    "psychosocial_index": self._psychosocial_index,
                    "n_nodes": len(result.nodes),
                },
                reasoning=f"Topological stress elevated: b={result.power_law_b:.3f}, PSI={self._psychosocial_index:.2f}"
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data={"power_law_b": result.power_law_b},
            reasoning="Topology within normal bounds"
        )

    def health_check(self) -> bool:
        return self._node_data is not None and len(self._node_data) >= 3
