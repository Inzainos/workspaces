"""Tests de la capa cimática espectral (tono de la ventana viva).

La capa entra como EVIDENCIA (audit 2026-10-21: familia 46.8% vs placebo
32.9%; solo-clima 51.2% — la configuración operacional). Estos tests
verifican el CONTRATO, no la habilidad: la habilidad está medida en el
audit con placebo, y lo que no hay es lo que se ve (None, nunca cero).
"""
import datetime as dt
import sqlite3

import numpy as np
import pytest

from sentinel_omega.core.firmas import cimatica_espectral as cs


# ── Fixture: DB sintética con regímenes distinguibles ────────────────────────
def _conn_sintetico(horas=2400, anchor_seismo=30, anchor_solar=30):
    """Clima con dos regímenes por bandas: quiet (sismico) / tormenta (solar).

    Banda quieta:  kp~1, viento~330 · Banda tormenta: kp~7, viento~700.
    Los anclas sísmicos caen en la banda quieta; los solares en la tormenta.
    """
    conn = sqlite3.connect(":memory:")
    cols = ", ".join(f"{c} REAL" for _, c in cs.SERIES)
    conn.execute(
        f"CREATE TABLE tbl_clima_espacial_raw (timestamp_blk TEXT PRIMARY KEY, "
        f"{cols})"
    )
    conn.execute(
        "CREATE TABLE tbl_eventos_no_sismicos (timestamp_blk TEXT, "
        "id_nodo INTEGER, event_class TEXT, fuente TEXT, intensidad REAL)"
    )
    conn.execute(
        "CREATE TABLE tbl_historico_sismico_raw (timestamp_blk TEXT, "
        "id_nodo INTEGER, sismo_count INTEGER DEFAULT 0, "
        "sismo_max_mag REAL DEFAULT 0.0, "
        "PRIMARY KEY (timestamp_blk, id_nodo))"
    )
    base = dt.datetime(2020, 1, 1)
    for h in range(horas):
        ts = (base + dt.timedelta(hours=h)).strftime("%Y-%m-%d %H:%M")
        tormenta = 700 < h < 1700
        kp = 7.0 + 0.1 * np.sin(h / 6.0) if tormenta else 1.0
        viento = 700.0 if tormenta else 330.0
        bz = -2.0 if tormenta else 2.0
        conn.execute(
            "INSERT INTO tbl_clima_espacial_raw VALUES (?,?,?,?,?,?)",
            (ts, bz, 0.1, viento, kp, 5.0 if tormenta else 4.0),
        )
    # anclas sísmicos en la primera banda quieta, con ventana completa.
    # Magnitud DISTINTA por ancla: el dedup del módulo (nodo+mag a ≤12 h =
    # el mismo sismo) colapsaría magnitudes repetidas.
    for i in range(anchor_seismo):
        h = 400 + i * 5
        ts = (base + dt.timedelta(hours=h)).strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT OR IGNORE INTO tbl_historico_sismico_raw VALUES (?,?,?,?)",
            (ts, 25, 1, 4.5 + (i % 20) * 0.1),
        )
    # anclas solares en plena banda de tormenta
    for i in range(anchor_solar):
        h = 1000 + i * 5
        ts = (base + dt.timedelta(hours=h)).strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO tbl_eventos_no_sismicos VALUES (?,?,?,?,?)",
            (ts, None, "TORMENTA_Kp6", "clima", 6.0),
        )
    conn.commit()
    return conn


# ── Huella ──────────────────────────────────────────────────────────────────
def test_huella_dimensiones_y_bins():
    conn = _conn_sintetico()
    filas = cs._ventana(conn, "2020-01-20 10:00")
    h = cs._huella_de_filas(filas)
    assert h is not None
    assert h.shape == (cs.DIM_HUELLA,)
    # sin NaN en este fixture (cobertura completa)
    assert not bool(np.isnan(h).any())


