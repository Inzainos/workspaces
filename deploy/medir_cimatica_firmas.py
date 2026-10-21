"""Medir el motor cimático de la tela SNT sobre las ventanas de las firmas.

Pedido del operador (2026-10-21): «meterle el motor cimático a las firmas
del padre». El motor vive en el repo SNT
(`The-shadow-Node-Theory/reconstruction_real/code/tela_cimatica.py`) y su
lectura es: la TRAYECTORIA de una ventana tiene un TONO espectral que
identifica el régimen — no el instrumento — con exactitud LOO medida
(66.2% por tono φ en el corpus SNT v2, 72% en los extremos).

Las firmas de Sentinel Omega son VECTORES agregados de la ventana de 14
días (`extraer_features_ventana` colapsa 336 horas a mean/min/max/std).
Este script reconstruye esas ventanas como SERIE y corre la misma prueba
LOO de la tela sobre los eventos que entrenaron las firmas:

  por CLASE    (SISMO_M4/M5/M6/M7, ERUPCION_VEI3/4/5, TORMENTA_Kp6/7)
  por FAMILIA  (sísmico | volcánico | solar — el «tono» de Omega)
  por NODO     (vs el nulo: la tasa del nodo más común)

La misma disciplina que la tela: medir ANTES de integrar. Si el tono no
identifica nada, esto se documenta en negativo y el padre no se toca.

Trayectorias (v0 — las series horarias que ya consulta el extractor):
  bz_promedio, bz_derivada, viento_solar_avg, kp_promedio,
  densidad_protones  (tbl_clima_espacial_raw, 1994→)
  sismo_count         (tbl_historico_sismico_raw, EL NODO del evento)

Limitaciones honestas (v0):
  - Schumann NO entra: `tbl_enjambre_telemetria` tiene 1.026 filas vivas
    (jul-2026→), sin backcast. El tono Schumann se acumulará en vivo.
  - Las celdas consecutivas del mismo sismo se deduplican (nodo+mag a
    ±12 h); un sismo grande persiste 2-3 celdas.
  - Ventanas con <50% de cobertura espacial en clima quedan SIN DATO
    (regla 2: ausente, no relleno) y se cuentan visible.
  - Interpolación lineal sobre los huecos internos de la fase — suaviza;
    documentado, como la rejilla de peras de la tela v1.

Uso (desde /home/deamon/workspaces, venv del workspace):
  .venv/bin/python deploy/medir_cimatica_firmas.py [--n-muestra N] [--sin-figuras]
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel_omega.infrastructure.database.ruta_db import (  # noqa: E402
    abrir_readonly,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("cimatica_firmas")

# ── Parámetros de la tela ────────────────────────────────────────────────────
VENTANA_H = 336            # 14 días — la misma de las firmas (ventana_horas)
N_FASES = 32               # retícula de fase de la tela
COBERTURA_MIN = 0.50       # <50% de horas reales en la ventana → SIN DATO
HUELLA_NBIN = 5            # valor de fase por BIN (medias; conteo por SUMA)
ARMONICOS_HUELLA = 3       # A1/A2/A3 en la huella, como la tela
SEED = 42

# Serie → tabla/columna; las mismas lecturas que extraer_features_ventana.
SERIES_CLIMA = [
    ("bz_promedio", "bz_promedio", "mean"),
    ("bz_derivada", "bz_derivada", "mean"),
    ("viento_solar_avg", "viento_solar_avg", "mean"),
    ("kp_promedio", "kp_promedio", "mean"),
    ("densidad_protones", "densidad_protones", "mean"),
]
# La serie del propio nodo: ritmo de precursores. SUMA por bin (es conteo).
SERIE_SISMO = ("sismo_count", "sismo_count", "sum")

FAMILIA_DE = {
    "SISMO": "sismico", "ERUPCION": "volcanico", "TORMENTA": "solar",
}


def familia_de(clase: str) -> str:
    for pref, fam in FAMILIA_DE.items():
        if clase.startswith(pref):
            return fam
    return "otro"


def clase_de_mag(mag: float) -> str:
    """El mismo umbral que _event_class del entrenamiento (exigibles M4.5+)."""
    if mag >= 7.0:
        return "SISMO_M7"
    if mag >= 6.0:
        return "SISMO_M6"
    if mag >= 5.0:
        return "SISMO_M5"
    return "SISMO_M4"          # 4.5–4.99 (el piso exigible)


# ── Muestreo estratificado de anclas ─────────────────────────────────────────
def muestrear_anclas(conn, n_m6=800, n_m5=800, n_m4=800) -> list:
    """Celdas M4.5+ deduplicadas por sismo + eventos no sísmicos completos."""
    rng = np.random.default_rng(SEED)
    anclas = []

    filas = conn.execute(
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw WHERE sismo_max_mag >= 4.5 "
        "ORDER BY timestamp_blk"
    ).fetchall()
    # Dedup: mismo nodo y misma magnitud (0.1) a ≤12 h = el mismo sismo.
    vistos: dict = {}
    por_clase: dict = {"SISMO_M7": [], "SISMO_M6": [], "SISMO_M5": [],
                       "SISMO_M4": []}
    for ts, nodo, mag in filas:
        clave = (nodo, round(float(mag), 1))
        prev = vistos.get(clave)
        if prev is not None and _horas_entre(prev, ts) <= 12:
            continue
        vistos[clave] = ts
        por_clase[clase_de_mag(float(mag))].append((ts, nodo, float(mag)))

    for clase, cupo in (("SISMO_M7", None), ("SISMO_M6", n_m6),
                        ("SISMO_M5", n_m5), ("SISMO_M4", n_m4)):
        casos = por_clase[clase]
        if cupo is not None and len(casos) > cupo:
            idx = rng.choice(len(casos), size=cupo, replace=False)
            casos = [casas_ for i, casas_ in sorted(zip(idx.tolist(), casos))]
        log.info("  anclas %s: %d (tras dedup de celdas repetidas)",
                 clase, len(casos))
        anclas += [{"ts": ts, "nodo": nodo, "clase": clase,
                    "familia": "sismico"} for ts, nodo, _ in casos]

    try:
        for ts, nodo, clase in conn.execute(
            "SELECT timestamp_blk, id_nodo, event_class "
            "FROM tbl_eventos_no_sismicos ORDER BY timestamp_blk"
        ).fetchall():
            anclas.append({"ts": ts, "nodo": nodo, "clase": clase,
                           "familia": familia_de(clase)})
    except sqlite3.OperationalError:
        log.warning("sin tabla de eventos no sísmicos")

    log.info("anclas totales: %d", len(anclas))
    return anclas


def _horas_entre(ts_a: str, ts_b: str) -> float:
    import datetime as _dt
    try:
        a = _dt.datetime.strptime(ts_a[:16], "%Y-%m-%d %H:%M")
        b = _dt.datetime.strptime(ts_b[:16], "%Y-%m-%d %H:%M")
        return abs((b - a).total_seconds()) / 3600.0
    except ValueError:
        return 1e9


# ── Trayectorias ─────────────────────────────────────────────────────────────
def _ventana_sql(ts: str) -> tuple:
    ini = f"datetime('{ts[:19]}', '-{VENTANA_H} hours')"
    return ini, f"'{ts[:19]}'"


def _win_inicio(ts: str):
    """(datetime del inicio de ventana, datetime del ancla) para offsets."""
    import datetime as _dt
    ancla = _dt.datetime.strptime(ts[:16], "%Y-%m-%d %H:%M")
    return ancla - _dt.timedelta(hours=VENTANA_H)


def _offset_h(ts_fila, win_ini) -> int:
    return int(round((ts_fila - win_ini).total_seconds() / 3600.0))


def trayectoria_clima(conn, ts: str) -> dict:
    """Las 336 horas previas como dict serie→np.array(336) (NaN si hueco)."""
    cols = ", ".join(c for _, c, _ in SERIES_CLIMA)
    ini, fin = _ventana_sql(ts)
    rows = conn.execute(
        f"SELECT timestamp_blk, {cols} FROM tbl_clima_espacial_raw "
        f"WHERE timestamp_blk >= {ini} AND timestamp_blk < {fin} "
        "ORDER BY timestamp_blk"
    ).fetchall()
    out = {nombre: np.full(VENTANA_H, np.nan) for nombre, _, _ in SERIES_CLIMA}
    if not rows:
        return out
    import datetime as _dt
    win_ini = _win_inicio(ts)
    for fila in rows:
        try:
            i = _offset_h(_dt.datetime.strptime(fila[0][:16], "%Y-%m-%d %H:%M"),
                          win_ini)
        except ValueError:
            continue
        if 0 <= i < VENTANA_H:
            for j, (nombre, _, _) in enumerate(SERIES_CLIMA):
                v = fila[1 + j]
                if v is not None:
                    out[nombre][i] = float(v)
    return out


def trayectoria_sismo(conn, ts: str, id_nodo) -> np.ndarray:
    """Ritmo de temblores del nodo en la ventana, como malla densa.

    `tbl_historico_sismico_raw` es evento-sparse: SOLO tiene filas en horas
    con temblores (verificado: 0 filas con count=0). La malla real es densa
    en ceros — hora sin fila = cero temblores, que es el dato verdadero,
    no un hueco (regla 2: es la semántica de la fuente, no relleno). Por
    eso aquí se inicializa en CEROS y el offset es absoluto desde el
    inicio de la ventana (la primera fila puede llegar a cualquier hora).
    """
    ini, fin = _ventana_sql(ts)
    col = SERIE_SISMO[1]
    rows = conn.execute(
        f"SELECT timestamp_blk, {col} FROM tbl_historico_sismico_raw "
        f"WHERE id_nodo = ? AND timestamp_blk >= {ini} AND timestamp_blk < {fin} "
        "ORDER BY timestamp_blk", (id_nodo,)
    ).fetchall()
    out = np.zeros(VENTANA_H)            # sin filas = cero temblores
    if not rows:
        return out
    import datetime as _dt
    win_ini = _win_inicio(ts)
    for fila in rows:
        try:
            i = _offset_h(_dt.datetime.strptime(fila[0][:16], "%Y-%m-%d %H:%M"),
                          win_ini)
        except ValueError:
            continue
        if 0 <= i < VENTANA_H and fila[1] is not None:
            out[i] = float(fila[1])
    return out


def a_fase(serie: np.ndarray) -> np.ndarray:
    """Serie 336 h → retícula de N_FASES puntos, interpolando solo lo real."""
    idx = np.arange(VENTANA_H) / (VENTANA_H - 1)
    ok = ~np.isnan(serie)
    if not ok.any():
        return np.full(N_FASES, np.nan)
    return np.interp(np.linspace(0.0, 1.0, N_FASES), idx[ok], serie[ok])


def espectro(fase: np.ndarray) -> np.ndarray:
    """Amplitudes FFT A1..A16 de la fase, detrend lineal + ventana Hann.

    La lección de beta1 aplicada: sin ventana la fuga espectral tiñe los
    armónicos; detrend+Hann antes de transformar.
    """
    ok = ~np.isnan(fase)
    if ok.sum() < 8:
        return np.full(16, np.nan)
    x = np.asarray(fase, dtype=float)
    t = np.linspace(0.0, 1.0, len(x))
    # detrend solo con los puntos reales (coef sobre máscara)
    p = np.polyfit(t[ok], x[ok], 1)
    det = x - np.polyval(p, t)
    det[~ok] = 0.0
    hann = 0.5 * (1 - np.cos(2 * np.pi * t))
    coef = np.fft.rfft((det * hann)[1:-1])
    return np.abs(coef)[:16]


def huella_de(tragos_clima: dict, trazo_sismo: np.ndarray) -> tuple:
    """Vector de rasgos: por serie, 5 bins de fase + log A1..A3.

    Bins de fase por MEDIA para series continuas; por SUMA para el conteo
    sísmico (un conteo no se promedia — se suma). Devuelve
    (vector, n_series_usables).
    """
    dims = []
    series = {**tragos_clima, SERIE_SISMO[0]: trazo_sismo}
    n_usables = 0
    for nombre, serie in series.items():
        fase = a_fase(np.asarray(serie, dtype=float))
        if bool(np.isnan(fase).all()):
            dims += [np.nan] * (HUELLA_NBIN + ARMONICOS_HUELLA)
            continue
        cobertura = float((~np.isnan(serie)).mean())
        if cobertura < COBERTURA_MIN:
            dims += [np.nan] * (HUELLA_NBIN + ARMONICOS_HUELLA)
            continue
        n_usables += 1
        # 5 bins de fase (medias sobre lo real)
        bordes = np.linspace(0, N_FASES - 1, HUELLA_NBIN + 1).astype(int)
        for a, b in zip(bordes[:-1], bordes[1:]):
            seg = fase[a:b if a == b else b + 1]
            seg = seg[~np.isnan(seg)]
            dims.append(float(seg.mean()) if seg.size else np.nan)
        if nombre == SERIE_SISMO[0]:
            # el conteo por bin: suma del segmento de la serie ORIGINAL
            segs = np.array_split(serie, HUELLA_NBIN)
            dims[-HUELLA_NBIN:] = [
                float(np.nansum(s)) if (~np.isnan(s)).any() else np.nan
                for s in segs
            ]
        amps = espectro(fase)[:ARMONICOS_HUELLA]
        dims += [float(np.log10(a + 1e-12)) for a in amps]
    return np.array(dims, dtype=float), n_usables


# ── LOO por centroide (la misma prueba de la tela, con máscara NaN) ─────────
def loo_centroide(X: np.ndarray, grupos: list, min_grupo: int = 2) -> dict:
    """Leave-one-out por centroide más cercano; distancia enmascarada por
    dims comparables (NaN fuera), como similitud_vec de las firmas."""
    etiquetas = list(grupos)
    evaluables = {g for g in etiquetas
                  if sum(1 for e in etiquetas if e == g) >= min_grupo}
    preds, reales = [], []
    n = X.shape[0]
    for i in range(n):
        if etiquetas[i] not in evaluables:
            continue
        mejor_g, mejor_d = None, np.inf
        for g in sorted(evaluables):
            idx_g = [j for j in range(n)
                     if j != i and etiquetas[j] == g]
            if not idx_g:
                continue
            C = X[idx_g]
            # Centroide por dim IGNORANDO NaN (nanmean): una dim es NaN
            # solo si NADIE del grupo la tiene. El mean plano envenenaba
            # la dim completa con un solo caso sin dato — y con 232 ventanas
            # de 1994 sin clima, mataba el tono de clima para todos.
            with np.errstate(invalid="ignore"):
                cent = np.nanmean(C, axis=0)
            xi = X[i]
            m = ~(np.isnan(xi) | np.isnan(cent))
            if m.sum() < 4:
                continue
            d = float(np.linalg.norm((xi - cent)[m]))
            if d < mejor_d:
                mejor_d, mejor_g = d, g
        if mejor_g is not None:
            preds.append(mejor_g)
            reales.append(etiquetas[i])
    reales = np.array(reales)
    preds = np.array(preds)
    acc = float((preds == reales).mean()) if reales.size else float("nan")
    # nulos honestos
    base = Counter(reales.tolist())
    nulo_mayoria = base.most_common(1)[0][1] / len(reales) if reales.size else float("nan")
    nulo_uniforme = 1.0 / len(evaluables) if evaluables else float("nan")
    por_grupo = {g: [int(((reales == g) & (preds == g)).sum()),
                     int((reales == g).sum())]
                 for g in sorted(evaluables)}
    return {"acc": acc, "n": len(reales), "nulo_mayoria": nulo_mayoria,
            "nulo_uniforme": nulo_uniforme, "por_grupo": por_grupo}


# ── Figuras ─────────────────────────────────────────────────────────────────
def figuras(casos, ruta_out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.warning("sin matplotlib — figuras omitidas")
        return
    # Tonos: espectro mediano por clase (kp y sismo_count)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, nombre in zip(axes, ["kp_promedio", "sismo_count"]):
        for clase in sorted({c["clase"] for c in casos}):
            fases = [c["fases"][nombre] for c in casos
                     if c["clase"] == clase and nombre in c["fases"]
                     and c["fases"][nombre] is not None]
            if not fases:
                continue
            espec = np.stack(fases)
            med = np.nanmedian(espec, axis=0)
            ax.plot(np.arange(1, len(med) + 1), med, "o-", lw=1.2, ms=3,
                    label=f"{clase} (n={len(fases)})")
        ax.set_yscale("log")
        ax.set_xlabel("armónico de la fase τ (1…16)")
        ax.set_ylabel("amplitud FFT mediana")
        ax.set_title(f"Tono: {nombre}")
        ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ruta_out / "fig_cimatica_firmas_tonos.png", dpi=200)
    plt.close(fig)
    log.info("figura tonos → %s", ruta_out / "fig_cimatica_firmas_tonos.png")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-m6", type=int, default=800)
    ap.add_argument("--n-m5", type=int, default=800)
    ap.add_argument("--n-m4", type=int, default=800)
    ap.add_argument("--sin-figuras", action="store_true")
    ap.add_argument("--ablation", action="store_true",
                    help="familia LOO en 3 variantes: completa, solo clima, "
                         "solo enjambre — qué lee el motor")
    a = ap.parse_args()

    t0 = time.time()
    conn = abrir_readonly()
    if conn is None:
        log.error("sin DB")
        return 1

    log.info("=== MOTOR CIMÁTICO (tela SNT) SOBRE LAS FIRMAS — MEDICIÓN LOO ===")
    anclas = muestrear_anclas(conn, a.n_m6, a.n_m5, a.n_m4)

    casos = []
    sin_datos = 0
    for i, anc in enumerate(anclas):
        if i and i % 500 == 0:
            log.info("  trayectorias %d/%d (%.0fs, sin_dato=%d)",
                     i, len(anclas), time.time() - t0, sin_datos)
        tr = trayectoria_clima(conn, anc["ts"])
        sis = trayectoria_sismo(conn, anc["ts"], anc["nodo"])
        vec, n_usables = huella_de(tr, sis)
        if n_usables == 0:
            sin_datos += 1
            continue
        # fases por serie para las figuras (espectro completo)
        fases = {}
        for nombre, serie in {**tr, "sismo_count": sis}.items():
            fase = a_fase(np.asarray(serie, dtype=float))
            fases[nombre] = espectro(fase) if (~np.isnan(fase)).sum() >= 8 else None
        casos.append({**anc, "vec": vec, "fases": fases})

    log.info("casos con datos: %d · sin_dato: %d · %.0fs",
             len(casos), sin_datos, time.time() - t0)

    if len(casos) < 50:
        log.error("muy pocos casos (%d) — abortando", len(casos))
        return 1

    X = np.stack([c["vec"] for c in casos])

    resumen = {}
    for nombre, campo in (("CLASE", "clase"), ("FAMILIA (el tono)", "familia"),
                         ("NODO", "nodo")):
        r = loo_centroide(X, [c[campo] for c in casos])
        resumen[nombre] = r
        log.info("LOO por %s: %.1f%% (n=%d) · nulo mayoria %.1f%% · "
                 "nulo uniforme %.1f%%",
                 nombre, 100 * r["acc"], r["n"], 100 * r["nulo_mayoria"],
                 100 * r["nulo_uniforme"])
        det = " | ".join(f"{g} {ok}/{n}"
                         for g, (ok, n) in list(r["por_grupo"].items())[:12])
        log.info("   por grupo: %s", det)

    # Control placebo (estándar del workspace, cf. H-φ en SNT v30): con las
    # etiquetas PERMUTADAS la exactitud debe caer al nulo. Si no cae, la
    # señal era estructura de los datos, no de la relación ventana→clase.
    rng = np.random.default_rng(SEED)
    for campo in ("clase", "familia"):
        et = [c[campo] for c in casos]
        accs = []
        for _ in range(5):
            perm = et.copy()
            rng.shuffle(perm)
            accs.append(loo_centroide(X, perm)["acc"])
        log.info("PLACEBO %s: %.1f%% ± %.1f%% (5 permutaciones) — "
                 "la señal real debe caer aquí",
                 campo, 100 * float(np.mean(accs)),
                 100 * float(np.std(accs)))
        resumen[f"PLACEBO_{campo}"] = float(np.mean(accs))

    if a.ablation:
        # Ablación: ¿de dónde sale el tono? 6 series → 5 clima + 1 enjambre.
        dim = HUELLA_NBIN + ARMONICOS_HUELLA
        clima_idx = list(range(0, 5 * dim))          # las 5 primeras series
        sismo_idx = list(range(5 * dim, 6 * dim))    # la sexta
        for nombre, idx in (("solo-clima", clima_idx),
                            ("solo-enjambre", sismo_idx)):
            r = loo_centroide(X[:, idx], [c["familia"] for c in casos])
            log.info("ABLACIÓN familia %s: %.1f%% (n=%d) — comparar contra "
                     "el LOO familia completo de ESTA corrida",
                     nombre, 100 * r["acc"], r["n"])
            resumen[f"ABLACION_{nombre}"] = r["acc"]

    # Huellas por clase (la tabla de identificación, como la tela)
    ruta_out = Path(__file__).resolve().parents[1] / "estado" / "cimatica_firmas"
    ruta_out.mkdir(parents=True, exist_ok=True)
    filas = []
    import warnings
    for clase in sorted({c["clase"] for c in casos}):
        sub = [c for c in casos if c["clase"] == clase]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            m = np.nanmean(np.stack([c["vec"] for c in sub]), axis=0)
        filas.append([clase, len(sub)] + [round(float(v), 4) for v in m])
    hdr = ["clase", "n"] + [f"dim{i}" for i in range(X.shape[1])]
    with open(ruta_out / "huellas_por_clase.csv", "w") as f:
        f.write(",".join(hdr) + "\n")
        for fila in filas:
            f.write(",".join(str(v) for v in fila) + "\n")
    log.info("huellas por clase → %s", ruta_out / "huellas_por_clase.csv")

    with open(ruta_out / "loo_resumen.json", "w") as f:
        json.dump(resumen, f, indent=2, default=str)

    if not a.sin_figuras:
        figuras(casos, ruta_out)

    log.info("COMPLETADO en %.0fs — veredicto: "
             "clase %.1f%% vs nulo %.1f%% · tono(familia) %.1f%% vs nulo %.1f%%",
             time.time() - t0,
             100 * resumen["CLASE"]["acc"], 100 * resumen["CLASE"]["nulo_mayoria"],
             100 * resumen["FAMILIA (el tono)"]["acc"],
             100 * resumen["FAMILIA (el tono)"]["nulo_mayoria"])
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
