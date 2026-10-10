"""Pipeline Schumann para la estación Eskdalemuir (BGS, 128 Hz) — método Sierra Nevada.

Método: el publicado para Sierra Nevada (github.com/asalinas62/Sierra_Nevada_SR,
GPL-3.0; copia local en data/schumann_eskdalemuir/pipeline_granada/ con su
LICENSE): FFT Welch en la banda calibrada 6-25 Hz con ventana Hann de 10 s →
quitar bandas antropogénicas (red europea 50 Hz) → ajuste LORENTZIANO TRIPLE
+ baseline lineal por intervalo de 10 min → parámetros con error de ajuste.

Adaptación a 128 Hz: nventa=4096 → df=0,03125 Hz, la MISMA resolución por
bin que Granada (256 Hz / 8192). Ventana de 10 s = 1280 muestras.

Lo que está VERIFICADO hoy vs lo que falta (regla 0):
  * VERIFICADO: la cadena espectro→antropo→lorentziano, contra espectros
    SINTÉTICOS de lorentzianas conocidas (`.venv/bin/python
    deploy/procesar_eskdalemuir.py --prueba-sintetica`): recupera las
    frecuencias a <0,05 Hz con ruido y picos antropogénicos encima.
  * FALTA: el LECTOR del formato crudo de BGS. No hay documentación del
    formato y escribirlo antes de ver el 2025.zip (21,3 GB, en descarga)
    sería inventar. `leer_archivo()` es un stub que se niega a fingir; cuando
    el zip llegue se inspecciona y se completa SOLO esa función.

Calibración, declarada: las constantes de respuesta de las bobinas de
Granada NO aplican a las de Eskdalemuir. Las FRECUENCIAS (posición de los
picos) son independientes de calibración; la amplitud queda en unidades
relativas de la estación (el test del precursor compara ventanas de la
MISMA estación, así que la escala absoluta se cancela; la respuesta ~1/f
distorsiona amp y Q — por eso el veredicto pesa las frecuencias).

Licencia del dato: Open Government Licence — «Contains data supplied by
UKRI.» Item NGDC 192216, DOI 10.5285/c80cd579-c647-4800-88f7-012ea304b22b.

Uso:
  deploy/procesar_eskdalemuir.py --prueba-sintetica
  deploy/procesar_eskdalemuir.py --procesar <dir_extraido> <db_out>   # cuando el lector exista
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, "/home/deamon/workspaces")

from sentinel_omega.infrastructure.api.schumann_granada import (  # noqa: E402
    ERROR_AJUSTE_VECES_MEDIANA,
    RANGOS_HZ,
    SATURACION_MAXIMA_PCT,
)

# ── Parámetros del método (los de Granada, re-escalados a 128 Hz) ────────────
FM = 128                       # Hz de muestreo de las bobinas de Eskdalemuir
NVENTA = 4096                  # → df = 128/4096 = 0,03125 Hz (igual que Granada)
DF = FM / NVENTA
BANDA = (6.0, 25.0)            # banda calibrada (Hz)
BANDA_AJUSTE = (6.35, 23.75)   # banda de ajuste (márgenes de Granada)
VENTANA_S = 10.0               # ventana Hann, segundos (Granada: 10 s)
DIVI_HORA = 6                  # intervalos de 10 min por hora

FRE = np.arange(BANDA[0], BANDA[1] + DF / 2, DF)
POS_AJUSTE = (int(round((BANDA_AJUSTE[0] - BANDA[0]) / DF)),
              int(round((BANDA_AJUSTE[1] - BANDA[0]) / DF)))
FRE_AJUSTE = FRE[POS_AJUSTE[0]:POS_AJUSTE[1] + 1]

# Ruido antropogénico (red 50 Hz, Europa — Granada y Escdalemuir comparten red):
# bandas contaminadas y sus referencias limpias (Antropo.py de Granada).
_ANTRO = ((14.55, 15.35), (16.50, 16.90))
_REFER = ((13.50, 13.90), (15.80, 16.40))
_FACFIL = 2.5

# Valores iniciales del ajuste (los de Granada: los picos son físicos).
_INI_F = (8.011, 14.2, 20.63)
_INI_S = (1.78, 1.94, 2.56)

TABLA = "tbl_schumann_eskdalemuir"
DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLA} (
  ts            TEXT NOT NULL,
  sensor        INTEGER NOT NULL,
  sr1_hz        REAL, sr2_hz   REAL, sr3_hz   REAL,
  sr1_amp       REAL, sr2_amp  REAL, sr3_amp  REAL,
  sr1_q         REAL, sr2_q    REAL, sr3_q    REAL,
  saturacion_pct REAL,
  error_ajuste  REAL,
  PRIMARY KEY (ts, sensor)
)"""


