"""
Beta-1 Agent — Spectral/Frequency Analysis + measured Schumann resonance
Sources: NOAA Kp index, USGS seismic catalog, IERS LOD, Lunar phase,
         Tomsk SRF (MEASURED Schumann resonance: frequency + activity)
Method: plain FFT spectral features on Kp + measured-Schumann excitation

Honestidad física (v2.5.1):
  El "filtro armónico Schumann" sobre Kp muestreado a 3 h era numerología:
  7.83 Hz está ~5 órdenes de magnitud por encima del Nyquist (~4.6e-5 Hz),
  así que la "coherencia armónica" salía ≈1 siempre y sumaba un boost
  espurio a la confianza. Se eliminó. Ahora:
    - El FFT del Kp es una feature espectral PLANA (energía, periodo
      dominante, ratio de alta frecuencia) — sin disfraz de resonancia.
    - "Schumann" es el dato MEDIDO real de Tomsk (schumann_frequency /
      schumann_activity), tratado como serie propia — la excitación medida
      sí puede subir confianza, porque es una observación, no un artefacto.
"""

import numpy as np
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType

# Maximum LOD reference (ms) used to normalise rotacion_tierra to [0, 1].
LOD_REF_MS: float = 3.0

# La correlación T-L solo es estadísticamente admisible con ventana larga:
# dos series suaves en ventana corta dan |r| alto por azar. Exigimos que la
# serie lunar cubra al menos 3 ciclos completos (3 wraps de fase).
MIN_CICLOS_LUNARES = 3


