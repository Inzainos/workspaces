"""
Entrenamiento de firmas — two-phase training over the 30-year backcast.

Fase 1 (reconocimiento, sin castigo):
  For every significant event in the historical catalog, extract the
  pre-event window (14 days, 1H blocks) and register it as a firma for
  each bot over its own feature domain. Recurrence promotes signatures:
  nueva -> observada -> recurrente -> consolidada.

Fase 2 (backtest disciplinario):
  Re-present the member events of consolidated signatures. If the firma
  no longer recognizes the window that formed it (similarity below the
  alert threshold), the Juez records a FALLO — the bot forgot enforceable
  knowledge. New signatures are never punished.

Run via: python sentinel_omega/launcher.py --entrenar
"""

import json
import logging
import math
import sqlite3
import time as _time
from datetime import datetime
from typing import Dict, List, Optional

from sentinel_omega.core.firmas.signature_engine import (
    FEATURE_KEYS,
    MIN_DIMENSIONES_COMPARABLES,
    SIMILARITY_ALERT,
    FirmaMemoria,
    extraer_features_ventana,
    similitud,
)
from sentinel_omega.core.juez.juez import Juez

# Espera por el candado de SQLite en los trabajos por LOTES.
#
# El defecto de SQLite son 5 s, y no alcanzan: un lote comparte la base con el
# launcher vivo, que cicla cada ~5 min y escribe bastante en cada ciclo.
# `sentinel-omega-mantenimiento.service` falló el 2026-09-27 a las 00:00:36 con
# el launcher corriendo, y las MISMAS funciones corren sin un error contra una
# copia sin contención --- así que el código está bien y el fallo fue del
# entorno. Que fuera el candado es lo más probable pero **no está probado**: el
# journal de systemd no es legible por el usuario del repo.
#
# Se arregla de todas formas porque es un defecto por sí solo: 5 s de
# presupuesto para un lote nocturno que compite con un escritor vivo es
# insuficiente en cualquier caso. Un lote puede esperar; fallar no le sirve a
# nadie.
ESPERA_CANDADO_S = 120

# Las conexiones de lote salen de aqui: ademas del `busy_timeout`, ponen
# `synchronous=NORMAL`. El commit con fsync era el 73 % de la Fase 2 (medido
# el 2026-10-02: 13.571 commits = 207,6 s de 286,1 s). Ver el docstring de
# `conexion_de_lote` para la medicion completa y lo que se canjea.
from sentinel_omega.infrastructure.database.schema import conexion_de_lote

logger = logging.getLogger(__name__)

# Cortes del Capitan, 2026-10-04.
# 2.5 es el gatillo: el temblor chico arma la firma. Se lee de la tabla
# que ya esta. Este diff no baja de USGS el tramo 2.5 a 4.49.
# 4.5 es la prediccion que el sistema sostiene. Por debajo se observa
# y no se cobra.
# 6 es el muro. Ahi se dispara la alerta. Un 4.5 no la dispara.
MIN_MAGNITUD_FIRMA = 4.5       # prediccion y castigo
MIN_MAGNITUD_OBSERVAR = 2.5    # gatillo; lee lo ya guardado
MIN_MAGNITUD_ALERTA = 6.0      # muro y alerta


def dispara_alerta(event_class: Optional[str]) -> bool:
    """La alerta sismica sale desde M6. Una clase que no es sismo no se calla."""
    if not event_class or not str(event_class).startswith("SISMO_"):
        return True
    return event_class in ("SISMO_M6", "SISMO_M7")



# Feature domain per bot — each bot only remembers what it measures.
# Padre keeps the full cross-domain vector (patterns within patterns).
# 2026-09-27 — LA FUGA DE ETIQUETA POR PROCEDENCIA, cerrada aquí.
#
# Un rasgo que está en `features_onnx.FEATURE_ORDER[bot]` y NO en esta lista es
# una fuga, no un descuido menor: `signature_engine` solo guarda en la firma las
# claves que esta lista declara, así que el rasgo vale **0 en toda la mitad
# etiquetada como alarma** (las firmas nacen de eventos) y un valor real en la
# mitad neutral (los ciclos vivos del Juez). El modelo no aprende el rasgo:
# aprende de qué TABLA vino la fila. Medido ese día:
#
#     bot     firmas   filas rasgo=0   P(alarma|0)   P(alarma|>0)
#     alfa1    1.632       1.632          98,8 %        1,4 %
#     loki       858         858         100,0 %        1,4 %
#     omega      307         307          96,7 %        1,2 %
#     beta2      806         806          99,8 %        1,5 %
#
# Los conteos coinciden EXACTO con el número de firmas de cada bot. En
# producción: con el Kp decayendo solo (kp_max 3 → 1), alfa1, loki y omega
# pasaron a WATCH en 10 de cada 10 ciclos, y el Juez se lo cobró como falso
# positivo --- peso hundido por un defecto de datos.
#
# Los 17 rasgos entran con su cobertura MEDIDA sobre las firmas de `padre`, que
# es el único bot con el vector completo y por tanto el testigo de qué produce
# de verdad `extraer_features_ventana`. No se declara nada con cobertura pobre:
# eso solo movería la fuga de sitio (`AGENTS.md` regla 8).
#
# Las firmas ya guardadas NO cambian por esto: hace falta un rebuild que las
# regenere. Hasta entonces el vector sigue leyendo 0 en la mitad de alarma.
BOT_FEATURES: Dict[str, Optional[List[str]]] = {
    # `kp_mean` y `kp_max` (cobertura 100 %, no-cero 100 %): estaban en el
    # vector de alfa1 desde siempre y jamás en sus firmas. Son el rasgo que
    # disparó las 44 WATCH del 27-sep.
    # `proton_max` (flujo >10 MeV) se queda declarado aunque YA NO esté en el
    # vector ONNX: el ciclo vivo lo mide desde el 2026-09-24 y así la historia
    # se acumula para el día que haya cobertura. Las dos de densidad son las
    # que el modelo lee ahora (ver `features_onnx.FEATURE_ORDER["alfa1"]`).
    "alfa1": ["bz_mean", "bz_min", "bz_deriv_std", "viento_avg", "viento_max",
              "proton_max", "densidad_prot_mean", "densidad_prot_max",
              "bz_mean_72h", "kp_mean", "kp_max"],
    "beta1": ["kp_mean", "kp_max", "schumann_mean", "schumann_std",
              "sismo_count_win", "sismo_max_mag_win", "fase_lunar",
              "sismo_depth_mean_win",
              "sismo_corteza_win",
              "sismo_profundo_win",
              "sismo_mag_mw_win",
              "sismo_mag_otro_win",
              "sismo_eq_win",
              "sismo_otro_tipo_win",
              "sismo_tsunami_win",
              "sismo_alert_max_win",
              "sismo_mmi_max_win",
              "sismo_cdi_max_win",
              "sismo_felt_sum_win",
              "sismo_sig_max_win",
              "es_sicigia", "kp_max_72h", "sismo_count_72h"],
    # beta2 — los cuatro volcánicos MÁS la marea terrestre.
    #
    # Las ocho de marea entraron al vector el 2026-09-26 y no aquí; ese error es
    # mío y la «mejora de discriminación de 0,0948 a 0,3994» que reporté ese día
    # era el modelo detectando la procedencia, no la marea. Ahora la firma las
    # puede llenar: `signature_engine._marea_de_ventana` hace la MISMA llamada
    # (`marea_ventana(ts, horas=24)`) que el lado vivo en `rasgos_juez._marea`.
    # Cobertura 100 % por construcción --- se calculan por efemérides, no se
    # consultan --- y es la única fuente del sistema sin huecos posibles.
    "beta2": ["so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d",
              "marea_total", "marea_luna", "marea_sol", "marea_sicigia",
              "marea_dist_luna", "marea_rango_24h", "marea_max_24h",
              "marea_deriv"],
    # `vix` se añade el 2026-09-27: el bot FINANCIERO no llevaba el índice
    # del miedo en sus firmas --- 0 de 676 --- mientras loki, que es
    # geofísico, sí lo tenía, y padre lo tenía en 6.959. Sin esto, el
    # vector de delta no puede incorporarlo: entrenaría con la columna en
    # cero y en vivo recibiría 14,87.
    "delta": ["btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h",
              "vix"],
    # alfa2 entrena desde la tabla tbl_cobertura_satelital, que se acumula en
    # ciclos en vivo (no hay backcast de 14 años de cobertura ESA Sentinel).
    # Las firmas de alfa2 empiezan en 0 y crecen con el tiempo operativo.
    # alfa2 pasa a VOTANTE el 2026-10-02 («vota y avisa», decisión del
    # operador). La cuarta señal es `satellite_revisita_dias`, elegida MIDIENDO
    # sobre las 3.231 filas del histórico: 153 valores distintos y 100 % de
    # cobertura, más varianza que cualquier otra columna de la capa. Detalle y
    # por qué no es redundante con el puntaje, en `FEATURE_KEYS`.
    "alfa2": ["satellite_coverage_score", "satellite_thermal_anomalies",
              "satellite_clear_passes", "satellite_revisita_dias"],
    # Omega — el ritmo cósmico: fase lunar/sicigias + resonancia Schumann +
    # envolvente solar + acoplamiento Schumann↔mercado. Todo mapeado de la
    # telemetría existente (sin fetchers nuevos). Sus correlaciones viven en
    # tbl_correlaciones_omega, independientes de las del Padre.
    # `bz_mean`, `kp_mean` y `viento_avg` (cobertura 100 %, no-cero 100 %):
    # omega los pide en su vector de 12 posiciones y no los guardaba.
    "omega": ["fase_lunar", "es_sicigia", "schumann_mean", "schumann_std",
              "kp_max", "kp_max_72h", "bz_min", "proton_max",
              "delta_schumann_coupling", "bz_mean", "kp_mean", "viento_avg"],
    # Loki — Fractal-Bayesiano: Bz, viento solar, Schumann, VIX, LOD.
    # Los nombres eran "bz"/"solar_wind"/"schumann_activity", que NO existen
    # en FEATURE_KEYS: el filtro `if k in feats` dejaba su vector vacío y Loki
    # se saltaba el entrenamiento aunque se le quitara de BOTS_LIVE_ONLY. Se
    # usan los canónicos; vix y lod ya se extraen tras rellenar sus columnas.
    #
    # `kp_mean`, `fase_lunar` y `bz_min` entran con cobertura 100 %.
    # `btc_volatilidad` con 96,2 %: medido sobre las ventanas desde 2014-09, que
    # es el rango real de las firmas de loki (858 firmas, 2014-09-17 →
    # 2026-01-08). Su 48,7 % global es un artefacto de mezclar 1994-2013, donde
    # no había BTC y donde loki no tiene ni una firma.
    "loki": ["bz_mean", "viento_avg", "schumann_mean", "vix", "lod",
             "kp_mean", "fase_lunar", "bz_min", "btc_volatilidad"],
    # Júpiter — atención colectiva: Kp + fulguración solar + interés de
    # búsqueda + Schumann. Seis de sus ocho nombres NO existían en
    # FEATURE_KEYS ("latest_kp", "storm_active", "attention_z",
    # "corr_significant") o no tenían tabla de origen ("xray_mean",
    # "trends_mean"): el filtro `if k in feats` los tiraba y a Júpiter le
    # quedaban 2 de 8, por debajo de su mínimo de 3. Se saltaba con un
    # `continue` mudo y consumió dos rebuilds de ~16 h sin una sola firma.
    # Ahora: nombres canónicos, y xray/trends ya se persisten en el ciclo
    # (tbl_xray_vivo / tbl_trends_vivo). Los conceptos sin serie propia
    # --- "storm_active" y "corr_significant" son derivados booleanos del
    # agente vivo, no magnitudes medidas --- se representan por el Kp y el
    # acoplamiento que sí existen.
    "jupiter": ["kp_mean", "kp_max", "kp_max_72h", "schumann_mean",
                "schumann_std", "xray_mean", "xray_max", "trends_mean"],
    # `None` = vector COMPLETO (42 claves), y tiene un coste medido que hay que
    # conocer antes de tocarlo (2026-10-09, bitácora del 8-oct §11.2-11.3).
    #
    # `similitud` es `1 - media|Δz|/2`: promediar 42 dimensiones no baja la
    # similitud, **encoge la varianza**, así que casi nada cruza el 0,80 fijo.
    # El padre empareja el 0,59 % de las ventanas de evento y el 41 % de sus
    # firmas no empareja NADA. Con 21 dimensiones su lift sería 5,26x contra el
    # 1,77x de hoy, y se activaría 12 veces más.
    #
    # **Y aun así NO se le puso una lista.** Al diseñarla por medición, los
    # cuatro rasgos que encabezan el ranking son de la familia `sismo_*_win`
    # --- la sismicidad PREVIA del propio nodo, que en una ventana de evento es
    # 30-75x la de una de calma. No es fuga de etiqueta (la ventana es
    # `timestamp_blk < ts_evento`, estricta) pero es **agrupamiento de Omori**,
    # lo mismo que la compuerta de habilidad rechaza con
    # `origen == "agrupamiento_omori"`. Y quitando esa familia el lift cae a
    # **1,04-1,09x** sobre Bz, Kp, LOD, mareas, fase lunar, VIX y protones:
    # o sea que el 5,26x venía ENTERO del historial sísmico.
    #
    # Darle una lista hoy cocería un 5x de Omori con cara de precursor en la
    # memoria del que avisa. Se revisa el día que haya rasgos que no sean la
    # historia del nodo. Reproducir: `deploy/disenar_rasgos_padre.py` y
    # `deploy/sin_omori.py`.
    "padre": None,  # full vector --- a propósito; ver arriba
}

