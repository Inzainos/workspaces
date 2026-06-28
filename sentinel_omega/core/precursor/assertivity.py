"""
Assertivity Tracker — V46 COMMANDER Lineage

Validates precursor predictions against real USGS seismic events.
Uses euclidean distance within a configurable radius (default 5°) to
determine if a predicted precursor zone experienced actual seismic activity.

Tracks:
  - Hit rate (predictions confirmed by events)
  - Miss rate (events not predicted)
  - False alarm rate (predictions with no corresponding event)

Legacy reference: TITAN V46 calcular_asertividad() compared UVG node
predictions with USGS catalog using 5-degree radius matching.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    timestamp: float
    latitude: float
    longitude: float
    risk_level: str
    fantasma: float
    source: str = "geodynamic"
    validated: Optional[bool] = None
    matching_event: Optional[Dict[str, Any]] = None


@dataclass
class AssertivityResult:
    total_predictions: int
    total_events: int
    hits: int
    misses: int
    false_alarms: int
    hit_rate: float
    miss_rate: float
    false_alarm_rate: float
    evaluation_window_days: int


class AssertivityTracker:
    """
    Tracks predictions and validates them against observed seismic events.
    Maintains a rolling window of predictions for continuous assertivity scoring.
    """

    def __init__(self, radius_degrees: float = 5.0, window_days: int = 30):
        self._radius = radius_degrees
        self._window_days = window_days
        self._predictions: List[Prediction] = []
        self._events: List[Dict[str, Any]] = []

    @property
    def prediction_count(self) -> int:
        return len(self._predictions)

    def record_prediction(
        self,
        latitude: float,
        longitude: float,
        risk_level: str,
        fantasma: float,
        source: str = "geodynamic",
    ) -> Prediction:
        pred = Prediction(
            timestamp=time.time(),
            latitude=latitude,
            longitude=longitude,
            risk_level=risk_level,
            fantasma=fantasma,
            source=source,
        )
        self._predictions.append(pred)
        self._prune_old()
        logger.info(
            f"Prediction recorded: ({latitude:.2f}, {longitude:.2f}) "
            f"risk={risk_level} fantasma={fantasma:.2f}"
        )
        return pred

    def ingest_events(self, events: List[Dict[str, Any]]) -> None:
        """
        Ingest real seismic events from USGS for validation.
        Each event dict must have: latitude, longitude, magnitude, time.
        """
        self._events = events
        logger.info(f"Assertivity: ingested {len(events)} seismic events")

    @staticmethod
    def _euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return np.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

    def validate(self, min_magnitude: float = 4.5) -> AssertivityResult:
        """
        Validate all pending predictions against ingested seismic events.
        A prediction is a HIT if any event M>=min_magnitude occurred within
        radius_degrees of the predicted location within the evaluation window.
        """
        filtered_events = [
            e for e in self._events
            if e.get("magnitude", 0) >= min_magnitude
        ]

        hits = 0
        false_alarms = 0
        for pred in self._predictions:
            matched = False
            for event in filtered_events:
                dist = self._euclidean_distance(
                    pred.latitude, pred.longitude,
                    event.get("latitude", 0), event.get("longitude", 0),
                )
                if dist <= self._radius:
                    pred.validated = True
                    pred.matching_event = event
                    matched = True
                    break

            if matched:
                hits += 1
            else:
                pred.validated = False
                false_alarms += 1

        matched_event_coords = set()
        for pred in self._predictions:
            if pred.matching_event:
                lat = pred.matching_event.get("latitude", 0)
                lon = pred.matching_event.get("longitude", 0)
                matched_event_coords.add((round(lat, 4), round(lon, 4)))

        misses = 0
        for event in filtered_events:
            coord = (round(event.get("latitude", 0), 4), round(event.get("longitude", 0), 4))
            if coord not in matched_event_coords:
                misses += 1

        total_preds = len(self._predictions)
        total_events = len(filtered_events)

        result = AssertivityResult(
            total_predictions=total_preds,
            total_events=total_events,
            hits=hits,
            misses=misses,
            false_alarms=false_alarms,
            hit_rate=hits / max(total_preds, 1),
            miss_rate=misses / max(total_events, 1),
            false_alarm_rate=false_alarms / max(total_preds, 1),
            evaluation_window_days=self._window_days,
        )

        logger.info(
            f"Assertivity: {result.hit_rate:.1%} hit rate, "
            f"{result.miss_rate:.1%} miss rate, "
            f"{hits}/{total_preds} predictions confirmed"
        )
        return result

    def _prune_old(self) -> None:
        cutoff = time.time() - (self._window_days * 86400)
        self._predictions = [p for p in self._predictions if p.timestamp >= cutoff]

    def format_report(self, result: AssertivityResult) -> str:
        """Format assertivity result for Telegram dispatch."""
        return (
            f"<b>ASSERTIVITY REPORT</b>\n\n"
            f"Window: <code>{result.evaluation_window_days}d</code>\n"
            f"Predictions: <code>{result.total_predictions}</code>\n"
            f"Events (M≥4.5): <code>{result.total_events}</code>\n\n"
            f"Hits: <code>{result.hits}</code> ({result.hit_rate:.0%})\n"
            f"Misses: <code>{result.misses}</code> ({result.miss_rate:.0%})\n"
            f"False Alarms: <code>{result.false_alarms}</code> ({result.false_alarm_rate:.0%})"
        )
