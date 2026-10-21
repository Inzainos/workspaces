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

from sentinel_omega.infrastructure.api._http import get_session

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

# Global event nodes — key volcanic, tectonic, and marine points of the grid.
# Volcano/tectonic nodes are scanned for degassing (CO/SO2); marine nodes for
# thermal anomalies (the marine "variable fantasma": anomalous sea-surface
# heating linked to ionization/energy discharge, per the V601 lineage).
GLOBAL_EVENT_NODES: Dict[str, Dict[str, Any]] = {
    "popocatepetl": {"lat": 19.02, "lon": -98.62, "tipo": "VOLCAN"},
    "yellowstone": {"lat": 44.42, "lon": -110.58, "tipo": "VOLCAN"},
    "fuji": {"lat": 35.36, "lon": 138.72, "tipo": "TECTONICO"},
    "andes_chile": {"lat": -33.44, "lon": -70.66, "tipo": "TECTONICO"},
    "san_andres": {"lat": 34.05, "lon": -118.24, "tipo": "TECTONICO"},
    "guerrero_gap": {"lat": 16.85, "lon": -99.90, "tipo": "TECTONICO"},
    "islandia_rift": {"lat": 64.96, "lon": -19.02, "tipo": "TECTONICO"},
    "bermudas": {"lat": 25.00, "lon": -71.00, "tipo": "MARINO"},
    "hawaii_hotspot": {"lat": 19.89, "lon": -155.58, "tipo": "MARINO"},
    "fosa_japon": {"lat": 36.00, "lon": 142.00, "tipo": "MARINO"},
}

# Marine surface temp above this (deg C) counts as a thermal anomaly candidate.
MARINE_THERMAL_THRESHOLD_C = 29.0

# Reference stations in remote, unpopulated zones (open ocean, desert, polar).
# Human industrial/traffic emissions are effectively zero here, so any measured
# SO2/CO is natural background or true tectonic/volcanic outgassing. Used to
# learn the "clean baseline" — the signature of what natural degassing looks
# like against zero human noise, so populated-zone readings can be corrected.
REFERENCE_STATIONS: Dict[str, Dict[str, float]] = {
    "pacifico_nemo": {"lat": -48.87, "lon": -123.39},   # Point Nemo — most remote ocean point
    "atlantico_sur": {"lat": -30.0, "lon": -15.0},      # mid South Atlantic
    "indico_sur": {"lat": -40.0, "lon": 80.0},          # mid South Indian Ocean
    "atacama": {"lat": -24.5, "lon": -69.25},           # driest desert, minimal industry
    "antartida": {"lat": -75.0, "lon": 0.0},            # polar clean-air baseline
}


