"""Tamaños: el vector que armamos y el modelo que lo recibe tienen que coincidir.

`vector_para(bot, ...)` arma un vector de `BOT_DIMS[bot]` posiciones. Si un
`.onnx` espera `[None, N]` con N distinto, hoy `pad_vector` rellena o recorta
en silencio y el modelo contesta sobre un vector que no es el suyo. Eso pasa
justo en el reinicio donde cambia el vector (17 rasgos nuevos, reentreno de los
8 ONNX): si un modelo viejo se queda en `models/`, opina sobre basura.

Contrato:
  1. Cada `.onnx` en disco declara `[None, BOT_DIMS[bot]]`.
  2. Si el modelo cargado no coincide con `BOT_DIMS[bot]`, `senal_desde_rasgos`
     devuelve None (manda la regla) y NUNCA llega a `predict_signal`.
     El chequeo puede vivir en `try_load_onnx`, `inferencia_de` o
     `senal_desde_rasgos`; este test lo detecta en cualquiera de los tres.

El (2) estuvo marcado xfail estricto hasta que existiera el chequeo. **Entró el
2026-09-27 en `core/onnx_mixin.inferencia_de`** --- compara la entrada declarada
del `.onnx` con `BOT_DIMS[bot]`, descarta el modelo con `logger.error` y deja
mandar a la regla --- así que la marca se quitó, como decía esta nota. Los 16 XPASS
(8 bots × 2 desviaciones) eran eso.

Archivo de Agente-T; la marca la quitó Claude al implementar el chequeo.
"""
from pathlib import Path

import pytest

ort = pytest.importorskip("onnxruntime")

from sentinel_omega.config.onnx_config import onnx_config
from sentinel_omega.core import onnx_mixin
from sentinel_omega.core.features_onnx import BOT_DIMS, FEATURE_ORDER
from sentinel_omega.core.onnx_engine import ONNXModelLoader, create_mock_onnx_session

MODELS = Path(__file__).resolve().parents[1] / "models"


def _dim_de(session):
    ins = session.get_inputs()
    assert len(ins) == 1, f"se esperaba una entrada, hay {len(ins)}"
    shape = ins[0].shape
    assert len(shape) == 2, f"se esperaba [None, N], hay {shape}"
    return shape[1]


@pytest.mark.parametrize("bot", sorted(BOT_DIMS))
def test_cada_onnx_en_disco_tiene_la_dimension_de_su_vector(bot):
    cfg = getattr(onnx_config, bot)
    ruta = MODELS / cfg.model_path
    assert ruta.exists(), f"{bot}: falta {ruta.name}"
    s = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
    n = _dim_de(s)
    assert n == BOT_DIMS[bot], (
        f"{bot}: {ruta.name} espera [None, {n}], el vector tiene {BOT_DIMS[bot]}")


def _rasgos_llenos(bot):
    orden = FEATURE_ORDER[bot]
    nombres = orden.keys() if isinstance(orden, dict) else orden
    return {n: 1.0 for n in nombres if isinstance(n, str)}


def _con_modelo_de(monkeypatch, bot, n):
    """El cargador devuelve un modelo de [None, n] y espiamos predict_signal."""
    llamadas = []
    monkeypatch.setattr(ONNXModelLoader, "load_model",
                        lambda self, cfg: create_mock_onnx_session(n, 2))
    monkeypatch.setattr(onnx_mixin, "_SESIONES", {})

    def espia(inferencia, vec, **kw):
        llamadas.append(len(vec))
        return ("ESPIA", 0.99, "espia")

    monkeypatch.setattr(onnx_mixin, "predict_signal", espia)
    return llamadas


# Bots cuyo ONNX está apagado a propósito en `onnx_config`: a ésos no se les
# pregunta aunque la dimensión cuadre, así que el control de abajo no aplica.
# alfa2, desde el 2026-10-02: vota con su REGLA porque su reentreno salía
# `hybrid real=23 + boot=2500` (99 % sintético, y cinco de las ocho columnas
# del prior llevan otra magnitud). Ver `tests/test_alfa2_votante.py`.
APAGADOS = {b for b in BOT_DIMS
            if not getattr(getattr(onnx_config, b, None), "enabled", True)}


@pytest.mark.parametrize("bot", sorted(BOT_DIMS))
def test_control_con_la_dimension_correcta_si_se_pregunta(monkeypatch, bot):
    """Control: sin este, el test de rechazo podría pasar por accidente."""
    if bot in APAGADOS:
        pytest.skip(f"{bot}: ONNX apagado a propósito en onnx_config")
    llamadas = _con_modelo_de(monkeypatch, bot, BOT_DIMS[bot])
    out = onnx_mixin.senal_desde_rasgos(bot, _rasgos_llenos(bot))
    assert out is not None and llamadas, f"{bot}: con N correcto no preguntó"


@pytest.mark.parametrize("bot", sorted(APAGADOS))
def test_al_apagado_no_se_le_pregunta_ni_con_la_dimension_correcta(monkeypatch, bot):
    """El otro lado del contrato: apagar tiene que SERVIR. Si `enabled=False`
    no se honrara, alfa2 votaría con el modelo que se decidió no usar."""
    llamadas = _con_modelo_de(monkeypatch, bot, BOT_DIMS[bot])
    out = onnx_mixin.senal_desde_rasgos(bot, _rasgos_llenos(bot))
    assert out is None and not llamadas, (
        f"{bot}: está apagado en onnx_config y aun así se le preguntó")


@pytest.mark.parametrize("bot", sorted(BOT_DIMS))
@pytest.mark.parametrize("delta", [-2, +3])
def test_un_modelo_de_otro_tamano_no_se_usa(monkeypatch, bot, delta):
    n = BOT_DIMS[bot] + delta
    llamadas = _con_modelo_de(monkeypatch, bot, n)
    out = onnx_mixin.senal_desde_rasgos(bot, _rasgos_llenos(bot))
    assert out is None and not llamadas, (
        f"{bot}: modelo [None, {n}] contra vector de {BOT_DIMS[bot]} "
        f"y aun así se le preguntó")
