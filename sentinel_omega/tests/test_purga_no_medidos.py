"""El relleno no es una medición, y entrenar con él desalinea la inferencia.

Medido el 2026-09-27, después del segundo rebuild: las firmas quedaron limpias
de Schumann (0 de 19.578, contra 397 antes) y aun así los ocho modelos se
reentrenaron viendo `schumann_mean = 8.26`. El entrenamiento lee de DOS fuentes
y solo se había limpiado una:

    TBL_JUEZ_AUDITORIA.detalles_json        387 filas con 8.26
    tbl_juez_rasgos_reconstruidos            72 filas con 8.26

El 8,26 es `7.83 + 21.46 × 0.02`: la fundamental de libro más una actividad
CONGELADA. El daño no es el valor, es que el ciclo en vivo entrega ausencia
(0,0) y el entrenamiento entregaba 8,26: el modelo aprendía con un número y se
le preguntaba con otro.
"""
import numpy as np

from sentinel_omega.models.train_onnx_from_db import purgar_no_medidos


def test_una_media_sin_desviacion_no_es_un_agregado_de_ventana():
    """El criterio es la FORMA, no el nombre ni el valor: un agregado de
    ventana produce media *y* dispersión."""
    fuera = purgar_no_medidos({"schumann_mean": 8.26, "bz_mean": -3.1})
    assert "schumann_mean" not in fuera, "el relleno entró al entrenamiento"
    assert fuera["bz_mean"] == -3.1, "se llevó por delante un rasgo bueno"


def test_una_lectura_con_su_dispersion_pasa_intacta():
    """Si Tomsk vuelve, la serie real trae las dos y no se toca. Filtrar por
    NOMBRE sería el mismo defecto al revés."""
    fuera = purgar_no_medidos({"schumann_mean": 7.91, "schumann_std": 0.13})
    assert fuera["schumann_mean"] == 7.91
    assert fuera["schumann_std"] == 0.13


def test_no_filtra_por_el_valor_8_26():
    """El valor envejece mal: cambió de fórmula dos veces (7,83 y 24,7x salen
    de la MISMA actividad 21,46). Un 8,26 con dispersión es una lectura."""
    fuera = purgar_no_medidos({"schumann_mean": 8.26, "schumann_std": 0.02})
    assert fuera["schumann_mean"] == 8.26


def test_una_desviacion_huerfana_no_se_toca():
    """Sin media que acompañar no hay nada que decidir; no se inventa un borrado."""
    fuera = purgar_no_medidos({"schumann_std": 0.4})
    assert fuera == {"schumann_std": 0.4}


def test_no_muta_el_diccionario_de_quien_llama():
    """El `detalles_json` del Juez se reusa; purgar no puede borrarlo en sitio."""
    dentro = {"schumann_mean": 8.26}
    purgar_no_medidos(dentro)
    assert dentro == {"schumann_mean": 8.26}


def test_el_relleno_no_llega_al_vector_del_modelo():
    """De punta a punta: lo que sale de la purga, pasado por la fuente única,
    pone 0,0 --- la misma ausencia que ve el ciclo en vivo."""
    from sentinel_omega.core.features_onnx import FEATURE_ORDER, vector_para

    rasgos = purgar_no_medidos({"schumann_mean": 8.26, "kp_mean": 2.0})
    vec = vector_para("beta1", rasgos)
    for i, nombre in enumerate(FEATURE_ORDER["beta1"]):
        if nombre == "schumann_mean":
            assert vec[i] == 0.0, f"posición {i} recibió relleno, no ausencia"
    assert np.any(vec > 0), "se vació el vector entero, no solo el relleno"
