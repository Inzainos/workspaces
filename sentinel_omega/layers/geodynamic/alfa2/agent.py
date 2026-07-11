"""
Alfa-2 Agent — Satellite Multispectral Thermal Anomaly Detection
Source: ESA Sentinel-2 L2A via EODAG (Copernicus Data Space)
Variables: Temporal coverage density, cloud-free revisit rate, thermal pass count
Method: Temporal coverage analysis over seismic zones
Role: Real-time cortical stress indicator via satellite observation frequency

Limitación proxy-of-proxy (v2.5.1, documentada y aplicada):
  Lo que este agente mide hoy es DENSIDAD DE OBSERVACIÓN (cuántas pasadas,
  qué tan despejadas, cada cuántos días) — un proxy de "qué tan bien vemos
  la zona", no de temperatura superficial. El conteo `thermal_anomaly_count`
  llega de fuera y el pipeline actual lo entrega en 0: NO existe todavía una
  medición térmica real (lst_c, Land Surface Temperature) detrás.

  Regla de honestidad: sin `lst_c` medida en la ingesta, un conteo de
  anomalías térmicas NO alcanza para ALERT — se degrada a WATCH y el
  reasoning lo dice. ALERT térmica requiere lecturas lst_c reales que
  respalden el conteo.
"""

import numpy as np
from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Alfa2Agent(BaseAgent):

    MIN_PASSES_FOR_SIGNAL = 3
    HIGH_COVERAGE_THRESHOLD = 8
    LOW_CLOUD_THRESHOLD = 20.0

    def __init__(self):
        super().__init__(name="alfa2", layer="geodynamic")
        self._zone_coverages: Dict[str, Dict[str, Any]] = {}
        self._thermal_anomaly_count: int = 0
        self._lst_c: Optional[List[float]] = None   # LST medida (°C); None = sin térmico real

    def ingest(self, data: Dict[str, Any]) -> None:
        self._zone_coverages = data.get("zone_coverages", {})
        self._thermal_anomaly_count = data.get("thermal_anomaly_count", 0)
        self._lst_c = data.get("lst_c")
        self.logger.info(
            f"Ingested satellite data for {len(self._zone_coverages)} zones"
        )

    def analyze(self) -> AgentSignal:
        if not self._zone_coverages:
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                reasoning="No satellite coverage data available",
            )

        zone_scores = {}
        for zone, cov in self._zone_coverages.items():
            s2_count = cov.get("s2_count", 0)
            s1_count = cov.get("s1_count", 0)
            total = cov.get("total_passes", s2_count + s1_count)
            mean_revisit = cov.get("mean_revisit_days", 0.0)
            cloud_covers = cov.get("s2_cloud_covers", [])

            clear_passes = sum(1 for cc in cloud_covers if cc < self.LOW_CLOUD_THRESHOLD)

            coverage_score = min(total / self.HIGH_COVERAGE_THRESHOLD, 1.0)
            clarity_score = clear_passes / max(len(cloud_covers), 1)
            revisit_score = max(0, 1.0 - mean_revisit / 12.0) if mean_revisit > 0 else 0.0

            zone_scores[zone] = {
                "coverage": coverage_score,
                "clarity": clarity_score,
                "revisit": revisit_score,
                "composite": (coverage_score * 0.4 + clarity_score * 0.3 + revisit_score * 0.3),
                "total_passes": total,
                "clear_passes": clear_passes,
            }

        avg_composite = np.mean([s["composite"] for s in zone_scores.values()])

        if self._thermal_anomaly_count > 2 and avg_composite > 0.5:
            tiene_lst = bool(self._lst_c)
            signal_data = {
                "zone_scores": zone_scores,
                "thermal_anomalies": self._thermal_anomaly_count,
                "avg_composite": float(avg_composite),
                "lst_medida": tiene_lst,
            }
            if tiene_lst:
                return self.emit_signal(
                    SignalType.ALERT, min(0.6 + self._thermal_anomaly_count * 0.05, 0.9),
                    data=signal_data,
                    reasoning=(
                        f"{self._thermal_anomaly_count} thermal anomalies backed by "
                        f"measured LST, good satellite coverage ({avg_composite:.2f})"
                    ),
                )
            # Sin lst_c medida el conteo es proxy-of-proxy: se degrada a WATCH
            return self.emit_signal(
                SignalType.WATCH, 0.5,
                data=signal_data,
                reasoning=(
                    f"{self._thermal_anomaly_count} thermal anomalies reported but "
                    f"NO measured LST backing them (proxy-of-proxy) — degraded to WATCH"
                ),
            )
        elif avg_composite > 0.6:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.4,
                data={"zone_scores": zone_scores, "avg_composite": float(avg_composite)},
                reasoning=f"Good satellite coverage ({avg_composite:.2f}), no anomalies detected",
            )
        else:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.2,
                data={"avg_composite": float(avg_composite)},
                reasoning=f"Insufficient satellite coverage ({avg_composite:.2f})",
            )

    def health_check(self) -> bool:
        return len(self._zone_coverages) > 0
