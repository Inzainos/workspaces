"""La cuenta regresiva necesita un ancla que el rebuild no borre.

`format_lag_line` sabe restar el tiempo transcurrido al lag aprendido, pero se
anclaba en `tbl_cimatica_patrones.primera_vez`. Medido el 2026-09-27: **279.453
de 279.453 filas** con la fecha del rebuild --- el 100 %. Así que la cuenta
regresiva se reiniciaba al máximo cada vez que se reconstruía la memoria,
mostrando un número plausible que no medía nada.

`TBL_FIRMAS.primera_vista` tampoco sirve: guarda fechas reales (1994–2026) pero
es la primera vez HISTÓRICA, y restarle el transcurrido da «restan 0 h».

El ancla correcta es el instante en que la firma empezó a emparejar EN LA RACHA
ACTUAL --- dato vivo, que no existía. Pedido del operador: *«si se mantiene esa
firma se le iban restando horas»*.
"""
import sqlite3
import time

import pytest

from sentinel_omega.infrastructure.messaging.alert_enrichment import (
    ancla_de_racha_viva,
    format_lag_line,
)
from sentinel_omega.launcher import RACHA_TOLERANCIA_MIN, _registrar_racha_viva


@pytest.fixture
def base(tmp_path):
    conn = sqlite3.connect(tmp_path / "racha.db")
    conn.execute(
        "CREATE TABLE TBL_FIRMAS (firma_id TEXT PRIMARY KEY, bot_name TEXT, "
        "event_class TEXT, lag_promedio_h REAL, recurrencia INTEGER)"
    )
    conn.executemany(
        "INSERT INTO TBL_FIRMAS VALUES (?,?,?,?,?)",
        [("f1", "beta1", "SISMO_M5", 202.7, 3517),
         ("f2", "alfa1", "SISMO_M5", 96.0, 12),
         ("f3", "loki", "SISMO_M6", None, 5)],
    )
    conn.commit()
    return conn


def _racha(conn, fid):
    return conn.execute(
        "SELECT inicio_ts, ultimo_ts, ciclos FROM tbl_firma_racha_viva "
        "WHERE firma_id = ?", (fid,)).fetchone()


def test_el_primer_emparejamiento_abre_la_racha(base):
    _registrar_racha_viva(base, [{"firma_id": "f1"}])
    r = _racha(base, "f1")
    assert r is not None and r[2] == 1
    assert r[0] == r[1], "el inicio y el último deberían coincidir en el ciclo 1"


def test_mientras_se_mantiene_el_inicio_NO_se_mueve(base):
    """El corazón del arreglo: la racha conserva su origen, así que el tiempo
    transcurrido crece y las horas restantes bajan."""
    _registrar_racha_viva(base, [{"firma_id": "f1"}])
    inicio_1 = _racha(base, "f1")[0]
    time.sleep(1.1)
    _registrar_racha_viva(base, [{"firma_id": "f1"}])
    inicio_2, ultimo_2, ciclos = _racha(base, "f1")
    assert inicio_2 == inicio_1, "el inicio se movió: la cuenta se reiniciaría"
    assert ultimo_2 > inicio_1, "el último visto no avanzó"
    assert ciclos == 2


def test_si_la_firma_desaparece_y_vuelve_la_racha_se_reinicia(base):
    """Un hueco mayor que la tolerancia es una racha nueva, no la misma."""
    _registrar_racha_viva(base, [{"firma_id": "f1"}])
    viejo = f"-{RACHA_TOLERANCIA_MIN + 10} minutes"
    base.execute(
        "UPDATE tbl_firma_racha_viva SET inicio_ts = datetime('now', ?), "
        "ultimo_ts = datetime('now', ?) WHERE firma_id = 'f1'", (viejo, viejo))
    base.commit()
    _registrar_racha_viva(base, [{"firma_id": "f1"}])
    inicio, _, ciclos = _racha(base, "f1")
    assert ciclos == 1, "no reinició el contador tras el hueco"
    assert inicio > base.execute(
        "SELECT datetime('now','-1 minutes')").fetchone()[0], (
        "el inicio quedó en el pasado: la cuenta arrancaría ya agotada")


def test_el_ancla_trae_el_lag_DE_LA_FIRMA_no_el_de_la_clase(base):
    """f1 y f2 son de la misma clase con lags distintos (202,7 y 96). Gana la
    de racha más larga, con SU propio lag."""
    _registrar_racha_viva(base, [{"firma_id": "f1"}, {"firma_id": "f2"}])
    time.sleep(1.1)
    _registrar_racha_viva(base, [{"firma_id": "f1"}])   # f1 acumula un ciclo más
    inicio, lag, ciclos = ancla_de_racha_viva(base, "SISMO_M5")
    assert lag == 202.7, f"tomó otro lag: {lag}"
    assert ciclos == 2
    assert inicio is not None


def test_una_firma_sin_lag_no_sirve_de_ancla(base):
    """Sin tiempo de vida aprendido no hay nada que restar."""
    _registrar_racha_viva(base, [{"firma_id": "f3"}])
    assert ancla_de_racha_viva(base, "SISMO_M6") == (None, None, None)


def test_sin_tabla_no_revienta_y_cae_al_patron_cimatico(tmp_path):
    conn = sqlite3.connect(tmp_path / "vacia.db")
    conn.execute("CREATE TABLE TBL_FIRMAS (firma_id TEXT, event_class TEXT, "
                 "lag_promedio_h REAL, recurrencia INTEGER)")
    assert ancla_de_racha_viva(conn, "SISMO_M5") == (None, None, None)


def test_de_punta_a_punta_las_horas_bajan(base):
    """Lo que el operador verá: el mismo lag, menos horas restantes."""
    _registrar_racha_viva(base, [{"firma_id": "f1"}])
    base.execute("UPDATE tbl_firma_racha_viva "
                 "SET inicio_ts = datetime('now','-40 hours') "
                 "WHERE firma_id = 'f1'")
    base.commit()
    inicio, lag, ciclos = ancla_de_racha_viva(base, "SISMO_M5")
    linea = format_lag_line(lag, None, inicio, ciclos)
    assert "restan ~163 h" in linea, linea
    assert "~203 h" in linea, "se perdió el lag aprendido de la firma"


def test_sin_matches_no_escribe_nada(base):
    _registrar_racha_viva(base, [])
    tablas = base.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='tbl_firma_racha_viva'"
    ).fetchone()[0]
    assert tablas == 0, "creó la tabla sin necesidad"
