"""Un tope no es un conteo, y contar otra cosa no es contar.

Medido el 2026-09-27 en el ciclo 14419: `sismo_count_win` y `sismo_count_72h`
llegaban al modelo como **500,0 exactos**, los dos, en todos los ciclos. Dos
defectos encadenados:

  1. el catálogo de USGS se pide con `limit=500` (`api/usgs.py: MAX_RESULTS`) y
     para M2,5+ en 30 días el mundo da 1.967, así que `len(...)` topaba siempre;
  2. la FIRMA cuenta otra cosa: del NODO y en 336 h / 72 h
     (`signature_engine.py:180` y `:281`), no del mundo en 30 días.

Contra la distribución con la que se entrenó --- mediana 7, p75 14, p99 244,
solo 34 de 15.282 firmas llegan a 500 --- ese 500 fijo situaba al modelo por
encima del percentil 99,8 en cada ciclo: «enjambre extremo», permanente y falso.
"""
import sqlite3

import pytest

from sentinel_omega.infrastructure.api.usgs import MAX_RESULTS


class _Runner:
    class pipeline:
        _cache = {"beta1": {"seismic_magnitudes": [3.1, 4.5, 6.6]}}


@pytest.fixture
def base(tmp_path):
    conn = sqlite3.connect(tmp_path / "sismos.db")
    conn.execute(
        "CREATE TABLE tbl_historico_sismico_raw (timestamp_blk TEXT, "
        "id_nodo INTEGER, sismo_count INTEGER, sismo_max_mag REAL)"
    )
    # Nodo 61 enjambrado, nodo 19 tranquilo. Dentro de las 72 h el 61 aporta
    # menos, para que las dos ventanas NO puedan salir iguales.
    conn.executemany(
        "INSERT INTO tbl_historico_sismico_raw VALUES "
        "(datetime('now', ?), ?, ?, ?)",
        [("-10 hours", 61, 7, 4.1), ("-200 hours", 61, 92, 6.5),
         ("-10 hours", 19, 2, 3.0), ("-200 hours", 19, 9, 3.8)],
    )
    conn.commit()
    return conn


def test_el_conteo_sale_del_nodo_y_de_la_ventana_de_la_firma(base):
    """336 h → el nodo más activo suma 99; 72 h → solo 7. Antes los dos
    valían 500 porque venían del catálogo global topado."""
    from sentinel_omega.launcher import _build_live_features

    f = _build_live_features(_Runner(), base) or {}
    assert f["sismo_count_win"] == 99.0, "no está contando 336 h del nodo"
    assert f["sismo_count_72h"] == 7.0, "no está contando 72 h del nodo"


def test_las_dos_ventanas_no_pueden_dar_lo_mismo(base):
    """El síntoma que destapó el defecto: 500,0 en las dos posiciones."""
    from sentinel_omega.launcher import _build_live_features

    f = _build_live_features(_Runner(), base) or {}
    assert f["sismo_count_win"] != f["sismo_count_72h"]
    assert f["sismo_count_win"] != float(MAX_RESULTS)
    assert f["sismo_count_72h"] != float(MAX_RESULTS)


def test_se_toma_el_nodo_mas_activo_no_la_suma_global(base):
    """El ciclo es global y la firma es por nodo: el máximo conserva la escala
    aprendida. La suma (99+11=110) la rompería."""
    from sentinel_omega.launcher import _build_live_features

    f = _build_live_features(_Runner(), base) or {}
    assert f["sismo_count_win"] == 99.0, "sumó los nodos en vez de tomar el máximo"


def test_sin_conexion_el_rasgo_falta_y_no_se_inventa():
    """Cero sintético: sin base no hay conteo, y 0,0 lo pone `vector_para`
    como «no lo sé», no esta función como si fuera una medición."""
    from sentinel_omega.launcher import _build_live_features

    f = _build_live_features(_Runner(), None) or {}
    assert "sismo_count_win" not in f
    assert "sismo_count_72h" not in f


def test_la_magnitud_maxima_si_se_conserva(base):
    """El catálogo llega topado, pero el máximo de esos 500 es un máximo
    medido. Se distingue de los conteos, que sí quedaban falseados."""
    from sentinel_omega.launcher import _build_live_features

    f = _build_live_features(_Runner(), base) or {}
    assert f["sismo_max_mag_win"] == 6.6


def test_el_tope_de_usgs_esta_declarado_y_no_escondido():
    """Se expuso como constante para que quien cuenta pueda saber si topó."""
    assert MAX_RESULTS == 500

    import inspect

    from sentinel_omega.infrastructure.api import usgs
    assert "limit={max_results}" in inspect.getsource(usgs.fetch_earthquakes)


def test_hay_manera_de_pedir_el_conteo_real_sin_tope():
    """FDSN tiene endpoint `count`: devuelve el total sin traer ni recortar.
    No se llama en el ciclo --- los conteos salen del histórico por nodo ---
    pero queda disponible y verificado (1.967 el 2026-09-27)."""
    from sentinel_omega.infrastructure.api.usgs import count_earthquakes

    import inspect
    fuente = inspect.getsource(count_earthquakes)
    assert "event/1/count" in fuente
    # El tope no puede ir en la URL. Se mira la URL, no la prosa: el docstring
    # explica el tope y una búsqueda cruda del texto se cazaría a sí misma.
    url = [l for l in fuente.splitlines() if "minmagnitude=" in l]
    assert url, "no se encontró la URL del conteo"
    assert not any("limit" in l for l in url), "un conteo con tope no es un conteo"
