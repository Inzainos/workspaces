"""Tests for the precursor detection module (TITAN V32/V46 lineage)."""

import time

import numpy as np
import pandas as pd
import pytest

from sentinel_omega.core.precursor.risk_calculator import (
    PrecursorRisk,
    compute_fantasma,
    classify_risk,
    compute_risk_from_signals,
    format_risk_report,
    RISK_THRESHOLDS,
)
from sentinel_omega.core.precursor.assertivity import (
    AssertivityTracker,
    AssertivityResult,
    Prediction,
)
from sentinel_omega.core.precursor.precursor_types import (
    PrecursorType,
    PrecursorProfile,
    PRECURSOR_PROFILES,
    PRECURSOR_DISPLAY_NAMES,
    get_profile,
    detect_blue_jet,
    detect_niebla_tule,
    detect_silent_trigger,
    detect_seismic_cluster,
    detect_volcanic_precursor,
)


# ── Risk Calculator (TITAN V32 fantasma) ────────────────────────────


class TestFantasmaFormula:

    def test_zero_inputs_produce_low_risk(self):
        risk = compute_fantasma(bz=0, viento=0, sch_wpc=0)
        assert risk.fantasma == 0.0
        assert risk.risk_level == "LOW"

    def test_core_formula_matches_titan_v32(self):
        """fantasma = (viento * 0.02) + (abs(bz) ** 2) + (sch_wpc * 1.5)"""
        bz = -5.0
        viento = 400.0
        sch_wpc = 0.2

        risk = compute_fantasma(bz=bz, viento=viento, sch_wpc=sch_wpc)
        expected = (400 * 0.02) + (5.0 ** 2) + (0.2 * 1.5)
        assert abs(risk.fantasma - expected) < 0.01

    def test_bz_squared_contribution(self):
        risk = compute_fantasma(bz=-10.0, viento=0, sch_wpc=0)
        assert risk.bz_contribution == 100.0
        assert risk.fantasma >= 100.0

    def test_negative_bz_same_as_positive(self):
        r1 = compute_fantasma(bz=-8.0, viento=0, sch_wpc=0)
        r2 = compute_fantasma(bz=8.0, viento=0, sch_wpc=0)
        assert r1.bz_contribution == r2.bz_contribution

    def test_wind_contribution(self):
        risk = compute_fantasma(bz=0, viento=600.0, sch_wpc=0)
        assert risk.wind_contribution == 12.0

    def test_schumann_contribution(self):
        risk = compute_fantasma(bz=0, viento=0, sch_wpc=0.8)
        assert abs(risk.schumann_contribution - 1.2) < 1e-10

    def test_severe_storm_conditions(self):
        """Bz=-20, viento=800, Schumann excited → CRITICAL."""
        risk = compute_fantasma(bz=-20.0, viento=800.0, sch_wpc=0.5)
        assert risk.risk_level == "CRITICAL"
        assert risk.fantasma > 30.0

    def test_moderate_conditions(self):
        risk = compute_fantasma(bz=-3.0, viento=350.0, sch_wpc=0.1)
        expected = (350 * 0.02) + (3.0 ** 2) + (0.1 * 1.5)
        assert abs(risk.fantasma - expected) < 0.01
        assert risk.risk_level == "HIGH"

    def test_is_elevated_property(self):
        low = compute_fantasma(bz=0, viento=0, sch_wpc=0)
        high = compute_fantasma(bz=-10, viento=500, sch_wpc=0.5)
        assert not low.is_elevated
        assert high.is_elevated


class TestPressureModifier:

    def test_normal_pressure_no_modifier(self):
        risk = compute_fantasma(bz=-2, viento=300, sch_wpc=0, pressure_hpa=1015.0)
        assert risk.pressure_modifier == 0.0

    def test_low_pressure_adds_risk(self):
        risk = compute_fantasma(bz=-2, viento=300, sch_wpc=0, pressure_hpa=1000.0)
        assert risk.pressure_modifier > 0.0
        expected_mod = (1008.0 - 1000.0) / 5.0
        assert abs(risk.pressure_modifier - expected_mod) < 0.01

    def test_very_low_pressure_capped(self):
        risk = compute_fantasma(bz=0, viento=0, sch_wpc=0, pressure_hpa=960.0)
        assert risk.pressure_modifier <= 3.0


