"""
OpenWeatherMap API connector — Atmospheric data for geodynamic analysis.

Fetches real-time weather for monitoring stations, mapping to fact_estado_tierra
schema: pressure, temperature, humidity, visibility, wind.

Legacy lineage: TITAN V32/V42 used OWM for Blue Jets pressure correlation
at Tlaxcala (19.31, -98.24). V2.0 extends to multiple seismic monitoring nodes.

Requires: OPENWEATHERMAP_KEY environment variable.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5"
OWM_AIR_BASE = "https://api.openweathermap.org/data/2.5/air_pollution"
TIMEOUT = 10

MONITORING_STATIONS: Dict[str, Dict[str, float]] = {
    "tlaxcala": {"lat": 19.31, "lon": -98.24},
    "oaxaca": {"lat": 17.07, "lon": -96.72},
    "guerrero": {"lat": 17.55, "lon": -99.50},
    "colima": {"lat": 19.24, "lon": -103.72},
    "michoacan": {"lat": 19.17, "lon": -102.05},
    "chiapas": {"lat": 16.75, "lon": -93.12},
    "cdmx": {"lat": 19.43, "lon": -99.13},
    "puebla": {"lat": 19.04, "lon": -98.21},
}


@dataclass
class AtmosphericReading:
    station: str
    lat: float
    lon: float
    pressure_hpa: float
    temp_c: float
    humidity_pct: float
    visibility_m: float
    wind_speed_ms: float
    wind_deg: float
    clouds_pct: float
    weather_id: int = 800


def _get_api_key() -> Optional[str]:
    key = os.environ.get("OPENWEATHERMAP_KEY")
    if not key:
        logger.warning("OPENWEATHERMAP_KEY not set")
    return key


def fetch_weather(
    lat: float,
    lon: float,
    station_name: str = "unknown",
) -> Optional[AtmosphericReading]:
    """Fetch current weather for a single coordinate."""
    api_key = _get_api_key()
    if not api_key:
        return None

    url = f"{OWM_BASE}/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        weather_list = data.get("weather", [])
        weather_id = weather_list[0].get("id", 800) if weather_list else 800

        reading = AtmosphericReading(
            station=station_name,
            lat=lat,
            lon=lon,
            pressure_hpa=main.get("pressure", 1013.0),
            temp_c=main.get("temp", 20.0),
            humidity_pct=main.get("humidity", 50.0),
            visibility_m=data.get("visibility", 10000),
            wind_speed_ms=wind.get("speed", 0.0),
            wind_deg=wind.get("deg", 0.0),
            clouds_pct=clouds.get("all", 0),
            weather_id=weather_id,
        )
        logger.info(
            f"OWM {station_name}: {reading.pressure_hpa}hPa, "
            f"{reading.temp_c}C, {reading.humidity_pct}%RH"
        )
        return reading
    except Exception as e:
        logger.error(f"OWM fetch failed for {station_name}: {e}")
        return None


def fetch_air_quality(
    lat: float,
    lon: float,
) -> Optional[Dict[str, float]]:
    """Fetch air pollution data (CO, SO2, NO2, PM2.5) for a coordinate."""
    api_key = _get_api_key()
    if not api_key:
        return None

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
    }
    try:
        resp = requests.get(OWM_AIR_BASE, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("list"):
            return None

        components = data["list"][0].get("components", {})
        result = {
            "co": components.get("co", 0.0),
            "so2": components.get("so2", 0.0),
            "no2": components.get("no2", 0.0),
            "pm2_5": components.get("pm2_5", 0.0),
            "pm10": components.get("pm10", 0.0),
            "o3": components.get("o3", 0.0),
            "aqi": data["list"][0].get("main", {}).get("aqi", 0),
        }
        logger.info(f"OWM AQ: CO={result['co']}, SO2={result['so2']}, AQI={result['aqi']}")
        return result
    except Exception as e:
        logger.error(f"OWM air quality fetch failed: {e}")
        return None


def fetch_monitoring_network(
    stations: Optional[List[str]] = None,
) -> List[AtmosphericReading]:
    """Fetch weather for multiple monitoring stations."""
    target = stations or list(MONITORING_STATIONS.keys())
    readings = []
    for name in target:
        coords = MONITORING_STATIONS.get(name)
        if coords is None:
            continue
        reading = fetch_weather(coords["lat"], coords["lon"], station_name=name)
        if reading:
            readings.append(reading)
    logger.info(f"Monitoring network: {len(readings)}/{len(target)} stations responding")
    return readings


def compute_pressure_gradient(readings: List[AtmosphericReading]) -> Dict[str, Any]:
    """Compute pressure anomalies across the monitoring network."""
    if len(readings) < 2:
        return {"mean_pressure": 1013.0, "pressure_spread": 0.0, "low_pressure_stations": []}

    pressures = [r.pressure_hpa for r in readings]
    mean_p = sum(pressures) / len(pressures)
    spread = max(pressures) - min(pressures)

    low_stations = [
        r.station for r in readings
        if r.pressure_hpa < 1008
    ]

    return {
        "mean_pressure": mean_p,
        "pressure_spread": spread,
        "low_pressure_stations": low_stations,
        "station_count": len(readings),
    }
