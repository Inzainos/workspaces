"""La FIGURA de una ventana: la curva, no el promedio.

`extraer_features_ventana` colapsa 336 h en agregados (media, max, std) y ahi
se pierde la forma. Esto saca la CURVA: cada canal horario se rebina a N
puntos y se z-normaliza, asi que la comparacion es sobre la FORMA --- invariante
al nivel y a la escala --- y no sobre la magnitud.

Canales con serie horaria real (medido 2026-10-09):
  tbl_clima_espacial_raw      287.105 filas  1994-2026  (Bz, viento, Kp, protones)
  tbl_astronomia_cinematica   280.352 filas  1994-2025  (LOD, fase lunar)
Schumann queda FUERA a proposito: 880 filas, un nodo, 76 % con el mismo valor.
"""
from __future__ import annotations
import math
import numpy as np

VENTANA_H = 336
N_BINS = 48            # 7 h por bin: robusto a huecos, conserva la forma

CANALES_CLIMA = ("bz_promedio", "bz_derivada", "viento_solar_avg",
                 "kp_promedio", "densidad_protones")
CANALES_ASTRO = ("lod_ms", "fase_lunar_pct")
CANALES_SISMO = ("sismo_count",)          # OMORI: separado y apagado por defecto


def _rebin(pares, t_fin_h, n_bins=N_BINS):
    """pares = [(horas_antes_del_fin, valor)] -> curva de n_bins (NaN si vacio)."""
    out = np.full(n_bins, np.nan)
    if not pares:
        return out
    acc = [[] for _ in range(n_bins)]
    ancho = VENTANA_H / n_bins
    for h, v in pares:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        i = int((VENTANA_H - h) / ancho)      # 0 = mas antiguo
        if 0 <= i < n_bins:
            acc[i].append(float(v))
    for i, vals in enumerate(acc):
        if vals:
            out[i] = sum(vals) / len(vals)
    return out


def _znorm(c):
    """Forma: resta la media y divide por la desviacion. Sin dato -> NaN."""
    m = np.nanmean(c) if np.any(~np.isnan(c)) else np.nan
    s = np.nanstd(c) if np.any(~np.isnan(c)) else np.nan
    if not np.isfinite(m) or not np.isfinite(s) or s < 1e-12:
        return np.full_like(c, np.nan)     # plano = sin forma, no una forma
    return (c - m) / s


def figura(conn, ts_fin: str, id_nodo: int | None = None,
           con_sismo: bool = False) -> dict:
    """{canal: curva z-normalizada de N_BINS} para la ventana que acaba en ts_fin."""
    fig = {}
    q = ("SELECT (julianday(?) - julianday(timestamp_blk)) * 24.0 AS h, {cols} "
         "FROM {tabla} WHERE timestamp_blk < ? "
         "AND timestamp_blk >= datetime(?, '-{v} hours')")

    for tabla, canales in (("tbl_clima_espacial_raw", CANALES_CLIMA),
                           ("tbl_astronomia_cinematica", CANALES_ASTRO)):
        sql = q.format(cols=", ".join(canales), tabla=tabla, v=VENTANA_H)
        try:
            filas = conn.execute(sql, (ts_fin, ts_fin, ts_fin)).fetchall()
        except Exception:
            continue
        for j, canal in enumerate(canales, start=1):
            fig[canal] = _znorm(_rebin([(r[0], r[j]) for r in filas], ts_fin))

    if con_sismo and id_nodo is not None:
        sql = ("SELECT (julianday(?) - julianday(timestamp_blk)) * 24.0, sismo_count "
               f"FROM tbl_historico_sismico_raw WHERE id_nodo = ? "
               "AND timestamp_blk < ? AND timestamp_blk >= datetime(?, "
               f"'-{VENTANA_H} hours')")
        try:
            filas = conn.execute(sql, (ts_fin, id_nodo, ts_fin, ts_fin)).fetchall()
            fig["sismo_count"] = _znorm(_rebin([(r[0], r[1]) for r in filas], ts_fin))
        except Exception:
            pass
    return fig


def parecido(a: dict, b: dict) -> float | None:
    """Correlacion media por canal: 1 = misma forma, 0 = nada que ver.

    Es la medida natural de «misma figura»: invariante al desplazamiento y a la
    escala, sensible al perfil. Un canal plano en cualquiera de las dos no
    cuenta --- no se inventa forma donde no hay.
    """
    rs = []
    for canal in set(a) & set(b):
        x, y = a[canal], b[canal]
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < N_BINS // 3:
            continue
        xv, yv = x[m], y[m]
        if np.std(xv) < 1e-12 or np.std(yv) < 1e-12:
            continue
        r = float(np.corrcoef(xv, yv)[0, 1])
        if np.isfinite(r):
            rs.append(r)
    return float(np.mean(rs)) if rs else None
