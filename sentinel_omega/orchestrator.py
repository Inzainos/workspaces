"""
Sentinel Omega — Master Orchestrator
Precursor detection platform for natural events.

Architecture:
  6 agents (Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Padre) in a single system.
  Everything correlates against Schumann resonance (Beta-1) — the heartbeat of the Earth.
  Hierarchical validation: #2 → #1 → Padre → cross-family check.

Pipeline: Real API connectors → Data Pipeline → Agent ingest() → Consensus → Risk
Alerts: Telegram dispatch when precursor risk is elevated
"""

import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from sentinel_omega.config.sentinel_config import SentinelOmegaConfig
from sentinel_omega.core.shared.agent_base import AgentSignal, ConsensusResult, SignalType
from sentinel_omega.core.precursor.risk_calculator import PrecursorRisk, format_risk_report
from sentinel_omega.infrastructure.api.telegram import (
    send_alert,
    format_consensus_alert,
    format_precursor_alert,
)
from sentinel_omega.core.precursor.muro_cinco_eventos import format_muro_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SENTINEL-OMEGA] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    is_online: bool = False
    last_consensus: Optional[ConsensusResult] = None
    last_precursor_risk: Optional[PrecursorRisk] = None
    last_muro: Optional[Any] = None
    active_precursors: List[str] = field(default_factory=list)
    uptime_s: float = 0.0
    total_signals: int = 0
    cycle_count: int = 0
    alerts_dispatched: int = 0


class SentinelOrchestrator:

    def __init__(self, config: SentinelOmegaConfig):
        self.config = config
        self._start_time = time.time()
        self._status = SystemStatus()
        self._runner = None

        logger.info(f"=== {config.project_name} v{config.version} ===")
        logger.info(f"Author: {config.author}")
        logger.info(f"Architecture: 6 agents — hierarchical Schumann-correlated consensus")

    @classmethod
    def create_with_live_pipelines(cls, config: SentinelOmegaConfig) -> "SentinelOrchestrator":
        """Factory: creates orchestrator with real API-backed layer runner."""
        from sentinel_omega.infrastructure.pipeline.layer_runners import (
            GeodynamicLayerRunner,
        )

        orch = cls(config)
        orch._runner = GeodynamicLayerRunner()
        orch._status.is_online = True
        logger.info("Runner registered: GeodynamicLayerRunner (6 agents)")
        return orch

    def run_cycle(self) -> Dict[str, ConsensusResult]:
        self._status.cycle_count += 1
        logger.info(f"--- Cycle #{self._status.cycle_count} ---")

        results = {}

        if self._runner:
            try:
                consensus = self._runner.run()
                results["geodynamic"] = consensus
                self._status.last_consensus = consensus
                self._status.total_signals += 1
            except Exception as e:
                logger.error(f"Cycle failed: {e}", exc_info=True)

        self._analyze_results(results)
        return results

    def _analyze_results(self, results: Dict[str, ConsensusResult]) -> None:
        geo = results.get("geodynamic")
        if not geo:
            return

        if geo.precursor_risk:
            risk: PrecursorRisk = geo.precursor_risk
            self._status.last_precursor_risk = risk

            if risk.is_elevated:
                logger.warning(
                    f"PRECURSOR ALERT — fantasma={risk.fantasma:.2f} "
                    f"level={risk.risk_level}"
                )
                alert_msg = format_risk_report(risk)
                if geo.consensus_reached:
                    alert_msg += (
                        f"\n\n<b>Consensus: REACHED</b> "
                        f"(confidence={geo.confidence:.0%})"
                    )
                send_alert(alert_msg)
                self._status.alerts_dispatched += 1

        if getattr(geo, "precursor_detections", None):
            detections = geo.precursor_detections
            self._status.active_precursors = [d.tipo.value for d in detections]
            for detection in detections:
                if detection.confidence >= 0.7:
                    details = ", ".join(
                        f"{k}={v}" for k, v in detection.values.items()
                    )
                    alert_msg = format_precursor_alert(
                        precursor_type=detection.tipo.value,
                        display_name=detection.display_name,
                        value=detection.confidence,
                        details=details,
                        lat=detection.lat,
                        lon=detection.lon,
                        lugar=detection.station,
                    )
                    send_alert(alert_msg)
                    self._status.alerts_dispatched += 1
                    logger.warning(
                        f"PRECURSOR DISPATCH: {detection.tipo.value} "
                        f"@ {detection.station} (conf={detection.confidence:.0%})"
                    )

        if self._runner and hasattr(self._runner, "last_muro") and self._runner.last_muro:
            muro = self._runner.last_muro
            self._status.last_muro = muro
            if muro.muro_breach:
                logger.warning(
                    f"MURO BREACH: {muro.walls_active}/{muro.total_walls} "
                    f"walls — {muro.risk_label}"
                )
                muro_msg = format_muro_report(muro)
                send_alert(muro_msg)
                self._status.alerts_dispatched += 1

        if geo.consensus_reached and geo.final_signal in (SignalType.ALERT, SignalType.WATCH):
            signal_label = geo.final_signal.value.upper()
            logger.warning(f"CONSENSUS {signal_label} — Schumann-correlated cross-family agreement")
            consensus_msg = format_consensus_alert(
                "geodynamic", geo.final_signal.value,
                geo.confidence, len(geo.agent_signals),
            )
            send_alert(consensus_msg)

    def get_status(self) -> SystemStatus:
        self._status.uptime_s = time.time() - self._start_time
        return self._status

    def health_check(self) -> Dict[str, bool]:
        return {"geodynamic": self._status.is_online}
