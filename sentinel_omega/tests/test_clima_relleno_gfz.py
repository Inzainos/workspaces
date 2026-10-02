"""El relleno de Kp desde GFZ: rellena hueco, y jamás pisa una medición.

Contexto (2026-10-01). Quedaron 23 horas con Bz real y Kp NULL cuando el
sistema volvió de estar apagado del 17 al 23 de septiembre: el primer ciclo
emitió el omni window hacia atrás hasta el 23-sep 15:00, el feed de Kp solo
cubre ~6 h, y el `INSERT OR IGNORE` congeló esos NULL. Son la huella del bug
que cerró `8a3eb99`.

NOAA ya no sirve esas fechas (6 h de Kp, 6 h de protones, 24 h de RTSW) y
`clima_gapfill_2026.py` lo dice en su propio comentario. GFZ Potsdam sirve 90
días, y el Kp **es por definición un índice de 3 horas**, así que asignar el
valor del bloque a sus tres horas no es interpolar: es el índice de ese periodo.

Lo que estas pruebas protegen es la parte peligrosa --- que un relleno nunca
sobreescriba un dato medido --- porque este guion escribe en la base de
producción.
"""
import sqlite3

import pandas as pd
import pytest

from sentinel_omega.infrastructure.pipeline import clima_relleno_gfz as crg

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

# Un bloque real de GFZ del tramo que se rellenó: 25-sep 09:00 UTC, Kp 4,0.
GFZ = pd.DataFrame({
    "time_tag": pd.to_datetime(["2026-09-25T09:00:00Z", "2026-09-25T12:00:00Z"],
                               utc=True),
    "kp_index": [4.0, 3.333],
})


@pytest.fixture
def base(tmp_path, monkeypatch):
    conn = sqlite3.connect(tmp_path / "c.db")
    conn.execute(DDL)
    conn.commit()
    monkeypatch.setattr(
        "sentinel_omega.infrastructure.api.gfz_kp.fetch_kp_history",
        lambda days=90: GFZ.copy())
    return conn


def _ins(conn, blk, bz=5.0, kp_prom=None, kp_max=None):
    conn.execute(
        "INSERT INTO tbl_clima_espacial_raw "
        "(timestamp_blk, bz_promedio, kp_promedio, kp_max) VALUES (?,?,?,?)",
        (blk, bz, kp_prom, kp_max))
    conn.commit()


def _kp(conn, blk):
    return conn.execute(
        "SELECT kp_promedio, kp_max FROM tbl_clima_espacial_raw "
        "WHERE timestamp_blk = ?", (blk,)).fetchone()


def test_el_bloque_de_tres_horas_cubre_sus_tres_horas(base):
    """Kp es un índice de bloque: 09:00, 10:00 y 11:00 toman el valor de 09:00."""
    for h in ("09", "10", "11"):
        _ins(base, f"2026-09-25 {h}:00")
    puestos, sin_cobertura = crg.rellenar(base, escribir=True)
    assert (puestos, sin_cobertura) == (3, 0)
    for h in ("09", "10", "11"):
        assert _kp(base, f"2026-09-25 {h}:00") == (4.0, 4.0)


def test_nunca_pisa_un_kp_ya_medido(base):
    """La garantía que importa: el guion escribe en producción."""
    _ins(base, "2026-09-25 09:00", kp_prom=1.11, kp_max=2.22)
    _ins(base, "2026-09-25 10:00")  # este sí está hueco
    crg.rellenar(base, escribir=True)
    assert _kp(base, "2026-09-25 09:00") == (1.11, 2.22), "pisó dato medido"
    assert _kp(base, "2026-09-25 10:00") == (4.0, 4.0)


def test_el_dry_run_no_escribe(base):
    _ins(base, "2026-09-25 09:00")
    puestos, _ = crg.rellenar(base, escribir=False)
    assert puestos == 1, "debió CONTAR la hora que rellenaría"
    assert _kp(base, "2026-09-25 09:00") == (None, None), "escribió en dry-run"


def test_una_hora_sin_bloque_que_la_cubra_se_queda_nula(base):
    """Cero sintético: fuera de la cobertura de GFZ no se inventa nada."""
    _ins(base, "2026-09-18 04:00")   # el apagón: GFZ de prueba no lo cubre
    puestos, sin_cobertura = crg.rellenar(base, escribir=True)
    assert (puestos, sin_cobertura) == (0, 1)
    assert _kp(base, "2026-09-18 04:00") == (None, None)


def test_no_toca_una_hora_sin_telemetria_real(base):
    """Una fila sin Bz no es un hueco de Kp: es una fila vacía, y rellenarle el
    Kp fabricaría una hora que el sistema nunca midió."""
    _ins(base, "2026-09-25 09:00", bz=None)
    puestos, _ = crg.rellenar(base, escribir=True)
    assert puestos == 0
    assert _kp(base, "2026-09-25 09:00") == (None, None)


def test_queda_rastro_de_procedencia(base):
    """Sin esto, el valor de GFZ sería indistinguible del de NOAA en un mes."""
    _ins(base, "2026-09-25 09:00")
    crg.rellenar(base, escribir=True)
    filas = base.execute(
        "SELECT columna, valor, fuente FROM tbl_clima_relleno_auditoria "
        "WHERE timestamp_blk = '2026-09-25 09:00' ORDER BY columna").fetchall()
    assert filas == [("kp_max", 4.0, crg.FUENTE),
                     ("kp_promedio", 4.0, crg.FUENTE)], filas


def test_una_segunda_pasada_no_cambia_nada(base):
    """Idempotente: correrlo dos veces no puede alterar lo ya escrito."""
    _ins(base, "2026-09-25 09:00")
    crg.rellenar(base, escribir=True)
    antes = _kp(base, "2026-09-25 09:00")
    puestos, _ = crg.rellenar(base, escribir=True)
    assert puestos == 0, "volvió a tratar como hueco algo ya relleno"
    assert _kp(base, "2026-09-25 09:00") == antes
