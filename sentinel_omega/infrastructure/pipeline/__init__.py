"""Data pipeline — wires real APIs into agent ingest() methods."""

from sentinel_omega.infrastructure.pipeline.data_pipeline import GeodynamicPipeline
from sentinel_omega.infrastructure.pipeline.layer_runners import GeodynamicLayerRunner
from sentinel_omega.infrastructure.pipeline.backcast import run_backcast
from sentinel_omega.infrastructure.pipeline.legacy_loader import LegacyDataLoader
from sentinel_omega.infrastructure.pipeline.reporte_sentinel import (
    reporte_general,
    reporte_padre,
    reporte_omega,
)
from sentinel_omega.infrastructure.pipeline.scheduler_reportes import ReporteScheduler
from sentinel_omega.infrastructure.pipeline.mantenimiento import (
    barrido_diario,
    construir_correlaciones_padre,
    evaluar_sesgo_aprendizaje,
    construir_correlaciones_omega,
)
