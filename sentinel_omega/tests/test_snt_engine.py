"""Tests for the core SNT engine modules."""

import numpy as np
import pytest

from sentinel_omega.core.snt_engine.satellization import (
    DominanceRegime,
    SatellizationEngine,
    SatellizationResult,
)
from sentinel_omega.core.snt_engine.friction import (
    FrictionLevel,
    InstitutionalFrictionCalculator,
)
from sentinel_omega.core.snt_engine.asi import AtomicSovereigntyIndex
from sentinel_omega.core.snt_engine.nbody import NBodyMatrix, NodeClassification


# ── SatellizationEngine ──────────────────────────────────────────────


class TestSatellizationEngine:

    def setup_method(self):
        self.engine = SatellizationEngine()

    def test_fit_positive_b_satellization(self):
        t = np.arange(1, 51, dtype=float)
        ratio = 2.0 * np.power(t, 0.4) + np.random.default_rng(42).normal(0, 0.05, len(t))
        result = self.engine.fit(t, ratio)
        assert result.regime in (DominanceRegime.SATELLIZATION, DominanceRegime.ROCHE_RADIUS)
        assert result.b > 0
        assert result.r_squared > 0.8
        assert result.n_observations == 50

    def test_fit_negative_b_convergence(self):
        t = np.arange(1, 51, dtype=float)
        ratio = 10.0 * np.power(t, -0.3)
        result = self.engine.fit(t, ratio)
        assert result.regime == DominanceRegime.CONVERGENCE
        assert result.b < -0.05

    def test_fit_near_zero_b_equilibrium(self):
        t = np.arange(1, 51, dtype=float)
        ratio = 5.0 * np.power(t, 0.01)
        result = self.engine.fit(t, ratio)
        assert result.regime == DominanceRegime.EQUILIBRIUM
        assert -0.05 <= result.b <= 0.05

    def test_fit_roche_radius(self):
        t = np.arange(1, 51, dtype=float)
        ratio = 1.0 * np.power(t, 1.5)
        result = self.engine.fit(t, ratio)
        assert result.regime == DominanceRegime.ROCHE_RADIUS
        assert result.b >= 1.0

    def test_fit_insufficient_data(self):
        t = np.array([1.0, 2.0])
        ratio = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="Insufficient data"):
            self.engine.fit(t, ratio)

    def test_fit_filters_invalid_values(self):
        t = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        ratio = np.array([np.nan, 1.0, 1.5, 2.0, 2.5, 3.0])
        result = self.engine.fit(t, ratio)
        assert result.n_observations == 5

    def test_classify_regime_boundaries(self):
        assert self.engine._classify_regime(1.5) == DominanceRegime.ROCHE_RADIUS
        assert self.engine._classify_regime(1.0) == DominanceRegime.ROCHE_RADIUS
        assert self.engine._classify_regime(0.5) == DominanceRegime.SATELLIZATION
        assert self.engine._classify_regime(0.03) == DominanceRegime.EQUILIBRIUM
        assert self.engine._classify_regime(-0.04) == DominanceRegime.EQUILIBRIUM
        assert self.engine._classify_regime(-0.1) == DominanceRegime.CONVERGENCE

    def test_detect_leapfrog_true(self):
        b_history = np.concatenate([
            np.full(15, 0.3),
            np.full(15, -0.2),
        ])
        assert self.engine.detect_leapfrog(b_history, window=10) == True

    def test_detect_leapfrog_false_insufficient_data(self):
        assert self.engine.detect_leapfrog(np.array([0.3, -0.1]), window=10) == False

    def test_detect_leapfrog_false_no_reversal(self):
        b_history = np.full(30, 0.3)
        assert self.engine.detect_leapfrog(b_history, window=10) == False

    def test_compare_triggers(self):
        rng = np.random.default_rng(42)
        abrupt = rng.normal(0.8, 0.1, 30)
        gradual = rng.normal(0.3, 0.1, 30)
        result = self.engine.compare_triggers(abrupt, gradual)
        assert result["abrupt_mean_b"] > result["gradual_mean_b"]
        assert result["velocity_ratio"] > 1.0
        assert "mann_whitney_U" in result
        assert "p_value" in result

    def test_power_law_static(self):
        assert SatellizationEngine.power_law(1.0, 2.0, 3.0) == 2.0
        assert SatellizationEngine.power_law(2.0, 1.0, 0.0) == 1.0


