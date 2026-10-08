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

from sentinel_omega.models.rasgos_juez import cargar_reconstruidos

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

# El orden de los rasgos y las dimensiones viven en core/features_onnx.py, que
# es la fuente UNICA: el 2026-09-25 se descubrió que la inferencia construía el
# vector por su cuenta y no coincidía (alfa1 entrenaba con `bz_mean` en la
# posición 0 y se le preguntaba con `bz_gsm`; en la 4, `bz_min` contra
# `dst_index`). Nada reventaba porque onnx_config solo declara CUÁNTOS rasgos.
from sentinel_omega.core.features_onnx import (  # noqa: E402
    BOT_DIMS,
    FEATURE_ORDER,
    vector_para,
)

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
    """Delega en la fuente única para que entrenar y preguntar no se separen."""
    return vector_para(bot, features)


def purgar_no_medidos(features: dict) -> dict:
    """Quita del diccionario los números que NO son mediciones.

    Medido el 2026-09-27: 387 filas vivas de `TBL_JUEZ_AUDITORIA` traen
    `schumann_mean = 8.26` y **ningún** `schumann_std`. Ese 8,26 es
    `7.83 + 21.46 × 0.02`: la fundamental de libro más una actividad CONGELADA
    que precede en siete semanas a cualquier lectura, no un dato de Tomsk. Un
    solo valor en las 387 filas, además, no distingue nada.

    El daño no es el valor: es el **desajuste entre entrenar y preguntar**. El
    ciclo en vivo entrega ausencia —Schumann en NULL mientras Tomsk esté
    caído—, que `vector_para` convierte en 0,0; el entrenamiento entregaba
    8,26. El modelo aprendía con un número y luego se le preguntaba con otro.

    El criterio NO es el nombre del rasgo ni el valor 8,26, porque los dos
    envejecen mal: si Tomsk vuelve, filtrar por nombre seguiría descartando
    lecturas buenas —el mismo defecto al revés— y filtrar por valor se cae en
    cuanto cambie la fórmula del relleno. El criterio es la **forma**: un
    agregado de ventana produce media *y* dispersión, así que una media suelta
    no salió de una ventana de muestras.

    El relleno entra por DOS caminos y este criterio los cubre los dos:

      * `detalles_json` --- 387 filas, lo que el bot vio en su momento
      * `tbl_juez_rasgos_reconstruidos` --- 72 filas. `rasgos_juez._schumann`
        filtra correctamente hoy (`AND COALESCE(en_vivo,1)=1`, y las 21 filas
        de `tbl_schumann_vivo` están todas marcadas `en_vivo=0`), pero esa
        tabla es MATERIALIZADA: se llenó antes de que existiera la bandera. Un
        filtro correcto no limpia lo que ya se guardó sin él. La raíz se cierra
        rematerializándola; esta purga es el cinturón.

    El coste de este criterio: si Tomsk vuelve y una ventana trae UNA sola
    lectura, `_schumann` devuelve su media sin desviación y aquí se descartaría.
    Hoy no cuesta nada --- en toda la base no hay una sola lectura viva de
    Schumann, las 72 reconstruidas son el mismo 8,26 sin `std` --- y cuando
    haya serie real traerá las dos y pasará intacta.
    """
    fuera = dict(features)
    for base in ("schumann",):
        media, desv = f"{base}_mean", f"{base}_std"
        if media in fuera and desv not in fuera:
            fuera.pop(media)
    return fuera


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


