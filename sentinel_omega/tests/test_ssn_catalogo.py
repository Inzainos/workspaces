"""Tests del loader SSN Mexico (sin red, DB temporal)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sentinel_omega.infrastructure.pipeline.ssn_catalogo import (
    DEFAULT_MIN_MAG,
    build_parser,
    cargar_ssn,
    detectar_encoding_ssn,
    leer_catalogo_ssn,
    make_ssnmx_id,
    parse_ssn_time_utc,
)
from sentinel_omega.infrastructure.pipeline.usgs_catalogo import asegurar_columnas

CSV_FIXTURE = """\"Catalogo de sismos - Servicio Sismologico Nacional (SSN) | UNAM - Mexico. DOI: 10.21766/SSNMX/EC/MX\"
\"Informacion sujeta a cambios. Archivo generado el 2026-09-11 a las 02:48:39 (tiempo del centro de Mexico).\"
\"Sismicidad del 1994-01-01 al 2026-09-11, todas las magnitudes, todas las profundidades, en todo el pais.\"
\"Total: 3 eventos.\"
Fecha,Hora,Magnitud,Latitud,Longitud,Profundidad,Referencia de localizacion,Fecha UTC,Hora UTC,Estatus
1994-01-02,09:22:43,4.3,15.41,-97.35,20.0,\"59 km al SUROESTE de PUERTO ESCONDIDO, OAX\",1994-01-02,15:22:43,revisado
1994-01-04,13:06:30,3.9,18.91,-97.86,76.0,\"6 km al SUROESTE de LOS REYES DE JUAREZ, PUE\",1994-01-04,19:06:30,verificado
2000-06-15,12:00:00,5.1,16.10,-98.00,33.0,\"cerca de PINOTEPA, OAX\",2000-06-15,18:00:05,revisado
"""


def _crear_tabla(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE tbl_eventos_sismicos_fuente (
            usgs_id TEXT PRIMARY KEY,
            time_utc TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            mag REAL NOT NULL,
            id_nodo INTEGER NOT NULL,
            topologia_version TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    asegurar_columnas(conn)


def _escribir_csv(dirpath: Path) -> Path:
    path = dirpath / "ssnmx_tiny.csv"
    path.write_text(CSV_FIXTURE, encoding="utf-8")
    return path


class Parse(unittest.TestCase):
    def test_parse_salta_meta_y_lee_filas(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _escribir_csv(Path(tmp))
            filas, skipped = leer_catalogo_ssn(csv_path, min_mag=0.0)
            self.assertEqual(skipped, 0)
            self.assertEqual(len(filas), 3)
            self.assertEqual(filas[0]["mag"], 4.3)
            self.assertEqual(filas[0]["depth_km"], 20.0)
            self.assertEqual(filas[0]["status"], "revisado")
            self.assertTrue(filas[0]["ssnmx_id"].startswith("ssnmx:"))
            self.assertEqual(
                filas[0]["ssnmx_id"],
                "ssnmx:19940102T152243Z_15.4100_-97.3500_4.3",
            )
            self.assertEqual(filas[0]["segmento"], "corteza")
            self.assertEqual(filas[1]["segmento"], "profundo")

    def test_make_ssnmx_id_estable(self):
        momento = parse_ssn_time_utc("1994-01-02", "15:22:43")
        self.assertEqual(
            make_ssnmx_id(momento, 15.41, -97.35, 4.3),
            "ssnmx:19940102T152243Z_15.4100_-97.3500_4.3",
        )

    def test_default_min_mag_es_4_5(self):
        self.assertEqual(DEFAULT_MIN_MAG, 4.5)
        args = build_parser().parse_args(["--csv", "x.csv"])
        self.assertEqual(args.min_mag, 4.5)
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _escribir_csv(Path(tmp))
            filas, _ = leer_catalogo_ssn(csv_path)  # default 4.5
            self.assertEqual(len(filas), 1)
            self.assertEqual(filas[0]["mag"], 5.1)

    def test_latin1_acentos_en_place(self):
        # Fila con acentos típicos SSN (latin-1): localización / Acapulco
        meta = (
            '"meta1"\n"meta2"\n"meta3"\n"Total: 1"\n'
            "Fecha,Hora,Magnitud,Latitud,Longitud,Profundidad,"
            "Referencia de localizacion,Fecha UTC,Hora UTC,Estatus\n"
        )
        data_line = (
            '2001-01-01,10:00:00,4.8,16.85,-99.90,12.0,'
            '"15 km al SUROESTE de ACAPULCO, GRO",'
            "2001-01-01,16:00:00,revisado\n"
        )
        # Insert latin-1 bytes for "localización" style accent in place
        place_accent = '15 km al SUROESTE de ACAPULCO, GRO — Cerca de Coyuca'.encode(
            "latin-1", errors="replace"
        )
        # Rebuild with explicit latin-1 accented chars (ó = 0xF3)
        header = (
            "Fecha,Hora,Magnitud,Latitud,Longitud,Profundidad,"
            "Referencia de localizacion,Fecha UTC,Hora UTC,Estatus\n"
        ).encode("ascii")
        row = (
            b'2001-01-01,10:00:00,4.8,16.85,-99.90,12.0,'
            b'"15 km al SUROESTE de ACAPULCO, GRO",'
            b"2001-01-01,16:00:00,revisado\n"
        )
        # Accented place: "Cerca de Coyuca de Ben\xedtez" (í = 0xED in latin-1)
        row_accent = (
            b'2001-01-01,10:00:00,4.8,16.85,-99.90,12.0,'
            b'"15 km al SUROESTE de ACAPULCO, GRO - Ben'
            + bytes([0xED])
            + b'tez",'
            + b"2001-01-01,16:00:00,revisado\n"
        )
        body = (
            b'"meta1"\n"meta2"\n"meta3"\n"Total: 1"\n' + header + row_accent
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ssn_latin1.csv"
            path.write_bytes(body)
            self.assertEqual(detectar_encoding_ssn(path), "latin-1")
            filas, skipped = leer_catalogo_ssn(path, min_mag=0.0)
            self.assertEqual(skipped, 0)
            self.assertEqual(len(filas), 1)
            self.assertIn("Ben", filas[0]["place"] or "")
            self.assertIn("tez", filas[0]["place"] or "")
            # ó/í must survive (not replacement char from wrong encoding)
            self.assertIn("\xed", filas[0]["place"])


class MatchYInsert(unittest.TestCase):
    def test_match_update_conserva_usgs_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _escribir_csv(Path(tmp))
            conn = sqlite3.connect(":memory:")
            _crear_tabla(conn)
            # USGS cercano al primer evento SSN (±90s, ±0.25°, ±0.3 mag)
            # depth NULL → fill-only debe rellenar desde SSN
            conn.execute(
                """INSERT INTO tbl_eventos_sismicos_fuente
                   (usgs_id, time_utc, lat, lon, mag, id_nodo, topologia_version,
                    depth_km, place, status, event_type)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "us7000TEST",
                    "1994-01-02 15:22:50.000000",
                    15.40,
                    -97.34,
                    4.2,
                    7,
                    "v1",
                    None,
                    None,
                    "reviewed",
                    "earthquake",
                ),
            )
            conn.commit()

            def resolver(_lat, _lon):
                return 0, "pending_ssnmx"

            resumen = cargar_ssn(
                csv_path, conn, apply=True, min_mag=0.0, resolver_nodo=resolver
            )
            self.assertEqual(resumen["matched_update"], 1)
            self.assertEqual(resumen["inserted_ssnmx"], 2)
            self.assertEqual(resumen["errors"], 0)

            fila = conn.execute(
                "SELECT usgs_id, depth_km, place, status, id_nodo, segmento FROM "
                "tbl_eventos_sismicos_fuente WHERE usgs_id=?",
                ("us7000TEST",),
            ).fetchone()
            self.assertIsNotNone(fila)
            self.assertEqual(fila[0], "us7000TEST")
            self.assertEqual(fila[1], 20.0)  # fill desde SSN (era NULL)
            self.assertIn("PUERTO ESCONDIDO", fila[2] or "")
            self.assertEqual(fila[3], "revisado")
            self.assertEqual(fila[4], 7)
            self.assertEqual(fila[5], "corteza")

            ssn_ids = [
                r[0]
                for r in conn.execute(
                    "SELECT usgs_id FROM tbl_eventos_sismicos_fuente "
                    "WHERE usgs_id LIKE 'ssnmx:%' ORDER BY usgs_id"
                ).fetchall()
            ]
            self.assertEqual(len(ssn_ids), 2)
            for sid in ssn_ids:
                self.assertTrue(sid.startswith("ssnmx:"))
                self.assertFalse(sid.startswith("us"))

    def test_match_depth_fill_only_no_sobrescribe(self):
        """Si USGS ya tiene depth_km, MATCH no lo pisa; status sí se actualiza."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _escribir_csv(Path(tmp))
            conn = sqlite3.connect(":memory:")
            _crear_tabla(conn)
            conn.execute(
                """INSERT INTO tbl_eventos_sismicos_fuente
                   (usgs_id, time_utc, lat, lon, mag, id_nodo, topologia_version,
                    depth_km, place, status, event_type, segmento)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "us7000KEEP",
                    "1994-01-02 15:22:50.000000",
                    15.40,
                    -97.34,
                    4.2,
                    7,
                    "v1",
                    55.0,  # USGS depth ya presente
                    "USGS place kept",
                    "reviewed",
                    "earthquake",
                    "intermedio",
                ),
            )
            conn.commit()
            resumen = cargar_ssn(
                csv_path,
                conn,
                apply=True,
                min_mag=0.0,
                resolver_nodo=lambda lat, lon: (0, "pending_ssnmx"),
            )
            self.assertEqual(resumen["matched_update"], 1)
            fila = conn.execute(
                "SELECT depth_km, place, status, segmento FROM "
                "tbl_eventos_sismicos_fuente WHERE usgs_id=?",
                ("us7000KEEP",),
            ).fetchone()
            self.assertEqual(fila[0], 55.0)  # no sobrescrito por SSN 20.0
            self.assertEqual(fila[1], "USGS place kept")  # place fill-only
            self.assertEqual(fila[2], "revisado")  # status sí desde Estatus
            self.assertEqual(fila[3], "intermedio")  # segmento no cambiado

    def test_insert_usa_prefijo_ssnmx(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _escribir_csv(Path(tmp))
            conn = sqlite3.connect(":memory:")
            _crear_tabla(conn)

            resumen = cargar_ssn(
                csv_path,
                conn,
                apply=True,
                min_mag=0.0,
                resolver_nodo=lambda lat, lon: (0, "pending_ssnmx"),
                limit=1,
            )
            self.assertEqual(resumen["inserted_ssnmx"], 1)
            self.assertEqual(resumen["matched_update"], 0)
            usgs_id, mag_type, event_type, id_nodo, topo = conn.execute(
                "SELECT usgs_id, mag_type, event_type, id_nodo, topologia_version "
                "FROM tbl_eventos_sismicos_fuente"
            ).fetchone()
            self.assertTrue(usgs_id.startswith("ssnmx:"))
            self.assertEqual(mag_type, "ssn")
            self.assertEqual(event_type, "earthquake")
            self.assertEqual(id_nodo, 0)
            self.assertEqual(topo, "pending_ssnmx")


class DryRun(unittest.TestCase):
    def test_dry_run_no_escribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _escribir_csv(Path(tmp))
            conn = sqlite3.connect(":memory:")
            _crear_tabla(conn)
            resumen = cargar_ssn(
                csv_path,
                conn,
                apply=False,
                min_mag=0.0,
                resolver_nodo=lambda lat, lon: (0, "pending_ssnmx"),
            )
            self.assertEqual(resumen["read"], 3)
            self.assertEqual(resumen["inserted_ssnmx"], 3)
            self.assertFalse(resumen["apply"])
            total = conn.execute(
                "SELECT COUNT(*) FROM tbl_eventos_sismicos_fuente"
            ).fetchone()[0]
            self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
