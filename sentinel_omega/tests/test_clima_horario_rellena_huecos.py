"""Una hora escrita sin Kp no puede quedarse sin Kp para siempre.

Hallado el 2026-10-01 tirando del hilo de `NOAA Kp fetch failed` en el log.
El error intermitente resultó ser lo de menos; debajo había dos defectos que se
multiplicaban:

  1. **`fetch_kp_index(days=...)` era un parámetro MUERTO.** La firma decía
     `days: int = 30`, el cuerpo nunca lo leía y la URL es fija. `data_pipeline`
     lo llamaba con `days=2` para armar las filas horarias de
     `tbl_clima_espacial_raw`: pedía 48 h y recibía **5 h 57 min** (358
     registros, medido), porque `planetary_k_index_1m.json` es de 1 minuto.

  2. **`INSERT OR IGNORE` hacía permanente el hueco.** El omni window llega
     mucho más atrás que esas ~6 h, así que las horas viejas del lote se
     escribían con `kp_promedio`/`kp_max` en NULL --- lo correcto, cero
     sintético --- y al ciclo siguiente, que YA traía el Kp de esas horas, se
     le descartaba la fila entera por tener la clave.

Medido en producción ese día, desde que el ciclo vivo escribe (2026-09-11):

    23 de 347 horas con Bz real y Kp NULO      6,6 %
    170 de 347 horas sin flujo de protones    49,0 %

El arreglo es un UPSERT con `COALESCE(col, excluded.col)`: rellena donde había
NULL y no pisa lo ya medido. Cura cualquier fallo transitorio de fuente, no
solo el del Kp.
"""
import sqlite3

import pytest

DDL = """
CREATE TABLE tbl_clima_espacial_raw (
    timestamp_blk    TEXT PRIMARY KEY,
    bz_promedio     REAL,
    bz_derivada     REAL,
    bz_min          REAL,
    bz_max          REAL,
    viento_solar_avg REAL,
    viento_solar_max REAL,
    kp_max          REAL,
    kp_promedio     REAL,
    proton_flux_10mev REAL
)
"""

# El orden de `_filas_clima_horarias`: ts + las nueve columnas.
#            ts      bz_prom bz_der bz_min bz_max v_avg v_max kp_max kp_prom prot
FILA_SIN_KP = ["2026-09-23 15:00", 5.04, 0.1, 1.0, 9.0, 420.0, 500.0, None, None, None]
FILA_CON_KP = ["2026-09-23 15:00", 5.04, 0.1, 1.0, 9.0, 420.0, 500.0, 4.0, 2.33, 0.29]


class _RepoFalso:
    """Lo mínimo que usa `_persist_clima`: `_execute` y `_executemany`."""

    def __init__(self, conn):
        self.conn = conn

    def _execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def _executemany(self, sql, filas):
        cur = self.conn.executemany(sql, filas)
        self.conn.commit()
        return cur


@pytest.fixture
def runner_y_base(tmp_path):
    """El runner REAL con un repo de prueba: se ejercita su SQL, no una copia.

    Construir una copia del UPSERT en el test lo volvería una prueba falsa ---
    pasaría aunque el código de producción siguiera en `INSERT OR IGNORE`.
    """
    from sentinel_omega.infrastructure.pipeline.layer_runners import (
        GeodynamicLayerRunner,
    )

    conn = sqlite3.connect(tmp_path / "clima.db")
    conn.execute(DDL)
    conn.commit()
    runner = object.__new__(GeodynamicLayerRunner)
    runner._repo = _RepoFalso(conn)
    return runner, conn


def _fila(conn, ts="2026-09-23 15:00"):
    return conn.execute(
        "SELECT kp_promedio, kp_max, proton_flux_10mev, bz_promedio "
        "FROM tbl_clima_espacial_raw WHERE timestamp_blk = ?", (ts,)
    ).fetchone()


