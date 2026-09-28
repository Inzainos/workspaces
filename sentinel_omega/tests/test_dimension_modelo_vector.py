"""El guardián de dimensión: lo que `test_onnx_dims.py` no cubre.

El contrato («un modelo de otro tamaño no se usa; manda la regla») lo fija
`tests/test_onnx_dims.py`, de Agente-T, sobre los 8 bots y dos desviaciones. Este
archivo prueba sólo lo que ese no mira, para no duplicar 16 casos:

  * que el descarte se DIGA (regla dura 10: un descarte silencioso esconde el
    fallo indefinidamente --- y aquí era doblemente invisible, porque el `None`
    de `predict_signal` es indistinguible de «este bot no tiene modelo»);
  * que una forma dinámica no apague la rama ML por precaución;
  * que una sesión que no sabe declarar su forma no reviente el ciclo.

Implementación en `core/onnx_mixin.inferencia_de` / `dimension_de_entrada`,
2026-09-27.
"""
import pytest

from sentinel_omega.core.features_onnx import BOT_DIMS
from sentinel_omega.core.onnx_mixin import (
    _SESIONES, dimension_de_entrada, inferencia_de, try_load_onnx,
)


@pytest.fixture(autouse=True)
def _sin_cache():
    """La sesión se memoriza por bot; cada prueba parte de cero."""
    _SESIONES.clear()
    yield
    _SESIONES.clear()


def test_el_descarte_se_dice_en_el_log(monkeypatch, caplog):
    """Si se descarta sin decirlo, el bot se queda en su rama de reglas para
    siempre y nadie sabe que hay un modelo inservible en `models/`."""
    import sentinel_omega.core.features_onnx as fo

    if try_load_onnx("alfa1")[0] is None:
        pytest.skip("alfa1: sin modelo en disco")
    monkeypatch.setitem(fo.BOT_DIMS, "alfa1", BOT_DIMS["alfa1"] + 3)
    with caplog.at_level("ERROR"):
        assert inferencia_de("alfa1") is None
    dicho = [r.getMessage() for r in caplog.records if "se DESCARTA" in r.getMessage()]
    assert dicho, "lo descartó en silencio"
    assert "Reentrena" in dicho[0], "no dice qué hacer para arreglarlo"


def test_forma_dinamica_no_bloquea():
    """Un modelo que no declara la última dimensión no se descarta: no se sabe
    que esté mal, y presumirlo apagaría la rama ML sin motivo."""
    class _Entrada:
        shape = ["batch", None]

    class _Sesion:
        def get_inputs(self):
            return [_Entrada()]

    assert dimension_de_entrada(_Sesion()) is None


def test_sesion_sin_forma_no_revienta():
    """Fail-soft: el guardián no puede ser él mismo la causa de una caída."""
    class _Sesion:
        def get_inputs(self):
            raise RuntimeError("sesión rara")

    assert dimension_de_entrada(_Sesion()) is None


def test_entrada_sin_forma_declarada():
    class _Entrada:
        shape = []

    class _Sesion:
        def get_inputs(self):
            return [_Entrada()]

    assert dimension_de_entrada(_Sesion()) is None
