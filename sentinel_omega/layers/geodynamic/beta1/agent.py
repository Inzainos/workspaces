"""
Beta-1 Agent — The Artist (Cymatic Figure Generator)
Role: Generate the "Cymatic Signature" of the current system state.
Method: Captures a high-fidelity snapshot of the telemetric bands (spectral, lunar, Schumann)
         and formats it as a "Figure" to be interpreted by Beta-2.

This agent does not decide if an event is likely; it only describes the current
vibrational pattern (The Figure).
"""

import numpy as np
from typing import Any, Dict, Optional
from sentinel_omega.core.shared.agent_base import (
    AgentSignal,
    BaseAgent,
    SignalType,
    valor_medido,
)

LOD_REF_MS: float = 3.0
MIN_CICLOS_LUNARES = 3

def kp_spectral_features(power_spectrum: np.ndarray, sample_interval_s: float) -> Dict[str, Any]:
    n_fft = len(power_spectrum)
    total_energy = float(np.sum(power_spectrum[1:]))
    if n_fft < 2 or total_energy < 1e-10:
        return {"total_energy": 0.0, "high_freq_ratio": 0.0, "dominant_period_h": 0.0}

    dominant_idx = int(np.argmax(power_spectrum[1:]) + 1)
    n_signal = 2 * (n_fft - 1)
    dominant_period_h = ((n_signal * sample_interval_s / 3600.0) / dominant_idx if dominant_idx > 0 else 0.0)
    high = float(np.sum(power_spectrum[n_fft // 2:]))
    return {"total_energy": total_energy, "high_freq_ratio": high / total_energy, "dominant_period_h": float(dominant_period_h)}

class Beta1Agent(BaseAgent):
    FFT_WINDOW_H = 48
    KP_SAMPLE_INTERVAL_H = 3

    def __init__(self):
        super().__init__(name="beta1", layer="geodynamic")
        self._kp_series: Optional[np.ndarray] = None
        self._lod_ms: Optional[np.ndarray] = None
        self._lunar_phase: Optional[np.ndarray] = None
        # None, no 7.83 ni 0.0 (auditoría del 2026-09-26). Beta-1 es el LATIDO:
        # CLAUDE.md dice que todo se correlaciona contra él. Con el 7.83 y el 0.0
        # de relleno, tres de sus cinco rutas de decisión quedaban muertas EN
        # SILENCIO --- `schumann_excited` (>15 %), `schumann_strong` (>30 %) y
        # `composite_vibration` --- mientras reportaba 7.83 Hz al 0 % como si lo
        # hubiera medido. Con Tomsk congelado desde julio, eso es lo que venía
        # pasando cada ciclo.
        #
        # Su ruta principal NO depende de Schumann (`high_freq_ratio > 0.6` sale
        # del espectro de Kp), así que sin Schumann sigue pudiendo alarmar. Lo
        # que cambia es que ahora lo DICE en vez de aparentar una medición.
        self._schumann_hz: Optional[float] = None
        self._schumann_activity: Optional[float] = None

    def ingest(self, data: Dict[str, Any]) -> None:
        self._kp_series = data.get("kp_series")
        self._lod_ms = data.get("lod_ms")
        self._lunar_phase = data.get("lunar_phase")
        self._schumann_hz = valor_medido(data, "schumann_frequency", "schumann_hz")
        self._schumann_activity = valor_medido(data, "schumann_activity")
        self.logger.info("Beta-1 (Artist) data ingested")

    def _generate_cymatic_figure(self) -> Dict[str, Any]:
        """
        Generates the "Figure": a compressed vector of the current system vibration.
        This is the "Drawing" that Beta-2 will interpret.
        """
        if self._kp_series is not None:
            window = self._kp_series[-self.FFT_WINDOW_H:]
            power_spectrum = np.abs(np.fft.rfft(window)) ** 2
            spec = kp_spectral_features(power_spectrum, self.KP_SAMPLE_INTERVAL_H * 3600)
        else:
            spec = {"total_energy": 0.0, "high_freq_ratio": 0.0, "dominant_period_h": 0.0}

        fase_luna = float(np.clip(self._lunar_phase[-1], 0.0, 1.0)) if self._lunar_phase is not None and len(self._lunar_phase) > 0 else 0.5
        lod_last = float(np.clip(1.0 - (self._lod_ms[-1] / LOD_REF_MS), 0.0, 1.0)) if self._lod_ms is not None and len(self._lod_ms) > 0 else 1.0

        figure = {
            "spectral_energy": spec["total_energy"],
            "high_freq_ratio": spec["high_freq_ratio"],
            "dominant_period": spec["dominant_period_h"],
            "schumann_activity": self._schumann_activity,
            "schumann_hz": self._schumann_hz,
            "lunar_phase": fase_luna,
            "earth_rotation": lod_last,
            # None, no 0.0: «no medí la vibración» no es «la vibración es cero».
            "composite_vibration": (
                (spec["high_freq_ratio"] * self._schumann_activity) / 100.0
                if self._schumann_activity is not None else None
            ),
        }
        return figure

    def _compute_tl_features(self) -> Dict[str, Any]:
        fase_luna = float(np.clip(self._lunar_phase[-1], 0.0, 1.0)) if self._lunar_phase is not None and len(self._lunar_phase) > 0 else 0.5
        lod_last = float(np.clip(1.0 - (self._lod_ms[-1] / LOD_REF_MS), 0.0, 1.0)) if self._lod_ms is not None and len(self._lod_ms) > 0 else 1.0

        correlacion_TL = None
        ciclos = 0
        if (
            self._lunar_phase is not None and len(self._lunar_phase) >= 2
            and self._lod_ms is not None and len(self._lod_ms) >= 2
        ):
            n = min(len(self._lunar_phase), len(self._lod_ms))
            lp = np.asarray(self._lunar_phase[-n:], dtype=float)
            ld = np.asarray(self._lod_ms[-n:], dtype=float)
            ciclos = int(np.sum(np.diff(lp) < -0.5))
            if ciclos >= MIN_CICLOS_LUNARES and np.std(lp) > 1e-10 and np.std(ld) > 1e-10:
                r = float(np.corrcoef(lp, ld)[0, 1])
                correlacion_TL = round(r, 4) if np.isfinite(r) else None

        return {
            "fase_luna": round(fase_luna, 4),
            "rotacion_tierra": round(lod_last, 4),
            "correlacion_TL": correlacion_TL,
            "ciclos_lunares_en_ventana": ciclos,
            "estado_TL": round(fase_luna * lod_last, 6),
        }

    def analyze(self) -> AgentSignal:
        if self._kp_series is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        figure = self._generate_cymatic_figure()
        tl = self._compute_tl_features()

        # Tres estados, no dos: excitado, no excitado y NO LO SÉ. Antes el
        # relleno de 0.0 hacía que «no lo sé» se comportara como «no excitado»,
        # y nadie podía notar la diferencia leyendo el veredicto.
        sch_act = self._schumann_activity
        schumann_excited = None if sch_act is None else sch_act > 15.0
        schumann_strong = None if sch_act is None else sch_act > 30.0
        high_freq_ratio = figure["high_freq_ratio"]
        comp_vib = figure["composite_vibration"]

        signal_data = {
            "cymatic_figure": figure,
            "dominant_period_h": figure["dominant_period"],
            "high_freq_ratio": high_freq_ratio,
            "spectral_energy": figure["spectral_energy"],
            # None se propaga como None: quien lea esto tiene que poder
            # distinguir «no hubo excitación» de «no se midió».
            "schumann_hz": self._schumann_hz,
            "schumann_activity_pct": sch_act,
            "schumann_excited": schumann_excited,
            "schumann_sin_dato": sch_act is None,
            "fase_luna": tl["fase_luna"],
            "rotacion_tierra": tl["rotacion_tierra"],
            "correlacion_TL": tl["correlacion_TL"],
            "ciclos_lunares_en_ventana": tl["ciclos_lunares_en_ventana"],
            "estado_TL": tl["estado_TL"],
        }

        if high_freq_ratio > 0.6 or (high_freq_ratio > 0.4 and schumann_excited):
            confidence = 0.7
            if schumann_excited:
                confidence += 0.1
            reasons = ["Elevated high-frequency Kp components"]
            if schumann_excited:
                reasons.append(f"measured Schumann excitation {sch_act:.0f}%")
            elif sch_act is None:
                # Se alarmó solo con el espectro de Kp. Decirlo importa: el
                # operador tiene que saber que el latido no entró en la cuenta.
                reasons.append("Schumann sin dato (solo espectro Kp)")
            return self.emit_signal(
                SignalType.ALERT, min(confidence, 0.95),
                data=signal_data,
                reasoning=" + ".join(reasons),
            )

        vibracion_alta = comp_vib is not None and comp_vib > 0.5
        if schumann_strong or vibracion_alta:
            confidence = 0.45 if schumann_strong else 0.35
            if vibracion_alta:
                confidence = max(confidence, 0.6)
            return self.emit_signal(
                SignalType.WATCH, confidence,
                data=signal_data,
                reasoning="Cymatic figure generated for Beta-2 interpretation; Schumann excitation active"
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data=signal_data,
            reasoning=(
                "Normal spectral distribution"
                + ("; Schumann sin dato" if sch_act is None else "")
            ),
        )

    def health_check(self) -> bool:
        return self._kp_series is not None and len(self._kp_series) >= self.FFT_WINDOW_H
