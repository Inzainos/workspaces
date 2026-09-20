"""
Layer Runner — orchestrates fetch → ingest → analyze → consensus.
Agents: Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Jupiter, Omega, Loki, Padre.

Hierarchical validation:
  1. All agents fetch and analyze independently
  2. #2 agents report to #1 agents for validation
  3. Padre cross-validates across families (+ Omega dual-ask)
  4. Everything correlates against Schumann (Beta-1)
  5. Loki provides Bayesian probability collapse (Act 3)
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
from sentinel_omega.layers.geodynamic.jupiter.agent import JupiterAgent
from sentinel_omega.layers.geodynamic.omega.agent import OmegaAgent
from sentinel_omega.layers.geodynamic.loki.agent import LokiAgent

from sentinel_omega.infrastructure.pipeline.data_pipeline import GeodynamicPipeline

logger = logging.getLogger(__name__)


class GeodynamicLayerRunner:

    def __init__(self, enable_satellite: bool = True, repo=None):
        self.pipeline = GeodynamicPipeline()
        # Repo para persistir el catálogo sísmico vivo en la operativa que lee
        # el Juez. Lazy: si no se inyecta, se crea contra la DB canónica.
        self._repo = repo
        self.alfa1 = Alfa1Agent()
        self.alfa2 = Alfa2Agent() if enable_satellite else None
        self.beta1 = Beta1Agent()
        self.beta2 = Beta2Agent()
        self.delta = DeltaAgent()
        self.jupiter = JupiterAgent()
        self.omega = OmegaAgent()
        self.loki = LokiAgent()  # Act 3 - Unified Field
        self.padre = GeodynamicPadre()
        self._enable_satellite = enable_satellite
        self.assertivity = AssertivityTracker(radius_degrees=5.0, window_days=30)
        self.scanner = PrecursorScanner()
        self.muro = MuroCincoEventos(min_walls_for_breach=3)
        self.last_risk: Optional[PrecursorRisk] = None
        self.last_detections: List[PrecursorDetection] = []
        self.last_muro: Optional[MuroResult] = None

    def _get_repo(self):
        """Repo lazy contra la DB canónica (per-thread connection)."""
        if self._repo is None:
            from sentinel_omega.infrastructure.database.repository import (
                SentinelRepository,
            )
            self._repo = SentinelRepository()
        return self._repo

    def _bind_locf(self) -> None:
        """Enlaza el repo al pipeline para que el LOCF persista en la DB.

        El patch (data_pipeline_locf_patch) instala bind_repository, pero
        nadie lo llamaba: el pipeline se construye sin `repository`, así que
        `self._repo` quedaba None y _locf_set nunca escribía en
        tbl_locf_cache (el fallo se tragaba en su try/except). Idempotente.
        """
        if getattr(self, "_locf_bound", False):
            return
        bind = getattr(self.pipeline, "bind_repository", None)
        if bind is None:
            return  # patch LOCF no activo
        try:
            bind(self._get_repo())
            self._locf_bound = True
            logger.info("LOCF enlazado al repositorio — persistencia activa")
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("No se pudo enlazar LOCF al repo: %s", exc)

    def _persist_sismos(self, beta1_data: Dict) -> None:
        """Persiste el catálogo sísmico vivo en TBL_HISTORICO_SISMICO (Juez).

        Fail-soft: nunca bloquea el ciclo. INSERT OR IGNORE dedup por event_id.
        """
        eventos = beta1_data.get("seismic_events") if isinstance(beta1_data, dict) else None
        if not eventos:
            return
        try:
            n = self._get_repo().bulk_insert_sismos(eventos)
            logger.info(
                "Sismos → operativa (Juez): +%d nuevos de %d vivos", n, len(eventos)
            )
        except Exception as exc:  # noqa: BLE001 — fail-soft por diseño
            logger.warning("Persistencia sísmica falló (no bloqueante): %s", exc)

    def _persist_clima(self, alfa1_data: Dict) -> None:
        """Persiste la telemetría horaria en tbl_clima_espacial_raw.

        Antes solo la llenaban el backcast y un gapfill manual, así que la
        tabla llevaba parada desde 2026-09-11 aunque el ciclo bajara estos
        datos de NOAA cada vuelta. De ella comen el entrenamiento (features
        bz/viento/kp/protones) y el fallback de delta_enriched.

        INSERT OR IGNORE por timestamp_blk. Fail-soft.
        """
        filas = alfa1_data.get("clima_horas") if isinstance(alfa1_data, dict) else None
        if not filas:
            return
        try:
            repo = self._get_repo()
            antes = repo._execute(
                "SELECT COUNT(*) FROM tbl_clima_espacial_raw"
            ).fetchone()[0]
            repo._executemany(
                "INSERT OR IGNORE INTO tbl_clima_espacial_raw "
                "(timestamp_blk, bz_promedio, bz_derivada, bz_min, bz_max, "
                " viento_solar_avg, viento_solar_max, kp_max, kp_promedio, "
                " proton_flux_10mev) VALUES (?,?,?,?,?,?,?,?,?,?)",
                filas,
            )
            despues = repo._execute(
                "SELECT COUNT(*) FROM tbl_clima_espacial_raw"
            ).fetchone()[0]
            if despues > antes:
                logger.info(
                    "Clima espacial → DB: +%d horas nuevas de %d",
                    despues - antes, len(filas),
                )
        except Exception as exc:  # noqa: BLE001 — fail-soft por diseño
            logger.warning("Persistencia de clima falló (no bloqueante): %s", exc)

    def _compute_precursor_risk(
        self,
        alfa1_data: Dict,
        beta1_data: Dict,
        beta2_data: Dict,
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
        pg = beta2_data.get("pressure_gradient")
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
        logger.info("=== Sentinel Omega Cycle ===")

        self._bind_locf()

        alfa1_data = self.pipeline.fetch_alfa1_data()
        beta1_data = self.pipeline.fetch_beta1_data()
        beta2_data = self.pipeline.fetch_beta2_data()
        delta_data = self.pipeline.fetch_delta_data()

        # El fetch de Beta-1 ya trajo el catálogo USGS: registrarlo en la
        # operativa que lee el Juez (antes se descartaba → Juez ciego).
        self._persist_sismos(beta1_data)
        # Ídem con la telemetría de Alfa-1 → tbl_clima_espacial_raw.
        self._persist_clima(alfa1_data)

        risk = self._compute_precursor_risk(alfa1_data, beta1_data, beta2_data)

        hurricane_data = self._fetch_hurricane_data()
        detections = self.scanner.scan(
            alfa1_data, beta1_data, beta2_data,
            hurricane_data=hurricane_data,
            financial_data=delta_data,
        )
        self.last_detections = detections

        muro_result = self.muro.evaluate(detections)
        self.last_muro = muro_result

        self.alfa1.ingest(alfa1_data)
        self.beta1.ingest(beta1_data)
        self.beta2.ingest(beta2_data)
        self.delta.ingest(delta_data)

        signals: List[AgentSignal] = [
            self.alfa1.analyze(),
            self.beta1.analyze(),
            self.beta2.analyze(),
            self.delta.analyze(),
        ]

        if self._enable_satellite and self.alfa2:
            try:
                alfa2_data = self.pipeline.fetch_alfa2_data()
                self.alfa2.ingest(alfa2_data)
                signals.append(self.alfa2.analyze())
                self._last_alfa2_data = alfa2_data
            except Exception as e:
                logger.warning(f"Satellite layer failed (non-blocking): {e}")
                self._last_alfa2_data = None
        else:
            self._last_alfa2_data = None

        try:
            jupiter_data = self.pipeline.fetch_jupiter_data()
            self.jupiter.ingest(jupiter_data)
            signals.append(self.jupiter.analyze())
        except Exception as e:
            logger.warning(f"Júpiter layer failed (non-blocking): {e}")

        # Omega: telemetría espacial + pregunta a Beta-1
        try:
            beta1_sig = next(
                (s for s in signals if getattr(s, "agent_name", "") == "beta1"),
                None,
            )
            omega_data = dict(alfa1_data or {})
            omega_data.update({
                "schumann_hz": (beta1_data or {}).get("schumann_frequency")
                or (beta1_data or {}).get("schumann_hz"),
                "schumann_mean": (beta1_data or {}).get("schumann_mean"),
                "schumann_std": (beta1_data or {}).get("schumann_std"),
            })
            self.omega.ingest(omega_data)
            self.omega.set_beta_context(beta1_sig)
            signals.append(self.omega.analyze())
        except Exception as e:
            logger.warning(f"Omega layer failed (non-blocking): {e}")

        # Loki (Act 3): Unified Field - Fractal-Bayesian collapse
        try:
            # Extract data needed by Loki
            omni_df = alfa1_data.get("omni_dataframe")
            bz_gsm = 0.0
            solar_wind = 400.0
            if omni_df is not None:
                if "bz_gsm" in omni_df.columns:
                    bz_gsm = float(omni_df["bz_gsm"].iloc[-1]) if len(omni_df) > 0 else 0.0
                if "plasma_speed" in omni_df.columns:
                    solar_wind = float(omni_df["plasma_speed"].iloc[-1]) if len(omni_df) > 0 else 400.0

            schumann_resonance = (beta1_data or {}).get("schumann_mean", 7.83)
            vix = (delta_data or {}).get("vix", 20.0)
            lod_ms = 0.0
            lod_series = beta1_data.get("lod_ms")
            if lod_series is not None and len(lod_series) > 0:
                lod_ms = float(lod_series[-1])

            loki_data = {
                "bz_gsm": bz_gsm,
                "solar_wind": solar_wind,
                "schumann_resonance": schumann_resonance,
                "vix": vix,
                "lod_ms": lod_ms,
            }
            self.loki.ingest(loki_data)
            signals.append(self.loki.analyze())
            logger.info(f"Loki signal: {signals[-1].signal_type.value} (conf={signals[-1].confidence:.2f})")
        except Exception as e:
            logger.warning(f"Loki layer failed (non-blocking): {e}")

        consensus = self.padre.evaluate_consensus(signals)
        consensus.precursor_risk = risk
        consensus.precursor_detections = detections
        # Exponer señales por bot para registrar_prediccion en launcher
        consensus.agent_signals = signals

        logger.info(
            f"Consensus: {consensus.final_signal.value} "
            f"(reached={consensus.consensus_reached}, conf={consensus.confidence:.2f}, "
            f"fantasma={risk.fantasma:.2f}, precursors={len(detections)}, "
            f"muro={muro_result.walls_active}/{muro_result.total_walls})"
        )
        return consensus