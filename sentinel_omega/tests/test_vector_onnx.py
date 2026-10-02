"""Entrenar y preguntar tienen que usar el MISMO vector.

Origen (2026-09-25): el entrenamiento y la inferencia construían el vector cada
uno por su lado y no coincidían. alfa1 entrenaba con `bz_mean` (media de 72 h)
en la posición 0 y se le preguntaba con `bz_gsm` (instantáneo); en la posición 4
entrenaba con `bz_min` y se le pasaba `dst_index`, que no es ni la misma
magnitud. omega ponía la confianza de beta donde el modelo espera `bz_min`.
Nada reventaba: `onnx_config` solo declara CUÁNTOS rasgos, nunca cuáles.
"""
import numpy as np
import pytest

from sentinel_omega.core.features_onnx import (
    BOT_DIMS,
    FEATURE_ORDER,
    agregados_omni,
    vector_para,
)


def test_el_entrenamiento_usa_la_fuente_unica():
    from sentinel_omega.models import train_onnx_from_db as tr
    assert tr.FEATURE_ORDER is FEATURE_ORDER
    assert tr.BOT_DIMS is BOT_DIMS


def test_cada_orden_cabe_en_su_dimension():
    for bot, dim in BOT_DIMS.items():
        assert len(FEATURE_ORDER[bot]) >= dim, bot


def test_cada_rasgo_cae_en_su_posicion():
    orden = FEATURE_ORDER["alfa1"]
    vec = vector_para("alfa1", {"bz_min": -9.0, "kp_max": 7.0})
    assert vec[orden.index("bz_min")] == pytest.approx(-9.0)
    assert vec[orden.index("kp_max")] == pytest.approx(7.0)
    assert vec[orden.index("viento_avg")] == 0.0     # ausente = 0, no inventado


def test_un_rasgo_que_no_existe_no_entra():
    # `dst_index` no está en el orden de alfa1: mandarlo no debe mover nada.
    assert not np.any(vector_para("alfa1", {"dst_index": 999.0}))


# ─── Los agregados de la ventana, que es lo que el modelo aprendió ───────────

def _ventana():
    cols = ["bz_gsm", "plasma_speed", "proton_flux_10mev", "kp_index"]
    m = np.array([
        [-5.0, 400.0, 1.0, 3.0],
        [-1.0, 600.0, 2.0, 5.0],
        [-3.0, 500.0, 0.5, 4.0],
    ])
    return cols, m


def test_los_agregados_son_de_la_ventana_no_del_ultimo_instante():
    cols, m = _ventana()
    a = agregados_omni(cols, m)
    assert a["bz_mean"] == pytest.approx(-3.0)      # media, no el último (-3)
    assert a["bz_min"] == pytest.approx(-5.0)
    assert a["viento_avg"] == pytest.approx(500.0)
    assert a["viento_max"] == pytest.approx(600.0)
    assert a["proton_max"] == pytest.approx(2.0)
    assert a["kp_mean"] == pytest.approx(4.0)
    assert a["kp_max"] == pytest.approx(5.0)


def test_bz_deriv_std_mide_cuanto_se_mueve():
    cols, m = _ventana()
    a = agregados_omni(cols, m)
    assert a["bz_deriv_std"] == pytest.approx(np.std(np.diff([-5.0, -1.0, -3.0])))


def test_una_columna_que_falta_no_se_inventa():
    a = agregados_omni(["bz_gsm"], np.array([[-4.0], [-2.0]]))
    assert "bz_mean" in a and "kp_mean" not in a
    assert vector_para("alfa1", a)[FEATURE_ORDER["alfa1"].index("kp_mean")] == 0.0


def test_sin_ventana_no_hay_agregados():
    assert agregados_omni(["bz_gsm"], None) == {}
    assert agregados_omni(["bz_gsm"], np.empty((0, 1))) == {}


def test_los_nan_no_contaminan_la_media():
    a = agregados_omni(["bz_gsm"], np.array([[-4.0], [np.nan], [-2.0]]))
    assert a["bz_mean"] == pytest.approx(-3.0)


# ─── Los dos agentes que SÍ infieren con ONNX ────────────────────────────────

def test_alfa1_no_pregunta_a_su_modelo_por_su_cuenta():
    """Un modelo, un vector, un sitio.

    Hasta el 2026-09-27 alfa1 inferí­a dos veces: aquí con los agregados de su
    propia ventana OMNI, y en `_aplicar_modelos` con el vector canónico del
    ciclo. En el ciclo 14419 dieron respuestas OPUESTAS --- WATCH 72 % y
    NO_SIGNAL 31 % --- porque `omni_dataframe` no tiene columna `kp_index`
    (nunca la ha tenido: se arma con magnetómetro y viento), así que `kp_mean`
    y `kp_max` llegaban como 0,0 y el modelo los leía como «Kp = 0», quietud
    extrema, no como «no lo sé».

    Coste medido en el Juez: 792 `watch` FALSO_POSITIVO contra 5 ACIERTO, todos
    de esa rama; cero desde la rama de reglas.
    """
    import inspect

    from sentinel_omega.layers.geodynamic.alfa1 import agent

    assert not hasattr(agent.Alfa1Agent, "_analyze_onnx"), (
        "volvió la segunda inferencia: el Juez registra el vector canónico, "
        "así que un veredicto sobre otro vector no se puede auditar")
    fuente = inspect.getsource(agent.Alfa1Agent)
    assert "_inference.predict(" not in fuente, (
        "el agente pregunta al modelo; eso le toca a _aplicar_modelos")


