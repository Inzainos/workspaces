"""
Static UVG-125 Node Matrix — loaded into RAM at import time.

The 125 nodes de la malla N-Body usan coordenadas geograficas REALES,
tomadas de la unica fuente de verdad topologica: SEED_NODOS
(infrastructure/database/seed_nodos.py).

CAMBIO v2.5.2 (10-13 ago 2026) — FIX CRITICO DE LOCALIZACION:
Version anterior generaba 102 de los 125 nodos con coordenadas
matematicas ficticias (lat = sin(i/PHI)*90, lon = cos(i/PHI)*180),
sin relacion alguna con geografia real. Confirmado en produccion:
el sismo real M7.4 de Choco, Colombia (2026-08-10) fue asignado
al nodo "Chiapas Subduccion" (Mexico, ~1700km de error) en vez del
nodo real mas cercano ("Colombia-Ecuador", ~350km), porque ese nodo
(id=30) no tenia coordenadas reales en el motor de calculo.

Este archivo ahora importa SEED_NODOS directamente — una sola fuente
de verdad para topologia, compartida entre el motor de calculo y los
reportes. Ya no hay generacion procedural de coordenadas fantasma.

Layout (heredado de SEED_NODOS, ver seed_nodos.py):
  - Nodes 1-50: Real (major seismic zones, volcanic centers, subduction zones)
  - Nodes 51-100: Ghost (shadow nodes inferred from geodynamic gaps)
  - Nodes 101-125: Geobattery (electrochemical accumulation zones)
  - Node 0: Observation point (Tlaxcala — asynchronous, does not affect Euler sum)
"""

import math
from functools import lru_cache

import numpy as np

from sentinel_omega.infrastructure.database.seed_nodos import SEED_NODOS

PHI = (1 + np.sqrt(5)) / 2  # Se conserva por compatibilidad con otros modulos que la importen de aqui.
RADIO_TERRESTRE_KM = 6371.0

NODO_OBSERVACION = {
    "id": 0,
    "tipo": "observacion",
    "lat": 19.3182,
    "lon": -98.2375,
    "name": "TLAXMASTER",
    "region": "Mexico",
    "conductividad": None,
}


def _generar_matriz_125() -> list:
    """Construye la matriz 125+1 en RAM a partir de SEED_NODOS (coordenadas reales).

    Ya no hay rama procedural con formula aurea. Cada uno de los 125 nodos
    usa exactamente la misma lat/lon/tipo/region que ve el pipeline de
    reportes (estado/), garantizando que el motor de calculo y los reportes
    hablen siempre de la misma geografia para el mismo id de nodo.
    """
    matriz = [NODO_OBSERVACION]

    seed_por_id = {n["node_id"]: n for n in SEED_NODOS}

    if len(seed_por_id) != 125:
        raise ValueError(
            f"SEED_NODOS debe tener exactamente 125 nodos, encontrados: {len(seed_por_id)}"
        )

    for i in range(1, 126):
        if i not in seed_por_id:
            raise KeyError(f"Falta node_id={i} en SEED_NODOS — matriz de topologia incompleta.")
        nodo = seed_por_id[i]
        matriz.append({
            "id": i,
            "tipo": nodo["tipo"],
            "lat": nodo["lat"],
            "lon": nodo["lon"],
            "name": nodo["nombre"],
            "region": nodo.get("region", ""),
            "conductividad": nodo.get("conductividad"),
        })

    return matriz


MATRIZ_UVG_125 = _generar_matriz_125()

NODOS_POR_ID = {n["id"]: n for n in MATRIZ_UVG_125}


# Coordenadas de los 125 nodos en radianes, una sola vez. El haversine se
# evalúa vectorizado sobre los 125 de golpe: `nodo_mas_cercano` se llama
# cientos de miles de veces en un backcast, y un bucle de Python con trig por
# nodo multiplicaría el coste del rebuild.
_LAT_RAD = np.radians(np.array([n["lat"] for n in MATRIZ_UVG_125], dtype=float))
_LON_RAD = np.radians(np.array([n["lon"] for n in MATRIZ_UVG_125], dtype=float))
_COS_LAT = np.cos(_LAT_RAD)

def distancias_a_nodos(lat: float, lon: float) -> "np.ndarray":
    """Distancia haversine en km desde (lat, lon) a cada uno de los 125 nodos.

    Reutiliza `RADIO_TERRESTRE_KM`, que ya existía en este módulo: dos radios
    distintos en el mismo archivo son una contradicción esperando a confundir.
    """
    p = math.radians(float(lat))
    dphi = _LAT_RAD - p
    dlam = _LON_RAD - math.radians(float(lon))
    h = (np.sin(dphi / 2.0) ** 2
         + math.cos(p) * _COS_LAT * np.sin(dlam / 2.0) ** 2)
    return 2.0 * RADIO_TERRESTRE_KM * np.arcsin(np.sqrt(h))


@lru_cache(maxsize=65536)
def _indice_mas_cercano(lat: float, lon: float) -> int:
    return int(np.argmin(distancias_a_nodos(lat, lon)))


def nodo_mas_cercano(lat: float, lon: float) -> dict:
    """El nodo UVG más cercano a unas coordenadas, por distancia HAVERSINE.

    Usaba `(lat-n.lat)**2 + (lon-n.lon)**2` --- euclidiana en GRADOS --- y su
    propio docstring reconocía la deuda: «si se requiere precisión geodésica
    real, evaluar migrar a haversine en un parche separado». Este es ese parche.

    Por qué no era un detalle: un grado de longitud mide 111 km en el ecuador y
    se encoge con el coseno de la latitud, así que la euclidiana sobrepondera
    las diferencias de longitud y elige mal cuanto más lejos del ecuador.
    Medido el 2026-10-01 sobre los 4.378 sismos de `TBL_HISTORICO_SISMICO`:

        mapean a nodo DISTINTO     352  (8,0 %)
        exceso de distancia        mediana 270 km · p90 724 km · max 2.359 km

    El peor caso es un M4.6 en (-53,21 · 23,50): la euclidiana lo asignaba a
    «Ghost East Africa Rift» a 5.700 km teniendo «Ghost Scotia Arc» a 3.341 km.

    Va necesariamente CON un rebuild: `entrenamiento.py` y `backcast.py` mapean
    cada evento a su nodo al extraer la firma, así que cambiar la métrica sin
    reconstruir deja las firmas viejas colgadas de un nodo y las nuevas de otro.

    Ojo con lo que esto NO arregla: la malla no tiene nodos polares, así que
    incluso el haversine deja 3.341 km al más cercano en el Océano Austral. La
    métrica ya es correcta; la cobertura sigue siendo gruesa.
    """
    return MATRIZ_UVG_125[_indice_mas_cercano(float(lat), float(lon))]
