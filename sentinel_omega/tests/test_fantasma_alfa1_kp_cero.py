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


def test_con_el_kp_real_el_modelo_no_alarma(modelo):
    """Con el Kp medido (1,94 / 3,0) no hay alarma. Se afirma que NO alarma, no
    la etiqueta exacta: `NO_SIGNAL` y `NEUTRAL` son los dos «nada que
    reportar» y cuál de los dos sale depende del reentrenamiento."""
    nombre, conf = _pred(modelo, _CICLO)
    assert nombre not in ("WATCH", "ALERT"), (
        f"con el Kp medido el modelo alarmó ({nombre} {conf:.3f}); el registro "
        "del ciclo 14419 dice que no")


def test_con_el_kp_ausente_el_modelo_YA_NO_inventa_un_watch(modelo):
    """El fantasma MURIÓ con el rebuild y el reentreno del 2026-09-27.

    Esta prueba nació fijando el defecto --- con el Kp ausente el modelo de alfa1
    respondía `WATCH` 0,7165, y su propio texto decía: «si ya no alarma, esta
    prueba sobra: bórrala con una medición que lo respalde, no la relajes». La
    medición llegó, así que en vez de borrarla se le da la vuelta: ahora fija que
    la ausencia **no** alarma, que es el invariante que hay que proteger.

    La causa era la fuga de etiqueta por procedencia: `kp_mean` estaba en el
    vector de alfa1 y no en sus firmas, así que valía 0 en las 1.632 firmas ---
    toda la mitad etiquetada como alarma --- y el modelo aprendió que el cero ERA
    la etiqueta. Cerrada metiéndolo en `BOT_FEATURES` y regenerando las firmas
    (`tests/test_fuga_de_procedencia.py`).

    Medido tras el reentreno, sobre el vector vivo real:

        con el Kp ausente   NO_SIGNAL 0,2932    (antes WATCH 0,7165)
        con el Kp real      NO_SIGNAL 0,2755

    Si esto se pone rojo, el fantasma volvió --- y lo más probable es que alguien
    haya añadido un rasgo al vector sin añadirlo a `BOT_FEATURES`.
    """
    sin_kp = {k: v for k, v in _CICLO.items() if not k.startswith("kp")}
    nombre, conf = _pred(modelo, sin_kp)
    assert nombre not in ("WATCH", "ALERT"), (
        f"el fantasma VOLVIÓ: con el Kp ausente sale {nombre} {conf:.3f}. "
        "Revisa si un rasgo entró a FEATURE_ORDER sin entrar a BOT_FEATURES, y "
        "si las firmas se regeneraron después")


def test_la_asimetria_del_fantasma_desaparecio(modelo):
    """Lo que hacía dañino al fantasma era la ASIMETRÍA: la respuesta al dato
    ausente pesaba más del doble que la respuesta al dato real, así que ganaba el
    consenso. Medido antes: 0,7165 contra 0,3114 (2,3x). Después: 0,2932 contra
    0,2755 (1,06x).

    No se exige que la ausencia pese MENOS --- un modelo puede ser algo más o
    menos confiado sin que eso sea un defecto. Se exige que no vuelva a pesar el
    doble, que es lo que le daba el voto.
    """
    _, conf_real = _pred(modelo, _CICLO)
    sin_kp = {k: v for k, v in _CICLO.items() if not k.startswith("kp")}
    _, conf_fantasma = _pred(modelo, sin_kp)
    assert conf_fantasma <= conf_real * 2, (
        f"la ausencia volvió a pesar más del doble que la medición "
        f"({conf_fantasma:.3f} contra {conf_real:.3f})")


def test_el_ciclo_canonico_si_trae_el_kp():
    """Por qué el arreglo funciona: el vector que el Juez registra saca el Kp de
    la serie de beta1, no del omni_dataframe."""
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher._build_live_features)
    assert 'features["kp_mean"]' in fuente
    assert "kp_series" in fuente
