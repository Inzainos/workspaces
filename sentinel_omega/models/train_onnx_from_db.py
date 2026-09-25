#!/usr/bin/env python3
"""
Reentrenamiento ONNX desde firmas reales (TBL_FIRMAS) + histórico.

Prioridad de datos:
  1. Features de TBL_FIRMAS (features_json) mapeadas al vector ONNX del bot
  2. Si hay pocas muestras (< MIN_SAMPLES), mezcla con bootstrap físico
  3. Si la DB está vacía, solo bootstrap (equivalente a train_onnx_bootstrap)

Exporta a sentinel_omega/models/*.onnx — listo para los agentes.

Uso:
  python -m sentinel_omega.models.train_onnx_from_db --db-path data/SENTINEL_OMEGA_PRO.db
  python sentinel_omega/models/train_onnx_from_db.py --db-path ... --min-samples 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ONNX_RETRAIN] %(levelname)s %(message)s",
)
logger = logging.getLogger("onnx_retrain")

MODELS_DIR = Path(__file__).resolve().parent
MIN_SAMPLES = 80
RANDOM_SEED = 42

# ─── Coste de equivocarse, que es lo que pesa cada muestra ────────────────────
#
# Medido el 2026-09-25 sobre la fase viva: de 19.422 muestras del Juez, 19.089
# (98,3 %) enseñaban NEUTRAL y 333 (1,7 %) enseñaban ALARMAR --- 57 a 1 a favor
# de callarse, porque la calma es casi todo. Sin pesos, un FALLO (callarse y que
# pase algo) contaba EXACTAMENTE lo mismo que un falso positivo, cuando el Juez
# castiga el primero diez veces más. La asimetría del diseño --- que existe para
# que los bots no se acostumbren al silencio --- no llegaba al entrenamiento: el
# domingo siguiente los modelos habrían aprendido a callar.
#
# Por eso cada muestra pesa el coste de EQUIVOCARSE en su ventana: si hubo
# evento, equivocarse es perderlo (10); si hubo calma, equivocarse es dar una
# falsa alarma (1). Así el desbalance efectivo baja de 57:1 a 5,7:1 y queda
# exactamente en la proporción que el operador eligió al fijar las severidades.
#
# Se usan las severidades BASE del Juez, no la columna `severidad` de la
# auditoría: esa lleva gravedad² y un multiplicador de reincidencia acumulativa,
# y medida ese día iba de 12,5 a 22.080 (mediana 1.384). Con esos números tres
# muestras se comerían el bosque entero.
try:
    from sentinel_omega.core.juez.juez import (
        SEVERIDAD_FALLO_BASE as _SEV_EVENTO,
        SEVERIDAD_FALSO_POSITIVO as _SEV_CALMA,
    )
except Exception:  # noqa: BLE001 — el reentrenamiento corre igual
    _SEV_EVENTO, _SEV_CALMA = 10.0, 1.0

PESO_BOOTSTRAP = 1.0   # el prior sintético no manda sobre lo medido

BOT_DIMS = {
    "alfa1": 10,
    "alfa2": 8,
    "beta1": 16,
    "beta2": 16,
    "delta": 16,
    "omega": 12,
    "loki": 8,
    "jupiter": 8,
}

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

NO_SIGNAL, NEUTRAL, WATCH, ALERT, BULLISH, BEARISH = 0, 1, 2, 3, 4, 5

EVENT_CLASS_LABEL = {
    "SISMO_M7": (ALERT, 0.90),
    "SISMO_M6": (ALERT, 0.80),
    "SISMO_M5": (WATCH, 0.65),
    "SISMO_M4": (WATCH, 0.50),
    "ERUPCION_VEI5": (ALERT, 0.85),
    "ERUPCION_VEI4": (ALERT, 0.75),
    "ERUPCION_VEI3": (WATCH, 0.55),
    "TORMENTA_Kp9": (ALERT, 0.90),
    "TORMENTA_Kp7": (ALERT, 0.80),
    "TORMENTA_Kp6": (WATCH, 0.60),
    "TSUNAMI_M7": (ALERT, 0.90),
    "TSUNAMI_M6": (ALERT, 0.75),
    "VOLCAN": (WATCH, 0.55),
    "DEFAULT": (NEUTRAL, 0.30),
}

ESTADO_BOOST = {
    "consolidada": 0.10,
    "recurrente": 0.05,
    "observada": 0.02,
    "nueva": 0.0,
}


def _label_from_row(event_class: str, estado: str) -> Tuple[float, float]:
    sig, conf = EVENT_CLASS_LABEL.get(event_class, EVENT_CLASS_LABEL["DEFAULT"])
    conf = min(0.95, conf + ESTADO_BOOST.get(estado, 0.0))
    return float(conf), float(sig)


def _features_to_vector(features: dict, bot: str) -> np.ndarray:
    order = FEATURE_ORDER[bot]
    dim = BOT_DIMS[bot]
    vec = np.zeros(dim, dtype=np.float32)
    for i, key in enumerate(order[:dim]):
        val = features.get(key)
        if val is None:
            continue
        try:
            fv = float(val)
            if np.isfinite(fv):
                vec[i] = fv
        except (TypeError, ValueError):
            pass
    return vec


def load_firmas_from_db(db_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """bot -> (X, y_conf, y_sig)"""
    out: Dict[str, list] = {b: [] for b in BOT_DIMS}
    path = Path(db_path)
    if not path.exists():
        logger.warning(f"DB no existe: {db_path}")
        return {}

    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT bot_name, event_class, estado, features_json FROM TBL_FIRMAS"
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning(f"No se pudo leer TBL_FIRMAS: {e}")
        conn.close()
        return {}
    conn.close()

    logger.info(f"Firmas en DB: {len(rows)}")
    for bot_name, event_class, estado, features_json in rows:
        bot = (bot_name or "").lower()
        if bot not in BOT_DIMS:
            continue
        try:
            features = json.loads(features_json) if features_json else {}
        except json.JSONDecodeError:
            continue
        if not isinstance(features, dict) or not features:
            continue
        vec = _features_to_vector(features, bot)
        if not np.any(np.abs(vec) > 1e-12):
            continue
        conf, sig = _label_from_row(event_class or "DEFAULT", estado or "nueva")
        out[bot].append((vec, conf, sig))

    result = {}
    for bot, samples in out.items():
        if not samples:
            continue
        X = np.stack([s[0] for s in samples]).astype(np.float32)
        y_conf = np.array([s[1] for s in samples], dtype=np.float32)
        y_sig = np.array([s[2] for s in samples], dtype=np.float32)
        result[bot] = (X, y_conf, y_sig)
        logger.info(f"  {bot}: {len(samples)} firmas reales")
    return result


def load_juez_feedback(db_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Etiquetas y PESOS desde TBL_JUEZ_AUDITORIA (ACIERTO/FALLO/FALSO_POSITIVO).

    El peso de cada muestra es el coste de equivocarse en su ventana (ver
    _SEV_EVENTO / _SEV_CALMA arriba): sin él, callarse ante un evento pesaba lo
    mismo que una falsa alarma y el entrenamiento aprendía a callar.
    """
    out: Dict[str, list] = {b: [] for b in BOT_DIMS}
    sin_rasgos: Dict[str, int] = {}
    path = Path(db_path)
    if not path.exists():
        return {}
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT bot_name, prediccion, confianza, resultado, detalles_json "
            "FROM TBL_JUEZ_AUDITORIA "
            "WHERE resultado IN ('ACIERTO','FALLO','FALSO_POSITIVO') "
            "AND fase = 'viva'"
        ).fetchall()
    except sqlite3.Error as e:
        logger.info(f"Juez sin filas útiles: {e}")
        conn.close()
        return {}
    conn.close()
    logger.info(f"Juez feedback vivo: {len(rows)} filas")
    for bot_name, prediccion, confianza, resultado, det_json in rows:
        bot = (bot_name or "").lower()
        if bot in ("padre", "padre_geo"):
            bot = "omega"
        if bot not in BOT_DIMS:
            continue
        features = {}
        try:
            det = json.loads(det_json) if det_json else {}
            if isinstance(det, dict):
                features = {k: v for k, v in det.items() if isinstance(v, (int, float))}
                # `features_generales` es DONDE están los rasgos físicos del
                # ciclo (bz_mean, kp_mean, schumann_mean, so2_kt_win…). La
                # clave se añadió el 2026-08-20 para que el Juez pudiera
                # enseñar, y este lector nunca la abrió: leía las de primer
                # nivel y las de firma_matches, que son metadatos de la firma
                # (firma_id, similitud, recurrencia), no señales. Otra señal
                # medida y no conectada.
                generales = det.get("features_generales")
                if isinstance(generales, dict):
                    features.update(
                        {k: v for k, v in generales.items() if isinstance(v, (int, float))}
                    )
                for m in (det.get("firma_matches") or [])[:1]:
                    if isinstance(m, dict):
                        features.update({k: v for k, v in m.items() if isinstance(v, (int, float))})
        except json.JSONDecodeError:
            pass
        vec = _features_to_vector(features, bot)
        pred = (prediccion or "").lower()
        conf0 = float(confianza or 0.3)
        # `peso` = coste de equivocarse en esta ventana. La ventana tuvo evento
        # en los dos casos en que el Juez lo vio: el FALLO (lo perdió) y el
        # ACIERTO por haber alarmado. Las otras dos casillas son ventanas en
        # calma, donde el error posible es la falsa alarma.
        if resultado == "ACIERTO":
            if pred in ("alert", "watch"):
                sig, conf = (ALERT if pred == "alert" else WATCH), min(0.95, conf0 + 0.05)
                peso = _SEV_EVENTO
            else:
                sig, conf = NEUTRAL, 0.35
                peso = _SEV_CALMA
        elif resultado == "FALSO_POSITIVO":
            sig, conf = NEUTRAL, 0.2
            peso = _SEV_CALMA
        else:
            sig, conf = ALERT, 0.7
            peso = _SEV_EVENTO
        # Si el vector sale vacío, la muestra NO ENTRA. Antes se rellenaba con
        # `vec[0] = conf`, que es fabricar el rasgo a partir de la etiqueta: el
        # modelo aprendía «con esta confianza, esta salida», sin mirar una sola
        # señal física. Medido el 2026-09-25: las 19.422 muestras vivas daban
        # vector de ceros --- el detalles_json guarda `firma_matches` (firma_id,
        # similitud, recurrencia, nodo_lat/lon), que no está en el FEATURE_ORDER
        # de ningún bot --- y eran entre el 57 % y el 100 % del entrenamiento
        # «real» de cada uno. Miles de entradas idénticas con un 98 % de
        # etiquetas NEUTRAL enseñan a callar pase lo que pase, y encima diluyen
        # las firmas, que sí traen rasgos. Faltante es faltante.
        if not np.any(np.abs(vec) > 1e-12):
            sin_rasgos[bot] = sin_rasgos.get(bot, 0) + 1
            continue
        out[bot].append((vec, conf, float(sig), float(peso)))
    if sin_rasgos:
        logger.warning(
            "Juez: %d muestras DESCARTADAS por no traer rasgos (%s). La "
            "auditoría guarda firma_matches, no el vector con el que el bot "
            "predijo: hasta que se registre eso, del Juez no se puede aprender.",
            sum(sin_rasgos.values()),
            ", ".join(f"{b}:{n}" for b, n in sorted(sin_rasgos.items())),
        )
    result = {}
    for bot, samples in out.items():
        if not samples:
            continue
        X = np.stack([s[0] for s in samples]).astype(np.float32)
        y_conf = np.array([s[1] for s in samples], dtype=np.float32)
        y_sig = np.array([s[2] for s in samples], dtype=np.float32)
        w = np.array([s[3] for s in samples], dtype=np.float32)
        result[bot] = (X, y_conf, y_sig, w)
        n_ev = int((w == _SEV_EVENTO).sum())
        logger.info(
            f"  juez/{bot}: {len(samples)} muestras "
            f"({n_ev} de ventanas con evento, peso x{_SEV_EVENTO:.0f})"
        )
    return result


