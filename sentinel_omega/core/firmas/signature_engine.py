"""
Signature Engine — extracts, stores, promotes, and matches firmas.

Protocol (from sentinel_omega.docx):
  - A firma captures the pre-event window (default 14 days at 1H resolution)
    of all measured variables, plus a near sub-window (72h) for short-lead
    precursors.
  - New firmas are catalogued WITHOUT punishment. Promotion by recurrence:
      1 sighting  -> nueva
      2 sightings -> observada
      3-4         -> recurrente
      >= 5        -> consolidada  (enforceable knowledge)
  - In operation, bots compare the live state against consolidated firmas;
    a high-similarity match means "this looks like what preceded event X".
  - ZERO synthetic data: features are computed only from non-NULL backcast
    rows; missing variables simply stay absent from the vector.
"""

import json
import logging
import sqlite3
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Fixed feature order — every firma vector uses these keys.
FEATURE_KEYS = [
    "bz_mean", "bz_min", "bz_deriv_std",
    "viento_avg", "viento_max",
    "kp_mean", "kp_max",
    # `proton_max` es el FLUJO >10 MeV, y está muerto en los dos lados: OMNI2
    # publica sus columnas 42-47 todas en centinela y NOAA solo sirve 6 h, así
    # que la tabla lo tiene en 178 de 286.932 horas (0,062 %). Se conserva
    # porque el ciclo vivo SÍ lo mide y la historia se acumula desde el
    # 2026-09-24; no está en el vector de ningún modelo.
    "proton_max",
    # DENSIDAD de protones — otra magnitud, y ésta sí tiene treinta años.
    # OMNI2 col 23: 97,7 % de cobertura, mediana 5,70 n/cc, cero negativos
    # (medido contra omni2_2024.dat el 2026-10-02). En vivo la baja
    # `fetch_solar_wind()` y llega hasta `omni_dataframe`; lo único que faltaba
    # era leerla. Ocupa las dos posiciones que el flujo repetía como relleno en
    # el vector de alfa1, así que entra sin cambiar dimensiones.
    "densidad_prot_mean", "densidad_prot_max",
    "schumann_mean", "schumann_std",
    "sismo_count_win", "sismo_max_mag_win",
    "fase_lunar", "es_sicigia", "lod", "vix",
    "btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h",
    "so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
    # near sub-window (last 72h before the event)
    "bz_mean_72h", "kp_max_72h", "sismo_count_72h",
    # alfa2: cobertura satelital ESA Sentinel (live-only, acumulado desde ciclos)
    "satellite_coverage_score", "satellite_thermal_anomalies", "satellite_clear_passes",
    # La CUARTA señal de alfa2 (2026-10-02, decisión del operador: «vota y
    # avisa»). Con tres rasgos nunca llegaba a `MIN_DIMENSIONES_COMPARABLES`
    # (4), así que no formaba firmas, no recibía peso y el tablero lo rotulaba
    # notificador. Todo colgaba de ese 3 < 4.
    #
    # Se eligió `revisit_days` MIDIENDO, no por conveniencia. Sobre las 3.231
    # filas de `tbl_cobertura_satelital_historico` (70 días reales):
    #
    #   revisit_days      153 valores distintos, 100 % de cobertura
    #                     p10 0,32 · p50 0,51 · p75 0,72 · p90 0,86 · max 1,68 d
    #   coverage_score    136 distintos
    #   total_passes       54 distintos
    #   clear_passes       31 distintos
    #
    # Y no es redundante con el puntaje aunque el puntaje lo use: su término es
    # `max(0, 1 - revisita/12) * 0,3`, con un tope de 12 DÍAS mientras la
    # realidad vive entre 0 y 1,7. Medido: el término solo se mueve de 0,2580 a
    # 0,3000 en todo el rango real --- el puntaje aplana el 98,6 % de esta
    # información. Darla cruda expone varianza que el agregado tira.
    "satellite_revisita_dias",
    # delta_enriched: acoplamiento geofísico-financiero (live-only, desde tbl_delta_cross)
    "delta_cross_coupling", "delta_geo_coupling", "delta_schumann_coupling",
    # jupiter: fulguraciones solares (GOES) + atención colectiva (Google Trends).
    # Antes se bajaban cada ciclo y se descartaban sin tabla ni escritor, así
    # que Júpiter no tenía de dónde formar su vector. Ahora se persisten en
    # tbl_xray_vivo / tbl_trends_vivo y se acumulan desde el ciclo operativo.
    "xray_mean", "xray_max", "trends_mean",
    # beta2: marea terrestre por efemérides (2026-09-27).
    #
    # Entran aquí porque faltar de esta lista las hacía IMPOSIBLES de aprender:
    # el vector ONNX de beta2 las pide desde el 2026-09-26, pero el filtro
    # `{k: v for ... if k in FEATURE_KEYS}` las descartaba en silencio, así que
    # valían 0 en las 806 firmas de beta2 y un valor real en la mitad viva.
    # `P(alarma | marea=0)` medida: 99,8 %. El modelo no aprendía la marea:
    # aprendía de qué tabla venía la fila (`tests/test_fuga_de_procedencia.py`).
    #
    # El lado vivo las calcula en `models/rasgos_juez._marea` con
    # `marea_ventana(momento, horas=24)`; la firma usa la MISMA llamada con el
    # ts de su ventana, así que las dos mitades hablan de lo mismo.
    "marea_total", "marea_luna", "marea_sol", "marea_sicigia",
    "marea_dist_luna", "marea_rango_24h", "marea_max_24h", "marea_deriv",
]

