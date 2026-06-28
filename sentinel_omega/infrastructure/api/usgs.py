"""
USGS Earthquake API connector.
Public FDSN web service, no authentication.
"""

import logging
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TIMEOUT = 15


def fetch_earthquakes(
    min_magnitude: float = 4.5,
    days: int = 30,
    max_results: int = 500,
) -> Optional[pd.DataFrame]:
    """Fetch recent earthquakes from USGS FDSN."""
    from datetime import datetime, timedelta

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        f"?format=geojson&starttime={start.isoformat()}"
        f"&endtime={end.isoformat()}"
        f"&minmagnitude={min_magnitude}&limit={max_results}"
        "&orderby=time"
    )
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        features = resp.json().get("features", [])

        records = []
        for f in features:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [None, None, None])
            records.append({
                "time": pd.to_datetime(props.get("time"), unit="ms"),
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "depth_km": coords[2] if len(coords) > 2 else None,
                "longitude": coords[0] if len(coords) > 0 else None,
                "latitude": coords[1] if len(coords) > 1 else None,
                "type": props.get("type"),
            })

        df = pd.DataFrame(records)
        logger.info(f"USGS: {len(df)} earthquakes (M>={min_magnitude}, {days}d)")
        return df.sort_values("time")
    except Exception as e:
        logger.error(f"USGS fetch failed: {e}")
    return None
