"""
Alfa-Crypto Agent — Historical Crypto Market Analysis
Sources: Exchange APIs (Bitso, Binance), CoinGecko, historical CSV
Variables: Price, Volume, Market Cap, BTC Dominance, RSI, MACD
Method: RandomForest + SNT satellization fitting
Role: Long-range market structure analysis via power law dynamics

SNT Application:
  - Fits R(t) = a·t^b to BTC/altcoin dominance ratios
  - b < 0 → Altcoin gaining (convergence / alt season)
  - b > 0 → BTC absorbing (satellization / BTC season)
  - b ≥ 1 → Roche Radius (altcoin collapse imminent)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import SatellizationEngine


class AlfaCryptoAgent(BaseAgent):

    TRACKED_PAIRS = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
        "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT",
    ]

    def __init__(self):
        super().__init__(name="alfa_crypto", layer="crypto")
        self._snt = SatellizationEngine()
        self._price_data: Optional[pd.DataFrame] = None
        self._dominance_ratios: Dict[str, float] = {}

    def ingest(self, data: Dict[str, Any]) -> None:
        self._price_data = data.get("price_dataframe")
        btc_mcap = data.get("btc_market_cap", 0)
        total_mcap = data.get("total_market_cap", 1)

        if btc_mcap and total_mcap:
            self._dominance_ratios["btc"] = btc_mcap / total_mcap

        self.logger.info(f"Ingested crypto data, BTC dominance: {self._dominance_ratios.get('btc', 0):.2%}")

    def analyze(self) -> AgentSignal:
        if self._price_data is None or len(self._price_data) < 30:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0,
                                   reasoning="Insufficient price history")

        results = {}
        for pair in self.TRACKED_PAIRS:
            col = pair.replace("/", "_").lower()
            if col not in self._price_data.columns:
                continue

            btc_col = "btc_usdt"
            if btc_col not in self._price_data.columns:
                continue

            ratio = self._price_data[col] / self._price_data[btc_col]
            ratio = ratio.dropna()
            if len(ratio) < 10:
                continue

            t = np.arange(1, len(ratio) + 1, dtype=float)
            try:
                fit = self._snt.fit_ratio(t, ratio.values)
                results[pair] = {
                    "b": fit.b,
                    "r_squared": fit.r_squared,
                    "regime": fit.regime.value,
                }
            except (ValueError, RuntimeError):
                continue

        if not results:
            return self.emit_signal(SignalType.NEUTRAL, 0.3)

        avg_b = np.mean([r["b"] for r in results.values()])

        if avg_b > 0.5:
            return self.emit_signal(
                SignalType.BEARISH, 0.7,
                data={"avg_b": float(avg_b), "pair_analysis": results},
                reasoning=f"Altcoins being satellized (avg b={avg_b:.3f}) — BTC dominance rising"
            )
        elif avg_b < -0.2:
            return self.emit_signal(
                SignalType.BULLISH, 0.65,
                data={"avg_b": float(avg_b), "pair_analysis": results},
                reasoning=f"Altcoin convergence detected (avg b={avg_b:.3f}) — alt season signal"
            )
        else:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.4,
                data={"avg_b": float(avg_b)},
                reasoning=f"Market in equilibrium (avg b={avg_b:.3f})"
            )

    def health_check(self) -> bool:
        return self._price_data is not None and len(self._price_data) >= 30