def _hann(m: int) -> np.ndarray:
    v = 1.0 - np.cos(np.arange(m) * np.pi / m) ** 2
    return v / np.sqrt(np.sum(v ** 2) / m)


def espectros_de_hora(muestras: np.ndarray) -> Tuple[List[np.ndarray], List[float]]:
    """Una hora de muestras → (espectros por intervalo de 10 min, sat % c/u).

    Welch como en Reading_Fourier.py: ventana Hann de 10 s, solape 50 %,
    promedio de |FFT|²; se excluyen los segmentos saturados del promedio y
    su fracción es la saturación del intervalo.
    """
    mw = int(VENTANA_S * FM)
    pw = mw // 2
    w = _hann(mw)
    nf = NVENTA // 2 + 1
    nhoradivi = (FM * 3600) // DIVI_HORA
    out: List[np.ndarray] = []
    sats: List[float] = []
    lim = 0.999 * np.iinfo(muestras.dtype).max if muestras.dtype.kind in "iub" \
        else None
    for d in range(DIVI_HORA):
        trozo = muestras[d * nhoradivi:(d + 1) * nhoradivi].astype(float)
        if trozo.size < nhoradivi:
            break
        acc = np.zeros(nf)
        nseg = nsat = 0
        for i0 in range(0, nhoradivi - mw + 1, pw):
            seg = trozo[i0:i0 + mw]
            if lim is not None and (seg >= lim).any():
                nsat += 1
                continue
            x = np.zeros(NVENTA)
            x[:mw] = seg * w
            acc += np.abs(np.fft.rfft(x)) ** 2
            nseg += 1
        if nseg == 0:
            out.append(np.full(len(FRE), np.nan))
            sats.append(100.0)
            continue
        spec = np.sqrt(acc * 2.0 / (nseg * FM * mw))
        sats.append(100.0 * nsat / (nsat + nseg))
        out.append(_recorte(spec))
    return out, sats


def _recorte(spec_completa: np.ndarray) -> np.ndarray:
    """Banda 6-25 Hz del espectro rfft (bin 0 = 0 Hz)."""
    df_full = FM / NVENTA
    i0 = int(round(BANDA[0] / df_full))
    i1 = int(round(BANDA[1] / df_full))
    return spec_completa[i0:i1 + 1]


def _recta(val: np.ndarray, frec: np.ndarray) -> Tuple[np.ndarray, float]:
    a = (val[-1] - val[0]) / (frec[-1] - frec[0])
    b = val[0]
    mod = a * (frec - frec[0]) + b
    de = np.max((val - mod) / mod) + np.min((val - mod) / mod)
    return mod, de


def quitar_antropogenicas(medidas: np.ndarray, sat: Sequence[float]) -> np.ndarray:
    """Antropo.py de Granada: interpola las bandas contaminadas."""
    m = np.array(medidas, dtype=float, copy=True)
    if m.ndim == 1:
        m = m.reshape(1, -1)
    antro_pos = [(int(round((a - BANDA[0]) / DF)), int(round((b - BANDA[0]) / DF)))
                 for a, b in _ANTRO]
    ref_pos = [(int(round((a - BANDA[0]) / DF)), int(round((b - BANDA[0]) / DF)))
               for a, b in _REFER]
    for i in range(m.shape[0]):
        if sat[min(i, len(sat) - 1)] >= 99.99:
            continue
        for (pa, pb), (ra, rb) in zip(antro_pos, ref_pos):
            _, desvia = _recta(m[i, ra:rb + 1], FRE[ra:rb + 1])
            mod, de = _recta(m[i, pa:pb + 1], FRE[pa:pb + 1])
            if de > _FACFIL * abs(desvia):
                m[i, pa:pb + 1] = mod
    return m


