"""Arquitectura de expertos: cada bot opina con SU modelo.

Hasta el 2026-09-26, de los ocho modelos que produce el reentrenamiento semanal
solo DOS se usaban para inferir (alfa1 y omega). Los otros seis corrían su rama
de reglas, y dos de ellos (loki, jupiter) ni siquiera tenían entrada en
`onnx_config`, así que el cargador devolvía None y no podían cargarse nunca.

Eso deformaba la disciplina, que es lo que lo destapó: **el que no alarma no
puede ser castigado por alarmar**. Medido ese día:

    alfa1    669 alarmas, 664 falsos positivos  ->  peso 0.300 (el suelo)
    jupiter  216 alarmas, 216 falsos positivos  ->  peso 1.000
    loki       0 alarmas,   0 castigos, 37 eventos perdidos -> peso 1.000
    delta      0 alarmas,   0 castigos, 37 eventos perdidos -> peso 1.000

Un experto que no opina no aporta al consenso y tampoco se puede corregir.
"""
from pathlib import Path

import pytest

from sentinel_omega.config.onnx_config import onnx_config
from sentinel_omega.core.features_onnx import BOT_DIMS, FEATURE_ORDER


# Modelos APAGADOS a propósito. Se declaran aquí, y no se afloja la prueba: su
# CONFIG y su ARCHIVO siguen verificándose como los demás; lo único que no se
# exige es que se les pregunte.
#
#   alfa2 (2026-10-02) — su reentreno salía `hybrid real=23 + boot=2500`, 99 %
#     sintético, y cinco de las ocho columnas del prior llevan otra magnitud
#     que el vector. Ver `tests/test_alfa2_votante.py`.
#
#   beta1, delta, loki, omega (2026-10-07) — los ONNX de `53f51e7` salieron
#     CONSTANTES: desviación típica de la confianza 0,0100-0,0183 sobre 27
#     ciclos, contra 0,1663 de alfa1. Cinco bots alarmaron el 100 % de los
#     ciclos dos días, con ganancia de Molchan 0,81x --- peor que el azar.
#     Ver `tests/test_modelos_constantes.py` y la nota de `onnx_config`.
APAGADOS_A_PROPOSITO = {"alfa2", "beta1", "beta2", "delta", "loki", "omega"}


def test_la_config_conoce_los_ocho_modelos():
    """Los ocho siguen declarados; `get_enabled_models` filtra los apagados."""
    conocidos = set(onnx_config.get_enabled_models()) | APAGADOS_A_PROPOSITO
    assert conocidos == set(BOT_DIMS), (
        f"faltan en onnx_config: {set(BOT_DIMS) - conocidos}")


def test_los_apagados_siguen_declarando_su_dimension():
    """Apagar no es borrar: si mañana se enciende, su config tiene que seguir
    cuadrando con el vector o `inferencia_de` lo descartará igual."""
    for bot in APAGADOS_A_PROPOSITO:
        cfg = getattr(onnx_config, bot)
        assert cfg.enabled is False
        assert cfg.input_features == BOT_DIMS[bot], (
            f"{bot}: apagado y además con la dimensión mal ({cfg.input_features} "
            f"contra {BOT_DIMS[bot]})")


def test_cada_modelo_declara_las_dimensiones_de_su_vector():
    for bot, cfg in onnx_config.get_enabled_models().items():
        assert cfg.input_features == BOT_DIMS[bot], (
            f"{bot}: config dice {cfg.input_features}, el vector tiene "
            f"{BOT_DIMS[bot]}")


def test_ningun_rasgo_es_inventado():
    """Un rasgo que el ciclo no puede llenar llega como 0.0 al vector, y 0.0
    para el modelo significa «Bz cero», no «no lo sé». loki pedía `bz`,
    `solar_wind` y `lod`; jupiter pedía `attention_z` y `corr_significant`:
    nombres que no existen ni en sus firmas ni en el ciclo."""
    prohibidos = {"bz", "solar_wind", "schumann_activity", "lod",
                  "latest_kp", "storm_active", "attention_z", "corr_significant"}
    for bot, orden in FEATURE_ORDER.items():
        malos = prohibidos & set(orden)
        assert not malos, f"{bot} pide rasgos que nadie produce: {malos}"


def test_el_ciclo_aplica_los_modelos():
    import inspect

    from sentinel_omega.infrastructure.pipeline import layer_runners
    fuente = inspect.getsource(layer_runners.GeodynamicLayerRunner)
    assert "_aplicar_modelos" in fuente
    # Antes del consenso: el Padre tiene que ver las señales ya corregidas.
    i = fuente.index("self._aplicar_modelos(signals)")
    j = fuente.index("self.padre.evaluate_consensus(signals)")
    assert i < j


def test_el_veredicto_del_modelo_queda_anotado():
    """Para que el Juez pueda comparar después quién acertaba: la regla o el
    modelo."""
    import inspect

    from sentinel_omega.infrastructure.pipeline.layer_runners import (
        GeodynamicLayerRunner,
    )
    fuente = inspect.getsource(GeodynamicLayerRunner._aplicar_modelos)
    for clave in ("onnx_senal", "onnx_conf", "regla_senal", "regla_conf"):
        assert clave in fuente


def test_delta_nunca_vota_alerta():
    """Su techo es WATCH por diseño: el estrés financiero es contexto
    correlacionable, no evidencia sísmica."""
    import inspect

    from sentinel_omega.infrastructure.pipeline.layer_runners import (
        GeodynamicLayerRunner,
    )
    fuente = inspect.getsource(GeodynamicLayerRunner._aplicar_modelos)
    assert 'SIN_ALERTA = {"delta"}' in fuente
    assert "permitir_alerta=bot not in SIN_ALERTA" in fuente


def test_sin_modelo_manda_la_regla():
    from sentinel_omega.core.onnx_mixin import senal_desde_rasgos
    assert senal_desde_rasgos("no_existe_este_bot", {"x": 1.0}) is None


def test_un_vector_vacio_no_se_pregunta():
    """Pedir una predicción sobre todo ceros es pedir ruido."""
    from sentinel_omega.core.onnx_mixin import senal_desde_rasgos
    assert senal_desde_rasgos("delta", {}) is None
    assert senal_desde_rasgos("delta", {"rasgo_que_no_usa": 5.0}) is None


def test_los_modelos_encendidos_cargan():
    """Los apagados a propósito se excluyen; el resto tiene que cargar, o el
    bot cae a reglas sin que nadie lo haya decidido."""
    from sentinel_omega.core.onnx_mixin import inferencia_de
    sin_cargar = [b for b in BOT_DIMS
                  if b not in APAGADOS_A_PROPOSITO and inferencia_de(b) is None]
    assert not sin_cargar, f"no cargan: {sin_cargar}"


def test_el_archivo_del_apagado_sigue_en_disco_y_con_su_dimension():
    """Lo que la prueba anterior ya no cubre, cubierto aquí: el `.onnx` de un
    bot apagado existe y declara la dimensión del vector. Así «apagado» no
    puede tapar «roto»."""
    import onnxruntime as ort

    from sentinel_omega.core.onnx_mixin import dimension_de_entrada

    for bot in APAGADOS_A_PROPOSITO:
        cfg = getattr(onnx_config, bot)
        ruta = Path(onnx_config.models_dir) / cfg.model_path
        assert ruta.exists(), f"{bot}: falta {ruta.name}"
        s = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
        assert dimension_de_entrada(s) == BOT_DIMS[bot], (
            f"{bot}: el archivo en disco no cuadra con el vector")
