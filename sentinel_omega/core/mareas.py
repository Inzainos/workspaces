"""Marea terrestre: el tirón de la Luna y el Sol sobre la corteza.

Por qué entra en beta2 (2026-09-26, a petición del operador)
------------------------------------------------------------
beta2 es el bot de desgasificación volcánica y **hoy no tiene ni una fuente
viva**: `tbl_desgasificacion_raw` se paró el 2026-07-31, así que en la ventana
viva sus cuatro rasgos llegan siempre ausentes. Es, además, el único con sesgo
grave (in-sample 0,983 contra causal 0,514) y a la vez el mejor de los nueve en
M5. Un especialista sin materia.

La marea arregla las dos cosas a la vez, y por una razón de fondo: el esfuerzo
de marea es un forzamiento candidato conocido para sismicidad y para actividad
volcánica, y se **calcula por efemérides**. No depende de ninguna API, no se
cae, no tiene huecos y existe para cualquier instante --- pasado o futuro. Es
la única fuente del sistema con cobertura del 100 %.

Qué se calcula
--------------
La aceleración de marea de un cuerpo de masa M a distancia d, en la superficie
de una Tierra de radio R, es `2·G·M·R / d³`. La de la Luna y la del Sol se
combinan según la **elongación** (el ángulo Luna-Sol visto desde la Tierra),
con el factor 2 del armónico de segundo grado que hace que la marea sea
semidiurna --- dos abultamientos, no uno:

    a_total = sqrt(a_L² + a_S² + 2·a_L·a_S·cos(2·elongación))

En sicigia (luna nueva o llena, elongación 0° o 180°) los dos tiran en línea y
la marea es máxima; en cuadratura se restan.

Comprobado contra valores de libro antes de conectarlo: la razón Sol/Luna sale
**0,448** (el valor conocido es ~0,46) y la razón sicigia/cuadratura del mes
sale 3,7×, que es lo que toca al combinar el ciclo de fases (2,7×) con el de
perigeo-apogeo (~1,3×).

Todo se devuelve en **µm/s²** (×1e6): en m/s² son números de orden 1e-6 y
conviven mal con rasgos como el viento solar, de orden 1e2.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, Optional

logger = logging.getLogger("mareas")

# Constantes físicas, en SI.
_G = 6.67430e-11          # constante gravitacional
_R_TIERRA = 6.371e6       # radio medio, m
_M_LUNA = 7.342e22        # kg
_M_SOL = 1.98847e30       # kg
_UA = 1.495978707e11      # unidad astronómica, m
_D_LUNA_MEDIA = 3.84399e8 # semieje mayor de la órbita lunar, m

_A_MICRO = 1e6            # m/s² → µm/s²


def _aceleracion(masa: float, distancia_m: float) -> float:
    """El término de marea `2·G·M·R / d³`, en m/s²."""
    if distancia_m <= 0:
        return 0.0
    return 2.0 * _G * masa * _R_TIERRA / distancia_m ** 3


def marea_en(momento) -> Dict[str, float]:
    """Los rasgos de marea en ese instante, o {} si no hay efemérides.

    `momento` es lo que acepte `ephem.Date`: un datetime, una cadena o un
    número. Si `ephem` no está instalado se devuelve {} --- ausente, nunca un
    cero que el modelo leería como «no hay marea».
    """
    try:
        import ephem
    except ImportError:
        logger.warning("ephem no está: la marea queda ausente, no en cero")
        return {}
    try:
        luna = ephem.Moon(momento)
        sol = ephem.Sun(momento)
        d_luna = float(luna.earth_distance) * _UA
        d_sol = float(sol.earth_distance) * _UA
        elong = float(luna.elong)   # radianes, Luna respecto al Sol
    except (TypeError, ValueError) as e:
        logger.warning("efemérides no disponibles para %s: %s", momento, e)
        return {}

    a_luna = _aceleracion(_M_LUNA, d_luna)
    a_sol = _aceleracion(_M_SOL, d_sol)
    # cos(2·elongación): +1 en sicigia (marea viva), -1 en cuadratura (muerta).
    coseno = math.cos(2.0 * elong)
    a_total = math.sqrt(max(0.0, a_luna ** 2 + a_sol ** 2
                            + 2.0 * a_luna * a_sol * coseno))
    return {
        "marea_total": a_total * _A_MICRO,
        "marea_luna": a_luna * _A_MICRO,
        "marea_sol": a_sol * _A_MICRO,
        # El indicador de viva/muerta, ya normalizado a [-1, 1].
        "marea_sicigia": coseno,
        # Perigeo/apogeo: <1 es luna más cerca, y la marea va con d³.
        "marea_dist_luna": d_luna / _D_LUNA_MEDIA,
    }


def marea_ventana(momento, horas: int = 24, pasos: int = 25) -> Dict[str, float]:
    """Cómo se MUEVE la marea en la ventana que termina en `momento`.

    No basta con cuánto vale: lo que se asocia al disparo de eventos es la
    **variación** del esfuerzo, así que se añaden el recorrido de la ventana y
    la pendiente del último tramo. `pasos` marca la resolución (25 pasos en
    24 h ≈ uno por hora), suficiente para el ciclo semidiurno.
    """
    import datetime as _dt

    base = marea_en(momento)
    if not base:
        return {}
    try:
        fin = (momento if isinstance(momento, _dt.datetime)
               else _dt.datetime.fromisoformat(str(momento)))
    except (TypeError, ValueError):
        return base

    serie = []
    for i in range(pasos):
        t = fin - _dt.timedelta(hours=horas * (pasos - 1 - i) / max(pasos - 1, 1))
        m = marea_en(t)
        if m:
            serie.append(m["marea_total"])
    if len(serie) < 2:
        return base

    fuera = dict(base)
    fuera[f"marea_rango_{horas}h"] = max(serie) - min(serie)
    fuera[f"marea_max_{horas}h"] = max(serie)
    # Pendiente del último tramo: si el esfuerzo sube o baja AHORA.
    dt_h = horas / max(pasos - 1, 1)
    fuera["marea_deriv"] = (serie[-1] - serie[-2]) / dt_h
    return fuera


def marea_para_ciclo(momento: Optional[object] = None) -> Dict[str, float]:
    """Lo que el ciclo vivo mete en el vector: marea instantánea + ventana 24 h."""
    import datetime as _dt

    if momento is None:
        momento = _dt.datetime.utcnow()
    return marea_ventana(momento, horas=24)