def ajustar_lorentziana(espectro: np.ndarray) -> Optional[Dict[str, float]]:
    """Lorentz_Lmfit.py de Granada: 3 lorentzianas + recta, con lmfit.

    Devuelve {sr1_hz..sr3_q, error} o None si el ajuste no converge.
    """
    from lmfit import Minimizer, Parameters

    y = np.asarray(espectro, dtype=float)[POS_AJUSTE[0]:POS_AJUSTE[1] + 1]
    if not np.all(np.isfinite(y)) or np.sum(y) <= 0:
        return None
    x = FRE_AJUSTE

    def residual(p, xx, data):
        v = p.valuesdict()
        model = (v["a1"] / (1 + ((xx - v["f1"]) ** 2) / v["s1"] ** 2)
                 + v["a2"] / (1 + ((xx - v["f2"]) ** 2) / v["s2"] ** 2)
                 + v["a3"] / (1 + ((xx - v["f3"]) ** 2) / v["s3"] ** 2)
                 + v["m"] * xx + v["n"])
        return data - model

    out: Dict[str, float] = {}
    for k in range(3):
        pos = int(round((_INI_F[k] - BANDA_AJUSTE[0]) / DF))
        pos = min(max(pos, 0), len(y) - 1)
        out[f"a{k+1}"] = float(max(y[pos], 1e-12))

    p = Parameters()
    for k in range(3):
        p.add(f"a{k+1}", value=out[f"a{k+1}"], min=0.0)
        p.add(f"f{k+1}", value=_INI_F[k],
              min=BANDA_AJUSTE[0], max=BANDA_AJUSTE[1])
        p.add(f"s{k+1}", value=_INI_S[k], min=0.05, max=10.0)
    p.add("m", value=0.0)
    p.add("n", value=0.0)

    try:
        res = Minimizer(residual, p, fcn_args=(x, y)).minimize(method="leastsq")
    except Exception:
        return None
    v = res.params
    err = float(np.sqrt(np.sum(np.asarray(residual(res.params, x, y)) ** 2)
                        / max(len(y) - 11, 1)))
    for k in range(3):
        f = float(v[f"f{k+1}"].value)
        a = float(v[f"a{k+1}"].value)
        s = abs(float(v[f"s{k+1}"].value))
        lo, hi = RANGOS_HZ[k]
        fuera = not (lo <= f <= hi)
        out[f"sr{k+1}_hz"] = None if fuera else round(f, 4)
        out[f"sr{k+1}_amp"] = round(a, 6)
        out[f"sr{k+1}_q"] = (None if (fuera or s < 1e-6) else round(f / s, 4))
    out["error_ajuste"] = round(err, 6)
    return out


def fila_de_intervalo(ts: str, sensor: int, ajuste: Optional[Dict[str, float]],
                      sat_pct: float, med_err: float) -> Optional[Dict[str, Any]]:
    """Compuertas de schumann_granada: saturación, error relativo, rangos."""
    if ajuste is None:
        return None
    lim = med_err * ERROR_AJUSTE_VECES_MEDIANA if med_err > 0 else float("inf")
    malo = sat_pct > SATURACION_MAXIMA_PCT or ajuste["error_ajuste"] > lim
    fila: Dict[str, Any] = {"ts": ts[:16], "sensor": sensor,
                            "saturacion_pct": round(sat_pct, 4),
                            "error_ajuste": ajuste["error_ajuste"]}
    for k in range(1, 4):
        f, a, q = ajuste[f"sr{k}_hz"], ajuste[f"sr{k}_amp"], ajuste[f"sr{k}_q"]
        lo, hi = RANGOS_HZ[k - 1]
        fuera = f is None or not (lo <= f <= hi)
        fila[f"sr{k}_hz"] = None if (malo or fuera) else f
        fila[f"sr{k}_amp"] = None if malo else a
        fila[f"sr{k}_q"] = None if (malo or fuera) else q
    return fila


def persistir(conn: sqlite3.Connection, filas: List[Dict[str, Any]]) -> int:
    conn.execute(DDL)
    conn.executemany(
        f"INSERT OR REPLACE INTO {TABLA} (ts, sensor, sr1_hz, sr2_hz, sr3_hz, "
        "sr1_amp, sr2_amp, sr3_amp, sr1_q, sr2_q, sr3_q, saturacion_pct, "
        "error_ajuste) VALUES (:ts,:sensor,:sr1_hz,:sr2_hz,:sr3_hz,:sr1_amp,"
        ":sr2_amp,:sr3_amp,:sr1_q,:sr2_q,:sr3_q,:saturacion_pct,:error_ajuste)",
        filas)
    conn.commit()
    return len(filas)


# ── El lector del crudo de BGS: LO ÚNICO que falta ───────────────────────────

def leer_archivo(path: Path) -> List[Tuple[str, int, np.ndarray]]:
    """Un archivo crudo de Eskdalemuir → [(timestamp ISO, sensor, muestras)].

    STUB HONESTO: el formato interno del 2025.zip no está documentado y no se
    puede escribir a ciegas. Cuando la descarga termine:

      1. unzip -l 2025.zip   → estructura
      2. file / hexdump -C del primer archivo → dtype y endianness
      3. llenar SOLO esta función (una hora o un día por archivo, sensor 0/1)

    Se niega a inventar: cualquier llamada hoy revienta con instrucciones.
    """
    raise NotImplementedError(
        f"Lector pendiente: inspecciona el formato dentro de {path} "
        "(unzip -l + hexdump del primer archivo) y completa leer_archivo(). "
        "Nada más de la cadena necesita cambios.")


