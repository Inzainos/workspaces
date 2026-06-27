"""
Sentinel Omega — Central Configuration
All layers share this configuration backbone.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class DatabaseConfig:
    geodynamic_db: str = "data/SENTINEL_OMEGA_PRO.db"
    crypto_db: str = "data/sentinel_crypto.db"
    bolsa_db: str = "data/sentinel_bolsa.db"
    lottery_db: str = "data/TITAN_MEMORY.db"  # STANDALONE — separate


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = True


@dataclass
class APIConfig:
    # Geodynamic
    noaa_swpc_url: str = "https://services.swpc.noaa.gov/json/"
    usgs_fdsn_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/"
    omni_nasa_url: str = "https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni/"
    tomsk_schumann_url: str = "http://sosrff.tsu.ru/"
    openweathermap_key: str = ""

    # Crypto
    bitso_key: str = ""
    bitso_secret: str = ""
    coingecko_url: str = "https://api.coingecko.com/api/v3/"
    binance_url: str = "https://api.binance.com/api/v3/"

    # Stock Market
    alpha_vantage_key: str = ""
    yahoo_finance_url: str = "https://query1.finance.yahoo.com/v8/"


@dataclass
class SNTConfig:
    min_data_points: int = 10
    roche_threshold: float = 1.0
    equilibrium_band: float = 0.05
    convergence_threshold: float = -0.05
    friction_spearman_rho: float = -0.68


@dataclass
class LayerConfig:
    enabled: bool = True
    refresh_interval_s: int = 300
    max_retries: int = 3
    consensus_threshold: float = 0.66


@dataclass
class SentinelOmegaConfig:
    project_name: str = "Sentinel Omega"
    version: str = "2.0.0-shadow-node"
    author: str = "Elán Zainos Corona (Fractal Core Research)"

    databases: DatabaseConfig = field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    apis: APIConfig = field(default_factory=APIConfig)
    snt: SNTConfig = field(default_factory=SNTConfig)

    layers: Dict[str, LayerConfig] = field(default_factory=lambda: {
        "geodynamic": LayerConfig(refresh_interval_s=300),
        "crypto": LayerConfig(refresh_interval_s=60),
        "bolsa": LayerConfig(refresh_interval_s=900),
        "lottery": LayerConfig(enabled=False),  # SEPARATED
    })

    hardware: str = "MSI Katana — RTX 3050 (CUDA) + Python 3.10+"
    deployment_path: str = "/opt/sentinel_omega/"

    coordinates: Dict[str, float] = field(default_factory=lambda: {
        "lat": 19.31,
        "lon": -98.24,
        "location": "Tlaxcala, México"
    })
