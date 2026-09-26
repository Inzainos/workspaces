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
import pytest

from sentinel_omega.config.onnx_config import onnx_config
from sentinel_omega.core.features_onnx import BOT_DIMS, FEATURE_ORDER


def test_la_config_conoce_los_ocho_modelos():
    conocidos = set(onnx_config.get_enabled_models())
    assert conocidos == set(BOT_DIMS), (
        f"faltan en onnx_config: {set(BOT_DIMS) - conocidos}")


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


def test_los_ocho_modelos_cargan():
    from sentinel_omega.core.onnx_mixin import inferencia_de
    sin_cargar = [b for b in BOT_DIMS if inferencia_de(b) is None]
    assert not sin_cargar, f"no cargan: {sin_cargar}"
