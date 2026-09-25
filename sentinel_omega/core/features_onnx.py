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
# reales para 8 posiciones y beta2 cuatro para 16. Mientras los dos lados usen
# esta misma tabla, repetir un valor es inofensivo.
FEATURE_ORDER: Dict[str, List[str]] = {
    "alfa1": [
        "bz_mean", "viento_avg", "proton_max", "proton_max",
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
    "beta2": [
        "so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
        "so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
        "so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
        "so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
    ],
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
    "loki": [
        "bz", "solar_wind", "schumann_activity", "vix", "lod",
        "kp_mean", "fase_lunar", "btc_volatilidad",
    ],
    "jupiter": [
        "latest_kp", "storm_active", "attention_z", "corr_significant",
        "kp_mean", "xray_mean", "trends_mean", "schumann_mean",
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