class TestKpModifier:

    def test_low_kp_no_multiplier(self):
        risk = compute_fantasma(bz=-3, viento=300, sch_wpc=0, kp=2.0)
        assert risk.kp_modifier == 1.0

    def test_storm_kp_multiplies(self):
        r_base = compute_fantasma(bz=-3, viento=300, sch_wpc=0, kp=0.0)
        r_storm = compute_fantasma(bz=-3, viento=300, sch_wpc=0, kp=7.0)
        assert r_storm.fantasma > r_base.fantasma
        assert r_storm.kp_modifier > 1.0


class TestLodModifier:

    def test_normal_lod_no_modifier(self):
        risk = compute_fantasma(bz=0, viento=0, sch_wpc=0, lod_ms=0.1)
        assert risk.lod_modifier == 0.0

    def test_anomalous_lod_adds_risk(self):
        risk = compute_fantasma(bz=0, viento=0, sch_wpc=0, lod_ms=1.5)
        assert risk.lod_modifier > 0.0


class TestRiskClassification:

    def test_thresholds(self):
        assert classify_risk(0.0) == "LOW"
        assert classify_risk(4.9) == "LOW"
        assert classify_risk(5.0) == "MODERATE"
        assert classify_risk(14.9) == "MODERATE"
        assert classify_risk(15.0) == "HIGH"
        assert classify_risk(29.9) == "HIGH"
        assert classify_risk(30.0) == "CRITICAL"
        assert classify_risk(100.0) == "CRITICAL"


class TestComputeRiskFromSignals:

    def test_from_agent_dicts(self):
        signals = [
            {"bz_mean": -8.0, "plasma_speed": 500.0},
            {"schumann_activity_pct": 20.0, "kp_mean": 6.0},
        ]
        risk = compute_risk_from_signals(signals, atmospheric={"mean_pressure": 1005.0})
        assert risk.fantasma > 0
        assert risk.components["bz_nT"] == -8.0
        assert risk.components["wind_kms"] == 500.0

    def test_empty_signals_produce_low(self):
        risk = compute_risk_from_signals([])
        assert risk.risk_level == "LOW"


class TestFormatRiskReport:

    def test_contains_all_components(self):
        risk = compute_fantasma(bz=-5, viento=400, sch_wpc=0.3, pressure_hpa=1003, kp=6)
        report = format_risk_report(risk)
        assert "PRECURSOR RISK" in report
        assert "Fantasma Index" in report
        assert "Bz²" in report
        assert "Wind" in report
        assert "Schumann" in report
        assert "Pressure" in report
        assert "Kp" in report


# ── Assertivity Tracker (V46 lineage) ───────────────────────────────


