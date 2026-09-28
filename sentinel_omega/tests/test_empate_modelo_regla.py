"""El empate modelo-vs-regla lo gana el de más confianza.

Hasta el 2026-09-27 el modelo ganaba SIEMPRE que hablara: las asignaciones de
`sig.signal_type` y `sig.confidence` eran incondicionales y la comparación de
arriba solo decidía si se escribía una línea de log. Un modelo con 0,35 apagaba
una alarma de regla con 0,60.

Se vio en cuanto el registro dejó de mentir, sobre cinco horas de operación real:

    beta1   modelo=WATCH    regla=neutral    22 veces
    beta2   modelo=NEUTRAL  regla=watch       8 veces

Las 8 de beta2 eran alarmas de la regla apagadas por el modelo. Decisión del
operador, consultada: **gana el de más confianza**, simétrico --- ni se privilegia
alarmar ni callar.
"""
import pytest

from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType
from sentinel_omega.infrastructure.pipeline import layer_runners


# El desempate se prueba sobre un bot que NO esté callado por `RASGOS_CON_FUGA`
# (el tapón de Agente-C, 2026-09-27): a un bot de esa lista ni se le pregunta al
# modelo, así que no hay empate que resolver y estas pruebas pasarían --- o
# fallarían --- por un motivo que no es el suyo. Se usaba `beta2`, que entró a la
# lista esa misma noche. `beta1` es el otro caso medido (22 veredictos subidos).
BOT = "beta1"


def _correr(monkeypatch, salida, senal_regla, conf_regla,
            texto_regla="Normal spectral distribution", bot=BOT):
    sig = AgentSignal(agent_name=bot, signal_type=senal_regla,
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


def test_el_bot_de_prueba_no_esta_callado():
    """Si el tapón crece hasta cubrir a `BOT`, estas pruebas dejan de probar el
    desempate sin dar señal. Que falle aquí, en una línea, y no en seis sitios."""
    assert BOT not in getattr(layer_runners, "RASGOS_CON_FUGA", {}), (
        f"{BOT} entró a RASGOS_CON_FUGA: elige otro bot para BOT")


def test_al_bot_callado_no_se_le_pregunta(monkeypatch):
    """La otra cara: un bot con fuga no llega al desempate --- decisión de C, que
    no escribe `gano` porque no hubo disputa. Se fija aquí para que el desempate
    y el tapón no se pisen sin que nadie lo note."""
    fuga = getattr(layer_runners, "RASGOS_CON_FUGA", {})
    if not fuga:
        pytest.skip("no hay tapón activo")
    callado = sorted(fuga)[0]
    sig = _correr(monkeypatch, (SignalType.WATCH, 0.99, "WATCH"),
                  SignalType.NEUTRAL, 0.20, bot=callado)
    assert sig.signal_type is SignalType.NEUTRAL, (
        f"{callado} tiene un rasgo con fuga y el modelo le cambió el veredicto")
    assert "gano" not in sig.data
    assert sig.data.get("onnx_callado", "").startswith("fuga:")


def test_el_modelo_ya_no_apaga_una_alarma_con_menos_confianza(monkeypatch):
    """El caso medido de beta2: regla `watch` 0,60 contra modelo `NEUTRAL` 0,35."""
    sig = _correr(monkeypatch, (SignalType.NEUTRAL, 0.35, "NEUTRAL"),
                  SignalType.WATCH, 0.60)
    assert sig.signal_type is SignalType.WATCH, "el modelo volvió a apagar la alarma"
    assert sig.confidence == 0.60
    assert sig.data["gano"] == "regla"


def test_la_regla_conserva_su_texto_cuando_gana(monkeypatch):
    sig = _correr(monkeypatch, (SignalType.NEUTRAL, 0.35, "NEUTRAL"),
                  SignalType.WATCH, 0.60, "Cymatic replica of M5 library")
    assert sig.reasoning == "Cymatic replica of M5 library", (
        "se reescribió el texto de quien decidió: el registro mentiría")


def test_el_modelo_gana_cuando_confia_mas(monkeypatch):
    """El caso de beta1: el modelo SÍ debe poder subir una alarma."""
    sig = _correr(monkeypatch, (SignalType.WATCH, 0.735, "WATCH"),
                  SignalType.NEUTRAL, 0.20)
    assert sig.signal_type is SignalType.WATCH
    assert sig.confidence == pytest.approx(0.735)
    assert sig.data["gano"] == "modelo"
    assert "ONNX" in sig.reasoning


def test_en_empate_exacto_manda_el_modelo(monkeypatch):
    """`>=`: aprendió de 19.578 firmas contra un umbral escrito a mano."""
    sig = _correr(monkeypatch, (SignalType.NEUTRAL, 0.40, "NEUTRAL"),
                  SignalType.WATCH, 0.40)
    assert sig.data["gano"] == "modelo"
    assert sig.signal_type is SignalType.NEUTRAL


def test_es_simetrico_no_privilegia_alarmar(monkeypatch):
    """Se descartó la opción asimétrica «puede subir pero nunca bajar». Con más
    confianza, el modelo baja la alarma; con menos, no."""
    baja = _correr(monkeypatch, (SignalType.NEUTRAL, 0.90, "NEUTRAL"),
                   SignalType.WATCH, 0.30)
    assert baja.signal_type is SignalType.NEUTRAL, "no bajó pese a más confianza"
    assert baja.data["gano"] == "modelo"


def test_las_dos_opiniones_se_registran_gane_quien_gane(monkeypatch):
    for salida, regla, conf_r, esperado in (
        ((SignalType.NEUTRAL, 0.35, "NEUTRAL"), SignalType.WATCH, 0.60, "regla"),
        ((SignalType.WATCH, 0.80, "WATCH"), SignalType.NEUTRAL, 0.20, "modelo"),
    ):
        sig = _correr(monkeypatch, salida, regla, conf_r)
        d = sig.data
        assert d["onnx"] is True
        assert d["onnx_senal"] == salida[2]
        assert d["regla_senal"] == regla.value
        assert d["gano"] == esperado


def test_gano_llega_al_juez():
    """Si no se persiste, saber quién decidió exigiría recalcular la comparación
    --- el mismo defecto que este bloque arregla."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import juez_cycle_register
    fuente = inspect.getsource(juez_cycle_register.register_cycle_predictions)
    assert '"gano"' in fuente, "el campo se calcula y se tira"


def test_si_el_modelo_calla_no_se_toca_nada(monkeypatch):
    sig = _correr(monkeypatch, None, SignalType.WATCH, 0.60, "regla dice watch")
    assert sig.signal_type is SignalType.WATCH
    assert sig.confidence == 0.60
    assert sig.reasoning == "regla dice watch"
    assert sig.data.get("onnx") is False
    assert "gano" not in sig.data, "no hubo empate que resolver"
