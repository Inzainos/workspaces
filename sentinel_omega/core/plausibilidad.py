"""Plausibilidad física en la frontera de ingesta (ítem 3 del plan, libro:
Data Cleaning Pocket Primer, ~/conocimiento — validación en el punto de
entrada).

Qué es y qué NO es (regla 9 del repo):
- ES un filtro de IMPOSIBILIDAD física: presión de 2 hPa, Kp de 14, un AQI
  de 0 en la escala 1–5 de OWM. Eso es API corrupta o unidad equivocada, y
  se reporta como NULL (regla 7/8), no como número.
- NO es un detector de anomalías: una presión de 960 hPa en un huracán es
  rara pero POSIBLE, y el rango lo admite. Los rangos se calibraron
  GENEROSOS a propósito: el objetivo es cazar basura de API sin tirar la
  señal de un evento real. Ajustarlos exige la misma vara que cualquier
  umbral: medir qué % de casos dispara antes de cambiarlos.

Los rangos de Kp/AQI son de la DOCUMENTACIÓN de la fuente (NOAA 0–9, OWM
1–5), no inventados. El resto son órdenes de magnitud físicos con colchón.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# nombre → (mín, máx, unidad) — generosos, imposibilidad física solamente.
RANGOS: Dict[str, tuple] = {
    # OWM clima (openweathermap.py)
    "pressure_hpa": (850.0, 1080.0, "hPa"),
    "grnd_level_hpa": (300.0, 1080.0, "hPa"),
    "temp_c": (-60.0, 60.0, "°C"),
    "humidity_pct": (0.0, 100.0, "%"),
    "visibility_m": (0.0, 80_000.0, "m"),
    "wind_speed_ms": (0.0, 120.0, "m/s"),
    "wind_gust_ms": (0.0, 150.0, "m/s"),
    "clouds_pct": (0.0, 100.0, "%"),
    "rain_1h": (0.0, 500.0, "mm"),
    "snow_1h": (0.0, 500.0, "mm"),
    # OWM aire (μg/m³, colchón x10 sobre típicos urbanos)
    "co": (0.0, 50_000.0, "μg/m³"),
    "so2": (0.0, 5_000.0, "μg/m³"),
    "no2": (0.0, 5_000.0, "μg/m³"),
    "o3": (0.0, 5_000.0, "μg/m³"),
    "pm2_5": (0.0, 1_000.0, "μg/m³"),
    "pm10": (0.0, 2_000.0, "μg/m³"),
    "aqi": (1, 5, "índice OWM — 0 NO existe"),
    # NOAA (noaa.py / risk_calculator)
    "kp": (0.0, 9.0, "índice NOAA"),
    "bz_nT": (-200.0, 200.0, "nT"),
    "viento_solar_kms": (0.0, 3_000.0, "km/s"),
    # GOES X-ray: el piso 1e-9 original era MUY apretado — el fondo real del
    # sol quieto en mínimo solar ronda 9,99e-10 y el validador lo anuló en
    # cascada (medido en vivo 2026-10-20, primer ciclo con el filtro: 4+
    # descartes de datos legítimos). El piso de IMPOSIBILIDAD física (ruido
    # del sensor) está en ~1e-11; regla 9: el rango se calibró contra el
    # dato real, no contra la intuición.
    "goes_flux": (1e-11, 1e-2, "W/m²"),
    "schumann_activity_pct": (0.0, 100.0, "%"),
    "schumann_wpc": (0.0, 1.0, "fracción 0–1 (activity/100)"),
    "lod_ms": (-10.0, 10.0, "ms de anomalía IERS"),
}


def validar(nombre: str, valor, origen: str = "") -> Optional[float]:
    """El valor si es físicamente plausible; None si no (y log).

    None/NaN pasan como None (ausencia ≠ implausible). El llamador ya
    distingue ausencia; aquí solo cazamos lo imposible.
    """
    if valor is None:
        return None
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    rango = RANGOS.get(nombre)
    if rango is None:
        return v  # sin rango declarado = pasa (fail-open deliberado:
        # añadir validación nueva no debe tumbar lecturas viejas)
    lo, hi, unidad = rango
    if lo <= v <= hi:
        return v
    logger.warning(
        "PLAUSIBILIDAD: %s=%s (%s) fuera de rango físico [%s, %s] — descartado"
        " como NULL%s",
        nombre, v, unidad, lo, hi,
        f" (origen: {origen})" if origen else "",
    )
    return None
