"""Catalogo USGS en una sola tabla, una fila por id.

La peticion es format=geojson. Si el conteo pasa de 20000, USGS responde
400: se parte la ventana en el tiempo, nunca por profundidad. La profundidad
va en la tercera coordenada. Vacio queda NULL. Un 0 se queda 0.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

LIMITE_USGS = 20000
# Mismo corte que precursor_types.detect_tsunami_potential (depth_km < 70).
CORTE_PROFUNDIDAD_KM = 70.0

COLUMNAS_NUEVAS = (
    ("depth_km", "REAL"),
    ("mag_type", "TEXT"),
    ("event_type", "TEXT"),
    ("place", "TEXT"),
    ("status", "TEXT"),
    ("tsunami", "INTEGER"),
    ("alert", "TEXT"),
    ("mmi", "REAL"),
    ("cdi", "REAL"),
    ("felt", "INTEGER"),
    ("sig", "INTEGER"),
    ("segmento", "TEXT"),
)


def segmento_de(depth_km):
    if depth_km is None:
        return None
    if depth_km < CORTE_PROFUNDIDAD_KM:
        return "corteza"
    return "profundo"


def _texto(valor):
    if valor is None:
        return None
    if isinstance(valor, str) and valor.strip() == "":
        return None
    return str(valor)


def _numero(valor, entero=False):
    if valor is None or valor == "":
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    if entero:
        return int(numero)
    return numero


def _time_utc(ms):
    ms = int(ms)
    segundos, resto = divmod(ms, 1000)
    momento = datetime.fromtimestamp(segundos, tz=timezone.utc).replace(
        microsecond=resto * 1000
    )
    return momento.strftime("%Y-%m-%d %H:%M:%S.%f")


def fila_de_feature(feature):
    """Una fila, o None si falta id, coordenada o magnitud."""
    if not isinstance(feature, dict):
        return None
    usgs_id = feature.get("id")
    if not usgs_id:
        return None
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    lon = _numero(coords[0])
    lat = _numero(coords[1])
    mag = _numero(props.get("mag"))
    cuando = props.get("time")
    if lon is None or lat is None or mag is None or cuando is None:
        return None
    if len(coords) >= 3:
        depth_km = _numero(coords[2])
    else:
        depth_km = None
    return {
        "usgs_id": str(usgs_id),
        "time_utc": _time_utc(cuando),
        "lat": lat,
        "lon": lon,
        "mag": mag,
        "depth_km": depth_km,
        "mag_type": _texto(props.get("magType")),
        "event_type": _texto(props.get("type")),
        "place": _texto(props.get("place")),
        "status": _texto(props.get("status")),
        "tsunami": _numero(props.get("tsunami"), entero=True),
        "alert": _texto(props.get("alert")),
        "mmi": _numero(props.get("mmi")),
        "cdi": _numero(props.get("cdi")),
        "felt": _numero(props.get("felt"), entero=True),
        "sig": _numero(props.get("sig"), entero=True),
        "segmento": segmento_de(depth_km),
    }


def _iso(momento):
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _partir(inicio, fin):
    if fin - inicio <= timedelta(milliseconds=1):
        raise RuntimeError("la ventana USGS no se puede partir mas")
    medio = inicio + (fin - inicio) / 2
    derecha = medio + timedelta(milliseconds=1)
    if derecha > fin:
        raise RuntimeError("la ventana USGS no se puede partir mas")
    return medio, derecha


def _params(inicio, fin, minmagnitude):
    return {
        "starttime": _iso(inicio),
        "endtime": _iso(fin),
        "minmagnitude": str(minmagnitude),
    }


def descargar_rango(inicio, fin, minmagnitude, pedir, limite=LIMITE_USGS):
    """Pide el conteo. Solo parte el tiempo si el conteo pasa de 20000.

    Un 429, un 500 o cualquier status distinto de 200 detiene la bajada.
    No se reintenta partiendo la ventana.
    """
    if fin <= inicio:
        raise ValueError("ventana vacia")
    base = _params(inicio, fin, minmagnitude)
    status, body = pedir("count", dict(base))
    if status != 200:
        raise RuntimeError(f"USGS count respondio {status}")
    total = int(str(body).strip() or "0")
    if total <= 0:
        return []
    if total > limite:
        medio, derecha = _partir(inicio, fin)
        return _unir(
            descargar_rango(inicio, medio, minmagnitude, pedir, limite)
            + descargar_rango(derecha, fin, minmagnitude, pedir, limite)
        )
    consulta = dict(base)
    consulta["format"] = "geojson"
    consulta["limit"] = str(limite)
    consulta["orderby"] = "time-asc"
    status, body = pedir("query", consulta)
    if status == 204 or not str(body).strip():
        return []
    if status != 200:
        raise RuntimeError(f"USGS query respondio {status}")
    features = json.loads(body).get("features") or []
    filas = []
    for feature in features:
        fila = fila_de_feature(feature)
        if fila is not None:
            filas.append(fila)
    return _unir(filas)


def descargar_anio(year, minmagnitude, pedir, limite=LIMITE_USGS):
    inicio = datetime(year, 1, 1, tzinfo=timezone.utc)
    fin = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    return descargar_rango(inicio, fin, minmagnitude, pedir, limite)


def _unir(filas):
    por_id = {}
    for fila in filas:
        por_id[fila["usgs_id"]] = fila
    return list(por_id.values())


def pedir_http(metodo, params, timeout=90):
    import requests

    url = f"https://earthquake.usgs.gov/fdsnws/event/1/{metodo}"
    respuesta = requests.get(url, params=params, timeout=timeout)
    return respuesta.status_code, respuesta.text


def asegurar_columnas(conn):
    tienen = {fila[1] for fila in conn.execute("PRAGMA table_info(tbl_eventos_sismicos_fuente)")}
    for nombre, tipo in COLUMNAS_NUEVAS:
        if nombre not in tienen:
            conn.execute(
                f"ALTER TABLE tbl_eventos_sismicos_fuente ADD COLUMN {nombre} {tipo}"
            )


def upsert_fila(conn, fila, id_nodo, topologia_version):
    conn.execute(
        """INSERT INTO tbl_eventos_sismicos_fuente
           (usgs_id, time_utc, lat, lon, mag, id_nodo, topologia_version,
            depth_km, mag_type, event_type, place, status, tsunami, alert,
            mmi, cdi, felt, sig, segmento)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(usgs_id) DO UPDATE SET
               time_utc=excluded.time_utc,
               lat=excluded.lat, lon=excluded.lon, mag=excluded.mag,
               id_nodo=excluded.id_nodo,
               topologia_version=excluded.topologia_version,
               depth_km=excluded.depth_km,
               mag_type=excluded.mag_type,
               event_type=excluded.event_type,
               place=excluded.place,
               status=excluded.status,
               tsunami=excluded.tsunami,
               alert=excluded.alert,
               mmi=excluded.mmi,
               cdi=excluded.cdi,
               felt=excluded.felt,
               sig=excluded.sig,
               segmento=excluded.segmento,
               updated_at=datetime('now')""",
        (
            fila["usgs_id"], fila["time_utc"], fila["lat"], fila["lon"], fila["mag"],
            id_nodo, topologia_version, fila["depth_km"], fila["mag_type"],
            fila["event_type"], fila["place"], fila["status"], fila["tsunami"],
            fila["alert"], fila["mmi"], fila["cdi"], fila["felt"], fila["sig"],
            fila["segmento"],
        ),
    )
