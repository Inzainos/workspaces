"""Tests for infrastructure: Telegram bot, data pipeline, config, orchestrator."""

import sqlite3
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from sentinel_omega.infrastructure.telegram.bot import SentinelTelegramBot, TelegramMessage
from sentinel_omega.core.shared.data_pipeline import (
    DatabaseManager,
    IngestionConfig,
    FILL_SENTINEL,
)
from sentinel_omega.config.sentinel_config import (
    SentinelOmegaConfig,
    LayerConfig,
    DatabaseConfig,
    SNTConfig,
)
from sentinel_omega.orchestrator import SentinelOrchestrator, SystemStatus
from sentinel_omega.core.shared.agent_base import ConsensusResult, SignalType


# ── TelegramBot ──────────────────────────────────────────────────────


class TestTelegramBot:

    def test_dry_run_no_token(self):
        bot = SentinelTelegramBot(token="", chat_id="")
        msg = TelegramMessage(
            layer="crypto", signal_type="BULLISH", confidence=0.85,
            summary="BTC altcoin convergence detected"
        )
        assert bot.send_alert(msg) is True

    def test_dry_run_with_details(self):
        bot = SentinelTelegramBot(token="", chat_id="")
        msg = TelegramMessage(
            layer="geodynamic", signal_type="ALERT", confidence=0.95,
            summary="Kp surge", details="Kp=7, Bz=-15nT"
        )
        assert bot.send_alert(msg) is True

    def test_layer_emojis_mapping(self):
        assert SentinelTelegramBot.LAYER_EMOJIS["geodynamic"] == "🌍"
        assert SentinelTelegramBot.LAYER_EMOJIS["crypto"] == "₿"
        assert SentinelTelegramBot.LAYER_EMOJIS["bolsa"] == "📈"
        assert SentinelTelegramBot.LAYER_EMOJIS["lottery"] == "🎰"

    def test_unknown_layer_gets_default_emoji(self):
        bot = SentinelTelegramBot(token="", chat_id="")
        msg = TelegramMessage(
            layer="unknown_layer", signal_type="TEST", confidence=0.5,
            summary="test"
        )
        assert bot.send_alert(msg) is True

    def test_send_heartbeat(self):
        bot = SentinelTelegramBot(token="", chat_id="")
        status = {"geodynamic": True, "crypto": True, "bolsa": False}
        assert bot.send_heartbeat(status) is True

    @patch("requests.post")
    def test_send_with_token(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_post.return_value = mock_resp

        bot = SentinelTelegramBot(token="test_token", chat_id="12345")
        msg = TelegramMessage(
            layer="crypto", signal_type="BULLISH", confidence=0.7,
            summary="Test alert"
        )
        assert bot.send_alert(msg) is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "test_token" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["chat_id"] == "12345"

    @patch("requests.post", side_effect=ConnectionError("Network error"))
    def test_send_failure_returns_false(self, mock_post):
        bot = SentinelTelegramBot(token="token", chat_id="123")
        msg = TelegramMessage(layer="crypto", signal_type="TEST", confidence=0.5, summary="fail")
        assert bot.send_alert(msg) is False


# ── DatabaseManager ──────────────────────────────────────────────────


class TestDatabaseManager:

    def test_execute_and_query(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        mgr = DatabaseManager(db_path)
        mgr.execute("CREATE TABLE t (id INTEGER, val REAL)")
        mgr.execute("INSERT INTO t VALUES (1, 3.14)")
        mgr.execute("INSERT INTO t VALUES (2, 2.72)")
        df = mgr.query("SELECT * FROM t")
        assert len(df) == 2
        assert df["val"].iloc[0] == pytest.approx(3.14)

    def test_table_count(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        mgr = DatabaseManager(db_path)
        mgr.execute("CREATE TABLE t (id INTEGER)")
        mgr.execute("INSERT INTO t VALUES (1)")
        mgr.execute("INSERT INTO t VALUES (2)")
        mgr.execute("INSERT INTO t VALUES (3)")
        assert mgr.table_count("t") == 3


# ── IngestionConfig ──────────────────────────────────────────────────


class TestIngestionConfig:

    def test_defaults(self):
        config = IngestionConfig(source_name="test", db_path="test.db", table_name="t")
        assert config.resolution_hours == 6
        assert config.max_gap_hours == 3
        assert config.fill_value == FILL_SENTINEL
        assert config.year_start == 1994
        assert config.year_end == 2024


# ── SentinelOmegaConfig ─────────────────────────────────────────────


class TestConfig:

    def test_default_config(self):
        config = SentinelOmegaConfig()
        assert config.version == "2.5.0-shadow-node"
        assert "Elán" in config.author
        assert len(config.layers) == 4

    def test_lottery_disabled_by_default(self):
        config = SentinelOmegaConfig()
        assert config.layers["lottery"].enabled is False

    def test_active_layers(self):
        config = SentinelOmegaConfig()
        active = [k for k, v in config.layers.items() if v.enabled]
        assert "geodynamic" in active
        assert "crypto" in active
        assert "bolsa" in active
        assert "lottery" not in active

    def test_refresh_intervals(self):
        config = SentinelOmegaConfig()
        assert config.layers["crypto"].refresh_interval_s == 60
        assert config.layers["geodynamic"].refresh_interval_s == 300
        assert config.layers["bolsa"].refresh_interval_s == 900

    def test_snt_config_defaults(self):
        config = SentinelOmegaConfig()
        assert config.snt.friction_pearson_rho == -0.68
        assert config.snt.roche_threshold == 1.0
        assert config.snt.equilibrium_band == 0.1

    def test_coordinates(self):
        config = SentinelOmegaConfig()
        assert config.coordinates["lat"] == pytest.approx(19.31)
        assert config.coordinates["lon"] == pytest.approx(-98.24)

    def test_database_paths(self):
        config = SentinelOmegaConfig()
        assert "SENTINEL_OMEGA_PRO" in config.databases.geodynamic_db
        assert "TITAN_MEMORY" in config.databases.lottery_db


# ── SentinelOrchestrator ────────────────────────────────────────────


class FakeLayer:
    def __init__(self, result):
        self._result = result

    def run(self):
        return self._result


class TestOrchestrator:

    def _config(self):
        return SentinelOmegaConfig()

    def test_register_layer(self):
        orch = SentinelOrchestrator(self._config())
        orch.register_layer("crypto", FakeLayer(None))
        assert "crypto" in orch._layers
        assert orch._status.layer_statuses["crypto"] is True

    def test_register_unknown_layer_raises(self):
        orch = SentinelOrchestrator(self._config())
        with pytest.raises(ValueError, match="Unknown layer"):
            orch.register_layer("quantum", FakeLayer(None))

    def test_register_disabled_layer_skips(self):
        orch = SentinelOrchestrator(self._config())
        orch.register_layer("lottery", FakeLayer(None))
        assert "lottery" not in orch._layers

    def test_run_cycle(self):
        consensus = ConsensusResult(
            consensus_reached=True,
            final_signal=SignalType.BULLISH,
            confidence=0.8,
            agent_signals=[],
        )
        orch = SentinelOrchestrator(self._config())
        orch.register_layer("crypto", FakeLayer(consensus))
        results = orch.run_cycle()
        assert "crypto" in results
        assert results["crypto"].final_signal == SignalType.BULLISH

    def test_run_cycle_handles_layer_error(self):
        class FailLayer:
            def run(self):
                raise RuntimeError("boom")

        orch = SentinelOrchestrator(self._config())
        orch.register_layer("crypto", FailLayer())
        results = orch.run_cycle()
        assert "crypto" not in results
        assert orch._status.layer_statuses["crypto"] is False

    def test_health_check(self):
        orch = SentinelOrchestrator(self._config())
        orch.register_layer("crypto", FakeLayer(None))
        health = orch.health_check()
        assert health["crypto"] is True

    def test_status_uptime(self):
        orch = SentinelOrchestrator(self._config())
        time.sleep(0.05)
        status = orch.get_status()
        assert status.uptime_s >= 0.04
