"""
Beta-Crypto Agent — On-Chain & Spectral Analysis
Sources: Blockchain explorers, exchange order books, mempool data
Variables: Active addresses, transaction volume, whale movements, funding rates
Method: FFT spectral analysis on market cycles + on-chain divergence
Role: Cycle detection, whale tracking, order book imbalance

SNT Application:
  - Whale wallets = Hubs, retail = Shadow Nodes
  - Friction = regulatory environment (varies by jurisdiction)
  - Order book FFT reveals manipulation patterns
"""

import numpy as np
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import InstitutionalFrictionCalculator


class BetaCryptoAgent(BaseAgent):

    FFT_WINDOW = 168  # 7 days of hourly data

    def __init__(self):
        super().__init__(name="beta_crypto", layer="crypto")
        self._friction_calc = InstitutionalFrictionCalculator()
        self._volume_series: Optional[np.ndarray] = None
        self._whale_ratio: float = 0.0
        self._funding_rate: float = 0.0

    def ingest(self, data: Dict[str, Any]) -> None:
        self._volume_series = data.get("volume_series")
        self._whale_ratio = data.get("whale_transaction_ratio", 0.0)
        self._funding_rate = data.get("funding_rate", 0.0)

        jurisdiction = data.get("jurisdiction", "unknown")
        self._friction = self._friction_calc.calculate(
            regulatory_density=data.get("regulatory_score", 0.2),
            structural_barriers=data.get("exchange_barriers", 0.1),
            temporal_inertia=data.get("market_maturity", 0.3),
            domain="crypto"
        )
        self.logger.info(f"Beta-Crypto: friction={self._friction.score:.2f}, whale_ratio={self._whale_ratio:.2%}")

    def analyze(self) -> AgentSignal:
        if self._volume_series is None or len(self._volume_series) < self.FFT_WINDOW:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        fft = np.fft.rfft(self._volume_series[-self.FFT_WINDOW:])
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(self.FFT_WINDOW)

        peak_idx = np.argmax(power[1:]) + 1
        dominant_period = 1.0 / freqs[peak_idx] if freqs[peak_idx] > 0 else 0

        whale_alert = self._whale_ratio > 0.35
        funding_extreme = abs(self._funding_rate) > 0.01

        risk_score = 0.0
        if whale_alert:
            risk_score += 0.4
        if funding_extreme:
            risk_score += 0.3
        if dominant_period < 24:
            risk_score += 0.3

        if risk_score > 0.6:
            signal = SignalType.BEARISH if self._funding_rate > 0 else SignalType.BULLISH
            return self.emit_signal(
                signal, risk_score,
                data={
                    "dominant_cycle_hours": float(dominant_period),
                    "whale_ratio": self._whale_ratio,
                    "funding_rate": self._funding_rate,
                    "friction_score": self._friction.score,
                },
                reasoning=f"On-chain divergence: whale={self._whale_ratio:.2%}, funding={self._funding_rate:.4f}"
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.3,
            data={"dominant_cycle_hours": float(dominant_period)},
        )

    def health_check(self) -> bool:
        return self._volume_series is not None and len(self._volume_series) >= self.FFT_WINDOW
