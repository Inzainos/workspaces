"""`confidence_threshold` estaba declarado ocho veces y leído por nadie.

Hallado el 2026-10-07 persiguiendo 159 falsos positivos y seis bots en el suelo.
`beta2` emitía WATCH con confianza 0,50 teniendo 0,60 declarado en
`onnx_config`, y el grep lo explicó: **cero menciones** de
`confidence_threshold` en todo el código fuera de la propia config. Un mando
muerto, de la misma familia que el `days` de `fetch_kp_index`.

Por qué SOLO para las señales que alarman
-----------------------------------------
Honrarlo simétricamente hace daño. Medido sobre los 27 ciclos vivos de cada bot:

    bot      umbral  senal    n  bajo umbral  pasaria a
    jupiter    0,55  NEUTRAL  27      27      regla neutral/WATCH
    beta2      0,60  NEUTRAL  19      19      regla neutral/WATCH
    beta2      0,60  WATCH     8       8      regla neutral
    alfa1      0,60  NEUTRAL   8       8      regla neutral
    delta/loki/omega  WATCH 27/27/27    0     sin cambio

Silenciaría a los dos bots que SÍ discriminan --- `jupiter` y `beta2`, los de
mejor peso, cuyos NEUTRAL vienen con poca confianza --- y dejaría intactos a los
cinco que alarman el 100 % de los ciclos, cuyas constantes de 0,68-0,76 están
cómodamente por encima de su umbral. Y como la regla de algunos de esos ciclos
dice `watch`, habría SUBIDO las alarmas.

La asimetría del sistema ya dice cuál es el acto costoso: perder un evento pesa
10x contra 1x de una falsa alarma. La barra es para ALARMAR. Pedirle confianza
a un «nada que reportar» es pedir seguridad para callarse.
"""
import logging

import numpy as np
import pytest

from sentinel_omega.core import onnx_mixin
from sentinel_omega.core.shared.agent_base import SignalType


class _Cfg:
    def __init__(self, umbral):
        self.confidence_threshold = umbral


class _Inferencia:
    """Lo mínimo que `predict_signal` usa de `ONNXBotInference`."""

    def __init__(self, nombre, conf, umbral, bot="probeta"):
        self.model_config = _Cfg(umbral)
        self.bot_name = bot
        self._r = (conf, nombre)

    def predict(self, features):
        return self._r


VEC = np.zeros(8, dtype=np.float32)


def test_una_alarma_por_debajo_del_umbral_manda_la_regla():
    """El caso de beta2: WATCH a 0,50 con 0,60 declarado."""
    assert onnx_mixin.predict_signal(_Inferencia("WATCH", 0.50, 0.60), VEC) is None


def test_una_alarma_por_encima_del_umbral_SI_pasa():
    out = onnx_mixin.predict_signal(_Inferencia("WATCH", 0.72, 0.55), VEC)
    assert out is not None
    assert out[0] == SignalType.WATCH


def test_justo_en_el_umbral_pasa():
    """`< umbral` descarta; igual al umbral no. Que el borde esté fijado."""
    out = onnx_mixin.predict_signal(_Inferencia("WATCH", 0.60, 0.60), VEC)
    assert out is not None and out[0] == SignalType.WATCH


@pytest.mark.parametrize("nombre", ["ALERT", "BULLISH", "BEARISH"])
def test_el_umbral_vale_para_TODAS_las_que_alarman(nombre):
    assert onnx_mixin.predict_signal(
        _Inferencia(nombre, 0.10, 0.60), VEC, allow_bullish_bearish=True) is None


def test_un_NEUTRAL_con_poca_confianza_NO_se_descarta():
    """La mitad que importa. Si se descartara, `jupiter` (27 NEUTRAL por debajo
    de 0,55) y `beta2` (19) caerían a su regla, que en algunos ciclos dice
    `watch`: el arreglo subiría las alarmas en vez de bajarlas."""
    out = onnx_mixin.predict_signal(_Inferencia("NEUTRAL", 0.10, 0.60), VEC)
    assert out is not None, (
        "se descartó un NEUTRAL por poca confianza: eso silencia a los bots "
        "que discriminan y deja pasar a los que alarman siempre")
    assert out[0] == SignalType.NEUTRAL


def test_sin_umbral_declarado_no_se_inventa_uno():
    """Un `model_config` sin el campo no puede volverse un filtro silencioso."""
    class _SinCfg:
        bot_name = "x"
        model_config = None
        def predict(self, f): return (0.01, "WATCH")
    out = onnx_mixin.predict_signal(_SinCfg(), VEC)
    assert out is not None and out[0] == SignalType.WATCH


def test_el_descarte_se_registra(caplog):
    """Regla dura 10: un descarte silencioso esconde el fallo indefinidamente."""
    with caplog.at_level(logging.INFO, logger=onnx_mixin.logger.name):
        onnx_mixin.predict_signal(_Inferencia("WATCH", 0.50, 0.60, bot="beta2"), VEC)
    texto = caplog.text
    assert "beta2" in texto and "0.500" in texto and "0.60" in texto, texto


def test_la_config_sigue_declarando_un_umbral_para_cada_bot():
    """Ahora que SE LEE, un bot sin umbral sería un bot sin barra."""
    from sentinel_omega.config.onnx_config import onnx_config
    from sentinel_omega.core.features_onnx import BOT_DIMS

    for bot in BOT_DIMS:
        u = getattr(onnx_config, bot).confidence_threshold
        assert u is not None and 0.0 < float(u) <= 1.0, (bot, u)
