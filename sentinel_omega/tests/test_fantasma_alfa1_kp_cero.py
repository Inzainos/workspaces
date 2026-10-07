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

Addendum del 2026-10-07 --- cómo NO leer el rojo de este archivo
----------------------------------------------------------------
Las dos primeras pruebas se pusieron rojas y su mensaje mandó a buscar una fuga
de procedencia que **no existía**: medido ese día, cero rasgos en
`FEATURE_ORDER` fuera de `BOT_FEATURES` en los nueve bots, y cero declarados
fuera de `FEATURE_KEYS`. Se perdió medio día, y la conclusión que casi se tomó
---apagar el modelo de alfa1--- habría sido correcta por un motivo falso.

La distinción que faltaba escrita, y que la bitácora §22.2 ya tenía:

    el fantasma es ASIMETRÍA, no «alarmar»

Antes del arreglo: ausencia 0,7165 contra dato real 0,3114 --- **2,3x**, y por
eso ganaba el consenso. Después: 1,06x. Medido el 2026-10-07 con el modelo del
4-oct: **1,016x** con los huecos de densidad y **1,002x** con densidad real. La
fuga sigue muerta.

Lo que sí pasaba el 7-oct es que ese modelo alarmaba en TODAS las
configuraciones (0,608 / 0,599 / 0,715), con AUC 0,467 por nodo y 0,511 global
---azar--- y 18 falsos positivos contra 1 acierto en sus 19 watches vivos. Eso
es el objetivo degenerado del entrenamiento, que es un defecto distinto y vive
en `train_onnx_from_db.py`, no aquí.

Regla práctica: **si `test_la_asimetria_del_fantasma_desaparecio` está verde, el
fantasma no ha vuelto**, por rojas que estén las otras dos.
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
#
# Son OCHO de las diez posiciones del vector, y las dos que faltan
# ---`densidad_prot_mean` y `densidad_prot_max`--- están ausentes **porque lo
# estaban**: `tbl_clima_espacial_raw.densidad_protones` se añadió el 2026-10-02
# y la ventana de 336 h de este ciclo tiene **0 lecturas no nulas** (medido el
# 2026-10-07). `vector_para` las pone en 0,0, que es «no lo sé», igual que hizo
# la ruta viva ese día.
#
# NO las rellenes. Poner un número aquí sería dato sintético (regla 2) y además
# cambia la respuesta ---medido con la densidad de octubre, el mismo modelo pasa
# de `WATCH` 0,6081 a `WATCH` 0,7153---, así que inventarlas convertiría esta
# prueba en una afirmación sobre un ciclo que nunca existió.
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


# Qué revisar cuando estas dos se pongan rojas, EN ESTE ORDEN.
#
# El mensaje viejo mandaba directo a «un rasgo entró a FEATURE_ORDER sin entrar
# a BOT_FEATURES». El 2026-10-07 se puso rojo y esa pista era falsa: la fuga
# estaba cerrada en los nueve bots y se perdió medio día persiguiéndola, con el
# agravante de que la conclusión que casi se tomó ---apagar el modelo de alfa1---
# se habría tomado por un motivo inexistente.
#
# El fantasma tiene una firma propia, y es la ASIMETRÍA. Mientras
# `test_la_asimetria_del_fantasma_desaparecio` siga en verde, el fantasma NO ha
# vuelto, por mucho que estas dos estén rojas: lo que falla entonces es el nivel
# del modelo, que es otro defecto y se arregla en otro sitio.
_QUE_REVISAR = (
    "QUÉ REVISAR, en este orden: "
    "(1) ¿está verde `test_la_asimetria_del_fantasma_desaparecio`? Si SÍ, el "
    "fantasma no ha vuelto --- la fuga se manifiesta como asimetría >2x entre "
    "el dato ausente y el real, no como alarmar. Pasa al (3). "
    "(2) si está ROJA, entonces sí es la fuga: corre "
    "`test_fuga_de_procedencia.py` y busca el rasgo que entró a FEATURE_ORDER "
    "sin entrar a BOT_FEATURES, y si las firmas se regeneraron después. "
    "(3) si la asimetría está bien, esto es NIVEL, no fantasma: el modelo "
    "llama alarma a un ciclo que el registro da por calmo. Mira la fecha del "
    "`.onnx` y qué reentrenamiento lo produjo. El del 2026-10-04 daba `WATCH` "
    "0,608 aquí, con AUC 0,467 por nodo y 0,511 global (azar) y 18 falsos "
    "positivos contra 1 acierto en 19 watches vivos. Eso es el objetivo "
    "degenerado del entrenamiento, no esta fuga."
)


def test_con_el_kp_real_el_modelo_no_alarma(modelo):
    """Con el Kp medido (1,94 / 3,0) no hay alarma. Se afirma que NO alarma, no
    la etiqueta exacta: `NO_SIGNAL` y `NEUTRAL` son los dos «nada que
    reportar» y cuál de los dos sale depende del reentrenamiento."""
    nombre, conf = _pred(modelo, _CICLO)
    assert nombre not in ("WATCH", "ALERT"), (
        f"con el Kp medido el modelo alarmó ({nombre} {conf:.3f}); el registro "
        f"del ciclo 14419 dice que no. {_QUE_REVISAR}")


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

    Si esto se pone rojo, **no concluyas todavía que el fantasma volvió**: el
    fantasma se manifiesta como ASIMETRÍA, y eso lo mide la prueba siguiente.
    Que el modelo alarme con el Kp ausente Y con el Kp real a la vez es otro
    defecto --- nivel, no procedencia. Ver `_QUE_REVISAR`.
    """
    sin_kp = {k: v for k, v in _CICLO.items() if not k.startswith("kp")}
    nombre, conf = _pred(modelo, sin_kp)
    assert nombre not in ("WATCH", "ALERT"), (
        f"con el Kp ausente sale {nombre} {conf:.3f}. {_QUE_REVISAR}")


def test_la_asimetria_del_fantasma_desaparecio(modelo):
    """Lo que hacía dañino al fantasma era la ASIMETRÍA: la respuesta al dato
    ausente pesaba más del doble que la respuesta al dato real, así que ganaba el
    consenso. Medido antes: 0,7165 contra 0,3114 (2,3x). Después: 0,2932 contra
    0,2755 (1,06x).

    No se exige que la ausencia pese MENOS --- un modelo puede ser algo más o
    menos confiado sin que eso sea un defecto. Se exige que no vuelva a pesar el
    doble, que es lo que le daba el voto.

    **Esta es la prueba que decide si el fantasma volvió**, no las dos de
    arriba. Medido el 2026-10-07 con el modelo del 4-oct: 1,016x con los huecos
    de densidad de este ciclo y 1,002x con densidad real. Las otras dos estaban
    rojas ese día y el fantasma seguía muerto; ver el addendum del módulo.
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
