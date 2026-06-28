"""
Layer Runners — orchestrate fetch → ingest → analyze → consensus per domain.
Each runner owns its agents and padre, calls the pipeline, and returns ConsensusResult.
"""

import logging
from typing import List

from sentinel_omega.core.shared.agent_base import AgentSignal, ConsensusResult, SignalType

from sentinel_omega.layers.geodynamic.alfa1.agent import Alfa1Agent
from sentinel_omega.layers.geodynamic.alfa2.agent import Alfa2Agent
from sentinel_omega.layers.geodynamic.beta1.agent import Beta1Agent
from sentinel_omega.layers.geodynamic.beta2.agent import Beta2Agent
from sentinel_omega.layers.geodynamic.delta.agent import DeltaAgent
from sentinel_omega.layers.geodynamic.padre.agent import GeodynamicPadre

from sentinel_omega.layers.crypto.alfa_crypto.agent import AlfaCryptoAgent
from sentinel_omega.layers.crypto.beta_crypto.agent import BetaCryptoAgent
from sentinel_omega.layers.crypto.delta_crypto.agent import DeltaCryptoAgent
from sentinel_omega.layers.crypto.padre_crypto.agent import CryptoPadre

from sentinel_omega.layers.bolsa.alfa_bolsa.agent import AlfaBolsaAgent
from sentinel_omega.layers.bolsa.beta_bolsa.agent import BetaBolsaAgent
from sentinel_omega.layers.bolsa.delta_bolsa.agent import DeltaBolsaAgent
from sentinel_omega.layers.bolsa.padre_bolsa.agent import BolsaPadre

from sentinel_omega.infrastructure.pipeline.data_pipeline import (
    GeodynamicPipeline,
    CryptoPipeline,
    BolsaPipeline,
)

logger = logging.getLogger(__name__)


class GeodynamicLayerRunner:

    def __init__(self, enable_satellite: bool = True):
        self.pipeline = GeodynamicPipeline()
        self.alfa1 = Alfa1Agent()
        self.alfa2 = Alfa2Agent() if enable_satellite else None
        self.beta1 = Beta1Agent()
        self.beta2 = Beta2Agent() if enable_satellite else None
        self.delta = DeltaAgent()
        self.padre = GeodynamicPadre()
        self._enable_satellite = enable_satellite

    def run(self) -> ConsensusResult:
        logger.info("=== Geodynamic Layer Cycle ===")

        alfa1_data = self.pipeline.fetch_alfa1_data()
        beta1_data = self.pipeline.fetch_beta1_data()
        delta_data = self.pipeline.fetch_delta_data()

        self.alfa1.ingest(alfa1_data)
        self.beta1.ingest(beta1_data)
        self.delta.ingest(delta_data)

        signals: List[AgentSignal] = [
            self.alfa1.analyze(),
            self.beta1.analyze(),
            self.delta.analyze(),
        ]

        if self._enable_satellite and self.alfa2 and self.beta2:
            try:
                alfa2_data = self.pipeline.fetch_alfa2_data()
                beta2_data = self.pipeline.fetch_beta2_data()
                self.alfa2.ingest(alfa2_data)
                self.beta2.ingest(beta2_data)
                signals.append(self.alfa2.analyze())
                signals.append(self.beta2.analyze())
            except Exception as e:
                logger.warning(f"Satellite layer failed (non-blocking): {e}")

        consensus = self.padre.evaluate_consensus(signals)
        logger.info(
            f"Geodynamic consensus: {consensus.final_signal.value} "
            f"(reached={consensus.consensus_reached}, conf={consensus.confidence:.2f})"
        )
        return consensus


class CryptoLayerRunner:

    def __init__(self, days: int = 90):
        self.pipeline = CryptoPipeline()
        self.alfa = AlfaCryptoAgent()
        self.beta = BetaCryptoAgent()
        self.delta = DeltaCryptoAgent()
        self.padre = CryptoPadre()
        self._days = days

    def run(self) -> ConsensusResult:
        logger.info("=== Crypto Layer Cycle ===")

        alfa_data = self.pipeline.fetch_alfa_data(days=self._days)
        beta_data = self.pipeline.fetch_beta_data()
        delta_data = self.pipeline.fetch_delta_data()

        self.alfa.ingest(alfa_data)
        self.beta.ingest(beta_data)
        self.delta.ingest(delta_data)

        signals: List[AgentSignal] = [
            self.alfa.analyze(),
            self.beta.analyze(),
            self.delta.analyze(),
        ]

        consensus = self.padre.evaluate_consensus(signals)
        logger.info(
            f"Crypto consensus: {consensus.final_signal.value} "
            f"(reached={consensus.consensus_reached}, conf={consensus.confidence:.2f})"
        )
        return consensus


class BolsaLayerRunner:

    def __init__(self, symbol: str = "AAPL", index_symbol: str = "SPY"):
        self.pipeline = BolsaPipeline()
        self.alfa = AlfaBolsaAgent()
        self.beta = BetaBolsaAgent()
        self.delta = DeltaBolsaAgent()
        self.padre = BolsaPadre()
        self._symbol = symbol
        self._index_symbol = index_symbol

    def run(self) -> ConsensusResult:
        logger.info(f"=== Bolsa Layer Cycle ({self._symbol}) ===")

        alfa_data = self.pipeline.fetch_alfa_data(
            symbol=self._symbol,
            index_symbol=self._index_symbol,
        )
        beta_data = self.pipeline.fetch_beta_data()
        delta_data = self.pipeline.fetch_delta_data()

        self.alfa.ingest(alfa_data)
        self.beta.ingest(beta_data)
        self.delta.ingest(delta_data)

        signals: List[AgentSignal] = [
            self.alfa.analyze(),
            self.beta.analyze(),
            self.delta.analyze(),
        ]

        consensus = self.padre.evaluate_consensus(signals)
        logger.info(
            f"Bolsa consensus: {consensus.final_signal.value} "
            f"(reached={consensus.consensus_reached}, conf={consensus.confidence:.2f})"
        )
        return consensus
