"""Tests for data pipeline, layer runners, and legacy data loader."""

import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

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
from sentinel_omega.core.shared.agent_base import SignalType


# ── Helpers ────────────────────────────────────────────────────────


def _mock_kp_df():
    return pd.DataFrame({
        "time_tag": pd.date_range("2024-01-01", periods=100, freq="3h"),
        "kp_index": np.random.uniform(0, 5, 100),
    })


def _mock_mag_df():
    return pd.DataFrame({
        "time_tag": pd.date_range("2024-01-01", periods=100, freq="1min"),
        "bz_gsm": np.random.uniform(-10, 5, 100),
    })


def _mock_wind_df():
    return pd.DataFrame({
        "time_tag": pd.date_range("2024-01-01", periods=100, freq="1min"),
        "proton_speed": np.random.uniform(300, 600, 100),
        "proton_density": np.random.uniform(2, 10, 100),
    })


def _mock_eq_df():
    return pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=20, freq="1D"),
        "magnitude": np.random.uniform(4.0, 7.0, 20),
        "place": [f"City {i}, Region {i % 5}" for i in range(20)],
        "depth_km": np.random.uniform(5, 100, 20),
        "longitude": np.random.uniform(-180, 180, 20),
        "latitude": np.random.uniform(-90, 90, 20),
        "type": ["earthquake"] * 20,
    })


def _mock_binance_df():
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=90, freq="1D"),
        "open": np.random.uniform(40000, 50000, 90),
        "high": np.random.uniform(40000, 50000, 90),
        "low": np.random.uniform(40000, 50000, 90),
        "close": np.random.uniform(40000, 50000, 90),
        "volume": np.random.uniform(1000, 5000, 90),
    })


def _mock_yahoo_df():
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=200, freq="1D"),
        "open": np.random.uniform(140, 180, 200),
        "high": np.random.uniform(140, 180, 200),
        "low": np.random.uniform(140, 180, 200),
        "close": np.random.uniform(140, 180, 200),
        "volume": np.random.uniform(50e6, 100e6, 200),
    })


# ── Geodynamic Pipeline ───────────────────────────────────────────


class TestGeodynamicPipeline:

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_solar_wind")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_mag_field")
    def test_alfa1_data(self, mock_mag, mock_wind):
        mock_mag.return_value = _mock_mag_df()
        mock_wind.return_value = _mock_wind_df()

        pipe = GeodynamicPipeline()
        data = pipe.fetch_alfa1_data()
        assert "omni_dataframe" in data
        df = data["omni_dataframe"]
        assert "bz_gsm" in df.columns

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_schumann_resonance")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_earthquakes")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_kp_index")
    def test_beta1_data(self, mock_kp, mock_eq, mock_schumann):
        mock_kp.return_value = _mock_kp_df()
        mock_eq.return_value = _mock_eq_df()
        mock_schumann.return_value = (8.12, 3.5)

        pipe = GeodynamicPipeline()
        data = pipe.fetch_beta1_data()
        assert "kp_series" in data
        assert len(data["kp_series"]) == 100
        assert "seismic_magnitudes" in data
        assert data["schumann_frequency"] == 8.12
        assert data["schumann_activity"] == 3.5

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_fear_greed_index")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_earthquakes")
    def test_delta_data(self, mock_eq, mock_fg):
        mock_eq.return_value = _mock_eq_df()
        mock_fg.return_value = {"value": 25, "classification": "Extreme Fear"}

        pipe = GeodynamicPipeline()
        data = pipe.fetch_delta_data()
        assert "energetic_nodes" in data
        assert len(data["energetic_nodes"]) > 0
        assert data["psychosocial_index"] == pytest.approx(0.25)

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_mag_field")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_solar_wind")
    def test_alfa1_no_data(self, mock_wind, mock_mag):
        mock_mag.return_value = None
        mock_wind.return_value = None

        pipe = GeodynamicPipeline()
        data = pipe.fetch_alfa1_data()
        assert data == {}


# ── Crypto Pipeline ────────────────────────────────────────────────


class TestCryptoPipeline:

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_coingecko_dominance")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_binance_klines")
    def test_alfa_data(self, mock_klines, mock_dom):
        mock_klines.return_value = _mock_binance_df()
        mock_dom.return_value = {"btc": 54.0, "eth": 17.0}

        pipe = CryptoPipeline()
        data = pipe.fetch_alfa_data(days=90)
        assert "price_dataframe" in data
        assert "btc_market_cap" in data
        assert data["btc_market_cap"] > 0

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_binance_klines")
    def test_beta_data(self, mock_klines):
        mock_klines.return_value = _mock_binance_df()

        pipe = CryptoPipeline()
        data = pipe.fetch_beta_data()
        assert "volume_series" in data
        assert "whale_transaction_ratio" in data

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_fear_greed_index")
    def test_delta_data(self, mock_fg):
        mock_fg.return_value = {"value": 75, "classification": "Greed"}

        pipe = CryptoPipeline()
        data = pipe.fetch_delta_data()
        assert data["fear_greed_index"] == 75


