"""La similitud puede ponderarse por discriminación --- y medido, NO conviene.

El encargo era «ponderar por capacidad de discriminación en vez de promediar».
El mecanismo está hecho y verificado; lo que la medición dice es que
**encenderlo empeora**, así que queda inerte por defecto. Esta prueba fija las
dos cosas: que el mecanismo es correcto y que viene apagado.

Por qué se construyó (2026-10-07)
---------------------------------
Las tres funciones de similitud promediaban la penalización sobre todas las
dimensiones con el mismo peso, y eso era el techo del sistema:

    similitud en EVENTO (mediana)   0,896-0,941
    similitud en CALMA  (mediana)   0,877-0,965

Idénticas. En `beta1` la calma puntuaba MÁS alto teniendo declaradas 16
columnas sísmicas de nodo: los rasgos que discriminan quedaban diluidos entre
los que son casi iguales en todo el planeta a cualquier hora.

Por qué NO se enciende
----------------------
Medido sobre 400 eventos y 400 calmas contra 4.000 firmas consolidadas de
`padre`, con los pesos sacados del poder discriminante real de cada rasgo:

    media uniforme (hoy)   evento p50 0,835 | calma p50 0,837 | AUC 0,504
    ponderada por poder    evento p50 0,931 | calma p50 0,965 | AUC 0,160

Se **invierte**: ponderar empeora. Y la causa explica todo lo demás --- los diez
rasgos con poder son `sismo_*`, y con 14.955 firmas consolidadas el MÁXIMO
sobre la biblioteca siempre encuentra una gemela: una ventana de calma halla la
firma que también tiene los `sismo_*` en cero. Ponderar solo afina la búsqueda
de ese gemelo.

La raíz está más arriba, y también está medida: de las firmas consolidadas,
**casi ninguna discrimina por sí misma** --- padre 0 de 1.500, alfa1 1 de 1.093,
beta2/loki/omega/delta 0; solo beta1 llega al 11,2 % y son las de `sismo_*`,
que es peligrosidad de nodo. La promoción `nueva → observada → recurrente →
consolidada` va por RECURRENCIA, nunca por discriminación: un patrón que
reaparece en calma se consolida igual. Mientras eso no cambie, ninguna métrica
de similitud lo arregla.
"""
from __future__ import annotations

import numpy as np
import pytest

from sentinel_omega.core.firmas import signature_engine as se

A = {"kp_mean": 2.0, "kp_max": 3.0, "bz_mean": -1.0, "bz_min": -4.0,
     "viento_avg": 400.0}
B = {"kp_mean": 2.1, "kp_max": 3.1, "bz_mean": -1.1, "bz_min": -9.0,
     "viento_avg": 405.0}


@pytest.fixture(autouse=True)
def _sin_pesos():
    """Que una prueba no le deje los pesos puestos a la siguiente."""
    se.fijar_pesos_discriminacion(None)
    yield
    se.fijar_pesos_discriminacion(None)


def _las_tres(a=A, b=B):
    va, vb = se._vector(a), se._vector(b)
    return (se.similitud(a, b),
            se.similitud_vec(va, vb),
            float(se.similitudes_contra(va, vb[None, :])[0]))


def test_las_TRES_funciones_calculan_lo_mismo_sin_pesos():
    """Si no coinciden, entrenar y servir se separan --- `similitudes_contra` es
    la del entrenamiento y `similitud` la del ciclo vivo. Es el defecto que
    costó 792 falsas alarmas con el Kp, en otra capa."""
    s1, s2, s3 = _las_tres()
    assert s1 == pytest.approx(s2, abs=1e-9)
    assert s1 == pytest.approx(s3, abs=1e-9)


def test_las_TRES_funciones_calculan_lo_mismo_CON_pesos():
    se.fijar_pesos_discriminacion({"bz_min": 1.0})
    s1, s2, s3 = _las_tres()
    assert s1 == pytest.approx(s2, abs=1e-9)
    assert s1 == pytest.approx(s3, abs=1e-9)


def test_ponderar_deja_de_diluir_el_rasgo_que_difiere():
    """`bz_min` es el único que difiere de verdad (-4 contra -9). Promediado
    entre cinco rasgos casi iguales queda escondido; ponderado, manda."""
    uniforme = se.similitud(A, B)
    se.fijar_pesos_discriminacion({"bz_min": 1.0})
    ponderada = se.similitud(A, B)
    assert ponderada < uniforme - 0.2, (uniforme, ponderada)


