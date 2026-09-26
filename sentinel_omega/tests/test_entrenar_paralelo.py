"""El entrenamiento paralelo por bot debe dar el MISMO resultado que el
secuencial — si no, produce memoria sesgada y no sirve."""

from datetime import datetime, timedelta

import pytest

from sentinel_omega.infrastructure.database.schema import init_database
from sentinel_omega.infrastructure.pipeline.entrenamiento import (
    entrenar_reconocimiento,
)
from sentinel_omega.infrastructure.pipeline.entrenar_paralelo import (
    entrenar_reconocimiento_paralelo,
)


def _seed(db_path, n_eventos=8):
    """Mini-backcast: 14 días de clima espacial por evento + eventos M5+."""
    conn = init_database(db_path)
    base = datetime(2010, 6, 1)
    for ev in range(n_eventos):
        ts_ev = base + timedelta(days=20 * ev)
        for h in range(336):
            ts = (ts_ev - timedelta(hours=336 - h)).strftime("%Y-%m-%d %H:%M")
            conn.execute(
                "INSERT OR IGNORE INTO tbl_clima_espacial_raw "
                "(timestamp_blk, bz_promedio, bz_min, bz_derivada, "
                " viento_solar_avg, viento_solar_max, kp_max, kp_promedio, "
                " proton_flux_10mev) VALUES (?,?,?,?,?,?,?,?,?)",
                (ts, -3.0 - ev * 0.1, -11.0, 0.4, 430.0, 600.0, 5.5, 3.0, 12.0))
            conn.execute(
                "INSERT OR IGNORE INTO tbl_astronomia_cinematica "
                "(timestamp_blk, fase_lunar_pct, es_sicigia) VALUES (?,?,?)",
                (ts, 0.9, 1))
        blk = ts_ev.strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT OR IGNORE INTO tbl_historico_sismico_raw "
            "(timestamp_blk, id_nodo, sismo_count, sismo_max_mag) "
            "VALUES (?, 45, 1, 6.4)", (blk,))
    conn.commit()
    conn.close()


def _firmas_resumen(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    filas = conn.execute(
        "SELECT bot_name, event_class, id_nodo, recurrencia, estado "
        "FROM TBL_FIRMAS ORDER BY bot_name, event_class, id_nodo"
    ).fetchall()
    conn.close()
    return filas


def test_paralelo_igual_que_secuencial(tmp_path):
    seq = str(tmp_path / "seq.db")
    par = str(tmp_path / "par.db")
    _seed(seq)
    _seed(par)

    # Mismos bots en ambos (excluye alfa2 live-only, que no entrena del backcast)
    bots = ["alfa1", "beta1", "padre"]

    entrenar_reconocimiento(seq, bots=bots)
    entrenar_reconocimiento_paralelo(par, bots=bots, n_workers=3)

    resumen_seq = _firmas_resumen(seq)
    resumen_par = _firmas_resumen(par)

    assert resumen_seq == resumen_par, (
        "El paralelo NO coincide con el secuencial — memoria fragmentada"
    )
    assert len(resumen_seq) > 0


def test_paralelo_no_deja_bots_fuera(tmp_path):
    par = str(tmp_path / "par.db")
    _seed(par)
    res = entrenar_reconocimiento_paralelo(par, bots=["alfa1", "beta1"],
                                           n_workers=2)
    assert res["firmas_unidas"] > 0
    assert set(res["por_bot"].keys()) == {"alfa1", "beta1"}


def test_un_bot_con_fecha_de_arranque_tambien_coincide(tmp_path):
    """El caso que la prueba de arriba NO tocaba.

    `alfa1`, `beta1` y `padre` no tienen entrada en `BOT_DESDE`, así que la
    rama de `desde_global` nunca se ejecutaba y la equivalencia quedaba probada
    sólo para el caso fácil. beta2 arranca en 2012 y es donde los dos caminos
    se pueden separar --- en la corrida completa NO deben.
    """
    from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_DESDE

    assert "beta2" in BOT_DESDE, "beta2 debería tener fecha de arranque"
    seq = str(tmp_path / "seq2.db")
    par = str(tmp_path / "par2.db")
    _seed(seq)
    _seed(par)
    bots = ["beta2", "alfa1"]

    entrenar_reconocimiento(seq, bots=bots)
    entrenar_reconocimiento_paralelo(par, bots=bots, n_workers=2)

    assert _firmas_resumen(seq) == _firmas_resumen(par)


def test_max_eventos_avisa_de_que_no_es_comparable(tmp_path, caplog):
    """No basta con que diverja: tiene que DECIRLO.

    Medido el 2026-09-26: `entrenar_reconocimiento` recorta a los primeros N
    eventos ANTES de filtrar por `BOT_DESDE`, así que un bot con fecha de
    arranque ve otro tramo según se entrene solo o acompañado. Una comparación
    hecha así da +N recurrencias y parece que el paralelo infla la memoria. No
    la infla --- pero quien lo mida tiene que enterarse por el registro, no
    descubriéndolo tres horas después.
    """
    import logging

    par = str(tmp_path / "par3.db")
    _seed(par)
    with caplog.at_level(logging.WARNING):
        entrenar_reconocimiento_paralelo(par, bots=["alfa1"], n_workers=1,
                                         max_eventos=3)
    assert any("max_eventos" in r.getMessage() for r in caplog.records), caplog.text


def test_cada_copia_se_borra_al_unirla(tmp_path):
    """El pico de disco es UNA copia, no ocho.

    Copiar cuesta ~7 s por base de 922 MB; tenerlas todas vivas cuesta 7,4 GB.
    Se borra cada una en cuanto sus filas están unidas.
    """
    par = str(tmp_path / "par4.db")
    trabajo = tmp_path / "wk"
    trabajo.mkdir()
    _seed(par)
    entrenar_reconocimiento_paralelo(par, bots=["alfa1", "beta1"], n_workers=2,
                                     dir_trabajo=str(trabajo))
    quedan = list(trabajo.glob("train_*.db"))
    assert quedan == [], f"copias sin borrar: {quedan}"


def test_el_rebuild_pide_la_fase_1_en_paralelo():
    """El módulo existía con sus pruebas desde antes y nadie lo llamaba: el
    rebuild usaba el secuencial. Esta prueba es para que no vuelva a pasar."""
    from pathlib import Path

    fuente = Path("deploy/rebuild_completo.py").read_text()
    assert "paralelo=True" in fuente

    import inspect

    from sentinel_omega.infrastructure.pipeline.entrenamiento import entrenar
    assert "paralelo" in inspect.signature(entrenar).parameters


def test_paralelo_con_max_eventos_no_se_usa_desde_entrenar(tmp_path):
    """`entrenar(paralelo=True, max_eventos=N)` cae al secuencial a propósito:
    con recorte los dos caminos no son comparables, así que no se finge."""
    import logging

    from sentinel_omega.infrastructure.pipeline import entrenamiento as E

    llamadas = {"serial": 0, "paralelo": 0}
    real_serial = E.entrenar_reconocimiento

    def espia_serial(*a, **k):
        llamadas["serial"] += 1
        return real_serial(*a, **k)

    db = str(tmp_path / "e.db")
    _seed(db)
    E.entrenar_reconocimiento = espia_serial
    try:
        E.entrenar(db, max_eventos=2, paralelo=True)
    except Exception:
        pass          # lo que nos importa es por qué rama entró
    finally:
        E.entrenar_reconocimiento = real_serial
    assert llamadas["serial"] >= 1
