"""Tests for agent base, consensus, and layer agents."""

import time
import numpy as np
import pandas as pd
import pytest

from sentinel_omega.core.shared.agent_base import (
    AgentSignal,
    BaseAgent,
    ConfidenceLevel,
    ConsensusResult,
    PadreAgent,
    SignalType,
)
from sentinel_omega.layers.geodynamic.padre.agent import GeodynamicPadre
from sentinel_omega.layers.crypto.padre_crypto.agent import CryptoPadre
from sentinel_omega.layers.crypto.alfa_crypto.agent import AlfaCryptoAgent


# ── Helpers ──────────────────────────────────────────────────────────


def _signal(name: str, signal_type: SignalType, confidence: float = 0.8) -> AgentSignal:
    return AgentSignal(
        agent_name=name,
        signal_type=signal_type,
        confidence=confidence,
        timestamp=time.time(),
    )


class ConcreteAgent(BaseAgent):
    def ingest(self, data):
        self._data = data

    def analyze(self):
        return self.emit_signal(SignalType.NEUTRAL, 0.5)

    def health_check(self):
        return True


# ── BaseAgent ────────────────────────────────────────────────────────


class TestBaseAgent:

    def test_emit_signal(self):
        agent = ConcreteAgent("test_agent", "test_layer")
        signal = agent.emit_signal(SignalType.ALERT, 0.9, reasoning="test")
        assert signal.agent_name == "test_agent"
        assert signal.signal_type == SignalType.ALERT
        assert signal.confidence == 0.9
        assert signal.reasoning == "test"
        assert signal.timestamp > 0

    def test_last_signal_stored(self):
        agent = ConcreteAgent("test", "layer")
        agent.emit_signal(SignalType.BULLISH, 0.7)
        assert agent._last_signal.signal_type == SignalType.BULLISH

    def test_analyze_returns_signal(self):
        agent = ConcreteAgent("test", "layer")
        signal = agent.analyze()
        assert isinstance(signal, AgentSignal)
        assert signal.signal_type == SignalType.NEUTRAL

    def test_signal_default_data(self):
        agent = ConcreteAgent("test", "layer")
        signal = agent.emit_signal(SignalType.NEUTRAL, 0.5)
        assert signal.data == {}


# ── PadreAgent (Asymmetric Loss) ─────────────────────────────────────


class TestPadreAsymmetricLoss:

    def test_missed_event_high_penalty(self):
        padre = GeodynamicPadre()
        loss = padre.asymmetric_loss(predicted=False, actual=True)
        assert loss == 10.0

    def test_false_alarm_low_penalty(self):
        padre = GeodynamicPadre()
        loss = padre.asymmetric_loss(predicted=True, actual=False)
        assert loss == 1.0

    def test_correct_prediction_zero_loss(self):
        padre = GeodynamicPadre()
        assert padre.asymmetric_loss(True, True) == 0.0
        assert padre.asymmetric_loss(False, False) == 0.0

    def test_crypto_asymmetric_loss_inverted(self):
        padre = CryptoPadre()
        miss_loss = padre.asymmetric_loss(predicted=False, actual=True)
        false_alarm_loss = padre.asymmetric_loss(predicted=True, actual=False)
        assert miss_loss == 3.0
        assert false_alarm_loss == 5.0


# ── PadreAgent (Veto Check) ──────────────────────────────────────────


class TestVetoCheck:

    def test_veto_on_empty_signals(self):
        padre = GeodynamicPadre()
        assert padre.veto_check([]) is True

    def test_veto_on_all_neutral(self):
        padre = GeodynamicPadre()
        signals = [_signal("a", SignalType.NEUTRAL), _signal("b", SignalType.NEUTRAL)]
        assert padre.veto_check(signals) is True

    def test_no_veto_on_unanimous(self):
        padre = GeodynamicPadre()
        signals = [
            _signal("a", SignalType.ALERT),
            _signal("b", SignalType.ALERT),
            _signal("c", SignalType.ALERT),
        ]
        assert padre.veto_check(signals) is False

    def test_veto_on_split_signals(self):
        padre = GeodynamicPadre()
        signals = [
            _signal("a", SignalType.ALERT),
            _signal("b", SignalType.BULLISH),
            _signal("c", SignalType.BEARISH),
        ]
        assert padre.veto_check(signals) is True


# ── GeodynamicPadre Consensus ────────────────────────────────────────


