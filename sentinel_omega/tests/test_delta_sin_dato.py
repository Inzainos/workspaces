"""Delta decidía con cuatro valores inventados. Que no vuelva.

Auditoría del 2026-09-26. `ingest` tenía cuatro respaldos que describían un
mercado NORMAL --- `fear_greed` 50, `vix` 20, `btc_dominance` 0,5 y
`yield_spread` 0,5 --- y la decisión los leía como medidos:

    self._yield_spread = data.get("yield_spread", 0.5)
    ...
    if self._yield_spread < 0:        # con el 0,5 de relleno: «no invertida»

Delta **no tiene fuente financiera desde el 2026-01-01**, así que venía
decidiendo con los cuatro fabricados y reportando «Financial markets within
normal bounds» sin haber consultado nada. Es el mismo patrón que omega con el
7,83, y lo mismo que el `or 0.0` deja pasar un cero medido como ausencia.
"""

from __future__ import annotations

import pytest

from sentinel_omega.core.shared.agent_base import SignalType, valor_medido
from sentinel_omega.layers.geodynamic.delta.agent import DeltaAgent


def test_sin_una_sola_fuente_no_dice_que_todo_esta_normal():
    ag = DeltaAgent()
    ag.ingest({})
    sig = ag.analyze()
    assert sig.signal_type == SignalType.NO_SIGNAL
    assert "no se midió" in (sig.reasoning or ""), sig.reasoning
    # y no publica los valores inventados
    assert sig.data.get("yield_spread") is None
    assert sig.data.get("fear_greed") is None


def test_con_un_solo_dato_ya_puede_hablar_de_normalidad():
    ag = DeltaAgent()
    ag.ingest({"vix": 18.0})
    sig = ag.analyze()
    assert sig.signal_type == SignalType.NEUTRAL


def test_el_spread_ausente_no_cuenta_como_curva_no_invertida():
    """El filo concreto: `if spread < 0` con el 0,5 de relleno respondía
    «no invertida» sin dato. Ahora ausente no suma ni descarta."""
    sin = DeltaAgent(); sin.ingest({"vix": 40.0})
    con = DeltaAgent(); con.ingest({"vix": 40.0, "yield_spread": -0.5})
    s_sin = sin._market_fear_score()
    s_con = con._market_fear_score()
    assert s_con > s_sin, "una curva invertida medida debe pesar más que su ausencia"
    assert "yield" not in (sin.analyze().reasoning or "").lower()


def test_el_cero_medido_de_un_indicador_no_es_ausencia():
    """`valor_medido` frente al viejo `or`: un spread de 0,0 es un dato."""
    assert valor_medido({"yield_spread": 0.0}, "yield_spread") == 0.0
    assert valor_medido({"fear_greed": 0.0}, "fear_greed") == 0.0
    assert valor_medido({}, "yield_spread") is None


def test_el_estres_medido_sigue_llegando():
    """Que el camino bueno no se rompió."""
    ag = DeltaAgent()
    ag.ingest({"vix": 38.0, "yield_spread": -0.3, "fear_greed": 85.0})
    sig = ag.analyze()
    razon = sig.reasoning or ""
    assert "VIX extreme" in razon and "yield curve inverted" in razon
    assert sig.confidence > 0.5


def test_el_registro_no_finge_un_cero():
    """El log de `ingest` formateaba con `:.1f` y `:.1%`, que reventaría con
    None o, peor, imprimiría el relleno como si fuera medición."""
    ag = DeltaAgent()
    ag.ingest({})                       # no debe lanzar
    assert ag._vix is None and ag._yield_spread is None


def test_los_inicializadores_tambien_son_none():
    """Antes valían 50, 20, 0,5 y 0,5 desde el constructor: un agente que
    nunca ingirió ya venía con un mercado normal puesto."""
    ag = DeltaAgent()
    for attr in ("_fear_greed", "_vix", "_btc_dominance", "_yield_spread"):
        assert getattr(ag, attr) is None, attr
