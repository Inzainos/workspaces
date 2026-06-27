"""
Sentinel Omega — Master Orchestrator
Coordinates all layers (Geodynamic, Crypto, Bolsa) under SNT framework.
Lottery layer operates independently (SEPARATED).

Architecture: Shadow Node Theory (R(t) = a·t^b)
Consensus: Hierarchical — each layer has its own Padre/Árbitro
Cross-layer: SNT engine provides shared analytical primitives
"""

import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from sentinel_omega.config.sentinel_config import SentinelOmegaConfig
from sentinel_omega.core.shared.agent_base import AgentSignal, ConsensusResult, SignalType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SENTINEL-OMEGA] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class SystemStatus:
    layer_statuses: Dict[str, bool] = field(default_factory=dict)
    last_consensus: Dict[str, Optional[ConsensusResult]] = field(default_factory=dict)
    uptime_s: float = 0.0
    total_signals: int = 0


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

    def run_cycle(self) -> Dict[str, ConsensusResult]:
        results = {}
        for name, layer in self._layers.items():
            try:
                if hasattr(layer, 'run'):
                    consensus = layer.run()
                    results[name] = consensus
                    self._status.last_consensus[name] = consensus
                    self._status.total_signals += 1
            except Exception as e:
                logger.error(f"Layer '{name}' cycle failed: {e}")
                self._status.layer_statuses[name] = False

        self._cross_layer_analysis(results)
        return results

    def _cross_layer_analysis(self, results: Dict[str, ConsensusResult]) -> None:
        geo = results.get("geodynamic")
        crypto = results.get("crypto")
        bolsa = results.get("bolsa")

        if geo and geo.consensus_reached and geo.final_signal == SignalType.ALERT:
            logger.warning("GEODYNAMIC ALERT — check crypto/bolsa for correlated anomalies")

            if crypto and crypto.final_signal == SignalType.BEARISH:
                logger.warning("CROSS-LAYER: Geodynamic alert + crypto bearish — potential systemic event")
            if bolsa and bolsa.final_signal == SignalType.BEARISH:
                logger.warning("CROSS-LAYER: Geodynamic alert + bolsa bearish — elevated risk")

    def get_status(self) -> SystemStatus:
        self._status.uptime_s = time.time() - self._start_time
        return self._status

    def health_check(self) -> Dict[str, bool]:
        return dict(self._status.layer_statuses)