class TestGeodynamicPadreConsensus:

    def setup_method(self):
        self.padre = GeodynamicPadre()

    def test_full_consensus_alert(self):
        signals = [
            _signal("alfa1", SignalType.ALERT),
            _signal("beta1", SignalType.ALERT),
            _signal("alfa2", SignalType.ALERT),
            _signal("beta2", SignalType.ALERT),
            _signal("delta", SignalType.ALERT),
        ]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is True
        assert result.final_signal == SignalType.ALERT
        assert result.confidence > 0

    def test_missing_layer_veto(self):
        signals = [
            _signal("alfa1", SignalType.ALERT),
            _signal("beta1", SignalType.ALERT),
        ]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is False
        assert result.veto_active is True
        assert "Missing" in result.veto_reason

    def test_no_consensus_mixed_signals(self):
        signals = [
            _signal("alfa1", SignalType.ALERT),
            _signal("beta1", SignalType.NEUTRAL),
            _signal("alfa2", SignalType.ALERT),
            _signal("beta2", SignalType.NEUTRAL),
            _signal("delta", SignalType.NEUTRAL),
        ]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is False


# ── CryptoPadre Consensus ───────────────────────────────────────────


class TestCryptoPadreConsensus:

    def setup_method(self):
        self.padre = CryptoPadre()

    def test_bullish_consensus(self):
        signals = [
            _signal("alfa_crypto", SignalType.BULLISH, 0.7),
            _signal("beta_crypto", SignalType.BULLISH, 0.8),
            _signal("delta_crypto", SignalType.NEUTRAL, 0.5),
        ]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is True
        assert result.final_signal == SignalType.BULLISH

    def test_bearish_consensus(self):
        signals = [
            _signal("alfa_crypto", SignalType.BEARISH, 0.7),
            _signal("beta_crypto", SignalType.BEARISH, 0.8),
            _signal("delta_crypto", SignalType.BEARISH, 0.9),
        ]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is True
        assert result.final_signal == SignalType.BEARISH

    def test_insufficient_layers_veto(self):
        signals = [_signal("alfa_crypto", SignalType.BULLISH)]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is False
        assert result.veto_active is True

    def test_conflicting_signals_no_consensus(self):
        signals = [
            _signal("alfa_crypto", SignalType.BULLISH),
            _signal("beta_crypto", SignalType.BEARISH),
            _signal("delta_crypto", SignalType.NEUTRAL),
        ]
        result = self.padre.evaluate_consensus(signals)
        assert result.consensus_reached is False

    def test_position_size_on_consensus(self):
        signals = [
            _signal("alfa_crypto", SignalType.BULLISH, 0.8),
            _signal("beta_crypto", SignalType.BULLISH, 0.8),
            _signal("delta_crypto", SignalType.BULLISH, 0.8),
        ]
        result = self.padre.evaluate_consensus(signals)
        size = self.padre.position_size(result, portfolio_value=100000)
        assert size == pytest.approx(100000 * 0.05 * 0.8, abs=1)

    def test_position_size_no_consensus(self):
        result = ConsensusResult(
            consensus_reached=False, final_signal=SignalType.NEUTRAL,
            confidence=0.5, agent_signals=[],
        )
        assert self.padre.position_size(result, 100000) == 0.0


# ── AlfaCryptoAgent ──────────────────────────────────────────────────


class TestAlfaCryptoAgent:

    def setup_method(self):
        self.agent = AlfaCryptoAgent()

    def test_no_signal_without_data(self):
        signal = self.agent.analyze()
        assert signal.signal_type == SignalType.NO_SIGNAL

    def test_health_check_no_data(self):
        assert self.agent.health_check() is False

    def test_ingest_sets_dominance(self):
        self.agent.ingest({
            "btc_market_cap": 500_000_000,
            "total_market_cap": 1_000_000_000,
        })
        assert self.agent._dominance_ratios["btc"] == pytest.approx(0.5)

    def test_analyze_with_price_data(self):
        rng = np.random.default_rng(42)
        n = 50
        df = pd.DataFrame({
            "btc_usdt": 50000 + rng.normal(0, 100, n),
            "eth_usdt": 3000 + rng.normal(0, 50, n),
        })
        self.agent.ingest({"price_dataframe": df})
        signal = self.agent.analyze()
        assert signal.signal_type in (
            SignalType.BULLISH, SignalType.BEARISH, SignalType.NEUTRAL
        )

    def test_tracked_pairs_count(self):
        assert len(AlfaCryptoAgent.TRACKED_PAIRS) == 8
        assert "BTC/USDT" in AlfaCryptoAgent.TRACKED_PAIRS
