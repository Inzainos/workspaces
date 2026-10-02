"""El lote no hace fsync; la ruta viva sí. Y eso no se puede invertir.

Cómo se encontró (2026-10-02)
-----------------------------
La misma Fase 2 tardó **14, >110 y 38 minutos** en tres corridas haciendo el
MISMO trabajo: 140.800 contra 140.613 evaluaciones, 0,1 % de diferencia. Se
descartaron por medición la E/S del proceso (94 % CPU, 0,58 MiB/s), la
competencia externa (carga 1,05 de 16 núcleos) y las estadísticas rancias
(`sqlite_stat1` decía 9 filas con 1.056.453, pero el plan de
`Juez.reincidencia` seguía siendo el correcto y tardaba 0,03 ms).

El perfil dijo dónde estaba:

    13.571 commits  =  207,6 s de 286,1 s  =  **73 %** del total
    4.523 evaluaciones -> 3,0 commits cada una

Tres commits por evaluación, uno en cada sitio y los tres correctos ahí:
`juez.registrar_prediccion`, `juez.evaluar_pendientes`, `pesos._ajustar`. En un
lote de 140.613 evaluaciones son **~420.000 fsync**.

    synchronous=FULL     6,83 ms/commit     <- el de la base
    synchronous=NORMAL   0,04 ms/commit     <- 170x

420.000 × 6,83 ms = 48 min de puro fsync, y la latencia del fsync es lo que
varía con la carga del disco. Ahí estaba la varianza.

A/B con el código real: **286,1 s -> 74,1 s, 3,9x**.

El canje
--------
Con WAL, `NORMAL` puede perder los últimos commits en un corte de luz o del
sistema operativo; **la base no se corrompe** y un fallo de la aplicación no
pierde nada. Un lote se vuelve a correr; un veredicto vivo perdido no se
recupera repitiendo nada. De ahí la asimetría que estas pruebas protegen.
"""
import sqlite3

import pytest

from sentinel_omega.infrastructure.database.schema import (
    ESPERA_CANDADO_S, conexion_de_lote,
)

NORMAL, FULL = 1, 2


def test_la_conexion_de_lote_no_hace_fsync(tmp_path):
    c = conexion_de_lote(str(tmp_path / "l.db"))
    assert c.execute("PRAGMA synchronous").fetchone()[0] == NORMAL
    c.close()


def test_la_conexion_de_lote_conserva_la_espera_del_candado(tmp_path):
    """El `busy_timeout` de 120 s se puso porque el mantenimiento nocturno
    competía con el launcher vivo. Bajar el fsync no puede costar eso."""
    c = conexion_de_lote(str(tmp_path / "l.db"))
    assert c.execute("PRAGMA busy_timeout").fetchone()[0] == int(
        ESPERA_CANDADO_S * 1000)
    c.close()


def test_el_lote_tiene_LA_MISMA_politica_que_la_ruta_viva(tmp_path):
    """El arreglo de verdad, y lo que esta prueba me enseñó al escribirla.

    Yo creía estar introduciendo un canje de durabilidad: «lote en NORMAL, vivo
    en FULL». Falso. La ruta viva (`get_connection`, vía el esquema expandido)
    lleva `synchronous=NORMAL` **desde siempre**; lo que pasaba es que los
    lotes abrían `sqlite3.connect` a pelo y heredaban el default de SQLite:

        sqlite3.connect pelado      synchronous = 2  (FULL)
        get_connection (ruta viva)  synchronous = 1  (NORMAL)

    Los lotes eran accidentalmente MÁS durables que el ciclo vivo y lo pagaban
    con un fsync por commit. El arreglo no afloja nada: alinea.

    Esta prueba compara las dos conexiones, así que también caza la duplicación
    de `PRAGMAS_RUNTIME`: si alguien cambia la política en un sitio y no en el
    otro, falla aquí.
    """
    from sentinel_omega.infrastructure.database.schema import get_connection

    viva = get_connection(str(tmp_path / "v.db"))
    lote = conexion_de_lote(str(tmp_path / "l.db"))
    for pragma in ("synchronous", "journal_mode", "cache_size", "temp_store"):
        pv = viva.execute(f"PRAGMA {pragma}").fetchone()[0]
        pl = lote.execute(f"PRAGMA {pragma}").fetchone()[0]
        assert pv == pl, (
            f"la política de '{pragma}' se separó: viva={pv!r} lote={pl!r}")
    viva.close()
    lote.close()


def test_sqlite3_pelado_sigue_dando_FULL(tmp_path):
    """La razón de que el ayudante exista, fijada: una conexión sin PRAGMA
    hereda FULL, y eso es lo que costaba 6,83 ms por commit."""
    c = sqlite3.connect(str(tmp_path / "pelada.db"))
    assert c.execute("PRAGMA synchronous").fetchone()[0] == FULL
    c.close()


def test_los_lotes_usan_el_ayudante_y_no_sqlite3_pelado():
    """Si alguien abre `sqlite3.connect` a mano en un lote, vuelve el fsync por
    commit y con él los 38 minutos."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import entrenamiento, mantenimiento

    for mod in (entrenamiento, mantenimiento):
        fuente = inspect.getsource(mod)
        assert "sqlite3.connect(db_path" not in fuente, (
            f"{mod.__name__} abre una conexión de lote a mano: usa "
            "conexion_de_lote(db_path)")
        assert "conexion_de_lote(db_path)" in fuente, mod.__name__


def test_normal_es_de_verdad_mas_rapido_que_full(tmp_path):
    """La medición, como prueba. No se afirma un factor exacto --- depende del
    disco ---, solo que FULL cuesta claramente más por commit.
    """
    import time

    tiempos = {}
    for modo in ("FULL", "NORMAL"):
        p = tmp_path / f"{modo}.db"
        c = sqlite3.connect(p)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute(f"PRAGMA synchronous={modo}")
        c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        c.commit()
        t0 = time.perf_counter()
        for _ in range(60):
            c.execute("INSERT INTO t (v) VALUES (?)", ("x" * 200,))
            c.commit()
        tiempos[modo] = time.perf_counter() - t0
        c.close()
    assert tiempos["NORMAL"] < tiempos["FULL"], tiempos


def test_la_base_puede_leerse_despues_de_un_lote(tmp_path):
    """Lo que NORMAL no puede romper: la integridad. Se escribe con la
    conexión de lote y se lee con otra."""
    ruta = str(tmp_path / "x.db")
    c = conexion_de_lote(ruta)
    c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v REAL)")
    c.executemany("INSERT INTO t (v) VALUES (?)", [(i * 1.5,) for i in range(500)])
    c.commit()
    c.close()

    d = sqlite3.connect(ruta)
    assert d.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 500
    assert d.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    d.close()
