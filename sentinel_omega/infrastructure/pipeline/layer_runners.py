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
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

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

    def _persist_jupiter(self, jupiter_data: Dict) -> None:
        """Persiste rayos X GOES e interés de búsqueda para Júpiter.

        Hasta ahora `fetch_jupiter_data()` bajaba `xray_df` y `trends_df` cada
        ciclo, se los pasaba al agente y los tiraba: no había escritor ni
        tabla. Por eso Júpiter no tenía histórico que entrenar --- el mismo
        patrón del catálogo sísmico, no un problema de nombres de features.

        Dos tablas propias, INSERT OR IGNORE por marca temporal. Fail-soft:
        que falle el guardado no debe tumbar el ciclo.
        """
        if not isinstance(jupiter_data, dict):
            return
        try:
            repo = self._get_repo()
            repo._execute(
                "CREATE TABLE IF NOT EXISTS tbl_xray_vivo ("
                " timestamp_blk TEXT PRIMARY KEY,"
                " flux_max REAL, flux_avg REAL, banda TEXT)"
            )
            repo._execute(
                "CREATE TABLE IF NOT EXISTS tbl_trends_vivo ("
                " fecha TEXT PRIMARY KEY, solar_interest REAL)"
            )

            xray = jupiter_data.get("xray_df")
            if xray is not None and len(xray) and "time_tag" in xray.columns:
                x = xray.copy()
                x["blk"] = x["time_tag"].dt.strftime("%Y-%m-%d %H:00")
                agg = x.groupby("blk")["flux"].agg(["max", "mean"]).reset_index()
                banda = str(x["energy"].iloc[0]) if "energy" in x.columns else ""
                repo._executemany(
                    "INSERT OR IGNORE INTO tbl_xray_vivo "
                    "(timestamp_blk, flux_max, flux_avg, banda) VALUES (?,?,?,?)",
                    [(r["blk"], float(r["max"]), float(r["mean"]), banda)
                     for _, r in agg.iterrows()
                     if pd.notna(r["max"]) and pd.notna(r["mean"])],
                )

            trends = jupiter_data.get("trends_df")
            if (trends is not None and len(trends)
                    and {"date", "solar_interest"}.issubset(trends.columns)):
                repo._executemany(
                    "INSERT OR IGNORE INTO tbl_trends_vivo "
                    "(fecha, solar_interest) VALUES (?,?)",
                    [(pd.Timestamp(r["date"]).strftime("%Y-%m-%d"),
                      float(r["solar_interest"]))
                     for _, r in trends.iterrows()
                     if pd.notna(r["solar_interest"])],
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("No se pudo persistir la telemetría de Júpiter: %s", e)

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

    def _aplicar_modelos(self, signals) -> None:
        """Pasa los rasgos del ciclo por el modelo de cada bot.

        El veredicto del modelo se ANOTA siempre en la señal (`onnx_*`), para
        que el Juez pueda comparar después quién acertaba, y sustituye a la
        rama de reglas solo cuando el modelo dice algo --- si devuelve None
        (sin modelo, vector vacío o «nada que reportar»), manda la regla.

        El techo de cada bot se respeta: delta nunca vota ALERT, porque el
        estrés financiero es contexto, no evidencia sísmica.
        """
        from sentinel_omega.core.onnx_mixin import senal_desde_rasgos
        from sentinel_omega.core.shared.agent_base import SignalType

        try:
            rasgos = self._rasgos_del_ciclo()
        except Exception as e:  # noqa: BLE001 — el ciclo sigue con las reglas
            logger.warning("No se pudieron armar los rasgos del ciclo: %s", e)
            return
        if not rasgos:
            return

        SIN_ALERTA = {"delta"}     # su techo es WATCH, por diseño
        for sig in signals:
            bot = str(getattr(sig, "agent_name", "") or "").lower()
            if not bot:
                continue
            try:
                salida = senal_desde_rasgos(
                    bot, rasgos, permitir_alerta=bot not in SIN_ALERTA)
            except Exception as e:  # noqa: BLE001
                logger.debug("%s: modelo no utilizable (%s)", bot, e)
                continue
            datos = getattr(sig, "data", None)
            if not isinstance(datos, dict):
                continue
            if salida is None:
                datos["onnx"] = False
                continue
            tipo, conf, nombre = salida
            datos.update({
                "onnx": True,
                "onnx_senal": nombre,
                "onnx_conf": round(float(conf), 4),
                "regla_senal": sig.signal_type.value,
                "regla_conf": round(float(sig.confidence or 0.0), 4),
            })
            if tipo != sig.signal_type or float(conf) > float(sig.confidence or 0):
                logger.info(
                    "%s: modelo %s (%.2f) sobre regla %s (%.2f)",
                    bot, nombre, conf, sig.signal_type.value, sig.confidence or 0,
                )
            sig.signal_type = tipo
            sig.confidence = float(conf)

    def _rasgos_del_ciclo(self) -> Dict[str, float]:
        """Los rasgos con los nombres canónicos, desde la misma función que
        alimenta al Juez: si el modelo se entrena con esos nombres, tiene que
        inferir con esos nombres."""
        from sentinel_omega.launcher import _build_live_features
        # La conexión es para los rasgos que viven en tablas (rayos X,
        # tendencias). Se abre en SOLO LECTURA: el ciclo no escribe desde aquí.
        conn = None
        try:
            import sqlite3
            from sentinel_omega.config.sentinel_config import load_config
            cfg = load_config()
            ruta = (Path(__file__).resolve().parents[2]
                    / cfg.databases.geodynamic_db)
            conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=5)
        except Exception as e:  # noqa: BLE001 — sin conexión, esos rasgos faltan
            logger.debug("rasgos de tabla no disponibles: %s", e)
        try:
            return _build_live_features(self, conn) or {}
        finally:
            if conn is not None:
                conn.close()

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
            risk=risk,
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
            self._persist_jupiter(jupiter_data)
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

        # ── Cada experto opina con SU modelo ──────────────────────────
        # Hasta el 2026-09-26 solo alfa1 y omega inferían con ONNX: se
        # entrenaban OCHO modelos y seis no se usaban. Y eso deformaba la
        # disciplina --- lo vio el operador: el que no alarma no puede ser
        # castigado por alarmar, así que el Juez hundía al que participa
        # (alfa1: 669 alarmas, peso 0.300) y dejaba en el techo a los que
        # callan (loki, delta, alfa2: 0 alarmas, 0 castigos, peso 1.000, y los
        # 37 eventos del periodo perdidos).
        #
        # La arquitectura es de expertos: cada bot en su dominio, con su modelo
        # y su memoria, y el Padre buscando patrones entre patrones. Un experto
        # que no opina no aporta, y tampoco se puede corregir.
        self._aplicar_modelos(signals)

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