"""La reconstrucción de rasgos del Juez: que sea dato real, no relleno.

Contexto (2026-09-26): 19.791 de las 21.204 filas vivas juzgadas llevaban
`features_generales` vacío, y los 313 FALLO --- la única casilla que pesa 10 ---
estaban TODOS en ese lote. El reentrenamiento aprendía de 1.056 muestras sin una
sola ventana con evento.

Lo que estas pruebas defienden es la frontera: se recompone desde telemetría
guardada, y una fuente que no cubre el instante NO aporta nada. Cero es «no lo
sé» para el modelo sólo si nadie lo escribe como si fuera medido.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from sentinel_omega.models.rasgos_juez import (
    ANTIGUEDAD_MAX_H,
    RASGOS_VALIDADOS,
    VENTANA_H,
    _no_muy_vieja,
    asegurar_tabla,
    cargar_reconstruidos,
    rasgos_en,
    reconstruir_faltantes,
)


@pytest.fixture()
def base(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    conn.executescript(
        """
        CREATE TABLE TBL_JUEZ_AUDITORIA (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL, bot_name TEXT, prediccion TEXT, confianza REAL,
            ventana_h INTEGER, verdad TEXT, resultado TEXT, severidad REAL,
            reincidencia INTEGER, detalles_json TEXT, resuelto_at TEXT,
            fase TEXT, created_at TEXT
        );
        CREATE TABLE tbl_clima_espacial_raw (
            timestamp_blk TEXT, bz_promedio REAL, bz_derivada REAL, bz_min REAL,
            bz_max REAL, viento_solar_avg REAL, viento_solar_max REAL,
            kp_max REAL, kp_promedio REAL, proton_flux_10mev REAL
        );
        CREATE TABLE tbl_historico_sismico_raw (
            timestamp_blk TEXT, id_nodo TEXT, sismo_count INTEGER, sismo_max_mag REAL
        );
        CREATE TABLE tbl_desgasificacion_raw (
            timestamp_blk TEXT, id_nodo TEXT, volcan TEXT, tipo_erupcion TEXT,
            vei REAL, so2_kt REAL
        );
        CREATE TABLE tbl_psique_financiera (
            timestamp_blk TEXT, btc_precio_usd REAL, volatilidad_24h REAL,
            vix REAL, fear_greed REAL, yield_spread REAL, btc_dominance REAL,
            fetch_flags TEXT
        );
        CREATE TABLE tbl_astronomia_cinematica (
            timestamp_blk TEXT, lod_ms REAL, fase_lunar_pct REAL,
            distancia_lunar_km REAL, es_sicigia INTEGER
        );
        CREATE TABLE tbl_schumann_vivo (
            timestamp_blk TEXT, schumann_hz REAL, schumann_activity REAL,
            creada_at TEXT
        );
        CREATE TABLE tbl_xray_vivo (
            timestamp_blk TEXT, flux_max REAL, flux_avg REAL, banda TEXT
        );
        CREATE TABLE tbl_trends_vivo (fecha TEXT, solar_interest REAL);
        CREATE TABLE tbl_cobertura_satelital_historico (
            timestamp_blk TEXT, zona TEXT, coverage_score REAL,
            thermal_anomalies INTEGER, clear_passes INTEGER, total_passes INTEGER,
            revisit_days REAL, archivada_at TEXT
        );
        """
    )
    conn.commit()
    return conn


def _clima(conn, horas, bz=-5.0, kp=3.0):
    for h in horas:
        conn.execute(
            "INSERT INTO tbl_clima_espacial_raw VALUES (?,?,?,?,?,?,?,?,?,?)",
            (h, bz, 0.1, bz - 2, bz + 2, 450.0, 520.0, kp + 1, kp, 1.5),
        )
    conn.commit()


def test_sin_telemetria_solo_queda_la_marea(base):
    """Ninguna tabla cubre el instante: ninguna CONSULTADA aporta nada.

    La marea sí aparece, y es la diferencia de fondo: no se consulta, se
    calcula por efemérides. Es la única fuente del sistema que no puede tener
    huecos, y por eso beta2 dejó de ser un experto sin materia.
    """
    rasgos, fuentes = rasgos_en(base, "2026-09-10 12:00")
    assert fuentes == ["marea"]
    assert all(k.startswith("marea_") for k in rasgos), sorted(rasgos)
    assert rasgos["marea_total"] > 0


def test_el_clima_da_sus_agregados(base):
    _clima(base, ["2026-09-10 08:00", "2026-09-10 09:00", "2026-09-10 10:00"])
    rasgos, fuentes = rasgos_en(base, "2026-09-10 12:00")
    assert "clima" in fuentes
    assert rasgos["bz_mean"] == pytest.approx(-5.0)
    assert rasgos["bz_min"] == pytest.approx(-7.0)
    assert rasgos["viento_max"] == pytest.approx(520.0)
    assert rasgos["kp_max"] == pytest.approx(4.0)


def test_la_ventana_es_de_24_horas_medidas(base):
    """Fuera de la ventana no entra. 24 h no es un número de memoria: es el que
    hace que `bz_min` case EXACTO con lo que el bot vio (error 0,000)."""
    assert VENTANA_H == 24
    _clima(base, ["2026-09-08 10:00"], bz=-50.0)   # 50 h antes: fuera
    _clima(base, ["2026-09-10 10:00"], bz=-5.0)    # 2 h antes: dentro
    rasgos, _ = rasgos_en(base, "2026-09-10 12:00")
    assert rasgos["bz_mean"] == pytest.approx(-5.0)
    assert rasgos["bz_min"] == pytest.approx(-7.0)  # nunca el -52 de fuera


def test_una_fuente_parada_no_se_hace_pasar_por_actual(base):
    """`tbl_astronomia_cinematica` se paró el 2025-12-31. Sin tope de
    antigüedad, su última fila entraría como si fuera de hoy --- el mismo error
    que el LOCF de Schumann, disfrazado de dato."""
    base.execute(
        "INSERT INTO tbl_astronomia_cinematica VALUES (?,?,?,?,?)",
        ("2025-12-31 18:00", 1.2, 48.0, 380000.0, 0),
    )
    base.commit()
    rasgos, fuentes = rasgos_en(base, "2026-09-10 12:00")
    assert "lunar" not in fuentes
    assert "fase_lunar" not in rasgos
    assert "es_sicigia" not in rasgos


def test_una_fuente_reciente_si_entra(base):
    base.execute(
        "INSERT INTO tbl_astronomia_cinematica VALUES (?,?,?,?,?)",
        ("2026-09-10 06:00", 1.2, 48.0, 380000.0, 1),
    )
    base.commit()
    rasgos, fuentes = rasgos_en(base, "2026-09-10 12:00")
    assert "lunar" in fuentes
    assert rasgos["fase_lunar"] == pytest.approx(0.48)  # el % pasa a 0-1
    assert rasgos["es_sicigia"] == 1.0


def test_solo_salen_rasgos_validados(base):
    """Un rasgo que la validación no respaldó no se escribe, ni aunque su
    fuente lo tenga. `sismo_count_win` vale 500 constante en vivo."""
    _clima(base, ["2026-09-10 10:00"])
    base.execute(
        "INSERT INTO tbl_historico_sismico_raw VALUES (?,?,?,?)",
        ("2026-09-10 10:00", "nodo1", 42, 5.5),
    )
    base.commit()
    rasgos, _ = rasgos_en(base, "2026-09-10 12:00")
    assert rasgos["sismo_max_mag_win"] == pytest.approx(5.5)
    assert "sismo_count_win" not in rasgos
    assert "sismo_count_72h" not in rasgos
    assert "bz_deriv_std" not in rasgos
    assert "kp_max_72h" not in rasgos
    assert set(rasgos) <= set(RASGOS_VALIDADOS)


def test_lo_que_el_bot_vio_manda_sobre_lo_reconstruido(base):
    """Una fila con rasgos propios NO se toca: son los de verdad."""
    _clima(base, ["2026-09-10 10:00"])
    import datetime
    ts = datetime.datetime(2026, 9, 10, 12, 0).timestamp()
    base.execute(
        "INSERT INTO TBL_JUEZ_AUDITORIA (timestamp, bot_name, resultado, "
        "detalles_json, fase) VALUES (?,?,?,?,?)",
        (ts, "alfa1", "ACIERTO",
         json.dumps({"features_generales": {"bz_mean": -99.0}}), "viva"),
    )
    base.execute(
        "INSERT INTO TBL_JUEZ_AUDITORIA (timestamp, bot_name, resultado, "
        "detalles_json, fase) VALUES (?,?,?,?,?)",
        (ts, "beta1", "FALLO",
         json.dumps({"features_generales": {}}), "viva"),
    )
    base.commit()
    r = reconstruir_faltantes(base)
    assert r["ya_tenian"] == 1
    assert r["reconstruidas"] == 1
    guardados = cargar_reconstruidos_de(base)
    assert len(guardados) == 1
    # la que se reconstruyó es la de beta1, y con el Bz de la telemetría
    (rasgos,) = guardados.values()
    assert rasgos["bz_mean"] == pytest.approx(-5.0)


def cargar_reconstruidos_de(conn):
    filas = conn.execute(
        "SELECT juez_id, rasgos_json FROM tbl_juez_rasgos_reconstruidos"
    ).fetchall()
    return {int(i): json.loads(r) for i, r in filas}


def test_medir_no_escribe(base):
    _clima(base, ["2026-09-10 10:00"])
    import datetime
    base.execute(
        "INSERT INTO TBL_JUEZ_AUDITORIA (timestamp, bot_name, resultado, "
        "detalles_json, fase) VALUES (?,?,?,?,?)",
        (datetime.datetime(2026, 9, 10, 12, 0).timestamp(), "alfa1", "FALLO",
         "{}", "viva"),
    )
    base.commit()
    r = reconstruir_faltantes(base, escribir=False)
    assert r["reconstruidas"] == 1
    assert r["escrito"] is False
    assert cargar_reconstruidos_de(base) == {}


def test_un_ciclo_se_consulta_una_vez(base):
    """Ocho bots comparten instante: ocho filas, UN barrido de telemetría."""
    _clima(base, ["2026-09-10 10:00"])
    import datetime
    ts = datetime.datetime(2026, 9, 10, 12, 0).timestamp()
    for bot in ("alfa1", "alfa2", "beta1", "beta2", "delta", "omega", "loki",
                "jupiter"):
        base.execute(
            "INSERT INTO TBL_JUEZ_AUDITORIA (timestamp, bot_name, resultado, "
            "detalles_json, fase) VALUES (?,?,?,?,?)",
            (ts, bot, "ACIERTO", "{}", "viva"),
        )
    base.commit()
    r = reconstruir_faltantes(base)
    assert r["reconstruidas"] == 8
    assert r["bloques_distintos"] == 1


def test_la_tabla_es_forward_only(base):
    """Crearla dos veces no rompe, y la auditoría no se toca."""
    asegurar_tabla(base)
    asegurar_tabla(base)
    cols = [r[1] for r in base.execute("PRAGMA table_info(TBL_JUEZ_AUDITORIA)")]
    assert "rasgos_json" not in cols  # nada se añadió a la auditoría


def test_antiguedad_rechaza_el_futuro_y_lo_viejo():
    """Una fila posterior al instante no representa a ese instante."""
    assert _no_muy_vieja("2026-09-10 10:00", "2026-09-10 12:00", 24) is True
    assert _no_muy_vieja("2026-09-08 10:00", "2026-09-10 12:00", 24) is False
    assert _no_muy_vieja("2026-09-10 14:00", "2026-09-10 12:00", 24) is False
    assert _no_muy_vieja(None, "2026-09-10 12:00", 24) is False
    assert set(ANTIGUEDAD_MAX_H) == {"satelital", "xray", "trends", "lunar"}


def test_cargar_reconstruidos_sin_tabla_no_revienta(tmp_path):
    p = tmp_path / "vacia.db"
    sqlite3.connect(str(p)).close()
    assert cargar_reconstruidos(str(p)) == {}
