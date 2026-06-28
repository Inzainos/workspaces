"""
Beta-1 Agent — Spectral/Frequency Analysis
Sources: NOAA Kp index, USGS seismic catalog, IERS LOD, Lunar phase
Method: FFT with Schumann harmonic filter
Role: Frequency/harmonic analysis, tidal cycles, cymatic patterns

Fourier-Schumann filter (Formulas.pdf):
  "Descartar frecuencias que no armonicen con la Resonancia de Schumann
   (7.83Hz o sus múltiplos)"
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType

SCHUMANN_HARMONICS_HZ: Tuple[float, ...] = (7.83, 14.3, 20.8, 27.3, 33.8)

HARMONIC_TOLERANCE = 0.15


def schumann_harmonic_filter(
    power_spectrum: np.ndarray,
    sample_interval_s: float,
    live_schumann_hz: float = 7.83,
    tolerance: float = HARMONIC_TOLERANCE,
) -> Dict[str, Any]:
    """
    Fourier-Schumann harmonic filter.

    Identifies which frequency bins in a power spectrum are sub-harmonic
    of the Schumann resonance (7.83 Hz and overtones). Attenuates
    non-resonant bins by 0.1×, keeping resonant energy intact.

    For low-rate geophysical data (hours-scale sampling), no bin can
    directly resolve 7.83 Hz. Instead we check sub-harmonic alignment:
    whether f_bin divides evenly into a Schumann harmonic.

    Returns coherence ratio, filtered spectrum, and resonant bin count.
    """
    n_fft = len(power_spectrum)
    n_signal = 2 * (n_fft - 1)
    freqs = np.fft.rfftfreq(n_signal, d=sample_interval_s)

    total_energy = float(np.sum(power_spectrum[1:]))
    if total_energy < 1e-10:
        return {
            "coherence": 0.0,
            "resonant_energy": 0.0,
            "total_energy": 0.0,
            "filtered_spectrum": power_spectrum.copy(),
            "resonant_bins": 0,
            "resonant_harmonics": [],
        }

    scale = live_schumann_hz / 7.83 if live_schumann_hz > 0 else 1.0
    scaled_harmonics = tuple(h * scale for h in SCHUMANN_HARMONICS_HZ)

    resonant_mask = np.zeros(n_fft, dtype=bool)
    resonant_mask[0] = True
    matched_harmonics: List[str] = []

    for i in range(1, n_fft):
        freq = freqs[i]
        if freq < 1e-10:
            continue
        for harmonic in scaled_harmonics:
            ratio = harmonic / freq
            nearest_int = round(ratio)
            if nearest_int > 0 and abs(ratio - nearest_int) / nearest_int < tolerance:
                resonant_mask[i] = True
                matched_harmonics.append(f"{freq:.6f}Hz→{harmonic:.2f}Hz//{nearest_int}")
                break

    resonant_energy = float(np.sum(power_spectrum[1:][resonant_mask[1:]]))
    coherence = resonant_energy / total_energy

    filtered = power_spectrum.copy()
    filtered[~resonant_mask] *= 0.1

    return {
        "coherence": coherence,
        "resonant_energy": resonant_energy,
        "total_energy": total_energy,
        "filtered_spectrum": filtered,
        "resonant_bins": int(np.sum(resonant_mask[1:])),
        "resonant_harmonics": matched_harmonics[:10],
    }


class Beta1Agent(BaseAgent):

    FFT_WINDOW_H = 48
    KP_SAMPLE_INTERVAL_H = 3
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

    def _apply_schumann_filter(
        self, power_spectrum: np.ndarray
    ) -> Dict[str, Any]:
        """Apply Fourier-Schumann harmonic filter to Kp power spectrum."""
        return schumann_harmonic_filter(
            power_spectrum=power_spectrum,
            sample_interval_s=self.KP_SAMPLE_INTERVAL_H * 3600,
            live_schumann_hz=self._schumann_hz,
        )

    def analyze(self) -> AgentSignal:
        if self._kp_series is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        window = self._kp_series[-self.FFT_WINDOW_H:]
        fft_result = np.fft.rfft(window)
        power_spectrum = np.abs(fft_result) ** 2

        sch_filter = self._apply_schumann_filter(power_spectrum)
        filtered_spectrum = sch_filter["filtered_spectrum"]

        dominant_freq_idx = np.argmax(filtered_spectrum[1:]) + 1
        dominant_period = len(window) / dominant_freq_idx if dominant_freq_idx > 0 else 0

        spectral_energy = np.sum(power_spectrum)
        filtered_energy = np.sum(filtered_spectrum)
        high_freq_ratio = (
            np.sum(filtered_spectrum[len(filtered_spectrum)//2:])
            / max(filtered_energy, 1e-10)
        )

        schumann_excited = self._schumann_activity > self.SCHUMANN_EXCITATION_THRESHOLD
        schumann_coherence = sch_filter["coherence"]

        signal_data = {
            "dominant_period_h": float(dominant_period),
            "high_freq_ratio": float(high_freq_ratio),
            "spectral_energy": float(spectral_energy),
            "filtered_energy": float(filtered_energy),
            "schumann_hz": float(self._schumann_hz),
            "schumann_activity_pct": float(self._schumann_activity),
            "schumann_coherence": float(schumann_coherence),
            "schumann_resonant_bins": sch_filter["resonant_bins"],
        }

        coherence_boost = schumann_coherence > 0.3
        if high_freq_ratio > 0.6 or (high_freq_ratio > 0.4 and schumann_excited):
            confidence = 0.7
            if schumann_excited:
                confidence += 0.1
            if coherence_boost:
                confidence += 0.05

            reasons = ["Elevated high-frequency Kp components (Schumann-filtered)"]
            if schumann_excited:
                reasons.append("Schumann excitation active")
            if coherence_boost:
                reasons.append(f"harmonic coherence={schumann_coherence:.0%}")

            return self.emit_signal(
                SignalType.ALERT, min(confidence, 0.95),
                data=signal_data,
                reasoning=" + ".join(reasons),
            )
        else:
            confidence = 0.3
            if coherence_boost and schumann_excited:
                confidence = 0.45
                return self.emit_signal(
                    SignalType.WATCH, confidence,
                    data=signal_data,
                    reasoning=(
                        f"Normal spectrum but Schumann-coherent "
                        f"(coherence={schumann_coherence:.0%}) with excitation"
                    ),
                )
            return self.emit_signal(
                SignalType.NEUTRAL, confidence,
                data=signal_data,
                reasoning="Normal spectral distribution (Schumann-filtered)",
            )

    def health_check(self) -> bool:
        return self._kp_series is not None and len(self._kp_series) >= self.FFT_WINDOW_H
