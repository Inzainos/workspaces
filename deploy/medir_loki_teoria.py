"""Medición para el rediseño de Loki — la teoría del operador, operacionalizada.

Fuente de la teoría: «TEORÍA DEL CAMPO UNIFICADO FRACTAL» (operador, 2026-09-16).
Tres pasos del «Masaje Bayesiano Tridimensional», cada uno medido aquí contra
287.178 h de historia (regla 8: tasa de disparo; regla 11: nulo al lado):

  A. FOURIER (paso B de la teoría): picos espectrales de Kp/viento/Bz
     contra el NULO DE RUIDO ROJO (AR(1) + chi² de Gilman et al. 1963).
     La mayoría de las series geofísicas son ruido rojo: un pico sólo
     cuenta si supera SU nulo. La física conocida dice que debe aparecer
     la rotación solar (~27,28 d Carrington; recurrencia de agujeros
     coronales) y los armónicos estacionales (Russell-McPherron).

  B. GANANCIA DE RECURRENCIA (el pico, en el dominio del tiempo): si el
     espectro muestra recurrencia, ¿predecir «hoy hay tormenta porque la
     hubo hace 27 días» gana contra el azar? P( tormenta | tormenta hace
     26-29 d ) contra P( tormenta ) — la ganancia de Molchan de la regla.

  C. GAUSS-JORDAN (paso A de la teoría): rango de la matriz ventanas×rasgos
     del clima espacial. La teoría lo usa para LIMPIAR (revelar variables
     ocultas); la pregunta honesta es si el rango/colinealidad discrimina
     calma de tormenta o si es preprocesado, no señal.

Uso:
    .venv/bin/python deploy/medir_loki_teoria.py [db_path]

Todo en solo lectura (mode=ro). No toca producción.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np

DB_DEFAULT = "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"

# Banda de recurrencia: rotación sinódica de Carrington 27,275 d; ±1,5 d
# de tolerancia es la usada operativamente en meteorología espacial.
REC_DIAS_MIN, REC_DIAS_MAX = 25.8, 28.8


def cargar(conn: sqlite3.Connection):
    """Serie horaria del backcast (1994→2025). El tramo vivo es minoritario
    y trae huecos de red: fuera, de lo contrario la 'señal' mide outage."""
    filas = conn.execute(
        "SELECT timestamp_blk, kp_max, kp_promedio, bz_promedio, bz_min, "
        "viento_solar_max, viento_solar_avg, proton_flux_10mev, densidad_protones "
        "FROM tbl_clima_espacial_raw "
        "WHERE timestamp_blk < '2026-01-01' ORDER BY timestamp_blk"
    ).fetchall()
    cols = list(zip(*filas))
    ts = np.array(cols[0], dtype="U16")
    kp_max = np.array([np.nan if v is None else float(v) for v in cols[1]])
    kp_prom = np.array([np.nan if v is None else float(v) for v in cols[2]])
    bz = np.array([np.nan if v is None else float(v) for v in cols[3]])
    bz_min = np.array([np.nan if v is None else float(v) for v in cols[4]])
    vmax = np.array([np.nan if v is None else float(v) for v in cols[5]])
    vavg = np.array([np.nan if v is None else float(v) for v in cols[6]])
    prot = np.array([np.nan if v is None else float(v) for v in cols[7]])
    dens = np.array([np.nan if v is None else float(v) for v in cols[8]])
    return ts, dict(kp_max=kp_max, kp_prom=kp_prom, bz=bz, bz_min=bz_min,
                    vmax=vmax, vavg=vavg, prot=prot, dens=dens)


def diario(serie: np.ndarray, ts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Media diaria: enfoca el espectro en periodos >= 2 d (rotación,
    estacionales) y amortigua el ciclo diurno ionosférico."""
    dias = np.array([t[:10] for t in ts])
    uniq, idx = np.unique(dias, return_index=True)
    orden = np.argsort(ts)
    dias_o = dias[orden]
    serie_o = serie[orden]
    bordes = np.searchsorted(dias_o, uniq)
    bordes = np.append(bordes, len(dias_o))
    out = np.full(len(uniq), np.nan)
    for i in range(len(uniq)):
        seg = serie_o[bordes[i]:bordes[i + 1]]
        seg = seg[np.isfinite(seg)]
        if seg.size:
            out[i] = seg.mean()
    return uniq, out