def test_huella_sin_lectura_si_no_hay_cobertura():
    conn = sqlite3.connect(":memory:")
    cols = ", ".join(f"{c} REAL" for _, c in cs.SERIES)
    conn.execute(
        f"CREATE TABLE tbl_clima_espacial_raw (timestamp_blk TEXT PRIMARY KEY, "
        f"{cols})"
    )
    # 3 horas de dato: ventana inservible → None (regla 2: ausencia, no cero)
    base = dt.datetime(2020, 1, 1)
    for h in range(3):
        ts = (base + dt.timedelta(hours=h)).strftime("%Y-%m-%d %H:%M")
        conn.execute("INSERT INTO tbl_clima_espacial_raw VALUES (?,?,?,?,?,?)",
                     (ts, 1.0, 0.1, 300.0, 1.0, 4.0))
    assert cs._huella_de_filas(cs._ventana(conn, "2020-01-02 00:00")) is None


def test_espectro_senoidal_peca_en_su_armonico():
    # seno de 2 ciclos por ventana → el pico de bajos armónicos es el 2
    # (Hann en 32 puntos riega al vecino: 8.19 vs 5.76 medido — el pico
    # sigue siendo el armónico correcto)
    fase = np.sin(2 * np.arange(cs.N_FASES) * 2 * np.pi / cs.N_FASES)
    t = np.linspace(0.0, 1.0, cs.N_FASES)
    p = np.polyfit(t, fase, 1)
    det = fase - np.polyval(p, t)
    hann = 0.5 * (1 - np.cos(2 * np.pi * t))
    amps = np.abs(np.fft.rfft(det * hann))
    assert amps[2] == max(amps[1:5])
    assert amps[2] > amps[1]


# ── Centroides y tono ───────────────────────────────────────────────────────
def test_construir_centroides_separa_regimenes():
    conn = _conn_sintetico()
    out = cs.construir_centroides(conn)
    assert out is not None
    fams = {k for k in out if k not in ("mu", "sd")}
    assert fams == {"sismico", "solar"}
    # persistidos
    cfg = cs._cargar_centroides(conn)
    assert cfg is not None
    assert "familia:sismico" in [f"familia:{f}" for f in cfg["centroides"]]
    assert cfg["meta"]["seed"] == cs.SEED


def test_tono_actual_sin_centroides_es_none_visible():
    conn = _conn_sintetico()
    assert cs.tono_actual(conn) is None


def test_tono_actual_identifica_el_regimen_vivo():
    conn = _conn_sintetico()
    cs.construir_centroides(conn)
    t = cs.tono_actual(conn)
    assert t is not None, "con datos y centroides debe leer"
    # el MAX(timestamp_blk) del fixture cae en la banda quieta → sismico
    assert t["tono"] == "sismico"
    assert set(t["dist"]) == {"sismico", "solar"}
    assert t["dist"]["sismico"] < t["dist"]["solar"]


def test_tono_actual_dim_insuficiente_none():
    """Si una familia queda con <8 dims comparables → None visible, no cero."""
    conn = _conn_sintetico()
    cs.construir_centroides(conn)
    # sabotear el centroide solar: vector con solo 2 dims no-NaN
    conn.execute(
        "UPDATE tbl_cimatica_tonos SET valor_json=? WHERE clave='familia:solar'",
        ('{"vec": [0.1, 0.2], "n": 30}',),
    )
    conn.commit()
    t = cs.tono_actual(conn)
    # con una sola familia comparable no hay tono
    assert t is None


# ── Audit de producción ─────────────────────────────────────────────────────
def test_audit_tono_eventos_cuenta_concordancia():
    conn = _conn_sintetico()
    cs.construir_centroides(conn)
    # evento sísmico en la banda quieta con ventana completa (h≈500),
    # epoch UTC-consistente con el módulo (fromtimestamp tz=utc)
    ts_ev = dt.datetime(2020, 1, 21, 20, 0).replace(tzinfo=dt.timezone.utc)
    epoch = ts_ev.timestamp()
    conn.execute(
        "CREATE TABLE TBL_HISTORICO_SISMICO (event_id TEXT PRIMARY KEY, "
        "timestamp REAL, lat REAL, lon REAL, magnitude REAL)"
    )
    conn.execute(
        "INSERT INTO TBL_HISTORICO_SISMICO VALUES ('x', ?, 1.0, 1.0, 4.7)",
        (epoch,),
    )
    res = cs.audit_tono_eventos(conn, desde_epoch=epoch - 86400)
    assert res["n_eventos"] == 1
    assert res["n_evaluados"] == 1
    assert res["eventos"][0]["tono"] == "sismico"
    assert res["aciertos_sismico"] == 1
    assert res["por_tono"] == {"sismico": 1}
