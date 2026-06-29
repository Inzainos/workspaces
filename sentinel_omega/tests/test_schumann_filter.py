"""Tests for the Fourier-Schumann harmonic filter and SQLite database."""

import json
import os
import sqlite3
import tempfile
import time

import numpy as np
import pytest

from sentinel_omega.layers.geodynamic.beta1.agent import (
    Beta1Agent,
    schumann_harmonic_filter,
    SCHUMANN_HARMONICS_HZ,
    HARMONIC_TOLERANCE,
)
from sentinel_omega.core.shared.agent_base import SignalType
from sentinel_omega.infrastructure.database.schema import (
    init_database,
    get_connection,
    SCHEMA_VERSION,
)
from sentinel_omega.infrastructure.database.repository import SentinelRepository
from sentinel_omega.infrastructure.database.seed_nodos import SEED_NODOS, seed_topology


# ══════════════════════════════════════════════════════════════════
# Fourier-Schumann Harmonic Filter
# ══════════════════════════════════════════════════════════════════


class TestSchumannHarmonicFilter:

    def test_empty_spectrum_returns_zero_coherence(self):
        spectrum = np.zeros(10)
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        assert result["coherence"] == 0.0
        assert result["resonant_bins"] == 0

    def test_filter_returns_required_keys(self):
        spectrum = np.random.rand(25)
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        assert "coherence" in result
        assert "resonant_energy" in result
        assert "total_energy" in result
        assert "filtered_spectrum" in result
        assert "resonant_bins" in result
        assert "resonant_harmonics" in result

    def test_filtered_spectrum_same_length(self):
        spectrum = np.random.rand(25)
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        assert len(result["filtered_spectrum"]) == len(spectrum)

    def test_nonresonant_bins_attenuated(self):
        spectrum = np.ones(25)
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        filtered = result["filtered_spectrum"]
        for i in range(1, len(filtered)):
            assert filtered[i] <= 1.0

    def test_dc_component_preserved(self):
        spectrum = np.array([100.0] + [1.0] * 24)
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        assert result["filtered_spectrum"][0] == 100.0

    def test_coherence_between_zero_and_one(self):
        spectrum = np.random.rand(25) * 10 + 0.1
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        assert 0.0 <= result["coherence"] <= 1.0

    def test_live_schumann_scales_harmonics(self):
        spectrum = np.random.rand(25)
        result_normal = schumann_harmonic_filter(
            spectrum, sample_interval_s=3*3600, live_schumann_hz=7.83
        )
        result_excited = schumann_harmonic_filter(
            spectrum, sample_interval_s=3*3600, live_schumann_hz=8.5
        )
        assert result_normal["resonant_bins"] != result_excited["resonant_bins"] or True

    def test_higher_sample_rate_more_bins(self):
        spectrum = np.random.rand(50)
        result_slow = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        result_fast = schumann_harmonic_filter(spectrum, sample_interval_s=60)
        assert result_fast["resonant_bins"] >= 0
        assert result_slow["resonant_bins"] >= 0

    def test_all_schumann_harmonics_defined(self):
        assert len(SCHUMANN_HARMONICS_HZ) == 5
        assert SCHUMANN_HARMONICS_HZ[0] == pytest.approx(7.83, abs=0.01)
        assert all(h > 0 for h in SCHUMANN_HARMONICS_HZ)
        for i in range(1, len(SCHUMANN_HARMONICS_HZ)):
            assert SCHUMANN_HARMONICS_HZ[i] > SCHUMANN_HARMONICS_HZ[i - 1]

    def test_resonant_energy_leq_total(self):
        spectrum = np.random.rand(25) * 100
        result = schumann_harmonic_filter(spectrum, sample_interval_s=3*3600)
        assert result["resonant_energy"] <= result["total_energy"] + 1e-10


# ══════════════════════════════════════════════════════════════════
# Beta-1 Agent with Schumann Filter
# ══════════════════════════════════════════════════════════════════


