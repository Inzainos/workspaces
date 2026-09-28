"""Un rasgo del vector que la firma no puede llenar es una FUGA DE ETIQUETA.

Encontrado el 2026-09-27: el diagnóstico de Agente-C sobre el Kp, generalizado.

El entrenamiento ONNX junta dos mitades con etiquetas opuestas:

  * `TBL_FIRMAS` --- construidas desde eventos, así que casi todas llevan
    etiqueta de ALARMA;
  * `TBL_JUEZ_AUDITORIA` de la fase viva --- ciclos en su mayoría en calma,
    etiqueta NEUTRAL.

`signature_engine` solo puede llenar en una firma los rasgos que estén en
`BOT_FEATURES[bot]`. Si el vector (`FEATURE_ORDER[bot]`) pide uno que no está
ahí, ese rasgo vale **0 en toda la mitad etiquetada como alarma** y un valor real
en la mitad neutral. El modelo no aprende el rasgo: aprende **de qué tabla vino
la fila**.

Medido ese día, y los conteos no dejan lugar a duda:

    bot      firmas   filas con rasgo=0   P(alarma|0)   P(alarma|>0)
    alfa1     1.632         1.632            98,8 %        1,4 %
    loki        858           858           100,0 %        1,4 %
    omega       307           307            96,7 %        1,2 %
    beta2       806           806            99,8 %        1,5 %

Consecuencia en producción: con el Kp geomagnético decayendo de forma natural
(kp_max 3 → 1 el 27-sep), alfa1, loki y omega pasaron a **WATCH en 10 de cada 10
ciclos** --- el modelo no distingue «campo quieto» de «sin dato», porque el cero
era la etiqueta.

**Cerrada en el código el 2026-09-27 (tarde).** Los 17 rasgos están declarados y
la lista de deuda quedó vacía. Cada uno entró con su cobertura MEDIDA sobre las
ventanas reales que forma cada bot, no sobre el agregado:

    bot     rasgos añadidos                                   cobertura
    alfa1   kp_mean, kp_max                                     100 %
    omega   bz_mean, kp_mean, viento_avg                        100 %
    loki    kp_mean, fase_lunar, bz_min, btc_volatilidad        100 %  (858/858)
    beta2   las 8 de marea                                      100 %  (efemérides)

Las 8 de marea pedían además abrirles paso en `FEATURE_KEYS`: no estaban, así que
el filtro `{k: v for k, v in features.items() if k in FEATURE_KEYS}` las habría
descartado en silencio y la lista de deuda habría bajado a cero **sin que la
firma las llevara**. Ese es el modo de fallo que esta prueba tiene que impedir, y
por eso `test_lo_declarado_existe_de_verdad` es tan importante como el conteo.

**Lo que el código NO puede arreglar solo:** las firmas ya guardadas no cambian.
Hasta que un rebuild las regenere y se reentrenen los 8 ONNX, el vector sigue
leyendo 0 en la mitad etiquetada como alarma. La verificación de que la fuga
murió es que `P(alarma | rasgo=0)` colapse del 98-100 % a la tasa base --- y esa
medición también hay que verificarla.
"""
import pytest

from sentinel_omega.core.features_onnx import FEATURE_ORDER
from sentinel_omega.core.firmas.signature_engine import FEATURE_KEYS
from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES

# Lo que se MIDIÓ el 2026-09-27. Es historia, no deuda: no se vacía cuando el
# rasgo se arregla, porque el hecho medido sigue siendo verdad y hay cosas
# ancladas a él --- `layer_runners.RASGOS_CON_FUGA` (el tapón de Agente-C) tiene
# que cubrir exactamente estos rasgos hasta que el rebuild regenere las firmas y
# se reentrenen los modelos.
FUGAS_MEDIDAS_2026_09_27 = {
    "alfa1": {"kp_max", "kp_mean"},
    # Las 8 de marea las añadió Claude el 2026-09-26 al vector de beta2 sin
    # añadirlas a BOT_FEATURES. La «mejora de discriminación de 0,0948 a 0,3994»
    # que se reportó ese día era el modelo detectando la procedencia.
    "beta2": {"marea_deriv", "marea_dist_luna", "marea_luna", "marea_max_24h",
              "marea_rango_24h", "marea_sicigia", "marea_sol", "marea_total"},
    "omega": {"bz_mean", "kp_mean", "viento_avg"},
    "loki": {"btc_volatilidad", "bz_min", "fase_lunar", "kp_mean"},
}

# Deuda PENDIENTE de declarar. Vacía desde el 2026-09-27 (tarde): los 17 rasgos
# medidos arriba están en `BOT_FEATURES`. Un nombre aquí es una fuga que se
# decidió tolerar, y va con su medición al lado; añadir uno sin medición es
# volver al problema.
FUGAS_CONOCIDAS: dict = {}


def _fugas(bot):
    bf = BOT_FEATURES.get(bot)
    if bf is None:          # el padre lleva el vector completo: no hay fuga posible
        return set()
    return set(FEATURE_ORDER[bot]) - set(bf)


@pytest.mark.parametrize("bot", sorted(FEATURE_ORDER))
def test_la_fuga_no_crece(bot):
    """Añadir un rasgo al vector sin añadirlo a BOT_FEATURES lo convierte en un
    detector de procedencia. Si esta prueba falla, es eso."""
    nuevas = _fugas(bot) - FUGAS_CONOCIDAS.get(bot, set())
    assert not nuevas, (
        f"{bot}: {sorted(nuevas)} está en FEATURE_ORDER y NO en BOT_FEATURES. "
        "Su firma no lo puede llenar, así que valdrá 0 en toda la mitad "
        "etiquetada como alarma y el modelo aprenderá la procedencia, no el "
        f"rasgo. Mételo en BOT_FEATURES['{bot}'] y regenera las firmas.")


