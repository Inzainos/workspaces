"""
Alfa-1 Agent — Historical Space Weather Analysis
Source: OMNI NASA SPDF (30 years, 6h resolution)
Variables: Bz (IMF Z), Solar Wind velocity/density, Proton flux
Method: RandomForest → ONNX export
Role: Base conditioning — long-range correlations
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Alfa1Agent(BaseAgent):

    FEATURES = [
        "bz_gsm", "plasma_speed", "proton_density",
        "proton_flux_10mev", "dst_index", "ae_index",
        "kp_index", "ap_index", "field_mag_avg", "flow_pressure"
    ]
    TARGET_WINDOW_H = 72

    def __init__(self):
        super().__init__(name="alfa1", layer="geodynamic")
        self._model = None
        self._latest_features: Optional[np.ndarray] = None

    def ingest(self, data: Dict[str, Any]) -> None:
        df = data.get("omni_dataframe")
        if df is None:
            self.logger.warning("No OMNI data provided")
            return

        available = [f for f in self.FEATURES if f in df.columns]
        self._latest_features = df[available].values
        self.logger.info(f"Ingested {len(df)} OMNI records, {len(available)} features")

    def analyze(self) -> AgentSignal:
        if self._latest_features is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0,
                                   reasoning="No data ingested")

        bz_mean = np.nanmean(self._latest_features[:, 0]) if self._latest_features.shape[1] > 0 else 0

        if bz_mean < -10:
            return self.emit_signal(
                SignalType.ALERT, 0.85,
                data={"bz_mean": float(bz_mean)},
                reasoning=f"Bz severely negative ({bz_mean:.1f} nT) — geomagnetic storm conditions"
            )
        elif bz_mean < -5:
            return self.emit_signal(
                SignalType.ALERT, 0.5,
                data={"bz_mean": float(bz_mean)},
                reasoning=f"Bz moderately negative ({bz_mean:.1f} nT) — elevated activity"
            )
        else:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.3,
                data={"bz_mean": float(bz_mean)},
                reasoning=f"Bz normal range ({bz_mean:.1f} nT)"
            )

    def health_check(self) -> bool:
        return self._latest_features is not None
