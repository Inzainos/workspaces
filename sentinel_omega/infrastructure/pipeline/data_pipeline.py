"""
Data Pipeline — fetches from real APIs and formats for agent ingest().
Single pipeline: all 6 agents are part of one geodynamic system.

Agent data mapping:
  - Alfa-1: NOAA OMNI (Bz, solar wind) — 30yr
  - Alfa-2: ESA Sentinel-2 satellite — 16yr
  - Beta-1: Kp, seismic, Schumann, LOD, lunar — 30yr
  - Beta-2: Atmospheric chemistry (pressure, SO2, air quality) — 16yr
  - Delta: Financial cross-correlation (crypto, bolsa, Fear & Greed, VIX) — 10yr
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from sentinel_omega.infrastructure.api.noaa import (
    fetch_kp_index,
    fetch_goes_xray,
    fetch_solar_wind,
    fetch_mag_field,
)
from sentinel_omega.infrastructure.api.usgs import fetch_earthquakes
from sentinel_omega.infrastructure.api.schumann import fetch_schumann_resonance
from sentinel_omega.infrastructure.api.geophysical import (
    fetch_lod_series,
    compute_lunar_phase_series,
)
from sentinel_omega.infrastructure.api.esa_sentinel import (
    search_sentinel2,
    search_sentinel1_sar,
    compute_temporal_coverage,
    get_seismic_zone_bboxes,
)
from sentinel_omega.infrastructure.api.openweathermap import (
    fetch_monitoring_network,
    fetch_air_quality,
    compute_pressure_gradient,
    MONITORING_STATIONS,
)
from sentinel_omega.infrastructure.api.crypto import (
    fetch_coingecko_dominance,
    fetch_binance_klines,
    fetch_fear_greed_index,
    fetch_coingecko_market_chart,
)
from sentinel_omega.infrastructure.api.bolsa import (
    fetch_yahoo_quote,
    fetch_vix,
    fetch_sector_etfs,
    fetch_yield_spread,
)

logger = logging.getLogger(__name__)


class GeodynamicPipeline:
    """Single pipeline for all 6 agents in the Sentinel Omega system."""

    def fetch_alfa1_data(self) -> Dict[str, Any]:
        """Build OMNI-like DataFrame for Alfa-1 from NOAA real-time data."""
        mag_df = fetch_mag_field()
        wind_df = fetch_solar_wind()

        if mag_df is None and wind_df is None:
            logger.warning("No NOAA data available for Alfa-1")
            return {}

        frames = []
        if mag_df is not None:
            mag_df = mag_df.set_index("time_tag")
            frames.append(mag_df)
        if wind_df is not None:
            wind_df = wind_df.rename(columns={
                "proton_speed": "plasma_speed",
            }).set_index("time_tag")
            frames.append(wind_df)

        if not frames:
            return {}

        omni_df = pd.concat(frames, axis=1)
        omni_df = omni_df.sort_index().ffill().dropna(how="all")
        logger.info(f"Alfa-1 pipeline: {len(omni_df)} records, {list(omni_df.columns)}")
        return {"omni_dataframe": omni_df.reset_index(names=["time_tag"])}

    def fetch_beta1_data(self) -> Dict[str, Any]:
        """Fetch Kp series, seismic, Schumann, LOD, lunar for Beta-1."""
        result: Dict[str, Any] = {}

        kp_df = fetch_kp_index()
        if kp_df is not None and len(kp_df) > 0:
            result["kp_series"] = kp_df["kp_index"].values.astype(float)

        eq_df = fetch_earthquakes(min_magnitude=2.5, days=30)
        if eq_df is not None and "magnitude" in eq_df.columns:
            result["seismic_magnitudes"] = eq_df["magnitude"].values.astype(float)

        try:
            schumann_hz, schumann_pct = fetch_schumann_resonance(cleanup=True)
            result["schumann_frequency"] = schumann_hz
            result["schumann_activity"] = schumann_pct
        except Exception as e:
            logger.warning(f"Schumann fetch failed: {e}")

        lod_df = fetch_lod_series(days=90)
        if lod_df is not None and len(lod_df) > 0:
            result["lod_ms"] = lod_df["lod_ms"].values.astype(float)

        try:
            result["lunar_phase"] = compute_lunar_phase_series(days=30)
        except Exception as e:
            logger.warning(f"Lunar phase computation failed: {e}")

        if not result:
            logger.warning("No Kp/seismic data for Beta-1")
        return result

    def fetch_alfa2_data(
        self,
        zones: Optional[List[str]] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Fetch Sentinel-2 multispectral coverage for seismic zone monitoring."""
        all_zones = get_seismic_zone_bboxes()
        target_zones = zones or ["guerrero_gap", "oaxaca_costa", "chiapas"]

        zone_coverages = {}
        for zone in target_zones:
            bbox = all_zones.get(zone)
            if bbox is None:
                continue
            try:
                cov = compute_temporal_coverage(bbox, days=days)
                zone_coverages[zone] = cov
            except Exception as e:
                logger.warning(f"Satellite coverage failed for {zone}: {e}")

        if not zone_coverages:
            logger.warning("No satellite coverage data for Alfa-2")
            return {}

        logger.info(f"Alfa-2 pipeline: {len(zone_coverages)} zones analyzed")
        return {
            "zone_coverages": zone_coverages,
            "thermal_anomaly_count": 0,
        }

    def fetch_beta2_data(self) -> Dict[str, Any]:
        """Fetch atmospheric chemistry data for Beta-2 (pressure, SO2, air quality)."""
        result: Dict[str, Any] = {}

        try:
            readings = fetch_monitoring_network(
                ["tlaxcala", "oaxaca", "guerrero", "colima"]
            )
            if readings:
                gradient = compute_pressure_gradient(readings)
                result["pressure_gradient"] = gradient
                result["atmospheric_readings"] = [
                    {
                        "station": r.station,
                        "lat": r.lat,
                        "lon": r.lon,
                        "pressure_hpa": r.pressure_hpa,
                        "temp_c": r.temp_c,
                        "humidity_pct": r.humidity_pct,
                        "visibility_m": r.visibility_m,
                        "weather_id": r.weather_id,
                    }
                    for r in readings
                ]
        except Exception as e:
            logger.warning(f"Atmospheric data fetch failed: {e}")

        try:
            tlaxcala = MONITORING_STATIONS["tlaxcala"]
            aq = fetch_air_quality(tlaxcala["lat"], tlaxcala["lon"])
            if aq:
                result["air_quality"] = aq
        except Exception as e:
            logger.warning(f"Air quality fetch failed: {e}")

        if not result:
            logger.warning("No atmospheric data for Beta-2")
        return result

    def fetch_delta_data(self) -> Dict[str, Any]:
        """
        Fetch financial + sentiment data for Delta.
        Crypto (Fear & Greed, BTC dominance), Bolsa (VIX, sectors, yield spread).
        """
        result: Dict[str, Any] = {}

        fg = fetch_fear_greed_index()
        result["fear_greed"] = fg["value"] if fg else 50.0

        dominance = fetch_coingecko_dominance()
        if dominance:
            result["btc_dominance"] = dominance.get("btc", 50.0) / 100.0

        crypto_ratios: Dict[str, float] = {}
        for symbol in ("ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"):
            df = fetch_binance_klines(symbol, limit=30)
            btc_df = fetch_binance_klines("BTCUSDT", limit=30)
            if df is not None and btc_df is not None:
                if "close" in df.columns and "close" in btc_df.columns:
                    ratio = float(df["close"].iloc[-1]) / max(float(btc_df["close"].iloc[-1]), 1)
                    crypto_ratios[symbol.replace("USDT", "")] = ratio
        if crypto_ratios:
            result["crypto_ratios"] = crypto_ratios

        vix_df = fetch_vix()
        if vix_df is not None and "close" in vix_df.columns:
            result["vix"] = float(vix_df["close"].iloc[-1])

        spread = fetch_yield_spread()
        if spread is not None:
            result["yield_spread"] = spread

        sector_dfs = fetch_sector_etfs(days=30)
        sector_caps: Dict[str, float] = {}
        for etf, df in sector_dfs.items():
            if "close" in df.columns and "volume" in df.columns:
                last_close = float(df["close"].iloc[-1])
                avg_vol = float(df["volume"].mean())
                sector_caps[etf] = last_close * avg_vol
        if sector_caps:
            result["sector_market_caps"] = sector_caps

        logger.info(
            f"Delta pipeline: FGI={result.get('fear_greed', '?')}, "
            f"VIX={result.get('vix', '?')}, "
            f"{len(crypto_ratios)} crypto ratios, "
            f"{len(sector_caps)} sectors"
        )
        return result
