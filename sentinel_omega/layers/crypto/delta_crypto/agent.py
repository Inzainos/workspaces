"""
Delta-Crypto Agent — Market Sentiment & Social Topology
Sources: Social media APIs, Fear & Greed index, Google Trends, news sentiment
Variables: Sentiment score, social volume, influencer impact, FUD/FOMO index
Method: ASI (Atomic Sovereignty Index) applied to market participants

SNT Application:
  - Social media influencers = Hubs, followers = Shadow Nodes
  - ASI measures whether traders act autonomously or follow herd
  - High ASI clusters → informed money (potential signal)
  - Low ASI mass → retail herd (potential fade signal)
"""

import numpy as np
from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType
from sentinel_omega.core.snt_engine import AtomicSovereigntyIndex, NBodyMatrix


class DeltaCryptoAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="delta_crypto", layer="crypto")
        self._asi = AtomicSovereigntyIndex()
        self._nbody = NBodyMatrix()
        self._fear_greed: float = 50.0
        self._social_volume: float = 0.0
        self._influencer_map: Dict[str, float] = {}

    def ingest(self, data: Dict[str, Any]) -> None:
        self._fear_greed = data.get("fear_greed_index", 50.0)
        self._social_volume = data.get("social_volume", 0.0)
        self._influencer_map = data.get("influencer_reach", {})
        self.logger.info(f"Delta-Crypto: FGI={self._fear_greed}, social_vol={self._social_volume:.0f}")

    def analyze(self) -> AgentSignal:
        extreme_fear = self._fear_greed < 20
        extreme_greed = self._fear_greed > 80

        topology_signal = SignalType.NEUTRAL
        topology_confidence = 0.3

        if self._influencer_map and len(self._influencer_map) >= 3:
            hub = max(self._influencer_map, key=self._influencer_map.get)
            result = self._nbody.analyze(self._influencer_map, hub)

            if result.power_law_b < -0.3:
                topology_signal = SignalType.BULLISH
                topology_confidence = 0.6
            elif result.power_law_b > 0.8:
                topology_signal = SignalType.BEARISH
                topology_confidence = 0.6

        if extreme_fear:
            return self.emit_signal(
                SignalType.BULLISH, 0.7,
                data={"fear_greed": self._fear_greed, "social_volume": self._social_volume},
                reasoning=f"Extreme fear ({self._fear_greed}) — contrarian bullish signal"
            )
        elif extreme_greed:
            return self.emit_signal(
                SignalType.BEARISH, 0.7,
                data={"fear_greed": self._fear_greed, "social_volume": self._social_volume},
                reasoning=f"Extreme greed ({self._fear_greed}) — contrarian bearish signal"
            )

        return self.emit_signal(
            topology_signal, topology_confidence,
            data={"fear_greed": self._fear_greed},
        )

    def health_check(self) -> bool:
        return 0 <= self._fear_greed <= 100
