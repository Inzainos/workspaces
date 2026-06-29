"""
Beta-2 Agent — Atmospheric Chemistry & Weather Anomaly Detection
Sources: OpenWeatherMap (pressure, temp, humidity, SO2, air quality)
Variables: Pressure gradient, SO2 levels, air quality index, fog/visibility
Training window: 16 years (satellite-era atmospheric records)
Reports to: Beta-1 (who validates against 30-year history)
"""

from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Beta2Agent(BaseAgent):

    LOW_PRESSURE_THRESHOLD = 1008.0
    HIGH_SO2_THRESHOLD = 20.0
    FOG_VISIBILITY_THRESHOLD = 1000
    TRAINING_YEARS = 16

    def __init__(self):
        super().__init__(name="beta2", layer="geodynamic")
        self._pressure_gradient: Optional[Dict[str, Any]] = None
        self._air_quality: Optional[Dict[str, float]] = None
        self._atmospheric_readings: List[Dict[str, Any]] = []

    def ingest(self, data: Dict[str, Any]) -> None:
        self._pressure_gradient = data.get("pressure_gradient")
        self._air_quality = data.get("air_quality")
        self._atmospheric_readings = data.get("atmospheric_readings", [])
        n_stations = len(self._atmospheric_readings)
        self.logger.info(f"Beta-2 ingested: {n_stations} stations, AQ={'yes' if self._air_quality else 'no'}")

    def _pressure_stress(self) -> float:
        if not self._pressure_gradient:
            return 0.0
        stress = 0.0
        mean_p = self._pressure_gradient.get("mean_pressure", 1013.0)
        if mean_p < self.LOW_PRESSURE_THRESHOLD:
            stress += (self.LOW_PRESSURE_THRESHOLD - mean_p) / 20.0
        spread = self._pressure_gradient.get("pressure_spread", 0.0)
        if spread > 10.0:
            stress += spread / 50.0
        return min(1.0, stress)

    def _chemical_stress(self) -> float:
        if not self._air_quality:
            return 0.0
        stress = 0.0
        so2 = self._air_quality.get("so2", 0.0)
        if so2 > self.HIGH_SO2_THRESHOLD:
            stress += min(0.4, so2 / 100.0)
        pm25 = self._air_quality.get("pm2_5", 0.0)
        if pm25 > 35.0:
            stress += min(0.2, pm25 / 200.0)
        co = self._air_quality.get("co", 0.0)
        if co > 400.0:
            stress += min(0.2, co / 2000.0)
        return min(1.0, stress)

    def _fog_anomaly(self) -> bool:
        for reading in self._atmospheric_readings:
            vis = reading.get("visibility_m", 10000)
            if vis < self.FOG_VISIBILITY_THRESHOLD:
                return True
        return False

    def analyze(self) -> AgentSignal:
        if not self._pressure_gradient and not self._air_quality:
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                reasoning="No atmospheric data available",
            )

        pressure_score = self._pressure_stress()
        chemical_score = self._chemical_stress()
        fog_detected = self._fog_anomaly()

        combined = pressure_score * 0.4 + chemical_score * 0.4
        if fog_detected:
            combined += 0.2

        signal_data = {
            "pressure_stress": pressure_score,
            "chemical_stress": chemical_score,
            "fog_detected": fog_detected,
            "combined_atmospheric": combined,
        }

        if self._pressure_gradient:
            signal_data["mean_pressure"] = self._pressure_gradient.get("mean_pressure", 1013.0)
        if self._air_quality:
            signal_data["so2"] = self._air_quality.get("so2", 0.0)
            signal_data["aqi"] = self._air_quality.get("aqi", 0)

        if combined > 0.6:
            reasons = []
            if pressure_score > 0.3:
                reasons.append(f"pressure anomaly ({pressure_score:.2f})")
            if chemical_score > 0.3:
                reasons.append(f"chemical anomaly ({chemical_score:.2f})")
            if fog_detected:
                reasons.append("fog/low visibility")
            return self.emit_signal(
                SignalType.ALERT,
                min(0.6 + combined * 0.3, 0.95),
                data=signal_data,
                reasoning=f"Atmospheric stress: {', '.join(reasons)}",
            )

        if combined > 0.3:
            return self.emit_signal(
                SignalType.WATCH, 0.4 + combined * 0.2,
                data=signal_data,
                reasoning=f"Moderate atmospheric anomaly (score={combined:.2f})",
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.2,
            data=signal_data,
            reasoning="Atmosphere within normal bounds",
        )

    def health_check(self) -> bool:
        return self._pressure_gradient is not None or self._air_quality is not None
