"""Node-level prediction validation for Juez auditor."""

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def validate_prediction_per_node(
    conn: sqlite3.Connection,
    nodos_prediccion: List[int],
    ts_evento_inicio: float,
    ts_evento_fin: float,
    mag_minima: float = 4.5,
    radio_km: float = 500,
) -> Dict[str, any]:
    """Validate a node-specific prediction against actual seismic events.

    When a prediction marks specific nodes (e.g., nodes 14, 21, 57),
    validate ONLY against earthquakes within the geographic zones of
    those nodes, not against the entire 50-node mesh.

    Args:
        conn: SQLite connection to SENTINEL_OMEGA_PRO.db
        nodos_prediccion: List of node_ids the prediction applies to
        ts_evento_inicio: Start timestamp of prediction window (unix seconds)
        ts_evento_fin: End timestamp of prediction window (unix seconds)
        mag_minima: Minimum magnitude to consider (default 4.5)
        radio_km: Search radius around each node (default 500 km for 5°)

    Returns:
        Dict with validation results:
            {
                "validacion": "ACIERTO" | "FALLO" | "FALSO_POSITIVO",
                "nodos_evaluados": [14, 21, 57],
                "eventos_encontrados": [
                    {
                        "event_id": "usgs2005...",
                        "timestamp": 1234567890.0,
                        "magnitude": 5.2,
                        "lat": 24.1,
                        "lon": -110.0,
                        "nodo_mas_cercano": 14,
                        "distancia_km": 45.3,
                    },
                    ...
                ],
                "eventos_cerca": 3,  # Count of matching events
                "tasa_base_local": 0.15,  # Tasa base for this zone/period
                "confianza_gana": True,  # Whether system beat baseline
            }
    """
    if not nodos_prediccion:
        return {
            "validacion": "FALSO_POSITIVO",
            "razon": "No nodes specified in prediction",
            "nodos_evaluados": [],
            "eventos_encontrados": [],
            "eventos_cerca": 0,
        }

    # Get lat/lon for each node
    nodo_coords = _get_node_coordinates(conn, nodos_prediccion)
    if not nodo_coords:
        return {
            "validacion": "FALSO_POSITIVO",
            "razon": "Could not locate node coordinates",
            "nodos_evaluados": nodos_prediccion,
            "eventos_encontrados": [],
            "eventos_cerca": 0,
        }

    # Query USGS catalog for events in the prediction window
    # within the geographic zones of the specified nodes
    eventos = _query_eventos_por_nodos(
        conn,
        nodos_prediccion,
        nodo_coords,
        ts_evento_inicio,
        ts_evento_fin,
        mag_minima,
        radio_km,
    )

    eventos_cerca = len(eventos)
    resultado = "ACIERTO" if eventos_cerca > 0 else "FALLO"

    return {
        "validacion": resultado,
        "nodos_evaluados": nodos_prediccion,
        "eventos_encontrados": eventos,
        "eventos_cerca": eventos_cerca,
        "ventana_inicio": datetime.fromtimestamp(ts_evento_inicio).isoformat(),
        "ventana_fin": datetime.fromtimestamp(ts_evento_fin).isoformat(),
        "mag_minima": mag_minima,
    }


def validate_prediction_global(
    conn: sqlite3.Connection,
    ts_evento_inicio: float,
    ts_evento_fin: float,
    mag_minima: float = 4.5,
) -> Dict[str, any]:
    """Validate a global (non-nodal) prediction against entire seismic catalog.

    Used for backwards compatibility and for measuring tasa base.

    Args:
        conn: SQLite connection
        ts_evento_inicio: Start timestamp (unix seconds)
        ts_evento_fin: End timestamp (unix seconds)
        mag_minima: Minimum magnitude to consider

    Returns:
        Dict with validation results
    """
    dt_inicio = datetime.fromtimestamp(ts_evento_inicio)
    dt_fin = datetime.fromtimestamp(ts_evento_fin)

    query = """
        SELECT event_id, timestamp, magnitude, lat, lon
        FROM TBL_HISTORICO_SISMICO
        WHERE timestamp >= ? AND timestamp < ? AND magnitude >= ?
        ORDER BY timestamp
    """

    eventos = conn.execute(
        query,
        (ts_evento_inicio, ts_evento_fin, mag_minima),
    ).fetchall()

    resultado = {
        "validacion": "ACIERTO" if eventos else "FALLO",
        "eventos_encontrados": [
            {
                "event_id": e[0],
                "timestamp": e[1],
                "magnitude": e[2],
                "lat": e[3],
                "lon": e[4],
            }
            for e in eventos
        ],
        "eventos_cerca": len(eventos),
        "ventana_inicio": dt_inicio.isoformat(),
        "ventana_fin": dt_fin.isoformat(),
        "mag_minima": mag_minima,
    }

    return resultado


def _get_node_coordinates(
    conn: sqlite3.Connection,
    nodos: List[int],
) -> Dict[int, Tuple[float, float]]:
    """Get lat/lon coordinates for each node.

    Returns:
        Dict mapping node_id -> (lat, lon)
    """
    placeholders = ",".join("?" * len(nodos))
    query = f"SELECT node_id, lat, lon FROM TBL_NODOS_TOPOLOGIA WHERE node_id IN ({placeholders})"

    rows = conn.execute(query, nodos).fetchall()
    return {int(row[0]): (float(row[1]), float(row[2])) for row in rows}


def _query_eventos_por_nodos(
    conn: sqlite3.Connection,
    nodos: List[int],
    nodo_coords: Dict[int, Tuple[float, float]],
    ts_inicio: float,
    ts_fin: float,
    mag_minima: float,
    radio_km: float,
) -> List[Dict[str, any]]:
    """Query USGS catalog for events within specified nodes' zones.

    Returns:
        List of event dicts with location and distance info
    """
    events = []

    # Fetch all events in the time window above magnitude threshold
    query = """
        SELECT event_id, timestamp, magnitude, lat, lon
        FROM TBL_HISTORICO_SISMICO
        WHERE timestamp >= ? AND timestamp < ? AND magnitude >= ?
        ORDER BY timestamp
    """

    rows = conn.execute(query, (ts_inicio, ts_fin, mag_minima)).fetchall()

    # Filter to only those within range of specified nodes
    for event_id, ts, mag, lat, lon in rows:
        distances = [
            (nodo, _haversine_distance(lat, lon, nlat, nlon))
            for nodo, (nlat, nlon) in nodo_coords.items()
        ]

        nearest_nodo, nearest_dist = min(distances, key=lambda x: x[1])

        if nearest_dist <= radio_km:
            events.append(
                {
                    "event_id": event_id,
                    "timestamp": ts,
                    "magnitude": mag,
                    "lat": lat,
                    "lon": lon,
                    "nodo_mas_cercano": nearest_nodo,
                    "distancia_km": round(nearest_dist, 1),
                }
            )

    return events


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km using Haversine formula."""
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth radius in km

    lat1_r = radians(lat1)
    lon1_r = radians(lon1)
    lat2_r = radians(lat2)
    lon2_r = radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c
