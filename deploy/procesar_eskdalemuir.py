"""Pipeline Schumann para la estación Eskdalemuir (BGS, 128 Hz) — método Sierra Nevada.

Método: el publicado para Sierra Nevada (github.com/asalinas62/Sierra_Nevada_SR,
GPL-3.0; copia local en data/schumann_eskdalemuir/pipeline_granada/ con su
LICENSE): FFT Welch en la banda calibrada 6-25 Hz con ventana Hann de 10 s →
quitar bandas antropogénicas (red europea 50 Hz) → ajuste LORENTZIANO TRIPLE
+ baseline lineal por intervalo de 10 min → parámetros con error de ajuste.

Adaptación a 128 Hz: nventa=4096 → df=0,03125 Hz, la MISMA resolución por
bin que Granada (256 Hz / 8192). Ventana de 10 s = 1280 muestras.

Lo que está VERIFICADO (regla 0):
  * La cadena espectro→antropo→lorentziano, contra espectros SINTÉTICOS de
    lorentzianas conocidas: frecuencias recuperadas a <0,01 Hz con ruido y
    picos de red encima (`--prueba-sintetica`).
  * El LECTOR contra el crudo real de BGS (2026-10-10): el `.ssc` es CSV de
    espacios (`%hh %mm %ss %tttt X[mV] Y[mV]`, 128 Hz), documentado por el
    propio BGS en `code/ProcessInductionCoil_oneday_MFS05coils_128Hz.py`
    (incluido en el zip). Las tablas de calibración de las bobinas MFS05
    (`05028/05038_2403_L_15V.dat`, respuesta mV/nT) calibran el espectro a
    nT/√Hz --- igual que el producto publicado de BGS (pT²/Hz).
  * La física del primer día real (2025-01-01) es la prueba: SR1/SR2/SR3
    tienen que salir cerca de 7,8/14,1/20,3 Hz. Ver §bitácora del 10-oct.

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


def espectros_de_hora(muestras: np.ndarray,
                      h_coil: Optional[np.ndarray] = None) -> Tuple[List[np.ndarray], List[float]]:
    """Una hora de muestras (mV) → (espectros por intervalo de 10 min, sat % c/u).

    Welch como en Reading_Fourier.py: ventana Hann de 10 s, solape 50 %,
    promedio de |FFT|². Se excluyen del promedio los segmentos con saturación
    (|mV| >= 14.000: el ADC es de ±15 V) o con NaN, y su fracción es la
    saturación del intervalo. Con `h_coil` (respuesta mV/nT en los bins de
    FRE), el espectro sale CALIBRADO en nT/√Hz: PSD_mV²/Hz ÷ h² = nT²/Hz.
    """
    mw = int(VENTANA_S * FM)
    pw = mw // 2
    w = _hann(mw)
    nf = NVENTA // 2 + 1
    nhoradivi = (FM * 3600) // DIVI_HORA
    out: List[np.ndarray] = []
    sats: List[float] = []
    for d in range(DIVI_HORA):
        trozo = muestras[d * nhoradivi:(d + 1) * nhoradivi].astype(float)
        if trozo.size < nhoradivi:
            break
        acc = np.zeros(nf)
        nseg = nsat = 0
        for i0 in range(0, nhoradivi - mw + 1, pw):
            seg = trozo[i0:i0 + mw]
            if (not np.all(np.isfinite(seg))) or (np.abs(seg) >= SAT_MV).any():
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
        spec = _recorte(np.sqrt(acc * 2.0 / (nseg * FM * mw)))   # mV/√Hz, banda 6-25
        if h_coil is not None:
            # h en mV/nT sobre los mismos 609 bins de FRE: mV/√Hz ÷ (mV/nT) = nT/√Hz
            spec = spec / np.where(h_coil > 0, h_coil, np.nan)
        sats.append(100.0 * nsat / (nsat + nseg))
        out.append(spec)
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


# ── El lector del crudo de BGS: documentado por el propio BGS ────────────────
#
# El zip trae `code/ProcessInductionCoil_oneday_MFS05coils_128Hz.py` (Ciaran
# Beggan, BGS, 2024) y DOS tablas de calibración de las bobinas GFZ MFS05
# instaladas en agosto de 2024 (se corren a 128 Hz):
#   * `05038_2403_L_15V.dat` → canal X (Norte-Sur)
#   * `05028_2403_L_15V.dat` → canal Y (Este-Oeste)
# El `.ssc` es CSV de espacios: `%hh %mm %ss %tttt X[mV] Y[mV]` con %tttt en
# DIEZMILÉSIMAS de segundo (128 Hz = 7,8125 ms; 0022 + 78 → 0100, medido).
# La calibración convierte mV → nT: PSD_mV²/Hz ÷ h(f)² [mV/nT]² = nT²/Hz, el
# mismo producto que BGS publica en pT²/Hz.

SAT_MV = 14_000.0        # el ADC es de ±15 V (nombre del .dat: «15V»)
DAT_X = "05038_2403_L_15V.dat"   # canal X = Norte-Sur  -> sensor 0
DAT_Y = "05028_2403_L_15V.dat"   # canal Y = Este-Oeste -> sensor 1


def calibracion_coil(path_dat: Path) -> np.ndarray:
    """Tabla de respuesta de la bobina -> h(f) interpolada en los bins de FRE.

    Columnas del .dat (fixed-width, 18 líneas de encabezado): X[Hz], P[deg],
    Mag[mV/nT]. Se usa la 1ª (frecuencia) y la 3ª (magnitud), como en el
    CoilCalibration_MF5coils de BGS.
    """
    import pandas as pd
    from scipy.interpolate import interp1d
    tabla = pd.read_fwf(path_dat, header=18, widths=[15, 15, 15])
    f = interp1d(tabla.values[:, 0].astype(float),
                 tabla.values[:, 2].astype(float), bounds_error=False)
    h = f(FRE)
    h[~np.isfinite(h)] = 0.0
    return h


def leer_ssc_dia(path: Path) -> List[Tuple[str, int, np.ndarray]]:
    """Un `.ssc` diario -> [(ts ISO de la hora, sensor, hora de muestras mV)].

    Devuelve la hora que ARRANCA cada bloque horario con datos; el resto de
    la cadena (espectros_de_hora) rebana en intervalos de 10 min y salta los
    incompletos. Sensor 0 = X (NS), 1 = Y (EW), la misma convención de
    orientaciones que Granada (0 = NS, 1 = EW).
    """
    import pandas as pd
    df = pd.read_csv(path, sep=r"\s+", header=0,
                     usecols=["X[mV]", "Y[mV]"], engine="c")
    n = len(df)
    if n < FM * 3600:
        print(f"  {path.name}: {n:,} muestras (< 1 h) --- se omite")
        return []
    x = pd.to_numeric(df["X[mV]"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(df["Y[mV]"], errors="coerce").to_numpy(dtype=float)
    fecha = path.name.split("-")[1]                    # '20250101'
    base = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"
    nhora = FM * 3600
    out = []
    for h in range(24):
        trozo0, trozo1 = h * nhora, min((h + 1) * nhora, n)
        if trozo1 - trozo0 < nhora:
            break                                     # hora incompleta: se omite
        ts = f"{base} {h:02d}:00"
        out.append((ts, 0, x[trozo0:trozo1]))
        out.append((ts, 1, y[trozo0:trozo1]))
    return out


# ── Modo real y prueba sintética ─────────────────────────────────────────────

def entradas_remotas(zip_local: Path) -> List[Dict]:
    """Directorio central del 2025.zip vía Range (HTTP 206): no espera al zip.

    El server sirve bytes arbitrarios, y el EOCD vive al final: se traen los
    últimos 6 MB, se parsea el EOCD64 y el directorio central completo. Da
    la lista EXACTA de entradas con offsets y tamaños comprimidos. El
    directorio central es estático: se cachea junto al zip (JSON) y las
    corridas siguientes no vuelven a tocar la red.
    """
    import json
    import struct
    import urllib.request

    cache = zip_local.parent / "esk_entradas.json"
    if cache.exists():
        try:
            return json.load(open(cache))
        except Exception:
            pass                                  # cache ilegible: se refetch

    total = 21_314_692_275
    url = ("https://webservices.bgs.ac.uk/accessions/download/192216"
           "?fileName=2025.zip")
    req = urllib.request.Request(url, headers={"User-Agent": UA_DESCARGA})
    req.add_header("Range", f"bytes={total - 6_000_000}-{total - 1}")
    with urllib.request.urlopen(req, timeout=300) as r:
        cola = r.read()
    k = cola.rfind(b"PK\x06\x06")
    if k < 0:
        raise RuntimeError("no se encontró el EOCD64 en la cola del zip")
    # Campos tras la firma: size(Q) ver(H) ver_n(H) disco(I) cd_disco(I)
    # n_disco(Q) n_total(Q) tam_cd(Q) off_cd(Q)
    (size, ver, ver_n, disco, cd_disco,
     n_disco, n_total, tam_cd, off_cd) = struct.unpack(
        "<QHHIIQQQQ", cola[k + 4:k + 4 + 52])
    req2 = urllib.request.Request(url, headers={"User-Agent": UA_DESCARGA})
    req2.add_header("Range", f"bytes={off_cd}-{off_cd + tam_cd - 1}")
    with urllib.request.urlopen(req2, timeout=300) as r:
        cd = r.read()
    entradas, i = [], 0
    while i < len(cd) and cd[i:i + 4] == b"PK\x01\x02":
        (ver, ver_n, flags, comp, mt, md, crc, csize, usize,
         nlen, elen, clen, disco, iattr, eattr, off) = struct.unpack(
            "<HHHHHHIIIHHHHHII", cd[i + 4:i + 46])
        nombre = cd[i + 46:i + 46 + nlen].decode("utf-8", "replace")
        # offset ZIP64 (0xFFFFFFFF): buscarlo en el extra field
        if off == 0xFFFFFFFF:
            e = cd[i + 46 + nlen:i + 46 + nlen + elen]
            j = 0
            while j + 4 <= len(e):
                eid, tam = struct.unpack("<HH", e[j:j + 4])
                if eid == 0x0001:
                    off = struct.unpack("<Q", e[j + 4:j + 12])[0]
                    break
                j += 4 + tam
        entradas.append({"nombre": nombre, "comp": comp, "csize": csize,
                         "usize": usize, "off": off})
        i += 46 + nlen + elen + clen
    json.dump(entradas, open(cache, "w"))
    return entradas


UA_DESCARGA = "Mozilla/5.0 (X11; Linux x86_64) SentinelOmega-research/1.0"


def extraer_si_completo(zip_local: Path, entrada: Dict, destino: Path) -> bool:
    """Extrae la entrada SOLO si su rango está íntegro en el parcial local.

    El header LOCAL manda en offsets reales (su `elen` puede diferir del del
    directorio central); el tamaño comprimido se valida contra el central.
    """
    import struct as _st
    import zlib as _zl
    with open(zip_local, "rb") as f:
        f.seek(entrada["off"])
        hdr = f.read(30)
        if hdr[:4] != b"PK\x03\x04":
            raise RuntimeError(f"firma inesperada en {entrada['off']}")
        (_, _, comp, _, _, _, csize, usize, nlen, elen) = \
            _st.unpack("<HHHHHIIIHH", hdr[4:30])
        csize = csize or entrada["csize"]
        fin = entrada["off"] + 30 + nlen + elen + csize + 32
        if zip_local.stat().st_size < fin:
            return False
        f.seek(entrada["off"] + 30 + nlen + elen)
        data = f.read(csize)
    raw = _zl.decompress(data, -15) if comp == 8 else data
    if len(raw) != entrada["usize"]:
        raise RuntimeError(f"{entrada['nombre']}: {len(raw):,} != {entrada['usize']:,}")
    destino.write_bytes(raw)
    return True


def dias_en_db(conn: sqlite3.Connection) -> set:
    """Días COMPLETOS procesados: se marcan al terminar, no al empezar.

    La marca vive aparte de las filas: si el proceso muere a media hora de un
    día, sus filas parciales quedan pero el día NO está marcado, y la
    siguiente corrida lo repite entero (INSERT OR REPLACE lo hace idempotente).
    """
    conn.execute("CREATE TABLE IF NOT EXISTS esk_dias_procesados ("
                 "dia TEXT PRIMARY KEY)")
    conn.commit()
    return {r[0] for r in conn.execute(
        "SELECT dia FROM esk_dias_procesados").fetchall()}


def _marcar_dia(conn: sqlite3.Connection, dia: str) -> None:
    conn.execute("INSERT OR REPLACE INTO esk_dias_procesados (dia) VALUES (?)",
                 (dia,))
    conn.commit()


def procesar_parcial(zip_local: Path, db_out: Path,
                     dir_calib: Optional[Path] = None) -> int:
    """Procesa los días `.ssc` COMPLETOS que ya viven dentro del zip parcial.

    Idempotente: los días marcados en `esk_dias_procesados` se saltan. A
    medida que la descarga avanza, cada corrida incorpora los días nuevos.
    El directorio central se trae por Range (cacheado): no requiere que el
    zip esté terminado.
    """
    import re
    import tempfile
    entradas = entradas_remotas(zip_local)
    # El archivo real es `ESK-YYYYMMDD-128Hz.ssc` (8 dígitos); las carpetas
    # de mes (`ESK-YYYYMM-...`) y de día tienen 6 u otra cuenta y se caen solas.
    pat = re.compile(r"ESK-(\d{8})-128Hz\.ssc$")
    sscs = [e for e in entradas
            if pat.search(e["nombre"]) and not e["nombre"].endswith("/")]
    tam_local = zip_local.stat().st_size
    print(f"{len(sscs)} días .ssc en el zip · descargados {tam_local/1e9:.2f} GB")
    conn = sqlite3.connect(db_out)
    conn.execute(DDL)
    conn.commit()
    hechos = dias_en_db(conn)
    cdir = Path(dir_calib) if dir_calib else zip_local.parent
    calibs: Dict[int, np.ndarray] = {}
    for sensor, nombre in ((0, DAT_X), (1, DAT_Y)):
        p = cdir / nombre
        if p.exists():
            calibs[sensor] = calibracion_coil(p)
    if not calibs:
        print("SIN calibración (espectros en mV/√Hz; frecuencias intactas)")
    total = 0
    with tempfile.TemporaryDirectory(prefix="esk_ssc_") as td:
        for e in sscs:
            d8 = pat.search(e["nombre"]).group(1)
            iso = f"{d8[:4]}-{d8[4:6]}-{d8[6:]}"
            if iso in hechos:
                continue
            tmp = Path(td) / Path(e["nombre"]).name
            if not extraer_si_completo(zip_local, e, tmp):
                print(f"  {iso}: aún no está completo en el parcial --- se para aquí")
                break
            print(f"  {iso}: extrayendo y procesando…", flush=True)
            for ts, sensor, muestras in leer_ssc_dia(tmp):
                specs, sats = espectros_de_hora(muestras, calibs.get(sensor))
                filas = filas_de_espectros(ts, sensor, specs, sats)
                if filas:
                    total += persistir(conn, filas)
            conn.commit()
            _marcar_dia(conn, iso)
            hechos.add(iso)
    conn.close()
    print(f"{total} intervalos NUEVOS persistidos")
    return total


def procesar(dir_dias: Path, db_out: Path,
              dir_calib: Optional[Path] = None) -> int:
    """Procesa los `ESK-*-128Hz.ssc` de un directorio (días extraídos).

    `dir_calib` busca ahí las dos tablas de bobina; si no están, se procesa
    SIN calibrar (espectros en mV/√Hz --- las frecuencias no cambian; se
    declara en el log).
    """
    sscs = sorted(Path(dir_dias).glob("**/*-128Hz.ssc"))
    if not sscs:
        print(f"sin .ssc en {dir_dias}")
        return 0
    cdir = Path(dir_calib) if dir_calib else Path(dir_dias)
    calibs: Dict[int, np.ndarray] = {}
    for sensor, nombre in ((0, DAT_X), (1, DAT_Y)):
        p = cdir / nombre
        if p.exists():
            calibs[sensor] = calibracion_coil(p)
        else:
            print(f"SIN CALIBRACIÓN para sensor {sensor} ({nombre} no está en {cdir})")
    conn = sqlite3.connect(db_out)
    total = 0
    for p in sscs:
        print(f"procesando {p.name} …", flush=True)
        for ts, sensor, muestras in leer_ssc_dia(p):
            specs, sats = espectros_de_hora(muestras, calibs.get(sensor))
            filas = filas_de_espectros(ts, sensor, specs, sats)
            if filas:
                total += persistir(conn, filas)
        conn.commit()
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
            print("uso: --procesar <dir_dias_extraidos> <db_out> [dir_calib]")
            return 1
        n = procesar(Path(sys.argv[2]), Path(sys.argv[3]),
                     Path(sys.argv[4]) if len(sys.argv) > 4 else None)
        print(f"{n} intervalos persistidos en {TABLA}")
        return 0
    if sys.argv[1] == "--procesar-parcial":
        if len(sys.argv) < 4:
            print("uso: --procesar-parcial <2025.zip parcial> <db_out> [dir_calib]")
            return 1
        n = procesar_parcial(Path(sys.argv[2]), Path(sys.argv[3]),
                             Path(sys.argv[4]) if len(sys.argv) > 4 else None)
        print(f"total nuevos: {n}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
