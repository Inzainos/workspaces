"""Data pipeline — wires real APIs into agent ingest() methods."""

from sentinel_omega.infrastructure.pipeline.data_pipeline import (
    GeodynamicPipeline,
    CryptoPipeline,
    BolsaPipeline,
)
from sentinel_omega.infrastructure.pipeline.layer_runners import (
    GeodynamicLayerRunner,
    CryptoLayerRunner,
    BolsaLayerRunner,
)
from sentinel_omega.infrastructure.pipeline.legacy_loader import LegacyDataLoader
