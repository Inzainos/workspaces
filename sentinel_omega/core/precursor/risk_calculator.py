"""
Precursor Risk Calculator — TITAN V32 Lineage

Core formula from legacy TITAN V32 (TOMSK WPC):
    fantasma = (viento * 0.02) + (abs(bz) ** 2) + (sch_wpc * 1.5)

Extended with:
    - Atmospheric pressure modifier (V32 Blue Jets correlation)
    - Kp storm-level escalation
    - LOD anomaly coupling

Variables:
    bz       — IMF Bz component (nT), southward = negative = geomagnetically active
    viento   — Solar wind proton speed (km/s)
    sch_wpc  — Schumann resonance WPC excitation (fraction, 0-1 range)
    pressure — Mean atmospheric pressure (hPa) at monitoring stations
    kp       — Planetary magnetic index (0-9)
    lod_ms   — Length-of-Day anomaly (ms)

Output: PrecursorRisk dataclass with composite risk score and component breakdown.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PrecursorRisk:
    timestamp: float
    fantasma: float
    risk_level: str
    bz_contribution: float
    wind_contribution: float
    schumann_contribution: float
    pressure_modifier: float
    kp_modifier: float
    lod_modifier: float
    components: Dict[str, float] = field(default_factory=dict)
    # Diagnósticos añadidos el 2026-09-25 al auditar el índice. No cambian el
    # `fantasma` heredado --- eso rompería la comparación con 3.261 ciclos de
    # historia --- pero dejan ver de qué está hecho el número.
    bz_es_norte: bool = False        # Bz positivo = orientación TRANQUILA
    fantasma_solo_sur: float = 0.0   # el mismo índice contando solo Bz sur

    @property
    def is_elevated(self) -> bool:
        return self.risk_level in ("HIGH", "CRITICAL")


# Los de siempre, heredados de TITAN V32. Se conservan para poder releer los
# 3.261 ciclos de historia con la vara con la que se escribieron.
RISK_THRESHOLDS_V32 = {
    "LOW": 0.0,
    "MODERATE": 5.0,
    "HIGH": 15.0,
    "CRITICAL": 30.0,
}

# Recalibrados el 2026-09-25 sobre 280.942 lecturas horarias reales. Los de V32
# no separaban nada:
#
#   umbral    repartía                      M7+ en 72 h
#   VERDE     6 horas de 280.942 (0,00 %)   ---
#   AMARILLO  69,8 %                        10,87 %
#   NARANJA   21,0 %                        11,27 %
#   ROJO       9,2 %                        11,80 %
#
# VERDE era inalcanzable porque el viento solar solo ya aporta 8-10 y el umbral
# era 5. Y la escala completa separaba 0,93 puntos de riesgo: los cuatro colores
# decían lo mismo. Puestos en los percentiles 50/90/98 de la propia
# distribución:
#
#   VERDE     50,0 %   10,71 %
#   AMARILLO  40,0 %   11,27 %
#   NARANJA    8,0 %   11,43 %
#   ROJO       2,0 %   13,08 %   <- 1,22x la tasa del VERDE
#
# Sigue siendo una discriminación DÉBIL --- 2,4 puntos de separación --- y hay
# que leerla así. Pero al menos los colores reparten y el extremo dice algo.
# El índice NO cambia de valor, así que la historia sigue comparable; lo que
# cambia es dónde se ponen las rayas.
RISK_THRESHOLDS = {
    "LOW": 0.0,
    "MODERATE": 11.5,   # percentil 50
    "HIGH": 28.6,       # percentil 90
    "CRITICAL": 77.7,   # percentil 98
}


def classify_risk(fantasma: float) -> str:
    if fantasma >= RISK_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif fantasma >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif fantasma >= RISK_THRESHOLDS["MODERATE"]:
        return "MODERATE"
    return "LOW"


def compute_fantasma(
    bz: float,
    viento: float,
    sch_wpc: float,
    pressure_hpa: float = 1013.0,
    kp: float = 0.0,
    lod_ms: float = 0.0,
) -> PrecursorRisk:
    """
    Compute precursor risk using the TITAN V32 fantasma formula.

    Core: fantasma = (viento * 0.02) + (abs(bz) ** 2) + (sch_wpc * 1.5)

    Modifiers applied post-core:
    - Low pressure (<1008 hPa) adds up to 3.0
    - Kp >= 5 (storm level) multiplies by up to 1.5×
    - LOD anomaly (>0.5 ms) adds coupling factor
    """
    # Sobre `abs(bz) ** 2`, que parece un error y NO lo es --- esto costó una
    # medición y merece quedar escrito.
    #
    # La fórmula es simétrica: +10 nT (norte) puntúa igual que -10 (sur), y el
    # encabezado de este módulo dice «southward = negative = geomagnetically
    # active». Parecía un error de signo: el Bz norte no activa el acoplamiento
    # con la magnetosfera, lo suprime.
    #
    # Se probó la versión «corregida» --- min(bz,0)², solo sur --- contra 32
    # años de sismos y 280.942 horas de clima espacial, midiendo qué fracción
    # del 1 % de horas más altas precede a un evento:
    #
    #        objetivo          simétrica |Bz|²   solo sur min(bz,0)²
    #        M7,0+ en 72 h         1,32x               1,13x
    #        M7,0+ en 24 h         1,42x               1,09x
    #        M6,5+ en 24 h         1,26x               1,19x
    #        M7,5+ en 72 h         0,90x               1,20x
    #
    # **La simétrica gana** donde más importa. La lectura razonable: |Bz| grande
    # mide CAMPO PERTURBADO en cualquier dirección --- la envoltura de una
    # eyección solar trae Bz grande y fluctuante --- y eso lleva más información
    # que el signo. Así que se queda como está, ahora por medición y no por
    # herencia. `fantasma_solo_sur` se conserva como diagnóstico, no como la
    # versión buena: los datos la rechazan.
    bz_contribution = abs(bz) ** 2
    wind_contribution = viento * 0.02
    schumann_contribution = sch_wpc * 1.5

    fantasma = bz_contribution + wind_contribution + schumann_contribution
    bz_es_norte = bz > 0
    # El mismo índice si el Bz norte no contara: min(bz, 0)² deja fuera lo que
    # no acopla.
    fantasma_solo_sur = (min(bz, 0.0) ** 2) + wind_contribution + schumann_contribution

    pressure_modifier = 0.0
    if pressure_hpa < 1008.0:
        pressure_modifier = min(3.0, (1008.0 - pressure_hpa) / 5.0)
        fantasma += pressure_modifier

    kp_modifier = 1.0
    if kp >= 5.0:
        kp_modifier = 1.0 + (kp - 5.0) * 0.1
        fantasma *= kp_modifier

    lod_modifier = 0.0
    if abs(lod_ms) > 0.5:
        lod_modifier = min(2.0, abs(lod_ms) * 0.5)
        fantasma += lod_modifier

    risk_level = classify_risk(fantasma)

    return PrecursorRisk(
        timestamp=time.time(),
        fantasma=fantasma,
        risk_level=risk_level,
        bz_contribution=bz_contribution,
        wind_contribution=wind_contribution,
        schumann_contribution=schumann_contribution,
        pressure_modifier=pressure_modifier,
        kp_modifier=kp_modifier,
        lod_modifier=lod_modifier,
        bz_es_norte=bz_es_norte,
        fantasma_solo_sur=round(fantasma_solo_sur, 3),
        components={
            "bz_nT": bz,
            "wind_kms": viento,
            "schumann_wpc": sch_wpc,
            "pressure_hpa": pressure_hpa,
            "kp": kp,
            "lod_ms": lod_ms,
        },
    )


def compute_risk_from_signals(
    agent_signals: List[Dict[str, Any]],
    atmospheric: Optional[Dict[str, Any]] = None,
) -> PrecursorRisk:
    """
    Extract variables from agent signal data dicts and compute fantasma.
    Used by the orchestrator to compute precursor risk from a completed cycle.
    """
    bz = 0.0
    viento = 0.0
    sch_wpc = 0.0
    kp = 0.0
    lod_ms = 0.0
    pressure_hpa = 1013.0

    for sig in agent_signals:
        data = sig if isinstance(sig, dict) else getattr(sig, "data", {})

        if "bz_mean" in data:
            bz = data["bz_mean"]
        if "plasma_speed" in data:
            viento = data["plasma_speed"]
        if "schumann_activity_pct" in data:
            sch_wpc = data["schumann_activity_pct"] / 100.0
        if "kp_mean" in data:
            kp = data["kp_mean"]
        if "lod_anomaly_ms" in data:
            lod_ms = data["lod_anomaly_ms"]

    if atmospheric:
        pressure_hpa = atmospheric.get("mean_pressure", 1013.0)

    return compute_fantasma(
        bz=bz, viento=viento, sch_wpc=sch_wpc,
        pressure_hpa=pressure_hpa, kp=kp, lod_ms=lod_ms,
    )


def format_risk_report(risk: PrecursorRisk) -> str:
    """Format risk for Telegram alert dispatch."""
    lines = [
        f"<b>PRECURSOR RISK: {risk.risk_level}</b>",
        f"Fantasma Index: <code>{risk.fantasma:.2f}</code>",
        "",
        "<b>Components:</b>",
        f"  Bz² = <code>{risk.bz_contribution:.2f}</code> (Bz={risk.components.get('bz_nT', 0):.1f} nT)",
        f"  Wind = <code>{risk.wind_contribution:.2f}</code> ({risk.components.get('wind_kms', 0):.0f} km/s)",
        f"  Schumann = <code>{risk.schumann_contribution:.2f}</code>",
        "",
        "<b>Modifiers:</b>",
        f"  Pressure = <code>+{risk.pressure_modifier:.2f}</code> ({risk.components.get('pressure_hpa', 1013):.0f} hPa)",
        f"  Kp = <code>×{risk.kp_modifier:.2f}</code> (Kp={risk.components.get('kp', 0):.1f})",
        f"  LOD = <code>+{risk.lod_modifier:.2f}</code> ({risk.components.get('lod_ms', 0):.2f} ms)",
    ]
    return "\n".join(lines)
