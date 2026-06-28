"""
Precursor Type Registry — All Natural Event Precursor Categories

Extracted from legacy TITAN V32/V46/V53 and Sentinel Orchestrator Jobs v2.0.
Each type maps to specific detection logic and validation windows.

The system detects precursors for:
  - Earthquakes (via Bz, Kp, Schumann, pressure, SO2, silent triggers, swarms)
  - Solar/geomagnetic storms (via NOAA real-time space weather)
  - Ionospheric anomalies (Blue Jets, TEC proxy)
  - Atmospheric anomalies (fog, pressure drops, chemical outgassing)
  - Volcanic precursors (SO2 spikes + seismic coupling)
  - Astrophysical events (GRBs)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class PrecursorType(Enum):
    SCHUMANN = "SCHUMANN"
    SILENT_TRIGGER = "SILENT_TRIGGER"
    SEISMIC_CLUSTER = "SEISMIC_CLUSTER"
    BLUE_JET = "BLUE_JET"
    NIEBLA_TULE = "NIEBLA_TULE"
    TORMENTA_SOLAR = "TORMENTA_SOLAR"
    PERTURBACION_GEOMAGNETICA = "PERTURBACION_GEOMAGNETICA"
    ML_INFERENCE = "ML_INFERENCE"
    GRB = "GRB"
    VOLCANICO = "VOLCANICO"
    FANTASMA = "FANTASMA"


@dataclass
class PrecursorProfile:
    tipo: PrecursorType
    description: str
    validation_window_hours: float
    min_magnitude_usgs: float
    radius_degrees: float
    variables: tuple


PRECURSOR_PROFILES = {
    PrecursorType.SCHUMANN: PrecursorProfile(
        tipo=PrecursorType.SCHUMANN,
        description="Resonancia Schumann excitation — deviation from 7.83 Hz baseline",
        validation_window_hours=72.0,
        min_magnitude_usgs=4.5,
        radius_degrees=10.0,
        variables=("schumann_hz", "schumann_activity_pct"),
    ),
    PrecursorType.SILENT_TRIGGER: PrecursorProfile(
        tipo=PrecursorType.SILENT_TRIGGER,
        description="Extreme magnetic calm — all Kp < 2.0 for 24h sustained",
        validation_window_hours=48.0,
        min_magnitude_usgs=5.0,
        radius_degrees=5.0,
        variables=("kp_median", "kp_max", "calm_duration_h"),
    ),
    PrecursorType.SEISMIC_CLUSTER: PrecursorProfile(
        tipo=PrecursorType.SEISMIC_CLUSTER,
        description="Seismic swarm — 10+ M4.0+ events within 24h in a region",
        validation_window_hours=48.0,
        min_magnitude_usgs=5.0,
        radius_degrees=5.0,
        variables=("event_count", "max_magnitude", "cluster_centroid"),
    ),
    PrecursorType.BLUE_JET: PrecursorProfile(
        tipo=PrecursorType.BLUE_JET,
        description="Ionospheric discharge — thunderstorm + temp > 25°C (pressure coupling)",
        validation_window_hours=72.0,
        min_magnitude_usgs=4.5,
        radius_degrees=8.0,
        variables=("temp_c", "pressure_hpa", "weather_id", "so2"),
    ),
    PrecursorType.NIEBLA_TULE: PrecursorProfile(
        tipo=PrecursorType.NIEBLA_TULE,
        description="Dense fog anomaly — humidity > 90%%, visibility < 1000m",
        validation_window_hours=72.0,
        min_magnitude_usgs=4.5,
        radius_degrees=5.0,
        variables=("humidity_pct", "visibility_m"),
    ),
    PrecursorType.TORMENTA_SOLAR: PrecursorProfile(
        tipo=PrecursorType.TORMENTA_SOLAR,
        description="Solar/geomagnetic storm — Bz severely southward + Kp >= 5",
        validation_window_hours=96.0,
        min_magnitude_usgs=4.5,
        radius_degrees=15.0,
        variables=("bz_nT", "kp", "viento_kms", "proton_flux"),
    ),
    PrecursorType.PERTURBACION_GEOMAGNETICA: PrecursorProfile(
        tipo=PrecursorType.PERTURBACION_GEOMAGNETICA,
        description="Geomagnetic perturbation — moderate Bz + elevated Kp",
        validation_window_hours=96.0,
        min_magnitude_usgs=4.5,
        radius_degrees=10.0,
        variables=("bz_nT", "kp", "dst_index"),
    ),
    PrecursorType.ML_INFERENCE: PrecursorProfile(
        tipo=PrecursorType.ML_INFERENCE,
        description="Machine learning composite inference from all features",
        validation_window_hours=48.0,
        min_magnitude_usgs=5.0,
        radius_degrees=5.0,
        variables=("ml_score", "feature_vector"),
    ),
    PrecursorType.GRB: PrecursorProfile(
        tipo=PrecursorType.GRB,
        description="Gamma-ray burst detection — astrophysical monitoring",
        validation_window_hours=168.0,
        min_magnitude_usgs=0.0,
        radius_degrees=180.0,
        variables=("grb_fluence", "grb_duration"),
    ),
    PrecursorType.VOLCANICO: PrecursorProfile(
        tipo=PrecursorType.VOLCANICO,
        description="Volcanic precursors — SO2 outgassing + seismic swarm coupling",
        validation_window_hours=72.0,
        min_magnitude_usgs=4.0,
        radius_degrees=3.0,
        variables=("so2_mass", "seismic_count", "pressure_hpa"),
    ),
    PrecursorType.FANTASMA: PrecursorProfile(
        tipo=PrecursorType.FANTASMA,
        description="TITAN V32 fantasma composite — core risk formula",
        validation_window_hours=72.0,
        min_magnitude_usgs=4.5,
        radius_degrees=5.0,
        variables=("bz_nT", "viento_kms", "schumann_wpc", "pressure_hpa", "kp", "lod_ms"),
    ),
}


PRECURSOR_DISPLAY_NAMES = {
    PrecursorType.SCHUMANN: "Resonancia Schumann",
    PrecursorType.SILENT_TRIGGER: "Patrón Silent Trigger (Calma)",
    PrecursorType.SEISMIC_CLUSTER: "Enjambre Sísmico Local",
    PrecursorType.BLUE_JET: "Blue Jet (Fuga Ionosférica)",
    PrecursorType.NIEBLA_TULE: "Niebla Tule (Anomalía)",
    PrecursorType.TORMENTA_SOLAR: "Tormenta Solar",
    PrecursorType.PERTURBACION_GEOMAGNETICA: "Perturbación Geomagnética",
    PrecursorType.ML_INFERENCE: "Inferencia ML",
    PrecursorType.GRB: "Gamma-Ray Burst",
    PrecursorType.VOLCANICO: "Precursor Volcánico",
    PrecursorType.FANTASMA: "Índice Fantasma (V32)",
}


def get_profile(tipo: PrecursorType) -> PrecursorProfile:
    return PRECURSOR_PROFILES[tipo]


def detect_blue_jet(temp_c: float, weather_id: int, pressure_hpa: float = 1013.0) -> bool:
    is_thunderstorm = 200 <= weather_id <= 232
    return is_thunderstorm and temp_c > 25.0


def detect_niebla_tule(humidity_pct: float, visibility_m: float) -> bool:
    return humidity_pct > 90.0 and visibility_m < 1000.0


def detect_silent_trigger(kp_series: list, min_hours: float = 12.0) -> bool:
    if len(kp_series) < 12:
        return False
    return all(kp < 2.0 for kp in kp_series) and (sum(kp_series) / len(kp_series)) <= 1.5


def detect_seismic_cluster(event_count_24h: int, threshold: int = 10) -> bool:
    return event_count_24h >= threshold


def detect_volcanic_precursor(so2_mass: float, seismic_count: int) -> bool:
    return so2_mass > 100.0 and seismic_count >= 3