def _con_pesos(xy, peso: float = PESO_BOOTSTRAP):
    """Normaliza a (X, y_conf, y_sig, pesos). Lo que no trae peso pesa `peso`:
    las firmas y el prior sintético no llevan coste asociado."""
    if xy is None:
        return None
    if len(xy) == 4:
        return xy
    X, yc, ys = xy
    return X, yc, ys, np.full(len(X), peso, dtype=np.float32)


def _merge_xy(a, b):
    a, b = _con_pesos(a), _con_pesos(b)
    if not a:
        return b
    if not b:
        return a
    X = np.vstack([a[0], b[0]]).astype(np.float32)
    yc = np.concatenate([a[1], b[1]]).astype(np.float32)
    ys = np.concatenate([a[2], b[2]]).astype(np.float32)
    w = np.concatenate([a[3], b[3]]).astype(np.float32)
    return X, yc, ys, w


def bootstrap_xy(bot: str, n: int = 2500):
    """Prior sintético del bot, o None si no existe generador para él.

    `loki` y `jupiter` no tienen: son los dos más nuevos. Devolver None en vez
    de reventar con KeyError importa desde el 2026-09-25, cuando se dejaron de
    admitir las muestras sin rasgos: hasta entonces jupiter llegaba al
    entrenamiento con 2.158 vectores vacíos y nunca pedía el prior.
    """
    sys.path.insert(0, str(MODELS_DIR.parent.parent))
    from sentinel_omega.models.train_onnx_bootstrap import (
        gen_alfa1, gen_alfa2, gen_beta1, gen_beta2, gen_delta, gen_omega,
    )
    gens = {
        "alfa1": gen_alfa1, "alfa2": gen_alfa2, "beta1": gen_beta1,
        "beta2": gen_beta2, "delta": gen_delta, "omega": gen_omega,
    }
    if bot not in gens:
        return None
    X, y_conf, y_sig = gens[bot](n)
    return X.astype(np.float32), y_conf.astype(np.float32), y_sig.astype(np.float32)