def test_el_hueco_de_kp_se_rellena_en_el_ciclo_siguiente(runner_y_base):
    """El caso que costó 23 horas de Kp: primero llega sin Kp (el feed solo
    cubre ~6 h), después llega con él."""
    runner, conn = runner_y_base
    runner._persist_clima({"clima_horas": [list(FILA_SIN_KP)]})
    assert _fila(conn)[:3] == (None, None, None), "la hora debió entrar sin Kp"

    runner._persist_clima({"clima_horas": [list(FILA_CON_KP)]})
    kp_prom, kp_max, prot, _ = _fila(conn)
    assert (kp_prom, kp_max, prot) == (2.33, 4.0, 0.29), (
        "el hueco no se rellenó: el UPSERT volvió a ser un OR IGNORE")


def test_no_se_pisa_un_valor_ya_medido(runner_y_base):
    """Lo contrario también importa: un dato bueno no se sobreescribe, ni con
    otro dato bueno. La tabla es append-only en espíritu."""
    runner, conn = runner_y_base
    runner._persist_clima({"clima_horas": [list(FILA_CON_KP)]})
    otro = list(FILA_CON_KP)
    otro[8] = 9.99   # kp_promedio distinto
    otro[1] = 111.0  # bz_promedio distinto
    runner._persist_clima({"clima_horas": [otro]})
    kp_prom, _, _, bz = _fila(conn)
    assert kp_prom == 2.33, "pisó el Kp ya medido"
    assert bz == 5.04, "pisó el Bz ya medido"


def test_un_nulo_posterior_no_borra_un_dato_bueno(runner_y_base):
    """La trampa del UPSERT mal escrito: si el ciclo siguiente trae NULL porque
    la fuente cayó, no puede vaciar lo que ya estaba medido."""
    runner, conn = runner_y_base
    runner._persist_clima({"clima_horas": [list(FILA_CON_KP)]})
    runner._persist_clima({"clima_horas": [list(FILA_SIN_KP)]})
    kp_prom, kp_max, prot, _ = _fila(conn)
    assert (kp_prom, kp_max, prot) == (2.33, 4.0, 0.29), (
        "un NULL posterior borró dato real")


def test_una_hora_nueva_sigue_entrando(runner_y_base):
    """Control: el UPSERT no puede dejar de insertar lo que no existía."""
    runner, conn = runner_y_base
    runner._persist_clima({"clima_horas": [list(FILA_CON_KP)]})
    nueva = list(FILA_CON_KP)
    nueva[0] = "2026-09-23 16:00"
    runner._persist_clima({"clima_horas": [nueva]})
    assert conn.execute(
        "SELECT COUNT(*) FROM tbl_clima_espacial_raw").fetchone()[0] == 2


def test_fetch_kp_index_ya_no_finge_aceptar_una_ventana():
    """Regla dura 9 --- el índice/parámetro se verifica contra el dato.

    `days` existía en la firma, no en el cuerpo, y la URL es fija: pedir 48 h
    devolvía 6. Si alguien lo vuelve a añadir sin hacerlo real, que falle aquí.
    """
    import inspect

    from sentinel_omega.infrastructure.api import noaa

    firma = inspect.signature(noaa.fetch_kp_index)
    assert "days" not in firma.parameters, (
        "volvió `days` a fetch_kp_index: este endpoint sirve ~6 h a 1 min y no "
        "puede honrar una ventana. Para historia larga usa "
        "api.gfz_kp.fetch_kp_history")


def test_nadie_vuelve_a_pedirle_una_ventana_al_feed_corto():
    """El defecto vivía en el CALL SITE, no en la función. Esta prueba mira
    ahí: `data_pipeline` pedía `days=2` y recibía 6 h en silencio."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import data_pipeline

    fuente = inspect.getsource(data_pipeline)
    assert "fetch_kp_index(days" not in fuente, (
        "alguien volvió a pedirle una ventana a fetch_kp_index")