def _filtro_juez_en_vivo(conn: sqlite3.Connection) -> str:
    """``" AND COALESCE(en_vivo,1)=1"`` si TBL_JUEZ_AUDITORIA tiene la columna.

    Medido el 2026-09-27: 594 filas con fase='viva' venían de un proceso
    duplicado viejo con la fuga de `kp_mean` y se marcaron `en_vivo=0` (387 ya
    resueltas). Filtrar solo por fase las dejaba entrar al entrenamiento. NULL
    cuenta como vivo, igual que en el resto de lectores; una base sin la
    columna (anterior a la bandera) se lee entera, con un aviso.
    """
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(TBL_JUEZ_AUDITORIA)")}
    except sqlite3.Error:
        return ""
    if "en_vivo" in cols:
        return " AND COALESCE(en_vivo,1)=1"
    logger.warning("TBL_JUEZ_AUDITORIA sin en_vivo: se entrena con todas las filas viva")
    return ""


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
            "SELECT id, bot_name, prediccion, confianza, resultado, detalles_json "
            "FROM TBL_JUEZ_AUDITORIA "
            "WHERE resultado IN ('ACIERTO','FALLO','FALSO_POSITIVO') "
            "AND fase = 'viva'" + _filtro_juez_en_vivo(conn)
        ).fetchall()
    except sqlite3.Error as e:
        logger.info(f"Juez sin filas útiles: {e}")
        conn.close()
        return {}
    conn.close()
    logger.info(f"Juez feedback vivo: {len(rows)} filas")
    # Respaldo para las filas anteriores al 2026-09-25 17:38, que llevan
    # `features_generales` vacío porque el lanzador no se lo pasaba: la
    # telemetría de su ventana, recompuesta y VALIDADA contra las filas que sí
    # los traen (ver models/rasgos_juez.py). Lo que el bot vio manda siempre;
    # esto sólo entra donde no hay nada.
    reconstruidos = cargar_reconstruidos(str(path))
    if reconstruidos:
        logger.info(
            "Rasgos reconstruidos disponibles para %d filas del Juez",
            len(reconstruidos),
        )
    n_reconstruidas = 0
    n_purgadas = 0
    for juez_id, bot_name, prediccion, confianza, resultado, det_json in rows:
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
        if not features:
            respaldo = reconstruidos.get(int(juez_id))
            if respaldo:
                features = dict(respaldo)
                n_reconstruidas += 1
        # Después del respaldo, porque el relleno entra por los DOS caminos.
        # `rasgos_juez._schumann` filtra bien hoy (`AND COALESCE(en_vivo,1)=1`,
        # y las 21 filas de `tbl_schumann_vivo` están marcadas en_vivo=0), pero
        # `tbl_juez_rasgos_reconstruidos` es una tabla MATERIALIZADA: se llenó
        # antes de que existiera la bandera y conserva 72 filas con el 8,26.
        # El filtro correcto no limpia lo que ya se guardó sin él.
        antes = len(features)
        features = purgar_no_medidos(features)
        if len(features) != antes:
            n_purgadas += 1
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
    if n_reconstruidas:
        logger.info(
            "Juez: %d muestras entraron con rasgos RECONSTRUIDOS de la "
            "telemetría de su ventana (las anteriores al 2026-09-25 llevan "
            "features_generales vacío)", n_reconstruidas,
        )
    if n_purgadas:
        logger.info(
            "Juez: %d muestras traían una media sin su desviación --- no es un "
            "agregado de ventana, es relleno. Se purgó para que el "
            "entrenamiento vea la misma ausencia que ve el ciclo en vivo",
            n_purgadas,
        )
    if sin_rasgos:
        logger.warning(
            "Juez: %d muestras DESCARTADAS por no traer rasgos (%s). Son las "
            "que ni el ciclo registró ni la telemetría guardada cubre --- "
            "beta2 (desgasificación, última el 2026-07-31) y delta (finanzas, "
            "2026-01-01) no tienen fuente en la ventana viva.",
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
        gen_alfa1, gen_beta1, gen_beta2, gen_delta, gen_omega,
    )
    # alfa2 SALE del prior sintético el 2026-10-02, con medición.
    #
    # `gen_alfa2` fabrica 2.500 muestras con `RNG.uniform/poisson/normal`, y
    # **cinco de sus ocho columnas llevan otra magnitud** que las del vector
    # vigente: la posición 4 del prior es `revisit` (1-14 días) donde el vector
    # tiene `coverage_score` (0,30-0,93); la 5 es `cloud` (0-1) donde el vector
    # tiene `clear_passes` (~5.437, suma de ventana). Las dimensiones cuadran
    # (8 = 8), así que `test_onnx_dims` no puede verlo.
    #
    # Con 23 muestras reales, el reentreno salía `hybrid real=23+boot=2500`:
    # un 99 % de ruido en las posiciones de los rasgos. Sin prior, el camino es
    # «NO se reentrena» y se conserva el modelo en disco --- que es lo que
    # quiere su propio comentario: «inventar muestras para rellenar sería peor
    # que no reentrenar».
    #
    # Los demás conservan su prior porque hoy no lo usan (alfa1 entrena
    # `db-only (1407)`), pero su alineación NO se ha medido: si a alguno le
    # bajan las muestras reales por debajo del mínimo, hay que comprobar
    # columna por columna antes de dejarlo bootstrapear.
    gens = {
        "alfa1": gen_alfa1, "beta1": gen_beta1,
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


# ─── La compuerta de habilidad (2026-10-07) ───────────────────────────────────
#
# Hasta hoy el ÚNICO control de calidad de este archivo era:
#
#     pred = model.predict(X)        # las MISMAS X del entrenamiento
#     mae  = np.mean(np.abs(pred[:,0] - y_conf))
#
# Error EN MUESTRA. Un bosque que memoriza saca MAE ~0 y se publica igual, y
# `models_meta.json` no guardaba ni un número de calidad --- solo `{path, n,
# source, reentrenado}`. Por eso el 2026-10-05 se publicaron OCHO modelos sin
# habilidad sin que nada chistara, y costó: cinco bots alarmando el 100 % de
# los ciclos, ganancia de Molchan 0,81x (peor que el azar) y 159 falsos
# positivos.
#
# Medido el 2026-10-07 con corte TEMPORAL sobre los rasgos de cada bot, contra
# el objetivo real (hubo evento en el horizonte aprendido): AUC 0,465-0,515 ---
# azar --- en los seis bots con material. Lo único que separaba era
# `sismo_count_win` (0,814), que es agrupamiento de Omori, no un precursor.
#
# Así que la compuerta no es una cortesía: es la diferencia entre un modelo y
# una alarma fija. Y niega el envío en los DOS casos que importan:
#
#   * objetivo degenerado --- una sola clase, o casi: no se PUEDE medir
#     habilidad, y es exactamente el estado de hoy (96-100 % de las muestras
#     etiquetadas como alarma, porque las firmas nacen de eventos);
#   * habilidad medida por debajo del azar útil.
#
# Se puede saltar con `--sin-compuerta`, que lo deja escrito en el log y en el
# metadato. Nunca en silencio.
AUC_MINIMA = 0.55          # por debajo de esto no hay nada que aprovechar

# Y un TECHO, que es la mitad que faltaba (medido el 2026-10-07).
#
# La primera versión de esta compuerta aprobó a los seis bots con AUC
# 0,989-0,999 --- o sea que habría dejado pasar exactamente los modelos que
# costaron 159 falsos positivos. La causa, comprobada:
#
#     AUC de «¿esta fila es una firma o una fila del Juez?» = 1,0000
#
# La clase ALARMA son las firmas (96-100 % de ellas llevan etiqueta de alarma,
# porque nacen de eventos) y la clase CALMA son las 28 filas vivas del Juez
# (3,6 %). Las dos tablas se distinguen PERFECTAMENTE, así que cualquier bosque
# saca 0,99 aprendiendo de qué tabla vino la fila, no física.
#
# Es la fuga de procedencia otra vez, pero a nivel de DISTRIBUCIÓN, no de
# ceros. La del 2026-09-27 era «este rasgo vale 0 en toda la mitad etiquetada
# como alarma» y se cerró declarando los rasgos; `test_fuga_de_procedencia.py`
# la vigila rasgo por rasgo y **no puede ver esta**, porque aquí todos los
# rasgos están declarados y llenos: lo que difiere es de dónde salen.
#
# Predecir un sismo con 0,99 de AUC no es un buen modelo, es una fuga. El techo
# lo dice con ese nombre, porque el número alto es lo que engaña.
AUC_MAXIMA_CREIBLE = 0.95

FRACCION_PRUEBA = 0.30
MIN_PARA_MEDIR = 60        # con menos, el AUC de prueba es ruido


def medir_habilidad(
    bot: str,
    X: np.ndarray,
    y_conf: np.ndarray,
    y_sig: np.ndarray,
    pesos: Optional[np.ndarray] = None,
    ts: Optional[np.ndarray] = None,
) -> dict:
    """AUC sobre un holdout, con corte TEMPORAL si hay marcas de tiempo.

    Devuelve `{'auc', 'n_train', 'n_test', 'base_test', 'corte', 'motivo'}`.
    `auc` es None cuando no se puede medir, y entonces `motivo` dice por qué ---
    que es la mitad útil del resultado.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import roc_auc_score

    # El objetivo binario es «¿esta ventana merecía alarma?». Es lo que el
    # sistema hace con la salida, así que es lo que hay que medir.
    alarma = (np.asarray(y_sig) >= WATCH).astype(int)
    n = len(X)
    clases = set(np.unique(alarma).tolist())
    if len(clases) < 2:
        return {"auc": None, "n_train": 0, "n_test": 0, "base_test": None,
                "corte": None,
                "motivo": (f"objetivo degenerado: las {n} muestras son de una "
                           f"sola clase ({'alarma' if 1 in clases else 'calma'}), "
                           "así que no hay nada que discriminar")}
    if n < MIN_PARA_MEDIR:
        return {"auc": None, "n_train": 0, "n_test": 0, "base_test": None,
                "corte": None,
                "motivo": f"solo {n} muestras; por debajo de {MIN_PARA_MEDIR} el AUC es ruido"}

    if ts is not None and len(ts) == n:
        orden = np.argsort(np.asarray(ts, dtype="U"))
        corte_tipo = "temporal"
    else:
        rng = np.random.RandomState(RANDOM_SEED)
        orden = rng.permutation(n)
        corte_tipo = "aleatorio (sin marcas de tiempo --- puede sobrestimar)"
    k = int(n * (1.0 - FRACCION_PRUEBA))
    tr, te = orden[:k], orden[k:]
    if len(set(alarma[tr].tolist())) < 2 or len(set(alarma[te].tolist())) < 2:
        return {"auc": None, "n_train": len(tr), "n_test": len(te),
                "base_test": float(alarma[te].mean()) if len(te) else None,
                "corte": corte_tipo,
                "motivo": ("el corte deja una sola clase a un lado: con este "
                           "reparto no se puede medir")}

    rf = RandomForestRegressor(
        n_estimators=80, max_depth=10, min_samples_leaf=3,
        random_state=RANDOM_SEED, n_jobs=-1,
    )
    w = None if pesos is None else np.asarray(pesos)[tr]
    rf.fit(X[tr], y_conf[tr], sample_weight=w)
    auc = float(roc_auc_score(alarma[te], rf.predict(X[te])))
    return {"auc": auc, "n_train": int(len(tr)), "n_test": int(len(te)),
            "base_test": float(alarma[te].mean()), "corte": corte_tipo,
            "motivo": None}


def train_export(
    bot: str,
    X: np.ndarray,
    y_conf: np.ndarray,
    y_sig: np.ndarray,
    pesos: Optional[np.ndarray] = None,
    ts: Optional[np.ndarray] = None,
    con_compuerta: bool = True,
) -> Tuple[Optional[Path], dict]:
    """Entrena y escribe el `.onnx` **solo si pasa la compuerta de habilidad**.

    Devuelve `(ruta_o_None, habilidad)`. Cuando la compuerta niega, el modelo
    anterior se queda en disco intacto: preferimos el de ayer, cuya habilidad
    al menos es conocida, a uno nuevo del que no sabemos nada.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.multioutput import MultiOutputRegressor
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    habilidad = medir_habilidad(bot, X, y_conf, y_sig, pesos, ts)
    auc = habilidad["auc"]
    if auc is None:
        logger.warning("  %s: NO se puede medir la habilidad --- %s",
                       bot, habilidad["motivo"])
    else:
        logger.info("  %s: AUC de prueba %.3f (corte %s, n_test=%d, base %.1f %%)",
                    bot, auc, habilidad["corte"], habilidad["n_test"],
                    100 * habilidad["base_test"])
    if auc is not None and auc > AUC_MAXIMA_CREIBLE:
        habilidad["motivo"] = (
            f"AUC {auc:.3f} es DEMASIADO BUENO para este problema: predecir un "
            "sismo así no pasa. Casi seguro las dos clases vienen de fuentes "
            "distintas y el bosque está aprendiendo la procedencia --- el "
            "2026-10-07 la clase alarma eran las firmas y la calma las filas "
            "vivas del Juez, y adivinar la tabla daba AUC 1,0000. Las muestras "
            "positivas y negativas tienen que salir de la MISMA extracción.")
    aprueba = (auc is not None
               and AUC_MINIMA <= auc <= AUC_MAXIMA_CREIBLE)
    habilidad["aprueba"] = bool(aprueba)
    habilidad["auc_minima"] = AUC_MINIMA
    habilidad["auc_maxima_creible"] = AUC_MAXIMA_CREIBLE
    if not aprueba:
        if con_compuerta:
            logger.error(
                "  %s: NO se escribe el modelo. %s. El `.onnx` anterior se "
                "queda: preferimos el de ayer, cuya habilidad al menos es "
                "conocida, a uno nuevo del que no sabemos nada. Para forzarlo, "
                "`--sin-compuerta`.",
                bot,
                habilidad["motivo"] or f"AUC {auc:.3f} < {AUC_MINIMA}")
            habilidad["escrito"] = False
            return None, habilidad
        logger.warning("  %s: la compuerta lo habría negado y se fuerza "
                       "(--sin-compuerta): %s", bot,
                       habilidad["motivo"] or f"AUC {auc:.3f} < {AUC_MINIMA}")
        habilidad["forzado"] = True

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
    # EN MUESTRA, y se dice: durante meses este número fue el único control de
    # calidad y no mide generalización. Lo que decide es `medir_habilidad`.
    logger.info(f"  {bot}: MAE EN MUESTRA conf={mae:.4f} (no mide "
                f"generalización)  n={len(X)}{peso_info}")
    habilidad["mae_en_muestra"] = mae

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
    habilidad["escrito"] = True
    return out, habilidad


def retrain(db_path: str, min_samples: int = MIN_SAMPLES,
            bots: Optional[List[str]] = None,
            con_compuerta: bool = True) -> dict:
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
        path, habilidad = train_export(bot, X, yc, ys, w,
                                       con_compuerta=con_compuerta)
        results[bot] = {
            "path": str(path) if path else None,
            "n": int(len(X)),
            "source": source,
            "reentrenado": path is not None,
            # La habilidad va al metadato SIEMPRE, también cuando la compuerta
            # niega: así «no se escribió» viene con el motivo al lado y no hay
            # que adivinarlo después (regla dura 10).
            "habilidad": habilidad,
        }
    aprobados = [b for b, r in results.items()
                 if (r.get("habilidad") or {}).get("aprueba")]
    negados = [b for b, r in results.items()
               if r.get("n") and not (r.get("habilidad") or {}).get("aprueba")]
    logger.info("Compuerta de habilidad: aprueban %s · niega %s",
                aprobados or "ninguno", negados or "ninguno")
    meta = {
        "retrained_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "db_path": str(db_path),
        "compuerta": {"auc_minima": AUC_MINIMA, "activa": bool(con_compuerta),
                      "aprueban": aprobados, "niega": negados},
        "bots": results,
    }
    (MODELS_DIR / "models_meta.json").write_text(json.dumps(meta, indent=2))
    return results


def main():
    ap = argparse.ArgumentParser(description="Reentrenar modelos ONNX desde firmas/DB")
    ap.add_argument("--db-path", required=True)
    ap.add_argument("--min-samples", type=int, default=MIN_SAMPLES)
    ap.add_argument("--bots", nargs="*", default=None)
    ap.add_argument(
        "--sin-compuerta", action="store_true",
        help=("escribe el .onnx aunque no se pueda medir su habilidad o esté "
              f"por debajo de AUC {AUC_MINIMA}. Queda en el log y en "
              "models_meta.json; no es un atajo, es una decisión que se firma"))
    args = ap.parse_args()
    res = retrain(args.db_path, min_samples=args.min_samples, bots=args.bots,
                  con_compuerta=not args.sin_compuerta)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