def test_el_vector_canonico_sigue_siendo_quien_pregunta():
    """Lo que se quitó del agente tiene que seguir existiendo en el runner."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import layer_runners

    fuente = inspect.getsource(layer_runners.GeodynamicLayerRunner._aplicar_modelos)
    assert "senal_desde_rasgos(" in fuente
    assert "_rasgos_del_ciclo()" in fuente


def test_kp_no_puede_salir_del_dataframe_de_omni():
    """La raíz del fantasma: `agregados_omni` mapea `kp_index`, pero
    `omni_dataframe` se arma solo con magnetómetro y viento. Si algún día se
    añade Kp ahí, esta prueba avisa de que hay DOS fuentes para las mismas dos
    posiciones y hay que decidir cuál manda."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import data_pipeline

    fuente = inspect.getsource(data_pipeline.GeodynamicPipeline.fetch_alfa1_data)
    # El dataframe sale de un concat de los `frames` que se van agregando.
    armado = fuente.split("omni_df = pd.concat")[0]
    agregados = [l.strip() for l in armado.splitlines() if "frames.append(" in l]
    assert agregados, "cambió el armado del omni_dataframe; revisar esta prueba"
    assert all("kp" not in l.lower() for l in agregados), (
        "entró Kp al omni_dataframe: ahora hay DOS fuentes de kp_mean/kp_max "
        "(esta y la kp_series de beta1 en launcher.py) y hay que decidir cuál "
        "manda --- es lo que produjo el fantasma de alfa1")


def _fuente_feature_vector() -> str:
    """El código de `_feature_vector`, entero.

    Antes se cortaba con `fuente[i:i + 2000]`, una ventana de bytes fija, y al
    crecer la función con comentarios la aserción dejaba de alcanzar la línea
    que buscaba: la prueba se ponía roja sin que el código cambiara de
    comportamiento. `inspect.getsource` de la función devuelve justo su cuerpo.
    """
    import inspect

    from sentinel_omega.layers.geodynamic.omega.agent import OmegaAgent
    return inspect.getsource(OmegaAgent._feature_vector)


def test_omega_pregunta_con_el_orden_canonico():
    bloque = _fuente_feature_vector()
    assert 'vector_para("omega"' in bloque
    assert "return [fase, sicigia" not in bloque


def test_omega_no_mete_la_senal_de_beta_en_el_vector():
    # beta_conf/beta_alert ocupaban las posiciones de bz_min y kp_max.
    bloque = _fuente_feature_vector()
    ini = bloque.index("candidatos = {")
    rasgos = bloque[ini:bloque.index("}", ini)]
    assert "beta_conf" not in rasgos and "beta_alert" not in rasgos


def test_el_vector_de_omega_tiene_su_dimension():
    orden = FEATURE_ORDER["omega"]
    vec = vector_para("omega", {"bz_min": -7.0, "kp_max": 6.0, "fase_lunar": 0.5})
    assert len(vec) == BOT_DIMS["omega"] == 12
    assert vec[orden.index("bz_min")] == pytest.approx(-7.0)
    assert vec[orden.index("kp_max")] == pytest.approx(6.0)


# ─── Lo que el ciclo GUARDA tiene que cubrir lo que el modelo PIDE ───────────

def test_el_ciclo_guarda_todos_los_rasgos_de_alfa1():
    """Revisando la tubería entera (2026-09-25) salió un desajuste más fino:
    `_build_live_features` calculaba a mano solo bz_mean, bz_min, viento_avg y
    viento_max, así que el Juez guardaba proton_max, bz_deriv_std y bz_mean_72h
    vacíos --- y el reentrenamiento habría aprendido «aquí siempre hay un 0»
    mientras la inferencia manda valores reales."""
    pd = pytest.importorskip("pandas")
    from sentinel_omega.launcher import _build_live_features

    df = pd.DataFrame({
        "bz_gsm": [-5.0, -9.0, -3.0],
        "plasma_speed": [400.0, 600.0, 500.0],
        "proton_flux_10mev": [1.0, 4.0, 2.0],
        "kp_index": [3.0, 5.0, 4.0],
        # `proton_density` entró al vector de alfa1 el 2026-10-02 en lugar de
        # `proton_max`, que ocupaba dos posiciones sin dato. La trae
        # `fetch_solar_wind()` y el `omni_dataframe` la lleva de verdad ---
        # verificado en vivo: 1.399 valores, mediana 3,58 n/cc.
        "proton_density": [4.0, 7.0, 5.0],
    })

    class _Pipeline:
        _cache = {"alfa1": {"omni_dataframe": df}}

    class _Runner:
        pipeline = _Pipeline()

    rasgos = _build_live_features(_Runner())
    faltan = [k for k in FEATURE_ORDER["alfa1"] if k not in rasgos]
    assert not faltan, f"el ciclo no guarda: {sorted(set(faltan))}"
    assert rasgos["proton_max"] == pytest.approx(4.0)
    assert rasgos["bz_mean_72h"] == pytest.approx(rasgos["bz_mean"])


def test_el_ciclo_usa_el_mismo_agregador_que_la_inferencia():
    import inspect
    from sentinel_omega import launcher
    fuente = inspect.getsource(launcher._build_live_features)
    assert "agregados_omni(" in fuente
    # La regresión: calcularlos a mano aquí y olvidar la mitad.
    assert 'features["bz_mean"] = float(bz.mean())' not in fuente
