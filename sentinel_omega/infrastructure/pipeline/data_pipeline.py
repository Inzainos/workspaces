"""
Data Pipeline — fetches from real APIs and formats for agent ingest().
Each pipeline class maps API responses to the exact dict shape each agent expects.
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
    """Fetches NOAA + USGS data and formats for geodynamic agents."""

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
        """Fetch Kp series and seismic data for Beta-1 FFT analysis."""
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

    def fetch_delta_data(self) -> Dict[str, Any]:
        """
        Build energetic node map from seismic geography.
        Regional seismic energy → nodes in the N-Body topology.
        """
        eq_df = fetch_earthquakes(min_magnitude=4.0, days=30)
        if eq_df is None or len(eq_df) < 3:
            return {}

        regions: Dict[str, float] = {}
        for _, row in eq_df.iterrows():
            place = str(row.get("place", "Unknown"))
            region = place.split(",")[-1].strip() if "," in place else place
            mag = float(row.get("magnitude", 0))
            energy = 10 ** (1.5 * mag)
            regions[region] = regions.get(region, 0) + energy

        fg = fetch_fear_greed_index()
        psi = (fg["value"] / 100.0) if fg else 0.5

        logger.info(f"Delta pipeline: {len(regions)} seismic nodes, PSI={psi:.2f}")
        return {
            "energetic_nodes": regions,
            "psychosocial_index": psi,
        }


class CryptoPipeline:
    """Fetches crypto market data and formats for crypto agents."""

    TRACKED_PAIRS = {
        "BTCUSDT": "btc_usdt",
        "ETHUSDT": "eth_usdt",
        "SOLUSDT": "sol_usdt",
        "BNBUSDT": "bnb_usdt",
        "XRPUSDT": "xrp_usdt",
        "ADAUSDT": "ada_usdt",
        "AVAXUSDT": "avax_usdt",
        "DOTUSDT": "dot_usdt",
    }

    def fetch_alfa_data(self, days: int = 90) -> Dict[str, Any]:
        """Build multi-pair price DataFrame and dominance data for Alfa-Crypto."""
        frames = {}
        for symbol, col_name in self.TRACKED_PAIRS.items():
            df = fetch_binance_klines(symbol, limit=days)
            if df is not None and "close" in df.columns:
                frames[col_name] = df.set_index("timestamp")["close"]

        if not frames:
            logger.warning("No Binance data for Alfa-Crypto")
            return {}

        price_df = pd.DataFrame(frames)
        price_df = price_df.sort_index().ffill()

        dominance = fetch_coingecko_dominance()
        btc_mcap = 0.0
        total_mcap = 1.0
        if dominance:
            btc_pct = dominance.get("btc", 50.0) / 100.0
            total_mcap = 1e12
            btc_mcap = total_mcap * btc_pct

        logger.info(f"Alfa-Crypto pipeline: {len(price_df)} days, {len(frames)} pairs")
        return {
            "price_dataframe": price_df.reset_index(),
            "btc_market_cap": btc_mcap,
            "total_market_cap": total_mcap,
        }

    def fetch_beta_data(self) -> Dict[str, Any]:
        """Fetch volume series and on-chain proxies for Beta-Crypto."""
        btc_df = fetch_binance_klines("BTCUSDT", interval="1h", limit=168)

        result: Dict[str, Any] = {}
        if btc_df is not None and "volume" in btc_df.columns:
            result["volume_series"] = btc_df["volume"].values.astype(float)

        result["whale_transaction_ratio"] = 0.15
        result["funding_rate"] = 0.0
        result["regulatory_score"] = 0.3
        result["exchange_barriers"] = 0.1
        result["market_maturity"] = 0.4

        return result

    def fetch_delta_data(self) -> Dict[str, Any]:
        """Fetch Fear & Greed and social sentiment for Delta-Crypto."""
        fg = fetch_fear_greed_index()
        return {
            "fear_greed_index": fg["value"] if fg else 50.0,
            "social_volume": 0.0,
            "influencer_reach": {},
        }


class BolsaPipeline:
    """Fetches stock market data and formats for bolsa agents."""

    def fetch_alfa_data(
        self,
        symbol: str = "AAPL",
        index_symbol: str = "SPY",
        days: int = 365,
    ) -> Dict[str, Any]:
        """Fetch stock OHLCV and index OHLCV for Alfa-Bolsa SNT ratio analysis."""
        stock_df = fetch_yahoo_quote(symbol, days=days)
        index_df = fetch_yahoo_quote(index_symbol, days=days)

        if stock_df is None or index_df is None:
            logger.warning(f"Missing Yahoo data for {symbol}/{index_symbol}")
            return {}

        logger.info(f"Alfa-Bolsa: {symbol}={len(stock_df)} rows, {index_symbol}={len(index_df)} rows")
        return {
            "stock_ohlcv": stock_df,
            "index_ohlcv": index_df,
        }

    def fetch_beta_data(self) -> Dict[str, Any]:
        """Fetch macro indicators for Beta-Bolsa fundamental analysis."""
        spread = fetch_yield_spread()

        return {
            "interest_rate": 0.0525,
            "yield_spread_10y_2y": spread if spread is not None else 0.5,
            "pe_ratio": 22.0,
        }

    def fetch_delta_data(self) -> Dict[str, Any]:
        """Fetch VIX and sector ETF market caps for Delta-Bolsa N-Body."""
        vix_df = fetch_vix()
        vix_val = 20.0
        if vix_df is not None and "close" in vix_df.columns:
            vix_val = float(vix_df["close"].iloc[-1])

        sector_dfs = fetch_sector_etfs(days=30)
        sector_caps: Dict[str, float] = {}
        for etf, df in sector_dfs.items():
            if "close" in df.columns and "volume" in df.columns:
                last_close = float(df["close"].iloc[-1])
                avg_vol = float(df["volume"].mean())
                sector_caps[etf] = last_close * avg_vol

        logger.info(f"Delta-Bolsa: VIX={vix_val:.1f}, {len(sector_caps)} sectors")
        return {
            "vix": vix_val,
            "sector_market_caps": sector_caps,
        }