def kp_spectral_features(
    power_spectrum: np.ndarray,
    sample_interval_s: float,
) -> Dict[str, Any]:
    """Plain spectral features of the Kp power spectrum.

    No harmonic/resonance interpretation: at hours-scale sampling the
    spectrum resolves periods of hours-days, nothing else. Returns total
    energy, high-frequency energy ratio and dominant period (hours).
    """
    n_fft = len(power_spectrum)
    total_energy = float(np.sum(power_spectrum[1:]))
    if n_fft < 2 or total_energy < 1e-10:
        return {
            "total_energy": 0.0,
            "high_freq_ratio": 0.0,
            "dominant_period_h": 0.0,
        }

    dominant_idx = int(np.argmax(power_spectrum[1:]) + 1)
    n_signal = 2 * (n_fft - 1)
    dominant_period_h = (
        (n_signal * sample_interval_s / 3600.0) / dominant_idx
        if dominant_idx > 0 else 0.0
    )
    high = float(np.sum(power_spectrum[n_fft // 2:]))
    return {
        "total_energy": total_energy,
        "high_freq_ratio": high / total_energy,
        "dominant_period_h": float(dominant_period_h),
    }


class Beta1Agent(BaseAgent):

    FFT_WINDOW_H = 48
    KP_SAMPLE_INTERVAL_H = 3
    SCHUMANN_EXCITATION_THRESHOLD = 15.0   # % actividad medida (Tomsk)
    SCHUMANN_STRONG_EXCITATION = 30.0      # excitación fuerte medida

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

    def _compute_tl_features(self) -> Dict[str, Any]:
        """Tierra-Luna (TL) features.

        correlacion_TL SOLO se calcula con ventana >= MIN_CICLOS_LUNARES
        ciclos lunares completos (dos series suaves en ventana corta dan
        |r| alto por azar). Con ventana corta se reporta None y NUNCA
        alimenta confianza — es dato informativo, no voto.
        """
        if self._lunar_phase is not None and len(self._lunar_phase) > 0:
            fase_luna = float(np.clip(self._lunar_phase[-1], 0.0, 1.0))
        else:
            fase_luna = 0.5

        if self._lod_ms is not None and len(self._lod_ms) > 0:
            lod_last = float(self._lod_ms[-1])
            rotacion_tierra = float(np.clip(1.0 - lod_last / LOD_REF_MS, 0.0, 1.0))
        else:
            rotacion_tierra = 1.0

        correlacion_TL = None
        ciclos = 0
        if (
            self._lunar_phase is not None and len(self._lunar_phase) >= 2
            and self._lod_ms is not None and len(self._lod_ms) >= 2
        ):
            n = min(len(self._lunar_phase), len(self._lod_ms))
            lp = np.asarray(self._lunar_phase[-n:], dtype=float)
            ld = np.asarray(self._lod_ms[-n:], dtype=float)
            # Ciclos completos = wraps de fase (salto de ~1 -> ~0)
            ciclos = int(np.sum(np.diff(lp) < -0.5))
            if (
                ciclos >= MIN_CICLOS_LUNARES
                and np.std(lp) > 1e-10 and np.std(ld) > 1e-10
            ):
                r = float(np.corrcoef(lp, ld)[0, 1])
                correlacion_TL = round(r, 4) if np.isfinite(r) else None

        return {
            "fase_luna": round(fase_luna, 4),
            "rotacion_tierra": round(rotacion_tierra, 4),
            "correlacion_TL": correlacion_TL,   # None si ventana corta
            "ciclos_lunares_en_ventana": ciclos,
            "estado_TL": round(fase_luna * rotacion_tierra, 6),
        }

    def analyze(self) -> AgentSignal:
        if self._kp_series is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        window = self._kp_series[-self.FFT_WINDOW_H:]
        fft_result = np.fft.rfft(window)
        power_spectrum = np.abs(fft_result) ** 2

        spec = kp_spectral_features(
            power_spectrum,
            sample_interval_s=self.KP_SAMPLE_INTERVAL_H * 3600,
        )
        high_freq_ratio = spec["high_freq_ratio"]

        # Schumann MEDIDO (Tomsk) — serie propia, no filtro del Kp
        schumann_excited = (
            self._schumann_activity > self.SCHUMANN_EXCITATION_THRESHOLD
        )
        schumann_strong = (
            self._schumann_activity > self.SCHUMANN_STRONG_EXCITATION
        )

        tl = self._compute_tl_features()
        signal_data = {
            "dominant_period_h": spec["dominant_period_h"],
            "high_freq_ratio": float(high_freq_ratio),
            "spectral_energy": spec["total_energy"],
            # Schumann medido (Tomsk) — observación real
            "schumann_hz": float(self._schumann_hz),
            "schumann_activity_pct": float(self._schumann_activity),
            "schumann_excited": bool(schumann_excited),
            # Tierra-Luna tidal coupling features (informativo)
            "fase_luna": tl["fase_luna"],
            "rotacion_tierra": tl["rotacion_tierra"],
            "correlacion_TL": tl["correlacion_TL"],
            "ciclos_lunares_en_ventana": tl["ciclos_lunares_en_ventana"],
            "estado_TL": tl["estado_TL"],
        }

        if high_freq_ratio > 0.6 or (high_freq_ratio > 0.4 and schumann_excited):
            confidence = 0.7
            if schumann_excited:
                confidence += 0.1   # excitación MEDIDA, no artefacto

            reasons = ["Elevated high-frequency Kp components"]
            if schumann_excited:
                reasons.append(
                    f"measured Schumann excitation "
                    f"{self._schumann_activity:.0f}%"
                )
            return self.emit_signal(
                SignalType.ALERT, min(confidence, 0.95),
                data=signal_data,
                reasoning=" + ".join(reasons),
            )

        if schumann_strong:
            # Espectro Kp normal pero la resonancia MEDIDA está fuertemente
            # excitada — estado intermedio de observación.
            return self.emit_signal(
                SignalType.WATCH, 0.45,
                data=signal_data,
                reasoning=(
                    f"Normal Kp spectrum but measured Schumann strongly "
                    f"excited ({self._schumann_activity:.0f}%)"
                ),
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data=signal_data,
            reasoning="Normal spectral distribution",
        )

    def health_check(self) -> bool:
        return self._kp_series is not None and len(self._kp_series) >= self.FFT_WINDOW_H
