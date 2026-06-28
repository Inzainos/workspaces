"""
Layer Runners — orchestrate fetch → ingest → analyze → consensus per domain.
Each runner owns its agents and padre, calls the pipeline, and returns ConsensusResult.

Geodynamic runner also computes TITAN V32 precursor risk (fantasma) from
the agent signals and atmospheric data collected during each cycle.
"""

import logging
from typing import Dict, List, Optional

from sentinel_omega.core.shared.agent_base import AgentSignal, ConsensusResult, SignalType
from sentinel_omega.core.precursor.risk_calculator import (
    PrecursorRisk,
    compute_fantasma,
    format_risk_report,
)
from sentinel_omega.core.precursor.assertivity import AssertivityTracker
from sentinel_omega.core.precursor.scanner import PrecursorScanner, PrecursorDetection
from sentinel_omega.core.precursor.muro_cinco_eventos import MuroCincoEventos, MuroResult

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
        self.assertivity = AssertivityTracker(radius_degrees=5.0, window_days=30)
        self.scanner = PrecursorScanner()
        self.muro = MuroCincoEventos(min_walls_for_breach=3)
        self.last_risk: Optional[PrecursorRisk] = None
        self.last_detections: List[PrecursorDetection] = []
        self.last_muro: Optional[MuroResult] = None

    def _compute_precursor_risk(
        self,
        alfa1_data: Dict,
        beta1_data: Dict,
        delta_data: Dict,
    ) -> PrecursorRisk:
        """Compute TITAN V32 fantasma from raw pipeline data."""
        import numpy as np

        bz = 0.0
        viento = 0.0
        omni_df = alfa1_data.get("omni_dataframe")
        if omni_df is not None:
            if "bz_gsm" in omni_df.columns:
                bz = float(np.nanmean(omni_df["bz_gsm"]))
            if "plasma_speed" in omni_df.columns:
                viento = float(np.nanmean(omni_df["plasma_speed"]))

        sch_wpc = beta1_data.get("schumann_activity", 0.0) / 100.0

        kp_series = beta1_data.get("kp_series")
        kp = float(np.nanmean(kp_series)) if kp_series is not None and len(kp_series) > 0 else 0.0

        lod_series = beta1_data.get("lod_ms")
        lod_ms = float(np.nanmean(lod_series)) if lod_series is not None and len(lod_series) > 0 else 0.0

        pressure_hpa = 1013.0
        pg = delta_data.get("pressure_gradient")
        if pg:
            pressure_hpa = pg.get("mean_pressure", 1013.0)

        risk = compute_fantasma(
            bz=bz, viento=viento, sch_wpc=sch_wpc,
            pressure_hpa=pressure_hpa, kp=kp, lod_ms=lod_ms,
        )
        self.last_risk = risk
        logger.info(f"Precursor risk: fantasma={risk.fantasma:.2f} level={risk.risk_level}")
        return risk

    def _fetch_hurricane_data(self) -> Dict:
        try:
            from sentinel_omega.infrastructure.api.noaa_hazards import (
                fetch_active_hurricanes,
                compute_hurricane_proximity,
            )
            cyclones = fetch_active_hurricanes()
            if not cyclones:
                return {}
            nearby = compute_hurricane_proximity(cyclones, 19.0, -99.0, max_distance_deg=15.0)
            return {
                "active_cyclones": [
                    {
                        "name": c.name, "category": c.category,
                        "lat": c.lat, "lon": c.lon,
                        "max_wind_kt": c.max_wind_kt,
                        "pressure_mb": c.pressure_mb,
                        "distance_deg": n["distance_deg"],
                    }
                    for c, n in zip(cyclones, nearby)
                ] if nearby else [],
            }
        except Exception as e:
            logger.warning(f"Hurricane data fetch failed (non-blocking): {e}")
            return {}

    def run(self, financial_data: Optional[Dict] = None) -> ConsensusResult:
        logger.info("=== Geodynamic Layer Cycle ===")

        alfa1_data = self.pipeline.fetch_alfa1_data()
        beta1_data = self.pipeline.fetch_beta1_data()
        delta_data = self.pipeline.fetch_delta_data()

        risk = self._compute_precursor_risk(alfa1_data, beta1_data, delta_data)

        hurricane_data = self._fetch_hurricane_data()
        detections = self.scanner.scan(
            alfa1_data, beta1_data, delta_data,
            hurricane_data=hurricane_data,
            financial_data=financial_data,
        )
        self.last_detections = detections

        muro_result = self.muro.evaluate(detections)
        self.last_muro = muro_result

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
        consensus.precursor_risk = risk
        consensus.precursor_detections = detections

        logger.info(
            f"Geodynamic consensus: {consensus.final_signal.value} "
            f"(reached={consensus.consensus_reached}, conf={consensus.confidence:.2f}, "
            f"fantasma={risk.fantasma:.2f}, precursors={len(detections)}, "
            f"muro={muro_result.walls_active}/{muro_result.total_walls})"
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