# ── Bolsa Pipeline ─────────────────────────────────────────────────


class TestBolsaPipeline:

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_yahoo_quote")
    def test_alfa_data(self, mock_yahoo):
        mock_yahoo.return_value = _mock_yahoo_df()

        pipe = BolsaPipeline()
        data = pipe.fetch_alfa_data("AAPL", "SPY")
        assert "stock_ohlcv" in data
        assert "index_ohlcv" in data

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_yield_spread")
    def test_beta_data(self, mock_spread):
        mock_spread.return_value = 1.5

        pipe = BolsaPipeline()
        data = pipe.fetch_beta_data()
        assert data["yield_spread_10y_2y"] == 1.5
        assert data["interest_rate"] > 0

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_sector_etfs")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_vix")
    def test_delta_data(self, mock_vix, mock_sectors):
        mock_vix.return_value = pd.DataFrame({
            "close": [18.5, 19.0, 20.0],
            "volume": [1e6, 1.1e6, 1.2e6],
        })
        mock_sectors.return_value = {
            "XLK": pd.DataFrame({"close": [200.0], "volume": [5e6]}),
            "XLF": pd.DataFrame({"close": [40.0], "volume": [8e6]}),
        }

        pipe = BolsaPipeline()
        data = pipe.fetch_delta_data()
        assert data["vix"] == pytest.approx(20.0)
        assert len(data["sector_market_caps"]) == 2


# ── Layer Runners ──────────────────────────────────────────────────


class TestLayerRunners:

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_schumann_resonance")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_fear_greed_index")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_earthquakes")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_kp_index")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_solar_wind")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_mag_field")
    def test_geodynamic_runner(self, mock_mag, mock_wind, mock_kp, mock_eq, mock_fg, mock_schumann):
        mock_mag.return_value = _mock_mag_df()
        mock_wind.return_value = _mock_wind_df()
        mock_kp.return_value = _mock_kp_df()
        mock_eq.return_value = _mock_eq_df()
        mock_fg.return_value = {"value": 50, "classification": "Neutral"}
        mock_schumann.return_value = (7.95, 1.2)

        runner = GeodynamicLayerRunner()
        consensus = runner.run()
        assert consensus is not None
        assert consensus.final_signal in SignalType

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_fear_greed_index")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_coingecko_dominance")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_binance_klines")
    def test_crypto_runner(self, mock_klines, mock_dom, mock_fg):
        mock_klines.return_value = _mock_binance_df()
        mock_dom.return_value = {"btc": 54.0}
        mock_fg.return_value = {"value": 30, "classification": "Fear"}

        runner = CryptoLayerRunner(days=90)
        consensus = runner.run()
        assert consensus is not None
        assert consensus.final_signal in SignalType

    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_sector_etfs")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_vix")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_yield_spread")
    @patch("sentinel_omega.infrastructure.pipeline.data_pipeline.fetch_yahoo_quote")
    def test_bolsa_runner(self, mock_yahoo, mock_spread, mock_vix, mock_sectors):
        mock_yahoo.return_value = _mock_yahoo_df()
        mock_spread.return_value = 0.8
        mock_vix.return_value = pd.DataFrame({
            "close": [22.0], "volume": [1e6],
        })
        mock_sectors.return_value = {
            "XLK": pd.DataFrame({"close": [200.0], "volume": [5e6]}),
            "XLF": pd.DataFrame({"close": [40.0], "volume": [8e6]}),
            "XLE": pd.DataFrame({"close": [80.0], "volume": [3e6]}),
        }

        runner = BolsaLayerRunner(symbol="AAPL", index_symbol="SPY")
        consensus = runner.run()
        assert consensus is not None
        assert consensus.final_signal in SignalType


# ── Legacy Data Loader ─────────────────────────────────────────────


