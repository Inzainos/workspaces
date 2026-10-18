"""
Alfa-2 Agent — Satellite Anomaly Detection (thermal precedent + GOES X-ray)
===========================================================================
Role: Senior Satellite Analyst — ESA Sentinel coverage/thermal + GOES X-ray.
Mission: Detect satellite-observable anomalies using ONLY measured history:
         per-zone thermal PRECEDENT (vs its own historic max) and NOAA
         flare classes. NO live training, NO online learning.

Decision logic (calibrated 2026-10-18 against tbl_cobertura_satelital_*):
  - The old z-score over thermal was the WRONG INSTRUMENT: the historic
    distribution is zero-inflated (nodo040: 58% of hours nonzero, live p99
    == historic p99), so a ROUTINE value scored 3σ+ and alfa2 emitted
    ALERT in 168/168 live cycles (measured in TBL_JUEZ_AUDITORIA).
  - Thermal now uses PRECEDENT per zone: `thermal > max_propio_historico`.
    Measured: fires in 2/15 live hour-blocks (13%) with >=1 zone, and
    multi-zone (>=3, spatially coherent) in 1/15 — discriminating triggers.
  - X-ray (GOES, integrated 2026-10-18 by operator decision — was jupiter's):
    NOAA flare classes are the physical threshold, not an invented number.
    X-class (>=1e-4 W/m²) -> ALERT; M-class (>=1e-5) -> WATCH.
"""

from typing import Any, Dict, List, Optional
import sqlite3
import statistics
import numpy as np
from pathlib import Path
from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType

# Umbrales físicos NOAA de clase de fulguración (W/m², banda 0.1-0.8 nm).
XRAY_CLASE_M = 1e-5
XRAY_CLASE_X = 1e-4

# Cuántas zonas sin precedente térmico simultáneas hacen ALERT (coherencia
# espacial: un precursor real es regional, no un nodo suelto). Con >=1 es
# WATCH. Medido sobre las horas vivas: 1/15 bloques cruza el >=3.
THERMAL_ALERT_ZONAS = 3


