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

    def test_fase2_reinforces_weights(self, db):
        conn, path = db
        _seed_backcast(conn, n_eventos=6)
        entrenar_reconocimiento(path)
        stats = backtest_disciplinario(path)
        # All signatures recognized -> credibility intact at baseline
        # (recognition repairs, it does not inflate)
        assert stats["fallos"] == 0
        for bot, peso in stats["pesos"].items():
            assert peso == pytest.approx(1.0)


# ── Pesos disciplinarios (castigo hijo x1, Padre x2) ─────────────────


class TestPesos:

    def test_castigo_hijo_vs_padre(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import castigar, cargar_pesos
        castigar(conn, "beta1", es_padre=False)
        castigar(conn, "padre", es_padre=True)
        pesos = cargar_pesos(conn)
        assert pesos["beta1"] == pytest.approx(0.95)
        assert pesos["padre"] == pytest.approx(0.90)  # double decay

    def test_castigo_escala_con_gravedad(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import castigar, cargar_pesos
        # Missing an M7 (gravedad 3) hurts much more than an M5 (gravedad 1)
        castigar(conn, "bot_m5", gravedad=1.0)
        castigar(conn, "bot_m7", gravedad=3.0)
        pesos = cargar_pesos(conn)
        assert pesos["bot_m5"] == pytest.approx(0.95)
        assert pesos["bot_m7"] == pytest.approx(0.95 ** 3)
        assert pesos["bot_m7"] < pesos["bot_m5"]

    def test_juez_severidad_cuadratica_en_gravedad(self, db):
        conn, _ = db
        juez = Juez(conn)
        juez.registrar_prediccion("a", "neutral", 0.3, ventana_h=0)
        res_m5 = juez.evaluar_pendientes(
            evento_ocurrido=True, verdad="M5", gravedad=1.0
        )
        juez.registrar_prediccion("b", "neutral", 0.3, ventana_h=0)
        res_m7 = juez.evaluar_pendientes(
            evento_ocurrido=True, verdad="M7", gravedad=3.0
        )
        # quadratic: gravedad 3 -> 9x the severity of gravedad 1
        assert res_m7[0]["severidad"] == pytest.approx(
            res_m5[0]["severidad"] * 9.0
        )

    def test_peso_bounded_below(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import castigar
        peso = 1.0
        for _ in range(50):
            peso = castigar(conn, "beta1")
        assert peso == pytest.approx(0.3)

    def test_refuerzo_normal_caps_at_baseline(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import reforzar
        peso = 1.0
        for _ in range(50):
            peso = reforzar(conn, "beta1")
        # doing your job repairs credibility but never exceeds baseline
        assert peso == pytest.approx(1.0)

    def test_refuerzo_recovers_after_castigo(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import castigar, reforzar
        castigar(conn, "beta1")  # 0.95
        peso = reforzar(conn, "beta1")
        assert 0.95 < peso <= 1.0

    def test_atencion_puede_superar_baseline(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import reforzar, PESO_MAX
        peso = 1.0
        for _ in range(50):
            peso = reforzar(conn, "beta1", hasta=PESO_MAX)
        assert peso == pytest.approx(1.5)

    def test_refuerzo_normal_no_baja_peso_ganado(self, db):
        conn, _ = db
        from sentinel_omega.core.juez.pesos import reforzar, PESO_MAX
        reforzar(conn, "beta1", hasta=PESO_MAX)  # 1.02 (above baseline)
        peso = reforzar(conn, "beta1")  # normal reinforcement
        assert peso == pytest.approx(1.02)  # never lowered back to 1.0

    def test_padre_applies_pesos_in_consensus(self):
        import time as _time
        from sentinel_omega.layers.geodynamic.padre.agent import GeodynamicPadre
        from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType

        def sig(name, stype, conf):
            return AgentSignal(agent_name=name, signal_type=stype,
                               confidence=conf, timestamp=_time.time())

        signals = [
            sig("alfa1", SignalType.ALERT, 0.9),
            sig("beta1", SignalType.ALERT, 0.9),
            sig("delta", SignalType.ALERT, 0.8),
        ]

        padre_neutral = GeodynamicPadre()
        res_neutral = padre_neutral.evaluate_consensus(signals)

        padre_castigado = GeodynamicPadre()
        padre_castigado.set_pesos({"alfa1": 0.5, "beta1": 0.5, "delta": 0.5})
        res_castigado = padre_castigado.evaluate_consensus(signals)

        # Punished bots' ALERTs demote to WATCH (peso < 0.6) — the same
        # signals no longer produce a full ALERT consensus.
        assert res_neutral.final_signal == SignalType.ALERT
        assert res_castigado.final_signal != SignalType.ALERT

    def test_muro_lags_convergencia(self):
        from sentinel_omega.core.precursor.muro_lags import evaluar_muro_lags
        matches = [
            {"firma_id": 1, "event_class": "SISMO_M5", "similitud": 0.85,
             "ventana_tipica_dias": 7.0},
            {"firma_id": 2, "event_class": "SISMO_M6", "similitud": 0.83,
             "ventana_tipica_dias": 9.0},
            {"firma_id": 3, "event_class": "SISMO_M5", "similitud": 0.82,
             "ventana_tipica_dias": 8.0},
        ]
        r = evaluar_muro_lags(matches)
        # ventanas: [3.5-10.5], [4.5-13.5], [4-12] → convergen en [4.5, 10.5]
        assert r["activo"] is True
        assert r["firmas_convergentes"] == 3
        assert r["ventana_dias"] == [4.5, 10.5]
        assert "SISMO_M6" in r["clases"]

    def test_muro_lags_sin_convergencia(self):
        from sentinel_omega.core.precursor.muro_lags import evaluar_muro_lags
        matches = [
            {"firma_id": 1, "event_class": "A", "similitud": 0.9,
             "ventana_tipica_dias": 1.0},
            {"firma_id": 2, "event_class": "B", "similitud": 0.9,
             "ventana_tipica_dias": 10.0},
            {"firma_id": 3, "event_class": "C", "similitud": 0.9,
             "ventana_tipica_dias": 100.0},
        ]
        r = evaluar_muro_lags(matches)
        assert r["activo"] is False

    def test_muro_lags_pocos_matches(self):
        from sentinel_omega.core.precursor.muro_lags import evaluar_muro_lags
        r = evaluar_muro_lags([
            {"firma_id": 1, "event_class": "A", "similitud": 0.9,
             "ventana_tipica_dias": 7.0},
        ])
        assert r["activo"] is False

    def test_peso_alto_no_demotion(self):
        import time as _time
        from sentinel_omega.layers.geodynamic.padre.agent import GeodynamicPadre
        from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType

        def sig(name, stype, conf):
            return AgentSignal(agent_name=name, signal_type=stype,
                               confidence=conf, timestamp=_time.time())

        signals = [
            sig("alfa1", SignalType.ALERT, 0.9),
            sig("beta1", SignalType.ALERT, 0.9),
            sig("delta", SignalType.ALERT, 0.8),
        ]
        padre = GeodynamicPadre()
        padre.set_pesos({"alfa1": 0.9, "beta1": 0.9, "delta": 0.9})
        res = padre.evaluate_consensus(signals)
        # Weights above the demotion threshold scale confidence but do NOT
        # demote the ALERT — consensus still escalates.
        assert res.final_signal == SignalType.ALERT
        assert res.consensus_reached is True


# ── Disciplina de trasfondo (castigo desde abajo) ────────────────────


class TestDisciplinaTrasfondo:
    """Disciplina rolling contra sismos menores: tabla temporal + pesos."""

    def _preparar(self, conn, path, monkeypatch, features):
        from sentinel_omega.infrastructure.pipeline import entrenamiento as E
        _seed_backcast(conn, n_eventos=6)          # firmas consolidadas en nodo 45
        entrenar_reconocimiento(path)
        # nodo 45 ≈ (40.18, -161.06): eventos menores que mapean ahí
        eventos = [("2010-10-25 00:00", 40.2, -161.0, 3.2 + i * 0.1)
                   for i in range(8)]
        monkeypatch.setattr(E, "_fetch_sismos_menores", lambda *a, **k: eventos)
        monkeypatch.setattr(E, "extraer_features_ventana", lambda *a, **k: features)
        return E

    def test_puebla_tabla_temporal_y_acota_pesos(self, db, monkeypatch):
        conn, path = db
        E = self._preparar(conn, path, monkeypatch, _features_base())
        pre = dict(conn.execute(
            "SELECT bot_name, peso FROM TBL_PESOS_BOTS").fetchall())
        res = E.disciplina_trasfondo(path, anio=2010, max_eventos=8)

        assert res["eventos"] == 8
        # La memoria permanente NO se toca; las menores van a su tabla temporal
        n_menores = conn.execute(
            "SELECT COUNT(*) FROM tbl_firmas_menores").fetchone()[0]
        assert n_menores > 0
        # Pesos dentro de límites y movidos a lo más MAX_AJUSTES pasos
        from sentinel_omega.core.juez.pesos import (
            PESO_MIN, PESO_MAX, CASTIGO_PADRE, REFUERZO,
        )
        post = dict(conn.execute(
            "SELECT bot_name, peso FROM TBL_PESOS_BOTS").fetchall())
        for bot, peso in post.items():
            assert PESO_MIN <= peso <= PESO_MAX
            # cota: nunca más allá de MAX_AJUSTES castigos del Padre (el más duro)
            piso = pre.get(bot, 1.0) * (CASTIGO_PADRE ** E.DISCIPLINA_MAX_AJUSTES)
            assert peso >= piso - 1e-9

    def test_ceguera_local_castiga(self, db, monkeypatch):
        conn, path = db
        # features MUY distintas a la firma aprendida -> no reconoce -> castigo
        distintas = _features_base(
            bz_mean=99.0, bz_min=99.0, viento_avg=9999.0, viento_max=9999.0,
            kp_mean=0.0, kp_max=0.0, proton_max=0.0,
        )
        E = self._preparar(conn, path, monkeypatch, distintas)
        res = E.disciplina_trasfondo(path, anio=2010, max_eventos=8)
        # Con ceguera local, al menos un bot recibe castigo
        total_castigos = sum(a["castigos"] for a in res["ajustes"].values())
        assert total_castigos >= 1

    def test_poda_rolling_por_edad(self, db, monkeypatch):
        conn, path = db
        E = self._preparar(conn, path, monkeypatch, _features_base())
        # Fila vieja artificial (más allá de la retención)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tbl_firmas_menores ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, "
            "event_class TEXT, id_nodo INTEGER, mag REAL, features_json TEXT, "
            "ts_evento TEXT, creada_at TEXT DEFAULT (datetime('now')))"
        )
        conn.execute(
            "INSERT INTO tbl_firmas_menores "
            "(bot_name, event_class, id_nodo, mag, features_json, ts_evento, "
            " creada_at) VALUES ('alfa1','SISMO_M3',45,3.1,'{}','x',"
            "datetime('now','-200 days'))"
        )
        conn.commit()
        E.disciplina_trasfondo(path, anio=2010, max_eventos=8)
        # La fila de hace 200 días quedó fuera (retención 90 días)
        viejas = conn.execute(
            "SELECT COUNT(*) FROM tbl_firmas_menores "
            "WHERE creada_at < datetime('now','-90 days')").fetchone()[0]
        assert viejas == 0
