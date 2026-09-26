"""El registro de escritura no puede comerse la base.

El 2026-09-25 el `-wal` de la base de producción llegó a **999,8 MB**, más que
la base misma. SQLite ya vuelca solo por encima de ~4 MB, así que llegar ahí
significa que ese volcado venía FALLANDO: un lector de larga vida mantiene
abierta una instantánea y las páginas no se pueden reclamar.

Lo grave no era el tamaño: **una copia hecha con `cp` del .db en ese estado no
incluye el WAL**. Las dos copias de seguridad de esa tarde salieron sin la vista
`viva_real` y sin los datos recientes --- respaldos que no servían.
"""
import sqlite3

import pytest

from sentinel_omega.infrastructure.database.wal import (
    UMBRAL_MB,
    tamano_wal_mb,
    volcar_si_crece,
    volcar_wal,
)


# OJO con el montaje: SQLite vuelca y BORRA el WAL cuando se cierra la última
# conexión. Cerrar la conexión antes de probar el volcado deja el registro en
# cero y el test pasa sin haber probado nada. Aquí se deja VIVA pero ociosa,
# que es el caso real: el ciclo tiene la base abierta todo el tiempo.
@pytest.fixture
def base(tmp_path):
    """Base en modo WAL con bastante escrito para que el registro crezca."""
    ruta = str(tmp_path / "prueba.db")
    conn = sqlite3.connect(ruta)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA wal_autocheckpoint=0")     # que NO se vacíe solo
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
    conn.executemany("INSERT INTO t (x) VALUES (?)",
                     [("y" * 400,) for _ in range(4000)])
    conn.commit()
    return ruta, conn


def test_se_mide_el_peso_del_wal(base):
    ruta, _ = base
    assert tamano_wal_mb(ruta) > 0


def test_sin_wal_el_peso_es_cero(tmp_path):
    ruta = str(tmp_path / "sin_wal.db")
    sqlite3.connect(ruta).close()
    assert tamano_wal_mb(ruta) == 0.0


def test_el_volcado_vacia_el_registro(base):
    ruta, conn = base
    antes = tamano_wal_mb(ruta)
    r = volcar_wal(ruta, modo="TRUNCATE")
    assert r["ok"] is True and r["bloqueado"] is False
    assert r["antes_mb"] == pytest.approx(antes, abs=0.1)
    assert tamano_wal_mb(ruta) == 0.0


def test_los_datos_siguen_ahi_despues_de_volcar(base):
    # Vaciar el registro NO es perder nada: se vuelca A la base.
    ruta, conn = base
    volcar_wal(ruta, modo="TRUNCATE")
    c = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 4000
    assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_por_debajo_del_umbral_no_se_toca_nada(base):
    ruta, conn = base
    antes = tamano_wal_mb(ruta)
    assert volcar_si_crece(ruta, umbral_mb=antes + 100) is None
    assert tamano_wal_mb(ruta) == pytest.approx(antes, abs=0.01)


def test_por_encima_del_umbral_se_vuelca(base):
    ruta, conn = base
    r = volcar_si_crece(ruta, umbral_mb=0.01)
    assert r is not None and r["ok"] is True
    assert r["despues_mb"] < r["antes_mb"]


def test_un_lector_abierto_no_cuelga_el_ciclo(base):
    """Lo que de verdad pasaba: alguien con la base tomada. El volcado tiene
    que informarlo y SEGUIR, no esperar para siempre."""
    ruta, conn = base
    lector = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    lector.execute("BEGIN")
    lector.execute("SELECT COUNT(*) FROM t").fetchone()   # instantánea abierta
    try:
        r = volcar_si_crece(ruta, umbral_mb=0.01, espera_s=1.0)
        assert r is not None
        if r["bloqueado"]:
            assert "procesos" in r          # dice QUIÉN lo impide
    finally:
        lector.close()


def test_un_modo_invalido_no_revienta(base):
    ruta, _ = base
    r = volcar_wal(ruta, modo="LO_QUE_SEA")
    assert r["ok"] is False and "error" in r


def test_una_base_que_no_existe_no_revienta(tmp_path):
    r = volcar_wal(str(tmp_path / "no_esta.db"))
    assert r["ok"] in (False, True)     # no lanza; puede crearla vacía


def test_el_umbral_por_defecto_avisa_antes_del_giga():
    assert UMBRAL_MB < 1024, "el umbral tiene que saltar ANTES de llegar al giga"


# ─── Que esté realmente conectado ────────────────────────────────────────────

def test_el_ciclo_revisa_el_wal():
    import inspect

    from sentinel_omega import launcher
    fuente = inspect.getsource(launcher)
    assert "volcar_si_crece(" in fuente
    # Fuera del try del ciclo: si el ciclo falla, el registro crece igual.
    i = fuente.index("volcar_si_crece(")
    assert "Cycle failed" in fuente[:i]


def test_el_barrido_de_medianoche_vacia():
    import inspect

    from sentinel_omega.infrastructure.pipeline import mantenimiento
    fuente = inspect.getsource(mantenimiento.barrido_diario)
    assert "volcar_wal(" in fuente
    assert fuente.index("volcar_wal(") < fuente.index("promover_eventos_vivos(")


def test_el_umbral_sale_de_la_configuracion():
    from sentinel_omega.config.sentinel_config import load_config
    cfg = load_config()
    assert cfg.wal.umbral_mb > 0
    assert isinstance(cfg.wal.vaciado_diario, bool)


def test_el_montaje_no_se_enganna_solo(base):
    """Guarda del propio test: si el WAL estuviera vacío al empezar, los tests
    de arriba pasarían sin probar nada. Pasó: cerrar la conexión lo borraba."""
    ruta, _ = base
    assert tamano_wal_mb(ruta) > 0.5
