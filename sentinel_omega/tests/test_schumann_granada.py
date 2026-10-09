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


# ─── La ruta de los `.npz` procesados ────────────────────────────────────────


def _npz_sintetico(path, n=6, sensor=0, f1=7.9, err=0.05, sat=0.0):
    """Un `SN_YYMM_s.npz` con la estructura real de `Packaging.py`.

    `sal = (sat, fre, freajus, rs, rs_LO, parLO, parLOC, parLOE, pr, tiempo)`
    -> claves `arr_0` .. `arr_9`.
    """
    import numpy as np
    parlo = np.zeros((n, sg.N_COLS_LO), dtype=float)
    for i in range(n):
        parlo[i, sg.COL_AMPLITUD[0]] = 0.37
        parlo[i, sg.COL_FRECUENCIA[0]] = f1 + i * 0.01
        parlo[i, sg.COL_FRECUENCIA[1]] = 14.33
        parlo[i, sg.COL_FRECUENCIA[2]] = 20.43
        parlo[i, sg.COL_ANCHURA[0]] = 1.2
        parlo[i, sg.COL_ANCHURA[1]] = 1.28
        parlo[i, sg.COL_ANCHURA[2]] = 1.49
    tiempo = np.array(
        [f"2014-06-0{1 + i // 144} {i % 24:02d}:{(i * 10) % 60:02d}:00.000000"
         for i in range(n)], dtype=str)
    import numpy as _np
    _np.savez(path,
              _np.full(n, sat),              # arr_0 sat
              _np.arange(6.0, 25.1, 0.1),    # arr_1 fre
              _np.arange(6.35, 23.8, 0.1),   # arr_2 freajus
              _np.zeros((n, 5)),             # arr_3 rs
              _np.zeros((n, 5)),             # arr_4 rs_LO
              parlo,                         # arr_5 parLO
              _np.full(n, err),              # arr_6 parLOC
              _np.zeros((n, sg.N_COLS_LOE)), # arr_7 parLOE
              _np.zeros((n, 6)),             # arr_8 pr
              tiempo)                        # arr_9 tiempo


def test_el_npz_trae_su_PROPIO_eje_de_tiempo(tmp_path):
    """`arr_9` son las marcas del instrumento, no una reconstruccion.

    Es la razon de preferir la ruta `.npz`: `Packaging.py` las lee de los
    `_info.txt` del equipo. Una hora cierta es la diferencia entre poder
    emparejar con un sismo y no poder.
    """
    p = tmp_path / "SN_1406_0.npz"
    _npz_sintetico(p, n=6)
    filas = sg.leer_npz(p)
    assert len(filas) == 6
    assert filas[0]["ts"].startswith("2014-06-01")
    assert len(filas[0]["ts"]) == 16          # "AAAA-MM-DD HH:MM"
    assert filas[0]["sensor"] == 0


def test_el_npz_respeta_el_rango_fisico(tmp_path):
    """Un f1 en 23 Hz es un fallo del ajuste: NULL, no un dato."""
    p = tmp_path / "SN_1406_1.npz"
    _npz_sintetico(p, n=4, sensor=1, f1=23.0)
    filas = sg.leer_npz(p)
    assert len(filas) == 4
    assert all(f["sr1_hz"] is None for f in filas), (
        "se guardo una SR1 fuera del rango fisico")
    # SR2 y SR3 sí están en rango y se conservan
    assert all(f["sr2_hz"] is not None for f in filas)


def test_el_npz_descarta_lo_SATURADO(tmp_path):
    p = tmp_path / "SN_1406_0.npz"
    _npz_sintetico(p, n=3, sat=50.0)
    filas = sg.leer_npz(p)
    assert all(f["sr1_hz"] is None for f in filas)
    assert all(f["saturacion_pct"] == 50.0 for f in filas), (
        "la saturacion medida tiene que quedar registrada aunque invalide")


def test_el_sensor_sale_del_NOMBRE_y_un_nombre_raro_no_pasa(tmp_path):
    p = tmp_path / "SN_1406_1.npz"
    _npz_sintetico(p, n=2, sensor=1)
    assert sg.leer_npz(p)[0]["sensor"] == 1
    malo = tmp_path / "cualquiera.npz"
    _npz_sintetico(malo, n=2)
    assert sg.leer_npz(malo) == []


def test_un_npz_desalineado_se_rechaza_entero(tmp_path):
    """Si sat, parLO y tiempo no tienen el mismo n, no se adivina."""
    import numpy as np
    p = tmp_path / "SN_1406_0.npz"
    np.savez(p, np.zeros(10), np.zeros(5), np.zeros(5),
             np.zeros((10, 5)), np.zeros((10, 5)),
             np.zeros((7, sg.N_COLS_LO)),      # parLO con 7 en vez de 10
             np.zeros(10), np.zeros((10, 11)), np.zeros((10, 6)),
             np.array(["2014-06-01 00:00:00.0"] * 10, dtype=str))
    assert sg.leer_npz(p) == []