class Alfa2Agent(BaseAgent):
    """
    Alfa-2 operates in PURE INFERENCE MODE against measured baselines.
    The baseline (obs/clarity mean+std and per-zone thermal HISTORIC MAX)
    is computed fresh from tbl_cobertura_satelital_historico at init.

    2026-10-18: the precomputed JSON path was REMOVED. The September file
    carried thermal_std=0.0 (historic was all zeros then) and shadowed the
    fresh DB computation forever — the root cause of ALERT 168/168. One
    source of truth, always current: the DB.
    """

    def __init__(self):
        super().__init__(name="alfa2", layer="geodynamic")
        self._cobertura_data: Optional[Dict[str, Any]] = None
        self._xray_max: Optional[float] = None
        self._xray_mean: Optional[float] = None
        self._baseline_stats: Optional[Dict[str, Dict[str, float]]] = None
        self._baseline_stats = self._baseline_desde_db() or self._default_baseline()

    def _baseline_desde_db(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Mean/std per zone (obs, clarity) + per-zone thermal HISTORIC MAX
        from tbl_cobertura_satelital_historico. Thermal max is the precedent
        bar: a live value above it is unprecedented for that zone."""
        db = Path(__file__).resolve().parents[3] / "data" / "SENTINEL_OMEGA_PRO.db"
        if not db.exists():
            return None
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            filas = con.execute(
                "SELECT zona, thermal_anomalies, clear_passes, total_passes "
                "FROM tbl_cobertura_satelital_historico WHERE total_passes > 0"
            ).fetchall()
            con.close()
        except Exception as exc:
            self.logger.warning("Alfa-2: no se pudo leer el histórico: %s", exc)
            return None

        acum: Dict[str, Dict[str, list]] = {}
        for zona, thermal, clear, total in filas:
            z = str(zona).lower()
            clarity = (clear or 0) / total
            obs = total * (0.5 + 0.5 * clarity)
            d = acum.setdefault(z, {"obs": [], "th": [], "cl": []})
            d["obs"].append(obs)
            d["th"].append(float(thermal or 0))
            d["cl"].append(clarity)

        out: Dict[str, Dict[str, float]] = {}
        for z, d in acum.items():
            if len(d["obs"]) < 30:      # muestra insuficiente para un baseline
                continue
            out[z] = {
                "obs_mean": statistics.fmean(d["obs"]),
                "obs_std": statistics.pstdev(d["obs"]) if len(d["obs"]) > 1 else 0.0,
                "clarity_mean": statistics.fmean(d["cl"]),
                "clarity_std": statistics.pstdev(d["cl"]) if len(d["cl"]) > 1 else 0.0,
                # La barra de precedente térmico: NADA de z-scores sobre la
                # distribución inflada en ceros (medido: daba 3σ a la p99
                # rutinaria de la propia zona). Máximo histórico, y listo.
                "thermal_max": float(max(d["th"])) if d["th"] else 0.0,
            }
        return out or None

    @staticmethod
    def _z(valor: float, mean: float, std: float, tope: float = 6.0) -> float:
        """z-score acotado para obs/clarity (distribuciones con varianza real).
        Sin varianza medida, la desviación es significativa pero su magnitud
        NO es medible: se reporta 2.5σ (WATCH), nunca el 3.0 exacto que
        colisionaba con la compuerta de ALERT."""
        if std <= 1e-9:
            return 0.0 if abs(valor - mean) <= 1e-9 else 2.5
        return max(-tope, min(tope, (valor - mean) / std))

    def _default_baseline(self) -> Dict[str, Dict[str, float]]:
        """Fallback defaults if no DB history at all (fresh installs)."""
        return {
            "mexico": {"obs_mean": 2.5, "obs_std": 1.2, "clarity_mean": 0.65, "clarity_std": 0.15, "thermal_max": 0.0},
            "peru": {"obs_mean": 3.1, "obs_std": 1.5, "clarity_mean": 0.72, "clarity_std": 0.12, "thermal_max": 0.0},
            "chile": {"obs_mean": 2.8, "obs_std": 1.3, "clarity_mean": 0.68, "clarity_std": 0.14, "thermal_max": 0.0},
        }

    def ingest(self, data: Dict[str, Any]) -> None:
        # El pipeline entrega "zone_coverages"; este agente leía solo
        # "cobertura_satelital" y el .get(k, {}) devolvía {} en silencio, así
        # que analyze() caía siempre en NO_SIGNAL 0.0 pese a haber cobertura
        # real en la DB. Los tests no lo detectaban porque llaman a ingest()
        # con la clave del agente, nunca con la del pipeline.
        # Se mantiene el fallback a "cobertura_satelital" porque los tests
        # (test_pipeline.py) y el pipeline legacy usan esa clave.
        self._cobertura_data = (
            data.get("zone_coverages")
            or data.get("cobertura_satelital")
            or {}
        )
        # GOES X-ray (integrado 2026-10-18; era de jupiter). Dos formatos:
        # el df crudo del pipeline (columna `flux`, con time_tag/energy) o
        # el agregado de tbl_xray_vivo (flux_max/flux_avg). None sin dato
        # (regla 7: faltante no dispara).
        xray_df = data.get("xray_df")
        self._xray_max = None
        self._xray_mean = None
        if xray_df is not None and len(xray_df):
            try:
                import pandas as pd
                if "flux" in xray_df.columns:
                    serie = pd.to_numeric(xray_df["flux"], errors="coerce").dropna()
                    if len(serie):
                        self._xray_max = float(serie.max())
                        self._xray_mean = float(serie.mean())
                if "flux_max" in xray_df.columns:
                    serie = pd.to_numeric(xray_df["flux_max"], errors="coerce").dropna()
                    if len(serie):
                        self._xray_max = float(serie.max())
                if "flux_avg" in xray_df.columns:
                    serie = pd.to_numeric(xray_df["flux_avg"], errors="coerce").dropna()
                    if len(serie):
                        self._xray_mean = float(serie.mean())
            except Exception as exc:
                self.logger.warning("Alfa-2: xray_df ilegible: %s", exc)
        n = len(self._cobertura_data)
        xr = f", xray_max={self._xray_max:.2e}" if self._xray_max is not None else ""
        self.logger.info(f"Alfa-2 (Satellite) ingested: {n} zone records{xr}")

    def _zonas_sin_precedente(self) -> List[Dict[str, Any]]:
        """Zonas cuyo térmico vivo EXCEDE el máximo de su propio histórico.
        Esa es la señal: actividad que esa zona nunca ha mostrado."""
        sin_precedente = []
        for zona, zone_data in (self._cobertura_data or {}).items():
            stats = self._baseline_stats.get(zona.lower())
            if not stats:
                continue
            thermal = zone_data.get("thermal_anomalies", 0) or 0
            if thermal > stats.get("thermal_max", 0.0):
                sin_precedente.append({
                    "zona": zona,
                    "thermal": thermal,
                    "max_historico": stats.get("thermal_max", 0.0),
                })
        return sin_precedente

    def _cobertura_degradada(self) -> List[str]:
        """Zonas con obs/clarity muy por DEBAJO de su baseline: es nubosidad
        o menos pases del satélite — problema de observación, no precursor.
        Se informa, no altera la señal."""
        degradadas = []
        for zona, zone_data in (self._cobertura_data or {}).items():
            stats = self._baseline_stats.get(zona.lower())
            if not stats:
                continue
            total = zone_data.get("total_passes", 0) or 0
            clear = zone_data.get("clear_passes", 0) or 0
            clarity = clear / total if total > 0 else 0.0
            obs = total * (0.5 + 0.5 * clarity)
            z_obs = self._z(obs, stats["obs_mean"], stats["obs_std"])
            z_cl = self._z(clarity, stats["clarity_mean"], stats["clarity_std"])
            if z_obs <= -2.0 or z_cl <= -2.0:
                degradadas.append(zona)
        return degradadas

    def analyze(self) -> AgentSignal:
        if not self._cobertura_data and self._xray_max is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0, reasoning="No satellite coverage / xray data")

        sin_precedente = self._zonas_sin_precedente()
        degradadas = self._cobertura_degradada()
        if degradadas:
            self.logger.info(
                "Alfa-2: cobertura degradada en %s (no eleva la señal)",
                ", ".join(degradadas),
            )

        signal_data = {
            "zonas_sin_precedente": sin_precedente,
            "n_sin_precedente": len(sin_precedente),
            "zonas_analizadas": len(self._cobertura_data or {}),
            "xray_max": self._xray_max,
            "xray_mean": self._xray_mean,
            "cobertura_degradada": degradadas,
            "baseline_source": "db_fresh",
        }

        # --- X-ray (NOAA flare classes: umbrales físicos) ---
        if self._xray_max is not None and self._xray_max >= XRAY_CLASE_X:
            return self.emit_signal(
                SignalType.ALERT,
                min(0.9, 0.65 + 0.1),
                data=signal_data,
                reasoning=f"X-class solar flare: GOES flux_max={self._xray_max:.2e} W/m² (≥{XRAY_CLASE_X:.0e})",
            )
        if self._xray_max is not None and self._xray_max >= XRAY_CLASE_M:
            flare = "M-class solar flare" if self._xray_max < XRAY_CLASE_X else "X-class"
            return self.emit_signal(
                SignalType.WATCH,
                0.5,
                data=signal_data,
                reasoning=f"{flare}: GOES flux_max={self._xray_max:.2e} W/m²",
            )

        # --- Térmico por PRECEDENTE de zona (nunca z-score inflado en ceros) ---
        if len(sin_precedente) >= THERMAL_ALERT_ZONAS:
            zonas = ", ".join(f"{s['zona']}={s['thermal']} (>máx {s['max_historico']:.0f})" for s in sin_precedente[:4])
            return self.emit_signal(
                SignalType.ALERT,
                0.75,
                data=signal_data,
                reasoning=f"{len(sin_precedente)} zonas con térmico SIN PRECEDENTE ({zonas})",
            )
        if sin_precedente:
            s = sin_precedente[0]
            return self.emit_signal(
                SignalType.WATCH,
                0.45,
                data=signal_data,
                reasoning=f"Térmico sin precedente en {s['zona']}: {s['thermal']} > máx histórico {s['max_historico']:.0f}",
            )

        return self.emit_signal(
            SignalType.NEUTRAL,
            0.2,
            data=signal_data,
            reasoning="Térmico dentro del rango histórico de cada zona; sin fulguración M/X",
        )

    def health_check(self) -> bool:
        return self._baseline_stats is not None and len(self._baseline_stats) > 0