class TestAssertivityTracker:

    def setup_method(self):
        self.tracker = AssertivityTracker(radius_degrees=5.0, window_days=30)

    def test_record_prediction(self):
        pred = self.tracker.record_prediction(
            latitude=17.0, longitude=-99.5,
            risk_level="HIGH", fantasma=25.0,
        )
        assert pred.latitude == 17.0
        assert pred.risk_level == "HIGH"
        assert self.tracker.prediction_count == 1

    def test_hit_within_radius(self):
        self.tracker.record_prediction(17.0, -99.5, "HIGH", 25.0)
        self.tracker.ingest_events([
            {"latitude": 16.5, "longitude": -99.0, "magnitude": 5.2, "time": time.time()},
        ])
        result = self.tracker.validate(min_magnitude=4.5)
        assert result.hits == 1
        assert result.false_alarms == 0
        assert result.hit_rate == 1.0

    def test_miss_outside_radius(self):
        self.tracker.record_prediction(17.0, -99.5, "HIGH", 25.0)
        self.tracker.ingest_events([
            {"latitude": 35.0, "longitude": -118.0, "magnitude": 6.0, "time": time.time()},
        ])
        result = self.tracker.validate(min_magnitude=4.5)
        assert result.hits == 0
        assert result.false_alarms == 1
        assert result.misses == 1

    def test_false_alarm_no_events(self):
        self.tracker.record_prediction(17.0, -99.5, "HIGH", 25.0)
        self.tracker.ingest_events([])
        result = self.tracker.validate()
        assert result.false_alarms == 1
        assert result.hits == 0

    def test_miss_no_predictions(self):
        self.tracker.ingest_events([
            {"latitude": 17.0, "longitude": -99.5, "magnitude": 5.0, "time": time.time()},
        ])
        result = self.tracker.validate()
        assert result.misses == 1
        assert result.total_predictions == 0

    def test_euclidean_distance(self):
        dist = AssertivityTracker._euclidean_distance(0, 0, 3, 4)
        assert abs(dist - 5.0) < 0.01

    def test_multiple_predictions_and_events(self):
        self.tracker.record_prediction(17.0, -99.5, "HIGH", 25.0)
        self.tracker.record_prediction(15.0, -92.0, "MODERATE", 10.0)
        self.tracker.record_prediction(40.0, -120.0, "HIGH", 20.0)

        self.tracker.ingest_events([
            {"latitude": 16.8, "longitude": -99.2, "magnitude": 5.5, "time": time.time()},
            {"latitude": 14.5, "longitude": -91.5, "magnitude": 4.8, "time": time.time()},
        ])
        result = self.tracker.validate()
        assert result.hits == 2
        assert result.false_alarms == 1

    def test_min_magnitude_filter(self):
        self.tracker.record_prediction(17.0, -99.5, "HIGH", 25.0)
        self.tracker.ingest_events([
            {"latitude": 17.0, "longitude": -99.5, "magnitude": 3.0, "time": time.time()},
        ])
        result = self.tracker.validate(min_magnitude=4.5)
        assert result.hits == 0
        assert result.total_events == 0

    def test_format_report(self):
        result = AssertivityResult(
            total_predictions=10, total_events=8,
            hits=6, misses=2, false_alarms=4,
            hit_rate=0.6, miss_rate=0.25, false_alarm_rate=0.4,
            evaluation_window_days=30,
        )
        report = self.tracker.format_report(result)
        assert "ASSERTIVITY REPORT" in report
        assert "60%" in report
        assert "25%" in report


# ── Integration: LayerRunner precursor risk ─────────────────────────


class TestGeodynamicPrecursorIntegration:

    def test_runner_computes_risk(self):
        from unittest.mock import patch, MagicMock
        from sentinel_omega.infrastructure.pipeline.layer_runners import GeodynamicLayerRunner

        runner = GeodynamicLayerRunner(enable_satellite=False)

        mock_alfa1 = {
            "omni_dataframe": pd.DataFrame({
                "bz_gsm": [-8.0, -7.0, -9.0],
                "plasma_speed": [500.0, 520.0, 480.0],
            }),
        }
        mock_beta1 = {
            "kp_series": np.array([3.0, 4.0, 5.0] * 20),
            "seismic_magnitudes": np.array([4.5, 5.0]),
            "schumann_activity": 25.0,
            "schumann_frequency": 7.83,
        }
        mock_delta = {
            "energetic_nodes": {"RegionA": 1e12, "RegionB": 5e11, "RegionC": 2e11},
            "psychosocial_index": 0.4,
            "pressure_gradient": {"mean_pressure": 1005.0, "pressure_spread": 8.0},
        }

        with (
            patch.object(runner.pipeline, "fetch_alfa1_data", return_value=mock_alfa1),
            patch.object(runner.pipeline, "fetch_beta1_data", return_value=mock_beta1),
            patch.object(runner.pipeline, "fetch_delta_data", return_value=mock_delta),
        ):
            consensus = runner.run()

        assert runner.last_risk is not None
        assert runner.last_risk.fantasma > 0
        assert runner.last_risk.components["bz_nT"] < 0
        assert consensus.precursor_risk is runner.last_risk

    def test_runner_risk_with_empty_data(self):
        from unittest.mock import patch
        from sentinel_omega.infrastructure.pipeline.layer_runners import GeodynamicLayerRunner

        runner = GeodynamicLayerRunner(enable_satellite=False)

        with (
            patch.object(runner.pipeline, "fetch_alfa1_data", return_value={}),
            patch.object(runner.pipeline, "fetch_beta1_data", return_value={}),
            patch.object(runner.pipeline, "fetch_delta_data", return_value={}),
        ):
            consensus = runner.run()

        assert runner.last_risk is not None
        assert runner.last_risk.fantasma == 0.0
        assert runner.last_risk.risk_level == "LOW"


