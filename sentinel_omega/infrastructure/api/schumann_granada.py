"""Schumann REAL: lector de la estacion ELF de Sierra Nevada (Granada).

Por que existe este modulo
--------------------------
La resonancia Schumann es el eje del proyecto ---todo se correlaciona contra el
latido--- y hasta el 2026-10-09 no estaba medida. Lo que habia:

    fuente      una imagen JPEG de Tomsk (sos70.ru)
    metodo      contar pixeles claros en el 40 % superior
    frecuencia  FABRICADA: 7,83 + actividad x 0,02 (exacto en 583/743 filas)
    variacion   la misma actividad (21,46 %) en 564/743 filas: congelado
    memoria     86 de 4.000 firmas (2,2 %), recorrido de 0,03 Hz

Esta fuente es lo contrario: espectro calibrado y **ajuste lorentziano**.

    estacion    Sierra Nevada ELF, Universidad de Granada
    cobertura   marzo 2013 -> febrero 2017
    muestreo    256 Hz, un archivo crudo por sensor y hora
    sensores    0 = NS, 1 = EW
    banda       6-25 Hz calibrada, ajuste en 6,35-23,75
    resolucion  10 minutos (144 intervalos por dia)
    codigo      github.com/asalinas62/Sierra_Nevada_SR (GPL-3.0)
    articulo    Computers & Geosciences 2022, 10.1016/j.cageo.2022.105148

Verificado sobre el dia 2015-03-01 que trae el repo:

    parametro   media      sd       rango            distintos
    SR1 (f1)     7,9348   0,1102   7,642 - 8,162     144/144
    SR2 (f2)    14,3326   0,1021  14,071 - 14,569    144/144
    SR3 (f3)    20,4276   0,3459  19,930 - 23,537    144/144

**SR1 recorre 0,5192 Hz en UN DIA** contra los 0,03 Hz que produccion tiene en
toda su historia. Eso es un sensor funcionando.

Formato de salida del pipeline de Granada (por mes y sensor)
------------------------------------------------------------
    SR{YYMM}_satper_{s}    144*dias   % de saturacion por intervalo
    SR{YYMM}_mediaLOC_{s}  144*dias   error de ajuste por intervalo
    SR{YYMM}_mediaLO_{s}   (n,14)     parametros de las 3 lorentzianas
    SR{YYMM}_mediaLOE_{s}  (n,11)     incertidumbre por parametro

Columnas de `mediaLO` verificadas por el valor que toman:
    0,1,2 -> a1,a2,a3  amplitudes
    6,7,8 -> f1,f2,f3  frecuencias centrales (SR1, SR2, SR3)
    9,10,11 -> s1,s2,s3  anchuras  (Q = f/s)
    12,13 -> m,n  fondo lineal

Las dos compuertas de calidad NO son opcionales (regla 2): un intervalo con
saturacion o error de ajuste por encima del limite se guarda como **NULL**, no
se usa con un valor plausible.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# Columnas de `mediaLO`, verificadas contra los valores que toman (no contra
# el manual: regla dura 9).
COL_AMPLITUD = (0, 1, 2)
COL_FRECUENCIA = (6, 7, 8)
COL_ANCHURA = (9, 10, 11)
N_COLS_LO = 14
N_COLS_LOE = 11
INTERVALO_MIN = 10

# ─── Compuertas de calidad, y el umbral del error es RELATIVO ────────────────
#
# Un intervalo saturado o mal ajustado no es una medicion: es un hueco. Pero el
# limite del error de ajuste NO puede ser absoluto, y casi lo escribi asi.
# Medido sobre el dia de muestra (2015-03-01, 144 intervalos por sensor):
#
#     sensor 0 (NS)   error p50 = 0,0770   p95 = 0,1222   max = 0,2015
#     sensor 1 (EW)   error p50 = 0,2554   p95 = 0,3919   max = 0,4736
#
# Son escalas distintas: el error tipico del sensor 1 es 3,3x el del 0. Un
# absoluto de 0,25 descartaba el **0 %** del sensor 0 y el **53,5 %** del 1. Y
# lo decisivo: de los 288 intervalos solo **3** tienen f1 fuera del rango
# fisico, y ninguno de los 23 con error alto en el sensor 0. O sea que el error
# **no marca dato malo: marca la escala del sensor**.
#
# Es el mismo error que mataba al padre con `pe - pc >= 0,05`: una vara
# absoluta sobre poblaciones que viven en escalas distintas. Asi que:
#
#   * compuerta PRIMARIA: el rango fisico (abajo), que es absoluto porque la
#     fisica lo es --- SR1 no esta en 23 Hz;
#   * compuerta SECUNDARIA: el error, RELATIVO a la mediana de ESE sensor en
#     ESE mes. Marca el ajuste anomalo para su propio sensor, no el que tiene
#     la escala mas alta.
SATURACION_MAXIMA_PCT = 5.0
ERROR_AJUSTE_VECES_MEDIANA = 3.0

# Rangos fisicos. SR1 nominal 7,83; SR2 14,3; SR3 20,8. Un ajuste que se sale
# de aqui es un fallo del ajuste, no una resonancia nueva --- el dia de muestra
# ya trae un f3 en 23,54 que hay que descartar.
RANGOS_HZ = ((7.0, 9.0), (13.0, 16.0), (19.0, 22.5))

TABLA = "tbl_schumann_granada"

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLA} (
  ts            TEXT NOT NULL,          -- inicio del intervalo de 10 min, UTC
  sensor        INTEGER NOT NULL,       -- 0 = NS, 1 = EW
  sr1_hz        REAL, sr2_hz   REAL, sr3_hz   REAL,
  sr1_amp       REAL, sr2_amp  REAL, sr3_amp  REAL,
  sr1_q         REAL, sr2_q    REAL, sr3_q    REAL,
  saturacion_pct REAL,
  error_ajuste  REAL,
  PRIMARY KEY (ts, sensor)
)
"""


