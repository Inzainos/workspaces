"""Data pipeline — wires real APIs into agent ingest() methods."""

from sentinel_omega.infrastructure.pipeline.data_pipeline import GeodynamicPipeline
from sentinel_omega.infrastructure.pipeline.layer_runners import GeodynamicLayerRunner
from sentinel_omega.infrastructure.pipeline.backcast import run_backcast
from sentinel_omega.infrastructure.pipeline.legacy_loader import LegacyDataLoader