def espectro_contra_ruido_rojo(x: np.ndarray, etiqueta: str) -> None:
    """Periodograma (Welch) + nulo AR(1) con umbral chi² 95 % (Gilman 1963).

    Un pico SÓLO cuenta si supera el nulo: la mayoría de las series
    geofísicas son ruido rojo y 'parecen' periódicas por autocorrelación.
    """
    x = x[np.isfinite(x)]
    n = x.size
    # AR(1) estimado por autocorresión de lag-1
    r1 = np.corrcoef(x[:-1], x[1:])[0, 1]
    f, pxx = _welch(x)
    # Espectro teórico AR(1) (normalizado a la potencia media observada)
    f_nyq = 0.5
    w = f / f_nyq * np.pi
    teo = (1 - r1 ** 2) / (1 - 2 * r1 * np.cos(w) + r1 ** 2)
    teo *= pxx.mean() / teo.mean()
    # Umbral 95 %: chi²₂ (2 grados por segmento promediado de Welch con 50 %
    # de solape ≈ escala), aproximación estándar de Gilman
    umbral = teo * 1.96  # cuantil ~95 de chi2_2/exponencial, escala por dof
    print(f"\n  [{etiqueta}] n_dias={n}  AR(1) r1={r1:.3f}")
    picos = []
    for target_d, nombre in [(365.25, "anual"), (182.6, "semi-anual"),
                             (27.275, "rotación Carrington"), (13.6, "media rotación"),
                             (9.1, "tercio de rotación")]:
        f_t = 1.0 / target_d
        i = np.argmin(np.abs(f - f_t))
        per_d = 1.0 / f[i]
        sig = "✓ SUPERA" if pxx[i] > umbral[i] else "✗ bajo el nulo"
        ratio = pxx[i] / umbral[i]
        picos.append((nombre, per_d, ratio, sig))
        print(f"    {nombre:22s} P={per_d:6.2f} d  potencia/umbral={ratio:6.2f}  {sig}")
    return picos


def _welch(x: np.ndarray, seg=256, solape=0.5):
    """Welch simple con ventana Hann; devuelve freq/día y potencia."""
    paso = int(seg * (1 - solape))
    win = np.hanning(seg)
    acum = None
    nseg = 0
    for i in range(0, x.size - seg + 1, paso):
        s = x[i:i + seg] - x[i:i + seg].mean()
        p = np.abs(np.fft.rfft(s * win)) ** 2
        acum = p if acum is None else acum + p
        nseg += 1
    pxx = acum / nseg / (win ** 2).sum()
    f = np.arange(pxx.size) / seg          # ciclos/muestra
    return f, pxx


def ganancia_recurrencia(kp_max_d: np.ndarray) -> None:
    """El pico de 27 d traducido a regla: ¿P(tormenta | tormenta hace
    26-29 d) > P(tormenta)? Molchan de la recurrencia, con su nulo."""
    tormenta = kp_max_d >= 5.0
    n = len(tormenta)
    base = tormenta.mean()
    ventana = [int(REC_DIAS_MIN), int(REC_DIAS_MAX)]
    hubo_hace = np.zeros(n, dtype=bool)
    for d in range(ventana[0], ventana[1] + 1):
        hubo_hace[d:] |= tormenta[:-d]
    evaluable = hubo_hace  # primer mes sin antecedente: fuera
    cond = tormenta[evaluable].mean() if evaluable.any() else float("nan")
    ganancia = cond / base if base > 0 else float("nan")
    print(f"\n  Recurrencia [26-29 d]: P(tormenta)={base*100:.2f}%  "
          f"P(tormenta | tormenta hace 26-29 d)={cond*100:.2f}%  "
          f"ganancia={ganancia:.2f}x")
    # Y sin tormenta previa (control espejo): la recurrencia tiene que
    # diferir de lo que pasa cuando NO hubo antecedente
    sin_ant = ~hubo_hace
    if sin_ant.any():
        cond2 = tormenta[sin_ant].mean()
        print(f"  Control: P(tormenta | SIN tormenta hace 26-29 d)={cond2*100:.2f}%  "
              f"— la diferencia {cond*100:.1f}% vs {cond2*100:.1f}% es la señal real")


