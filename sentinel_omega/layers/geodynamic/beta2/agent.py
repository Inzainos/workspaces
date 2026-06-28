"""
Beta-2 Agent — SAR Interferometric Deformation Analysis
Source: ESA Sentinel-1 SAR GRD via EODAG (Copernicus Data Space)
Variables: SAR temporal baseline, interferometric pair availability, deformation proxy
Method: Temporal pair density analysis for InSAR-ready monitoring
Role: Cortical deformation detection via SAR coherence proxy
"""

import numpy as np
from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Beta2Agent(BaseAgent):

    IDEAL_BASELINE_DAYS = 12
    MIN_PAIRS_FOR_INSAR = 2

    def __init__(self):
        super().__init__(name="beta2", layer="geodynamic")
        self._sar_coverages: Dict[str, Dict[str, Any]] = {}
        self._deformation_flags: List[str] = []

    def ingest(self, data: Dict[str, Any]) -> None:
        self._sar_coverages = data.get("sar_coverages", {})
        self._deformation_flags = data.get("deformation_flags", [])
        self.logger.info(
            f"Ingested SAR data for {len(self._sar_coverages)} zones, "
            f"{len(self._deformation_flags)} deformation flags"
        )

    def analyze(self) -> AgentSignal:
        if not self._sar_coverages:
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                reasoning="No SAR coverage data available",
            )

        zone_analyses = {}
        for zone, cov in self._sar_coverages.items():
            s1_count = cov.get("s1_count", 0)
            mean_revisit = cov.get("mean_revisit_days", 0.0)
            min_revisit = cov.get("min_revisit_days", 0.0)

            insar_ready = s1_count >= self.MIN_PAIRS_FOR_INSAR
            baseline_quality = max(0, 1.0 - abs(mean_revisit - self.IDEAL_BASELINE_DAYS) / self.IDEAL_BASELINE_DAYS) if mean_revisit > 0 else 0.0

            zone_analyses[zone] = {
                "s1_count": s1_count,
                "insar_ready": insar_ready,
                "baseline_quality": baseline_quality,
                "mean_revisit_days": mean_revisit,
            }

        insar_ready_zones = [z for z, a in zone_analyses.items() if a["insar_ready"]]
        avg_quality = np.mean([a["baseline_quality"] for a in zone_analyses.values()])

        if self._deformation_flags:
            flagged_zones = set(self._deformation_flags) & set(insar_ready_zones)
            if flagged_zones:
                return self.emit_signal(
                    SignalType.ALERT,
                    min(0.65 + len(flagged_zones) * 0.1, 0.95),
                    data={
                        "zone_analyses": zone_analyses,
                        "deformation_flags": self._deformation_flags,
                        "flagged_insar_zones": list(flagged_zones),
                    },
                    reasoning=(
                        f"Deformation flags in {len(flagged_zones)} InSAR-ready zones: "
                        f"{', '.join(flagged_zones)}"
                    ),
                )

        if avg_quality > 0.7 and len(insar_ready_zones) > 2:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.3,
                data={
                    "zone_analyses": zone_analyses,
                    "insar_ready_zones": insar_ready_zones,
                    "avg_quality": float(avg_quality),
                },
                reasoning=(
                    f"Good SAR coverage: {len(insar_ready_zones)} zones InSAR-ready, "
                    f"quality={avg_quality:.2f}"
                ),
            )
        else:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.15,
                data={"avg_quality": float(avg_quality)},
                reasoning=f"Limited SAR coverage (quality={avg_quality:.2f})",
            )

    def health_check(self) -> bool:
        return len(self._sar_coverages) > 0
