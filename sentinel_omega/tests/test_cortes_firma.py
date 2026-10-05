"""Cortes del 2026-10-04 y agregados de la ventana sismica.

2.5 arma la firma, 4.5 es la prediccion, 6 dispara la alerta.
La bajada USGS de 2.5 a 4.49 no entra aqui.
"""
import sqlite3

import pytest

from sentinel_omega.core.features_onnx import FEATURE_ORDER
from sentinel_omega.core.firmas.signature_engine import (
    FEATURE_KEYS, _sismos_de_ventana,
)
from sentinel_omega.infrastructure.pipeline.entrenamiento import (
    BOT_FEATURES, MIN_MAGNITUD_ALERTA, MIN_MAGNITUD_FIRMA,
    MIN_MAGNITUD_OBSERVAR, dispara_alerta,
)

NUEVAS = [
    "sismo_depth_mean_win", "sismo_corteza_win", "sismo_profundo_win",
    "sismo_mag_mw_win", "sismo_mag_otro_win", "sismo_eq_win",
    "sismo_otro_tipo_win", "sismo_tsunami_win", "sismo_alert_max_win",
    "sismo_mmi_max_win", "sismo_cdi_max_win", "sismo_felt_sum_win",
    "sismo_sig_max_win",
]


def test_los_tres_cortes():
    assert MIN_MAGNITUD_OBSERVAR == 2.5
    assert MIN_MAGNITUD_FIRMA == 4.5
    assert MIN_MAGNITUD_ALERTA == 6.0


def test_la_alerta_sale_desde_m6():
    assert dispara_alerta("SISMO_M4") is False
    assert dispara_alerta("SISMO_M5") is False
    assert dispara_alerta("SISMO_M4_obs") is False
    assert dispara_alerta("SISMO_M6") is True
    assert dispara_alerta("SISMO_M7") is True
    assert dispara_alerta("ERUPCION_VEI4") is True
    assert dispara_alerta(None) is True


def test_el_onnx_no_crece():
    assert len(FEATURE_ORDER["beta1"]) == 16
    for k in NUEVAS:
        assert k not in FEATURE_ORDER["beta1"]
        assert k in FEATURE_KEYS
        assert k in BOT_FEATURES["beta1"]


def _tabla(conn):
    conn.execute(
        "CREATE TABLE tbl_eventos_sismicos_fuente ("
        "usgs_id TEXT PRIMARY KEY, time_utc TEXT NOT NULL, lat REAL NOT NULL, "
        "lon REAL NOT NULL, mag REAL NOT NULL, id_nodo INTEGER NOT NULL, "
        "topologia_version TEXT NOT NULL, depth_km REAL, mag_type TEXT, "
        "event_type TEXT, tsunami INTEGER, alert TEXT, mmi REAL, cdi REAL, "
        "felt INTEGER, sig INTEGER, segmento TEXT)"
    )


def _fila(conn, usgs, ts, event_type, depth, segmento, mag_type,
          tsunami, alert, mmi, cdi, felt, sig, nodo=7):
    conn.execute(
        "INSERT INTO tbl_eventos_sismicos_fuente ("
        "usgs_id, time_utc, lat, lon, mag, id_nodo, topologia_version, "
        "depth_km, segmento, mag_type, event_type, tsunami, alert, mmi, "
        "cdi, felt, sig) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (usgs, ts, 0.0, 0.0, 5.0, nodo, "t", depth, segmento, mag_type,
         event_type, tsunami, alert, mmi, cdi, felt, sig),
    )


def test_agregados_de_la_ventana_dejan_fuera_el_evento_y_lo_que_no_es_sismo():
    conn = sqlite3.connect(":memory:")
    _tabla(conn)
    ts = "2026-09-21 00:00"
    _fila(conn, "a", "2026-09-20 01:00", "earthquake", 10, "corteza", "mb",
          0, None, None, None, 0, 100)
    _fila(conn, "b", "2026-09-20 02:00", "earthquake", 80, "profundo", "mww",
          1, "red", 5, 4, 3, 600)
    _fila(conn, "c", "2026-09-20 03:00", "explosion", 5, "corteza", "ml",
          0, None, None, None, 0, 10)
    _fila(conn, "d", ts, "earthquake", 1, "corteza", "mb",
          0, None, 9, 9, 9, 900)
    _fila(conn, "e", "2026-09-20 04:00", "earthquake", None, None, None,
          None, None, None, None, None, None)
    _fila(conn, "f", "2026-09-19 00:00", "earthquake", 0, "corteza", "mw",
          0, None, None, None, None, None)
    conn.commit()
    out = _sismos_de_ventana(conn, ts, 7)
    assert out["sismo_depth_mean_win"] == pytest.approx(30.0)
    assert out["sismo_corteza_win"] == 2
    assert out["sismo_profundo_win"] == 1
    assert out["sismo_mag_mw_win"] == 2
    assert out["sismo_mag_otro_win"] == 1
    assert out["sismo_eq_win"] == 4
    assert out["sismo_otro_tipo_win"] == 1
    assert out["sismo_tsunami_win"] == 1
    assert out["sismo_alert_max_win"] == 4
    assert out["sismo_mmi_max_win"] == 5
    assert out["sismo_cdi_max_win"] == 4
    assert out["sismo_felt_sum_win"] == 3
    assert out["sismo_sig_max_win"] == 600


def test_si_falta_la_medicion_no_se_inventa_cero():
    conn = sqlite3.connect(":memory:")
    _tabla(conn)
    _fila(conn, "z", "2026-09-20 01:00", "earthquake", None, None, None,
          None, None, None, None, None, None)
    conn.commit()
    out = _sismos_de_ventana(conn, "2026-09-21 00:00", 7)
    assert out["sismo_eq_win"] == 1
    assert out["sismo_otro_tipo_win"] == 0
    for k in NUEVAS:
        if k in ("sismo_eq_win", "sismo_otro_tipo_win"):
            continue
        assert k not in out


def test_sin_columnas_no_hay_agregados():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tbl_eventos_sismicos_fuente (usgs_id TEXT)")
    assert _sismos_de_ventana(conn, "2026-09-21 00:00", 7) == {}
