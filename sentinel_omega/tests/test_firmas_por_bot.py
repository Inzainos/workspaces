"""Cada bot pregunta a SU memoria, y el emparejamiento dice de quién es.

`TBL_FIRMAS` tiene `bot_name` desde siempre --- medido el 2026-09-27: padre
14.289 (el conjunto, `BOT_FEATURES["padre"] = None`), alfa1 1.632, beta1 993,
loki 858, beta2 809, delta 676, omega 307, jupiter 14, alfa2 0 --- y cada bot
tiene su propio ONNX. Pero `match_estado_actual` recorría las 12.872
consolidadas de los nueve contra un único diccionario global, y **tiraba el
`bot_name`**. Así que:

  * un bot no podía preguntarle nada a su propia memoria;
  * y un emparejamiento no era ATRIBUIBLE, por lo que el doble de
    `SEVERIDAD_FALLO_FIRMA_CONOCIDA` solo podía aplicarse al padre (en el
    entrenamiento sí llega a cada bot, vía `firma_conocida=es_exigible`).

Este cambio es ADITIVO: sin `bot` el comportamiento es idéntico al de antes.
Que el emparejamiento influya en la DECISIÓN es otro cambio --- hoy
`match_estado_actual` se llama desde `_auditar_ciclo`, después del consenso.
"""
import json
import sqlite3

import pytest

from sentinel_omega.core.firmas.signature_engine import (
    SIMILARITY_ALERT,
    FirmaMemoria,
)

# Dos firmas idénticas de bots distintos + una que no empareja.
_RASGOS = {"bz_mean": -5.0, "kp_mean": 4.0, "viento_avg": 500.0, "bz_min": -9.0}
_OTROS = {"bz_mean": 40.0, "kp_mean": 0.0, "viento_avg": 100.0, "bz_min": 39.0}


@pytest.fixture
def memoria(tmp_path):
    conn = sqlite3.connect(tmp_path / "firmas.db")
    conn.execute(
        "CREATE TABLE TBL_FIRMAS (firma_id INTEGER PRIMARY KEY, bot_name TEXT, "
        "event_class TEXT, id_nodo INTEGER, features_json TEXT, "
        "recurrencia INTEGER, estado TEXT)"
    )
    conn.executemany(
        "INSERT INTO TBL_FIRMAS VALUES (?,?,?,?,?,?,?)",
        [(1, "beta2", "SISMO_M5", 83, json.dumps(_RASGOS), 71, "consolidada"),
         (2, "delta", "SISMO_M4", 64, json.dumps(_RASGOS), 68, "consolidada"),
         (3, "alfa1", "SISMO_M6", 12, json.dumps(_OTROS), 9, "consolidada"),
         (4, "beta2", "SISMO_M7", 99, json.dumps(_RASGOS), 3, "nueva")],
    )
    conn.commit()
    return FirmaMemoria(conn)


def test_sin_bot_se_comporta_como_antes(memoria):
    """Aditivo: el llamado de siempre sigue viendo las firmas de todos."""
    r = memoria.match_estado_actual(_RASGOS)
    assert {m["bot_name"] for m in r} == {"beta2", "delta"}


def test_el_emparejamiento_dice_de_quien_es(memoria):
    """Lo que faltaba para que el castigo sea atribuible."""
    r = memoria.match_estado_actual(_RASGOS)
    assert r, "no emparejó nada"
    for m in r:
        assert "bot_name" in m, "se sigue tirando el dueño de la firma"


def test_cada_bot_ve_solo_las_suyas(memoria):
    assert [m["bot_name"] for m in memoria.match_estado_actual(_RASGOS, bot="beta2")] == ["beta2"]
    assert [m["bot_name"] for m in memoria.match_estado_actual(_RASGOS, bot="delta")] == ["delta"]
    assert memoria.match_estado_actual(_RASGOS, bot="alfa1") == []


def test_la_suma_por_bot_es_el_global(memoria):
    """El filtro PARTE el conjunto: no pierde ni duplica. Verificado también
    contra la base real el 2026-09-27: 17 por bot = 17 global."""
    global_ = memoria.match_estado_actual(_RASGOS)
    bots = {m["bot_name"] for m in global_}
    suma = sum(len(memoria.match_estado_actual(_RASGOS, bot=b)) for b in bots)
    assert suma == len(global_)


def test_un_bot_sin_firmas_no_revienta(memoria):
    assert memoria.match_estado_actual(_RASGOS, bot="alfa2") == []
    assert memoria.match_estado_actual(_RASGOS, bot="no_existe") == []


def test_solo_las_consolidadas_son_exigibles(memoria):
    """La firma 4 es `nueva` y empareja igual de bien; no debe aparecer ---
    solo las consolidadas son exigibles (AGENTS.md)."""
    r = memoria.match_estado_actual(_RASGOS, bot="beta2")
    assert [m["firma_id"] for m in r] == [1]


def test_el_umbral_sigue_mandando(memoria):
    assert memoria.match_estado_actual(_RASGOS, bot="beta2", umbral=1.01) == []
    assert SIMILARITY_ALERT == 0.8


def test_la_comparacion_sigue_siendo_post_decision():
    """Guardia: este cambio NO conecta la memoria a la decisión. Si algún día
    `match_estado_actual` se llama antes del consenso, esta prueba cae y hay que
    medir el impacto en los veredictos antes de aceptarlo."""
    import inspect

    from sentinel_omega import launcher
    fuente = inspect.getsource(launcher)
    i = fuente.index("match_estado_actual")
    antes = fuente[:i]
    assert "def _auditar_ciclo" in antes, (
        "el emparejamiento salió de _auditar_ciclo: ahora puede influir en la "
        "decisión, y eso mueve veredictos")
