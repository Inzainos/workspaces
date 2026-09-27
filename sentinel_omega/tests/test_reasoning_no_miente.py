"""Si el modelo pisa a la regla, el registro tiene que decirlo.

Medido el 2026-09-27, ciclo 14432, primera corrida con el código nuevo. El Juez
guardó esta fila:

    beta1   watch 0.735   "Normal spectral distribution; Schumann sin dato"

El texto describe lo que concluyó la REGLA; el `watch 0.735` es del MODELO.
`_aplicar_modelos` sustituía `signal_type` y `confidence` y dejaba el
`reasoning` intacto. Quien audita esa fila --- el Padre, el operador, o quien
lea la bitácora --- ve una contradicción y no sabe cuál mandó.

Es primo de la regla dura 10 de AGENTS.md: «un descarte silencioso esconde el
fallo indefinidamente». Aquí no se descarta trabajo, se descarta la EXPLICACIÓN.
"""
import inspect

from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType
from sentinel_omega.infrastructure.pipeline import layer_runners


def _aplicar(monkeypatch, salida, senal_regla, conf_regla, texto_regla):
    """Corre `_aplicar_modelos` con el modelo forzado a devolver `salida`."""
    sig = AgentSignal(agent_name="beta1", signal_type=senal_regla,
                      confidence=conf_regla, timestamp=0.0, data={},
                      reasoning=texto_regla)
    runner = object.__new__(layer_runners.GeodynamicLayerRunner)
    monkeypatch.setattr(runner, "_rasgos_del_ciclo", lambda: {"kp_mean": 2.0},
                        raising=False)
    monkeypatch.setattr(
        "sentinel_omega.core.onnx_mixin.senal_desde_rasgos",
        lambda bot, rasgos, **kw: salida)
    layer_runners.GeodynamicLayerRunner._aplicar_modelos(runner, [sig])
    return sig


def test_el_texto_dice_que_mando_el_modelo(monkeypatch):
    sig = _aplicar(monkeypatch, (SignalType.WATCH, 0.735, "WATCH"),
                   SignalType.NEUTRAL, 0.2, "Normal spectral distribution")
    assert sig.signal_type is SignalType.WATCH
    assert "ONNX" in sig.reasoning, (
        f"el registro no dice que el veredicto es del modelo: {sig.reasoning!r}")


def test_no_se_tira_lo_que_dijo_la_regla(monkeypatch):
    """La regla es la segunda opinión. Cuando el modelo se equivoque va a ser
    lo primero que haya que leer."""
    sig = _aplicar(monkeypatch, (SignalType.WATCH, 0.735, "WATCH"),
                   SignalType.NEUTRAL, 0.2, "Normal spectral distribution")
    assert "Normal spectral distribution" in sig.reasoning
    assert "neutral" in sig.reasoning.lower()


def test_el_registro_ya_no_se_contradice(monkeypatch):
    """La fila del ciclo 14432: `watch` junto a un texto que decía «normal», sin
    nada que dijera quién decidió."""
    sig = _aplicar(monkeypatch, (SignalType.WATCH, 0.735, "WATCH"),
                   SignalType.NEUTRAL, 0.2, "Normal spectral distribution")
    veredicto = sig.signal_type.value          # 'watch'
    # El texto menciona las dos señales Y cuál es de quién.
    assert veredicto in sig.reasoning.lower()
    assert sig.reasoning.index("ONNX") < sig.reasoning.lower().index("regla")


def test_si_el_modelo_calla_no_se_toca_el_texto(monkeypatch):
    """`None` = «nada que reportar»: manda la regla y su explicación queda
    intacta. Reescribirla ahí sería la mentira contraria."""
    sig = _aplicar(monkeypatch, None, SignalType.NEUTRAL, 0.2,
                   "Normal spectral distribution")
    assert sig.reasoning == "Normal spectral distribution"
    assert sig.signal_type is SignalType.NEUTRAL
    assert sig.data.get("onnx") is False


def test_se_conservan_las_dos_confianzas_en_los_datos(monkeypatch):
    """Ya estaban; la prueba las fija para que el `reasoning` y `data` no se
    separen."""
    sig = _aplicar(monkeypatch, (SignalType.WATCH, 0.735, "WATCH"),
                   SignalType.NEUTRAL, 0.2, "Normal spectral distribution")
    assert sig.data["onnx_conf"] == 0.735
    assert sig.data["regla_conf"] == 0.2
    assert sig.data["regla_senal"] == "neutral"


def test_una_regla_sin_texto_no_revienta(monkeypatch):
    sig = _aplicar(monkeypatch, (SignalType.WATCH, 0.9, "WATCH"),
                   SignalType.NEUTRAL, 0.2, "")
    assert "ONNX" in sig.reasoning


def test_aplicar_modelos_escribe_el_reasoning():
    """Guardia de regresión sobre la fuente: es el campo que se olvidó."""
    fuente = inspect.getsource(
        layer_runners.GeodynamicLayerRunner._aplicar_modelos)
    assert "sig.reasoning =" in fuente, (
        "volvió el defecto: se sustituye el veredicto y no la explicación")