def asegurar_tabla(conn: sqlite3.Connection) -> None:
    conn.execute(DDL)
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLA}_ts ON {TABLA}(ts)")
    conn.commit()


def _leer(path: Path):
    import numpy as np
    return np.genfromtxt(path)


def leer_mes(dir_fd: Path, yymm: str, sensor: int) -> List[Dict]:
    """Un mes de un sensor -> filas listas para insertar.

    `dir_fd` es el directorio con los `SR{yymm}_*` del pipeline de Granada.
    El tiempo NO se inventa: sale de los nombres de los archivos crudos, que
    llevan `YYMMDDHHMM`. Sin ellos no se devuelve nada --- un intervalo sin
    hora cierta no sirve para emparejar con un sismo.
    """
    import numpy as np

    sat_p = dir_fd / f"SR{yymm}_satper_{sensor}"
    lo_p = dir_fd / f"SR{yymm}_mediaLO_{sensor}"
    loc_p = dir_fd / f"SR{yymm}_mediaLOC_{sensor}"
    for p in (sat_p, lo_p, loc_p):
        if not p.exists():
            logger.warning("falta %s: no se lee el mes %s sensor %s", p.name,
                           yymm, sensor)
            return []

    sat = np.atleast_1d(_leer(sat_p))
    loc = np.atleast_1d(_leer(loc_p))
    lo = _leer(lo_p)
    n = len(sat)
    if n == 0 or lo.size != n * N_COLS_LO:
        logger.warning("mes %s sensor %s: %d intervalos pero mediaLO tiene %d "
                       "valores (esperados %d)", yymm, sensor, n, lo.size,
                       n * N_COLS_LO)
        return []
    lo = lo.reshape(n, N_COLS_LO)

    horas = _horas_de_crudos(dir_fd, yymm, sensor, n)
    if horas is None:
        return []

    # El limite del error se calibra contra ESTE sensor en ESTE mes. Con un
    # absoluto, el sensor EW perdia la mitad de sus intervalos por tener su
    # escala de error 3x mas alta, sin que sus frecuencias fueran peores.
    med_err = float(np.median(loc[np.isfinite(loc)])) if np.any(np.isfinite(loc)) else 0.0
    lim_err = med_err * ERROR_AJUSTE_VECES_MEDIANA if med_err > 0 else float("inf")
    logger.info("mes %s sensor %s: error de ajuste mediano %.4f -> limite "
                "%.4f (%.1fx la mediana)", yymm, sensor, med_err, lim_err,
                ERROR_AJUSTE_VECES_MEDIANA)

    filas = []
    for i in range(n):
        s_pct = float(sat[i])
        err = float(loc[i])
        malo = s_pct > SATURACION_MAXIMA_PCT or err > lim_err
        fila = {"ts": horas[i], "sensor": sensor,
                "saturacion_pct": round(s_pct, 4),
                "error_ajuste": round(err, 6)}
        for k in range(3):
            f = float(lo[i, COL_FRECUENCIA[k]])
            a = float(lo[i, COL_AMPLITUD[k]])
            w = float(lo[i, COL_ANCHURA[k]])
            lo_hz, hi_hz = RANGOS_HZ[k]
            fuera = not (lo_hz <= f <= hi_hz)
            # Faltante = NULL. Nunca un valor plausible rellenado (regla 2).
            fila[f"sr{k+1}_hz"] = None if (malo or fuera) else round(f, 4)
            fila[f"sr{k+1}_amp"] = None if malo else round(a, 6)
            fila[f"sr{k+1}_q"] = (None if (malo or fuera or abs(w) < 1e-6)
                                  else round(f / abs(w), 4))
        filas.append(fila)
    return filas