# ── Modo real y prueba sintética ─────────────────────────────────────────────

def procesar(dir_o_zip: Path, db_out: Path) -> int:
    import zipfile
    conn = sqlite3.connect(db_out)
    total = 0
    zips = [dir_o_zip] if dir_o_zip.suffix == ".zip" else sorted(dir_o_zip.rglob("*"))
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for nombre in zf.namelist():
                for ts, sensor, muestras in leer_archivo(Path(nombre)):
                    specs, sats = espectros_de_hora(muestras)
                    filas = filas_de_espectros(ts, sensor, specs, sats)
                    total += persistir(conn, filas)
    conn.close()
    return total


def filas_de_espectros(ts: str, sensor: int, specs: List[np.ndarray],
                       sats: List[float]) -> List[Dict[str, Any]]:
    corregidas = quitar_antropogenicas(np.asarray(specs), sats)
    ajustes = [ajustar_lorentziana(e) for e in corregidas]
    errores = [a["error_ajuste"] for a in ajustes if a]
    med_err = float(np.median(errores)) if errores else 0.0
    filas = []
    for i, a in enumerate(ajustes):
        ts_i = _ts_mas(ts, i * 10)
        fila = fila_de_intervalo(ts_i, sensor, a, sats[i], med_err)
        if fila:
            filas.append(fila)
    return filas


def _ts_mas(ts: str, minutos: int) -> str:
    import datetime as dt
    t = dt.datetime.strptime(ts[:16], "%Y-%m-%d %H:%M") + dt.timedelta(minutes=minutos)
    return t.strftime("%Y-%m-%d %H:%M")


def prueba_sintetica() -> int:
    """Cadena completa contra lorentzianas CONOCIDAS + ruido + antropogénicos."""
    rng = np.random.default_rng(7)
    f_real = (7.9, 14.1, 20.4)
    s_real = (1.7, 1.9, 2.5)
    a_real = (1.0, 0.55, 0.30)

    def lorentz(x):
        y = 0.002 * x + 0.01
        for k in range(3):
            y += a_real[k] / (1 + ((x - f_real[k]) ** 2) / s_real[k] ** 2)
        return y

    specs, sats = [], []
    for _ in range(12):
        y = lorentz(FRE)
        y += rng.normal(0, 0.003, len(FRE))          # ruido
        # picos antropogénicos AGUDOS en la banda contaminada 14,55-15,35:
        for f_linea in (14.8, 15.0, 15.2):
            y += 0.8 * np.exp(-((FRE - f_linea) ** 2) / (2 * 0.02 ** 2))
        specs.append(y)
        sats.append(0.0)

    filas = filas_de_espectros("2025-03-01 00:00", 0, specs, sats)
    assert len(filas) == 12, f"se esperaban 12 filas, salieron {len(filas)}"
    errores_f = []
    for k in range(3):
        rec = [f[f"sr{k+1}_hz"] for f in filas]
        assert all(v is not None for v in rec), f"sr{k+1}: ajuste no convergió"
        err = max(abs(v - f_real[k]) for v in rec)
        errores_f.append(err)
        print(f"  sr{k+1}_hz: real {f_real[k]:.2f} · recuperado "
              f"{min(rec):.3f}–{max(rec):.3f} · error máx {err:.3f} Hz")
    assert max(errores_f) < 0.05, "frecuencia fuera de tolerancia"
    # el pico antropogénico de 14,8-15,2 NO debe aparecer como frecuencia:
    f2 = [f["sr2_hz"] for f in filas]
    assert all(14.4 < v < 14.9 or abs(v - 14.1) < 0.25 for v in f2), \
        "la banda antropogénica contaminó el ajuste"
    print(f"  OK: cadena verificada ({len(filas)} intervalos sintéticos, "
          "frecuencias a <0,05 Hz, antropogénicos removidos)")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if sys.argv[1] == "--prueba-sintetica":
        return prueba_sintetica()
    if sys.argv[1] == "--procesar":
        if len(sys.argv) < 4:
            print("uso: --procesar <dir_o_zip> <db_out>")
            return 1
        n = procesar(Path(sys.argv[2]), Path(sys.argv[3]))
        print(f"{n} intervalos persistidos en {TABLA}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
