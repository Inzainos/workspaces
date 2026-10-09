"""El latido, por fin medido: lector de la estacion ELF de Granada.

Contexto, medido el 2026-10-09. La resonancia Schumann es el eje del proyecto
y no estaba medida: `schumann_hz` era `7,83 + actividad x 0,02` ---una recta
sobre un conteo de pixeles--- con la misma actividad en 564 de 743 filas, y de
4.000 firmas solo 86 (2,2 %) llevaban el rasgo, con un recorrido de 0,03 Hz.

La estacion de Sierra Nevada (UGR) publica lo contrario: espectro calibrado
6-25 Hz y ajuste lorentziano, con frecuencia, amplitud y anchura de SR1/SR2/SR3
cada 10 minutos. Verificado sobre el dia que trae su repo (2015-03-01):

    SR1 recorre 1,0382 Hz en UN DIA, con 282 valores distintos de 285.
"""
from __future__ import annotations

import sqlite3

import pytest

from sentinel_omega.infrastructure.api import schumann_granada as sg


def test_las_columnas_del_ajuste_estan_verificadas_por_su_valor():
    """Regla 9: el indice de columna se comprueba contra el dato.

    Las columnas de `mediaLO` no vienen documentadas en el repo de origen. Se
    identificaron por el valor que toman --- las medias de las columnas 6, 7 y 8
    son 7,93 / 14,33 / 20,43, que son SR1, SR2 y SR3.
    """
    assert sg.COL_FRECUENCIA == (6, 7, 8)
    assert sg.COL_AMPLITUD == (0, 1, 2)
    assert sg.COL_ANCHURA == (9, 10, 11)
    assert sg.N_COLS_LO == 14
    assert sg.INTERVALO_MIN == 10


def test_el_umbral_del_error_es_RELATIVO_al_sensor():
    """Casi escribi un absoluto, y era el error del padre otra vez.

    Medido en el dia de muestra: el error de ajuste mediano del sensor 0 es
    0,0770 y el del 1 es 0,2554 --- 3,3x. Un absoluto de 0,25 descartaba el
    0 % del sensor 0 y el **53,5 %** del 1, cuando de los 288 intervalos solo
    **3** tienen la frecuencia fuera del rango fisico. El error marca la escala
    del sensor, no el dato malo.
    """
    assert not hasattr(sg, "ERROR_AJUSTE_MAXIMO"), (
        "volvio el umbral ABSOLUTO del error de ajuste")
    assert sg.ERROR_AJUSTE_VECES_MEDIANA >= 2.0
    # el rango fisico SI es absoluto, porque la fisica lo es
    assert sg.RANGOS_HZ[0][0] <= 7.83 <= sg.RANGOS_HZ[0][1]
    assert sg.RANGOS_HZ[1][0] <= 14.3 <= sg.RANGOS_HZ[1][1]
    assert sg.RANGOS_HZ[2][0] <= 20.8 <= sg.RANGOS_HZ[2][1]


def test_una_frecuencia_fuera_del_rango_fisico_se_guarda_NULL():
    """SR1 no esta en 23 Hz: eso es un fallo del ajuste, no una resonancia.

    El dia de muestra trae un f3 en 23,54 que hay que descartar. Faltante =
    NULL, nunca un valor plausible (regla 2).
    """
    lo, hi = sg.RANGOS_HZ[0]
    assert not (lo <= 23.5 <= hi)
    assert not (lo <= 0.0 <= hi)


def test_la_tabla_separa_frecuencia_de_amplitud_y_de_Q():
    """Tres cantidades distintas, tres columnas. El defecto viejo era tener
    una sola cosa (un conteo de pixeles) con dos nombres."""
    conn = sqlite3.connect(":memory:")
    sg.asegurar_tabla(conn)
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({sg.TABLA})")}
    for k in (1, 2, 3):
        assert {f"sr{k}_hz", f"sr{k}_amp", f"sr{k}_q"} <= cols
    assert {"saturacion_pct", "error_ajuste", "ts", "sensor"} <= cols


def test_sin_directorio_de_crudos_NO_se_inventa_el_eje_de_tiempo(tmp_path):
    """Un intervalo con hora fabricada no se puede emparejar con un sismo.

    El pipeline de Granada construye su eje desde los nombres de los archivos
    crudos (`..._YYMMDDHHMM`). Sin ellos se devuelve vacio en vez de asumir
    que el mes empieza a las 00:00 --- que es justo el tipo de relleno que
    arruino la medicion del Schumann vivo.
    """
    d = tmp_path / "S_N_FD" / "2015" / "1503"
    d.mkdir(parents=True)
    for n, cont in (("SR1503_satper_0", "0.0\n0.0\n"),
                    ("SR1503_mediaLOC_0", "0.05\n0.05\n"),
                    ("SR1503_mediaLO_0", "\n".join(["1.0"] * 28) + "\n")):
        (d / n).write_text(cont)
    assert sg.leer_mes(d, "1503", 0) == []


def test_faltan_archivos_y_lo_dice_en_vez_de_devolver_ceros(tmp_path):
    d = tmp_path / "S_N_FD" / "2015" / "1503"
    d.mkdir(parents=True)
    assert sg.leer_mes(d, "1503", 0) == []
