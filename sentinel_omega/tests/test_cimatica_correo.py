"""Tests de cimática (snapshot de patrones) y outbox de correo."""

import pytest

from sentinel_omega.infrastructure.database.schema import init_database
from sentinel_omega.core.firmas.cimatica import (
    FRECUENCIA_CONSISTENTE,
    banda,
    clave_patron,
    patrones_consistentes,
    registrar_snapshot,
)
from sentinel_omega.infrastructure.api.correo import (
    encolar_correo,
    enviar_pendientes,
)


@pytest.fixture
def db(tmp_path):
    conn = init_database(str(tmp_path / "test_cimatica.db"))
    yield conn
    conn.close()


FEATURES = {
    "bz_mean": -8.2, "kp_max": 6.0, "viento_avg": 540.0,
    "schumann_mean": 7.9, "fase_lunar": 0.95,
}


class TestBanda:

    def test_cero_para_pequenos(self):
        assert banda(0.0) == 0
        assert banda(0.3) == 0
        assert banda(-0.4) == 0

    def test_conserva_signo(self):
        assert banda(8.0) > 0
        assert banda(-8.0) < 0
        assert banda(8.0) == -banda(-8.0)

    def test_magnitudes_parecidas_misma_banda(self):
        assert banda(500.0) == banda(520.0)

    def test_magnitudes_distintas_banda_distinta(self):
        assert banda(3.0) != banda(300.0)

    def test_nan_es_cero(self):
        assert banda(float("nan")) == 0


class TestClavePatron:

    def test_determinista(self):
        assert clave_patron(FEATURES) == clave_patron(dict(FEATURES))

    def test_estado_parecido_misma_clave(self):
        cerca = dict(FEATURES, viento_avg=548.0)
        assert clave_patron(FEATURES) == clave_patron(cerca)

    def test_estado_distinto_clave_distinta(self):
        lejos = dict(FEATURES, bz_mean=12.0, kp_max=1.0)
        assert clave_patron(FEATURES) != clave_patron(lejos)

    def test_ignora_no_numericos(self):
        con_texto = dict(FEATURES, etiqueta="x")
        assert clave_patron(con_texto) == clave_patron(FEATURES)


class TestRegistrarSnapshot:

    def test_nuevo_guarda_telemetria_completa(self, db):
        pid, es_nuevo, frec = registrar_snapshot(db, FEATURES)
        assert es_nuevo is True
        assert frec == 1
        import json
        tele = json.loads(db.execute(
            "SELECT telemetria_json FROM tbl_cimatica_patrones "
            "WHERE patron_id = ?", (pid,)).fetchone()[0])
        assert tele["bz_mean"] == pytest.approx(-8.2)

    def test_existente_suma_uno(self, db):
        registrar_snapshot(db, FEATURES)
        pid, es_nuevo, frec = registrar_snapshot(db, FEATURES)
        assert es_nuevo is False
        assert frec == 2

    def test_nodo_y_general_separados(self, db):
        p1, n1, _ = registrar_snapshot(db, FEATURES)
        p2, n2, _ = registrar_snapshot(db, FEATURES, id_nodo=14)
        assert n1 and n2
        assert p1 != p2

    def test_etiqueta_event_class_despues(self, db):
        pid, _, _ = registrar_snapshot(db, FEATURES)
        registrar_snapshot(db, FEATURES, event_class="SISMO_M5")
        ec = db.execute(
            "SELECT event_class FROM tbl_cimatica_patrones "
            "WHERE patron_id = ?", (pid,)).fetchone()[0]
        assert ec == "SISMO_M5"

    def test_consistentes(self, db):
        for _ in range(FRECUENCIA_CONSISTENTE):
            registrar_snapshot(db, FEATURES, event_class="SISMO_M5")
        cons = patrones_consistentes(db)
        assert len(cons) == 1
        assert cons[0][4] == FRECUENCIA_CONSISTENTE

    def test_features_vacios_no_registran(self, db):
        pid, es_nuevo, frec = registrar_snapshot(db, {})
        assert pid == 0


class TestCorreo:

    def test_encolar(self, db):
        cid = encolar_correo(db, "asunto x", "cuerpo y", tipo="REPORTE")
        fila = db.execute(
            "SELECT destinatario, tipo, estado FROM tbl_correo_salida "
            "WHERE correo_id = ?", (cid,)).fetchone()
        assert fila[0] == "elan.zainos.corona@gmail.com"
        assert fila[1] == "REPORTE"
        assert fila[2] == "PENDIENTE"

    def test_sin_credenciales_queda_pendiente(self, db, monkeypatch):
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_PASS", raising=False)
        encolar_correo(db, "alerta", "cuerpo")
        r = enviar_pendientes(db)
        assert r["enviados"] == 0
        assert r["pendientes"] == 1
        estado = db.execute(
            "SELECT estado FROM tbl_correo_salida").fetchone()[0]
        assert estado == "PENDIENTE"

    def test_outbox_vacio(self, db):
        r = enviar_pendientes(db)
        assert r == {"enviados": 0, "pendientes": 0, "fallidos": 0}
