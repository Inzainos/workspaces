"""El 0,0 de «no lo sé» lo leyó el modelo como «Kp = 0», y costó 792 falsas alarmas.

Medido el 2026-09-27 sobre el ciclo 14419 y el histórico del Juez. La cadena:

  1. `omni_dataframe` se arma con magnetómetro y viento; nunca ha tenido columna
     `kp_index` (`data_pipeline.fetch_alfa1_data`).
  2. `agregados_omni` mapea `kp_index → kp_mean, kp_max`, así que no producía
     ninguno de los dos.
  3. `vector_para` rellena lo ausente con 0,0 --- documentado como «no lo sé».
  4. El modelo no puede saber eso: entrenó con esas posiciones y aprendió que
     0,0 es Kp CERO, quietud geomagnética extrema.
  5. Con el Kp real (1,94 / 3,0) el mismo modelo se abstiene; con 0,0 dice
     WATCH 0,7165.
  6. En el Juez: 792 `watch` FALSO_POSITIVO contra 5 ACIERTO, todos de la rama
     propia del agente. Cero desde la rama de reglas.
  7. La disciplina hundió el peso de alfa1 a 0,300 y cada rebuild lo devolvía a
     1,425, porque las firmas no pasan por ese vector.

Esta es la cuarta cara del mismo defecto: el cero que significa dos cosas.
"""
import numpy as np
import pytest


@pytest.fixture(scope="module")
def modelo():
    from sentinel_omega.core.onnx_mixin import inferencia_de
    inf = inferencia_de("alfa1")
    if inf is None:
        pytest.skip("sin modelo de alfa1 en disco")
    return inf


def _pred(modelo, rasgos):
    from sentinel_omega.core.features_onnx import vector_para
    vec = np.asarray(vector_para("alfa1", rasgos), dtype=np.float32).reshape(-1)
    conf, nombre = modelo.predict(vec)
    return nombre, float(conf)


# Los rasgos reales del ciclo 14419 que tocan a alfa1.
_CICLO = {
    "bz_mean": -0.2743169014084506,
    "bz_min": -4.43,
    "bz_mean_72h": -0.2743169014084506,
    "bz_deriv_std": 0.64443128713443,
    "viento_avg": 459.4935074100212,
    "viento_max": 505.7,
    "kp_mean": 1.941340782122905,
    "kp_max": 3.0,
}


def test_con_el_kp_real_el_modelo_se_abstiene(modelo):
    nombre, _ = _pred(modelo, _CICLO)
    assert nombre == "NO_SIGNAL", (
        f"con el Kp medido el modelo dijo {nombre}; el registro del ciclo 14419 "
        "dice que se abstuvo")


def test_con_el_kp_ausente_el_modelo_inventa_un_watch(modelo):
    """La prueba del fantasma: quitar el rasgo cambia la respuesta a WATCH con
    alta confianza. No es que el modelo mida algo distinto --- es que lee la
    ausencia como una medición."""
    sin_kp = {k: v for k, v in _CICLO.items() if not k.startswith("kp")}
    nombre, conf = _pred(modelo, sin_kp)
    assert (nombre, round(conf, 3)) == ("WATCH", 0.717), (
        f"el fantasma cambió de forma: ahora sale {nombre} {conf:.3f}")


def test_el_fantasma_es_mas_confiado_que_la_medicion(modelo):
    """Lo que lo hacía dañino: la respuesta al dato ausente pesa MÁS que la
    respuesta al dato real, así que ganaba el consenso."""
    _, conf_real = _pred(modelo, _CICLO)
    sin_kp = {k: v for k, v in _CICLO.items() if not k.startswith("kp")}
    _, conf_fantasma = _pred(modelo, sin_kp)
    assert conf_fantasma > conf_real * 2


def test_el_ciclo_canonico_si_trae_el_kp():
    """Por qué el arreglo funciona: el vector que el Juez registra saca el Kp de
    la serie de beta1, no del omni_dataframe."""
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher._build_live_features)
    assert 'features["kp_mean"]' in fuente
    assert "kp_series" in fuente