# Dimensiones compartidas mínimas para que dos firmas puedan compararse.
# Por DEBAJO de esto, similitud() devuelve 0.0 --- un vector no se reconoce
# ni a sí mismo. Es el suelo REAL de todo el sistema de firmas: un bot que
# registre con menos features crea firmas singleton que jamás emparejarán,
# acumulando memoria que el Juez no puede usar.
#
# `MIN_FEATURES_POR_BOT` (entrenamiento.py) debe respetarlo. Durante meses no
# lo hizo: permitía registrar con 2 o 3, y Júpiter llegó a 44.830 firmas
# TODAS vistas una sola vez, recurrencia máxima 1.
MIN_DIMENSIONES_COMPARABLES = 4

VENTANA_HORAS = 336  # 14 days
SUBVENTANA_HORAS = 72

SIMILARITY_MATCH = 0.85     # same firma family
SIMILARITY_ALERT = 0.80     # operational "looks like" threshold

# Cuántos avistamientos concretos se guardan por firma. Una firma que se
# repite 24,719 veces son 24,719 eventos CASI IDÉNTICOS (por eso matchean la
# misma firma) — guardarlos todos es puro bulto. Nos quedamos con una MUESTRA
# (los primeros N, que en entrenamiento cronológico son los más viejos → el
# min(ts) real se preserva) y el CONTEO fiel vive en `recurrencia`. Los tres
# lectores solo necesitan: min(ts) [orden=1], primeros 3 [lags], y una muestra
# para re-presentar [backtest] — todos cubiertos con N pequeño.
CAP_EVENTOS_MUESTRA = 10

ESTADO_POR_RECURRENCIA = [
    (5, "consolidada"),
    (3, "recurrente"),
    (2, "observada"),
    (1, "nueva"),
]


def _estado(recurrencia: int) -> str:
    for minimo, estado in ESTADO_POR_RECURRENCIA:
        if recurrencia >= minimo:
            return estado
    return "nueva"


