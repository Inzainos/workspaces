"""
Sentinel Omega — Master Orchestrator
Precursor detection platform for natural events.
Coordinates geophysical layers and computes TITAN V32 fantasma risk index.

Architecture: SNT mathematical framework (R(t) = a·t^b)
Consensus: Hierarchical — each layer has its own Padre/Árbitro
Precursor: TITAN V32 fantasma formula on every geodynamic cycle
Alerts: Telegram dispatch when precursor risk is elevated
Pipeline: Real API connectors → Data Pipeline → Agent ingest() → Consensus → Risk
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
    layer_statuses: Dict[str, bool] = field(default_factory=dict)
    last_consensus: Dict[str, Optional[ConsensusResult]] = field(default_factory=dict)
    last_precursor_risk: Optional[PrecursorRisk] = None
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
        self._layers: Dict[str, object] = {}

        logger.info(f"=== {config.project_name} v{config.version} ===")
        logger.info(f"Author: {config.author}")
        logger.info(f"Architecture: Shadow Node Theory")
        logger.info(f"Active layers: {[k for k, v in config.layers.items() if v.enabled]}")

    def register_layer(self, name: str, layer_instance: object) -> None:
        if name not in self.config.layers:
            raise ValueError(f"Unknown layer: {name}")
        if not self.config.layers[name].enabled:
            logger.warning(f"Layer '{name}' is disabled in config")
            return
        self._layers[name] = layer_instance
        self._status.layer_statuses[name] = True
        logger.info(f"Layer registered: {name}")

    @classmethod
    def create_with_live_pipelines(cls, config: SentinelOmegaConfig) -> "SentinelOrchestrator":
        """Factory: creates orchestrator with real API-backed layer runners."""
        from sentinel_omega.infrastructure.pipeline.layer_runners import (
            GeodynamicLayerRunner,
            CryptoLayerRunner,
            BolsaLayerRunner,
        )

        orch = cls(config)

        if config.layers.get("geodynamic") and config.layers["geodynamic"].enabled:
            orch.register_layer("geodynamic", GeodynamicLayerRunner())

        if config.layers.get("crypto") and config.layers["crypto"].enabled:
            orch.register_layer("crypto", CryptoLayerRunner())

        if config.layers.get("bolsa") and config.layers["bolsa"].enabled:
            orch.register_layer("bolsa", BolsaLayerRunner())

        return orch

    def _collect_financial_data(self, results: Dict[str, ConsensusResult]) -> Dict:
        """Extract financial signals from crypto/bolsa consensus for cross-correlation."""
        financial = {}
        crypto = results.get("crypto")
        bolsa = results.get("bolsa")

        if crypto:
            financial["market_signal"] = crypto.final_signal.value
            for sig in crypto.agent_signals:
                if "fear_greed_index" in sig.data:
                    financial["fear_greed"] = sig.data["fear_greed_index"]
                if "btc_change_pct" in sig.data:
                    financial["btc_change_pct"] = sig.data["btc_change_pct"]

        if bolsa:
            for sig in bolsa.agent_signals:
                if "vix" in sig.data:
                    financial["vix"] = sig.data["vix"]

        return financial

    def run_cycle(self) -> Dict[str, ConsensusResult]:
        self._status.cycle_count += 1
        logger.info(f"--- Cycle #{self._status.cycle_count} ---")

        results = {}

        for name in ("crypto", "bolsa"):
            layer = self._layers.get(name)
            if layer and hasattr(layer, 'run'):
                try:
                    consensus = layer.run()
                    results[name] = consensus
                    self._status.last_consensus[name] = consensus
                    self._status.total_signals += 1
                    self._status.layer_statuses[name] = True
                except Exception as e:
                    logger.error(f"Layer '{name}' cycle failed: {e}")
                    self._status.layer_statuses[name] = False

        financial_data = self._collect_financial_data(results)

        geo_layer = self._layers.get("geodynamic")
        if geo_layer and hasattr(geo_layer, 'run'):
            try:
                consensus = geo_layer.run(financial_data=financial_data)
                results["geodynamic"] = consensus
                self._status.last_consensus["geodynamic"] = consensus
                self._status.total_signals += 1
                self._status.layer_statuses["geodynamic"] = True
            except Exception as e:
                logger.error(f"Layer 'geodynamic' cycle failed: {e}")
                self._status.layer_statuses["geodynamic"] = False

        self._cross_layer_analysis(results)
        return results

    def _cross_layer_analysis(self, results: Dict[str, ConsensusResult]) -> None:
        geo = results.get("geodynamic")
        crypto = results.get("crypto")
        bolsa = results.get("bolsa")

        if geo and geo.precursor_risk:
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

        if geo and getattr(geo, "precursor_detections", None):
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

        geo_layer = self._layers.get("geodynamic")
        if geo_layer and hasattr(geo_layer, "last_muro") and geo_layer.last_muro:
            muro = geo_layer.last_muro
            if muro.muro_breach:
                logger.warning(
                    f"MURO BREACH: {muro.walls_active}/{muro.total_walls} "
                    f"walls — {muro.risk_label}"
                )
                muro_msg = format_muro_report(muro)
                send_alert(muro_msg)
                self._status.alerts_dispatched += 1

        if geo and geo.consensus_reached and geo.final_signal == SignalType.ALERT:
            logger.warning("GEODYNAMIC ALERT — check crypto/bolsa for correlated anomalies")
            consensus_msg = format_consensus_alert(
                "geodynamic", geo.final_signal.value,
                geo.confidence, len(geo.agent_signals),
            )
            send_alert(consensus_msg)

            if crypto and crypto.final_signal == SignalType.BEARISH:
                logger.warning("CROSS-LAYER: Geodynamic alert + crypto bearish — potential systemic event")
            if bolsa and bolsa.final_signal == SignalType.BEARISH:
                logger.warning("CROSS-LAYER: Geodynamic alert + bolsa bearish — elevated risk")

    def get_status(self) -> SystemStatus:
        self._status.uptime_s = time.time() - self._start_time
        return self._status

    def health_check(self) -> Dict[str, bool]:
        return dict(self._status.layer_statuses)
