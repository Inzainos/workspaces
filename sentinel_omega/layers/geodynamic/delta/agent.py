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

    LOW_PRESSURE_THRESHOLD = 1008.0

    def __init__(self):
        super().__init__(name="delta", layer="geodynamic")
        self._nbody = NBodyMatrix()
        self._node_data: Optional[Dict[str, float]] = None
        self._psychosocial_index: float = 0.0
        self._pressure_gradient: Optional[Dict[str, Any]] = None
        self._air_quality: Optional[Dict[str, float]] = None

    def ingest(self, data: Dict[str, Any]) -> None:
        self._node_data = data.get("energetic_nodes")
        self._psychosocial_index = data.get("psychosocial_index", 0.0)
        self._pressure_gradient = data.get("pressure_gradient")
        self._air_quality = data.get("air_quality")
        self.logger.info(f"Delta ingested: {len(self._node_data or {})} nodes, PSI={self._psychosocial_index:.2f}")

    def _atmospheric_stress(self) -> float:
        """Compute atmospheric stress factor from pressure gradient and air quality."""
        stress = 0.0
        if self._pressure_gradient:
            mean_p = self._pressure_gradient.get("mean_pressure", 1013.0)
            if mean_p < self.LOW_PRESSURE_THRESHOLD:
                stress += (self.LOW_PRESSURE_THRESHOLD - mean_p) / 20.0
            spread = self._pressure_gradient.get("pressure_spread", 0.0)
            if spread > 10.0:
                stress += spread / 50.0
        if self._air_quality:
            so2 = self._air_quality.get("so2", 0.0)
            if so2 > 20.0:
                stress += min(0.3, so2 / 100.0)
        return min(1.0, stress)

    def analyze(self) -> AgentSignal:
        if not self._node_data:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        hub_name = max(self._node_data, key=self._node_data.get)
        result = self._nbody.analyze(self._node_data, hub_name)

        extraction_mean = np.mean([n.extraction_vector for n in result.nodes])
        topology_stress = abs(result.power_law_b + 0.5)
        atm_stress = self._atmospheric_stress()

        combined_score = (
            topology_stress * 0.35
            + self._psychosocial_index * 0.25
            + extraction_mean * 0.25
            + atm_stress * 0.15
        )

        signal_data = {
            "power_law_b": result.power_law_b,
            "r_squared": result.r_squared,
            "psychosocial_index": self._psychosocial_index,
            "n_nodes": len(result.nodes),
            "atmospheric_stress": atm_stress,
        }

        if combined_score > 0.7:
            reasoning = f"Topological stress elevated: b={result.power_law_b:.3f}, PSI={self._psychosocial_index:.2f}"
            if atm_stress > 0.3:
                reasoning += f", atmospheric anomaly ({atm_stress:.2f})"
            return self.emit_signal(
                SignalType.ALERT, combined_score,
                data=signal_data,
                reasoning=reasoning,
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data=signal_data,
            reasoning="Topology within normal bounds",
        )

    def health_check(self) -> bool:
        return self._node_data is not None and len(self._node_data) >= 3
