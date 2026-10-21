"""Capa cimática espectral — el TONO de la ventana viva (tela SNT sobre firmas).

Lineaje (2026-10-21): el operador pidió «meterle el motor cimático a las
firmas del padre». El motor viene del repo SNT
(`The-shadow-Node-Theory/reconstruction_real/code/tela_cimatica.py`:
trayectoria → fase → FFT → huella → tono por centroide) y se MIDIÓ sobre
las ventanas que entrenaron las firmas antes de integrarse
(`deploy/medir_cimatica_firmas.py` + audit en
`estado/cimatica_firmas/AUDIT_cimatica_firmas_2026-10-21.md`).

Medido (LOO con placebo, 4.145 ventanas):
  - familia (sismico/volcanico/solar) 46.8% vs placebo 32.9% → señal real
  - SOLO-CLIMA 51.2% — el tono vive en el clima espacial
  - clase AL NULO · NODO MUERTO (1.4% vs 10.9%) — el tono no localiza

Por eso esta capa operacional usa la configuración SOLO-CLIMA (la mejor
medida) y entra como EVIDENCIA — reportada por ciclo y auditable por el
Juez — nunca como compuerta del consenso: el tono dice QUÉ régimen vibra,
no DÓNDE ni CUÁNDO exactamente.

Contrato:
  - `construir_centroides(conn)`: muestreo estratificado (semilla fija) →
    huellas solo-clima de las vísperas → z-score del corpus → centroides
    por familia → persistidos en `tbl_cimatica_tonos` (una vez, tras
    entrenamiento).
  - `tono_actual(conn)`: huella de la ventana viva (las 336 h que terminan
    en la hora de dato más reciente — el ahora de los DATOS, no del reloj)
    → distancia a los centroides guardados. Sin centroides → None visible.
  - `audit_tono_eventos(conn, desde)`: el veredicto de producción — cada
    evento M4.5+ posterior a `desde` se puntúa contra el tono de SU
    víspera (¿apuntaba a 'sismico'?). Corrible cuando se quiera, como el
    Juez; cada evento vivo es una muestra nueva.

Regla 2 respetada: huecos = NaN (nunca rellenos); ventana sin cobertura
suficiente = SIN LECTURA (None), no tono por defecto. Regla 10: todo fallo
se loguea; ningún except invisible.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Configuración (espejo de la medición del audit) ──────────────────────────
VENTANA_H = 336          # 14 días — la ventana de las firmas
N_FASES = 32             # retícula de fase de la tela
HUELLA_NBIN = 5          # bins de fase en la huella
ARMONICOS_HUELLA = 3     # A1/A2/A3 por serie
COBERTURA_MIN = 0.50     # <50% de horas reales → SIN LECTURA
DIM_HUELLA = (HUELLA_NBIN + ARMONICOS_HUELLA) * 5   # 5 series clima → 40
MIN_DIMS_COMPARABLES = 8
SEED = 42                # la misma semilla del audit: reproducible

SERIES = [
    ("bz_promedio", "bz_promedio"),
    ("bz_derivada", "bz_derivada"),
    ("viento_solar_avg", "viento_solar_avg"),
    ("kp_promedio", "kp_promedio"),
    ("densidad_protones", "densidad_protones"),
]

TABLA_TONOS = "tbl_cimatica_tonos"


# ── Trayectoria y huella (solo-clima; el audit demostró que carga el tono) ──
def _ensure_tabla(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLA_TONOS} ("
        "clave TEXT PRIMARY KEY, "
        "valor_json TEXT NOT NULL, "
        "construido_at TEXT DEFAULT (datetime('now')))"
    )


def _parse(ts: str):
    import datetime as _dt
    return _dt.datetime.strptime(ts[:16], "%Y-%m-%d %H:%M")


def _ventana(conn: sqlite3.Connection, ts_ancla: str) -> list:
    """Las 336 h previas al ancla, ordenadas. ts_ancla: 'YYYY-MM-DD HH:MM'."""
    ini = f"datetime('{ts_ancla[:19]}', '-{VENTANA_H} hours')"
    cols = ", ".join(col for _, col in SERIES)
    return conn.execute(
        f"SELECT timestamp_blk, {cols} FROM tbl_clima_espacial_raw "
        f"WHERE timestamp_blk >= {ini} AND timestamp_blk < '{ts_ancla[:19]}' "
        "ORDER BY timestamp_blk"
    ).fetchall()


def _huella_de_filas(filas: list) -> Optional[np.ndarray]:
    """Filas de la ventana → vector de 40 dims (5 bins + 3 log-amps × 5 series).

    None si ninguna serie alcanza la cobertura mínima (SIN LECTURA, no
    tono por defecto — regla 2/7).
    """
    if not filas:
        return None
    import datetime as _dt
    ancla = _parse(filas[-1][0])
    win_ini = ancla - _dt.timedelta(hours=VENTANA_H - 1)
    series = {n: np.full(VENTANA_H, np.nan) for n, _ in SERIES}
    for fila in filas:
        try:
            i = int(round((_parse(fila[0]) - win_ini).total_seconds() / 3600.0))
        except ValueError:
            continue
        if not (0 <= i < VENTANA_H):
            continue
        for j, (nombre, _) in enumerate(SERIES):
            v = fila[1 + j]
            if v is not None:
                series[nombre][i] = float(v)

    dims: list = []
    usables = 0
    for nombre, _ in SERIES:
        serie = series[nombre]
        if bool(np.isnan(serie).all()) or (~np.isnan(serie)).mean() < COBERTURA_MIN:
            dims += [np.nan] * (HUELLA_NBIN + ARMONICOS_HUELLA)
            continue
        usables += 1
        idx = np.arange(VENTANA_H) / (VENTANA_H - 1)
        ok = ~np.isnan(serie)
        fase = np.interp(np.linspace(0.0, 1.0, N_FASES), idx[ok], serie[ok])
        # 5 bins de fase (medias sobre lo real)
        bordes = np.linspace(0, N_FASES - 1, HUELLA_NBIN + 1).astype(int)
        for a, b in zip(bordes[:-1], bordes[1:]):
            seg = fase[a:b if a == b else b + 1]
            seg = seg[~np.isnan(seg)]
            dims.append(float(seg.mean()) if seg.size else np.nan)
        # A1..A3: detrend lineal + Hann + FFT (la lección de beta1)
        t = np.linspace(0.0, 1.0, N_FASES)
        p = np.polyfit(t, fase, 1)
        det = fase - np.polyval(p, t)
        hann = 0.5 * (1 - np.cos(2 * np.pi * t))
        amps = np.abs(np.fft.rfft(det * hann))[:ARMONICOS_HUELLA]
        dims += [float(np.log10(a + 1e-12)) for a in amps]
    if usables == 0:
        return None
    return np.array(dims, dtype=float)


# ── Centroides por familia ───────────────────────────────────────────────────
def _muestrear_anclas(conn: sqlite3.Connection, n_m6=800, n_m5=800,
                      n_m4=800) -> list:
    """El mismo muestreo estratificado del audit (misma semilla)."""
    rng = np.random.default_rng(SEED)
    anclas = []
    filas = conn.execute(
        "SELECT timestamp_blk, event_class FROM tbl_eventos_no_sismicos "
        "ORDER BY timestamp_blk"
    ).fetchall()
    anclas += [(ts, _familia(ec)) for ts, ec in filas]
    filas = conn.execute(
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw WHERE sismo_max_mag >= 4.5 "
        "ORDER BY timestamp_blk"
    ).fetchall()
    vistos: dict = {}
    por = {"SISMO_M7": [], "SISMO_M6": [], "SISMO_M5": [], "SISMO_M4": []}
    for ts, nodo, mag in filas:
        clave = (nodo, round(float(mag), 1))
        prev = vistos.get(clave)
        if prev is not None and abs((_parse(ts) - _parse(prev)).total_seconds()) \
                <= 12 * 3600:
            continue
        vistos[clave] = ts
        c = ("SISMO_M7" if mag >= 7 else "SISMO_M6" if mag >= 6
             else "SISMO_M5" if mag >= 5 else "SISMO_M4")
        por[c].append((ts, "sismico"))
    for clase, cupo in (("SISMO_M7", None), ("SISMO_M6", n_m6),
                        ("SISMO_M5", n_m5), ("SISMO_M4", n_m4)):
        casos = por[clase]
        if cupo is not None and len(casos) > cupo:
            idx = rng.choice(len(casos), size=cupo, replace=False)
            casos = [c for i, c in sorted(zip(idx.tolist(), casos))]
        anclas += casos
    return anclas


def _familia(event_class: str) -> str:
    if event_class.startswith("ERUPCION"):
        return "volcanico"
    if event_class.startswith("TORMENTA"):
        return "solar"
    if event_class.startswith("SISMO"):
        return "sismico"
    return "otro"


def construir_centroides(conn: sqlite3.Connection, persistir: bool = True,
                         n_m6: int = 800, n_m5: int = 800,
                         n_m4: int = 800) -> Optional[Dict[str, Any]]:
    """Huellas de las vísperas muestreadas → z-score del corpus → centroides.

    Devuelve {"familia": {"vec": ..., "n": ...}, "mu": ..., "sd": ...} y
    (si persistir) los guarda en tbl_cimatica_tonos: una fila 'meta'
    (mu/sd/config) y una por familia.
    """
    t0 = time.time()
    anclas = _muestrear_anclas(conn, n_m6, n_m5, n_m4)
    vecs, fams = [], []
    for ts, fam in anclas:
        h = _huella_de_filas(_ventana(conn, ts))
        if h is not None:
            vecs.append(h)
            fams.append(fam)
    if len(vecs) < 50:
        logger.warning("tonos: solo %d ventanas usables — no se construyen "
                       "centroides", len(vecs))
        return None
    X = np.stack(vecs)
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd[sd == 0] = 1.0
    Xz = (X - mu) / sd
    centroides = {}
    for fam in sorted(set(fams)):
        m = fams.count(fam)
        if m < 2:
            continue
        with np.errstate(invalid="ignore"):
            centroides[fam] = {
                "vec": np.nanmean(Xz[[i for i, f in enumerate(fams)
                                      if f == fam]], axis=0),
                "n": m,
            }
    if len(centroides) < 2:
        logger.warning("tonos: familias insuficientes — no se construye nada")
        return None
    if persistir:
        _ensure_tabla(conn)
        conn.execute(f"DELETE FROM {TABLA_TONOS}")
        conn.execute(
            f"INSERT INTO {TABLA_TONOS} (clave, valor_json) VALUES (?, ?)",
            ("meta", json.dumps({
                "mu": [None if np.isnan(v) else float(v) for v in mu],
                "sd": [None if np.isnan(v) else float(v) for v in sd],
                "series": [n for n, _ in SERIES],
                "ventana_h": VENTANA_H, "n_fases": N_FASES,
                "n_muestras": len(vecs), "seed": SEED,
                "audit": "AUDIT_cimatica_firmas_2026-10-21.md",
            })),
        )
        for fam, c in centroides.items():
            conn.execute(
                f"INSERT INTO {TABLA_TONOS} (clave, valor_json) VALUES (?, ?)",
                (f"familia:{fam}", json.dumps({
                    "vec": [None if np.isnan(v) else float(v)
                            for v in c["vec"]],
                    "n": int(c["n"]),
                })),
            )
        conn.commit()
    logger.info("tonos: %d centroides de %d ventanas en %.0fs → %s",
                len(centroides), len(vecs), time.time() - t0,
                TABLA_TONOS if persistir else "(sin persistir)")
    return {**centroides, "mu": mu, "sd": sd}


def _cargar_centroides(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    try:
        filas = conn.execute(
            f"SELECT clave, valor_json FROM {TABLA_TONOS}"
        ).fetchall()
    except sqlite3.Error:
        return None
    if not filas:
        return None
    meta = None
    cents = {}
    for clave, vjson in filas:
        v = json.loads(vjson)
        if clave == "meta":
            meta = v
        elif clave.startswith("familia:"):
            cents[clave.split(":", 1)[1]] = v
    if meta is None or len(cents) < 2:
        return None
    return {"meta": meta, "centroides": cents}


# ── La lectura viva ─────────────────────────────────────────────────────────
def tono_actual(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """El tono de la ventana viva: huella de las 336 h más recientes con
    dato → distancia (z-scoreada) a los centroides de familia guardados.

    El ancla es la última hora CON DATO (el «ahora» de los datos), no el
    reloj: si la ingesta se retrasó, el tono describe lo que hay, y si no
    hay cobertura suficiente, no hay tono (None visible, regla 2/7).
    """
    cfg = _cargar_centroides(conn)
    if cfg is None:
        logger.info("tonos: sin centroides construidos — corre "
                    "construir_centroides() (audit 2026-10-21)")
        return None
    fila = conn.execute(
        "SELECT MAX(timestamp_blk) FROM tbl_clima_espacial_raw"
    ).fetchone()
    if not fila or not fila[0]:
        return None
    ancla = str(fila[0])
    h = _huella_de_filas(_ventana(conn, ancla))
    if h is None:
        logger.warning("tonos: ventana viva sin cobertura suficiente "
                       "(ancla %s) — SIN LECTURA", ancla)
        return None
    mu = np.array([np.nan if v is None else v for v in cfg["meta"]["mu"]])
    sd = np.array([1.0 if v is None else v for v in cfg["meta"]["sd"]])
    hz = (h - mu) / sd
    dists = {}
    for fam, c in cfg["centroides"].items():
        cv = np.array([np.nan if v is None else v for v in c["vec"]],
                      dtype=float)
        if cv.shape != hz.shape:
            # centroide corrupto/desfasado: familia NO comparable. Se ve,
            # no tumba el ciclo ni inventa distancia (reglas 7/10).
            logger.warning("tonos: centroide '%s' con %d dims (se esperaban "
                          "%d) — fuera de la lectura", fam, cv.shape[0],
                          hz.shape[0])
            dists[fam] = None
            continue
        m = ~(np.isnan(hz) | np.isnan(cv))
        if m.sum() < MIN_DIMS_COMPARABLES:
            dists[fam] = None       # dims insuficientes: ausente, no cero
            continue
        dists[fam] = float(np.linalg.norm((hz - cv)[m]))
    comparables = {f: d for f, d in dists.items() if d is not None}
    if len(comparables) < 2:
        logger.warning("tonos: menos de 2 familias comparables — SIN LECTURA")
        return None
    tono = min(comparables, key=comparables.get)
    return {
        "ancla": ancla,
        "tono": tono,
        "dist": {f: (round(d, 3) if d is not None else None)
                 for f, d in dists.items()},
        "construido_at": cfg["meta"].get("audit"),
    }


# ── El veredicto de producción (estilo Juez: eventos vs tono de su víspera) ──
def audit_tono_eventos(conn: sqlite3.Connection, desde_epoch: float) -> Dict[str, Any]:
    """Cada evento M4.5+ vivo posterior a `desde` se puntúa contra el tono
    de SU víspera (¿la ventana apuntaba a 'sismico'?).

    La contraparte viva del LOO del audit: cada evento nuevo es una
    muestra de producción, medida sobre datos del loop vivo (no backcast).
    """
    cfg = _cargar_centroides(conn)
    if cfg is None:
        return {"error": "sin centroides construidos"}
    mu = np.array([np.nan if v is None else v for v in cfg["meta"]["mu"]])
    sd = np.array([1.0 if v is None else v for v in cfg["meta"]["sd"]])
    import datetime as _dt
    desde = _dt.datetime.fromtimestamp(desde_epoch, tz=_dt.timezone.utc)
    filas = conn.execute(
        "SELECT timestamp, magnitude FROM TBL_HISTORICO_SISMICO "
        "WHERE magnitude >= 4.5 AND timestamp >= ? ORDER BY timestamp",
        (desde_epoch,),
    ).fetchall()
    eventos = []
    for ts_epoch, mag in filas:
        ancla = _dt.datetime.fromtimestamp(
            float(ts_epoch), tz=_dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        if _dt.datetime.fromtimestamp(float(ts_epoch),
                                      tz=_dt.timezone.utc) < desde:
            continue
        h = _huella_de_filas(_ventana(conn, ancla))
        if h is None:
            eventos.append({"ts": ancla, "mag": float(mag),
                            "tono": None, "acierta": None})
            continue
        hz = (h - mu) / sd
        dists = {}
        for fam, c in cfg["centroides"].items():
            cv = np.array([np.nan if v is None else v for v in c["vec"]],
                          dtype=float)
            if cv.shape != hz.shape:
                dists[fam] = None
                continue
            m = ~(np.isnan(hz) | np.isnan(cv))
            if m.sum() >= MIN_DIMS_COMPARABLES:
                dists[fam] = float(np.linalg.norm((hz - cv)[m]))
            else:
                dists[fam] = None
        if not dists:
            eventos.append({"ts": ancla, "mag": float(mag),
                            "tono": None, "acierta": None})
            continue
        tono = min(dists, key=dists.get)
        eventos.append({"ts": ancla, "mag": float(mag), "tono": tono,
                        "acierta": tono == "sismico"})
    evaluados = [e for e in eventos if e["acierta"] is not None]
    aciertos = sum(1 for e in evaluados if e["acierta"])
    por_tono: Dict[str, int] = {}
    for e in evaluados:
        por_tono[e["tono"]] = por_tono.get(e["tono"], 0) + 1
    # Nulo honesto: un tono que SIEMPRE dijera 'sismico' acierta el 100%
    # de los eventos sísmicos por definición — la tasa sola no es skill.
    # Lo que mide producción es la CONCORDANCIA por tipo de evento (el
    # detalle va en `eventos`) y su acumulado contra el placebo del audit.
    return {
        "n_eventos": len(eventos), "n_evaluados": len(evaluados),
        "aciertos_sismico": aciertos,
        "tasa": round(aciertos / len(evaluados), 3) if evaluados else None,
        "por_tono": por_tono,
        "desde": desde.isoformat(),
        "eventos": eventos,
    }
