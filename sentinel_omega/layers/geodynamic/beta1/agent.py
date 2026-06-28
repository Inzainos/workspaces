"""
Beta-1 Agent — Spectral/Frequency Analysis
Sources: NOAA Kp index, USGS seismic catalog, IERS LOD, Lunar phase
Method: FFT — Fourier pattern detection
Role: Frequency/harmonic analysis, tidal cycles, cymatic patterns
"""

import numpy as np
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Beta1Agent(BaseAgent):

    FFT_WINDOW_H = 48

    SCHUMANN_EXCITATION_THRESHOLD = 15.0

    def __init__(self):
        super().__init__(name="beta1", layer="geodynamic")
        self._kp_series: Optional[np.ndarray] = None
        self._seismic_data: Optional[np.ndarray] = None
        self._lod_ms: Optional[np.ndarray] = None
        self._lunar_phase: Optional[np.ndarray] = None
        self._schumann_hz: float = 7.83
        self._schumann_activity: float = 0.0

    def ingest(self, data: Dict[str, Any]) -> None:
        self._kp_series = data.get("kp_series")
        self._seismic_data = data.get("seismic_magnitudes")
        self._lod_ms = data.get("lod_ms")
        self._lunar_phase = data.get("lunar_phase")
        self._schumann_hz = data.get("schumann_frequency", 7.83)
        self._schumann_activity = data.get("schumann_activity", 0.0)
        self.logger.info("Beta-1 data ingested")

    def analyze(self) -> AgentSignal:
        if self._kp_series is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        fft_result = np.fft.rfft(self._kp_series[-self.FFT_WINDOW_H:])
        power_spectrum = np.abs(fft_result) ** 2
        dominant_freq_idx = np.argmax(power_spectrum[1:]) + 1
        dominant_period = len(self._kp_series) / dominant_freq_idx if dominant_freq_idx > 0 else 0

        spectral_energy = np.sum(power_spectrum)
        high_freq_ratio = np.sum(power_spectrum[len(power_spectrum)//2:]) / max(spectral_energy, 1e-10)

        schumann_excited = self._schumann_activity > self.SCHUMANN_EXCITATION_THRESHOLD
        signal_data = {
            "dominant_period_h": float(dominant_period),
            "high_freq_ratio": float(high_freq_ratio),
            "spectral_energy": float(spectral_energy),
            "schumann_hz": float(self._schumann_hz),
            "schumann_activity_pct": float(self._schumann_activity),
        }

        if high_freq_ratio > 0.6 or (high_freq_ratio > 0.4 and schumann_excited):
            confidence = 0.7 if not schumann_excited else 0.8
            return self.emit_signal(
                SignalType.ALERT, confidence,
                data=signal_data,
                reasoning=(
                    "Elevated high-frequency Kp components"
                    + (" with Schumann excitation" if schumann_excited else "")
                ),
            )
        else:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.3,
                data=signal_data,
                reasoning="Normal spectral distribution",
            )

    def health_check(self) -> bool:
        return self._kp_series is not None and len(self._kp_series) >= self.FFT_WINDOW_H
