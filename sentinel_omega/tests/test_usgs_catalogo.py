"""Segmento y peticion USGS, sin red y sin la base viva."""
import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from sentinel_omega.infrastructure.pipeline.usgs_catalogo import (
    asegurar_columnas,
    descargar_rango,
    fila_de_feature,
    upsert_fila,
)


def feature(usgs_id, lon, lat, depth, mag=5.0, cuando=1_700_000_000_000, **props):
    coordinates = [lon, lat] if depth is None else [lon, lat, depth]
    properties = {"mag": mag, "time": cuando, "type": "earthquake"}
    properties.update(props)
    return {
        "id": usgs_id,
        "properties": properties,
        "geometry": {"type": "Point", "coordinates": coordinates},
    }


class Segmento(unittest.TestCase):
    def test_profundidades(self):
        casos = [
            (99, "profundo", 99),
            (70, "profundo", 70),
            (20, "corteza", 20),
            (0, "corteza", 0),
        ]
        for depth, segmento, guardado in casos:
            fila = fila_de_feature(feature("us1", -99, 19, depth))
            self.assertEqual(fila["segmento"], segmento)
            self.assertEqual(fila["depth_km"], guardado)

    def test_sin_profundidad_queda_null(self):
        fila = fila_de_feature(feature("us1", -99, 19, None))
        self.assertIsNone(fila["depth_km"])
        self.assertIsNone(fila["segmento"])

    def test_cero_no_se_vuelve_null(self):
        fila = fila_de_feature(
            feature("us1", -99, 19, 0, tsunami=0, felt=0, sig=0, mmi=0)
        )
        self.assertEqual(fila["tsunami"], 0)
        self.assertEqual(fila["felt"], 0)
        self.assertEqual(fila["sig"], 0)
        self.assertEqual(fila["mmi"], 0.0)

    def test_vacio_queda_null(self):
        fila = fila_de_feature(
            feature("us1", -99, 19, 10, place="", alert=None, magType="")
        )
        self.assertIsNone(fila["place"])
        self.assertIsNone(fila["alert"])
        self.assertIsNone(fila["mag_type"])

    def test_sin_magnitud_no_entra(self):
        self.assertIsNone(fila_de_feature(feature("us1", -99, 19, 10, mag=None)))


def _catalogo(eventos, limite_query=None):
    """eventos: lista de (id, datetime, feature)."""

    def pedir(metodo, params):
        if "mindepth" in params or "maxdepth" in params:
            raise AssertionError("la peticion no se parte por profundidad")
        inicio = datetime.strptime(params["starttime"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        fin = datetime.strptime(params["endtime"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        dentro = [ev for ev in eventos if inicio <= ev[1] <= fin]
        if metodo == "count":
            return 200, str(len(dentro))
        if limite_query is not None and len(dentro) > limite_query:
            return 400, "over limit"
        return 200, json.dumps({"features": [ev[2] for ev in dentro]})

    return pedir


class Particion(unittest.TestCase):
    def test_parte_el_tiempo_y_no_duplica_el_borde(self):
        base = datetime(2020, 1, 1, tzinfo=timezone.utc)
        momentos = [base, base + timedelta(hours=12), base + timedelta(hours=24)]
        eventos = []
        for i, momento in enumerate(momentos):
            ms = int(momento.timestamp() * 1000)
            eventos.append((f"us{i}", momento, feature(f"us{i}", -100, 20, 15, cuando=ms)))
        filas = descargar_rango(
            base,
            base + timedelta(hours=24),
            4.5,
            _catalogo(eventos, limite_query=2),
            limite=2,
        )
        self.assertEqual(sorted(f["usgs_id"] for f in filas), ["us0", "us1", "us2"])


class Errores(unittest.TestCase):
    def test_500_y_429_paran(self):
        inicio = datetime(2020, 1, 1, tzinfo=timezone.utc)
        fin = inicio + timedelta(days=1)

        def count_500(metodo, params):
            return 500, "no"

        with self.assertRaises(RuntimeError):
            descargar_rango(inicio, fin, 4.5, count_500, limite=2)

        def query_429(metodo, params):
            if metodo == "count":
                return 200, "1"
            return 429, "slow"

        with self.assertRaises(RuntimeError):
            descargar_rango(inicio, fin, 4.5, query_429, limite=2)


class Tabla(unittest.TestCase):

    def test_una_fila_por_id(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE tbl_eventos_sismicos_fuente (
                usgs_id TEXT PRIMARY KEY, time_utc TEXT NOT NULL,
                lat REAL NOT NULL, lon REAL NOT NULL, mag REAL NOT NULL,
                id_nodo INTEGER NOT NULL, topologia_version TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')))"""
        )
        asegurar_columnas(conn)
        asegurar_columnas(conn)
        fila = fila_de_feature(feature("us1", -99.1, 19.2, 110, tsunami=0, place="Oaxaca"))
        upsert_fila(conn, fila, 7, "v1")
        fila["mag"] = 5.5
        upsert_fila(conn, fila, 8, "v2")
        conn.commit()
        total, tsunami, segmento, nodo = conn.execute(
            "SELECT COUNT(*), tsunami, segmento, id_nodo FROM tbl_eventos_sismicos_fuente"
        ).fetchone()
        self.assertEqual(total, 1)
        self.assertEqual(tsunami, 0)
        self.assertEqual(segmento, "profundo")
        self.assertEqual(nodo, 8)


if __name__ == "__main__":
    unittest.main()
