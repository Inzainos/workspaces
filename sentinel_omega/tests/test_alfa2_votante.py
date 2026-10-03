"""alfa2 vota y avisa (2026-10-02) --- y vota con su REGLA, no con un modelo
entrenado sobre ruido.

Cómo pasó de notificador a votante
----------------------------------
Estaba en `BOTS_ESPERANDO_SENALES` desde el 2026-09-24 porque sus tres rasgos
nunca llegaban a `MIN_DIMENSIONES_COMPARABLES` (4): sin cuatro dimensiones
`similitud()` devuelve 0,0 y una firma no empareja ni consigo misma. De ese
3 < 4 colgaba todo: no formaba firmas, no recibía peso, y el tablero lo
rotulaba notificador.

La condición escrita para que saliera era «cuando la capa satelital aporte una
cuarta señal real». Se cumplió con `satellite_revisita_dias`, y la elección se
MIDIÓ sobre las 3.231 filas del histórico satelital (70 días):

    revisit_days      153 valores distintos, 100 % de cobertura
                      p10 0,32 · p50 0,51 · p75 0,72 · p90 0,86 · max 1,68 d
    coverage_score    136 distintos
    total_passes       54 distintos
    clear_passes       31 distintos

Y no es redundante con el puntaje aunque éste la use: su término es
`max(0, 1 - revisita/12) * 0,3`, con tope en 12 DÍAS mientras la realidad vive
entre 0 y 1,7. Medido: el término solo se mueve de 0,2580 a 0,3000 --- el
puntaje aplana el 98,6 % de esta señal.

Resultado: 19 firmas, 15 consolidadas, 1.966 recurrencias y **peso 1,0** en su
primera pasada. Asertividad 0,996 con 2.125 aciertos.

Por qué el ONNX queda APAGADO
-----------------------------
Al reentrenarlo el trazo dijo `alfa2: hybrid real=23 + boot=2500 → 2684`: un
99 % sintético de `train_onnx_bootstrap.gen_alfa2`. Y cinco de sus ocho
columnas llevan OTRA MAGNITUD que las del vector vigente --- la posición 4 del
prior es `revisit` (1-14 d) donde el vector tiene `coverage_score` (0,30-0,93);
la 5 es `cloud` (0-1) donde el vector tiene `clear_passes` (~5.437). Las
dimensiones cuadran (8 = 8), así que `test_onnx_dims` no puede verlo: solo
cuenta posiciones.

Un modelo así no responde a los rasgos, responde a ruido en sus posiciones. Así
que alfa2 vota con su regla, que sí es honesta, hasta tener material real.
"""
import pytest

from sentinel_omega.config.onnx_config import onnx_config
from sentinel_omega.core.features_onnx import BOT_DIMS, FEATURE_ORDER
from sentinel_omega.core.firmas.signature_engine import (
    FEATURE_KEYS, MIN_DIMENSIONES_COMPARABLES,
)
from sentinel_omega.infrastructure.pipeline.entrenamiento import (
    BOTS_ESPERANDO_SENALES, BOT_FEATURES, MIN_FEATURES_POR_BOT,
)

CUARTA = "satellite_revisita_dias"


def test_alfa2_ya_no_espera_senales():
    assert "alfa2" not in BOTS_ESPERANDO_SENALES, (
        "alfa2 volvió a notificador: si fue a propósito, documenta por qué su "
        "cuarta señal dejó de servir")


def test_alfa2_alcanza_el_suelo_de_emparejamiento():
    """El 3 < 4 del que colgaba todo. Ahora son cuatro."""
    rasgos = BOT_FEATURES["alfa2"]
    assert len(rasgos) >= MIN_DIMENSIONES_COMPARABLES, rasgos
    assert len(rasgos) >= MIN_FEATURES_POR_BOT["alfa2"], rasgos


def test_la_cuarta_senal_esta_en_los_tres_sitios():
    """`FEATURE_KEYS` o la firma la descarta en silencio; `BOT_FEATURES` o no
    se guarda; `FEATURE_ORDER` o el modelo no la lee."""
    assert CUARTA in FEATURE_KEYS
    assert CUARTA in BOT_FEATURES["alfa2"]
    assert CUARTA in FEATURE_ORDER["alfa2"]


def test_alfa2_no_cambio_de_dimension():
    """Entró en posiciones que repetían relleno: 4 rasgos reales en 8."""
    assert BOT_DIMS["alfa2"] == 8
    assert len(FEATURE_ORDER["alfa2"]) == 8
    assert len(set(FEATURE_ORDER["alfa2"])) == 4, (
        f"alfa2 ya no tiene cuatro rasgos distintos: "
        f"{sorted(set(FEATURE_ORDER['alfa2']))}")


def test_el_onnx_de_alfa2_esta_apagado_a_proposito():
    """Vota con su regla hasta tener muestras reales. `try_load_onnx` honra
    este flag (onnx_mixin.py:31) y deja la razón en el log."""
    assert onnx_config.alfa2.enabled is False, (
        "se encendió el ONNX de alfa2: comprueba que su reentreno diga "
        "'db-only (N)' y NO 'hybrid', o votará con ruido sintético")


def test_alfa2_no_tiene_prior_sintetico():
    """Sin prior, `merge_or_bootstrap` toma el camino «NO se reentrena» y
    conserva el modelo en disco --- lo que pide su propio comentario:
    «inventar muestras para rellenar sería peor que no reentrenar»."""
    from sentinel_omega.models.train_onnx_from_db import bootstrap_xy

    # Se comprueba el COMPORTAMIENTO, no el texto: una primera versión de esta
    # prueba buscaba "gen_alfa2" en el código fuente y casaba con el comentario
    # que explica por qué se quitó.
    assert bootstrap_xy("alfa2") is None, (
        "alfa2 volvió al prior sintético: cinco de sus ocho columnas llevan "
        "otra magnitud que el vector y las dimensiones cuadran, así que "
        "test_onnx_dims no lo caza")


def test_el_prior_sintetico_sigue_declarando_a_quien_SI_lo_usa():
    """No se borró el mecanismo: los otros conservan su prior. Pero su
    alineación NO está medida --- si a alguno le bajan las muestras reales por
    debajo del mínimo, hay que comprobar columna por columna antes."""
    from sentinel_omega.models.train_onnx_from_db import bootstrap_xy

    for bot in ("alfa1", "beta1", "beta2", "delta", "omega"):
        assert bootstrap_xy(bot) is not None, f"desapareció el prior de {bot}"


def test_la_revisita_no_es_redundante_con_el_puntaje():
    """La razón medida de por qué se eligió ésta y no otra: el puntaje la usa
    pero la aplana. Con tope de 12 días y realidad de 0-1,7, su término solo se
    mueve de 0,2580 a 0,3000 --- el 1,4 % del rango que podría ocupar."""
    from sentinel_omega.core.alfa2_zonas import puntaje_zona

    base = dict(total_passes=8, clear_passes=5, muestras_nube=10)
    p_min = puntaje_zona(**base, mean_revisit_days=0.0)
    p_max = puntaje_zona(**base, mean_revisit_days=1.68)
    recorrido = abs(p_min - p_max)
    assert recorrido < 0.05, (
        f"el puntaje ya NO aplana la revisita (recorrido {recorrido:.4f}): "
        "si el tope cambió, vuelve a medir si la cuarta señal sigue aportando")
