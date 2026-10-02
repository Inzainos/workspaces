"""La densidad de protones SÍ tiene treinta años. El flujo >10 MeV no.

El 2026-10-02 el operador recordó que «la densidad de protones la traíamos de
una API de la NASA», y la documentación lo confirmaba --- bitácora del 20-sep,
líneas 101-103: *«`fetch_solar_wind()` sí baja `proton_speed`/`proton_density`,
pero `fetch_alfa1_data` renombra `proton_speed → plasma_speed`»*. Se bajaba y se
tiraba, y `alfa1/agent.py:24` la declara entre sus tres variables.

El arreglo de ese día cableó el **flujo >10 MeV** --- otra magnitud, y la única
de las dos que está muerta en los dos lados:

    flujo >10 MeV   OMNI2 cols 42-47    100 % CENTINELA
                    NOAA                ventana de 6 h
                    en la tabla         178 de 286.932 h   (0,062 %)
                    en firmas de alfa1  26 de 1.483        (1,75 %)

    DENSIDAD        OMNI2 col 23        97,7 %, mediana 5,70 n/cc, 0 negativos
                    en vivo             llega, mediana 3,58 n/cc
                    tras el relleno     275.241 de 286.951 h   (95,9 %)
                    en firmas de alfa1  1.404 de 1.406         (99,86 %)

Así que la posición 2-3 del vector de alfa1, que repetía `proton_max` como
relleno, pasó a llevar media y máximo de densidad. Y la regresión lo demostró:
con las dos posiciones VACÍAS el modelo reentrenado alarmaba `WATCH 0,692` en un
ciclo en calma --- el fantasma que costó 792 falsas alarmas. Con la medición
real dentro, los tres tests de ese fantasma vuelven a pasar.
"""
import sqlite3

import pytest

from sentinel_omega.core.features_onnx import (
    BOT_DIMS, FEATURE_ORDER, agregados_omni,
)
from sentinel_omega.core.firmas.signature_engine import FEATURE_KEYS
from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES

CLAVES = ("densidad_prot_mean", "densidad_prot_max")


def test_la_densidad_esta_declarada_en_los_tres_sitios():
    """Los tres hacen falta: `FEATURE_KEYS` o la firma lo descarta en silencio,
    `BOT_FEATURES` o no se guarda, `FEATURE_ORDER` o el modelo no lo lee."""
    for k in CLAVES:
        assert k in FEATURE_KEYS, f"{k} no está en FEATURE_KEYS"
        assert k in BOT_FEATURES["alfa1"], f"{k} no está en BOT_FEATURES[alfa1]"
        assert k in FEATURE_ORDER["alfa1"], f"{k} no está en el vector de alfa1"


def test_el_flujo_muerto_ya_no_esta_en_el_vector():
    """`proton_max` sigue DECLARADO en BOT_FEATURES --- el ciclo vivo lo mide y
    la historia se acumula ---, pero ningún modelo lo lee."""
    assert "proton_max" in BOT_FEATURES["alfa1"]
    culpables = {b: o for b, o in FEATURE_ORDER.items() if "proton_max" in o}
    assert not culpables, (
        f"proton_max volvió al vector de {sorted(culpables)}: la tabla lo tiene "
        "en el 0,062 % de sus horas y no hay fuente histórica")


def test_alfa1_no_cambio_de_dimension():
    """Se sustituyó relleno por medición, no se añadieron posiciones."""
    assert BOT_DIMS["alfa1"] == 10
    assert len(FEATURE_ORDER["alfa1"]) == 10


def test_el_vector_no_repite_la_densidad():
    """El relleno repetido era justo el problema: dos posiciones con el mismo
    rasgo vacío. Ahora son dos agregados DISTINTOS de la misma serie."""
    assert FEATURE_ORDER["alfa1"].count("densidad_prot_mean") == 1
    assert FEATURE_ORDER["alfa1"].count("densidad_prot_max") == 1


def test_el_agregado_vivo_sale_de_proton_density():
    """`agregados_omni` tiene que reconocer la columna que trae el ciclo.

    Si el nombre no coincide, el rasgo se queda fuera y `vector_para` pone 0,0
    --- que es exactamente el defecto que se está cerrando.
    """
    import numpy as np
    cols = ["bz_gsm", "plasma_speed", "proton_density"]
    m = np.array([[-5.0, 400.0, 4.0],
                  [-9.0, 600.0, 8.0],
                  [-3.0, 500.0, 6.0]])
    f = agregados_omni(cols, m)
    assert f["densidad_prot_mean"] == pytest.approx(6.0)
    assert f["densidad_prot_max"] == pytest.approx(8.0)


def test_la_columna_23_de_omni2_es_la_densidad():
    """Regla dura 9 --- el índice se verifica contra el dato.

    No pega a la red: comprueba que el código sigue apuntando al 23. La firma
    medida contra `omni2_2024.dat` el 2026-10-02 fue mediana 5,70 n/cc, máximo
    87,40, cero negativos y 2,3 % de centinela, el MISMO hueco que la velocidad
    (col 24) porque salen del mismo instrumento de plasma. Si alguien mueve el
    índice, que vuelva a medir esa firma antes.
    """
    import inspect

    from sentinel_omega.infrastructure.pipeline import backcast

    fuente = inspect.getsource(backcast.extraer_nasa_omni_real)
    assert "CO_DENSIDAD" in fuente
    assert "= 16, 24, 38, 23" in fuente, (
        "cambió el índice de la densidad: vuelve a medir la columna contra "
        "omni2_2024.dat (mediana ~5,7 n/cc, cero negativos) antes de confiar")


def test_el_centinela_no_se_cuela():
    """999.9 es el centinela y los valores reales no pasan de ~140 n/cc, así que
    el corte en 999.0 no puede comerse un dato bueno."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import backcast

    assert "999.0" in inspect.getsource(backcast.extraer_nasa_omni_real)


def test_la_columna_se_anade_sin_borrar_nada(tmp_path):
    """Regla dura 5 --- migración forward-only. `asegurar_columnas` es
    idempotente y no toca las columnas que ya estaban."""
    from sentinel_omega.infrastructure.pipeline.backcast import asegurar_columnas

    c = sqlite3.connect(tmp_path / "c.db")
    c.execute("CREATE TABLE tbl_clima_espacial_raw ("
              "timestamp_blk TEXT PRIMARY KEY, bz_promedio REAL)")
    c.commit()
    asegurar_columnas(c)
    asegurar_columnas(c)          # dos veces: no puede fallar
    cols = [r[1] for r in c.execute("PRAGMA table_info(tbl_clima_espacial_raw)")]
    assert cols == ["timestamp_blk", "bz_promedio", "densidad_protones"], cols


def test_la_ventana_viva_es_la_de_la_firma():
    """La regla que gobierna `launcher.py`: el rasgo sale de la MISMA fuente y
    la MISMA ventana que lo calcula la firma, o el modelo responde a una
    magnitud que no aprendió. La firma usa 336 h de `tbl_clima_espacial_raw`.
    """
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher._build_live_features)
    assert "AVG(densidad_protones), MAX(densidad_protones)" in fuente
    i = fuente.index("AVG(densidad_protones)")
    assert "-336 hours" in fuente[i:i + 400], (
        "la densidad viva dejó de leer la ventana de 336 h: eso es el "
        "desajuste del Kp otra vez")