# Bots que NO forman firmas a propósito, por no alcanzar
# MIN_DIMENSIONES_COMPARABLES con las señales de que disponen hoy.
#
# NO es una carencia: es un ROL. Estos bots operan en el ciclo vivo y emiten
# detecciones; lo que no hacen es votar con el peso de una firma consolidada.
# Funcionan como AVISO TEMPRANO --- una anomalía suya es motivo para ir a
# mirar, no una predicción del consenso.
#
# alfa2 SALIÓ de aquí el 2026-10-02: «vota y avisa» (decisión del operador).
#
# Estuvo dentro desde el 2026-09-24 porque sus tres features
# ---coverage_score, thermal_anomalies, clear_passes--- nunca llegaban a las
# cuatro que exige el emparejamiento, y las alternativas de entonces eran malas:
# bajar el suelo (debilita a TODOS los bots) o prestarle features de otras capas
# (deja de ser satelital). La condición escrita para que saliera era «cuando la
# capa satelital aporte una cuarta señal real», y se cumplió: la capa aporta
# `satellite_revisita_dias`, con 153 valores distintos y 100 % de cobertura
# sobre 70 días de histórico --- más varianza que cualquier otra columna suya.
#
# No pierde el aviso temprano al votar: sus sensores siguen yendo casi en tiempo
# real y su señal ya llegaba al consenso (está en `padre.FAMILIES` como junior
# de `space_weather`). Lo que gana es memoria y peso propios.
#
# El dashboard rotula `notificador` a quien NO esté en `TBL_PESOS_BOTS`
# (api.py:567), así que se corrige solo en cuanto la Fase 2 le dé peso.
#
# El conjunto se conserva VACÍO a propósito: es el mecanismo, y el día que otro
# bot se quede sin señales suficientes tiene que poder entrar aquí en vez de
# fallar en silencio.
BOTS_ESPERANDO_SENALES: set = set()


def _auditar_features_declaradas(bots_activos) -> None:
    """Avisa, ANTES de gastar horas, si algún bot no puede formar su vector.

    El filtro `{k: v for k, v in features.items() if k in keys}` descarta en
    silencio toda feature cuyo nombre no exista en FEATURE_KEYS. Si quedan
    menos que el mínimo del bot, se salta con un `continue` mudo: el
    entrenamiento termina "bien", el bot no aparece en TBL_PESOS_BOTS y nadie
    se entera hasta auditar la tabla a mano.

    Le pasó a Loki (nombres no canónicos) y seguía pasándole a Júpiter, que
    consumió dos rebuilds completos de ~16 h sin registrar una sola firma.
    """
    disponibles = set(FEATURE_KEYS)
    for bot, keys in bots_activos.items():
        if keys is None:
            continue
        existen = [k for k in keys if k in disponibles]
        faltan = [k for k in keys if k not in disponibles]
        minimo = MIN_FEATURES_POR_BOT.get(bot, 0)
        if faltan:
            logger.warning(
                "%s declara %d features que NO existen en FEATURE_KEYS y se "
                "descartarán en silencio: %s", bot, len(faltan), faltan)
        if len(existen) < minimo:
            if bot in BOTS_ESPERANDO_SENALES:
                logger.info(
                    "%s opera como NOTIFICADOR (aviso temprano), no como "
                    "votante: tiene %d features y el suelo de emparejamiento "
                    "son %d. Decisión deliberada --- formará firmas cuando su "
                    "capa aporte más señales.",
                    bot, len(existen), minimo)
            else:
                logger.error(
                    "%s NO PUEDE ENTRENAR: le quedan %d features utilizables "
                    "de las %d declaradas y necesita %d. No registrará "
                    "ninguna firma y no aparecerá en TBL_PESOS_BOTS. "
                    "Utilizables: %s",
                    bot, len(existen), len(keys), minimo, existen)


# Features mínimas para que un bot registre una firma.
#
# NINGUNO puede estar por debajo de MIN_DIMENSIONES_COMPARABLES: por debajo de
# ese suelo, similitud() devuelve 0.0 y la firma no empareja ni consigo misma.
# Registrar ahí no es "aprender poco" --- es fabricar memoria inservible. Se
# permitía con 2 y 3 y nadie lo notó: Júpiter acumuló 44.830 firmas, TODAS
# vistas una sola vez, recurrencia máxima 1. El bot parecía entrenar.
#
# alfa2 se queda deliberadamente por encima de lo que puede alcanzar: sus tres
# features satelitales nunca llegan a cuatro, así que NO formará firmas hasta
# que la capa satelital aporte más señales. Decisión del operador (2026-09-22):
# preferible que no tenga memoria a que tenga memoria que no empareja.
MIN_FEATURES_POR_BOT = {"alfa1": 4, "beta1": 4, "beta2": 4, "delta": 4,
                        "alfa2": 4, "omega": 4, "loki": 4, "jupiter": 4,
                        "padre": 5}

# El contrato se verifica al importar: si alguien baja un mínimo por debajo del
# suelo, el módulo no carga. Un fallo al arranque es barato; 16 h de cómputo
# produciendo firmas singleton, no.
_bajo_el_suelo = {b: n for b, n in MIN_FEATURES_POR_BOT.items()
                  if n < MIN_DIMENSIONES_COMPARABLES}
if _bajo_el_suelo:
    raise ValueError(
        f"MIN_FEATURES_POR_BOT por debajo de MIN_DIMENSIONES_COMPARABLES="
        f"{MIN_DIMENSIONES_COMPARABLES}: {_bajo_el_suelo}. Esos bots "
        f"registrarían firmas que similitud() nunca podrá emparejar."
    )

# Each bot only trains inside its own historical window (data availability):
# beta2 = desde 2012 (catálogo volcánico NASA MSVOLSO2L4)
# delta = desde 2016 (BTC/cripto/tendencias)
# loki = desde 2014 (necesita datos financieros VIX + espacio + Schumann)
# jupiter = desde 2014 (necesita datos financieros + Kp histórico)
# alfa2 NO tiene ventana de arranque fija: entrena solo desde la primera fila
# de tbl_cobertura_satelital (datos en vivo). El backcast no la incluye.
BOT_DESDE: Dict[str, str] = {
    "beta2": "2012-01-01",
    "delta": "2016-01-01",
    "loki": "2014-01-01",
    "jupiter": "2014-01-01",
}

# Bots que solo entrenan desde datos EN VIVO (no tienen backcast en la DB).
# El loop de Fase 1 los salta si la fuente es tbl_historico_sismico_raw
# sin filas de tbl_cobertura_satelital en el mismo periodo.
# Antes {"alfa2", "jupiter", "loki"}: los tres quedaban sin memoria ni peso,
# invisibles para el consenso ponderado. La exclusión era el síntoma, no la
# causa — sus features no existían en el extractor o sus datos estaban muertos.
# Resuelto: alfa2 ya lee la cobertura histórica, y Loki tiene vix y lod
# rellenados desde ^VIX e IERS. Jupiter entrena con las features que sí tienen
# histórico (Kp, Schumann); las de Google Trends solo cubren 90 días y se
# acumulan en vivo.
BOTS_LIVE_ONLY: set = set()


def _event_class(mag: float) -> str:
    if mag >= 7.0:
        return "SISMO_M7"
    if mag >= 6.0:
        return "SISMO_M6"
    if mag >= 5.0:
        return "SISMO_M5"
    if mag >= 4.5:
        return "SISMO_M4"      # 4.5–4.99: piso de prediccion y castigo; la alerta es M6
    if mag >= 4.0:
        return "SISMO_M4_obs"  # 4.0–4.49: observado, no exigible
    if mag >= 3.0:
        return "SISMO_M3_obs"  # 3.0–3.99: observado, no exigible
    return "SISMO_M2_obs"      # 2.0–2.99: observado, no exigible


