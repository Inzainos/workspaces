"""
Alfa-Bolsa Agent — Technical Stock Market Analysis
Sources: Yahoo Finance, Alpha Vantage, BMV/IPC data
Variables: OHLCV, RSI, MACD, Bollinger, Volume profile
Method: RandomForest + SNT satellization on sector ratios

SNT Application:
  - Sector ETF = Hub, component stocks = Shadow Nodes
  - Fits R(t) to stock/sector ratio over rolling windows
  - Leapfrog detection: stock breaking out of sector gravity
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import SatellizationEngine


class AlfaBolsaAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="alfa_bolsa", layer="bolsa")
        self._snt = SatellizationEngine()
        self._ohlcv: Optional[pd.DataFrame] = None
        self._index_data: Optional[pd.DataFrame] = None

    def ingest(self, data: Dict[str, Any]) -> None:
        self._ohlcv = data.get("stock_ohlcv")
        self._index_data = data.get("index_ohlcv")
        self.logger.info("Alfa-Bolsa data ingested")

    def analyze(self) -> AgentSignal:
        if self._ohlcv is None or self._index_data is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        if "close" not in self._ohlcv.columns or "close" not in self._index_data.columns:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0)

        min_len = min(len(self._ohlcv), len(self._index_data))
        stock_close = self._ohlcv["close"].values[-min_len:]
        index_close = self._index_data["close"].values[-min_len:]

        ratio = stock_close / np.where(index_close > 0, index_close, 1)
        t = np.arange(1, len(ratio) + 1, dtype=float)

        try:
            fit = self._snt.fit_ratio(t, ratio)
        except (ValueError, RuntimeError):
            return self.emit_signal(SignalType.NEUTRAL, 0.3)

        rsi = self._compute_rsi(stock_close)

        if fit.b < -0.1 and rsi < 30:
            return self.emit_signal(
                SignalType.BULLISH, 0.75,
                data={"snt_b": fit.b, "rsi": rsi, "regime": fit.regime.value},
                reasoning=f"Stock converging on index (b={fit.b:.3f}), RSI oversold ({rsi:.0f})"
            )
        elif fit.b > 0.5 and rsi > 70:
            return self.emit_signal(
                SignalType.BEARISH, 0.7,
                data={"snt_b": fit.b, "rsi": rsi, "regime": fit.regime.value},
                reasoning=f"Stock being satellized (b={fit.b:.3f}), RSI overbought ({rsi:.0f})"
            )

        return self.emit_signal(
            SignalType.NEUTRAL, 0.4,
            data={"snt_b": fit.b, "rsi": rsi},
        )

    @staticmethod
    def _compute_rsi(prices: np.ndarray, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices[-(period + 1):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def health_check(self) -> bool:
        return self._ohlcv is not None and len(self._ohlcv) >= 30