@pytest.mark.parametrize("bot", sorted(FUGAS_CONOCIDAS))
def test_las_fugas_arregladas_se_borran_de_la_lista(bot):
    """Lo contrario: si una fuga ya se arregló, hay que sacarla de aquí para que
    la lista no mienta sobre la deuda que queda."""
    resueltas = FUGAS_CONOCIDAS[bot] - _fugas(bot)
    assert not resueltas, (
        f"{bot}: {sorted(resueltas)} ya está en BOT_FEATURES --- sácalo de "
        "FUGAS_CONOCIDAS, con el conteo que lo respalde")


def test_los_bots_limpios_siguen_limpios():
    """alfa2, beta1, delta y jupiter no tenían ninguna el 2026-09-27."""
    for bot in ("alfa2", "beta1", "delta", "jupiter"):
        assert _fugas(bot) == set(), f"{bot} perdió su vector limpio: {_fugas(bot)}"


@pytest.mark.parametrize("bot", sorted(b for b, v in BOT_FEATURES.items() if v))
def test_lo_declarado_existe_de_verdad(bot):
    """Declarar un rasgo que `FEATURE_KEYS` no conoce es un arreglo FALSO.

    El filtro de `registrar` descarta en silencio toda clave que no esté en
    `FEATURE_KEYS`, así que un nombre inventado hace bajar el conteo de fugas
    sin que la firma lleve nada. Las 8 de marea estaban exactamente así: en el
    vector ONNX desde el 2026-09-26 y ausentes de `FEATURE_KEYS` hasta hoy.

    Es la regla dura 10 --- un descarte silencioso esconde el fallo --- aplicada
    a la corrección, no al defecto.
    """
    huerfanos = sorted(k for k in BOT_FEATURES[bot] if k not in FEATURE_KEYS)
    assert not huerfanos, (
        f"{bot} declara {huerfanos}, que no existen en FEATURE_KEYS: la firma "
        "los descartaría sin decir nada y el rasgo valdría 0 igual que antes")


def test_la_marea_llega_a_la_firma():
    """Que el rasgo esté declarado no prueba que la extracción lo produzca.

    Esta es la comprobación de punta a punta (regla 0): se pide la ventana de un
    evento y se exige que las ocho claves salgan con un número finito. La marea
    se calcula por efemérides, así que no necesita ninguna tabla poblada ---
    razón por la que cubre el 100 % de las ventanas, incluidas las de 1994.
    """
    from sentinel_omega.core.firmas.signature_engine import _marea_de_ventana

    esperadas = {"marea_total", "marea_luna", "marea_sol", "marea_sicigia",
                 "marea_dist_luna", "marea_rango_24h", "marea_max_24h",
                 "marea_deriv"}
    for ts in ("1994-03-05 00:00", "2014-11-20 03:00", "2026-09-01 12:00"):
        vals = dict(_marea_de_ventana(ts))
        assert esperadas <= set(vals), f"{ts}: faltan {esperadas - set(vals)}"
        assert vals["marea_total"] > 0.0, f"{ts}: la Luna no puede no tirar"
    # Y que sean las MISMAS ocho que el vector de beta2 pide.
    assert esperadas == {k for k in FEATURE_ORDER["beta2"] if k.startswith("marea")}


def test_el_padre_no_puede_tener_fuga():
    """`BOT_FEATURES["padre"] = None` significa vector cruzado completo."""
    assert BOT_FEATURES.get("padre", "ausente") is None


def test_la_medicion_historica_sigue_completa():
    """17 rasgos en 4 bots. `layer_runners.RASGOS_CON_FUGA` se ancla a esto
    (`tests/test_claves_omega_loki.py`, de Agente-C), así que borrarlo porque «ya
    está arreglado» dejaría al tapón sin referencia."""
    total = sum(len(v) for v in FUGAS_MEDIDAS_2026_09_27.values())
    assert total == 17, f"la medición cambió a {total}: eso es reescribir historia"
    assert set(FUGAS_MEDIDAS_2026_09_27) == {"alfa1", "beta2", "omega", "loki"}


def test_el_tapon_cubre_lo_medido_mientras_no_se_reentrene():
    """Las firmas guardadas siguen sin los rasgos: hasta el rebuild y el
    reentreno, el modelo de esos bots tiene que seguir callado."""
    from sentinel_omega.infrastructure.pipeline import layer_runners

    tapon = getattr(layer_runners, "RASGOS_CON_FUGA", None)
    if tapon is None:
        pytest.skip("no hay tapón en este árbol")
    for bot, medidos in FUGAS_MEDIDAS_2026_09_27.items():
        cubiertos = set(tapon.get(bot, ()))
        assert cubiertos <= medidos, (
            f"{bot}: el tapón calla rasgos que no se midieron con fuga: "
            f"{sorted(cubiertos - medidos)}")


def test_no_queda_deuda_declarada():
    """Eran 17 rasgos en 4 bots el 2026-09-27 por la mañana; ahora cero.

    Si esto falla, alguien toleró una fuga nueva: que venga con su medición de
    cobertura al lado, como las cuatro que se cerraron.
    """
    total = sum(len(v) for v in FUGAS_CONOCIDAS.values())
    assert total == 0, f"deuda declarada: {FUGAS_CONOCIDAS}"


def test_ningun_bot_tiene_fuga_hoy():
    """El conteo directo, sin pasar por la lista de tolerados."""
    vivas = {b: sorted(_fugas(b)) for b in FEATURE_ORDER if _fugas(b)}
    assert not vivas, f"fugas vivas: {vivas}"
