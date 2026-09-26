"""Schumann: arrastre sin límite, pero siempre con bandera.

Historia: hasta el 2026-09-26 el respaldo LOCF arrastraba la última lectura
buena y la volvía a guardar como si fuera la medición de esa hora; así se
congelaron 38 bloques en 8,26 Hz / 21,46 % sin que nada lo distinguiera. Ese
día se le puso un tope de 6 h. Después el Capitán decidió: arrastrar sin tope
hasta que la API vuelva, pero con bandera ``en_vivo`` para que el sistema sepa
si el dato es en vivo o si la API está caída.
"""
import inspect
import sqlite3

import pytest

from sentinel_omega import launcher
from sentinel_omega.core import schumann_vivo as sv

H = 3600.0
T0 = 1790000000.0  # un instante fijo cualquiera (UTC)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


def _filas(conn):
    return conn.execute(
        "SELECT timestamp_blk, schumann_hz, schumann_activity, en_vivo, "
        "ultimo_vivo_ts, atraso_horas FROM tbl_schumann_vivo "
        "ORDER BY timestamp_blk").fetchall()


def test_caso_normal_guarda_en_vivo(conn):
    r = sv.registrar(conn, 7.9, 25.0, ahora=T0)
    assert r["estado"] == "en_vivo" and r["en_vivo"] == 1
    (f,) = _filas(conn)
    assert f[1:4] == (7.9, 25.0, 1)
    assert f[4] == f[0] and f[5] == 0


def test_api_caida_arrastra_el_ultimo_valor_marcado(conn):
    sv.registrar(conn, 7.9, 25.0, ahora=T0)
    r = sv.registrar(conn, None, None, ahora=T0 + H)
    assert r["estado"] == "arrastrado"
    assert (r["schumann_hz"], r["schumann_activity"]) == (7.9, 25.0)
    assert r["en_vivo"] == 0 and r["atraso_horas"] == 1.0
    vivo, arr = _filas(conn)
    assert arr[3] == 0 and arr[4] == vivo[0]


def test_api_caida_muchas_horas_no_caduca_ni_se_alimenta_a_si_mismo(conn):
    sv.registrar(conn, 7.9, 25.0, ahora=T0)
    for h in range(1, 49):  # dos días caída, más que el viejo tope de 6 h
        r = sv.registrar(conn, 7.83, 0.0, ahora=T0 + h * H)
    assert r["estado"] == "arrastrado" and r["atraso_horas"] == 48.0
    filas = _filas(conn)
    assert len(filas) == 49
    assert sum(1 for f in filas if f[3] == 1) == 1
    # Todos los arrastres apuntan a la única lectura real.
    assert {f[4] for f in filas} == {filas[0][0]}


def test_recuperacion_vuelve_a_en_vivo(conn):
    sv.registrar(conn, 7.9, 25.0, ahora=T0)
    sv.registrar(conn, None, None, ahora=T0 + H)
    r = sv.registrar(conn, 8.1, 30.0, ahora=T0 + 2 * H)
    assert r["estado"] == "en_vivo" and r["atraso_horas"] == 0.0
    assert sv.estado_actual(conn)["estado"] == "en_vivo"
    r = sv.registrar(conn, None, None, ahora=T0 + 3 * H)
    assert (r["schumann_hz"], r["atraso_horas"]) == (8.1, 1.0)


def test_un_arrastre_no_pisa_una_lectura_real_de_la_misma_hora(conn):
    sv.registrar(conn, 7.9, 25.0, ahora=T0)
    r = sv.registrar(conn, None, None, ahora=T0 + 60)  # mismo bloque horario
    assert r["en_vivo"] == 1
    (f,) = _filas(conn)
    assert f[3] == 1


def test_sin_lectura_real_nunca_es_desconocido_y_no_se_inventa(conn):
    r = sv.registrar(conn, None, None, ahora=T0)
    assert r["estado"] == "desconocido" and r["schumann_hz"] is None
    assert _filas(conn) == []


def test_migracion_agrega_columnas_sin_borrar(conn):
    conn.execute(
        "CREATE TABLE tbl_schumann_vivo (timestamp_blk TEXT PRIMARY KEY, "
        "schumann_hz REAL, schumann_activity REAL, creada_at TEXT)")
    conn.execute("INSERT INTO tbl_schumann_vivo VALUES ('2026-09-20 10:00',8.0,20.0,'x')")
    assert sv.filtro_en_vivo(conn) == ""
    sv.asegurar_tabla(conn)
    sv.asegurar_tabla(conn)  # idempotente
    (f,) = _filas(conn)
    assert f[:4] == ("2026-09-20 10:00", 8.0, 20.0, 1)
    assert "en_vivo" in sv.filtro_en_vivo(conn)


def test_el_launcher_ya_no_tiene_tope_y_usa_el_modulo():
    fuente = inspect.getsource(launcher)
    assert not hasattr(launcher, "SCHUMANN_LOCF_HORAS")
    assert "schumann_vivo.registrar" in fuente


def test_el_placeholder_de_libro_sigue_reconociendose():
    from sentinel_omega.infrastructure.api.schumann import is_baseline_placeholder
    assert is_baseline_placeholder(7.83, 0.0) is True
    assert is_baseline_placeholder(8.26, 21.46) is False
    assert is_baseline_placeholder(None, None) is True
    assert sv.es_senal_muerta(7.83, 0.0) and sv.es_senal_muerta(None, 1.0)
    assert not sv.es_senal_muerta(8.26, 21.46)


def test_el_volcado_conserva_la_ultima_lectura_real(tmp_path):
    """Revisión de T: el volcado de 24 h borraba también la última lectura
    real y el arrastre volvía a caducar. Ahora la conserva."""
    import time
    from sentinel_omega.infrastructure.pipeline import mantenimiento
    ruta = tmp_path / "v.db"
    c = sqlite3.connect(ruta)
    c.execute("CREATE TABLE tbl_enjambre_telemetria (timestamp_blk TEXT, "
              "id_nodo INTEGER, schumann_hz REAL, UNIQUE(timestamp_blk, id_nodo))")
    viejo = time.time() - 72 * H
    sv.registrar(c, 7.9, 25.0, ahora=viejo - 2 * H)   # lectura real vieja
    sv.registrar(c, 8.0, 26.0, ahora=viejo)           # la última real
    sv.registrar(c, None, None, ahora=viejo + H)      # arrastre viejo
    c.commit()
    c.close()
    res = mantenimiento.volcar_telemetria_viva(str(ruta), run_cascada=False)
    assert res["schumann_movidos"] == 2  # las dos reales pasan al enjambre
    c = sqlite3.connect(ruta)
    quedan = _filas(c)
    assert len(quedan) == 1 and quedan[0][1:4] == (8.0, 26.0, 1)
    r = sv.registrar(c, None, None)
    assert r["estado"] == "arrastrado"
    assert (r["schumann_hz"], r["schumann_activity"]) == (8.0, 26.0)
    assert 71.0 <= r["atraso_horas"] <= 73.0
    c.close()
