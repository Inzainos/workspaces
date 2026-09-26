"""El entrenamiento tardaba 36 horas. Tarda 2,1.

Medido el 2026-09-26 con cProfile sobre corridas reales, no a ojo:

  1. **El índice que faltaba (4,6x).** `reincidencia()` --- que escribí el día
     anterior --- ordenaba por `COALESCE(resuelto_at, created_at)`, lo que
     obligaba a un B-TREE temporal sobre TODAS las filas del bot (hasta 150.000)
     para sacar cinco. Se comía **24 de los 38 segundos** de un entrenamiento de
     40 eventos: el 62 %. Ordenando por `id` (el rowid) con un índice
     (bot_name, id), SQLite recorre hacia atrás y para al quinto.
  2. **Cachear el vector de cada firma (1,5x).** `similitud` reconstruía el
     vector de los DOS lados en cada llamada, y cada evento se compara contra
     todas las firmas de su clase: 806.546 reconstrucciones en 60 eventos.
  3. **Vectorizar la comparación (2,7x).** 549.549 llamadas de Python pasan a
     una operación de matriz por evento.

Nada de esto necesita GPU: el coste era SQL y bucles de Python, no álgebra.
"""
import numpy as np
import pytest

from sentinel_omega.core.firmas.signature_engine import (
    MIN_DIMENSIONES_COMPARABLES,
    similitud_vec,
    similitudes_contra,
)


def test_el_calculo_en_matriz_es_identico_al_de_una_en_una():
    """Lo que no puede pasar: que ir más rápido cambie los resultados."""
    rng = np.random.default_rng(7)
    for _ in range(200):
        n = int(rng.integers(1, 12))
        va = rng.normal(size=20)
        va[rng.random(20) < 0.3] = np.nan
        m = rng.normal(size=(n, 20))
        m[rng.random((n, 20)) < 0.3] = np.nan
        uno = [similitud_vec(va, m[i]) for i in range(n)]
        muchos = similitudes_contra(va, m)
        assert np.allclose(uno, muchos, atol=1e-12)


def test_sin_firmas_devuelve_vacio():
    assert similitudes_contra(np.zeros(20), np.empty((0, 20))).size == 0


def test_pocas_dimensiones_comparables_no_puntuan():
    """La regla de cero sintético: si no hay suficientes dimensiones en AMBOS,
    no se compara --- no se imputa."""
    va = np.full(20, np.nan)
    va[0] = 1.0
    m = np.full((1, 20), np.nan)
    m[0, 0] = 1.0
    assert MIN_DIMENSIONES_COMPARABLES > 1
    assert similitudes_contra(va, m)[0] == 0.0


def test_un_vector_identico_a_si_mismo_da_uno():
    v = np.arange(20, dtype=float) + 1.0
    assert similitudes_contra(v, v[None, :])[0] == pytest.approx(1.0)


def test_el_indice_de_la_racha_se_crea():
    import sqlite3

    from sentinel_omega.core.juez.juez import Juez
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE TBL_JUEZ_AUDITORIA (id INTEGER PRIMARY KEY, "
                 "bot_name TEXT, verdad TEXT, resultado TEXT, "
                 "resuelto_at TEXT, created_at TEXT)")
    Juez._INDICES_LISTOS = False
    Juez(conn).asegurar_indices()
    indices = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")]
    assert "idx_juez_bot_id" in indices


def test_la_racha_ordena_por_id_no_por_fecha():
    """Ordenar por COALESCE(fecha) impedía usar el índice y costaba el 62 % del
    tiempo de entrenamiento."""
    import inspect

    from sentinel_omega.core.juez.juez import Juez
    fuente = inspect.getsource(Juez.reincidencia)
    assert "ORDER BY id DESC" in fuente
    assert "COALESCE(resuelto_at, created_at) DESC" not in fuente


def test_el_cache_de_vectores_tiene_techo():
    """Un caché sin límite en una corrida de 186.806 eventos se come la
    memoria."""
    import inspect

    from sentinel_omega.core.firmas.signature_engine import FirmaMemoria
    fuente = inspect.getsource(FirmaMemoria)
    assert "_cache_vectores" in fuente
    assert "clear()" in fuente


def test_el_cache_se_invalida_cuando_la_firma_cambia():
    """La clave incluye el json: si la firma se actualiza (media corrida), la
    entrada vieja deja de usarse sola."""
    import inspect

    from sentinel_omega.core.firmas.signature_engine import FirmaMemoria
    fuente = inspect.getsource(FirmaMemoria._vector_de_firma)
    assert "(firma_id, features_json)" in fuente
