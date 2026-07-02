"""Tests for the signature engine (firmas) and the Juez auditor."""

import sqlite3
import time

import pytest

from sentinel_omega.infrastructure.database.schema import init_database
from sentinel_omega.core.firmas.signature_engine import (
    FirmaMemoria,
    extraer_features_ventana,
    similitud,
)
from sentinel_omega.core.juez.juez import Juez
from sentinel_omega.infrastructure.pipeline.entrenamiento import (
    entrenar_reconocimiento,
    backtest_disciplinario,
    _event_class,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test_firmas.db")
    conn = init_database(path)
    yield conn, path
    conn.close()


def _features_base(**overrides):
    f = {
        "bz_mean": -3.2, "bz_min": -12.0, "bz_deriv_std": 1.1,
        "viento_avg": 420.0, "viento_max": 610.0,
        "kp_mean": 3.1, "kp_max": 6.0,
        "schumann_mean": 7.9, "schumann_std": 0.2,
        "sismo_count_win": 4.0, "sismo_max_mag_win": 4.8,
        "fase_lunar": 0.92, "es_sicigia": 1.0,
    }
    f.update(overrides)
    return f


# ── Similitud ────────────────────────────────────────────────────────


class TestSimilitud:

    def test_identical_vectors(self):
        f = _features_base()
        assert similitud(f, dict(f)) == pytest.approx(1.0)

    def test_very_different_vectors(self):
        a = _features_base()
        b = _features_base(bz_mean=15.0, bz_min=10.0, kp_mean=0.1,
                           kp_max=0.2, viento_avg=250.0, viento_max=260.0,
                           sismo_count_win=0.0, schumann_mean=14.0)
        assert similitud(a, b) < 0.85

    def test_too_few_shared_dimensions(self):
        assert similitud({"kp_mean": 3.0}, {"kp_mean": 3.0}) == 0.0

    def test_missing_keys_excluded(self):
        a = _features_base()
        b = {k: v for k, v in _features_base().items() if k != "btc_volatilidad"}
        assert similitud(a, b) == pytest.approx(1.0)


# ── FirmaMemoria (promoción) ────────────────────────────────────────


class TestFirmaMemoria:

    def test_first_sighting_is_nueva(self, db):
        conn, _ = db
        memoria = FirmaMemoria(conn)
        fid, estado, es_nueva = memoria.registrar(
            "beta1", "SISMO_M6", 45, _features_base(), "ev1", "2020-01-01 00:00"
        )
        assert es_nueva is True
        assert estado == "nueva"

    def test_recurrence_promotes(self, db):
        conn, _ = db
        memoria = FirmaMemoria(conn)
        estados = []
        for i in range(5):
            _, estado, _ = memoria.registrar(
                "beta1", "SISMO_M6", 45, _features_base(),
                f"ev{i}", f"2020-0{i+1}-01 00:00",
            )
            estados.append(estado)
        assert estados[0] == "nueva"
        assert estados[1] == "observada"
        assert estados[2] == "recurrente"
        assert estados[4] == "consolidada"

    def test_different_signature_creates_new(self, db):
        conn, _ = db
        memoria = FirmaMemoria(conn)
        memoria.registrar("beta1", "SISMO_M6", 45, _features_base(), "a", "2020-01-01")
        distinta = _features_base(
            bz_mean=18.0, bz_min=12.0, kp_mean=0.1, kp_max=0.3,
            viento_avg=250.0, viento_max=255.0, schumann_mean=14.5,
            sismo_count_win=0.0, sismo_max_mag_win=0.0, fase_lunar=0.05,
        )
        _, _, es_nueva = memoria.registrar(
            "beta1", "SISMO_M6", 12, distinta, "b", "2021-01-01"
        )
        assert es_nueva is True
        assert memoria.stats()["total"] == 2

    def test_match_estado_actual_only_consolidadas(self, db):
        conn, _ = db
        memoria = FirmaMemoria(conn)
        for i in range(5):
            memoria.registrar("padre", "SISMO_M7", 45, _features_base(),
                              f"e{i}", f"202{i}-01-01")
        matches = memoria.match_estado_actual(_features_base())
        assert len(matches) == 1
        assert matches[0]["event_class"] == "SISMO_M7"
        assert matches[0]["similitud"] > 0.9

    def test_no_match_when_nothing_consolidated(self, db):
        conn, _ = db
        memoria = FirmaMemoria(conn)
        memoria.registrar("padre", "SISMO_M7", 45, _features_base(), "e", "2020-01-01")
        assert memoria.match_estado_actual(_features_base()) == []


# ── Juez ─────────────────────────────────────────────────────────────


class TestJuez:

    def test_acierto(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("padre", "alert", 0.8, ventana_h=0)
        res = juez.evaluar_pendientes(evento_ocurrido=True, verdad="M6.1")
        assert res[0]["resultado"] == "ACIERTO"
        assert res[0]["severidad"] == 0.0

    def test_falso_positivo_cheap(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("padre", "alert", 0.8, ventana_h=0)
        res = juez.evaluar_pendientes(evento_ocurrido=False)
        assert res[0]["resultado"] == "FALSO_POSITIVO"
        assert res[0]["severidad"] == 1.0

    def test_fallo_severity_asymmetric(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("padre", "neutral", 0.3, ventana_h=0)
        res = juez.evaluar_pendientes(evento_ocurrido=True, verdad="M7.0")
        assert res[0]["resultado"] == "FALLO"
        assert res[0]["severidad"] >= 10.0

    def test_fallo_firma_conocida_worst(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("padre", "neutral", 0.3, ventana_h=0)
        res = juez.evaluar_pendientes(
            evento_ocurrido=True, verdad="M7.0", firma_conocida=True
        )
        assert res[0]["severidad"] >= 20.0

    def test_recidivism_scales_severity(self, db):
        conn, _ = db
        juez = Juez(conn)
        severidades = []
        for _ in range(3):
            juez.registrar_prediccion("padre", "neutral", 0.3, ventana_h=0)
            res = juez.evaluar_pendientes(evento_ocurrido=True, verdad="M6")
            severidades.append(res[0]["severidad"])
        assert severidades[1] > severidades[0]
        assert severidades[2] > severidades[1]

    def test_open_window_stays_pending(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("padre", "alert", 0.8, ventana_h=72)
        res = juez.evaluar_pendientes(evento_ocurrido=True)
        assert res == []

    def test_resumen_por_bot(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("padre", "alert", 0.8, ventana_h=0)
        juez.evaluar_pendientes(evento_ocurrido=True)
        resumen = juez.resumen_por_bot()
        assert resumen["padre"]["ACIERTO"] == 1
        assert resumen["padre"]["asertividad"] == 1.0


# ── Entrenamiento sobre backcast sintetizado en test ────────────────


def _seed_backcast(conn, n_eventos=6):
    """Insert minimal 1H backcast rows + significant events for training.

    Test fixture data (allowed synthetic: this is a test database, not
    production ingestion).
    """
    from datetime import datetime, timedelta

    base = datetime(2010, 6, 1)
    for ev in range(n_eventos):
        ts_evento = base + timedelta(days=30 * ev)
        # 14 days of hourly space weather before each event, similar pattern
        for h in range(336):
            ts = ts_evento - timedelta(hours=336 - h)
            blk = ts.strftime("%Y-%m-%d %H:%M")
            conn.execute(
                "INSERT OR IGNORE INTO tbl_clima_espacial_raw "
                "(timestamp_blk, bz_promedio, bz_min, bz_derivada, "
                " viento_solar_avg, viento_solar_max, kp_max, kp_promedio, "
                " proton_flux_10mev) VALUES (?,?,?,?,?,?,?,?,?)",
                (blk, -3.0, -11.0, 0.4, 430.0, 600.0, 5.5, 3.0, 12.0),
            )
        blk_evento = ts_evento.strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT OR IGNORE INTO tbl_historico_sismico_raw "
            "(timestamp_blk, id_nodo, sismo_count, sismo_max_mag) "
            "VALUES (?, 45, 1, 6.4)",
            (blk_evento,),
        )
    conn.commit()


class TestEntrenamiento:

    def test_event_class(self):
        assert _event_class(5.2) == "SISMO_M5"
        assert _event_class(6.4) == "SISMO_M6"
        assert _event_class(7.8) == "SISMO_M7"

    def test_fase1_learns_and_promotes(self, db):
        conn, path = db
        _seed_backcast(conn, n_eventos=6)
        stats = entrenar_reconocimiento(path)
        assert stats["eventos"] == 6
        assert stats["firmas_nuevas"] >= 1
        assert stats["recurrencias"] >= 1
        # 6 near-identical events -> the recurring firma consolidates
        assert stats["memoria"].get("consolidada", 0) >= 1

    def test_fase2_recognizes_consolidated(self, db):
        conn, path = db
        _seed_backcast(conn, n_eventos=6)
        entrenar_reconocimiento(path)
        stats = backtest_disciplinario(path)
        assert stats["firmas_evaluadas"] > 0
        assert stats["reconocidas"] > 0

    def test_extraer_features_none_without_data(self, db):
        conn, _ = db
        assert extraer_features_ventana(conn, "2015-01-01 00:00", 45) is None