def rango_por_ventana(series: dict, ts: np.ndarray) -> None:
    """Gauss-Jordan operacionalizado: rango de la matriz horas×rasgos por
    ventana de 7 d, calma contra tormenta. Pregunta: ¿discrimina?"""
    M = np.column_stack([series[k] for k in
                         # `prot` fuera: 0 % de cobertura en el backcast
                         # (documentado: el histórico nunca tuvo flujo de
                         # protones). Con ella, ninguna fila era finita.
                         ("bz", "bz_min", "vmax", "vavg", "kp_max", "kp_prom", "dens")])
    kp = series["kp_max"]
    WIN = 168  # 7 d en horas
    rangos_calma, rangos_torm = [], []
    for i in range(0, len(M) - WIN, WIN):        # ventanas contiguas
        w = M[i:i + WIN]
        w = w[np.isfinite(w).all(axis=1)]        # filas completas solamente
        if w.shape[0] < 24:                      # sin filas, sin rango honesto
            continue
        r = np.linalg.matrix_rank(w)
        (rangos_torm if kp[i:i + WIN].max() >= 5 else rangos_calma).append(r)
    c = np.array(rangos_calma) if rangos_calma else np.array([np.nan])
    t = np.array(rangos_torm) if rangos_torm else np.array([np.nan])
    print(f"\n  Rango de la matriz 168h×7 (Gauss-Jordan), filas finitas:")
    print(f"    calma     n={c.size:>4}  media={np.mean(c):.2f}  p5={np.percentile(c,5):.0f}  p95={np.percentile(c,95):.0f}")
    print(f"    tormenta  n={t.size:>4}  media={np.mean(t):.2f}  p5={np.percentile(t,5):.0f}  p95={np.percentile(t,95):.0f}")
    print("    (8 = rango completo; si calma y tormenta dan igual, el paso es")
    print("     preprocesado — limpiar redundancias — no señal de decisión)")


def punto_de_colapso(series: dict, ts: np.ndarray) -> None:
    """La conjunción de la teoría: resonancia con el ciclo mayor (hubo
    tormenta hace 26-29 d) Y grieta viva (bz_min del día <= -5). El
    «colapso» es P(tormenta | ambas) contra sus partes y contra la base:
    la tabla de Bayes que necesita loki para un posterior honesto."""
    dias, kp_d = diario(series["kp_max"], ts)
    _, bzmin_d = diario(series["bz_min"], ts)
    n = len(kp_d)
    tormenta = kp_d >= 5.0
    rec = np.zeros(n, dtype=bool)
    for d in range(int(REC_DIAS_MIN), int(REC_DIAS_MAX) + 1):
        rec[d:] |= tormenta[:-d]
    grieta = bzmin_d <= -5.0
    ok = np.isfinite(bzmin_d)
    base = tormenta.mean()

    def p(cond_mask):
        m = cond_mask & ok
        if m.sum() == 0:
            return float("nan"), 0, 0
        hits = int(tormenta[m].sum())
        return tormenta[m].mean() * 100, hits, int(m.sum())

    print(f"\n  PUNTO DE COLAPSO (resonancia ∧ grieta) — n_días={n}, base={base*100:.2f}%:")
    for etiqueta, m in [
        ("base (P a secas)",                    np.ones(n, bool)),
        ("solo resonancia 26-29 d",             rec),
        ("solo grieta (bz_min<=-5)",             grieta),
        ("COLAPSO: resonancia ∧ grieta",         rec & grieta),
    ]:
        prob, hits, tot = p(m)
        print(f"    {etiqueta:32s} n={tot:>5}  aciertos={hits:>3}  P(tormenta)={prob:6.2f}%")
    m_col = rec & grieta & ok
    if m_col.sum() > 0:
        pc = tormenta[m_col].mean()
        print(f"    → ganancia del colapso contra la base: {pc/base:.2f}x (n={m_col.sum()} días en 32 años: estimación FRÁGIL, reportada con su n)")


def main() -> None:
    db = sys.argv[1] if len(sys.argv) > 1 else DB_DEFAULT
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30.0)
    ts, series = cargar(conn)
    conn.close()
    print(f"Serie horaria 1994→2025: {len(ts)} h "
          f"({ts[0]} → {ts[-1]})")

    # A. Fourier contra ruido rojo
    for clave in ("kp_max", "vmax", "bz"):
        dias, x = diario(series[clave], ts)
        espectro_contra_ruido_rojo(x, f"{clave} (media diaria)")

    # B. La ganancia de la recurrencia (el pico que importe, en regla)
    dias, kp_d = diario(series["kp_max"], ts)
    ganancia_recurrencia(kp_d)

    # B2. El punto de colapso: resonancia ∧ grieta (la conjunción de la teoría)
    punto_de_colapso(series, ts)

    # C. Gauss-Jordan: rango por ventana
    rango_por_ventana(series, ts)


if __name__ == "__main__":
    main()