def _stats(values: List[float]) -> Optional[Tuple[float, float, float, float]]:
    arr = np.array([v for v in values if v is not None], dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return None
    return float(arr.mean()), float(arr.min()), float(arr.max()), float(arr.std())


def _tiene_columna(conn, tabla: str, columna: str) -> bool:
    """¿Existe la columna? Los esquemas antiguos pueden no tenerla."""
    try:
        return any(r[1] == columna for r in conn.execute(f"PRAGMA table_info({tabla})"))
    except sqlite3.Error:
        return False


def extraer_features_ventana(
    conn: sqlite3.Connection,
    ts_evento: str,
    id_nodo: int,
) -> Optional[Dict[str, float]]:
    """Build the feature vector for the pre-event window ending at ts_evento.

    Reads the backcast tables (1H blocks). Returns None when the window has
    no space-weather coverage at all (nothing real to learn from).
    """
    # `densidad_protones` se añadió el 2026-10-02 y puede faltar en un esquema
    # viejo: se pide solo si existe, igual que el resto de las lecturas
    # defensivas de este módulo.
    hay_densidad = _tiene_columna(conn, "tbl_clima_espacial_raw",
                                  "densidad_protones")
    q_win = (
        "SELECT bz_promedio, bz_min, bz_derivada, viento_solar_avg, "
        "viento_solar_max, kp_promedio, kp_max, proton_flux_10mev"
        + (", densidad_protones " if hay_densidad else " ")
        + "FROM tbl_clima_espacial_raw "
        "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?) "
        "ORDER BY timestamp_blk"
    )
    rows = conn.execute(
        q_win, (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours")
    ).fetchall()
    if not rows:
        return None

    cols = list(zip(*rows))
    features: Dict[str, float] = {}

    bz = _stats(list(cols[0]))
    if bz:
        features["bz_mean"], features["bz_min"] = bz[0], bz[1]
    bz_deriv = _stats(list(cols[2]))
    if bz_deriv:
        features["bz_deriv_std"] = bz_deriv[3]
    viento = _stats(list(cols[3]))
    if viento:
        features["viento_avg"] = viento[0]
    viento_max = _stats(list(cols[4]))
    if viento_max:
        features["viento_max"] = viento_max[2]
    kp = _stats(list(cols[5]))
    if kp:
        features["kp_mean"] = kp[0]
    kp_max = _stats(list(cols[6]))
    if kp_max:
        features["kp_max"] = kp_max[2]
    protones = _stats(list(cols[7]))
    if protones:
        features["proton_max"] = protones[2]
    if hay_densidad and len(cols) > 8:
        # Media Y máximo: el nivel de densidad y su pico dicen cosas distintas
        # --- una corriente rápida comprime el plasma antes de llegar ---, y son
        # las dos posiciones que el flujo repetido ocupaba sin dato.
        densidad = _stats(list(cols[8]))
        if densidad:
            features["densidad_prot_mean"] = densidad[0]
            features["densidad_prot_max"] = densidad[2]

    if not features:
        return None

    # Schumann per-window (node 0 = observation node feed)
    sch_rows = conn.execute(
        "SELECT schumann_hz FROM tbl_enjambre_telemetria "
        "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?)"
        # en_vivo=0 = valor congelado/arrastrado (Tomsk caído): no es medición.
        + (" AND COALESCE(en_vivo,1)=1"
           if _tiene_columna(conn, "tbl_enjambre_telemetria", "en_vivo") else ""),
        (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
    ).fetchall()
    sch = _stats([r[0] for r in sch_rows])
    if sch:
        features["schumann_mean"], features["schumann_std"] = sch[0], sch[3]

    # Seismic context at the same node: foreshocks / quiescence / swarm
    sis = conn.execute(
        "SELECT COALESCE(SUM(sismo_count),0), COALESCE(MAX(sismo_max_mag),0) "
        "FROM tbl_historico_sismico_raw "
        "WHERE id_nodo = ? AND timestamp_blk < ? "
        "AND timestamp_blk >= datetime(?, ?)",
        (id_nodo, ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
    ).fetchone()
    features["sismo_count_win"] = float(sis[0])
    features["sismo_max_mag_win"] = float(sis[1])

    # Lunar state at event time (tidal trigger context)
    luna = conn.execute(
        "SELECT fase_lunar_pct, es_sicigia, lod_ms FROM tbl_astronomia_cinematica "
        "WHERE timestamp_blk <= ? ORDER BY timestamp_blk DESC LIMIT 1",
        (ts_evento,),
    ).fetchone() if _tiene_columna(conn, "tbl_astronomia_cinematica", "lod_ms") else conn.execute(
        "SELECT fase_lunar_pct, es_sicigia, NULL FROM tbl_astronomia_cinematica "
        "WHERE timestamp_blk <= ? ORDER BY timestamp_blk DESC LIMIT 1",
        (ts_evento,),
    ).fetchone()
    if luna and luna[0] is not None:
        features["fase_lunar"] = float(luna[0])
        features["es_sicigia"] = float(luna[1] or 0)
    # LOD (exceso de duración del día, IERS) — feature de Loki. Rellenado
    # desde finals2000A.all; antes la columna era 0.0 en las 280.352 filas.
    if luna and luna[2] is not None:
        features["lod"] = float(luna[2])

    # Financial psyche (2014+) — Delta's domain: volatility pattern + net move
    btc = conn.execute(
        "SELECT volatilidad_24h, btc_precio_usd FROM tbl_psique_financiera "
        "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?) "
        "AND volatilidad_24h IS NOT NULL "
        "ORDER BY timestamp_blk",
        (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
    ).fetchall()
    btc_stats = _stats([r[0] for r in btc])
    if btc_stats:
        features["btc_volatilidad"] = btc_stats[0]
        features["btc_vol_max"] = btc_stats[2]
        precios = [r[1] for r in btc if r[1] is not None]
        if len(precios) >= 2 and precios[0]:
            features["btc_ret_win"] = (precios[-1] - precios[0]) / precios[0] * 100
        btc72 = conn.execute(
            "SELECT AVG(volatilidad_24h) FROM tbl_psique_financiera "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?) "
            "AND volatilidad_24h IS NOT NULL",
            (ts_evento, ts_evento, f"-{SUBVENTANA_HORAS} hours"),
        ).fetchone()
        if btc72 and btc72[0] is not None:
            features["btc_vol_72h"] = float(btc72[0])

    # VIX medio de la ventana — feature de Loki. La columna estaba 100% NULL
    # hasta el backfill desde ^VIX (Yahoo, 1993+). Los días sin cotización
    # (fin de semana) no cuentan: se promedia solo lo medido.
    try:
        vix_win = conn.execute(
            "SELECT AVG(vix) FROM tbl_psique_financiera "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?) "
            "AND vix IS NOT NULL",
            (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
        ).fetchone()
        if vix_win and vix_win[0] is not None:
            features["vix"] = float(vix_win[0])
    except sqlite3.OperationalError:
        pass    # esquema sin la columna: la feature simplemente no se añade

    # Volcanic degassing (Beta-2's domain) — global planetary SO2 state.
    # 14-day window + 90-day charge context. Zero eruptions in the window is
    # a real signal ONLY when the catalog is actually loaded — an empty table
    # would otherwise mint garbage all-zero signatures.
    try:
        catalogo = conn.execute(
            "SELECT COUNT(*) FROM tbl_desgasificacion_raw"
        ).fetchone()
        if not catalogo or catalogo[0] == 0:
            raise sqlite3.OperationalError("catalog empty")
        des = conn.execute(
            "SELECT COALESCE(SUM(so2_kt),0), COUNT(*) "
            "FROM tbl_desgasificacion_raw "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?)",
            (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
        ).fetchone()
        des90 = conn.execute(
            "SELECT COALESCE(SUM(so2_kt),0), COUNT(*) "
            "FROM tbl_desgasificacion_raw "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, '-90 days')",
            (ts_evento, ts_evento),
        ).fetchone()
        features["so2_kt_win"] = float(des[0])
        features["erupciones_win"] = float(des[1])
        features["so2_kt_90d"] = float(des90[0])
        features["erupciones_90d"] = float(des90[1])
    except sqlite3.OperationalError:
        pass  # table not present in this database

    # Near sub-window (last 72h)
    near = conn.execute(
        "SELECT AVG(bz_promedio), MAX(kp_max) FROM tbl_clima_espacial_raw "
        "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?)",
        (ts_evento, ts_evento, f"-{SUBVENTANA_HORAS} hours"),
    ).fetchone()
    if near and near[0] is not None:
        features["bz_mean_72h"] = float(near[0])
    if near and near[1] is not None:
        features["kp_max_72h"] = float(near[1])
    sis72 = conn.execute(
        "SELECT COALESCE(SUM(sismo_count),0) FROM tbl_historico_sismico_raw "
        "WHERE id_nodo = ? AND timestamp_blk < ? "
        "AND timestamp_blk >= datetime(?, ?)",
        (id_nodo, ts_evento, ts_evento, f"-{SUBVENTANA_HORAS} hours"),
    ).fetchone()
    features["sismo_count_72h"] = float(sis72[0])

    # Cobertura satelital alfa2. Se mira la tabla viva Y la histórica: el
    # volcado de 24h mueve las filas de una a otra, así que consultar solo la
    # viva dejaba a alfa2 sin features para cualquier evento pasado — por eso
    # estaba en BOTS_LIVE_ONLY y nunca acumulaba memoria.
    try:
        sat = conn.execute(
            "SELECT coverage_score, thermal_anomalies, clear_passes, revisit_days "
            "FROM tbl_cobertura_satelital "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?) "
            "UNION ALL "
            "SELECT coverage_score, thermal_anomalies, clear_passes, revisit_days "
            "FROM tbl_cobertura_satelital_historico "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?)",
            (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours",
             ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
        ).fetchall()
        if sat:
            cov_scores = [r[0] for r in sat if r[0] is not None]
            thermal = [r[1] for r in sat if r[1] is not None]
            clear_p = [r[2] for r in sat if r[2] is not None]
            if cov_scores:
                features["satellite_coverage_score"] = float(
                    np.mean(cov_scores)
                )
            if thermal:
                features["satellite_thermal_anomalies"] = float(sum(thermal))
            if clear_p:
                features["satellite_clear_passes"] = float(sum(clear_p))
            # La cuarta: MEDIA de la revisita en la ventana. Media y no suma,
            # porque es un periodo (días entre pasadas), no un conteo --- su
            # suma no significa nada.
            revisitas = [r[3] for r in sat if r[3] is not None]
            if revisitas:
                features["satellite_revisita_dias"] = float(np.mean(revisitas))
    except Exception:
        pass  # tabla no existe aún → features de alfa2 ausentes (NaN en vector)

    # ── jupiter: rayos X GOES + atención colectiva ───────────────────────────
    try:
        xr = conn.execute(
            "SELECT flux_max, flux_avg FROM tbl_xray_vivo "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?)",
            (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
        ).fetchall()
        picos = [r[0] for r in xr if r[0] is not None]
        medias = [r[1] for r in xr if r[1] is not None]
        if medias:
            features["xray_mean"] = float(np.mean(medias))
        if picos:
            features["xray_max"] = float(max(picos))
    except Exception:
        pass  # sin tabla aún → jupiter arranca con el vector incompleto

    try:
        tr = conn.execute(
            "SELECT solar_interest FROM tbl_trends_vivo "
            "WHERE fecha < date(?) AND fecha >= date(?, ?)",
            (ts_evento, ts_evento, f"-{VENTANA_HORAS // 24} days"),
        ).fetchall()
        vals = [r[0] for r in tr if r[0] is not None]
        if vals:
            features["trends_mean"] = float(np.mean(vals))
    except Exception:
        pass

    # Delta cross-correlation coupling (tbl_delta_cross).
    # Populated in live operation by the delta_enriched pipeline.
    # During backcast training these values are absent (NaN in vector) —
    # the system learns them incrementally from live cycles.
    try:
        dc = conn.execute(
            "SELECT AVG(cross_coupling), AVG(geomagnetic_coupling), "
            "AVG(schumann_coupling) "
            "FROM tbl_delta_cross "
            "WHERE timestamp_blk < ? AND timestamp_blk >= datetime(?, ?)",
            (ts_evento, ts_evento, f"-{VENTANA_HORAS} hours"),
        ).fetchone()
        if dc and dc[0] is not None:
            features["delta_cross_coupling"] = float(dc[0])
        if dc and dc[1] is not None:
            features["delta_geo_coupling"] = float(dc[1])
        if dc and dc[2] is not None:
            features["delta_schumann_coupling"] = float(dc[2])
    except Exception:
        pass  # tabla no existe aún → features delta_cross ausentes (NaN en vector)

    # ── beta2: marea terrestre en la ventana de la firma ─────────────────────
    # No se consulta ninguna tabla: se CALCULA por efemérides, así que cubre el
    # 100 % de las ventanas, incluidas las de 1994. Es la razón por la que este
    # rasgo puede cerrar la fuga sin depender de recuperar ninguna fuente.
    features.update(_marea_de_ventana(str(ts_evento)))

    return features


@lru_cache(maxsize=8192)
def _marea_de_ventana(ts_evento: str) -> Tuple[Tuple[str, float], ...]:
    """La marea al cierre de la ventana, memorizada por instante.

    Depende SOLO del instante --- no del nodo --- y un mismo evento se extrae
    una vez por cada nodo de su ventana, así que la caché evita repetir las 25
    efemérides. Medido: 0,651 ms por ventana sin caché.

    Devuelve una tupla (inmutable, para poder memorizarla); vacía si `ephem` no
    está o el instante no es interpretable. Ausente, nunca cero: un 0,0 en
    `marea_total` sería «la Luna no tira», que no existe.
    """
    try:
        from sentinel_omega.core.mareas import marea_ventana
        vals = marea_ventana(ts_evento, horas=24)
    except Exception as e:  # noqa: BLE001 — la firma se forma sin marea
        logger.warning("marea no disponible para %s: %s", ts_evento, e)
        return ()
    return tuple(
        (k, float(v)) for k, v in sorted(vals.items())
        if v is not None and np.isfinite(float(v))
    )


def _vector(features: Dict[str, float]) -> np.ndarray:
    """Fixed-order vector; missing keys become NaN (excluded from similarity)."""
    return np.array(
        [features.get(k, np.nan) for k in FEATURE_KEYS], dtype=float
    )


def similitud_vec(va: np.ndarray, vb: np.ndarray) -> float:
    """Igual que `similitud`, pero con los vectores YA construidos.

    Existe por una medición del 2026-09-26: `similitud` rehacía el vector de
    los DOS lados en cada llamada, y `registrar` compara un evento contra todas
    las firmas de su clase. Resultado: 806.546 llamadas a `_vector` en 60
    eventos --- 8 de los 22 segundos --- reconstruyendo una y otra vez los
    mismos vectores. Construirlos una vez y compararlos es el mismo cálculo sin
    el desperdicio.
    """
    mask = ~(np.isnan(va) | np.isnan(vb))
    if mask.sum() < MIN_DIMENSIONES_COMPARABLES:
        return 0.0
    va, vb = va[mask], vb[mask]
    scale = np.maximum(np.abs(va) + np.abs(vb), 1e-9) / 2.0
    diff = np.abs(va - vb) / scale
    return float(max(0.0, 1.0 - np.mean(np.minimum(diff, 2.0)) / 2.0))


def similitudes_contra(va: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    """Las similitudes de UN vector contra MUCHOS, de una sola vez.

    Exactamente el mismo cálculo que `similitud_vec`, fila a fila, pero en una
    operación de matriz. Medido el 2026-09-26: comparar de una en una gastaba
    549.549 llamadas de Python en 80 eventos --- 8 de los 12 segundos ---
    porque cada evento se compara contra todas las firmas de su clase.

    `matriz` es (n_firmas × n_rasgos). Devuelve un vector de n_firmas.
    """
    if matriz.size == 0:
        return np.zeros(0, dtype=float)
    mask = ~(np.isnan(va)[None, :] | np.isnan(matriz))
    cuenta = mask.sum(axis=1)
    with np.errstate(invalid="ignore"):
        escala = np.maximum(np.abs(va)[None, :] + np.abs(matriz), 1e-9) / 2.0
        diff = np.abs(va[None, :] - matriz) / escala
    # Solo las dimensiones comparables entran en la media.
    aporte = np.where(mask, np.minimum(diff, 2.0), 0.0).sum(axis=1)
    sim = np.zeros(matriz.shape[0], dtype=float)
    ok = cuenta >= MIN_DIMENSIONES_COMPARABLES
    sim[ok] = np.maximum(0.0, 1.0 - (aporte[ok] / cuenta[ok]) / 2.0)
    return sim


def similitud(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Similarity in [0,1] over the features BOTH vectors actually have.

    Normalized inverse mean absolute z-difference. Missing (NaN) dimensions
    are excluded — never imputed (zero-synthetic rule).
    """
    va, vb = _vector(a), _vector(b)
    mask = ~(np.isnan(va) | np.isnan(vb))
    if mask.sum() < MIN_DIMENSIONES_COMPARABLES:
        return 0.0
    va, vb = va[mask], vb[mask]
    scale = np.maximum(np.abs(va) + np.abs(vb), 1e-9) / 2.0
    diff = np.abs(va - vb) / scale
    return float(max(0.0, 1.0 - np.mean(np.minimum(diff, 2.0)) / 2.0))


class _ClaseEnMemoria:
    """Las firmas de un (bot, clase) como matriz viva, no rearmada cada vez.

    Guarda las mismas cuatro columnas que leía el SELECT de `registrar` ---
    `firma_id`, `features_json`, `recurrencia`, `eventos_json` --- y su vector,
    en un buffer que se dobla al llenarse en vez de crecer fila a fila. `matriz()`
    devuelve una VISTA de las filas en uso: no copia.

    El orden es el de `ORDER BY firma_id`, y las firmas nuevas llegan siempre al
    final porque el id es AUTOINCREMENT. Así `argmax` rompe los empates igual
    que antes.
    """

    __slots__ = ("ids", "jsons", "recurrencias", "eventos", "_buf", "n", "_dim")

    def __init__(self) -> None:
        self.ids: List[int] = []
        self.jsons: List[str] = []
        self.recurrencias: List[int] = []
        self.eventos: List[Optional[str]] = []
        self._buf: Optional[np.ndarray] = None
        self.n = 0
        self._dim = 0

    def agregar(
        self,
        firma_id: int,
        features_json: str,
        recurrencia: int,
        eventos_json: Optional[str],
        vector: Optional[np.ndarray],
    ) -> None:
        if vector is None:
            raise ValueError("una firma sin vector no puede entrar en la matriz")
        if self._buf is None:
            self._dim = int(vector.shape[0])
            self._buf = np.empty((max(8, 16), self._dim), dtype=vector.dtype)
        if self.n == self._buf.shape[0]:
            mayor = np.empty((self._buf.shape[0] * 2, self._dim),
                             dtype=self._buf.dtype)
            mayor[: self.n] = self._buf[: self.n]
            self._buf = mayor
        self._buf[self.n] = vector
        self.ids.append(firma_id)
        self.jsons.append(features_json)
        self.recurrencias.append(recurrencia)
        self.eventos.append(eventos_json)
        self.n += 1

    def actualizar(
        self,
        i: int,
        features_json: str,
        recurrencia: int,
        vector: np.ndarray,
    ) -> None:
        self.jsons[i] = features_json
        self.recurrencias[i] = recurrencia
        self._buf[i] = vector

    def fila(self, i: int) -> Tuple[int, str, int, Optional[str]]:
        """La tupla que `registrar` esperaba del SELECT, en el mismo orden."""
        return (self.ids[i], self.jsons[i], self.recurrencias[i], self.eventos[i])

    def matriz(self) -> np.ndarray:
        if self._buf is None or self.n == 0:
            return np.zeros((0, 0), dtype=float)
        return self._buf[: self.n]


class FirmaMemoria:
    """CRUD + promotion over TBL_FIRMAS. One instance per database."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        # Vector de cada firma, cacheado por (firma_id, su json). El json
        # forma parte de la clave a propósito: cuando una firma se actualiza
        # (media corrida), su json cambia y la entrada vieja deja de usarse
        # sola. Sin esto se reconstruía el mismo vector en cada comparación.
        self._cache_vectores: Dict[Tuple[int, str], np.ndarray] = {}
        # La MATRIZ de comparación de cada (bot, clase), viva entre eventos.
        #
        # Medido el 2026-09-26, después del rebuild: el padre se lleva el 60-66 %
        # de la Fase 1, y no porque calcule más, sino porque tiene 14.286 firmas
        # contra las 1.632 de alfa1 --- y `registrar` leía LAS 14.286 FILAS de
        # SQLite con su `features_json` completo y rearmaba la matriz con
        # `vstack` **en cada evento**. Son 186.820 eventos: 2.700 millones de
        # lecturas de fila y 186.820 matrices reconstruidas para comparar contra
        # algo que entre un evento y el siguiente cambia en UNA fila.
        #
        # Aquí se mantiene viva y se actualiza esa fila. El cálculo es el mismo;
        # lo que desaparece es el desperdicio. Es seguro porque dentro del bucle
        # de entrenamiento `registrar` es el ÚNICO que escribe las columnas que
        # entran en la comparación: los otros escritores de TBL_FIRMAS tocan
        # `lag_promedio_h`/`lag_n`, que no van en el vector, o corren fuera.
        self._clases: Dict[Tuple[str, str], _ClaseEnMemoria] = {}

    def olvidar_matrices(self) -> None:
        """Tirar las matrices cacheadas. Necesario si alguien de fuera escribe
        en TBL_FIRMAS mientras esta instancia sigue viva."""
        self._clases.clear()

    def _clase(self, bot_name: str, event_class: str) -> "_ClaseEnMemoria":
        clave = (bot_name, event_class)
        c = self._clases.get(clave)
        if c is None:
            filas = self._conn.execute(
                "SELECT firma_id, features_json, recurrencia, eventos_json "
                "FROM TBL_FIRMAS WHERE bot_name = ? AND event_class = ? "
                # El orden es explícito para que `argmax` rompa los empates
                # igual siempre. `firma_id` es INTEGER PRIMARY KEY, así que es
                # el mismo orden que devolvía el barrido sin ORDER BY.
                "ORDER BY firma_id",
                (bot_name, event_class),
            ).fetchall()
            c = _ClaseEnMemoria()
            for f in filas:
                c.agregar(f[0], f[1], f[2], f[3],
                          self._vector_de_firma(f[0], f[1]))
            self._clases[clave] = c
        return c

    def _vector_de_firma(self, firma_id: int, features_json: str) -> np.ndarray:
        clave = (firma_id, features_json)
        v = self._cache_vectores.get(clave)
        if v is None:
            v = _vector(json.loads(features_json))
            if len(self._cache_vectores) > 50000:
                self._cache_vectores.clear()   # techo: no crecer sin límite
            self._cache_vectores[clave] = v
        return v

    def registrar(
        self,
        bot_name: str,
        event_class: str,
        id_nodo: Optional[int],
        features: Dict[str, float],
        evento_ref: str,
        ts_evento: str,
    ) -> Tuple[int, str, bool]:
        """Register a signature sighting.

        If it matches an existing firma of the same class (>= SIMILARITY_MATCH)
        the firma's recurrence rises, its features update as a running mean,
        and its state may promote. Otherwise a new firma is created.

        Returns (firma_id, estado, es_nueva).
        """
        clase = self._clase(bot_name, event_class)

        # El vector del evento UNA vez, y todas las firmas de la clase en una
        # sola operación de matriz --- que ya está armada y viva.
        v_evento = _vector(features)
        best_id, best_sim, best_row = None, 0.0, None
        best_i = -1
        if clase.n:
            sims = similitudes_contra(v_evento, clase.matriz())
            i = int(np.argmax(sims))
            if sims[i] > 0.0:
                best_i = i
                best_id, best_sim = clase.ids[i], float(sims[i])
                best_row = clase.fila(i)

        if best_id is not None and best_sim >= SIMILARITY_MATCH:
            old_features = json.loads(best_row[1])
            recurrencia = best_row[2] + 1
            # Running mean over shared keys; keep keys only one side has.
            merged = dict(old_features)
            for k, v in features.items():
                if k in merged:
                    merged[k] = merged[k] + (v - merged[k]) / recurrencia
                else:
                    merged[k] = v
            estado = _estado(recurrencia)
            nuevo_json = json.dumps(merged)
            self._conn.execute(
                "UPDATE TBL_FIRMAS SET features_json = ?, recurrencia = ?, "
                "estado = ?, ultima_vista = ? WHERE firma_id = ?",
                (nuevo_json, recurrencia, estado, ts_evento, best_id),
            )
            # La media corrida cambió el vector de ESA firma: se actualiza su
            # fila, no la matriz entera.
            clase.actualizar(best_i, nuevo_json, recurrencia,
                             self._vector_de_firma(best_id, nuevo_json))
            # 1NF + muestreo: el evento es una FILA (append O(1)), y solo
            # guardamos los primeros CAP_EVENTOS_MUESTRA — el conteo fiel es
            # `recurrencia`. No escribimos la serie entera (era O(n²) y bulto).
            if recurrencia <= CAP_EVENTOS_MUESTRA:
                self._conn.execute(
                    "INSERT OR IGNORE INTO tbl_firma_eventos "
                    "(firma_id, evento_ref, ts_evento, orden) VALUES (?, ?, ?, ?)",
                    (best_id, evento_ref, ts_evento, recurrencia),
                )
            self._conn.commit()
            return best_id, estado, False

        cur = self._conn.execute(
            "INSERT INTO TBL_FIRMAS "
            "(bot_name, event_class, id_nodo, features_json, ventana_horas, "
            " recurrencia, estado, primera_vista, ultima_vista) "
            "VALUES (?, ?, ?, ?, ?, 1, 'nueva', ?, ?)",
            (bot_name, event_class, id_nodo, json.dumps(features),
             VENTANA_HORAS, ts_evento, ts_evento),
        )
        firma_id = cur.lastrowid
        self._conn.execute(
            "INSERT OR IGNORE INTO tbl_firma_eventos "
            "(firma_id, evento_ref, ts_evento, orden) VALUES (?, ?, ?, 1)",
            (firma_id, evento_ref, ts_evento),
        )
        self._conn.commit()
        # Se añade al final, que es donde la devolvería `ORDER BY firma_id`:
        # el id es AUTOINCREMENT, así que la nueva siempre es la mayor.
        nuevo_json = json.dumps(features)
        clase.agregar(firma_id, nuevo_json, 1, None,
                      self._vector_de_firma(firma_id, nuevo_json))
        return firma_id, "nueva", True

    def consolidadas(self, bot_name: Optional[str] = None) -> List[Dict[str, Any]]:
        q = ("SELECT firma_id, bot_name, event_class, id_nodo, features_json, "
             "recurrencia, estado FROM TBL_FIRMAS WHERE estado = 'consolidada'")
        params: tuple = ()
        if bot_name:
            q += " AND bot_name = ?"
            params = (bot_name,)
        return [
            {
                "firma_id": r[0], "bot_name": r[1], "event_class": r[2],
                "id_nodo": r[3], "features": json.loads(r[4]),
                "recurrencia": r[5], "estado": r[6],
            }
            for r in self._conn.execute(q, params).fetchall()
        ]

    def match_estado_actual(
        self,
        features: Dict[str, float],
        umbral: float = SIMILARITY_ALERT,
        bot: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Compare the live state against consolidated firmas.

        Returns matches sorted by similarity — "the current state looks
        similar (0.87) to the signature that preceded SISMO_M7 at node 45".

        `bot` limita la comparación a las firmas DE ESE BOT. Añadido el
        2026-09-27: cada bot ya tiene sus propias firmas en `TBL_FIRMAS`
        --- alfa1 1.632, beta1 993, loki 858, padre 14.289 (el conjunto, con
        `BOT_FEATURES["padre"] = None`) --- y su propio modelo ONNX, pero esta
        comparación recorría las 12.872 consolidadas de los nueve contra un
        único diccionario global. Sin el filtro, un bot no puede preguntarle
        nada a su propia memoria.

        `bot_name` viaja en el resultado, que es lo que faltaba para que un
        emparejamiento sea ATRIBUIBLE. Sin él:

          * el `firma_matches` que guarda el Juez no dice de quién era la
            firma, así que el doble de `SEVERIDAD_FALLO_FIRMA_CONOCIDA` solo
            puede aplicarse al padre --- en el entrenamiento sí llega a cada
            bot, vía `firma_conocida=es_exigible`;
          * y un fallo no se puede asignar a su responsable.

        Medido ese día sobre los 35 FALLO que registran emparejamientos: los
        35 tenían firmas, el primero con **similitud 1,0** en una consolidada
        de recurrencia 71 y clase SISMO_M5. El estado se reconoció perfecto y
        el veredicto fue `neutral`.

        El defecto vecino NO se toca aquí, y conviene saberlo: esta función se
        llama desde `_auditar_ciclo`, o sea DESPUÉS de que el consenso decidió.
        Con `bot` y `bot_name` ya se puede medir cuántos ciclos traen
        emparejamiento propio por bot; dejar que influya en la decisión es otro
        cambio, y ese sí mueve veredictos.
        """
        matches = []
        for firma in self.consolidadas(bot_name=bot):
            sim = similitud(features, firma["features"])
            if sim >= umbral:
                matches.append({
                    "firma_id": firma["firma_id"],
                    "bot_name": firma["bot_name"],
                    "event_class": firma["event_class"],
                    "id_nodo": firma["id_nodo"],
                    "similitud": round(sim, 3),
                    "recurrencia": firma["recurrencia"],
                })
        return sorted(matches, key=lambda m: -m["similitud"])

    def stats(self) -> Dict[str, int]:
        rows = self._conn.execute(
            "SELECT estado, COUNT(*) FROM TBL_FIRMAS GROUP BY estado"
        ).fetchall()
        out = {estado: n for estado, n in rows}
        out["total"] = sum(out.values())
        return out
