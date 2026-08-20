"""
Sentinel Omega — Master Orchestrator
Precursor detection platform for natural events.

Architecture:
  Agents (Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Omega, Padre) in a single system.
  Everything correlates against Schumann resonance (Beta-1) — the heartbeat of the Earth.
  Hierarchical validation: #2 → #1 → Padre → cross-family check + Omega dual-ask.

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
    dispatch_cycle_alerts,
    send_alert_gated,
    format_consensus_alert,
    format_omega_dual_ask,
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
        logger.info(f"Architecture: multi-agent — hierarchical Schumann-correlated consensus")

    @classmethod
    def create_with_live_pipelines(cls, config: SentinelOmegaConfig) -> "SentinelOrchestrator":
        """Factory: creates orchestrator with real API-backed layer runner."""
        from sentinel_omega.infrastructure.pipeline.layer_runners import (
            GeodynamicLayerRunner,
        )

        orch = cls(config)
        orch._runner = GeodynamicLayerRunner()
        orch._status.is_online = True
        logger.info("Runner registered: GeodynamicLayerRunner")
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

        from sentinel_omega.infrastructure.api.telegram import (
            send_alert_gated,
            dispatch_cycle_alerts,
            format_precursor_alert,
        )
        from sentinel_omega.core.precursor.risk_calculator import format_risk_report
        from sentinel_omega.core.precursor.muro_cinco_eventos import format_muro_report

        risk = geo.precursor_risk
        if risk:
            self._status.last_precursor_risk = risk

        detections = getattr(geo, "precursor_detections", None) or []
        if detections:
            self._status.active_precursors = [
                getattr(d.tipo, "value", str(d.tipo)) for d in detections
            ]
            for detection in detections:
                if getattr(detection, "confidence", 0) >= 0.7:
                    details = ", ".join(
                        f"{k}={v}" for k, v in (detection.values or {}).items()
                    )
                    alert_msg = format_precursor_alert(
                        precursor_type=getattr(detection.tipo, "value", str(detection.tipo)),
                        display_name=detection.display_name,
                        value=detection.confidence,
                        details=details,
                        lat=getattr(detection, "lat", None),
                        lon=getattr(detection, "lon", None),
                        lugar=getattr(detection, "station", None),
                    )
                    if send_alert_gated(
                        alert_msg,
                        f"PREC_{getattr(detection.tipo, 'value', 'X')}",
                    ):
                        self._status.alerts_dispatched += 1

        muro_msg = None
        if self._runner and getattr(self._runner, "last_muro", None):
            muro = self._runner.last_muro
            self._status.last_muro = muro
            if getattr(muro, "muro_breach", False):
                muro_msg = format_muro_report(muro)

        elevated_msg = None
        if risk and getattr(risk, "is_elevated", False):
            elevated_msg = format_risk_report(risk)
            if geo.consensus_reached:
                elevated_msg += (
                    f"\n\n<b>Consensus: REACHED</b> "
                    f"(confidence={geo.confidence:.0%})"
                )

        comps = getattr(risk, "components", None) or {} if risk else {}
        fantasma = float(getattr(risk, "fantasma", 0) or 0) if risk else None
        bz = comps.get("bz_nT")
        wind = comps.get("wind_kms")
        sch = comps.get("schumann_hz") or comps.get("schumann_wpc")

        n = dispatch_cycle_alerts(
            fantasma=fantasma if fantasma is not None else None,
            bz=float(bz) if bz is not None else None,
            wind=float(wind) if wind is not None else None,
            schumann=float(sch) if sch is not None else None,
            consensus_signal=geo.final_signal.value if geo.final_signal else None,
            consensus_conf=float(geo.confidence or 0),
            agents_n=len(geo.agent_signals or []),
            metadata=getattr(geo, "metadata", None) or {},
            muro_msg=muro_msg,
            elevated_risk_msg=elevated_msg,
        )
        self._status.alerts_dispatched += n

    def get_status(self) -> SystemStatus:
        self._status.uptime_s = time.time() - self._start_time
        return self._status

    def health_check(self) -> Dict[str, bool]:
        return {"geodynamic": self._status.is_online}