class TestLegacyDataLoader:

    @pytest.fixture
    def cerebro_db(self, tmp_path):
        db_path = tmp_path / "cerebro.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE historicos (
                id INTEGER PRIMARY KEY,
                fecha TEXT,
                sismo_max_mag REAL,
                promedio_kp REAL,
                promedio_tomsk REAL,
                so2_mass REAL,
                co_flux REAL,
                temp_max REAL,
                presion_atm REAL
            )
        """)
        for i in range(100):
            conn.execute(
                "INSERT INTO historicos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (i, f"2024-01-{(i % 28) + 1:02d}", 4.0 + i * 0.01,
                 2.0 + i * 0.01, 7.83, 0.0, 0.0, 20.0, 1013.0),
            )
        conn.execute("""
            CREATE TABLE bitacora (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                fecha TEXT,
                v_fantasma REAL,
                kp REAL,
                bz REAL,
                tomsk_val REAL,
                viento REAL,
                riesgo_ia REAL,
                energia_latente REAL
            )
        """)
        conn.execute(
            "INSERT INTO bitacora VALUES (1, 1704067200.0, '2024-01-01', "
            "100.0, 3.0, -2.5, 7.83, 400.0, 2.0, 5000.0)"
        )
        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def titan_db(self, tmp_path):
        db_path = tmp_path / "titan.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE MELATE (
                id INTEGER PRIMARY KEY,
                r1 INT, r2 INT, r3 INT, r4 INT, r5 INT, r6 INT, r7 INT, r8 INT
            )
        """)
        for i in range(50):
            conn.execute(
                "INSERT INTO MELATE VALUES (?, 40, ?, ?, ?, ?, ?, 0, 0)",
                (i, 1 + i % 20, 5 + i % 15, 10 + i % 10, 25 + i % 5, 30 + i % 8),
            )
        conn.execute("""
            CREATE TABLE weights_melate (
                number INTEGER, weight REAL, last_updated TEXT
            )
        """)
        conn.execute(
            "INSERT INTO weights_melate VALUES (7, 9.1e21, '2024-01-01')"
        )
        conn.commit()
        conn.close()
        return db_path

    def test_list_tables(self, cerebro_db):
        loader = LegacyDataLoader(str(cerebro_db))
        tables = loader.list_tables()
        assert "historicos" in tables
        assert "bitacora" in tables

    def test_table_info(self, cerebro_db):
        loader = LegacyDataLoader(str(cerebro_db))
        info = loader.table_info("historicos")
        assert info["row_count"] == 100
        col_names = [c[0] for c in info["columns"]]
        assert "sismo_max_mag" in col_names

    def test_load_historicos(self, cerebro_db):
        loader = LegacyDataLoader(str(cerebro_db))
        df = loader.load_historicos()
        assert len(df) == 100
        assert "sismo_max_mag" in df.columns

    def test_load_historicos_filtered(self, cerebro_db):
        loader = LegacyDataLoader(str(cerebro_db))
        df = loader.load_historicos(start_date="2024-01-10")
        assert len(df) < 100

    def test_load_bitacora(self, cerebro_db):
        loader = LegacyDataLoader(str(cerebro_db))
        df = loader.load_bitacora()
        assert len(df) == 1
        assert "v_fantasma" in df.columns

    def test_historicos_to_snt_input(self, cerebro_db):
        loader = LegacyDataLoader(str(cerebro_db))
        arrays = loader.historicos_to_snt_input()
        assert "kp" in arrays
        assert "sismo_max_mag" in arrays
        assert len(arrays["kp"]) == 100

    def test_load_lottery_game(self, titan_db):
        loader = LegacyDataLoader(str(titan_db))
        df = loader.load_lottery_game("MELATE")
        assert len(df) == 50
        assert "r1" in df.columns

    def test_load_lottery_weights(self, titan_db):
        loader = LegacyDataLoader(str(titan_db))
        df = loader.load_lottery_weights("melate")
        assert len(df) == 1
        assert df.iloc[0]["number"] == 7

    def test_missing_db(self):
        with pytest.raises(FileNotFoundError):
            LegacyDataLoader("/nonexistent/path.db")


# ── Schumann / Tomsk WPC ─────────────────────────────────────────


class TestSchumannConnector:

    @patch("sentinel_omega.infrastructure.api.schumann.requests.get")
    def test_fetch_spectrogram(self, mock_get):
        from sentinel_omega.infrastructure.api.schumann import fetch_schumann_spectrogram

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        path = fetch_schumann_spectrogram()
        assert path is not None
        import os
        assert os.path.exists(path)
        os.remove(path)

    @patch("sentinel_omega.infrastructure.api.schumann.requests.get")
    def test_fetch_spectrogram_failure(self, mock_get):
        from sentinel_omega.infrastructure.api.schumann import fetch_schumann_spectrogram

        mock_get.side_effect = Exception("Network error")
        path = fetch_schumann_spectrogram()
        assert path is None

    def test_analyze_missing_image(self):
        from sentinel_omega.infrastructure.api.schumann import analyze_spectrogram

        hz, pct = analyze_spectrogram("/nonexistent/image.jpg")
        assert hz == 7.83
        assert pct == 0.0

    def test_analyze_none_path(self):
        from sentinel_omega.infrastructure.api.schumann import analyze_spectrogram

        hz, pct = analyze_spectrogram(None)
        assert hz == 7.83
        assert pct == 0.0

    @patch("sentinel_omega.infrastructure.api.schumann.fetch_schumann_spectrogram")
    @patch("sentinel_omega.infrastructure.api.schumann.analyze_spectrogram")
    def test_full_pipeline(self, mock_analyze, mock_fetch):
        from sentinel_omega.infrastructure.api.schumann import fetch_schumann_resonance

        mock_fetch.return_value = "/tmp/fake.jpg"
        mock_analyze.return_value = (8.5, 12.0)

        hz, pct = fetch_schumann_resonance(cleanup=False)
        assert hz == 8.5
        assert pct == 12.0

    @patch("sentinel_omega.infrastructure.api.schumann.fetch_schumann_spectrogram")
    def test_full_pipeline_no_download(self, mock_fetch):
        from sentinel_omega.infrastructure.api.schumann import fetch_schumann_resonance

        mock_fetch.return_value = None
        hz, pct = fetch_schumann_resonance()
        assert hz == 7.83
        assert pct == 0.0
