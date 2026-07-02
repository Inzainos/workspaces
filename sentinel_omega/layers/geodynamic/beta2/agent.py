"""
Beta-2 Agent — Atmospheric Chemistry & Degassing Anomaly Detection
Sources: OpenWeatherMap (pressure, SO2/CO/NO2 gases, air quality)
Variables: Pressure gradient, tectonic degassing signature, fog/visibility
Training window: 16 years (satellite-era atmospheric records)
Reports to: Beta-1 (who validates against 30-year history)

The precursor here is DEGASSING (gases venting from the ground before an event),
not temperature. Tectonic/volcanic outgassing is separated from urban pollution
by (1) subtracting the natural background learned from remote clean zones and
(2) the SO2/NO2 ratio — real degassing raises SO2 without raising NO2.
"""

from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Beta2Agent(BaseAgent):

    LOW_PRESSURE_THRESHOLD = 1008.0
    HIGH_SO2_THRESHOLD = 20.0
    FOG_VISIBILITY_THRESHOLD = 1000
    TRAINING_YEARS = 16

    MARINE_THERMAL_THRESHOLD_C = 29.0
    NODE_SO2_EXCESS_ALERT = 50.0
    NODE_CO_ALERT = 400.0

    def __init__(self):
        super().__init__(name="beta2", layer="geodynamic")
        self._pressure_gradient: Optional[Dict[str, Any]] = None
        self._air_quality: Optional[Dict[str, float]] = None
        self._atmospheric_readings: List[Dict[str, Any]] = []
        self._degassing_baseline: Optional[Dict[str, float]] = None
        self._global_node_scan: List[Dict[str, Any]] = []

    def ingest(self, data: Dict[str, Any]) -> None:
        self._pressure_gradient = data.get("pressure_gradient")
        self._air_quality = data.get("air_quality")
        self._atmospheric_readings = data.get("atmospheric_readings", [])
        self._degassing_baseline = data.get("degassing_baseline")
        self._global_node_scan = data.get("global_node_scan", [])
        n_stations = len(self._atmospheric_readings)
        self.logger.info(
            f"Beta-2 ingested: {n_stations} stations, "
            f"AQ={'yes' if self._air_quality else 'no'}, "
            f"baseline={'yes' if self._degassing_baseline else 'no'}, "
            f"global_nodes={len(self._global_node_scan)}"
        )

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

    def _degassing_signature(self) -> Dict[str, float]:
        """
        Isolate tectonic/volcanic outgassing from urban pollution.

        Two-step separation:
          1. Subtract the natural background learned from remote clean zones
             (open ocean, desert, poles) — this is the SO2/CO the planet
             degasses with zero human input. What remains is the EXCESS.
          2. Weight the SO2 excess by its "tectonic purity": true outgassing
             raises SO2 without raising NO2, while traffic/industry raise both.
             A high SO2/NO2 ratio => genuine degassing; low ratio => city noise.
        """
        aq = self._air_quality or {}
        base = self._degassing_baseline or {}

        so2 = aq.get("so2", 0.0)
        no2 = aq.get("no2", 0.0)

        so2_excess = max(0.0, so2 - base.get("so2", 0.0))
        no2_excess = max(0.0, no2 - base.get("no2", 0.0))

        # purity in [0,1]: 1.0 = pure SO2 spike (tectonic), ~0 = NO2-heavy (urban)
        tectonic_purity = so2_excess / (so2_excess + no2_excess + 1.0)

        return {
            "so2_excess": round(so2_excess, 2),
            "no2_excess": round(no2_excess, 2),
            "tectonic_purity": round(tectonic_purity, 3),
        }

    def _chemical_stress(self) -> float:
        if not self._air_quality:
            return 0.0

        sig = self._degassing_signature()
        so2_excess = sig["so2_excess"]
        tectonic_purity = sig["tectonic_purity"]

        stress = 0.0
        # Degassing signal: excess SO2 over the natural background, weighted by
        # how clean (tectonic vs urban) the signature is.
        if so2_excess > 5.0:
            stress += min(0.5, (so2_excess / 50.0) * (0.4 + 0.6 * tectonic_purity))

        # PM2.5 / CO are more ambiguous markers — mild contribution only.
        pm25 = self._air_quality.get("pm2_5", 0.0)
        if pm25 > 35.0:
            stress += min(0.15, pm25 / 300.0)
        co = self._air_quality.get("co", 0.0)
        if co > 400.0:
            stress += min(0.15, co / 3000.0)

        return min(1.0, stress)

    def _global_node_anomalies(self) -> List[Dict[str, Any]]:
        """Evaluate the global event nodes for degassing and marine anomalies.

        Volcano/tectonic nodes: SO2 excess over the natural baseline (or high
        CO) marks active outgassing. Marine nodes: anomalous sea-surface
        heating (the marine variable fantasma) marks possible energy discharge.
        """
        base = self._degassing_baseline or {}
        base_so2 = base.get("so2", 0.0)
        anomalies: List[Dict[str, Any]] = []

        for node in self._global_node_scan:
            tipo = node.get("tipo", "")
            name = node.get("node", "?")

            if tipo in ("VOLCAN", "TECTONICO"):
                so2_excess = max(0.0, node.get("so2", 0.0) - base_so2)
                co = node.get("co", 0.0)
                if so2_excess > self.NODE_SO2_EXCESS_ALERT or co > self.NODE_CO_ALERT:
                    anomalies.append({
                        "node": name,
                        "tipo": tipo,
                        "anomaly": "DEGASSING",
                        "so2_excess": round(so2_excess, 2),
                        "co": co,
                        "lat": node.get("lat"),
                        "lon": node.get("lon"),
                    })
            elif tipo == "MARINO":
                temp = node.get("temp_c")
                if temp is not None and temp > self.MARINE_THERMAL_THRESHOLD_C:
                    anomalies.append({
                        "node": name,
                        "tipo": tipo,
                        "anomaly": "MARINE_THERMAL",
                        "temp_c": temp,
                        "lat": node.get("lat"),
                        "lon": node.get("lon"),
                    })

        return anomalies

    def _fog_anomaly(self) -> bool:
        for reading in self._atmospheric_readings:
            vis = reading.get("visibility_m", 10000)
            if vis < self.FOG_VISIBILITY_THRESHOLD:
                return True
        return False

    def analyze(self) -> AgentSignal:
        if (
            not self._pressure_gradient
            and not self._air_quality
            and not self._global_node_scan
        ):
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                reasoning="No atmospheric data available",
            )

        pressure_score = self._pressure_stress()
        chemical_score = self._chemical_stress()
        fog_detected = self._fog_anomaly()
        node_anomalies = self._global_node_anomalies()

        combined = pressure_score * 0.4 + chemical_score * 0.4
        if fog_detected:
            combined += 0.2
        # Each global node anomaly (degassing at a volcano, marine heating)
        # raises the composite — capped so a single noisy node can't max it.
        combined += min(0.3, len(node_anomalies) * 0.15)

        signal_data = {
            "pressure_stress": pressure_score,
            "chemical_stress": chemical_score,
            "fog_detected": fog_detected,
            "combined_atmospheric": combined,
            "global_node_anomalies": node_anomalies,
        }

        if self._pressure_gradient:
            signal_data["mean_pressure"] = self._pressure_gradient.get("mean_pressure", 1013.0)
        if self._air_quality:
            signal_data["so2"] = self._air_quality.get("so2", 0.0)
            signal_data["aqi"] = self._air_quality.get("aqi", 0)
            sig = self._degassing_signature()
            signal_data["so2_excess"] = sig["so2_excess"]
            signal_data["tectonic_purity"] = sig["tectonic_purity"]
            if self._degassing_baseline:
                signal_data["so2_natural_baseline"] = self._degassing_baseline.get("so2", 0.0)

        if combined > 0.6:
            reasons = []
            if pressure_score > 0.3:
                reasons.append(f"pressure anomaly ({pressure_score:.2f})")
            if chemical_score > 0.3:
                sig = self._degassing_signature()
                reasons.append(
                    f"tectonic degassing (SO2 excess {sig['so2_excess']}, "
                    f"purity {sig['tectonic_purity']})"
                )
            if fog_detected:
                reasons.append("fog/low visibility")
            for anomaly in node_anomalies:
                reasons.append(f"{anomaly['anomaly']} @ {anomaly['node']}")
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