# ── InstitutionalFrictionCalculator ──────────────────────────────────


class TestFrictionCalculator:

    def setup_method(self):
        self.calc = InstitutionalFrictionCalculator()

    def test_zero_friction(self):
        profile = self.calc.calculate(0.0, 0.0, 0.0, "epidemic")
        assert profile.level == FrictionLevel.ZERO
        assert profile.score == 0.0

    def test_low_friction(self):
        profile = self.calc.calculate(0.2, 0.3, 0.1, "crypto")
        assert profile.level == FrictionLevel.LOW
        assert 0.1 <= profile.score < 0.3

    def test_medium_friction(self):
        profile = self.calc.calculate(0.5, 0.6, 0.4, "stock_market")
        assert profile.level == FrictionLevel.MEDIUM

    def test_high_friction(self):
        profile = self.calc.calculate(0.8, 0.9, 0.7, "sovereign")
        assert profile.level == FrictionLevel.HIGH

    def test_maximum_friction(self):
        profile = self.calc.calculate(1.0, 1.0, 1.0, "geodynamic")
        assert profile.level == FrictionLevel.MAXIMUM
        assert profile.score == 1.0

    def test_weighted_score_calculation(self):
        profile = self.calc.calculate(1.0, 0.0, 0.0, "test")
        assert profile.score == pytest.approx(0.4, abs=1e-6)

        profile = self.calc.calculate(0.0, 1.0, 0.0, "test")
        assert profile.score == pytest.approx(0.35, abs=1e-6)

        profile = self.calc.calculate(0.0, 0.0, 1.0, "test")
        assert profile.score == pytest.approx(0.25, abs=1e-6)

    def test_expected_b_values(self):
        profile_zero = self.calc.calculate(0.0, 0.0, 0.0, "epidemic")
        assert self.calc.expected_b(profile_zero) == 0.95

        profile_max = self.calc.calculate(1.0, 1.0, 1.0, "geodynamic")
        assert self.calc.expected_b(profile_max) == 0.02

    def test_anomaly_score(self):
        profile = self.calc.calculate(0.0, 0.0, 0.0, "epidemic")
        score = self.calc.anomaly_score(0.95, profile)
        assert score == pytest.approx(0.0, abs=1e-6)

        score = self.calc.anomaly_score(0.5, profile)
        assert score > 0

    def test_domain_baselines(self):
        assert InstitutionalFrictionCalculator.DOMAIN_BASELINES["crypto"] == FrictionLevel.LOW
        assert InstitutionalFrictionCalculator.DOMAIN_BASELINES["geodynamic"] == FrictionLevel.MAXIMUM
        assert InstitutionalFrictionCalculator.DOMAIN_BASELINES["stock_market"] == FrictionLevel.MEDIUM

    def test_profile_stores_domain(self):
        profile = self.calc.calculate(0.5, 0.5, 0.5, "my_domain")
        assert profile.domain == "my_domain"


# ── AtomicSovereigntyIndex ───────────────────────────────────────────