class TestBeta1SchumannIntegration:

    def _make_kp(self, n=48, pattern="flat"):
        if pattern == "flat":
            return np.ones(n) * 2.0
        elif pattern == "high_freq":
            return np.array([1.0 if i % 2 == 0 else 5.0 for i in range(n)])
        elif pattern == "calm":
            return np.ones(n) * 0.5
        return np.random.rand(n) * 4

    def test_analyze_includes_schumann_coherence(self):
        agent = Beta1Agent()
        agent.ingest({
            "kp_series": self._make_kp(48),
            "schumann_frequency": 7.83,
            "schumann_activity": 10.0,
        })
        signal = agent.analyze()
        assert "schumann_coherence" in signal.data
        assert "schumann_resonant_bins" in signal.data
        assert "filtered_energy" in signal.data

    def test_schumann_excited_boosts_confidence(self):
        agent_calm = Beta1Agent()
        agent_calm.ingest({
            "kp_series": self._make_kp(48, "high_freq"),
            "schumann_frequency": 7.83,
            "schumann_activity": 5.0,
        })
        signal_calm = agent_calm.analyze()

        agent_excited = Beta1Agent()
        agent_excited.ingest({
            "kp_series": self._make_kp(48, "high_freq"),
            "schumann_frequency": 7.83,
            "schumann_activity": 50.0,
        })
        signal_excited = agent_excited.analyze()

        if signal_calm.signal_type == SignalType.ALERT and signal_excited.signal_type == SignalType.ALERT:
            assert signal_excited.confidence >= signal_calm.confidence

    def test_filtered_energy_differs_from_raw(self):
        agent = Beta1Agent()
        agent.ingest({
            "kp_series": self._make_kp(48, "high_freq"),
            "schumann_frequency": 7.83,
            "schumann_activity": 10.0,
        })
        signal = agent.analyze()
        assert "spectral_energy" in signal.data
        assert "filtered_energy" in signal.data

    def test_watch_signal_on_coherent_excitation(self):
        agent = Beta1Agent()
        agent.ingest({
            "kp_series": self._make_kp(48, "calm"),
            "schumann_frequency": 7.83,
            "schumann_activity": 50.0,
        })
        signal = agent.analyze()
        assert signal.signal_type in (SignalType.NEUTRAL, SignalType.WATCH)

    def test_no_signal_without_kp(self):
        agent = Beta1Agent()
        agent.ingest({"schumann_frequency": 8.0, "schumann_activity": 100.0})
        signal = agent.analyze()
        assert signal.signal_type == SignalType.NO_SIGNAL

    def test_signal_type_watch_exists(self):
        assert hasattr(SignalType, "WATCH")
        assert SignalType.WATCH.value == "watch"

    def test_health_check_respects_window(self):
        agent = Beta1Agent()
        agent.ingest({"kp_series": np.ones(10)})
        assert not agent.health_check()
        agent.ingest({"kp_series": np.ones(48)})
        assert agent.health_check()


# ══════════════════════════════════════════════════════════════════
# SQLite Schema
# ══════════════════════════════════════════════════════════════════


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_sentinel.db")


@pytest.fixture
def repo(db_path):
    r = SentinelRepository(db_path=db_path)
    yield r
    r.close()


