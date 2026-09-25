"""
Molchan Baseline — modelo nulo "alertar siempre"

Un hit-rate solo significa algo comparado contra lo que lograría una
estrategia SIN habilidad. El modelo nulo de Molchan es el peor predictor
honesto posible: alerta SIEMPRE, en cada slot de 72 h, en cada ubicación
evaluada. Su hit-rate es exactamente la tasa base de sismicidad
(la probabilidad de que caiga un evento M>=umbral dentro del radio de 5°
y la ventana de 72 h de una alerta cualquiera).

Ganancia = hit_rate_sistema / tasa_base:
  - > 1  → el sistema aporta información real sobre alertar a ciegas
  - <= 1 → el sistema NO supera al modelo nulo (fantasía de habilidad)

Misma geometría que AssertivityTracker: radio euclidiano en grados
(default 5°) y ventana de precursor de 72 h.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DEFAULT_RADIUS_DEG = 5.0
DEFAULT_WINDOW_H = 72


def _event_epoch(event: Dict[str, Any]) -> Optional[float]:
    """Epoch en segundos del evento; acepta segundos o milisegundos USGS."""
    t = event.get("time")
    if t is None:
        return None
    try:
        t = float(t)
    except (TypeError, ValueError):
        return None
    # USGS FDSN entrega milisegundos; cualquier valor > ~year 33658 en
    # segundos es en realidad ms.
    return t / 1000.0 if t > 1e12 else t


@dataclass
class BaselineResult:
    base_rate: float                 # hit-rate del modelo nulo alertar-siempre
    system_hit_rate: float           # hit-rate real del sistema (viva)
    gain: Optional[float]            # None si la tasa base es 0 (sin eventos)
    n_cells: int                     # celdas (ubicación × slot de 72 h)
    n_cells_with_event: int          # celdas con >= 1 evento M>=umbral
    window_h: int
    radius_degrees: float

    @property
    def veredicto(self) -> str:
        if self.gain is None:
            return "SIN EVENTOS EN VENTANA — ganancia indefinida"
        if self.gain > 1.5:
            return "GANANCIA REAL sobre alertar-siempre"
        if self.gain > 1.0:
            return "ganancia marginal sobre el modelo nulo"
        return "SIN ganancia — no supera a alertar-siempre"


class AlwaysAlertBaseline:
    """Modelo nulo de Molchan: alerta siempre, en todas partes.

    base_rate() responde: si hubiéramos alertado en TODAS las ubicaciones
    evaluadas, en TODOS los slots de 72 h de la ventana, ¿qué fracción de
    esas alertas habría sido "confirmada" por un evento? Esa fracción es
    el piso que el sistema tiene que superar para reclamar habilidad.
    """

    def __init__(
        self,
        radius_degrees: float = DEFAULT_RADIUS_DEG,
        window_h: int = DEFAULT_WINDOW_H,
    ):
        self._radius = radius_degrees
        self._window_h = window_h

    def base_rate(
        self,
        locations: Sequence[Tuple[float, float]],
        events: List[Dict[str, Any]],
        window_days: int,
        min_magnitude: float = 4.5,
        now: Optional[float] = None,
    ) -> Tuple[float, int, int]:
        """(tasa_base, celdas_con_evento, celdas_totales)."""
        if not locations or window_days <= 0:
            return 0.0, 0, 0

        now = now if now is not None else time.time()
        start = now - window_days * 86400
        n_slots = max(1, int(np.ceil(window_days * 24 / self._window_h)))
        slot_s = self._window_h * 3600.0

        qualifying = []
        for e in events:
            if e.get("magnitude", 0) < min_magnitude:
                continue
            epoch = _event_epoch(e)
            lat, lon = e.get("latitude"), e.get("longitude")
            if lat is None or lon is None:
                continue
            qualifying.append((float(lat), float(lon), epoch))

        n_cells = len(locations) * n_slots
        hits = 0
        for lat0, lon0 in locations:
            for s in range(n_slots):
                s_ini = start + s * slot_s
                s_fin = s_ini + slot_s
                for elat, elon, eepoch in qualifying:
                    if eepoch is not None and not (s_ini <= eepoch < s_fin):
                        continue
                    d = np.sqrt((lat0 - elat) ** 2 + (lon0 - elon) ** 2)
                    if d <= self._radius:
                        hits += 1
                        break
        return hits / n_cells, hits, n_cells

    def evaluate(
        self,
        locations: Sequence[Tuple[float, float]],
        events: List[Dict[str, Any]],
        system_hit_rate: float,
        window_days: int,
        min_magnitude: float = 4.5,
        now: Optional[float] = None,
    ) -> BaselineResult:
        rate, cells_hit, cells = self.base_rate(
            locations, events, window_days, min_magnitude, now=now
        )
        gain = (system_hit_rate / rate) if rate > 0 else None
        return BaselineResult(
            base_rate=rate,
            system_hit_rate=system_hit_rate,
            gain=round(gain, 3) if gain is not None else None,
            n_cells=cells,
            n_cells_with_event=cells_hit,
            window_h=self._window_h,
            radius_degrees=self._radius,
        )


# ─── Molchan sobre los veredictos del Juez ────────────────────────────────────
#
# El mismo criterio, aplicado a lo que el Juez ya resolvió en la fase viva.
# Vive aquí, y no dentro del script del reporte, porque es el concepto de este
# módulo y porque una métrica que decide si el sistema sirve tiene que poder
# probarse sin base de datos.
#
# Corregido el 2026-09-25: el reporte calculaba la ganancia como
# (aciertos / TODAS las ventanas) ÷ tasa base. El numerador contaba cada «dije
# calma y hubo calma», que es el 98% de las ventanas, así que un bot MUDO
# sacaba 56.70× y el sistema 53.50%×: la métrica premiaba callarse, justo lo
# contrario del diseño del Juez (un FALLO cuesta 10 o 20; un falso positivo, 1).

@dataclass
class VeredictosResult:
    """Molchan a partir de veredictos ya resueltos."""

    ventanas: int
    con_evento: int
    alarmas: int
    detectados: int
    fallos: int
    falsos_positivos: int
    tasa_base: float                 # P(evento en una ventana cualquiera)
    precision: Optional[float]       # P(evento | el sistema alarmó)
    tau: float                       # fracción de ventanas en alarma
    deteccion: Optional[float]       # fracción de eventos detectados
    ganancia: Optional[float]        # precision / tasa_base
    diagonal: Optional[float]        # (1 - detección) + tau; 1.0 = sin habilidad
    asertividad: float               # aciertos / ventanas (incluye los silencios)
    asertividad_muda: float          # lo que saca un bot que nunca alarma
    coste_sistema: float
    coste_mudo: float
    coste_alarmista: float
    umbral_rentable: float           # P(evento) a partir de la cual alarmar paga

    @property
    def veredicto(self) -> str:
        if self.ganancia is None:
            return "sin alarmas o sin eventos — ganancia indefinida"
        if self.ganancia > 1.5:
            return "GANANCIA REAL: el sistema aporta información"
        if self.ganancia > 1.0:
            return "ganancia marginal sobre alertar a ciegas"
        return "SIN ganancia — alertar siempre habría rendido igual o mejor"


def evaluar_veredictos(
    filas: Sequence[Tuple[str, str]],
    sev_fallo: float = 10.0,
    sev_falso_positivo: float = 1.0,
) -> Optional[VeredictosResult]:
    """Evalúa `(verdad, resultado)` ya resueltos por el Juez.

    Una ventana tuvo evento si su `verdad` NO empieza por «sin eventos». El
    veredicto identifica la decisión sin depender del vocabulario de
    predicciones, que cambia entre capas: `FALSO_POSITIVO` es alarma sin
    evento, y un `ACIERTO` con evento solo puede venir de una alarma (callarse
    con evento sería `FALLO`).

    El coste pesa cada error con las severidades del Juez, para poder comparar
    al sistema con las dos estrategias tontas en la moneda del diseño: castigar
    el silencio diez veces más que la falsa alarma es deliberado, para que los
    bots no se acostumbren a callar. `umbral_rentable` es la consecuencia
    aritmética de esa asimetría: alarmar sale a cuenta cuando la probabilidad
    de evento en la ventana supera sev_falso_positivo / (sev_fallo + sev_fp).
    """
    if not filas:
        return None
    ventanas = len(filas)
    tuvo = [not str(v or "").startswith("sin eventos") for v, _ in filas]
    con_evento = sum(tuvo)
    aciertos = sum(1 for _, r in filas if r == "ACIERTO")
    detectados = sum(1 for (v, r), ev in zip(filas, tuvo) if r == "ACIERTO" and ev)
    falsos_pos = sum(1 for _, r in filas if r == "FALSO_POSITIVO")
    fallos = sum(1 for _, r in filas if r == "FALLO")
    alarmas = detectados + falsos_pos

    tasa_base = con_evento / ventanas
    precision = (detectados / alarmas) if alarmas else None
    deteccion = (detectados / con_evento) if con_evento else None
    ganancia = (precision / tasa_base) if (precision is not None and tasa_base > 0) else None
    diagonal = ((1 - deteccion) + alarmas / ventanas) if deteccion is not None else None
    total_sev = sev_fallo + sev_falso_positivo
    return VeredictosResult(
        ventanas=ventanas,
        con_evento=con_evento,
        alarmas=alarmas,
        detectados=detectados,
        fallos=fallos,
        falsos_positivos=falsos_pos,
        tasa_base=tasa_base,
        precision=precision,
        tau=alarmas / ventanas,
        deteccion=deteccion,
        ganancia=round(ganancia, 3) if ganancia is not None else None,
        diagonal=round(diagonal, 4) if diagonal is not None else None,
        asertividad=aciertos / ventanas,
        asertividad_muda=(ventanas - con_evento) / ventanas,
        coste_sistema=fallos * sev_fallo + falsos_pos * sev_falso_positivo,
        coste_mudo=con_evento * sev_fallo,
        coste_alarmista=(ventanas - con_evento) * sev_falso_positivo,
        umbral_rentable=(sev_falso_positivo / total_sev) if total_sev > 0 else 0.0,
    )
