"""
Alfa-2 Agent — Satellite Thermal Anomaly Detection (self-learning baseline)
===========================================================================
Source: ESA Sentinel-2/-1 via EODAG (Copernicus Data Space); thermal index per
seismic zone. Role: real-time cortical-stress indicator from satellite thermal
observation.

Like Beta-2 (which subtracts a learned natural degassing background and measures
the EXCESS), Alfa-2 **learns its own per-zone baseline** and scores each new
observation as a deviation from that baseline — instead of thresholding raw
coverage counts. This makes Alfa-2 a genuine sensor with its own patterns rather
than a coverage meter, so it stops being a "dead eye" in the 6-agent consensus.

Mechanism:
  * Per zone, an online mean/variance (Welford) is maintained over the zone's
    thermal-observation index across cycles — the learned baseline.
  * Each cycle the current observation is scored as Z = (x - mean) / std.
    |Z| >= Z_ALERT  -> ALERT ;  |Z| >= Z_WATCH -> WATCH ; otherwise NEUTRAL.
  * The baseline is updated after scoring, and (optionally) persisted to disk
    (SNT_STATE_DIR) so the learned patterns accumulate across runs.

Regla de honestidad proxy-of-proxy (v2.5.1):
  El conteo `thermal_anomaly_count` llega de fuera y el pipeline actual lo
  entrega en 0: sin una medición térmica real detrás (`lst_c`, Land Surface
  Temperature — global o por zona), ese conteo NO alcanza para ALERT: se
  degrada a WATCH y el reasoning lo dice. El baseline auto-aprendido sí
  puede escalar a ALERT por desviación (>= Z_ALERT σ) porque compara la
  zona contra SU PROPIA historia observada — deviación medida, no conteo
  sin respaldo. `_observation_index` prefiere `lst_c` real cuando existe.
"""

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Alfa2Agent(BaseAgent):

    MIN_PASSES_FOR_SIGNAL = 3
    HIGH_COVERAGE_THRESHOLD = 8
    LOW_CLOUD_THRESHOLD = 20.0

    # Self-learning baseline
    MIN_HISTORY = 5          # cycles needed before a zone can be scored
    Z_WATCH = 1.5
    Z_ALERT = 2.5

    def __init__(self, state_path: Optional[str] = None):
        super().__init__(name="alfa2", layer="geodynamic")
        self._zone_coverages: Dict[str, Dict[str, Any]] = {}
        self._thermal_anomaly_count: int = 0
        self._lst_c = None   # LST medida (°C); None = sin térmico real global
        # learned baseline: zone -> {"n": int, "mean": float, "M2": float}
        self._baselines: Dict[str, Dict[str, float]] = {}
        self._state_path = self._resolve_state_path(state_path)
        self._load_baselines()

    # ── baseline persistence ─────────────────────────────────────────────
    @staticmethod
    def _resolve_state_path(explicit: Optional[str]) -> Optional[Path]:
        if explicit is not None:
            return Path(explicit)
        env = os.getenv("SNT_STATE_DIR")
        if env:
            return Path(env) / "alfa2_baseline.json"
        return None  # in-memory only (per process)

    def _load_baselines(self) -> None:
        if self._state_path and self._state_path.exists():
            try:
                self._baselines = json.loads(self._state_path.read_text())
                self.logger.info(
                    f"Loaded learned baseline for {len(self._baselines)} zones"
                )
            except (OSError, ValueError) as exc:
                self.logger.warning(f"Could not load Alfa-2 baseline: {exc}")

    def _save_baselines(self) -> None:
        if not self._state_path:
            return
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(self._baselines))
        except OSError as exc:
            self.logger.warning(f"Could not persist Alfa-2 baseline: {exc}")

    # ── online mean/variance (Welford) ───────────────────────────────────
    def _zscore(self, zone: str, x: float) -> Optional[float]:
        """Deviation of x from the zone's learned baseline (None while learning)."""
        b = self._baselines.get(zone)
        if not b or b["n"] < self.MIN_HISTORY:
            return None
        var = b["M2"] / b["n"]
        std = math.sqrt(var)
        if std <= 1e-9:
            return 0.0
        return (x - b["mean"]) / std

    def _update_baseline(self, zone: str, x: float) -> None:
        b = self._baselines.setdefault(zone, {"n": 0, "mean": 0.0, "M2": 0.0})
        b["n"] += 1
        delta = x - b["mean"]
        b["mean"] += delta / b["n"]
        b["M2"] += delta * (x - b["mean"])

    @staticmethod
    def _observation_index(cov: Dict[str, Any]) -> float:
        """
        Per-zone scalar the baseline is learned over. Prefers a real thermal
        value if the pipeline provides one (`lst_c` land-surface temperature or
        `thermal_index`); otherwise falls back to a clarity-weighted coverage
        density so the agent still learns a stable per-zone pattern.
        """
        if cov.get("lst_c") is not None:
            return float(cov["lst_c"])
        if cov.get("thermal_index") is not None:
            return float(cov["thermal_index"])
        total = cov.get("total_passes", cov.get("s2_count", 0) + cov.get("s1_count", 0))
        clouds = cov.get("s2_cloud_covers", [])
        clear = sum(1 for c in clouds if c < Alfa2Agent.LOW_CLOUD_THRESHOLD)
        clarity = clear / max(len(clouds), 1)
        return float(total) * (0.5 + 0.5 * clarity)

    # ── agent interface ──────────────────────────────────────────────────
    def ingest(self, data: Dict[str, Any]) -> None:
        self._zone_coverages = data.get("zone_coverages", {})
        self._thermal_anomaly_count = data.get("thermal_anomaly_count", 0)
        self._lst_c = data.get("lst_c")
        self.logger.info(
            f"Ingested satellite data for {len(self._zone_coverages)} zones"
        )

    def analyze(self) -> AgentSignal:
        if not self._zone_coverages:
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                reasoning="No satellite coverage data available",
            )

        zone_scores: Dict[str, Dict[str, Any]] = {}
        anomalies: Dict[str, float] = {}
        learning_zones = 0

        for zone, cov in self._zone_coverages.items():
            total = cov.get("total_passes", cov.get("s2_count", 0) + cov.get("s1_count", 0))
            cloud_covers = cov.get("s2_cloud_covers", [])
            clear_passes = sum(1 for cc in cloud_covers if cc < self.LOW_CLOUD_THRESHOLD)

            obs = self._observation_index(cov)
            z = self._zscore(zone, obs)          # deviation vs learned baseline
            self._update_baseline(zone, obs)     # then learn from it
            if z is None:
                learning_zones += 1
            else:
                anomalies[zone] = z

            zone_scores[zone] = {
                "observation_index": round(obs, 3),
                "z_score": round(z, 3) if z is not None else None,
                "baseline_n": self._baselines[zone]["n"],
                "total_passes": total,
                "clear_passes": clear_passes,
            }

        self._save_baselines()

        max_abs_z = max((abs(v) for v in anomalies.values()), default=0.0)
        worst_zone = max(anomalies, key=lambda k: abs(anomalies[k])) if anomalies else None
        tiene_lst = bool(self._lst_c) or any(
            cov.get("lst_c") is not None for cov in self._zone_coverages.values()
        )
        base_data = {
            "zone_scores": zone_scores,
            "thermal_anomalies": self._thermal_anomaly_count,
            "max_abs_z": float(max_abs_z),
            "worst_zone": worst_zone,
            "learning_zones": learning_zones,
            "lst_medida": tiene_lst,
        }

        # 1) Conteo térmico explícito: ALERT solo con LST medida detrás;
        #    sin lst_c es proxy-of-proxy y se degrada a WATCH (honestidad).
        if self._thermal_anomaly_count > 2:
            if tiene_lst:
                return self.emit_signal(
                    SignalType.ALERT,
                    min(0.6 + self._thermal_anomaly_count * 0.05, 0.9),
                    data=base_data,
                    reasoning=(
                        f"{self._thermal_anomaly_count} thermal anomalies backed "
                        f"by measured LST across satellite coverage"
                    ),
                )
            return self.emit_signal(
                SignalType.WATCH, 0.5,
                data=base_data,
                reasoning=(
                    f"{self._thermal_anomaly_count} thermal anomalies reported but "
                    f"NO measured LST backing them (proxy-of-proxy) — degraded to WATCH"
                ),
            )

        # 2) Learned-baseline deviation.
        if max_abs_z >= self.Z_ALERT:
            return self.emit_signal(
                SignalType.ALERT, min(0.6 + (max_abs_z - self.Z_ALERT) * 0.1, 0.9),
                data=base_data,
                reasoning=(
                    f"Thermal index at {worst_zone} deviates {max_abs_z:.1f}σ from "
                    f"its learned baseline"
                ),
            )
        if max_abs_z >= self.Z_WATCH:
            return self.emit_signal(
                SignalType.WATCH, 0.4 + (max_abs_z - self.Z_WATCH) * 0.1,
                data=base_data,
                reasoning=(
                    f"Thermal index at {worst_zone} elevated ({max_abs_z:.1f}σ) vs "
                    f"learned baseline"
                ),
            )

        # 3) Still learning (not enough history yet) vs. within-baseline.
        if learning_zones == len(self._zone_coverages):
            return self.emit_signal(
                SignalType.NEUTRAL, 0.3,
                data=base_data,
                reasoning=(
                    f"Learning per-zone baseline ({learning_zones} zones, "
                    f"need {self.MIN_HISTORY} cycles each)"
                ),
            )
        return self.emit_signal(
            SignalType.NEUTRAL, 0.2,
            data=base_data,
            reasoning=f"Thermal indices within learned baseline (max {max_abs_z:.1f}σ)",
        )

    def health_check(self) -> bool:
        return len(self._zone_coverages) > 0