def test_un_rasgo_sin_peso_no_puede_SUBIR_la_similitud():
    """El defecto de la media: un rasgo casi idéntico da penalización ~0 y
    empuja la similitud hacia 1. Con peso 0 ya no participa."""
    se.fijar_pesos_discriminacion({"bz_min": 1.0})
    solo_el_que_importa = se.similitud(A, B)
    se.fijar_pesos_discriminacion({"bz_min": 1.0, "kp_mean": 0.0,
                                   "kp_max": 0.0, "viento_avg": 0.0})
    con_ceros = se.similitud(A, B)
    assert con_ceros == pytest.approx(solo_el_que_importa, abs=1e-9)


# ─── Que venga apagado, y que apagarse no sea un fallo silencioso ────────────

def test_por_defecto_NO_hay_pesos():
    """Medido: encenderlos baja el AUC de 0,504 a 0,160. Vienen apagados, y si
    alguien los enciende tiene que ser con una medición que lo respalde."""
    assert se._PESOS_DISCRIMINACION is None


def test_un_mapa_vacio_vuelve_a_la_media_uniforme():
    se.fijar_pesos_discriminacion({"bz_min": 1.0})
    assert se._PESOS_DISCRIMINACION is not None
    assert se.fijar_pesos_discriminacion(None) == 0
    assert se._PESOS_DISCRIMINACION is None


def test_pesos_todos_en_cero_NO_dejan_la_similitud_indefinida(caplog):
    """Un mapa que suma cero dividiría por cero. Se vuelve a la media y se
    dice --- un descarte silencioso esconde el fallo (regla dura 10)."""
    import logging

    with caplog.at_level(logging.WARNING, logger=se.logger.name):
        n = se.fijar_pesos_discriminacion({"bz_min": 0.0, "kp_mean": 0.0})
    assert n == 0 and se._PESOS_DISCRIMINACION is None
    assert "cero" in caplog.text
    assert se.similitud(A, B) > 0.0


def test_un_rasgo_desconocido_no_rompe_el_alineado():
    """Los pesos se alinean con `FEATURE_KEYS`, que es el orden de `_vector`.
    Un nombre que no está en la lista se ignora en vez de desplazar todo."""
    n = se.fijar_pesos_discriminacion({"rasgo_que_no_existe": 1.0,
                                       "bz_min": 1.0})
    assert n == 1
    assert se._PESOS_DISCRIMINACION is not None
    assert len(se._PESOS_DISCRIMINACION) == len(se.FEATURE_KEYS)


def test_sin_tabla_de_pesos_no_es_un_fallo(tmp_path, caplog):
    """Una base que todavía no los ha medido se queda en la media uniforme,
    diciéndolo. Un checkout limpio no tiene la tabla."""
    import logging
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "vacia.db"))
    with caplog.at_level(logging.INFO, logger=se.logger.name):
        assert se.cargar_pesos_discriminacion(conn) == 0
    assert se._PESOS_DISCRIMINACION is None
    assert "sin pesos de discriminación" in caplog.text
    conn.close()


def test_los_pesos_se_cargan_de_la_tabla_cuando_existe(tmp_path):
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "con.db"))
    conn.execute(f"CREATE TABLE {se.TABLA_DISCRIMINACION} "
                 "(rasgo TEXT PRIMARY KEY, poder REAL)")
    conn.executemany(
        f"INSERT INTO {se.TABLA_DISCRIMINACION} (rasgo, poder) VALUES (?,?)",
        [("sismo_count_win", 0.827), ("bz_mean", 0.002)])
    conn.commit()
    assert se.cargar_pesos_discriminacion(conn) == 2
    i = se.FEATURE_KEYS.index("sismo_count_win")
    assert se._PESOS_DISCRIMINACION[i] == pytest.approx(0.827)
    conn.close()


def test_el_minimo_de_dimensiones_sigue_mandando():
    """Por debajo de `MIN_DIMENSIONES_COMPARABLES` la similitud es 0,0 con
    pesos o sin ellos: una firma no debe emparejar ni consigo misma."""
    se.fijar_pesos_discriminacion({"bz_min": 1.0})
    pocos = {"bz_min": -4.0, "kp_mean": 2.0}
    assert se.similitud(pocos, pocos) == 0.0