class TestASI:

    def setup_method(self):
        self.asi = AtomicSovereigntyIndex()

    def test_calculate_sovereign(self):
        sequence = ["commit", "push", "review", "merge", "deploy"]
        result = self.asi.calculate(sequence, autonomous_actions=9, total_actions=10, friction_index=0.5)
        assert result.asi_score >= 3.0
        assert result.above_threshold is True

    def test_calculate_captured(self):
        sequence = ["prompted"]
        result = self.asi.calculate(sequence, autonomous_actions=1, total_actions=100, friction_index=1.0)
        assert result.asi_score < 0.5
        assert result.above_threshold is False

    def test_event_wall_threshold(self):
        below = self.asi.calculate(["a", "b", "c", "d"], 4, 4, 0.1)
        assert below.above_threshold is False
        assert below.event_count == 4

        at_wall = self.asi.calculate(["a", "b", "c", "d", "e"], 5, 5, 0.1)
        assert at_wall.above_threshold is True
        assert at_wall.event_count == 5

    def test_shannon_entropy_uniform(self):
        sequence = ["a", "b", "c", "d"]
        entropy = AtomicSovereigntyIndex._shannon_entropy(sequence)
        assert entropy == pytest.approx(2.0, abs=1e-6)

    def test_shannon_entropy_single_symbol(self):
        entropy = AtomicSovereigntyIndex._shannon_entropy(["x", "x", "x"])
        assert entropy == 0.0

    def test_shannon_entropy_empty(self):
        assert AtomicSovereigntyIndex._shannon_entropy([]) == 0.0

    def test_zero_friction_clamped(self):
        result = self.asi.calculate(["a", "b", "c"], 3, 3, 0.0)
        assert result.friction == 0.0
        assert np.isfinite(result.asi_score)

    def test_sovereignty_classification(self):
        assert self.asi.sovereignty_classification(3.5) == "sovereign"
        assert self.asi.sovereignty_classification(2.0) == "semi_autonomous"
        assert self.asi.sovereignty_classification(0.8) == "dependent"
        assert self.asi.sovereignty_classification(0.1) == "captured"

    def test_alpha_ratio(self):
        result = self.asi.calculate(["a"], 5, 10, 1.0)
        assert result.alpha == 0.5

    def test_zero_total_actions(self):
        result = self.asi.calculate(["a"], 0, 0, 1.0)
        assert result.alpha == 0.0


# ── NBodyMatrix ──────────────────────────────────────────────────────


class TestNBodyMatrix:

    def setup_method(self):
        self.nbody = NBodyMatrix()

    def test_analyze_basic(self):
        entities = {
            "CDMX": 400.0,
            "Jalisco": 100.0,
            "Nuevo_Leon": 90.0,
            "Puebla": 50.0,
            "Tlaxcala": 10.0,
        }
        result = self.nbody.analyze(entities, hub_name="CDMX")
        assert result.power_law_b < 0
        assert result.r_squared > 0
        assert len(result.nodes) == 5
        assert result.nodes[0].name == "CDMX"
        assert result.nodes[0].level == NodeClassification.MACRO_HUB

    def test_analyze_hub_not_found(self):
        with pytest.raises(ValueError, match="Hub.*not found"):
            self.nbody.analyze({"A": 10}, hub_name="B")

    def test_node_classification_levels(self):
        entities = {
            "hub": 100.0,
            "secondary": 70.0,
            "bypass": 40.0,
            "shadow": 20.0,
            "exogenous": 5.0,
        }
        result = self.nbody.analyze(entities, hub_name="hub")
        levels = {n.name: n.level for n in result.nodes}
        assert levels["hub"] == NodeClassification.MACRO_HUB
        assert levels["secondary"] == NodeClassification.SECONDARY_ATTRACTOR
        assert levels["bypass"] == NodeClassification.BYPASS_LOGISTIC
        assert levels["shadow"] == NodeClassification.SHADOW_NODE
        assert levels["exogenous"] == NodeClassification.EXOGENOUS

    def test_extraction_vector(self):
        entities = {"hub": 100.0, "shadow": 25.0}
        result = self.nbody.analyze(entities, hub_name="hub")
        shadow_node = [n for n in result.nodes if n.name == "shadow"][0]
        assert shadow_node.extraction_vector == pytest.approx(0.75, abs=1e-6)

    def test_composite_gradient_positive(self):
        entities = {"hub": 100.0, "a": 30.0, "b": 10.0}
        result = self.nbody.analyze(entities, hub_name="hub")
        assert result.composite_gradient > 0

    def test_two_entities_minimum(self):
        entities = {"hub": 100.0, "shadow": 10.0}
        result = self.nbody.analyze(entities, hub_name="hub")
        assert len(result.nodes) == 2
        assert result.power_law_b < 0
