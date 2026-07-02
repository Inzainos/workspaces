"""
Static UVG-125 Node Matrix — loaded into RAM at import time.

The 125 nodes of the Becker-Hagens (UVG 120) grid are a geometric constant.
They never change, so we load them once into memory and never query SQLite
for topology at runtime.

Layout:
  - Nodes 1-50: Physical (real seismic zones, volcanic centers)
  - Nodes 51-100: Ghost (inferred from seismic gaps)
  - Nodes 101-125: Geobattery (electrochemical accumulation)
  - Node 0: Observation point (Tlaxcala — asynchronous, does not affect Euler sum)
"""

import numpy as np

PHI = (1 + np.sqrt(5)) / 2
RADIO_TERRESTRE_KM = 6371.0

NODO_OBSERVACION = {
    "id": 0,
    "tipo": "observacion",
    "lat": 19.3182,
    "lon": -98.2375,
    "name": "TLAXMASTER",
    "region": "Mexico",
}

NODOS_MAESTROS_CONOCIDOS = {
    1: {"lat": 17.2, "lon": -100.5, "name": "Guerrero Gap", "tipo": "real"},
    2: {"lat": 15.9, "lon": -97.1, "name": "Oaxaca Costa", "tipo": "real"},
    3: {"lat": 14.8, "lon": -92.5, "name": "Chiapas Subducción", "tipo": "real"},
    4: {"lat": 19.2, "lon": -104.0, "name": "Jalisco-Colima", "tipo": "real"},
    5: {"lat": 18.0, "lon": -103.0, "name": "Michoacán Costa", "tipo": "real"},
    6: {"lat": 18.8, "lon": -98.9, "name": "Puebla-Morelos", "tipo": "real"},
    7: {"lat": 19.4, "lon": -99.1, "name": "CDMX Lago", "tipo": "real"},
    8: {"lat": 19.02, "lon": -98.63, "name": "Popocatépetl", "tipo": "real"},
    9: {"lat": 19.51, "lon": -103.62, "name": "Colima Volcán", "tipo": "real"},
    10: {"lat": 18.46, "lon": -97.39, "name": "Tehuacán", "tipo": "real"},
    11: {"lat": 19.32, "lon": -98.24, "name": "Tlaxcala", "tipo": "real"},
    14: {"lat": 25.0, "lon": 142.0, "name": "Triángulo Dragón", "tipo": "ghost"},
    16: {"lat": 19.5, "lon": -155.5, "name": "Hawaii Hotspot", "tipo": "real"},
    18: {"lat": 25.0, "lon": -71.0, "name": "Triángulo Bermudas", "tipo": "ghost"},
    21: {"lat": 33.0, "lon": 135.0, "name": "Japón Nankai", "tipo": "real"},
    26: {"lat": 26.95, "lon": -103.70, "name": "Vórtice 26 Fantasma", "tipo": "ghost"},
    29: {"lat": 29.9792, "lon": 31.1342, "name": "Giza Master", "tipo": "real"},
    35: {"lat": -20.0, "lon": -70.0, "name": "Nazca Andes", "tipo": "real"},
    43: {"lat": 19.5, "lon": -155.5, "name": "Hamakulia Hawaii", "tipo": "real"},
    47: {"lat": -26.4, "lon": -112.5, "name": "Isla Pascua", "tipo": "ghost"},
    61: {"lat": 90.0, "lon": 0.0, "name": "Polo Norte Vórtice", "tipo": "ghost"},
    62: {"lat": -90.0, "lon": 0.0, "name": "Polo Sur Vórtice", "tipo": "ghost"},
    125: {"lat": 0.0, "lon": 0.0, "name": "Núcleo Singularidad", "tipo": "geobattery"},
}


def _generar_matriz_125() -> list:
    """Generate the full 125+1 node matrix in RAM using golden ratio geometry."""
    matriz = [NODO_OBSERVACION]

    for i in range(1, 126):
        if i in NODOS_MAESTROS_CONOCIDOS:
            nodo = NODOS_MAESTROS_CONOCIDOS[i]
            matriz.append({
                "id": i,
                "tipo": nodo["tipo"],
                "lat": nodo["lat"],
                "lon": nodo["lon"],
                "name": nodo["name"],
                "region": nodo.get("region", ""),
            })
        else:
            tipo = "ghost" if i % 2 == 0 else "real"
            if i > 100:
                tipo = "geobattery"
            lat_calc = float(np.sin(i / PHI) * 90.0)
            lon_calc = float(np.cos(i / PHI) * 180.0)
            matriz.append({
                "id": i,
                "tipo": tipo,
                "lat": lat_calc,
                "lon": lon_calc,
                "name": f"NODO_UVG_{i}",
                "region": "",
            })

    return matriz


MATRIZ_UVG_125 = _generar_matriz_125()

NODOS_POR_ID = {n["id"]: n for n in MATRIZ_UVG_125}


def nodo_mas_cercano(lat: float, lon: float) -> dict:
    """Find the nearest UVG node to given coordinates. O(n) in-memory lookup."""
    return min(
        MATRIZ_UVG_125,
        key=lambda n: (lat - n["lat"]) ** 2 + (lon - n["lon"]) ** 2,
    )