def merge_or_bootstrap(
    bot: str,
    firmas: Dict[str, Tuple[np.ndarray, ...]],
    min_samples: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """Devuelve (X, y_conf, y_sig, pesos, descripción). Los pesos viajan con las
    muestras: si se remuestrea lo real, su peso se remuestrea igual."""
    disponible = _con_pesos(firmas.get(bot))
    if disponible is not None and len(disponible[0]) >= min_samples:
        X, yc, ys, w = disponible
        return X, yc, ys, w, f"db-only ({len(X)})"
    prior = _con_pesos(bootstrap_xy(bot))
    if prior is None:
        # Sin prior y sin datos suficientes no se entrena NADA: se conserva el
        # modelo que ya está en disco. Inventar muestras para rellenar sería
        # peor que no reentrenar.
        n = 0 if disponible is None else len(disponible[0])
        return None, None, None, None, (
            f"NO se reentrena: {n} muestras reales (<{min_samples}) y sin prior")
    Xb, ycb, ysb, wb = prior
    if disponible is None or len(disponible[0]) == 0:
        return Xb, ycb, ysb, wb, f"bootstrap-only ({len(Xb)})"
    Xf, ycf, ysf, wf = disponible
    target_real = max(len(Xf), min(len(Xb) // 2, max(min_samples, len(Xf) * 8)))
    idx = np.random.default_rng(RANDOM_SEED).choice(len(Xf), size=target_real, replace=True)
    X = np.vstack([Xf[idx], Xb]).astype(np.float32)
    yc = np.concatenate([ycf[idx], ycb]).astype(np.float32)
    ys = np.concatenate([ysf[idx], ysb]).astype(np.float32)
    w = np.concatenate([wf[idx], wb]).astype(np.float32)
    return X, yc, ys, w, f"hybrid real={len(Xf)}+boot={len(Xb)} → {len(X)}"


def train_export(
    bot: str,
    X: np.ndarray,
    y_conf: np.ndarray,
    y_sig: np.ndarray,
    pesos: Optional[np.ndarray] = None,
) -> Path:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.multioutput import MultiOutputRegressor
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    y = np.column_stack([y_conf, y_sig])
    model = MultiOutputRegressor(
        RandomForestRegressor(
            n_estimators=80, max_depth=10, min_samples_leaf=3,
            random_state=RANDOM_SEED, n_jobs=-1,
        )
    )
    # sample_weight es lo que lleva la asimetría del Juez al bosque: perder un
    # evento pesa diez veces una falsa alarma. Sin esto, con 57 calmas por cada
    # evento el modelo aprende a decir NEUTRAL siempre.
    if pesos is not None:
        model.fit(X, y, sample_weight=pesos)
    else:
        model.fit(X, y)
    pred = model.predict(X)
    mae = float(np.mean(np.abs(pred[:, 0] - y_conf)))
    peso_info = ""
    if pesos is not None:
        peso_info = (f"  pesos: min={pesos.min():.0f} max={pesos.max():.0f} "
                     f"suma={pesos.sum():.0f}")
    logger.info(f"  {bot}: train MAE conf={mae:.4f}  n={len(X)}{peso_info}")

    onnx_model = convert_sklearn(
        model,
        initial_types=[("input", FloatTensorType([None, X.shape[1]]))],
        target_opset=12,
    )
    names = {
        "alfa1": "alfa1_spaceweather_rf.onnx",
        "alfa2": "alfa2_satellite_cnn.onnx",
        "beta1": "beta1_schumann_fft.onnx",
        "beta2": "beta2_atmospheric_cnn.onnx",
        "delta": "delta_financial_lstm.onnx",
        "omega": "omega_espacial_rf.onnx",
        "loki": "loki_unificado_rf.onnx",
        "jupiter": "jupiter_attention_rf.onnx",
    }
    out = MODELS_DIR / names[bot]
    with open(out, "wb") as f:
        f.write(onnx_model.SerializeToString())
    logger.info(f"  wrote {out.name} ({out.stat().st_size} bytes)")
    return out


def retrain(db_path: str, min_samples: int = MIN_SAMPLES, bots: Optional[List[str]] = None) -> dict:
    bots = bots or list(BOT_DIMS.keys())
    firmas = load_firmas_from_db(db_path)
    juez = load_juez_feedback(db_path)
    for bot, xy in juez.items():
        firmas[bot] = _merge_xy(firmas.get(bot), xy)
        logger.info(f"  merge juez→{bot}: n={len(firmas[bot][0])}")
    results = {}
    for bot in bots:
        X, yc, ys, w, source = merge_or_bootstrap(bot, firmas, min_samples)
        if X is None:
            logger.warning(f"=== {bot}: {source} ===")
            results[bot] = {"path": None, "n": 0, "source": source,
                            "reentrenado": False}
            continue
        logger.info(f"=== {bot}: {source} ===")
        path = train_export(bot, X, yc, ys, w)
        results[bot] = {"path": str(path), "n": int(len(X)), "source": source,
                        "reentrenado": True}
    meta = {
        "retrained_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "db_path": str(db_path),
        "bots": results,
    }
    (MODELS_DIR / "models_meta.json").write_text(json.dumps(meta, indent=2))
    return results


def main():
    ap = argparse.ArgumentParser(description="Reentrenar modelos ONNX desde firmas/DB")
    ap.add_argument("--db-path", required=True)
    ap.add_argument("--min-samples", type=int, default=MIN_SAMPLES)
    ap.add_argument("--bots", nargs="*", default=None)
    args = ap.parse_args()
    res = retrain(args.db_path, min_samples=args.min_samples, bots=args.bots)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