def _horas_de_crudos(dir_fd: Path, yymm: str, sensor: int,
                     n_intervalos: int) -> Optional[List[str]]:
    """Las horas, desde los nombres de los archivos crudos (`..._YYMMDDHHMM`).

    El pipeline de Granada construye su eje de tiempo igual (`Packaging.py`).
    Si el directorio de crudos no esta, se devuelve None en vez de fabricar un
    eje: un intervalo con hora inventada no se puede emparejar con un sismo.
    """
    base = dir_fd.parent.parent.parent          # .../S_N_FD/AAAA/AAMM -> raiz
    for cand in (base / "S_N_Data" / f"20{yymm[:2]}" / yymm,
                 dir_fd.parent.parent.parent / "S_N_Data" / f"20{yymm[:2]}" / yymm):
        if cand.is_dir():
            dir_datos = cand
            break
    else:
        logger.warning("no se encuentra el directorio de crudos para %s: "
                       "sin eje de tiempo cierto, no se ingiere", yymm)
        return None

    pat = re.compile(rf"_sensor_{sensor}_(\d{{10}})$")
    sellos = sorted({m.group(1) for f in dir_datos.iterdir()
                     if (m := pat.search(f.name))})
    if not sellos:
        logger.warning("sin archivos crudos del sensor %s en %s", sensor,
                       dir_datos)
        return None

    # Cada archivo crudo cubre una hora -> 6 intervalos de 10 min.
    import datetime as dt
    horas: List[str] = []
    for s in sellos:
        t0 = dt.datetime.strptime(s, "%y%m%d%H%M").replace(minute=0, second=0)
        for k in range(60 // INTERVALO_MIN):
            horas.append((t0 + dt.timedelta(minutes=k * INTERVALO_MIN))
                         .strftime("%Y-%m-%d %H:%M"))
    if len(horas) < n_intervalos:
        logger.warning("%s sensor %s: %d intervalos pero solo %d horas de "
                       "crudos; se ingiere lo que cuadra", yymm, sensor,
                       n_intervalos, len(horas))
        return horas + [None] * 0 if False else horas[:len(horas)] or None
    return horas[:n_intervalos]


def ingerir(conn: sqlite3.Connection, dir_fd: Path, yymm: str,
            sensores=(0, 1)) -> Dict[str, int]:
    """Ingiere un mes. Idempotente (`INSERT OR REPLACE` por ts+sensor)."""
    asegurar_tabla(conn)
    total = {"filas": 0, "con_sr1": 0, "descartadas": 0}
    for sensor in sensores:
        filas = leer_mes(Path(dir_fd), yymm, sensor)
        for f in filas:
            conn.execute(
                f"INSERT OR REPLACE INTO {TABLA} (ts, sensor, sr1_hz, sr2_hz, "
                "sr3_hz, sr1_amp, sr2_amp, sr3_amp, sr1_q, sr2_q, sr3_q, "
                "saturacion_pct, error_ajuste) "
                "VALUES (:ts,:sensor,:sr1_hz,:sr2_hz,:sr3_hz,:sr1_amp,"
                ":sr2_amp,:sr3_amp,:sr1_q,:sr2_q,:sr3_q,:saturacion_pct,"
                ":error_ajuste)", f)
            total["filas"] += 1
            if f["sr1_hz"] is not None:
                total["con_sr1"] += 1
            else:
                total["descartadas"] += 1
    conn.commit()
    return total


# ─── La ruta buena: los `.npz` ya procesados ─────────────────────────────────
#
# `Packaging.py` guarda, por mes y sensor, `np.savez(..., *sal)` con
#
#     sal = (sat, fre, freajus, rs, rs_LO, parLO, parLOC, parLOE, pr, tiempo)
#
# o sea las claves `arr_0` .. `arr_9`:
#
#     arr_0  sat       % de saturacion por intervalo
#     arr_1  fre       eje de frecuencia de calibracion (6-25 Hz)
#     arr_2  freajus   eje de frecuencia del ajuste (6,35-23,75)
#     arr_3  rs        espectro medio por intervalo
#     arr_4  rs_LO     curva lorentziana ajustada
#     arr_5  parLO     (n, 14) parametros --- esto es lo que se usa
#     arr_6  parLOC    error de ajuste por intervalo
#     arr_7  parLOE    (n, 11) incertidumbre por parametro
#     arr_8  pr        amplitud y frecuencia de pico leidas de la curva
#     arr_9  tiempo    MARCAS DE TIEMPO, como texto
#
# `arr_9` es la razon de preferir esta ruta: las horas salen de los `_info.txt`
# del instrumento (`Packaging.py` las lee del archivo, caracteres 22-45), asi
# que **no hay que reconstruir el eje de tiempo desde los nombres de archivo**.
# Una hora cierta es la diferencia entre poder emparejar con un sismo y no.
NPZ_SAT, NPZ_PARLO, NPZ_PARLOC, NPZ_TIEMPO = "arr_0", "arr_5", "arr_6", "arr_9"

# El nombre real del archivo publicado por la UGR es
# `SN_{YYMM}_LO_6_1_{sensor}.npz` ---el `LO_6_1` es la banda de ajuste--- y no
# `SN_{YYMM}_{sensor}.npz` como construye `Packaging.py` por defecto. Se aceptan
# las dos formas: lo que importa son el mes y el sensor, y el sensor es siempre
# el ULTIMO campo.
_RE_NPZ = re.compile(r"SN_(\d{4})_(?:.+_)?(\d)\.npz$")


def leer_npz(path_npz: Path) -> List[Dict]:
    """Un `SN_YYMM_s.npz` -> filas listas para insertar.

    Mismas compuertas que `leer_mes`: rango fisico (absoluto, porque la fisica
    lo es) y error de ajuste RELATIVO a la mediana de este sensor en este mes.
    """
    import numpy as np

    m = _RE_NPZ.search(path_npz.name)
    if not m:
        logger.warning("%s no tiene la forma SN_YYMM_s.npz", path_npz.name)
        return []
    sensor = int(m.group(2))

    try:
        z = np.load(path_npz, allow_pickle=False)
    except Exception as exc:
        logger.warning("no se pudo abrir %s: %s", path_npz.name, exc)
        return []

    faltan = [k for k in (NPZ_SAT, NPZ_PARLO, NPZ_PARLOC, NPZ_TIEMPO)
              if k not in z]
    if faltan:
        logger.warning("%s: faltan %s", path_npz.name, faltan)
        return []

    sat = np.atleast_1d(z[NPZ_SAT]).astype(float)
    loc = np.atleast_1d(z[NPZ_PARLOC]).astype(float)
    lo = np.asarray(z[NPZ_PARLO], dtype=float)
    tiempo = np.atleast_1d(z[NPZ_TIEMPO])
    n = len(sat)
    if lo.ndim == 1:
        if lo.size != n * N_COLS_LO:
            logger.warning("%s: parLO con %d valores para %d intervalos",
                           path_npz.name, lo.size, n)
            return []
        lo = lo.reshape(n, N_COLS_LO)
    if lo.shape[0] != n or len(tiempo) != n:
        logger.warning("%s: desalineado --- sat=%d parLO=%d tiempo=%d",
                       path_npz.name, n, lo.shape[0], len(tiempo))
        return []

    med_err = float(np.median(loc[np.isfinite(loc)])) if np.any(np.isfinite(loc)) else 0.0
    lim_err = med_err * ERROR_AJUSTE_VECES_MEDIANA if med_err > 0 else float("inf")

    filas = []
    for i in range(n):
        ts = str(tiempo[i])[:16]          # "AAAA-MM-DD HH:MM"
        if len(ts) < 16 or ts[4] != "-":
            continue                      # hora ilegible: se salta, no se finge
        s_pct = float(sat[i])
        err = float(loc[i])
        malo = s_pct > SATURACION_MAXIMA_PCT or err > lim_err
        fila = {"ts": ts, "sensor": sensor,
                "saturacion_pct": round(s_pct, 4),
                "error_ajuste": round(err, 6)}
        for k in range(3):
            f = float(lo[i, COL_FRECUENCIA[k]])
            a = float(lo[i, COL_AMPLITUD[k]])
            w = float(lo[i, COL_ANCHURA[k]])
            lo_hz, hi_hz = RANGOS_HZ[k]
            fuera = not (lo_hz <= f <= hi_hz)
            fila[f"sr{k+1}_hz"] = None if (malo or fuera) else round(f, 4)
            fila[f"sr{k+1}_amp"] = None if malo else round(a, 6)
            fila[f"sr{k+1}_q"] = (None if (malo or fuera or abs(w) < 1e-6)
                                  else round(f / abs(w), 4))
        filas.append(fila)
    logger.info("%s: %d intervalos, error mediano %.4f (limite %.4f)",
                path_npz.name, len(filas), med_err, lim_err)
    return filas


def ingerir_npz_dir(conn: sqlite3.Connection, dir_npz: Path) -> Dict[str, int]:
    """Ingiere todos los `SN_*.npz` de un directorio. Idempotente."""
    asegurar_tabla(conn)
    tot = {"archivos": 0, "filas": 0, "con_sr1": 0, "descartadas": 0}
    for p in sorted(Path(dir_npz).rglob("SN_*.npz")):
        filas = leer_npz(p)
        if not filas:
            continue
        tot["archivos"] += 1
        conn.executemany(
            f"INSERT OR REPLACE INTO {TABLA} (ts, sensor, sr1_hz, sr2_hz, "
            "sr3_hz, sr1_amp, sr2_amp, sr3_amp, sr1_q, sr2_q, sr3_q, "
            "saturacion_pct, error_ajuste) VALUES (:ts,:sensor,:sr1_hz,"
            ":sr2_hz,:sr3_hz,:sr1_amp,:sr2_amp,:sr3_amp,:sr1_q,:sr2_q,"
            ":sr3_q,:saturacion_pct,:error_ajuste)", filas)
        tot["filas"] += len(filas)
        tot["con_sr1"] += sum(1 for f in filas if f["sr1_hz"] is not None)
        tot["descartadas"] += sum(1 for f in filas if f["sr1_hz"] is None)
        conn.commit()
    return tot