# ── Precursor Types Registry ────────────────────────────────────────


class TestPrecursorTypes:

    def test_all_types_have_profiles(self):
        for pt in PrecursorType:
            assert pt in PRECURSOR_PROFILES

    def test_all_types_have_display_names(self):
        for pt in PrecursorType:
            assert pt in PRECURSOR_DISPLAY_NAMES

    def test_profile_has_required_fields(self):
        for pt, profile in PRECURSOR_PROFILES.items():
            assert profile.tipo == pt
            assert profile.validation_window_hours > 0
            assert len(profile.variables) > 0

    def test_get_profile(self):
        p = get_profile(PrecursorType.FANTASMA)
        assert p.tipo == PrecursorType.FANTASMA
        assert "bz_nT" in p.variables


class TestBlueJetDetection:

    def test_thunderstorm_hot(self):
        assert detect_blue_jet(temp_c=30.0, weather_id=210) is True

    def test_thunderstorm_cold(self):
        assert detect_blue_jet(temp_c=15.0, weather_id=210) is False

    def test_clear_sky_hot(self):
        assert detect_blue_jet(temp_c=35.0, weather_id=800) is False

    def test_boundary_weather_id(self):
        assert detect_blue_jet(temp_c=30.0, weather_id=200) is True
        assert detect_blue_jet(temp_c=30.0, weather_id=232) is True
        assert detect_blue_jet(temp_c=30.0, weather_id=199) is False
        assert detect_blue_jet(temp_c=30.0, weather_id=233) is False


class TestNieblaTuleDetection:

    def test_dense_fog(self):
        assert detect_niebla_tule(humidity_pct=95.0, visibility_m=500.0) is True

    def test_normal_conditions(self):
        assert detect_niebla_tule(humidity_pct=60.0, visibility_m=10000.0) is False

    def test_high_humidity_good_visibility(self):
        assert detect_niebla_tule(humidity_pct=95.0, visibility_m=5000.0) is False

    def test_low_visibility_low_humidity(self):
        assert detect_niebla_tule(humidity_pct=50.0, visibility_m=500.0) is False


class TestSilentTriggerDetection:

    def test_all_low_kp(self):
        kp = [0.5, 1.0, 0.3, 1.2, 0.8, 0.5, 1.0, 0.3, 1.2, 0.8, 1.5, 0.7]
        assert detect_silent_trigger(kp) is True

    def test_one_high_kp(self):
        kp = [0.5, 1.0, 0.3, 1.2, 0.8, 0.5, 1.0, 3.5, 1.2, 0.8, 1.5, 0.7]
        assert detect_silent_trigger(kp) is False

    def test_insufficient_data(self):
        assert detect_silent_trigger([1.0, 0.5, 0.3]) is False


class TestSeismicClusterDetection:

    def test_cluster_detected(self):
        assert detect_seismic_cluster(15) is True

    def test_below_threshold(self):
        assert detect_seismic_cluster(5) is False

    def test_exact_threshold(self):
        assert detect_seismic_cluster(10) is True


class TestVolcanicPrecursor:

    def test_volcanic_detected(self):
        assert detect_volcanic_precursor(so2_mass=150.0, seismic_count=5) is True

    def test_no_so2(self):
        assert detect_volcanic_precursor(so2_mass=20.0, seismic_count=5) is False

    def test_no_seismicity(self):
        assert detect_volcanic_precursor(so2_mass=150.0, seismic_count=1) is False


class TestTelegramPrecursorFormat:

    def test_format_precursor_alert(self):
        from sentinel_omega.infrastructure.api.telegram import format_precursor_alert
        msg = format_precursor_alert(
            precursor_type="BLUE_JET",
            display_name="Blue Jet (Fuga Ionosférica)",
            value=1.0,
            details="Thunderstorm detected at Tlaxcala node",
            lat=19.31, lon=-98.24,
            lugar="Tlaxcala",
        )
        assert "ALERTA DE PRECURSOR" in msg
        assert "Blue Jet" in msg
        assert "72h" in msg
        assert "48h" in msg
        assert "Tlaxcala" in msg
