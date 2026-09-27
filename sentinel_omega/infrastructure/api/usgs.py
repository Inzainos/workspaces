"""
USGS Earthquake API connector.
Public FDSN web service, no authentication.
"""

import logging
from typing import Optional

import pandas as pd
from sentinel_omega.infrastructure.api._http import get_session
from sentinel_omega.infrastructure.api.circuit_breaker import circuit

logger = logging.getLogger(__name__)

TIMEOUT = 15

# El tope que se le pide a FDSN. Se expone porque quien CUENTA el catálogo
# necesita saber si topó: para M2,5+ en 30 días el mundo da muchos más de
# 500, así que `len(catálogo)` vale 500 constante y eso NO es un conteo.
# Medido el 2026-09-27: `sismo_count_win` y `sismo_count_72h` llegaban a los
# modelos como 500 fijo en todos los ciclos (launcher.py:659).
MAX_RESULTS = 500


@circuit("usgs")
def fetch_earthquakes(
    min_magnitude: float = 4.5,
    days: int = 30,
    max_results: int = MAX_RESULTS,
) -> Optional[pd.DataFrame]:
    """Fetch recent earthquakes from USGS FDSN."""
    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    _fdsn_fmt = "%Y-%m-%dT%H:%M:%S"
    starttime = start.strftime(_fdsn_fmt)
    endtime = end.strftime(_fdsn_fmt)

    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        f"?format=geojson&starttime={starttime}"
        f"&endtime={endtime}"
        f"&minmagnitude={min_magnitude}&limit={max_results}"
        "&orderby=time"
    )
    try:
        resp = get_session().get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        features = resp.json().get("features", [])

        records = []
        for f in features:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [None, None, None])
            event_id = f.get("id") or props.get("code") or props.get("ids")
            if isinstance(event_id, str) and event_id.startswith(","):
                event_id = event_id.strip(",").split(",")[0]
            records.append({
                "event_id": event_id or None,
                "time": pd.to_datetime(props.get("time"), unit="ms"),
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "depth_km": coords[2] if len(coords) > 2 else None,
                "longitude": coords[0] if len(coords) > 0 else None,
                "latitude": coords[1] if len(coords) > 1 else None,
                "type": props.get("type"),
                "mag_type": props.get("magType") or "",
            })

        df = pd.DataFrame(records)
        logger.info(f"USGS: {len(df)} earthquakes (M>={min_magnitude}, {days}d)")
        return df.sort_values("time")
    except Exception as e:
        logger.error(f"USGS fetch failed: {e}")
    return None


@circuit("usgs")
def count_earthquakes(
    min_magnitude: float = 2.5,
    days: int = 30,
) -> Optional[int]:
    """El conteo REAL del catálogo, sin el tope de `limit`.

    `fetch_earthquakes` pide `limit=MAX_RESULTS`, así que `len(...)` de su
    resultado vale 500 en cuanto haya más de 500 --- y para M2,5+ en 30 días
    siempre hay más. Los modelos recibían ese 500 como si fuera un conteo
    (`sismo_count_win`, `sismo_count_72h`: dos posiciones del vector de beta1
    ocupadas por una constante, medido el 2026-09-27 en el ciclo 14419).

    FDSN tiene un endpoint aparte que devuelve sólo el número de eventos que
    coinciden, sin traerlos ni recortarlos. Con eso el conteo vuelve a ser una
    medición en vez de un tope.

    Devuelve None si no se pudo contar --- y entonces quien llama OMITE el
    rasgo. Un 0 ahí diría «ningún sismo», que es peor mentira que el tope.
    """
    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    _fdsn_fmt = "%Y-%m-%dT%H:%M:%S"

    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/count"
        f"?format=geojson&starttime={start.strftime(_fdsn_fmt)}"
        f"&endtime={end.strftime(_fdsn_fmt)}"
        f"&minmagnitude={min_magnitude}"
    )
    try:
        resp = get_session().get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        cuerpo = resp.json()
        # El endpoint responde {"count": N} con format=geojson; en texto plano
        # devuelve el número solo. Se aceptan las dos formas.
        n = cuerpo.get("count") if isinstance(cuerpo, dict) else cuerpo
        if n is None:
            return None
        n = int(n)
        logger.info("USGS count: %d sismos (M>=%s, %dd)", n, min_magnitude, days)
        return n
    except Exception as e:  # noqa: BLE001 — nunca bloquea el ciclo
        logger.warning("USGS count falló (%s): el conteo queda sin dato", e)
        return None
