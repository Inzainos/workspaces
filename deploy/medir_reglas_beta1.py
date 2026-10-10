"""Las reglas de beta1, medidas contra la historia (regla 8).

El §7 de BITACORA_2026-10-08 las dejó abiertas: los umbrales de beta1 nunca
se midieron contra su distribución, y un umbral sin calibrar o bien dispara
siempre o bien nunca --- en los dos casos no discrimina nada.

Qué mide, contra qué:
  * `high_freq_ratio > 0.6` (rama ALERT sola) y `> 0.4` (con Schumann excitado):
    la fracción de energía espectral de Kp en periodos <= 12 h de la ventana
    de 48 muestras (6 días a 3 h). Se recalcula con la MISMA función del agente
    (`kp_spectral_features`), deslizando la ventana por TODA la historia de
    clima espacial, no una muestra.
  * `schumann_activity > 15` (excitado) y `> 30` (strong): contra TODAS las
    lecturas vivas de `tbl_schumann_vivo`.
  * `composite_vibration > 0.5`: hfr x actividad/100 --- aritméticamente
    exige actividad > 50 %; se comprueba contra los datos.

Aproximación declarada: la serie viva de Kp es la de NOAA a 3 h
(`kp_index`); aquí se reconstruye desde `tbl_clima_espacial_raw.kp_promedio`
(horaria) rebinada a 3 h. No es la serie exacta del vivo, sí su distribución.

Uso:  .venv/bin/python deploy/medir_reglas_beta1.py [db]
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np

sys.path.insert(0, "/home/deamon/workspaces")

from sentinel_omega.layers.geodynamic.beta1.agent import (  # noqa: E402
    kp_spectral_features,
)

DB = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/deamon/workspaces/sentinel_omega/data/SENTINEL_OMEGA_PRO.db"

VENTANA_MUESTRAS = 48       # la del agente: FFT_WINDOW_H
INTERVALO_H = 3             # KP_SAMPLE_INTERVAL_H


def resumen(nombre, vals, umbrales):
    v = np.asarray(vals, dtype=float)
    v = v[np.isfinite(v)]
    if not len(v):
        print(f"  {nombre}: SIN DATOS")
        return
    print(f"  {nombre:24} n={len(v):7,}  media={v.mean():.3f}  "
          f"mediana={np.median(v):.3f}  p90={np.percentile(v, 90):.3f}  "
          f"p99={np.percentile(v, 99):.3f}  max={v.max():.3f}")
    for u in umbrales:
        pct = 100.0 * float((v > u).sum()) / len(v)
        print(f"      > {u:4}: {pct:6.2f} %  ({int((v > u).sum()):,} de {len(v):,})")


def main() -> int:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)

    # Serie de Kp a 3 h desde la historia horaria.
    filas = c.execute(
        "SELECT timestamp_blk, kp_promedio FROM tbl_clima_espacial_raw "
        "WHERE kp_promedio IS NOT NULL ORDER BY timestamp_blk").fetchall()
    if len(filas) < VENTANA_MUESTRAS:
        print("sin historia de Kp suficiente")
        return 1
    por_bloque = {}
    for ts, kp in filas:
        h = ts[:13]                      # 'YYYY-MM-DD HH'
        hora = int(h[11:13]) // INTERVALO_H * INTERVALO_H
        por_bloque.setdefault((ts[:10], hora), []).append(float(kp))
    serie = sorted((d, h, sum(v) / len(v))
                   for (d, h), v in por_bloque.items())
    kp = [v for _, _, v in serie]
    print(f"Kp a {INTERVALO_H} h: {len(kp):,} muestras, "
          f"{serie[0][0]} -> {serie[-1][0]}")

    hfrs = []
    for i in range(VENTANA_MUESTRAS, len(kp)):
        window = np.asarray(kp[i - VENTANA_MUESTRAS:i], dtype=float)
        ps = np.abs(np.fft.rfft(window)) ** 2
        hfrs.append(kp_spectral_features(ps, INTERVALO_H * 3600)["high_freq_ratio"])

    print("\n=== high_freq_ratio (la MISMA funcion del agente, toda la historia) ===")
    resumen("high_freq_ratio", hfrs, (0.4, 0.6))

    act = [r[0] for r in c.execute(
        "SELECT schumann_activity FROM tbl_schumann_vivo "
        "WHERE schumann_activity IS NOT NULL").fetchall()]
    print("\n=== schumann_activity (lecturas vivas, todas) ===")
    resumen("actividad %", act, (15.0, 30.0, 50.0))

    # composite_vibration: hfr x act/100 con el peor hfr observado.
    if act:
        print("\n=== composite_vibration > 0.5: aritmetica y datos ===")
        print(f"  max hfr observado: {max(hfrs):.3f}; max actividad: {max(act):.1f} %")
        print(f"  comp_vib maximo posible con esos datos: "
              f"{max(hfrs) * max(act) / 100:.3f}  (umbral: 0.5)")
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