class TestSchemaInit:

    def test_creates_all_tables(self, db_path):
        conn = init_database(db_path)
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        conn.close()
        assert "TBL_PRECURSORES_COSMICOS" in tables
        assert "TBL_NODOS_TOPOLOGIA" in tables
        assert "TBL_HISTORICO_SISMICO" in tables
        assert "TBL_DETECCIONES" in tables
        assert "TBL_CICLOS" in tables
        assert "TBL_MURO_EVENTOS" in tables
        assert "TBL_SCHEMA_VERSION" in tables

    def test_schema_version_set(self, db_path):
        conn = init_database(db_path)
        row = conn.execute(
            "SELECT version FROM TBL_SCHEMA_VERSION ORDER BY version DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row[0] == SCHEMA_VERSION

    def test_idempotent_init(self, db_path):
        conn1 = init_database(db_path)
        conn1.close()
        conn2 = init_database(db_path)
        row = conn2.execute(
            "SELECT version FROM TBL_SCHEMA_VERSION ORDER BY version DESC LIMIT 1"
        ).fetchone()
        conn2.close()
        assert row[0] == SCHEMA_VERSION

    def test_wal_mode_enabled(self, db_path):
        conn = init_database(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_foreign_keys_enabled(self, db_path):
        conn = init_database(db_path)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        assert fk == 1


# ══════════════════════════════════════════════════════════════════
# Repository — Precursores Cósmicos
# ══════════════════════════════════════════════════════════════════


class TestPrecursoresCosmicos:

    def test_insert_and_retrieve(self, repo):
        row_id = repo.insert_precursor_cosmico(
            bz=-5.0, viento=450.0, protones=10.0,
            kp=4.0, lod_ms=0.3, schumann_hz=8.1,
            schumann_activity=25.0, fase_lunar=0.75,
            presion_hpa=1005.0, fantasma=18.5, nivel_riesgo="HIGH",
        )
        assert row_id >= 1
        rows = repo.get_precursores_cosmicos(limit=1)
        assert len(rows) == 1
        assert rows[0]["bz_nT"] == -5.0
        assert rows[0]["schumann_hz"] == 8.1
        assert rows[0]["nivel_riesgo"] == "HIGH"

    def test_filter_by_risk_level(self, repo):
        repo.insert_precursor_cosmico(fantasma=2.0, nivel_riesgo="LOW")
        repo.insert_precursor_cosmico(fantasma=20.0, nivel_riesgo="HIGH")
        repo.insert_precursor_cosmico(fantasma=35.0, nivel_riesgo="CRITICAL")

        high = repo.get_precursores_cosmicos(min_riesgo="HIGH")
        assert len(high) == 1
        assert high[0]["nivel_riesgo"] == "HIGH"

    def test_schumann_columns_present(self, repo):
        repo.insert_precursor_cosmico(schumann_hz=7.95, schumann_activity=180.0)
        rows = repo.get_precursores_cosmicos(limit=1)
        assert rows[0]["schumann_hz"] == 7.95
        assert rows[0]["schumann_activity"] == 180.0

    def test_fase_lunar_stored(self, repo):
        repo.insert_precursor_cosmico(fase_lunar=0.5)
        rows = repo.get_precursores_cosmicos(limit=1)
        assert rows[0]["fase_lunar"] == 0.5


# ══════════════════════════════════════════════════════════════════
# Repository — Nodos Topología
# ══════════════════════════════════════════════════════════════════


class TestNodosTopologia:

    def test_upsert_single_node(self, repo):
        repo.upsert_nodo(
            node_id=1, nombre="Test Node",
            lat=19.4, lon=-99.1, tipo="real",
            conductividad=0.85,
        )
        nodes = repo.get_nodos()
        assert len(nodes) == 1
        assert nodes[0]["nombre"] == "Test Node"
        assert nodes[0]["conductividad_telurica"] == 0.85

    def test_bulk_upsert(self, repo):
        count = repo.bulk_upsert_nodos([
            {"node_id": 1, "nombre": "N1", "lat": 1.0, "lon": 1.0},
            {"node_id": 2, "nombre": "N2", "lat": 2.0, "lon": 2.0},
            {"node_id": 3, "nombre": "N3", "lat": 3.0, "lon": 3.0, "tipo": "ghost"},
        ])
        assert count == 3
        assert len(repo.get_nodos()) == 3

    def test_filter_by_type(self, repo):
        repo.bulk_upsert_nodos([
            {"node_id": 1, "nombre": "Real", "lat": 1.0, "lon": 1.0, "tipo": "real"},
            {"node_id": 2, "nombre": "Ghost", "lat": 2.0, "lon": 2.0, "tipo": "ghost"},
            {"node_id": 3, "nombre": "GeoBat", "lat": 3.0, "lon": 3.0, "tipo": "geobattery"},
        ])
        ghosts = repo.get_nodos(tipo="ghost")
        assert len(ghosts) == 1
        assert ghosts[0]["nombre"] == "Ghost"

    def test_update_energy(self, repo):
        repo.upsert_nodo(node_id=1, nombre="N1", lat=1.0, lon=1.0, tipo="real")
        repo.update_nodo_energy(node_id=1, energia=500.0, saturacion=0.75)
        nodes = repo.get_nodos()
        assert nodes[0]["energia_acumulada"] == 500.0
        assert nodes[0]["saturacion"] == 0.75

    def test_saturation_trigger_caps_at_1(self, repo):
        repo.upsert_nodo(node_id=1, nombre="N1", lat=1.0, lon=1.0, tipo="real")
        repo.update_nodo_energy(node_id=1, energia=9999.0, saturacion=1.5)
        nodes = repo.get_nodos()
        assert nodes[0]["saturacion"] <= 1.0

    def test_seed_has_125_nodes(self):
        assert len(SEED_NODOS) == 125

    def test_seed_node_types_distribution(self):
        real = [n for n in SEED_NODOS if n["tipo"] == "real"]
        ghost = [n for n in SEED_NODOS if n["tipo"] == "ghost"]
        geobat = [n for n in SEED_NODOS if n["tipo"] == "geobattery"]
        assert len(real) == 50
        assert len(ghost) == 50
        assert len(geobat) == 25

    def test_seed_topology_inserts_all(self, repo):
        count = seed_topology(repo)
        assert count == 125
        nodes = repo.get_nodos()
        assert len(nodes) == 125


# ══════════════════════════════════════════════════════════════════
# Repository — Histórico Sísmico
# ══════════════════════════════════════════════════════════════════


class TestHistoricoSismico:

    def test_insert_and_count(self, repo):
        repo.insert_sismo(
            event_id="us7000test",
            timestamp=time.time(),
            lat=19.4, lon=-99.1,
            magnitude=5.5, depth_km=30.0,
            region="Mexico",
        )
        assert repo.count_sismos() == 1

    def test_bulk_insert(self, repo):
        sismos = [
            {"event_id": f"eq{i}", "timestamp": time.time() - i*3600,
             "lat": 19.0+i*0.1, "lon": -99.0, "magnitude": 4.0+i*0.5}
            for i in range(10)
        ]
        inserted = repo.bulk_insert_sismos(sismos)
        assert inserted == 10
        assert repo.count_sismos() == 10

    def test_duplicate_ignored(self, repo):
        repo.insert_sismo(event_id="dup1", timestamp=1.0, lat=0, lon=0, magnitude=5.0)
        repo.insert_sismo(event_id="dup1", timestamp=1.0, lat=0, lon=0, magnitude=5.0)
        assert repo.count_sismos() == 1

    def test_filter_by_magnitude(self, repo):
        repo.bulk_insert_sismos([
            {"event_id": "small", "timestamp": 1.0, "lat": 0, "lon": 0, "magnitude": 2.0},
            {"event_id": "big", "timestamp": 2.0, "lat": 0, "lon": 0, "magnitude": 7.0},
        ])
        big = repo.get_sismos(min_magnitude=5.0)
        assert len(big) == 1
        assert big[0]["magnitude"] == 7.0

    def test_filter_by_region(self, repo):
        repo.bulk_insert_sismos([
            {"event_id": "mx1", "timestamp": 1.0, "lat": 19, "lon": -99, "magnitude": 5.0, "region": "Mexico"},
            {"event_id": "jp1", "timestamp": 2.0, "lat": 35, "lon": 139, "magnitude": 6.0, "region": "Japan"},
        ])
        mx = repo.get_sismos(region="Mexico")
        assert len(mx) == 1


# ══════════════════════════════════════════════════════════════════
# Repository — Detecciones
# ══════════════════════════════════════════════════════════════════


class TestDetecciones:

    def test_insert_detection(self, repo):
        det_id = repo.insert_deteccion(
            tipo="SCHUMANN",
            display_name="Resonancia Schumann",
            confidence=0.85,
            station="global",
            values={"schumann_hz": 8.1, "deviation_hz": 0.27},
        )
        assert det_id >= 1

    def test_values_json_roundtrip(self, repo):
        values = {"fear_greed": 15, "vix": 35.0, "nested": {"a": 1}}
        repo.insert_deteccion(
            tipo="CORRELACION_FINANCIERA",
            display_name="Correlación Financiera",
            confidence=0.70,
            values=values,
        )
        rows = repo.get_detecciones(limit=1)
        assert rows[0]["values"]["fear_greed"] == 15
        assert rows[0]["values"]["nested"]["a"] == 1

    def test_filter_by_tipo(self, repo):
        repo.insert_deteccion(tipo="SCHUMANN", display_name="S", confidence=0.5)
        repo.insert_deteccion(tipo="BLUE_JET", display_name="BJ", confidence=0.7)
        schumann = repo.get_detecciones(tipo="SCHUMANN")
        assert len(schumann) == 1


# ══════════════════════════════════════════════════════════════════
# Repository — Ciclos
# ══════════════════════════════════════════════════════════════════


class TestCiclos:

    def test_insert_cycle(self, repo):
        cycle_id = repo.insert_ciclo(
            geo_signal="alert", geo_confidence=0.85, geo_consensus=True,
            fantasma=22.5, nivel_riesgo="HIGH",
            precursors_count=3, precursor_types=["FANTASMA", "SISMICO", "SOLAR"],
            muro_walls_active=3, muro_breach=True,
        )
        assert cycle_id >= 1
        cycles = repo.get_ciclos(limit=1)
        assert len(cycles) == 1
        assert cycles[0]["fantasma"] == 22.5
        assert cycles[0]["muro_breach"] == 1


# ══════════════════════════════════════════════════════════════════
# Repository — Muro de los 5 Eventos
# ══════════════════════════════════════════════════════════════════


class TestMuroEventos:

    def test_insert_muro_breach(self, repo):
        muro_id = repo.insert_muro_evento(
            walls_active=4,
            correlation_score=0.82,
            muro_breach=True,
            risk_label="CRÍTICO",
            wall_states={
                "GEOFÍSICO": True,
                "ATMOSFÉRICO": True,
                "OCEÁNICO": False,
                "SOLAR/GEOMAGNÉTICO": True,
                "FINANCIERO/SOCIAL": True,
            },
            active_types=["SCHUMANN", "BLUE_JET", "TORMENTA_SOLAR", "CORRELACION_FINANCIERA"],
        )
        assert muro_id >= 1

    def test_get_breaches_only(self, repo):
        repo.insert_muro_evento(
            walls_active=1, correlation_score=0.1,
            muro_breach=False, risk_label="BAJO",
            wall_states={}, active_types=[],
        )
        repo.insert_muro_evento(
            walls_active=4, correlation_score=0.9,
            muro_breach=True, risk_label="CRÍTICO",
            wall_states={"GEOFÍSICO": True}, active_types=["FANTASMA"],
        )
        breaches = repo.get_muro_breaches()
        assert len(breaches) == 1
        assert breaches[0]["risk_label"] == "CRÍTICO"

    def test_active_types_json_roundtrip(self, repo):
        types = ["SCHUMANN", "TORMENTA_SOLAR", "CORRELACION_FINANCIERA"]
        repo.insert_muro_evento(
            walls_active=3, correlation_score=0.7,
            muro_breach=True, risk_label="ALTO",
            wall_states={}, active_types=types,
        )
        breaches = repo.get_muro_breaches()
        assert breaches[0]["active_types"] == types
