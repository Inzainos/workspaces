"""El sistema observaba pero había dejado de recordar.

Medido el 2026-09-25 revisando la tubería entera:

    TBL_HISTORICO_SISMICO        (vivo, USGS)                último: hoy
    tbl_eventos_sismicos_fuente  (fuente de topología)       último: 15-sep
    tbl_historico_sismico_raw    (bloques hora × nodo)       último:  3-sep
    tbl_firma_eventos            (de donde salen las firmas) último:  3-sep

Los sismos seguían llegando y ninguno posterior al 3 de septiembre entraba en la
memoria: la tabla fuente solo se llenaba con `--refetch` (que nadie programó) y
los bloques solo se reconstruían si CAMBIABA la topología.
"""
import sqlite3

import pytest

from sentinel_omega.infrastructure.pipeline.mantenimiento import promover_eventos_vivos


@pytest.fixture
def db(tmp_path):
    ruta = tmp_path / "puente.db"
    conn = sqlite3.connect(ruta)
    conn.executescript("""
        CREATE TABLE TBL_HISTORICO_SISMICO (
            event_id TEXT, timestamp REAL, lat REAL, lon REAL,
            depth_km REAL, magnitude REAL, mag_type TEXT, region TEXT,
            source TEXT, created_at TEXT);
        CREATE TABLE tbl_eventos_sismicos_fuente (
            usgs_id TEXT PRIMARY KEY, time_utc TEXT NOT NULL, lat REAL NOT NULL,
            lon REAL NOT NULL, mag REAL NOT NULL, id_nodo INTEGER NOT NULL,
            topologia_version TEXT NOT NULL, updated_at TEXT);
        CREATE TABLE tbl_historico_sismico_raw (
            timestamp_blk TEXT NOT NULL, id_nodo INTEGER NOT NULL,
            sismo_count INTEGER DEFAULT 0, sismo_max_mag REAL DEFAULT 0.0,
            PRIMARY KEY (timestamp_blk, id_nodo));
    """)
    conn.commit()
    return str(ruta), conn


def _vivo(conn, event_id, ts, lat=19.4, lon=-99.1, mag=5.5):
    conn.execute(
        "INSERT INTO TBL_HISTORICO_SISMICO (event_id, timestamp, lat, lon, "
        "magnitude, source) VALUES (?,?,?,?,?,'USGS')",
        (event_id, ts, lat, lon, mag))
    conn.commit()


TS = 1790379581.0      # 2026-09-25 23:39:41 UTC


def test_el_evento_vivo_llega_a_la_tabla_fuente(db):
    ruta, conn = db
    _vivo(conn, "us6000txqi", TS)
    stats = promover_eventos_vivos(ruta)
    assert stats["eventos_nuevos"] == 1
    fila = conn.execute("SELECT usgs_id, mag, id_nodo FROM tbl_eventos_sismicos_fuente").fetchone()
    assert fila[0] == "us6000txqi" and fila[1] == 5.5
    assert fila[2] > 0, "se le asigna nodo con la geometría real"


def test_y_su_bloque_por_hora_queda_refrescado(db):
    ruta, conn = db
    _vivo(conn, "a", TS)
    _vivo(conn, "b", TS + 60, mag=6.1)      # misma hora, mismo nodo
    promover_eventos_vivos(ruta)
    fila = conn.execute(
        "SELECT timestamp_blk, sismo_count, sismo_max_mag FROM tbl_historico_sismico_raw"
    ).fetchone()
    assert fila[1] == 2 and fila[2] == pytest.approx(6.1)
    assert fila[0].endswith(":00"), "los bloques son por hora"


def test_no_duplica_lo_que_ya_estaba(db):
    ruta, conn = db
    _vivo(conn, "a", TS)
    assert promover_eventos_vivos(ruta)["eventos_nuevos"] == 1
    assert promover_eventos_vivos(ruta)["eventos_nuevos"] == 0
    assert conn.execute("SELECT COUNT(*) FROM tbl_eventos_sismicos_fuente").fetchone()[0] == 1


def test_nunca_borra_el_historico(db):
    # La reconstrucción de la cascada hace DELETE de toda la tabla. Esto es
    # incremental: 22 días de bloques viejos no se pueden perder por añadir uno.
    ruta, conn = db
    conn.execute("INSERT INTO tbl_historico_sismico_raw VALUES ('2026-09-03 21:00', 7, 3, 4.9)")
    conn.commit()
    _vivo(conn, "a", TS)
    promover_eventos_vivos(ruta)
    viejo = conn.execute(
        "SELECT sismo_count FROM tbl_historico_sismico_raw WHERE timestamp_blk='2026-09-03 21:00'"
    ).fetchone()
    assert viejo is not None and viejo[0] == 3


def test_un_evento_sin_coordenadas_no_entra(db):
    ruta, conn = db
    conn.execute("INSERT INTO TBL_HISTORICO_SISMICO (event_id, timestamp, magnitude) "
                 "VALUES ('sin_coords', ?, 5.0)", (TS,))
    conn.commit()
    assert promover_eventos_vivos(ruta)["eventos_nuevos"] == 0


def test_una_marca_de_tiempo_rota_se_cuenta_y_no_revienta(db):
    ruta, conn = db
    _vivo(conn, "bueno", TS)
    conn.execute("INSERT INTO TBL_HISTORICO_SISMICO (event_id, timestamp, lat, lon, "
                 "magnitude) VALUES ('roto', 'no es una fecha', 1.0, 1.0, 5.0)")
    conn.commit()
    stats = promover_eventos_vivos(ruta)
    assert stats["eventos_nuevos"] == 1 and stats["omitidos"] == 1


def test_en_seco_no_escribe_nada(db):
    ruta, conn = db
    _vivo(conn, "a", TS)
    stats = promover_eventos_vivos(ruta, dry_run=True)
    assert stats["eventos_nuevos"] == 1
    assert conn.execute("SELECT COUNT(*) FROM tbl_eventos_sismicos_fuente").fetchone()[0] == 0


def test_sin_las_tablas_no_revienta(tmp_path):
    ruta = tmp_path / "vacia.db"
    sqlite3.connect(ruta).close()
    assert promover_eventos_vivos(str(ruta))["eventos_nuevos"] == 0


def test_en_seco_informa_los_bloques_que_refrescaria(db):
    # Sin esto el modo en seco decía «0 bloques», porque los contaba desde una
    # tabla en la que aún no había escrito nada.
    ruta, conn = db
    _vivo(conn, "a", TS)
    _vivo(conn, "b", TS + 7200, lat=-33.0, lon=-70.0)   # otra hora y otro nodo
    stats = promover_eventos_vivos(ruta, dry_run=True)
    assert stats["eventos_nuevos"] == 2
    assert stats["bloques_refrescados"] == 2
    assert conn.execute("SELECT COUNT(*) FROM tbl_historico_sismico_raw").fetchone()[0] == 0