def _event_class_volcanico(vei: float) -> str:
    """Volcanic event class by VEI (Volcanic Explosivity Index)."""
    if vei >= 5.0:
        return "ERUPCION_VEI5"
    if vei >= 4.0:
        return "ERUPCION_VEI4"
    return "ERUPCION_VEI3"


def _event_class_solar(kp_max: float) -> str:
    """Solar storm event class by Kp index (NOAA G-scale proxy)."""
    if kp_max >= 9.0:
        return "TORMENTA_Kp9"   # G5 extreme
    if kp_max >= 7.0:
        return "TORMENTA_Kp7"   # G3 strong
    return "TORMENTA_Kp6"       # G2 moderate


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


def derivar_eventos_no_sismicos(conn: sqlite3.Connection) -> int:
    """Derive non-seismic event catalog from existing backcast tables.

    Volcanic: rows in tbl_desgasificacion_raw with vei >= 3.
    Solar storms: onset rows in tbl_clima_espacial_raw where kp_max >= 6.
    An onset is the first row in a consecutive block above the threshold;
    i.e., the previous row in the ordered dataset was NOT a storm. This
    relies on the hourly resolution of tbl_clima_espacial_raw — rows are
    consecutive 1-hour samples. If the data has gaps, the onset detection
    may still fire at the start of each gap-separated burst, which is
    acceptable (each burst is a distinct storm event).

    Stores to tbl_eventos_no_sismicos. Idempotent (INSERT OR IGNORE).
    Returns the number of rows actually inserted (not total attempts).
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_eventos_no_sismicos "
        "(timestamp_blk TEXT NOT NULL, id_nodo INTEGER NOT NULL, "
        " event_class TEXT NOT NULL, fuente TEXT DEFAULT '', "
        " intensidad REAL DEFAULT 0.0, "
        " PRIMARY KEY (timestamp_blk, id_nodo, event_class))"
    )
    total = 0

    # ── Volcanic events ──────────────────────────────────────────────
    try:
        erupciones = conn.execute(
            "SELECT timestamp_blk, id_nodo, vei FROM tbl_desgasificacion_raw "
            "WHERE vei >= 3 ORDER BY timestamp_blk"
        ).fetchall()
        for ts, id_nodo, vei in erupciones:
            clase = _event_class_volcanico(float(vei))
            before = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO tbl_eventos_no_sismicos "
                "(timestamp_blk, id_nodo, event_class, fuente, intensidad) "
                "VALUES (?, ?, ?, 'tbl_desgasificacion_raw', ?)",
                (ts, id_nodo, clase, float(vei)),
            )
            total += conn.total_changes - before
        logger.info(f"  Eventos volcánicos derivados: {len(erupciones)}")
    except sqlite3.OperationalError:
        logger.info("  tbl_desgasificacion_raw sin datos VEI — saltando volcánicos")

    # ── Solar storm onset events (global → node 0) ───────────────────
    try:
        solar_rows = conn.execute(
            "SELECT timestamp_blk, kp_max FROM tbl_clima_espacial_raw "
            "WHERE kp_max IS NOT NULL ORDER BY timestamp_blk"
        ).fetchall()
        prev_storm = False
        n_solar = 0
        for ts, kp in solar_rows:
            if kp is None:
                prev_storm = False
                continue
            is_storm = float(kp) >= 6.0
            if is_storm and not prev_storm:
                clase = _event_class_solar(float(kp))
                conn.execute(
                    "INSERT OR IGNORE INTO tbl_eventos_no_sismicos "
                    "(timestamp_blk, id_nodo, event_class, fuente, intensidad) "
                    "VALUES (?, 0, ?, 'tbl_clima_espacial_raw', ?)",
                    (ts, clase, float(kp)),
                )
                n_solar += 1
                total += 1
            prev_storm = is_storm
        logger.info(f"  Tormentas solares derivadas (onset): {n_solar}")
    except sqlite3.OperationalError:
        logger.info("  tbl_clima_espacial_raw sin datos Kp — saltando tormentas solares")

    conn.commit()
    logger.info(f"Eventos no sísmicos derivados total: {total}")
    return total


def entrenar_reconocimiento(
    db_path: str,
    max_eventos: Optional[int] = None,
    bots: Optional[List[str]] = None,
    desde: Optional[str] = None,
) -> Dict:
    """Fase 1 — learn signatures from every observed historical event.

    Observes ALL magnitudes >= MIN_MAGNITUD_OBSERVAR (2.5): bots register
    firma patterns for every size of event so that small precursors are
    captured. The Juez logs an ACIERTO for every successful registration —
    this builds the positive pattern-history used by resumen_por_bot() even
    before Fase 2 discipline runs.

    Events below MIN_MAGNITUD_FIRMA (4.5) are non-enforceable: they generate
    firmas and Juez ACIERTOs but never trigger discipline (castigo).

    bots: restrict registration to these bots (e.g. ["beta2", "delta"] for
    an incremental training pass without inflating other bots' recurrence).
    """
    conn = conexion_de_lote(db_path)
    memoria = FirmaMemoria(conn)
    juez = Juez(conn)
    bots_activos = {
        b: k for b, k in BOT_FEATURES.items() if bots is None or b in bots
    }
    _auditar_features_declaradas(bots_activos)

    # If every active bot has a bounded window, skip events before the
    # earliest one (no bot would register them anyway).
    desde_global = None
    if bots is not None and all(b in BOT_DESDE for b in bots_activos):
        desde_global = min(BOT_DESDE[b] for b in bots_activos)

    query = (
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= ? "
    )
    params: tuple = (MIN_MAGNITUD_OBSERVAR,)
    if desde_global:
        query += "AND timestamp_blk >= ? "
        params = (MIN_MAGNITUD_OBSERVAR, desde_global)
    # `desde` acota a lo que AÚN NO se ha aprendido. Medido el 2026-09-25: la
    # corrida completa recorre 186.806 eventos a 1,5 por segundo --- 36 HORAS ---
    # y por eso nunca se programó, así que el sistema dejó de aprender el 3 de
    # septiembre. Con el corte, lo nuevo de un día se aprende en minutos.
    if desde:
        query += "AND timestamp_blk > ? "
        params = params + (desde,)
    query += "ORDER BY timestamp_blk"
    eventos = conn.execute(query, params).fetchall()
    if max_eventos:
        eventos = eventos[:max_eventos]

    logger.info(
        f"=== FASE 1 RECONOCIMIENTO: {len(eventos)} eventos "
        f"M{MIN_MAGNITUD_OBSERVAR}+ (exigibles desde M{MIN_MAGNITUD_FIRMA}) ==="
    )

    stats = {"eventos": len(eventos), "firmas_nuevas": 0, "recurrencias": 0,
             "sin_datos": 0, "juez_aciertos": 0}

    import time as _time

    for idx, (ts_evento, id_nodo, mag) in enumerate(eventos):
        if idx % 1000 == 0 and idx > 0:
            logger.info(
                f"  Fase 1 progreso: {idx}/{len(eventos)} eventos "
                f"({stats['firmas_nuevas']} firmas, "
                f"{stats['recurrencias']} recurrencias)"
            )
        features = extraer_features_ventana(conn, ts_evento, id_nodo)
        if features is None:
            stats["sin_datos"] += 1
            continue

        clase = _event_class(mag)
        evento_ref = f"{ts_evento}|nodo{id_nodo}|M{mag:.1f}"
        bots_registrados: List[str] = []

        for bot, keys in bots_activos.items():
            # alfa2 (y cualquier bot live-only) NO tiene datos en el backcast;
            # sus firmas se acumulan desde ciclos operativos en tbl_cobertura_satelital.
            if bot in BOTS_LIVE_ONLY:
                continue
            desde = BOT_DESDE.get(bot)
            if desde and ts_evento < desde:
                continue  # event predates this bot's historical window
            sub = (
                features if keys is None
                else {k: v for k, v in features.items() if k in keys}
            )
            if len(sub) < MIN_FEATURES_POR_BOT[bot]:
                continue
            _, _, es_nueva = memoria.registrar(
                bot, clase, id_nodo, sub, evento_ref, ts_evento
            )
            if es_nueva:
                stats["firmas_nuevas"] += 1
            else:
                stats["recurrencias"] += 1
            bots_registrados.append(bot)

        # Juez: log ACIERTO for every bot that successfully registered a firma.
        # Uses ventana_h=0 so records resolve immediately (event is already known).
        # This builds the positive audit history from the learning phase onward.
        for bot in bots_registrados:
            juez.registrar_prediccion(
                bot_name=bot,
                prediccion="alert",
                confianza=1.0,
                ventana_h=0,
                detalles={
                    "fase": "reconocimiento",
                    "clase": clase,
                    "evento": evento_ref,
                    "mag": round(float(mag), 1),
                    "exigible": float(mag) >= MIN_MAGNITUD_FIRMA,
                },
                timestamp=_time.time(),
            )
        if bots_registrados:
            juez.evaluar_pendientes(
                evento_ocurrido=True,
                verdad=evento_ref,
                firma_conocida=False,  # Fase 1 is learning, not enforcement
                fase="reconocimiento",  # NUNCA resolver las vivas del launcher
            )
            stats["juez_aciertos"] += len(bots_registrados)

    stats["memoria"] = memoria.stats()
    logger.info(f"Fase 1 completa: {stats}")
    conn.close()
    return stats


def backtest_disciplinario(db_path: str, bots: Optional[List[str]] = None) -> Dict:
    """Fase 2 — el Padre castiga.

    Re-presents the member events of every consolidated signature:
      - Bot recognizes the pattern -> ACIERTO logged to Juez + mild refuerzo.
      - Bot fails to recognize enforceable knowledge (mag >= MIN_MAGNITUD_FIRMA)
        -> castigo hijo (x1): weight drops and the Juez records FALLO.
      - The Padre's own meta-signature fails -> castigo Padre (x2): double
        weight decay and double Juez severity (base_geo protocol).
      - Events below MIN_MAGNITUD_FIRMA are observed but NOT disciplined: Juez
        still records the FALLO pattern for audit, but castigar() is skipped so
        sub-threshold misses do not erode a bot's credibility weight.
    The adjusted weights persist in TBL_PESOS_BOTS and the Padre uses them
    to weigh each bot's vote in live consensus.
    """
    conn = conexion_de_lote(db_path)
    memoria = FirmaMemoria(conn)
    juez = Juez(conn)

    consolidadas = memoria.consolidadas()
    if bots is not None:
        consolidadas = [f for f in consolidadas if f["bot_name"] in bots]
    logger.info(
        f"=== FASE 2 DISCIPLINA: {len(consolidadas)} firmas consolidadas ==="
    )

    stats = {"firmas_evaluadas": 0, "reconocidas": 0, "fallos": 0,
             "castigos_hijo": 0, "castigos_padre": 0,
             "atencion_redistribuida": 0, "juez_aciertos": 0}

    from sentinel_omega.core.firmas.signature_engine import similitud
    from sentinel_omega.core.juez.pesos import (
        PESO_MAX, castigar, reforzar, cargar_pesos,
    )

    import time as _time

    # evento_ref -> {bot: reconoció} — needed for attention redistribution
    resultados_por_evento: Dict[str, Dict[str, bool]] = {}

    for firma in consolidadas:
        bot = firma["bot_name"]
        es_padre = bot == "padre"

        # Eventos desde la tabla hija normalizada (1NF).
        eventos = [
            r[0] for r in conn.execute(
                "SELECT evento_ref FROM tbl_firma_eventos "
                "WHERE firma_id = ? ORDER BY orden",
                (firma["firma_id"],),
            )
        ]

        for ref in eventos:
            try:
                ts_evento, nodo_part, mag_part = ref.split("|")
                id_nodo = int(nodo_part.replace("nodo", ""))
                # mag_part may be "M6.4" (seismic) or "ERUPCION_VEI4:4.0" (non-seismic)
                mag_str = mag_part.replace("M", "").split(":")[0]
                magnitud = float(mag_str)
            except (ValueError, IndexError):
                continue

            # base_geo: gravity scales with event size above the enforcement floor
            # (M5 -> 1, M6 -> 2, M7 -> 3); sub-threshold events stay at 1.0
            gravedad = 1.0 + max(0.0, magnitud - MIN_MAGNITUD_FIRMA)
            es_exigible = magnitud >= MIN_MAGNITUD_FIRMA

            features = extraer_features_ventana(conn, ts_evento, id_nodo)
            if features is None:
                continue

            keys = BOT_FEATURES.get(bot)
            sub = (
                features if keys is None
                else {k: v for k, v in features.items() if k in keys}
            )
            sim = similitud(sub, firma["features"])
            stats["firmas_evaluadas"] += 1
            reconocio = sim >= SIMILARITY_ALERT
            resultados_por_evento.setdefault(ref, {})[bot] = reconocio

            if reconocio:
                stats["reconocidas"] += 1
                reforzar(conn, bot)
                # Log ACIERTO so resumen_por_bot() and asertividad reflect
                # successful recognitions, not just failures.
                juez.registrar_prediccion(
                    bot_name=bot,
                    prediccion="alert",
                    confianza=round(sim, 3),
                    ventana_h=0,
                    detalles={
                        "fase": "backtest",
                        "firma_id": firma["firma_id"],
                        "evento": ref,
                        "similitud": round(sim, 3),
                        "gravedad": round(gravedad, 2),
                    },
                    timestamp=_time.time(),
                )
                juez.evaluar_pendientes(
                    evento_ocurrido=True,
                    verdad=ref,
                    firma_conocida=es_exigible,
                    fase="backtest",
                )
                stats["juez_aciertos"] += 1
            else:
                stats["fallos"] += 1
                # Only discipline (weight penalty) for enforceable events.
                # Sub-threshold misses are recorded for auditing but do not
                # erode the bot's credibility.
                if es_exigible:
                    castigar(conn, bot, es_padre=es_padre, gravedad=gravedad)
                    if es_padre:
                        stats["castigos_padre"] += 1
                    else:
                        stats["castigos_hijo"] += 1

                juez.registrar_prediccion(
                    bot_name=bot,
                    prediccion="no_signal",
                    confianza=0.0,
                    ventana_h=0,
                    detalles={
                        "fase": "backtest",
                        "firma_id": firma["firma_id"],
                        "evento": ref,
                        "similitud": round(sim, 3),
                        "gravedad": round(gravedad, 2),
                        "exigible": es_exigible,
                    },
                )
                juez.evaluar_pendientes(
                    evento_ocurrido=True,
                    verdad=ref,
                    firma_conocida=es_exigible,
                    multiplicador=2.0 if es_padre else 1.0,
                    gravedad=gravedad,
                    fase="backtest",
                )

    # base_geo: when the Padre missed an event that a subordinate DID see,
    # the punished Padre is forced to give more attention weight to the bot
    # that was right — extra reinforcement for that bot.
    for ref, resultados in resultados_por_evento.items():
        if resultados.get("padre") is False:
            for bot, reconocio in resultados.items():
                if bot != "padre" and reconocio:
                    reforzar(conn, bot, hasta=PESO_MAX)
                    stats["atencion_redistribuida"] += 1
                    logger.info(
                        f"ATENCIÓN REDISTRIBUIDA: {bot} vio {ref} que el "
                        f"Padre ignoró — refuerzo extra"
                    )

    stats["auditoria"] = juez.resumen_por_bot()
    stats["pesos"] = cargar_pesos(conn)

    # Aligerar el historial: el backtest evaluó TODO el catálogo para ajustar
    # los pesos y calcular la reincidencia, pero esos FALLOs son transitorios
    # y se regeneran en cada entrenamiento. Ya cumplieron su función — nos
    # quedamos con lo significativo (los pesos + las predicciones VIVAS) y
    # podamos el registro del backtest para que el ledger no crezca sin fin.
    # Por columna fase (estricta) — las filas 'viva' JAMÁS se tocan: la
    # auditoría viva es append-only (PENDIENTE→resuelto, nunca DELETE).
    podados = conn.execute(
        "DELETE FROM TBL_JUEZ_AUDITORIA WHERE fase = 'backtest'"
    ).rowcount
    conn.commit()
    stats["auditoria_backtest_podada"] = podados

    logger.info(f"Fase 2 completa: {stats}")
    conn.close()
    return stats


def ultimo_bloque_aprendido(db_path: str) -> Optional[str]:
    """El bloque más reciente que YA produjo firma. None si no hay ninguno."""
    conn = conexion_de_lote(db_path)
    try:
        fila = conn.execute("SELECT MAX(ts_evento) FROM tbl_firma_eventos").fetchone()
        return fila[0] if fila else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def entrenar_incremental(db_path: str, max_eventos: Optional[int] = None) -> Dict:
    """Aprende SOLO los eventos posteriores al último que ya dejó firma.

    Existe porque la corrida completa tarda 36 h (186.806 eventos a 1,5/s,
    medido el 2026-09-25) y por eso nunca se programó: el sistema dejaba de
    aprender entre reconstrucciones manuales. Esto sí cabe en un temporizador.

    No toca las fases 2, lags ni correlaciones: esas repasan todo el histórico
    y son el grueso del coste. Aquí solo se registran las firmas nuevas.
    """
    desde = ultimo_bloque_aprendido(db_path)
    logger.info("Entrenamiento incremental desde %s", desde or "el principio")
    stats = entrenar_reconocimiento(db_path, max_eventos=max_eventos, desde=desde)
    stats["desde"] = desde
    return stats



def calcular_umbral_muro(db_path: str) -> Dict[str, Dict]:
    """Calcula y guarda el umbral del muro por magnitud.

    No es un rebuild. No toca firmas, pesos, cimatica ni el corte en vivo.
    La fila es el ciclo cuya marca es la ultima estrictamente anterior al
    sismo. El ciclo del mismo instante no entra. Si no hay suficientes
    sismos, el umbral queda NULL. No se copia el 3.
    """
    from datetime import timezone

    from sentinel_omega.core.precursor.muro_cinco_eventos import (
        CLASES_BLANCO_MURO,
        clase_blanco_muro,
        WALL_ATMOSFERICO,
        WALL_FINANCIERO,
        WALL_GEOFISICO,
        WALL_OCEANICO,
        WALL_SOLAR,
        entrenar_umbral_por_magnitud,
        filas_muros_antes_del_sismo,
    )

    columnas = (
        ("wall_geofisico", WALL_GEOFISICO),
        ("wall_atmosferico", WALL_ATMOSFERICO),
        ("wall_oceanico", WALL_OCEANICO),
        ("wall_solar", WALL_SOLAR),
        ("wall_financiero", WALL_FINANCIERO),
    )
    conn = conexion_de_lote(db_path)
    try:
        crudos = conn.execute(
            "SELECT timestamp, wall_geofisico, wall_atmosferico, "
            "wall_oceanico, wall_solar, wall_financiero "
            "FROM TBL_MURO_EVENTOS ORDER BY timestamp"
        ).fetchall()
        ciclos = []
        for ts, *flags in crudos:
            senales = tuple(
                nombre for (_, nombre), flag in zip(columnas, flags) if flag
            )
            ciclos.append((float(ts), senales))
        if ciclos:
            desde = datetime.fromtimestamp(ciclos[0][0], timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            sismos_raw = conn.execute(
                "SELECT time_utc, mag FROM tbl_eventos_sismicos_fuente "
                "WHERE mag >= ? AND time_utc >= ? "
                "AND (event_type IS NULL OR event_type = 'earthquake') "
                "ORDER BY time_utc",
                (MIN_MAGNITUD_FIRMA, desde),
            ).fetchall()
        else:
            sismos_raw = []
        sismos = []
        for time_utc, mag in sismos_raw:
            ts = datetime.strptime(str(time_utc)[:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            ).timestamp()
            sismos.append((ts, float(mag)))
        filas = filas_muros_antes_del_sismo(ciclos, sismos)
        umbral = entrenar_umbral_por_magnitud(filas)
        ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tbl_muro_umbral_magnitud ("
            "clase TEXT PRIMARY KEY, senales TEXT NOT NULL, "
            "umbral INTEGER, n_filas INTEGER NOT NULL, "
            "calculado_en TEXT NOT NULL)"
        )
        conn.execute("DELETE FROM tbl_muro_umbral_magnitud")
        for clase in CLASES_BLANCO_MURO:
            dato = umbral[clase]
            conn.execute(
                "INSERT INTO tbl_muro_umbral_magnitud "
                "(clase, senales, umbral, n_filas, calculado_en) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    clase,
                    json.dumps(list(dato["senales"])),
                    dato["umbral"],
                    sum(
                        1 for _, mag in filas
                        if mag is not None and clase_blanco_muro(mag) == clase
                    ),
                    ahora,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return umbral


def entrenar(
    db_path: str,
    max_eventos: Optional[int] = None,
    paralelo: bool = False,
) -> Dict:
    """Full training run: Fase 1 (seismic) + Fase 1b (non-seismic) + Fase 2 + lags + correlaciones.

    Envuelto en la medición del sesgo de aprendizaje (realidad vs fantasía):
    se mide ANTES del pre-entrenamiento (línea base, sin castigo) y DESPUÉS
    de la disciplina (con castigo si la decisión real sigue floja), y se
    reporta cuánto mejoró el reconocimiento CAUSAL de cada bot con esta
    corrida — la diferencia entre las decisiones antes y después de aprender.

    `paralelo` reparte la Fase 1 por bot, un proceso cada uno sobre su copia
    (`entrenar_paralelo`). El eje que no fragmenta la memoria es el bot, no el
    mes: las firmas de un bot jamás se cruzan con las de otro. Va apagado por
    defecto --- lo enciende el rebuild, que es quien tiene la corrida larga ---
    y se ignora con `max_eventos`, donde los dos caminos NO son equivalentes
    (el recorte se aplica antes del filtro por fecha de arranque; el módulo
    paralelo lo explica).
    """
    from sentinel_omega.infrastructure.pipeline.mantenimiento import (
        evaluar_sesgo_aprendizaje,
    )

    # PRE: línea base sin disciplinar (¿qué tan real era su competencia antes?)
    sesgo_pre = {}
    try:
        sesgo_pre = evaluar_sesgo_aprendizaje(db_path, aplicar_castigo=False)
        logger.info(f"Sesgo PRE-entrenamiento (línea base): {sesgo_pre.get('por_bot')}")
    except Exception as e:
        logger.warning(f"Sesgo pre-entrenamiento no disponible: {e}")

    if paralelo and max_eventos:
        logger.warning(
            "paralelo + max_eventos no son compatibles (no dan el mismo "
            "resultado): se usa la Fase 1 secuencial."
        )
        paralelo = False
    if paralelo:
        from sentinel_omega.infrastructure.pipeline.entrenar_paralelo import (
            entrenar_reconocimiento_paralelo,
        )
        fase1 = entrenar_reconocimiento_paralelo(db_path)
    else:
        fase1 = entrenar_reconocimiento(db_path, max_eventos=max_eventos)
    fase1b = entrenar_reconocimiento_no_sismico(db_path, max_eventos=max_eventos)
    fase2 = backtest_disciplinario(db_path)
    lags = calcular_lags_anticipacion(db_path)
    correlaciones = calcular_correlaciones_evento(db_path)

    # Entrenamiento cimático: graba en tbl_cimatica_patrones la telemetría
    # de la víspera de cada evento histórico con frecuencias ya contadas —
    # la cimática viva no empieza de cero.
    cimatica_stats = {}
    try:
        from sentinel_omega.core.firmas.cimatica import entrenar_cimatica
        cimatica_stats = entrenar_cimatica(db_path, max_eventos=max_eventos)
    except Exception as e:
        logger.warning(f"Entrenamiento cimático no disponible: {e}")

    # ── Qué memoria es EXIGIBLE, antes de medir el sesgo ────────────────────
    #
    # Va aquí y no al final del rebuild por una razón de orden: el sesgo POST
    # es el que CASTIGA, y desde el 2026-10-07 castiga sobre la ganancia
    # (`causal - falsa_alarma`), que se mide sobre las firmas EXIGIBLES. Si la
    # discriminación se midiera después, el castigo saldría de un conjunto que
    # el sistema ya no consulta --- las 23.244 consolidadas en vez de las que
    # discriminan.
    #
    # Y hace falta aquí dentro porque el rebuild hace `DELETE FROM TBL_FIRMAS`:
    # las marcas de una medición anterior se van con las filas, así que cada
    # reconstrucción tiene que volver a medir o todo vuelve a contar como
    # exigible (NULL = exigible, para no demotar en silencio lo no mirado).
    #
    # Medido el 2026-10-07 sobre produccion: de 30.367 firmas con recurrencia
    # >= 3, solo 1.023 (3,4 %) emparejan eventos mas que calma. `padre`: 0 de
    # 21.076.
    discriminacion = {}
    try:
        from sentinel_omega.infrastructure.pipeline.mantenimiento import (
            medir_discriminacion_firmas,
        )
        discriminacion = medir_discriminacion_firmas(db_path, aplicar=True)
        logger.info("Discriminación de firmas: %s exigibles de %s (criterio: %s)",
                    discriminacion.get("exigibles"), discriminacion.get("firmas"),
                    discriminacion.get("criterio"))
    except Exception as e:  # noqa: BLE001 — el rebuild sigue
        logger.warning("Discriminación de firmas no disponible: %s", e)

    # POST: medición disciplinaria (castiga al Padre/Omega si lo real no mejora)
    sesgo_post = {}
    mejora = {}
    try:
        sesgo_post = evaluar_sesgo_aprendizaje(db_path, aplicar_castigo=True)
        pre_bots = sesgo_pre.get("por_bot", {})
        for bot, d in sesgo_post.get("por_bot", {}).items():
            antes = pre_bots.get(bot, {}).get("causal")
            if antes is not None:
                mejora[bot] = round(d["causal"] - antes, 4)
        logger.info(f"Mejora causal por bot (post - pre): {mejora}")
    except Exception as e:
        logger.warning(f"Sesgo post-entrenamiento no disponible: {e}")

    umbral_muro = calcular_umbral_muro(db_path)
    return {"fase1": fase1, "fase1b": fase1b, "fase2": fase2, "lags": lags,
            "correlaciones": correlaciones,
            "cimatica": cimatica_stats,
            "sesgo_pre": sesgo_pre.get("por_bot", {}),
            "sesgo_post": sesgo_post.get("por_bot", {}),
            "mejora_causal": mejora,
            "discriminacion": discriminacion,
            "umbral_muro": umbral_muro}


# Offsets probados: la ventana de la firma termina N horas ANTES del evento.
# El lag de un evento es el offset MÁS TEMPRANO donde la firma ya se reconocía.
# Rejilla GRUESA para acotar el inicio del emparejamiento (14d, 10d, 7d, 5d, 3d, 1d).
# Sus huecos son de 48 a 96 h, así que por sí sola mide en días, no en horas:
# medido el 2026-09-27, de 37 valores distintos de `lag_promedio_h` los seis
# puntos exactos de esta rejilla concentran las firmas y el resto son promedios
# de dos o tres puntos. Y como el barrido va de lejos a cerca y para en el primer
# emparejamiento, SIEMPRE REDONDEA HACIA ABAJO: una firma que empieza a emparejar
# a las 100 h se registra como 72.
#
# El extremo CERCANO se añadió el 2026-10-08. La rejilla paraba en 24 h, y una
# firma cuyo patrón solo es visible en las últimas horas devolvía `None` --- o
# sea «sin anticipación medida», indistinguible de «no se midió». Medido sobre
# 40 firmas exigibles de beta1/SISMO_M4, el porcentaje que empareja NO se
# derrumba al acercarse al evento, sube:
#
#     offset   336   240   168   120    72    48    24    12     6     3     1     0
#     empareja  33%   38%   40%   35%   53%   45%   58%   65%   73%   70%   80%   80%
#
# Así que por debajo de 24 h hay más de la mitad de la señal, y se estaba
# tirando. Doce puntos en vez de seis: el coste sube ~2x y la bisección sigue
# acotando el tramo.
LAG_OFFSETS_H = [336, 240, 168, 120, 72, 48, 24, 12, 6, 3, 1]

# Resolución del refinamiento por bisección dentro del tramo acotado.
LAG_RESOLUCION_H = 1

# Tope POR BOT Y CLASE, y se cuenta en FIRMAS. Hasta el 2026-10-08 el contador
# (`evaluados`) se incrementaba por EVENTO SONDEADO y cada firma gasta hasta 3
# (`LIMIT 3`), así que un «tope de 150» eran **50 firmas** --- y el resto se
# saltaba con un `continue` SIN LOG (regla dura 10). El efecto medido ese día,
# y la huella estaba a la vista en los datos:
#
#     beta1 SISMO_M4   417 exigibles -> 9 con lag     <- topado
#     beta1 SISMO_M5   260 exigibles -> 12 con lag    <- topado
#     beta1 SISMO_M4_obs 20 exigibles -> 20 con lag   <- cabe entero
#     beta1 SISMO_M7     19 exigibles -> 19 con lag   <- cabe entero
#
# Los cubos PEQUEÑOS con cobertura total y los GRANDES casi vacíos es el revés
# de lo que haría un muestreo: era el presupuesto, no la física. De las 367
# firmas saltadas en beta1/SISMO_M4 se midió a mano que entre el 33 % y el 80 %
# SÍ dan lag según el offset. Se perdía el tiempo de aviso de la mayoría de las
# firmas con las que el sistema alerta.
#
# El tope existe porque esto corría sobre 19.578 firmas. Hoy `consolidadas()`
# devuelve solo las EXIGIBLES (982 el 8-oct), así que cabe medirlas TODAS y el
# tope deja de morder; se conserva alto como malla de seguridad por si el
# conjunto exigible vuelve a crecer.
LAG_MUESTRA_POR_CLASE = 2000

# Sondeos de CALMA por firma, para el modelo nulo del lag. Tres, los mismos que
# eventos (`LIMIT 3`), para que las dos cifras salgan de muestras comparables.
LAG_MUESTRA_CALMA = 3

# Semilla fija: dos corridas sobre la misma base tienen que dar el mismo nulo,
# o la cifra se mueve sin que nada haya cambiado y no hay forma de comparar.
LAG_SEMILLA_CALMA = 20261008

# Horizonte que define «calma»: ninguna hora con evento en las siguientes N h
# en ESE nodo. Es el mismo que usa `medir_discriminacion_firmas`.
LAG_HORIZONTE_CALMA_H = 190


def _lag_detectado(conn, firma_features, t0, id_nodo) -> Optional[float]:
    """El offset MÁS GRANDE (en horas) en que la firma todavía se reconocía.

    Es «el tiempo de vida de la firma»: cuánta anticipación dio ESTE patrón
    sobre ESTE evento. Dos etapas, y la primera es exactamente el barrido que
    había hasta el 2026-09-27:

      1. **Rejilla gruesa** `LAG_OFFSETS_H`, de más lejos a más cerca; el primer
         emparejamiento gana. Da el mismo resultado que antes.
      2. **Bisección** entre ese punto y el inmediatamente anterior --- el que NO
         emparejó --- hasta `LAG_RESOLUCION_H`.

    La bisección NO se aplica sobre todo el rango, y es deliberado: eso asumiría
    que la similitud es monótona en el tiempo, y **eso no está medido**. Una firma
    puede emparejar a 100 h, no a 80 y otra vez a 60; un barrido binario global se
    saltaría el inicio real. Acotar primero con la rejilla confina la suposición
    al interior de UN tramo, que es donde está la transición, y si el refinamiento
    no encuentra nada se devuelve el punto grueso: **nunca peor que antes**.

    Coste: <=6 sondeos de la rejilla + ~7 de bisección sobre un tramo de 96 h =
    ~13, contra los <=6 de antes. Resolución 48 veces más fina por ~2x el coste,
    en vez de las 336 evaluaciones de un barrido horario completo.
    """
    from datetime import timedelta as _td2

    def empareja(offset_h: int) -> bool:
        ts = (t0 - _td2(hours=offset_h)).strftime("%Y-%m-%d %H:%M")
        f = extraer_features_ventana(conn, ts, id_nodo)
        if f is None:
            return False
        return similitud(f, firma_features) >= SIMILARITY_ALERT

    bruto = None
    sin_emparejar = None        # el offset MAYOR que no emparejó
    for offset_h in LAG_OFFSETS_H:
        if empareja(offset_h):
            bruto = offset_h
            break
        sin_emparejar = offset_h
    if bruto is None:
        return None
    if sin_emparejar is None:
        # Emparejó ya en el punto más lejano de la rejilla: el inicio real puede
        # estar aún antes, pero fuera de la ventana de la firma. No se extrapola.
        return float(bruto)

    lo, hi = bruto, sin_emparejar          # empareja(lo) y no empareja(hi)
    while hi - lo > LAG_RESOLUCION_H:
        mid = (lo + hi) // 2
        if mid <= lo or mid >= hi:
            break
        if empareja(mid):
            lo = mid
        else:
            hi = mid
    return float(lo)


def calcular_lags_anticipacion(db_path: str) -> Dict:
    """Anticipación aprendida: cuánto avisa cada firma, en horas.

    Para cada firma consolidada se reprueba cada uno de sus eventos con la
    ventana desplazada atrás en el tiempo. Si la firma ya emparejaba 7 días
    antes del evento, el sistema tuvo ~7 días de aviso. Se persiste por firma en
    `TBL_FIRMAS.lag_promedio_h` / `lag_n` y agregado por clase en
    `tbl_lag_anticipacion`.

    El objetivo, que es lo que lo hace útil en vivo: si una firma viva es
    idéntica a una que ya se vio en el pasado, **trae su propio tiempo de vida**
    en vez del promedio de su clase --- y entonces el aviso puede decir «restan
    ~N h» con un número que significa algo.

    Cambiado el 2026-09-27, a pedido del operador:

      * **Los nueve bots, no solo `padre`.** Había un filtro fijo
        `if f["bot_name"] == "padre"`, y por eso solo 182 de 19.578 firmas
        tenían lag --- las 182 de padre. Ninguna firma de alfa1, beta1 ni el
        resto podía decir cuánto anticipa.
      * **Resolución de 1 h en vez de 48–96 h**, por bisección dentro del tramo
        acotado (ver `_lag_detectado`).
      * **El tope de muestra es por BOT Y CLASE.** Con el tope por clase, quitar
        el filtro no habría servido: padre tiene el 73 % de las firmas y se
        habría llevado el presupuesto entero.

    Nota sobre `tbl_lag_anticipacion`: su agregado por clase ahora mezcla los
    nueve bots, no solo padre, así que responde «cuánto avisa esta clase de
    evento» en vez de «cuánto avisa el padre». Es lo que el digest de Telegram
    imprime como `SISMO_M4: ~152h`.
    """
    import bisect as _bisect
    import random as _random
    from datetime import datetime as _dt, timedelta as _td
    from sentinel_omega.core.firmas.signature_engine import similitud

    conn = conexion_de_lote(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_lag_anticipacion ("
        "event_class TEXT PRIMARY KEY, lag_promedio_h REAL, lag_max_h REAL, "
        "lag_min_h REAL, n_eventos INTEGER, "
        "updated_at TEXT DEFAULT (datetime('now')))"
    )

    memoria = FirmaMemoria(conn)
    consolidadas = list(memoria.consolidadas())

    lags_por_clase: Dict[str, List[float]] = {}
    # La clave del tope es (bot, clase), no la clase: ver LAG_MUESTRA_POR_CLASE.
    evaluados: Dict[tuple, int] = {}
    lags_por_bot: Dict[str, int] = {}

    saltadas: Dict[tuple, int] = {}
    sin_anticipacion = 0
    sin_eventos = 0
    no_especificas = 0     # tienen lag, pero también emparejan en calma

    # `lag_n` nace en 0 por esquema (`lag_n INTEGER DEFAULT 0`; al hallarlo,
    # 39.094 de 40.695 filas lo tenían sin medición ninguna --- el conteo baja
    # a medida que se miden, pero el DEFAULT no cambia y es lo que importa),
    # así que escribir un 0 NO distingue «la medí y este patrón no
    # se ve antes del evento» de «nunca la medí». Hace falta una marca propia:
    # migración forward-only (regla 5), igual que las columnas de
    # discriminación.
    try:
        _cols = {r[1] for r in conn.execute("PRAGMA table_info(TBL_FIRMAS)")}
        if _cols:
            for _nom, _tipo in (("lag_medido_at", "TEXT"),
                                ("lag_calma_h", "REAL"),
                                ("lag_calma_n", "INTEGER")):
                if _nom not in _cols:
                    conn.execute(
                        f"ALTER TABLE TBL_FIRMAS ADD COLUMN {_nom} {_tipo}")
                    logger.info("TBL_FIRMAS: columna %s añadida", _nom)
            conn.commit()
    except sqlite3.Error as exc:
        logger.warning("no se pudieron asegurar las columnas de lag: %s", exc)

    # ─── El MODELO NULO del lag ──────────────────────────────────────────────
    #
    # Hasta el 2026-10-08 este barrido solo iba hacia atrás DESDE EVENTOS, así
    # que medía «cuánto tiempo atrás se sigue reconociendo el patrón» y lo
    # llamaba anticipación. Medido a mano ese día sobre 120 firmas exigibles:
    #
    #     antes de evento   media 219 h   mediana 228 h
    #     antes de CALMA    media 242 h   mediana 273 h   <- MÁS LARGO
    #
    # O sea que, condicionado a que empareje, el patrón vive igual o más en
    # calma. La mitad buena: el **69,2 %** de las firmas exigibles no empareja
    # en NINGUNA ventana de calma (con dato presente en las 120, cero
    # artefacto), y para esas el lag sí es tiempo de aviso.
    #
    # Así que el lag no es un número, son dos: el del evento y el del nulo. Se
    # sondea la misma firma en ventanas de calma de SUS PROPIOS NODOS --- mismo
    # nodo, para que la disponibilidad de dato sea comparable y la diferencia no
    # sea un artefacto de cobertura.
    eventos_por_nodo: Dict[int, List[str]] = {}
    for _ts, _nd in conn.execute(
            "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
            "WHERE sismo_max_mag >= ? ORDER BY timestamp_blk",
            (MIN_MAGNITUD_FIRMA,)):
        eventos_por_nodo.setdefault(int(_nd), []).append(str(_ts))
    horas_clima = [r[0] for r in conn.execute(
        "SELECT timestamp_blk FROM tbl_clima_espacial_raw ORDER BY timestamp_blk")]
    _rng_calma = _random.Random(LAG_SEMILLA_CALMA)

    def _t0_calma(id_nodo: int) -> Optional["_dt"]:
        """Una hora de ese nodo SIN evento en el horizonte siguiente."""
        if not horas_clima:
            return None
        lista = eventos_por_nodo.get(id_nodo)
        for _ in range(60):
            ts = horas_clima[_rng_calma.randrange(len(horas_clima))]
            try:
                t = _dt.strptime(str(ts)[:16], "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            if lista:
                i = _bisect.bisect_right(lista, str(ts))
                if i < len(lista):
                    tope = (t + _td(hours=LAG_HORIZONTE_CALMA_H)
                            ).strftime("%Y-%m-%d %H:%M")
                    if lista[i] <= tope:
                        continue          # hubo evento: no es calma
            return t
        return None

    for firma in consolidadas:
        clase = firma["event_class"]
        bot = firma["bot_name"]
        cupo = (bot, clase)
        if evaluados.get(cupo, 0) >= LAG_MUESTRA_POR_CLASE:
            # Regla dura 10: el `continue` que descarta trabajo lleva cuenta.
            # Sin esto, 367 de 417 firmas de beta1/SISMO_M4 se saltaban en
            # silencio y el resultado parecía «estas firmas no anticipan».
            saltadas[cupo] = saltadas.get(cupo, 0) + 1
            continue
        # Muestra de 3 eventos desde la tabla hija (no cargamos el array entero).
        eventos = [
            r[0] for r in conn.execute(
                "SELECT evento_ref FROM tbl_firma_eventos "
                "WHERE firma_id = ? ORDER BY orden LIMIT 3",
                (firma["firma_id"],),
            )
        ]

        if not eventos:
            sin_eventos += 1
            continue

        # El presupuesto se gasta POR FIRMA, no por evento sondeado: una firma
        # con tres eventos no vale el triple que una con uno.
        evaluados[cupo] = evaluados.get(cupo, 0) + 1

        lags_firma: List[float] = []
        nodos_firma: List[int] = []
        for ref in eventos:  # muestra por firma (ya viene limitada a 3)
            try:
                ts_evento, nodo_part, _ = ref.split("|")
                id_nodo = int(nodo_part.replace("nodo", ""))
                t0 = _dt.strptime(ts_evento, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            nodos_firma.append(id_nodo)

            lag_detectado = _lag_detectado(conn, firma["features"], t0, id_nodo)
            if lag_detectado is not None:
                lags_firma.append(lag_detectado)

        # El NULO: la misma firma sondeada en ventanas de calma de sus propios
        # nodos. Si no empareja en ninguna, el lag del evento es tiempo de
        # aviso; si empareja con vida igual o mayor, el número mide persistencia
        # del patrón y NO anticipa nada.
        lags_calma: List[float] = []
        for id_nodo in (nodos_firma or [])[:LAG_MUESTRA_CALMA]:
            t_cal = _t0_calma(id_nodo)
            if t_cal is None:
                continue
            l_cal = _lag_detectado(conn, firma["features"], t_cal, id_nodo)
            if l_cal is not None:
                lags_calma.append(l_cal)

        # El agregado por clase solo admite firmas ESPECÍFICAS: si entraran las
        # que también emparejan en calma, el promedio de clase ---que es el
        # respaldo del aviso--- quedaría contaminado con patrones que no avisan.
        if lags_firma and not lags_calma:
            for v in lags_firma:
                lags_por_clase.setdefault(clase, []).append(v)
            lags_por_bot[bot] = lags_por_bot.get(bot, 0) + len(lags_firma)
        elif lags_firma:
            no_especificas += 1

        # Per-signature lead time: THIS firma's own typical window
        if lags_firma:
            conn.execute(
                "UPDATE TBL_FIRMAS SET lag_promedio_h = ?, lag_n = ?, "
                "lag_calma_h = ?, lag_calma_n = ?, "
                "lag_medido_at = datetime('now') WHERE firma_id = ?",
                (sum(lags_firma) / len(lags_firma), len(lags_firma),
                 (sum(lags_calma) / len(lags_calma)) if lags_calma else None,
                 len(lags_calma),
                 firma["firma_id"]),
            )
        else:
            # MEDIDA Y SIN ANTICIPACIÓN no es lo mismo que SIN MEDIR (regla
            # dura 10). La marca va en `lag_medido_at`, no en `lag_n`, porque
            # `lag_n` ya vale 0 en toda la tabla por defecto de esquema.
            sin_anticipacion += 1
            conn.execute(
                "UPDATE TBL_FIRMAS SET lag_promedio_h = NULL, lag_n = 0, "
                "lag_calma_h = ?, lag_calma_n = ?, "
                "lag_medido_at = datetime('now') WHERE firma_id = ?",
                ((sum(lags_calma) / len(lags_calma)) if lags_calma else None,
                 len(lags_calma), firma["firma_id"]))

    resultado = {}
    for clase, lags in lags_por_clase.items():
        prom = sum(lags) / len(lags)
        conn.execute(
            "INSERT OR REPLACE INTO tbl_lag_anticipacion "
            "(event_class, lag_promedio_h, lag_max_h, lag_min_h, n_eventos, "
            " updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (clase, prom, max(lags), min(lags), len(lags)),
        )
        resultado[clase] = {
            "lag_promedio_dias": round(prom / 24, 1),
            "lag_max_dias": round(max(lags) / 24, 1),
            "n": len(lags),
        }
    conn.commit()
    conn.close()
    logger.info(f"Lags de anticipación: {resultado}")
    # Por bot, para que se vea si algún bot quedó sin medir. Antes este número
    # era «padre: todo, el resto: nada» y no había forma de notarlo desde el log.
    logger.info("Lags por bot (firmas con anticipación medida): %s",
                dict(sorted(lags_por_bot.items(), key=lambda kv: -kv[1])) or "NINGUNO")
    # Las tres cuentas que faltaban. Sin ellas, «esta firma no tiene lag» podía
    # significar tres cosas distintas y no había forma de saber cuál.
    logger.info(
        "Cobertura del lag: %d firmas evaluadas · %d medidas y SIN "
        "anticipación (lag_n=0) · %d sin eventos hijos · %d SALTADAS por tope",
        sum(evaluados.values()), sin_anticipacion, sin_eventos,
        sum(saltadas.values()))
    # El nulo, que es lo que separa anticipar de persistir.
    especificas = sum(evaluados.values()) - sin_anticipacion - no_especificas
    logger.info(
        "Nulo del lag: %d firmas con lag ESPECÍFICO (no emparejan en calma) · "
        "%d con lag pero TAMBIÉN en calma --- su número mide persistencia, no "
        "anticipación, y queda FUERA del promedio por clase · %d sondeos de "
        "evento alimentan ese promedio",
        especificas, no_especificas,
        sum(len(v) for v in lags_por_clase.values()))
    if saltadas:
        logger.warning(
            "El tope de %d firmas por (bot,clase) MORDIÓ y dejó firmas sin "
            "medir: %s. Esas firmas alertan sin poder decir cuánto anticipan; "
            "sube LAG_MUESTRA_POR_CLASE.", LAG_MUESTRA_POR_CLASE,
            dict(sorted(saltadas.items(), key=lambda kv: -kv[1])[:8]))

    factores = analizar_factores_lag(db_path)
    resultado["factores"] = factores
    return resultado


def analizar_factores_lag(db_path: str) -> Dict:
    """What do slow-warning firmas share vs fast-warning ones?

    Splits per-firma lags into terciles (rápidas = shortest lead, lentas =
    longest lead) and compares each feature's mean between groups. The top
    differentiating factors reveal WHY some events announce themselves
    earlier — persisted to tbl_factores_lag for the report and, in time,
    for predicting a match's expected delay from its own features.
    """
    conn = conexion_de_lote(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_factores_lag ("
        "feature TEXT PRIMARY KEY, media_rapidas REAL, media_lentas REAL, "
        "diferencia_norm REAL, updated_at TEXT DEFAULT (datetime('now')))"
    )

    rows = conn.execute(
        "SELECT features_json, lag_promedio_h FROM TBL_FIRMAS "
        "WHERE bot_name = 'padre' AND estado = 'consolidada' "
        "AND lag_promedio_h IS NOT NULL ORDER BY lag_promedio_h"
    ).fetchall()
    if len(rows) < 9:  # need enough firmas for terciles to mean anything
        conn.close()
        return {}

    tercio = len(rows) // 3
    rapidas = [json.loads(r[0]) for r in rows[:tercio]]
    lentas = [json.loads(r[0]) for r in rows[-tercio:]]

    def _media(grupo: List[Dict], key: str) -> Optional[float]:
        vals = [g[key] for g in grupo if key in g]
        return sum(vals) / len(vals) if len(vals) >= max(3, len(grupo) // 3) else None

    factores = []
    for key in FEATURE_KEYS:
        mr, ml = _media(rapidas, key), _media(lentas, key)
        if mr is None or ml is None:
            continue
        escala = (abs(mr) + abs(ml)) / 2
        if escala < 1e-9:
            continue
        diff = (ml - mr) / escala  # >0: higher in slow-warning firmas
        factores.append((key, mr, ml, diff))

    factores.sort(key=lambda f: -abs(f[3]))
    for key, mr, ml, diff in factores:
        conn.execute(
            "INSERT OR REPLACE INTO tbl_factores_lag "
            "(feature, media_rapidas, media_lentas, diferencia_norm, "
            " updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (key, mr, ml, diff),
        )
    conn.commit()

    lag_stats = conn.execute(
        "SELECT MIN(lag_promedio_h), AVG(lag_promedio_h), MAX(lag_promedio_h), "
        "COUNT(*) FROM TBL_FIRMAS WHERE bot_name='padre' "
        "AND lag_promedio_h IS NOT NULL"
    ).fetchone()
    conn.close()

    top = {
        f[0]: {"rapidas": round(f[1], 2), "lentas": round(f[2], 2),
               "dif": round(f[3], 2)}
        for f in factores[:6]
    }
    logger.info(f"Factores de lag (top): {top}")
    return {
        "firmas_con_lag": lag_stats[3],
        "lag_dias": {
            "min": round(lag_stats[0] / 24, 1),
            "prom": round(lag_stats[1] / 24, 1),
            "max": round(lag_stats[2] / 24, 1),
        },
        "top_factores": top,
    }


def entrenar_reconocimiento_no_sismico(
    db_path: str,
    max_eventos: Optional[int] = None,
    bots: Optional[List[str]] = None,
) -> Dict:
    """Fase 1b — learn signatures from non-seismic natural events.

    Trains on volcanic eruptions (VEI≥3, from tbl_desgasificacion_raw) and
    solar storm onsets (Kp≥6, from tbl_clima_espacial_raw). Both are derived
    from existing backcast tables via derivar_eventos_no_sismicos() and stored
    in tbl_eventos_no_sismicos before the training loop runs.

    Uses the same feature extraction and firma registration as Fase 1 —
    the same 14-day pre-event window — so bots learn what precedes eruptions
    and solar storms, not just earthquakes.

    The Padre's full-vector signatures will now capture financial (Delta) and
    atmospheric (Beta-2) patterns that precede these events too, enabling
    the correlation heatmap to reveal cross-domain relationships.
    """
    conn = conexion_de_lote(db_path)

    # Derive if table is absent or empty
    n_previos = 0
    if _table_exists(conn, "tbl_eventos_no_sismicos"):
        n_previos = conn.execute(
            "SELECT COUNT(*) FROM tbl_eventos_no_sismicos"
        ).fetchone()[0]
    if n_previos == 0:
        derivar_eventos_no_sismicos(conn)

    eventos = conn.execute(
        "SELECT timestamp_blk, id_nodo, event_class, intensidad "
        "FROM tbl_eventos_no_sismicos ORDER BY timestamp_blk"
    ).fetchall()
    if max_eventos:
        eventos = eventos[:max_eventos]

    memoria = FirmaMemoria(conn)
    bots_activos = {
        b: k for b, k in BOT_FEATURES.items() if bots is None or b in bots
    }
    _auditar_features_declaradas(bots_activos)

    logger.info(
        f"=== FASE 1b RECONOCIMIENTO NO SÍSMICO: {len(eventos)} eventos ==="
    )
    stats = {"eventos": len(eventos), "firmas_nuevas": 0, "recurrencias": 0,
             "sin_datos": 0}

    for idx, (ts_evento, id_nodo, event_class, intensidad) in enumerate(eventos):
        if idx % 500 == 0 and idx > 0:
            logger.info(
                f"  Fase 1b progreso: {idx}/{len(eventos)} "
                f"({stats['firmas_nuevas']} firmas, "
                f"{stats['recurrencias']} recurrencias)"
            )
        features = extraer_features_ventana(conn, ts_evento, id_nodo)
        if features is None:
            stats["sin_datos"] += 1
            continue

        evento_ref = f"{ts_evento}|nodo{id_nodo}|{event_class}:{intensidad:.1f}"

        for bot, keys in bots_activos.items():
            if bot in BOTS_LIVE_ONLY:
                continue
            desde = BOT_DESDE.get(bot)
            if desde and ts_evento < desde:
                continue
            sub = (
                features if keys is None
                else {k: v for k, v in features.items() if k in keys}
            )
            if len(sub) < MIN_FEATURES_POR_BOT[bot]:
                continue
            _, _, es_nueva = memoria.registrar(
                bot, event_class, id_nodo, sub, evento_ref, ts_evento
            )
            if es_nueva:
                stats["firmas_nuevas"] += 1
            else:
                stats["recurrencias"] += 1

    stats["memoria"] = memoria.stats()
    logger.info(f"Fase 1b completa: {stats}")
    conn.close()
    return stats


def calcular_correlaciones_evento(db_path: str) -> Dict:
    """Compute feature × event_class correlation matrix from TBL_FIRMAS.

    For every (event_class, feature) pair, computes the mean feature value
    across all firmas of that class and normalises by the global mean across
    ALL classes. A ratio > 1 means the feature tends to be elevated in the
    14-day window before that event type; a ratio < 1 means it is suppressed.

    The resulting matrix is stored in tbl_patrones_correlacion and is used by
    the report generator to render the correlation heatmap. Re-running is safe
    (INSERT OR REPLACE).
    """
    conn = conexion_de_lote(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_patrones_correlacion "
        "(event_class TEXT NOT NULL, feature TEXT NOT NULL, "
        " media REAL DEFAULT 0.0, global_media REAL DEFAULT 0.0, "
        " ratio REAL DEFAULT 1.0, n_firmas INTEGER DEFAULT 0, "
        " updated_at TEXT DEFAULT (datetime('now')), "
        " PRIMARY KEY (event_class, feature))"
    )

    rows = conn.execute(
        "SELECT event_class, features_json FROM TBL_FIRMAS"
    ).fetchall()

    # Aggregate per (event_class, feature) and globally
    class_feat: Dict[str, Dict[str, list]] = {}
    global_feat: Dict[str, list] = {k: [] for k in FEATURE_KEYS}

    for event_class, features_json in rows:
        try:
            feats = json.loads(features_json)
        except Exception:
            continue
        cf = class_feat.setdefault(event_class, {k: [] for k in FEATURE_KEYS})
        for feat in FEATURE_KEYS:
            v = feats.get(feat)
            if v is None or math.isnan(float(v)) if isinstance(v, (int, float)) else True:
                continue
            cf[feat].append(float(v))
            global_feat[feat].append(float(v))

    global_means = {
        feat: sum(vals) / len(vals)
        for feat, vals in global_feat.items() if vals
    }

    resultado: Dict[str, Dict[str, float]] = {}
    for event_class, feat_lists in class_feat.items():
        resultado[event_class] = {}
        for feat, vals in feat_lists.items():
            if not vals:
                continue
            media = sum(vals) / len(vals)
            gm = global_means.get(feat, 0.0)
            ratio = media / gm if abs(gm) > 1e-9 else 1.0
            conn.execute(
                "INSERT OR REPLACE INTO tbl_patrones_correlacion "
                "(event_class, feature, media, global_media, ratio, "
                " n_firmas, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (event_class, feat, round(media, 4), round(gm, 4),
                 round(ratio, 3), len(vals)),
            )
            resultado[event_class][feat] = round(ratio, 3)

    conn.commit()
    conn.close()
    n_classes = len(resultado)
    n_pairs = sum(len(v) for v in resultado.values())
    logger.info(
        f"Correlaciones calculadas: {n_classes} event classes, {n_pairs} pares"
    )
    return resultado


# ── Disciplina de trasfondo — "castigo desde abajo" ──────────────────────────
# Las firmas permanentes se guardan desde la prediccion (M4.5). La alerta sale desde M6.
# Pero para que no se duerman con los precursores chiquitos, se les disciplina
# cada cierto tiempo contra sismos MENORES (M3.3–4.49) de un bloque reciente de
# años. Esas firmas viven en una tabla TEMPORAL que se poda por edad — solo
# sobreviven los PESOS neuronales. El ajuste de peso por corrida está ACOTADO
# para no cráterizar la credibilidad de un bot de un golpe.
MAG_MENOR_MIN = 3.3   # este fetch no baja a 2.5: esa bajada no entra en este diff
MAG_MENOR_MAX = MIN_MAGNITUD_FIRMA          # 4.5, por debajo de la prediccion
DISCIPLINA_MAX_EVENTOS = 300                # muestreo acotado por corrida
DISCIPLINA_RETENCION_DIAS = 90             # poda rolling de la tabla temporal
DISCIPLINA_MAX_AJUSTES = 3                  # pasos de peso por bot por corrida


def _fetch_sismos_menores(anio: int, mag_min: float, mag_max: float,
                          max_results: int = 20000) -> List[tuple]:
    """USGS por rango de fecha+magnitud (bloque histórico, no ventana viva)."""
    import requests
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": f"{anio}-01-01",
        "endtime": f"{anio}-12-31T23:59:59",
        "minmagnitude": mag_min,
        "maxmagnitude": mag_max,
        "limit": max_results,
        "orderby": "time",
    }
    try:
        r = requests.get(url, params=params, timeout=90)
        r.raise_for_status()
        out = []
        for f in r.json().get("features", []):
            props = f.get("properties", {})
            coords = (f.get("geometry") or {}).get("coordinates", [None, None, None])
            mag, lon, lat, t = props.get("mag"), coords[0], coords[1], props.get("time")
            if mag is None or lat is None or lon is None or t is None:
                continue
            ts = datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d %H:%M")
            out.append((ts, lat, lon, float(mag)))
        return out
    except Exception as e:
        logger.warning(f"Disciplina de trasfondo: fetch USGS falló: {e}")
        return []


def disciplina_trasfondo(db_path: str, anio: Optional[int] = None,
                         max_eventos: int = DISCIPLINA_MAX_EVENTOS,
                         dry_run: bool = False) -> Dict:
    """Castigo desde abajo — disciplina rolling contra sismos menores.

    No toca la memoria permanente (TBL_FIRMAS): las firmas menores van a
    tbl_firmas_menores (temporal, podada por edad). Solo persisten los pesos.

    El Juez registra un ACIERTO o FALLO por cada par bot × evento evaluado,
    para que su historial refleje también la vigilancia de precursores pequeños.
    Esos registros llevan fase="trasfondo" y NO se podan al terminar —
    son parte del historial de patrones del Juez.

    Con dry_run=True evalúa y reporta los castigos/refuerzos que APLICARÍA,
    pero no escribe nada: ni la tabla temporal, ni los registros del Juez,
    ni los pesos.
    """
    from sentinel_omega.core.juez.pesos import castigar, reforzar
    from sentinel_omega.core.shared.geometria_uvg import nodo_mas_cercano

    import time as _time

    conn = conexion_de_lote(db_path)
    juez = Juez(conn)
    if not dry_run:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tbl_firmas_menores ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, event_class TEXT, "
            "id_nodo INTEGER, mag REAL, features_json TEXT, ts_evento TEXT, "
            "creada_at TEXT DEFAULT (datetime('now')))"
        )
        # Poda rolling: fuera las firmas menores más viejas que la retención.
        conn.execute(
            "DELETE FROM tbl_firmas_menores WHERE creada_at < datetime('now', ?)",
            (f"-{DISCIPLINA_RETENCION_DIAS} days",),
        )
        conn.commit()

    # Bloque reciente = último año con contexto en el backcast.
    if anio is None:
        maxblk = conn.execute(
            "SELECT MAX(timestamp_blk) FROM tbl_clima_espacial_raw"
        ).fetchone()[0]
        anio = int(maxblk[:4]) if maxblk else datetime.utcnow().year - 1

    eventos = _fetch_sismos_menores(anio, MAG_MENOR_MIN, MAG_MENOR_MAX)
    if not eventos:
        conn.close()
        return {"anio": anio, "eventos": 0, "nota": "sin datos de sismos menores"}
    if len(eventos) > max_eventos:                 # muestreo uniforme
        paso = len(eventos) / max_eventos
        eventos = [eventos[int(i * paso)] for i in range(max_eventos)]

    memoria = FirmaMemoria(conn)
    consolidadas = {b: memoria.consolidadas(b) for b in BOT_FEATURES}
    conteo = {b: {"evaluadas": 0, "reconocidas": 0} for b in BOT_FEATURES}

    for ts, lat, lon, mag in eventos:
        nodo = nodo_mas_cercano(lat, lon)["id"]
        feats = extraer_features_ventana(conn, ts, nodo)
        if feats is None:
            continue
        clase = f"SISMO_M{int(mag)}"               # M2 / M3 / M4 (menores)
        evento_ref = f"{ts}|nodo{nodo}|M{mag:.1f}"
        bots_acierto: List[str] = []
        bots_fallo: List[str] = []

        for bot, keys in BOT_FEATURES.items():
            # alfa2 no tiene backcast → sus firmas consolidadas estarán vacías
            # durante el entrenamiento inicial; saltarlo evita falsos cero.
            if bot in BOTS_LIVE_ONLY:
                continue
            firmas_bot = consolidadas.get(bot) or []
            if not firmas_bot:
                continue
            sub = feats if keys is None else {k: feats[k] for k in keys if k in feats}
            if not sub:
                continue
            # Reconocimiento ESPACIAL: ¿la memoria del bot PARA ESE NODO
            # anticipó el chiquito ahí? Sin firma en el nodo = ceguera local.
            firmas_nodo = [f for f in firmas_bot if f["id_nodo"] == nodo]
            best = max((similitud(sub, f["features"]) for f in firmas_nodo),
                       default=0.0)
            conteo[bot]["evaluadas"] += 1
            if best >= SIMILARITY_ALERT:
                conteo[bot]["reconocidas"] += 1
                bots_acierto.append(bot)
            else:
                bots_fallo.append(bot)
            if not dry_run:
                conn.execute(
                    "INSERT INTO tbl_firmas_menores "
                    "(bot_name, event_class, id_nodo, mag, features_json, ts_evento) "
                    "VALUES (?,?,?,?,?,?)",
                    (bot, clase, nodo, mag, json.dumps(sub), ts),
                )

        # Juez: log per-bot verdict for this minor event.
        if not dry_run:
            now = _time.time()
            for bot in bots_acierto:
                juez.registrar_prediccion(
                    bot_name=bot, prediccion="alert", confianza=1.0,
                    ventana_h=0,
                    detalles={"fase": "trasfondo", "clase": clase,
                              "evento": evento_ref, "mag": round(float(mag), 1)},
                    timestamp=now,
                )
            for bot in bots_fallo:
                juez.registrar_prediccion(
                    bot_name=bot, prediccion="no_signal", confianza=0.0,
                    ventana_h=0,
                    detalles={"fase": "trasfondo", "clase": clase,
                              "evento": evento_ref, "mag": round(float(mag), 1)},
                    timestamp=now,
                )
            if bots_acierto or bots_fallo:
                juez.evaluar_pendientes(
                    evento_ocurrido=True,
                    verdad=evento_ref,
                    firma_conocida=False,  # minor events are never enforceable
                    fase="trasfondo",
                )

    # Ajuste de pesos ACOTADO por bot: más ceguera a los chiquitos → más castigo
    # (hasta DISCIPLINA_MAX_AJUSTES pasos), el resto se convierte en refuerzo.
    ajustes = {}
    for bot, c in conteo.items():
        if c["evaluadas"] == 0:
            continue
        tasa = c["reconocidas"] / c["evaluadas"]
        n_castigos = min(DISCIPLINA_MAX_AJUSTES,
                         round((1.0 - tasa) * DISCIPLINA_MAX_AJUSTES))
        n_refuerzos = DISCIPLINA_MAX_AJUSTES - n_castigos
        es_padre = bot == "padre"
        if not dry_run:
            for _ in range(n_castigos):
                castigar(conn, bot, es_padre=es_padre, gravedad=1.0)
            for _ in range(n_refuerzos):
                reforzar(conn, bot)
        ajustes[bot] = {"reconocimiento": round(tasa, 3),
                        "castigos": n_castigos, "refuerzos": n_refuerzos}
    if not dry_run:
        conn.commit()
    conn.close()
    logger.info(
        f"Disciplina de trasfondo ({anio}, M{MAG_MENOR_MIN}-{MAG_MENOR_MAX}, "
        f"{len(eventos)} eventos, dry_run={int(dry_run)}): {ajustes}"
    )
    return {"anio": anio, "eventos": len(eventos), "ajustes": ajustes,
            "dry_run": dry_run}