@dataclass
class AtmosphericReading:
    """Lectura atmosférica. Campo ausente = None (regla 7/8), nunca un
    número plausible: 1013 hPa/20 °C/cielo despejado venían aquí como
    defaults benignos y entraban a beta2 y al Fantasma como si estuvieran
    medidos (hallado 2026-10-19). Campos nuevos (gust/rain/grnd_level) son
    datos que OWM ya entregaba y se tiraban."""
    station: str
    lat: float
    lon: float
    pressure_hpa: Optional[float] = None       # nivel del mar (OWM "pressure")
    temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    visibility_m: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_deg: Optional[float] = None
    clouds_pct: Optional[float] = None
    weather_id: Optional[int] = None
    wind_gust_ms: Optional[float] = None       # ráfaga — perturbación pre-tormenta
    rain_1h: Optional[float] = None             # mm en la última hora
    snow_1h: Optional[float] = None
    grnd_level_hpa: Optional[float] = None      # presión a nivel de estación
    data_ts: Optional[int] = None               # dt del servidor OWM (frescura)


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
        resp = get_session().get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        rain = data.get("rain", {})
        snow = data.get("snow", {})
        weather_list = data.get("weather", [])

        # Sin defaults: campo ausente = None (regla 7/8). Antes un JSON sin
        # "pressure" se publicaba como 1013 hPa — calma falsa en cadena.
        # Plausibilidad física (ítem 3, 2026-10-20): API corrupta → NULL.
        from sentinel_omega.infrastructure.api.plausibilidad import validar

        def _f(n, v) -> Optional[float]:
            return validar(n, _f_raw(v), origen=station_name)

        def _f_raw(v) -> Optional[float]:
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        reading = AtmosphericReading(
            station=station_name,
            lat=lat,
            lon=lon,
            pressure_hpa=_f("pressure_hpa", main.get("pressure")),
            temp_c=_f("temp_c", main.get("temp")),
            humidity_pct=_f("humidity_pct", main.get("humidity")),
            visibility_m=_f("visibility_m", data.get("visibility")),
            wind_speed_ms=_f("wind_speed_ms", wind.get("speed")),
            wind_deg=_f_raw(wind.get("deg")),
            clouds_pct=_f("clouds_pct", clouds.get("all")),
            weather_id=(
                int(weather_list[0].get("id"))
                if weather_list and weather_list[0].get("id") is not None
                else None
            ),
            wind_gust_ms=_f("wind_gust_ms", wind.get("gust")),
            rain_1h=_f("rain_1h", rain.get("1h")),
            snow_1h=_f("snow_1h", snow.get("1h")),
            grnd_level_hpa=_f("grnd_level_hpa", main.get("grnd_level")),
            data_ts=data.get("dt"),
        )
        faltantes = sum(
            1 for v in (reading.pressure_hpa, reading.temp_c, reading.humidity_pct)
            if v is None
        )
        if faltantes:
            logger.warning(
                "OWM %s: %d campo(s) base ausentes en el JSON — se reportan "
                "como NULL, no como valores plausibles", station_name, faltantes,
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
        resp = get_session().get(OWM_AIR_BASE, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("list"):
            return None

        components = data["list"][0].get("components", {})
        # Sin defaults: gas ausente = None (regla 7/8). Antes 0.0 "medido";
        # y aqi 0 es un valor IMPOSIBLE (la escala OWM es 1-5).
        # Plausibilidad física (ítem 3, 2026-10-20): gas absurdo → NULL.
        from sentinel_omega.infrastructure.api.plausibilidad import validar

        result: Dict[str, Optional[float]] = {
            "co": validar("co", components.get("co")),
            "so2": validar("so2", components.get("so2")),
            "no2": validar("no2", components.get("no2")),
            "pm2_5": validar("pm2_5", components.get("pm2_5")),
            "pm10": validar("pm10", components.get("pm10")),
            "o3": validar("o3", components.get("o3")),
            "aqi": validar("aqi", data["list"][0].get("main", {}).get("aqi")),
        }
        logger.info(f"OWM AQ: CO={result['co']}, SO2={result['so2']}, AQI={result['aqi']}")
        return result
    except Exception as e:
        logger.error(f"OWM air quality fetch failed: {e}")
        return None


def fetch_reference_baseline() -> Optional[Dict[str, float]]:
    """
    Learn the natural degassing signature from remote, unpopulated zones.

    Averages air-quality gases across ocean/desert/polar reference stations
    where human emissions are ~zero. The result is the "clean background" —
    what the atmosphere looks like with only natural degassing present.
    Populated-zone readings are then compared against this to isolate the
    true tectonic/volcanic outgassing from urban pollution noise.
    """
    samples: List[Dict[str, float]] = []
    for name, coords in REFERENCE_STATIONS.items():
        aq = fetch_air_quality(coords["lat"], coords["lon"])
        if aq:
            samples.append(aq)

    if not samples:
        return None

    # Media por gas IGNORANDO muestras sin ese gas (None); gas sin ninguna
    # muestra válida → None, no 0.0 (regla 7/8).
    gases = ("co", "so2", "no2", "pm2_5", "pm10", "o3")
    baseline: Dict[str, Optional[float]] = {}
    for g in gases:
        vals = [s[g] for s in samples if s.get(g) is not None]
        baseline[g] = round(sum(vals) / len(vals), 3) if vals else None
    baseline["station_count"] = len(samples)
    logger.info(
        f"Reference baseline (natural degassing): "
        f"SO2={baseline['so2']}, CO={baseline['co']} from {len(samples)} clean zones"
    )
    return baseline


def scan_global_nodes(
    nodes: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scan the global event nodes for degassing and marine thermal anomalies.

    For each node fetches gases (CO/SO2/NO2) and surface temperature.
    Volcano/tectonic nodes carry the degassing reading; marine nodes carry
    the sea-surface temperature for thermal-anomaly analysis in Beta-2.
    """
    target = nodes or list(GLOBAL_EVENT_NODES.keys())
    results: List[Dict[str, Any]] = []

    for name in target:
        cfg = GLOBAL_EVENT_NODES.get(name)
        if cfg is None:
            continue

        entry: Dict[str, Any] = {
            "node": name,
            "lat": cfg["lat"],
            "lon": cfg["lon"],
            "tipo": cfg["tipo"],
        }

        aq = fetch_air_quality(cfg["lat"], cfg["lon"])
        if aq:
            # Solo campos presentes: un gas ausente ya no se reporta como 0.0.
            for g in ("so2", "co", "no2"):
                if aq.get(g) is not None:
                    entry[g] = aq[g]

        reading = fetch_weather(cfg["lat"], cfg["lon"], station_name=name)
        if reading:
            if reading.temp_c is not None:
                entry["temp_c"] = reading.temp_c
            if reading.pressure_hpa is not None:
                entry["pressure_hpa"] = reading.pressure_hpa

        # El nodo entra si produjo ALGÚN dato medido (no defaults).
        if any(k in entry for k in ("so2", "co", "no2", "temp_c", "pressure_hpa")):
            results.append(entry)

    logger.info(f"Global node scan: {len(results)}/{len(target)} nodes responding")
    return results


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
    """Gradiente de presión SOBRE las lecturas que traen presión medida.

    Sin suficientes presiones válidas → mean_pressure None (sin dato), no
    1013.0: ese default alimentaba el término de presión del Fantasma con
    calma falsa cuando OWM no respondía (regla 7/8, hallado 2026-10-19)."""
    presiones = [r for r in readings if r.pressure_hpa is not None]
    if len(presiones) < 2:
        logger.warning(
            "Gradiente de presión: %d de %d lecturas con presión — sin dato",
            len(presiones), len(readings),
        )
        return {
            "mean_pressure": None,
            "pressure_spread": None,
            "low_pressure_stations": [],
            "station_count": len(presiones),
        }

    vals = [r.pressure_hpa for r in presiones]
    mean_p = sum(vals) / len(vals)
    spread = max(vals) - min(vals)
    low_stations = [r.station for r in presiones if r.pressure_hpa < 1008]

    return {
        "mean_pressure": mean_p,
        "pressure_spread": spread,
        "low_pressure_stations": low_stations,
        "station_count": len(presiones),
    }


# ── Pronóstico 5 días / 3 horas (2026-10-19) ────────────────────────────────
# Endpoint incluido en la MISMA key (tier gratuito) y nunca usado: es la
# anticipación atmosférica — la caída barométrica PRONOSTICADA, no solo el
# "ahora" que ya consume beta2. TTL de 3 h: OWM emite el forecast cada ~3 h y
# así no gastamos cuota por ciclo (10 estaciones × ciclo de 5 min).
OWM_FORECAST_TTL_S = 3 * 3600
_forecast_cache: Dict[str, Dict[str, Any]] = {}
_forecast_cache_ts: Dict[str, float] = {}


def fetch_forecast(
    lat: float,
    lon: float,
    station_name: str = "unknown",
) -> Optional[Dict[str, Any]]:
    """Resumen del pronóstico 5d/3h de OWM para una coordenada.

    Devuelve el dato útil para precursores, no la lista cruda:
      - presion_min_48h / caida_24h: mínimo y caída de presión pronosticados
      - presion_min_ts: hora (ISO) de ese mínimo — cuándo llega el pico
      - lluvia_24h_mm / rafaga_max_ms: precipitación y ráfaga acumuladas
      - n_pasos: pasos recibidos (sanity)
    None en un campo = OWM no lo pronosticó (regla 7/8). Fail-soft total.
    """
    import time as _time

    clave = f"{station_name}:{lat:.2f},{lon:.2f}"
    ahora = _time.time()
    cached = _forecast_cache.get(clave)
    if cached and (ahora - _forecast_cache_ts.get(clave, 0.0)) < OWM_FORECAST_TTL_S:
        return cached

    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        resp = get_session().get(
            f"{OWM_BASE}/forecast",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        pasos = resp.json().get("list", [])
        if not pasos:
            return None

        presiones = [
            (p["main"]["pressure"], p["dt"])
            for p in pasos
            if isinstance(p.get("main"), dict) and p["main"].get("pressure") is not None
        ]
        emision_ts = pasos[0].get("dt")

        def _sum_rain(field: str, horas: int) -> Optional[float]:
            total = 0.0
            hay = False
            for p in pasos[:horas // 3]:
                v = (p.get(field) or {}).get("3h")
                if v is not None:
                    total += float(v)
                    hay = True
            return round(total, 2) if hay else None

        rafagas = [
            p["wind"].get("gust")
            for p in pasos[:8]
            if isinstance(p.get("wind"), dict) and p["wind"].get("gust") is not None
        ]

        resumen: Dict[str, Any] = {
            "station": station_name,
            "emision_dt": emision_ts,
            "presion_min_24h": min((p for p, _ in presiones[:8]), default=None),
            "presion_min_48h": min((p for p, _ in presiones[:16]), default=None),
            "presion_min_ts": (
                min(presiones[:16], key=lambda x: x[0])[1] if len(presiones) >= 16 or presiones else None
            ),
            "lluvia_24h_mm": _sum_rain("rain", 24),
            "nieve_24h_mm": _sum_rain("snow", 24),
            "rafaga_max_24h_ms": max(rafagas) if rafagas else None,
            "n_pasos": len(pasos),
        }
        # Caída pronosticada desde la primera lectura (proxy del "ahora").
        if presiones:
            resumen["caida_24h_hpa"] = round(presiones[0][0] - (resumen["presion_min_24h"] or presiones[0][0]), 2)
        else:
            resumen["caida_24h_hpa"] = None

        _forecast_cache[clave] = resumen
        _forecast_cache_ts[clave] = ahora
        logger.info(
            "OWM forecast %s: mín 48h=%s hPa, caída 24h=%s hPa, lluvia 24h=%s mm",
            station_name, resumen["presion_min_48h"],
            resumen["caida_24h_hpa"], resumen["lluvia_24h_mm"],
        )
        return resumen
    except Exception as e:  # noqa: BLE001 — fail-soft, como el resto de OWM
        logger.warning("OWM forecast falló para %s: %s", station_name, e)
        return None
