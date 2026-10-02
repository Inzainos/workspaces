"""El orden de los rasgos del vector ONNX — UNA sola fuente de verdad.

Existe por lo que se encontró el 2026-09-25: el entrenamiento y la inferencia
construían el vector cada uno por su lado, y no coincidían.

    alfa1, posición 0:  entrenaba con `bz_mean` (media de la ventana de 72 h)
                        preguntaba con `bz_gsm` (valor instantáneo)
    alfa1, posición 4:  entrenaba con `bz_min`
                        preguntaba con `dst_index`   ← ni la misma magnitud
    omega, posiciones 7-8: entrenaba con bz_min y kp_max
                        preguntaba con la confianza de beta y su bandera

`onnx_config` solo declara CUÁNTOS rasgos (10, 8, 16…), nunca cuáles, así que
nada reventaba: el modelo respondía a un vector cuyas columnas no significaban
lo que había aprendido. Y de los ocho modelos que el reentrenamiento semanal
produce, solo alfa1 y omega se usan para inferir; los otros seis corren su rama
de reglas.

Quien construya un vector para un modelo ONNX usa `vector_para()`. Si el orden
cambia, cambia para los dos lados a la vez, y hay que REENTRENAR: un modelo
entrenado con un orden y preguntado con otro no avisa, solo se equivoca.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

# Dimensión de entrada de cada modelo (coincide con onnx_config.input_features).
BOT_DIMS: Dict[str, int] = {
    "alfa1": 10,
    "alfa2": 8,
    "beta1": 16,
    "beta2": 16,
    "delta": 16,
    "omega": 12,
    "loki": 8,
    "jupiter": 8,
}

# Las repeticiones son RELLENO deliberado, no descuidos: alfa2 tiene 3 rasgos
# reales para 8 posiciones. Mientras los dos lados usen esta misma tabla,
# repetir un valor es inofensivo --- redundancia, no falsedad. Es un defecto
# DISTINTO del que costó 792 falsas alarmas en alfa1: allí el problema era un
# rasgo AUSENTE que el modelo leía como un cero medido (ver
# `tests/test_fantasma_alfa1_kp_cero.py`). Repetir no inventa información;
# rellenar con 0,0 sí.
#
# Lo que sí hay que cuidar al tocar esta tabla: **un rasgo solo entra si existe
# en el material de ENTRENAMIENTO y en el CICLO VIVO.** Añadir uno que el ciclo
# no puede llenar es fabricar el fantasma a mano.
#
# alfa2 sigue con 3 y no se puede mejorar hoy: sus rasgos de ESA
# (`api/esa_frp.py`, verificado contra un producto real) llevan **una sola
# detección** en `tbl_frp_detecciones` --- un producto S3B del 2026-09-26,
# guerrero_gap, FRP 5,68 MW. Una fila no es material de entrenamiento. El
# vector de alfa2 cambia cuando haya historia, no antes.
FEATURE_ORDER: Dict[str, List[str]] = {
    # alfa1, 2026-10-02: las dos posiciones que repetían `proton_max` ahora
    # llevan la DENSIDAD de protones, que es la magnitud que sí existe.
    #
    # `proton_max` es el flujo >10 MeV: OMNI2 publica sus columnas 42-47 todas
    # en centinela y NOAA sirve 6 h, así que la tabla lo tenía en **178 de
    # 286.932 horas (0,062 %)** --- 26 de las 1.483 firmas de alfa1 ---, y el
    # launcher SÍ lo ponía en vivo. Era el espejo de la fuga de procedencia:
    # cero constante en el entrenamiento, valor real en producción.
    #
    # La densidad (OMNI2 col 23) tiene **97,7 %** de cobertura desde 1994,
    # mediana 5,70 n/cc, y en vivo la baja `fetch_solar_wind()` y llega hasta
    # `omni_dataframe` --- solo faltaba leerla. Lo documentaba la bitácora del
    # 20-sep: «`fetch_solar_wind()` sí baja `proton_speed`/`proton_density`,
    # pero `fetch_alfa1_data` renombra `proton_speed → plasma_speed`». El
    # arreglo de ese día cableó el flujo, que es la que no tiene historia.
    #
    # La dimensión NO cambia (10): se sustituye relleno por medición.
    "alfa1": [
        "bz_mean", "viento_avg", "densidad_prot_mean", "densidad_prot_max",
        "bz_min", "kp_mean", "kp_max", "bz_deriv_std",
        "viento_max", "bz_mean_72h",
    ],
    "alfa2": [
        "satellite_coverage_score", "satellite_thermal_anomalies",
        "satellite_clear_passes", "satellite_coverage_score",
        "satellite_clear_passes", "satellite_thermal_anomalies",
        "satellite_coverage_score", "satellite_thermal_anomalies",
    ],
    "beta1": [
        "kp_mean", "kp_max", "schumann_mean", "schumann_std",
        "sismo_count_win", "sismo_max_mag_win", "fase_lunar",
        "es_sicigia", "kp_max_72h", "sismo_count_72h",
        "schumann_mean", "schumann_std", "kp_mean", "kp_max",
        "fase_lunar", "sismo_max_mag_win",
    ],
    # beta2, rehecho el 2026-09-26. Tenía CUATRO rasgos repetidos cuatro veces,
    # y los cuatro llegan ausentes desde que `tbl_desgasificacion_raw` se paró
    # el 2026-07-31: un experto con dieciséis posiciones y cero materia. Ahora
    # lleva la MAREA TERRESTRE (`core/mareas.py`), que es el forzamiento que el
    # operador señaló y que se calcula por efemérides: sin API, sin huecos y
    # disponible para cualquier instante, pasado o futuro. Los cuatro rasgos
    # volcánicos se conservan --- son su dominio --- y vuelven solos el día que
    # la fuente se alimente otra vez.
    "beta2": [
        "marea_total", "marea_luna", "marea_sol", "marea_sicigia",
        "marea_dist_luna", "marea_rango_24h", "marea_max_24h", "marea_deriv",
        "so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
        "marea_total", "marea_sicigia", "marea_rango_24h", "marea_deriv",
    ],
    # `vix` NO está aquí, y el intento de añadirlo el 2026-09-27 quedó anotado
    # porque el error es instructivo: medí la cobertura de `vix` sobre las
    # firmas de delta+alfa2+padre JUNTAS y salió 6.959, así que lo añadí. Pero
    # padre tiene 14.289 de esas firmas y **delta tiene 0 de 676** --- el
    # 6.959 era de padre. Añadirlo así da al modelo una columna que vale 0 en
    # todo el entrenamiento y 14,87 en producción: el fantasma de alfa1 en
    # espejo, entrenar con cero e inferir con un dato real.
    #
    # Verificado además en el modelo reentrenado con `vix` dentro: la salida es
    # IDÉNTICA con vix 11, 14,87, 22 y 35. No lo usaba.
    #
    # La causa está en `entrenamiento.BOT_FEATURES["delta"]`, que construye sus
    # firmas con solo los cuatro `btc_*`. Ahí sí se añadió `vix`, así que las
    # firmas del PRÓXIMO rebuild lo llevarán. Cuando haya cobertura, entra aquí.
    # Primero el dato, después el vector.
    "delta": [
        "btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h",
        "btc_volatilidad", "btc_ret_win", "btc_vol_max",
        "btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h",
        "btc_volatilidad", "btc_ret_win", "btc_vol_max",
        "btc_vol_72h", "btc_ret_win",
    ],
    "omega": [
        "fase_lunar", "es_sicigia", "schumann_mean", "schumann_std",
        "bz_mean", "kp_mean", "viento_avg", "bz_min",
        "kp_max", "schumann_mean", "fase_lunar", "kp_max_72h",
    ],
    # loki y jupiter, corregidos el 2026-09-26. Pedían nombres que NO existen
    # ni en sus firmas ni en el ciclo (`bz`, `solar_wind`, `schumann_activity`,
    # `lod`, `latest_kp`, `storm_active`, `attention_z`, `corr_significant`):
    # de 8 rasgos, loki llenaba 3 y jupiter UNO. Los demás llegaban como 0.0,
    # que para el modelo significa «Bz cero, el Sol no emite rayos X», no «no lo
    # sé». Ahora llevan los nombres reales de sus firmas, todos con variación
    # medida.
    #
    # `lod` sale del vector de loki: la tabla de astronomía lleva parada desde
    # 2025-12-31 y el ciclo no puede llenarlo en vivo. **Un rasgo que no se
    # puede llenar al inferir no debe entrenarse** --- si no, el modelo aprende
    # de una columna que en producción siempre vale cero.
    "loki": [
        "bz_mean", "viento_avg", "schumann_mean", "vix",
        "kp_mean", "fase_lunar", "btc_volatilidad", "bz_min",
    ],
    "jupiter": [
        "kp_mean", "kp_max", "kp_max_72h", "schumann_mean",
        "schumann_std", "xray_mean", "xray_max", "trends_mean",
    ],
}


def vector_para(bot: str, rasgos: Mapping[str, object]) -> np.ndarray:
    """El vector del bot, con cada rasgo en SU posición y 0.0 donde falte.

    Cero es «no lo sé», no un valor medido. Es el mismo criterio que usa el
    entrenamiento, así que un rasgo ausente se comporta igual en los dos lados.
    """
    orden = FEATURE_ORDER[bot]
    dim = BOT_DIMS[bot]
    vec = np.zeros(dim, dtype=np.float32)
    for i, clave in enumerate(orden[:dim]):
        val = rasgos.get(clave)
        if val is None:
            continue
        try:
            fv = float(val)
        except (TypeError, ValueError):
            continue
        if np.isfinite(fv):
            vec[i] = fv
    return vec


# Nombre de columna cruda de OMNI → el agregado que espera el vector.
# La ventana de alfa1 son 72 h, así que `bz_mean` y `bz_mean_72h` salen de la
# misma serie; se dejan las dos claves porque el orden tiene las dos posiciones.
_AGREGADOS_OMNI = {
    "bz_gsm": (("bz_mean", "mean"), ("bz_min", "min"),
               ("bz_mean_72h", "mean"), ("bz_deriv_std", "deriv_std")),
    "plasma_speed": (("viento_avg", "mean"), ("viento_max", "max")),
    "proton_flux_10mev": (("proton_max", "max"),),
    "kp_index": (("kp_mean", "mean"), ("kp_max", "max")),
    # Densidad de protones: `fetch_solar_wind()` la trae y el `omni_dataframe`
    # la lleva intacta (el rename de `data_pipeline` solo toca `proton_speed`).
    # OJO: esta ventana es la del RTSW (~6 h) y la firma usa 336 h, así que
    # `launcher._build_live_features` la PISA con el agregado de la tabla ---
    # igual que hace con el Kp. Esto es el respaldo para cuando no hay conexión
    # a la base, no la vía principal.
    "proton_density": (("densidad_prot_mean", "mean"),
                       ("densidad_prot_max", "max")),
}


def agregados_omni(
    columnas: Sequence[str],
    matriz: Optional[np.ndarray],
) -> Dict[str, float]:
    """Los agregados de la ventana de OMNI, con los NOMBRES del vector.

    `matriz` es (muestras × columnas) y `columnas` dice qué es cada una. Sin
    esto, el agente mandaba los valores crudos del último instante en las
    posiciones de los promedios. Una columna que no viene, no se inventa: se
    queda fuera y `vector_para` pondrá 0.0.
    """
    fuera: Dict[str, float] = {}
    if matriz is None or len(matriz) == 0:
        return fuera
    for columna, salidas in _AGREGADOS_OMNI.items():
        if columna not in columnas:
            continue
        serie = np.asarray(matriz[:, list(columnas).index(columna)], dtype=float)
        serie = serie[np.isfinite(serie)]
        if serie.size == 0:
            continue
        for clave, como in salidas:
            if como == "mean":
                valor = float(np.mean(serie))
            elif como == "min":
                valor = float(np.min(serie))
            elif como == "max":
                valor = float(np.max(serie))
            else:  # deriv_std: cuánto se MUEVE, no cuánto vale
                valor = float(np.std(np.diff(serie))) if serie.size > 1 else 0.0
            if np.isfinite(valor):
                fuera[clave] = valor
    return fuera
