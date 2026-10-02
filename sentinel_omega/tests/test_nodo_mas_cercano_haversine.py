"""Un grado de longitud no mide lo mismo en el ecuador que a 53 grados sur.

`nodo_mas_cercano` elegía con `(lat-n.lat)**2 + (lon-n.lon)**2` --- euclidiana
en GRADOS --- y su propio docstring reconocía la deuda: «si se requiere
precisión geodésica real, evaluar migrar a haversine en un parche separado».

Por qué no era un detalle: un grado de longitud mide 111 km en el ecuador y se
encoge con el coseno de la latitud. La euclidiana sobrepondera la longitud, y
el error crece al alejarse del ecuador. Medido el 2026-10-01 sobre los 4.378
sismos de `TBL_HISTORICO_SISMICO`:

    mapean a nodo DISTINTO     352  (8,0 %)
    exceso de distancia        mediana 270 km · p90 724 km · max 2.359 km

Va CON un rebuild: `entrenamiento.py` y `backcast.py` mapean cada evento a su
nodo al extraer la firma, así que cambiar la métrica sin reconstruir dejaría
las firmas viejas colgadas de un nodo y las nuevas de otro.
"""
import math

import pytest

from sentinel_omega.core.shared.geometria_uvg import (
    MATRIZ_UVG_125, RADIO_TERRESTRE_KM, distancias_a_nodos, nodo_mas_cercano,
)


def _hav(a1, o1, a2, o2):
    """Haversine escrito aquí a mano, a propósito: si la prueba llamara a la
    del módulo, pasaría aunque las dos estuvieran mal igual."""
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = p2 - p1, math.radians(o2 - o1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TERRESTRE_KM * math.asin(math.sqrt(h))


def _euclidiana(lat, lon):
    """La métrica vieja, para poder exigir que el resultado CAMBIE."""
    return min(MATRIZ_UVG_125,
               key=lambda n: (lat - n["lat"]) ** 2 + (lon - n["lon"]) ** 2)


def test_el_peor_caso_medido_queda_corregido():
    """M4.6 en (-53,21 · 23,50), Océano Austral. La euclidiana lo mandaba al
    Rift de África Oriental, a 2.359 km más que el nodo real más cercano."""
    lat, lon = -53.21, 23.50
    viejo = _euclidiana(lat, lon)
    nuevo = nodo_mas_cercano(lat, lon)
    assert viejo["name"] == "Ghost East Africa Rift", (
        "cambió la malla: vuelve a medir el caso antes de confiar en esta prueba")
    assert nuevo["name"] == "Ghost Scotia Arc", nuevo
    d_viejo = _hav(lat, lon, viejo["lat"], viejo["lon"])
    d_nuevo = _hav(lat, lon, nuevo["lat"], nuevo["lon"])
    assert d_viejo - d_nuevo > 2000, (d_viejo, d_nuevo)


@pytest.mark.parametrize("lat,lon", [
    (19.3182, -98.2375),   # Tlaxcala, el punto de observación
    (-53.21, 23.50),       # Océano Austral, donde más duele
    (64.0, -21.0),         # Islandia
    (-17.7, 178.0),        # Fiyi, cruzando el antimeridiano
    (0.0, 0.0),            # ecuador y meridiano
    (-60.0, -179.5),       # justo al oeste del antimeridiano
])
def test_siempre_devuelve_el_minimo_real(lat, lon):
    """La propiedad que define la función: ningún nodo puede estar más cerca
    que el devuelto, medido con un haversine independiente."""
    elegido = nodo_mas_cercano(lat, lon)
    d_elegido = _hav(lat, lon, elegido["lat"], elegido["lon"])
    for n in MATRIZ_UVG_125:
        assert _hav(lat, lon, n["lat"], n["lon"]) >= d_elegido - 1e-6, (
            f"{n['name']} está más cerca que {elegido['name']}")


def test_la_matriz_de_125_tiene_126_entradas():
    """Sorpresa encontrada escribiendo estas pruebas, y conviene fijarla.

    `MATRIZ_UVG_125` son 50 reales + 50 ghost + 25 geobatería **+ el punto de
    observación de Tlaxcala (id 0)**, que `_generar_matriz_125` mete como
    primer elemento. Es de antes del haversine. Importa porque `nodo_mas_cercano`
    lo considera candidato: un sismo cerca de Tlaxcala puede quedar asignado al
    punto de OBSERVACIÓN, que según el propio módulo «does not affect Euler
    sum» --- o sea, no es un nodo de la malla.
    """
    por_tipo = {}
    for n in MATRIZ_UVG_125:
        por_tipo[n["tipo"]] = por_tipo.get(n["tipo"], 0) + 1
    assert len(MATRIZ_UVG_125) == 126, len(MATRIZ_UVG_125)
    assert por_tipo == {"observacion": 1, "real": 50,
                        "ghost": 50, "geobattery": 25}, por_tipo


def test_la_distancia_coincide_con_un_haversine_independiente():
    """`distancias_a_nodos` vectorizado contra el de a mano, nodo por nodo."""
    lat, lon = -33.45, -70.67     # Santiago de Chile
    d = distancias_a_nodos(lat, lon)
    assert len(d) == len(MATRIZ_UVG_125)
    for i, n in enumerate(MATRIZ_UVG_125):
        assert abs(d[i] - _hav(lat, lon, n["lat"], n["lon"])) < 1e-6, n["name"]


def test_la_longitud_pesa_menos_lejos_del_ecuador():
    """La razón de fondo, como prueba: a 60 grados de latitud, 10 grados de
    longitud son ~557 km, mientras 10 de latitud son ~1.112 km. La euclidiana
    en grados los trataba como iguales."""
    d_lon = _hav(60.0, 0.0, 60.0, 10.0)
    d_lat = _hav(60.0, 0.0, 70.0, 0.0)
    assert d_lat / d_lon > 1.9, (d_lat, d_lon)


def test_el_cache_no_cambia_la_respuesta():
    """Hay un lru_cache delante: la segunda llamada debe dar lo mismo."""
    for _ in range(3):
        assert nodo_mas_cercano(-53.21, 23.50)["id"] == 97


def test_devuelve_el_nodo_de_la_matriz_no_una_copia():
    """El llamador lee ['id'] y ['lat']: tiene que ser el nodo de verdad."""
    n = nodo_mas_cercano(19.3182, -98.2375)
    assert n is MATRIZ_UVG_125[[m["id"] for m in MATRIZ_UVG_125].index(n["id"])]
