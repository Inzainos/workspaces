"""
Sentinel Omega — Central Configuration
All secrets loaded from environment variables. Never hardcode tokens.
"""

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DatabaseConfig:
    geodynamic_db: str = "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"
    lottery_db: str = "sentinel_omega/data/TITAN_MEMORY.db"
    ensure_dir: bool = True


@dataclass
class TelegramConfig:
    bot_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id: str = field(default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", ""))
    enabled: bool = field(default_factory=lambda: bool(
        os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")
    ))

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


@dataclass
class APIConfig:
    # Geodynamic (public, no keys needed)
    noaa_swpc_url: str = "https://services.swpc.noaa.gov/json/"
    usgs_fdsn_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/"
    omni_nasa_url: str = "https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni/"
    tomsk_schumann_url: str = "http://sosrff.tsu.ru/"

    # Financial data (used by Delta agent)
    coingecko_url: str = "https://api.coingecko.com/api/v3/"
    binance_url: str = "https://api.binance.com/api/v3/"
    yahoo_finance_url: str = "https://query1.finance.yahoo.com/v8/finance/chart/"
    bitso_key: str = field(default_factory=lambda: os.environ.get("BITSO_API_KEY", ""))
    bitso_secret: str = field(default_factory=lambda: os.environ.get("BITSO_API_SECRET", ""))
    coingecko_api_key: str = field(default_factory=lambda: os.environ.get("COINGECKO_API_KEY", ""))

    alpha_vantage_key: str = field(default_factory=lambda: os.environ.get("ALPHA_VANTAGE_KEY", ""))

    # Weather
    openweathermap_key: str = field(default_factory=lambda: os.environ.get("OPENWEATHERMAP_KEY", ""))

    # Astronomy (public APIs)
    noaa_goes_xray_url: str = "https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json"


@dataclass
class SNTConfig:
    min_data_points: int = 3
    extreme_threshold: float = 2.0
    roche_threshold: float = 1.0
    active_threshold: float = 0.3
    gradual_threshold: float = 0.05
    equilibrium_threshold: float = -0.1
    equilibrium_band: float = 0.1
    friction_pearson_rho: float = -0.68
    friction_p_value: float = 2.5e-97
    corpus_cases: int = 721
    corpus_domains: int = 11


@dataclass
class LayerConfig:
    enabled: bool = True
    refresh_interval_s: int = 300
    max_retries: int = 3
    consensus_threshold: float = 0.66


@dataclass
class ONNXConfig:
    """ONNX Models Configuration"""
    enabled: bool = True
    models_dir: str = "sentinel_omega/models"
    fallback_to_mock: bool = True  # Use mock models if real ones not found
    use_gpu: bool = field(default_factory=lambda: os.environ.get("ONNX_USE_GPU", "true").lower() == "true")


@dataclass
class JupyterConfig:
    """Jupyter/Notebook-specific settings"""
    enabled: bool = field(default_factory=lambda: os.environ.get("JUPYTER_ENABLED", "false").lower() == "true")
    notebook_mode: bool = True  # True = notebook, False = script
    disable_telegram: bool = field(default_factory=lambda: os.environ.get("JUPYTER_DISABLE_TELEGRAM", "true").lower() == "true")
    display_plots: bool = True
    refresh_interval_s: int = 300


@dataclass
class SentinelOmegaConfig:
    project_name: str = "Sentinel Omega"
    version: str = "2.5.0-shadow-node"
    author: str = "Elán Zainos Corona (Fractal Core Research)"

    databases: DatabaseConfig = field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    apis: APIConfig = field(default_factory=APIConfig)
    snt: SNTConfig = field(default_factory=SNTConfig)
    onnx: ONNXConfig = field(default_factory=ONNXConfig)
    jupyter: JupyterConfig = field(default_factory=JupyterConfig)

    layers: Dict[str, LayerConfig] = field(default_factory=lambda: {
        "geodynamic": LayerConfig(refresh_interval_s=300),
        "lottery": LayerConfig(enabled=False),
    })

    hardware: str = "MSI Katana — RTX 3050 (CUDA) + Python 3.10+"
    deployment_path: str = "/opt/sentinel_omega/"

    coordinates: Dict[str, float] = field(default_factory=lambda: {
        "lat": 19.31,
        "lon": -98.24,
        "location": "Tlaxcala, México",
    })


# Global config instance
config = SentinelOmegaConfig()
