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

Esta prueba NO exige cero fugas: exige que no CREZCAN. Arreglar una pide meter el
rasgo en `BOT_FEATURES` y un rebuild que regenere las firmas, y hasta entonces la
deuda queda fijada aquí, contada y visible.
"""
import pytest

from sentinel_omega.core.features_onnx import FEATURE_ORDER
from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES

# Deuda MEDIDA el 2026-09-27. Para bajar un número hay que meter el rasgo en
# BOT_FEATURES y regenerar las firmas; entonces se actualiza aquí con la
# medición que lo respalde. Subir un número es una regresión.
FUGAS_CONOCIDAS = {
    "alfa1": {"kp_max", "kp_mean"},
    # Las 8 de marea las añadió Claude el 2026-09-26 al vector de beta2 sin
    # añadirlas a BOT_FEATURES. La «mejora de discriminación de 0,0948 a 0,3994»
    # que se reportó ese día era el modelo detectando la procedencia.
    "beta2": {"marea_deriv", "marea_dist_luna", "marea_luna", "marea_max_24h",
              "marea_rango_24h", "marea_sicigia", "marea_sol", "marea_total"},
    "omega": {"bz_mean", "kp_mean", "viento_avg"},
    "loki": {"btc_volatilidad", "bz_min", "fase_lunar", "kp_mean"},
}


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


def test_el_padre_no_puede_tener_fuga():
    """`BOT_FEATURES["padre"] = None` significa vector cruzado completo."""
    assert BOT_FEATURES.get("padre", "ausente") is None


def test_el_total_de_deuda_esta_contado():
    """17 rasgos en 4 bots. El número va en la bitácora y en el CHANGELOG."""
    total = sum(len(v) for v in FUGAS_CONOCIDAS.values())
    assert total == 17, f"la deuda cambió a {total}: actualiza la documentación"
