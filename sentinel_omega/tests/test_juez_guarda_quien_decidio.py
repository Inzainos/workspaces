"""El Juez tiene que poder comparar quién acertaba: el modelo o la regla.

`layer_runners._aplicar_modelos` calcula cinco campos y los deja en `sig.data`,
y su docstring dice para qué: «se ANOTA siempre en la señal (`onnx_*`), para que
el Juez pueda comparar después quién acertaba».

`juez_cycle_register` armaba el `detalles` con cuatro claves fijas y nunca leía
`sig.data`. Medido el 2026-09-27: **0 filas** de `TBL_JUEZ_AUDITORIA` tenían
`onnx_senal`. Los campos se calculaban y se tiraban --- la señal medida y no
conectada, esta vez en el camino de auditoría.
"""
import json

import pytest

from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType
from sentinel_omega.infrastructure.pipeline.juez_cycle_register import (
    register_cycle_predictions,
)


class _JuezFalso:
    def __init__(self):
        self.filas = []

    def registrar_prediccion(self, bot_name, prediccion, confianza,
                             ventana_h=72, detalles=None, fase=None, **kw):
        self.filas.append((bot_name, prediccion, detalles or {}))


class _Geo:
    def __init__(self, signals):
        self.final_signal = SignalType.NEUTRAL
        self.confidence = 0.3
        self.agent_signals = signals


def _senal(nombre, data):
    return AgentSignal(agent_name=nombre, signal_type=SignalType.WATCH,
                       confidence=0.735, timestamp=0.0, data=data,
                       reasoning="modelo ONNX: WATCH (74%) [regla: neutral (20%)]")


DATA_MODELO = {
    "onnx": True, "onnx_senal": "WATCH", "onnx_conf": 0.735,
    "regla_senal": "neutral", "regla_conf": 0.2,
}


def _fila(juez, bot):
    return next(d for b, _, d in juez.filas if b == bot)


def test_se_guarda_lo_que_dijo_el_modelo_y_lo_que_dijo_la_regla():
    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo([_senal("beta1", dict(DATA_MODELO))]))
    d = _fila(juez, "beta1")
    assert d["onnx_senal"] == "WATCH"
    assert d["regla_senal"] == "neutral"
    assert d["onnx_conf"] == 0.735
    assert d["regla_conf"] == 0.2


def test_la_discrepancia_es_consultable_con_json_extract():
    """El objetivo del arreglo: una consulta SQL, no parsear prosa."""
    import sqlite3

    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo([_senal("beta1", dict(DATA_MODELO))]))
    detalles_json = json.dumps(_fila(juez, "beta1"))

    conn = sqlite3.connect(":memory:")
    fila = conn.execute(
        "SELECT json_extract(?,'$.onnx_senal'), json_extract(?,'$.regla_senal')",
        (detalles_json, detalles_json),
    ).fetchone()
    assert fila == ("WATCH", "neutral")
    assert fila[0].lower() != fila[1].lower(), "el modelo pisó a la regla"


def test_cuando_el_modelo_calla_se_registra_que_calló():
    """`_aplicar_modelos` pone `onnx: False` si el modelo se abstuvo. Eso también
    es información: distingue «la regla decidió» de «no hubo modelo»."""
    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo([_senal("loki", {"onnx": False})]))
    d = _fila(juez, "loki")
    assert d["onnx"] is False
    assert "onnx_senal" not in d, "no se inventa un veredicto que no hubo"


def test_un_agente_sin_data_no_revienta():
    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo([_senal("omega", {})]))
    d = _fila(juez, "omega")
    assert "features_generales" in d
    assert "onnx_senal" not in d


def test_no_se_vuelca_sig_data_entero():
    """A propósito: si un agente mete lo que quiera en su `data`, el
    `detalles_json` de CADA fila del Juez crecería sin control."""
    juez = _JuezFalso()
    ruido = dict(DATA_MODELO)
    ruido["matriz_gigante"] = list(range(500))
    ruido["bz_mean"] = -3.1
    register_cycle_predictions(juez, _Geo([_senal("beta1", ruido)]))
    d = _fila(juez, "beta1")
    assert "matriz_gigante" not in d
    assert "bz_mean" not in d
    assert d["onnx_senal"] == "WATCH"


def test_las_cuatro_claves_de_siempre_siguen_estando():
    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo([_senal("beta1", dict(DATA_MODELO))]),
                               features={"kp_mean": 2.0})
    d = _fila(juez, "beta1")
    for k in ("nodos", "padre_signal", "reasoning", "features_generales"):
        assert k in d, f"se perdió {k}"
    assert d["features_generales"] == {"kp_mean": 2.0}
