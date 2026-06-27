"""
Core SNT Satellization Engine
R(t) = a · t^b

b < 0  → Convergence (shadow node gaining on hub)
b ≈ 0  → Equilibrium (stable orbit)
b > 0  → Satellization (hub absorbing shadow node)
b ≥ 1  → Roche Radius (accelerating absorption)
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import spearmanr, mannwhitneyu
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DominanceRegime(Enum):
    CONVERGENCE = "convergence"
    EQUILIBRIUM = "equilibrium"
    SATELLIZATION = "satellization"
    ROCHE_RADIUS = "roche_radius"
    LEAPFROG = "leapfrog"


@dataclass
class SatellizationResult:
    a: float
    b: float
    r_squared: float
    p_value: float
    regime: DominanceRegime
    n_observations: int
    trigger_type: Optional[str] = None


class SatellizationEngine:
    ROCHE_THRESHOLD = 1.0
    EQUILIBRIUM_BAND = 0.05
    CONVERGENCE_THRESHOLD = -0.05

    @staticmethod
    def power_law(t, a, b):
        return a * np.power(t, b)

    def fit(self, t: np.ndarray, ratio: np.ndarray) -> SatellizationResult:
        mask = (t > 0) & np.isfinite(ratio) & (ratio > 0)
        t_clean = t[mask]
        r_clean = ratio[mask]

        if len(t_clean) < 3:
            raise ValueError(f"Insufficient data points: {len(t_clean)}")

        log_t = np.log(t_clean)
        log_r = np.log(r_clean)
        coeffs = np.polyfit(log_t, log_r, 1)
        b_init, a_init = coeffs[0], np.exp(coeffs[1])

        try:
            popt, pcov = curve_fit(
                self.power_law, t_clean, r_clean,
                p0=[a_init, b_init], maxfev=10000
            )
            a, b = popt
        except RuntimeError:
            a, b = a_init, b_init

        r_pred = self.power_law(t_clean, a, b)
        ss_res = np.sum((r_clean - r_pred) ** 2)
        ss_tot = np.sum((r_clean - np.mean(r_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        rho, p_value = spearmanr(t_clean, r_clean)

        regime = self._classify_regime(b)

        return SatellizationResult(
            a=a, b=b, r_squared=r_squared, p_value=p_value,
            regime=regime, n_observations=len(t_clean)
        )

    def _classify_regime(self, b: float) -> DominanceRegime:
        if b >= self.ROCHE_THRESHOLD:
            return DominanceRegime.ROCHE_RADIUS
        elif b > self.EQUILIBRIUM_BAND:
            return DominanceRegime.SATELLIZATION
        elif b >= self.CONVERGENCE_THRESHOLD:
            return DominanceRegime.EQUILIBRIUM
        else:
            return DominanceRegime.CONVERGENCE

    def detect_leapfrog(self, b_history: np.ndarray, window: int = 10) -> bool:
        if len(b_history) < window * 2:
            return False
        early = np.mean(b_history[:window])
        late = np.mean(b_history[-window:])
        return early > 0.1 and late < -0.05

    def compare_triggers(
        self, abrupt_bs: np.ndarray, gradual_bs: np.ndarray
    ) -> dict:
        stat, p = mannwhitneyu(abrupt_bs, gradual_bs, alternative='greater')
        ratio = np.mean(abrupt_bs) / np.mean(gradual_bs) if np.mean(gradual_bs) != 0 else float('inf')
        return {
            "abrupt_mean_b": float(np.mean(abrupt_bs)),
            "gradual_mean_b": float(np.mean(gradual_bs)),
            "velocity_ratio": ratio,
            "mann_whitney_U": stat,
            "p_value": p,
        }
