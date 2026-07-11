"""
Mantenimiento — barrido diario del historial operativo.

Los ciclos escriben todo el día en las tablas operativas (cada ~2h). Una vez
al día, el barrido se queda con lo SIGNIFICANTE y bota el bulto:

  - Resumen del día  -> tbl_resumen_diario (una fila por día: fantasma máx/
    media, breaches, alertas, señal dominante).
  - Ciclos: se conservan los significativos (HIGH/CRITICAL o con breach); los
    ciclos de calma anteriores a la ventana de retención se botan (su esencia
    ya quedó en el resumen).
  - Detecciones: se colapsan a una por (día, tipo, muro) con la confianza más
    alta — las mismas detecciones repetidas cada ciclo dejan de acumularse.

Mismo principio que las referencias legacy: aprender/registrar la esencia,
soltar el crudo. Se corre 1×/día (lo dispara el vigilante).
"""

import logging
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict

logger = logging.getLogger(__name__)

DIAS_RETENCION_FULL = 7  # días recientes que se conservan a resolución de ciclo


def _dia_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def barrido_diario(db_path: str, dias_full: int = DIAS_RETENCION_FULL) -> Dict:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_resumen_diario ("
        "dia TEXT PRIMARY KEY, n_ciclos INTEGER, fantasma_max REAL, "
        "fantasma_media REAL, nivel_max TEXT, breaches INTEGER, alertas INTEGER, "
        "senal_dominante TEXT, creada_at TEXT DEFAULT (datetime('now')))"
    )

    hoy = datetime.now(timezone.utc).date()
    corte = hoy - timedelta(days=dias_full)
    corte_ts = datetime(
        corte.year, corte.month, corte.day, tzinfo=timezone.utc
    ).timestamp()
    hoy_ts = datetime(hoy.year, hoy.month, hoy.day, tzinfo=timezone.utc).timestamp()

    NIVEL_ORD = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
    stats = {"dias_resumidos": 0, "ciclos_botados": 0, "detecciones_colapsadas": 0}

    # ── 1) Resumen de días anteriores al corte, aún no resumidos ──
    ya = {r[0] for r in conn.execute("SELECT dia FROM tbl_resumen_diario")}
    por_dia: Dict[str, list] = {}
    for row in conn.execute(
        "SELECT timestamp, fantasma, nivel_riesgo, muro_breach, geo_signal "
        "FROM TBL_CICLOS WHERE timestamp < ?", (corte_ts,)
    ):
        d = _dia_utc(row[0])
        if d not in ya:
            por_dia.setdefault(d, []).append(row)

    for dia, filas in por_dia.items():
        fant = [f[1] for f in filas if f[1] is not None]
        niveles = [f[2] for f in filas if f[2]]
        senales = [f[4] for f in filas if f[4]]
        conn.execute(
            "INSERT OR REPLACE INTO tbl_resumen_diario "
            "(dia, n_ciclos, fantasma_max, fantasma_media, nivel_max, breaches, "
            " alertas, senal_dominante) VALUES (?,?,?,?,?,?,?,?)",
            (dia, len(filas), round(max(fant), 2) if fant else None,
             round(sum(fant) / len(fant), 2) if fant else None,
             max(niveles, key=lambda n: NIVEL_ORD.get(n, 0)) if niveles else None,
             sum(1 for f in filas if f[3]),
             sum(1 for s in senales if s == "alert"),
             Counter(senales).most_common(1)[0][0] if senales else None),
        )
        stats["dias_resumidos"] += 1

    # ── 2) Botar ciclos de calma anteriores al corte ──
    stats["ciclos_botados"] = conn.execute(
        "DELETE FROM TBL_CICLOS WHERE timestamp < ? "
        "AND muro_breach = 0 AND nivel_riesgo NOT IN ('HIGH','CRITICAL')",
        (corte_ts,),
    ).rowcount
    conn.execute(
        "DELETE FROM TBL_PRECURSORES_COSMICOS WHERE timestamp < ? AND fantasma < 15",
        (corte_ts,),
    )

    # ── 3) Colapsar detecciones repetidas de días ya cerrados ──
    dets = conn.execute(
        "SELECT id, timestamp, tipo, wall_name, confidence "
        "FROM TBL_DETECCIONES WHERE timestamp < ?", (hoy_ts,)
    ).fetchall()
    mejor: Dict[tuple, tuple] = {}
    for did, ts, tipo, muro, conf in dets:
        clave = (_dia_utc(ts), tipo, muro)
        if clave not in mejor or (conf or 0) > (mejor[clave][1] or 0):
            mejor[clave] = (did, conf)
    conservar = {v[0] for v in mejor.values()}
    a_botar = [d[0] for d in dets if d[0] not in conservar]
    if a_botar:
        conn.executemany(
            "DELETE FROM TBL_DETECCIONES WHERE id = ?", [(i,) for i in a_botar]
        )
        stats["detecciones_colapsadas"] = len(a_botar)

    conn.commit()
    conn.close()

    # Correlaciones del Padre y Omega, sesgo de todos los bots
    stats["correlaciones_padre"] = construir_correlaciones_padre(db_path)
    stats["correlaciones_omega"] = construir_correlaciones_omega(db_path)
    stats["sesgo_aprendizaje"] = evaluar_sesgo_aprendizaje(db_path)

    # El Padre también ve el ORDEN en que se presentaron los precursores y
    # discierne si la secuencia importa o es indiferente (contando).
    stats["orden_precursores"] = analizar_orden_precursores(db_path)

    # Y la SECUENCIA DE NODOS: la ruta espacial por la que se propaga la
    # energía. Rutas globales (que preceden a distintos tipos) = cimática
    # organizada; locales = causas específicas.
    stats["secuencia_nodos"] = analizar_secuencia_nodos(db_path)

    # Poda cimática: la línea base es TODA la telemetría, pero el patrón
    # que tras su gracia nunca se asoció a un evento es ruido → se elimina.
    try:
        from sentinel_omega.core.firmas.cimatica import poda_cimatica
        conn_poda = sqlite3.connect(db_path)
        stats["cimatica_podados"] = poda_cimatica(conn_poda)
        conn_poda.close()
    except Exception as e:
        logger.warning(f"Poda cimática falló (non-blocking): {e}")

    logger.info(f"Barrido diario: {stats}")
    return stats


# ── Tabla de correlaciones del Padre ─────────────────────────────────────────

CORRELACION_MIN_N = 50


def _patron_padre(f: dict) -> str:
    """Discretiza el vector cruzado del Padre en qué DOMINIOS estaban activos."""
    flags = []
    kp = max(f.get("kp_max", 0) or 0, f.get("kp_max_72h", 0) or 0)
    bz = f.get("bz_min", 0) or 0
    prot = f.get("proton_max", 0) or 0
    if kp >= 4 or bz <= -8 or prot >= 100:
        flags.append("SOLAR")
    elif kp < 2 and abs(bz) < 3:
        flags.append("CALMA")
    if (f.get("sismo_count_win", 0) or 0) >= 3 or \
       (f.get("sismo_max_mag_win", 0) or 0) >= 4.5:
        flags.append("SISMICO")
    if (f.get("so2_kt_win", 0) or 0) > 0 or (f.get("erupciones_win", 0) or 0) > 0:
        flags.append("DESGAS")
    if (f.get("btc_volatilidad", 0) or 0) >= 5 or \
       (f.get("btc_vol_max", 0) or 0) >= 15:
        flags.append("FINANCIERO")
    return "+".join(flags) if flags else "DIFUSO"


def construir_correlaciones_padre(db_path: str, min_n: int = CORRELACION_MIN_N) -> Dict:
    """Colapsa las firmas del Padre en correlaciones patrón×clase con conteos.
    Solo se conservan correlaciones significativas (n >= min_n).
    """
    import json as _json

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_correlaciones_padre ("
        "patron TEXT, event_class TEXT, n INTEGER, fuerza REAL, "
        "actualizada_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (patron, event_class))"
    )

    conteo: Dict[tuple, int] = {}
    for feats_json, clase, rec in conn.execute(
        "SELECT features_json, event_class, recurrencia "
        "FROM TBL_FIRMAS WHERE bot_name = 'padre'"
    ):
        try:
            patron = _patron_padre(_json.loads(feats_json))
        except Exception:
            continue
        conteo[(patron, clase)] = conteo.get((patron, clase), 0) + (rec or 1)

    total = sum(conteo.values()) or 1
    conn.execute("DELETE FROM tbl_correlaciones_padre")
    filas = [
        (p, c, n, round(n / total, 4))
        for (p, c), n in conteo.items() if n >= min_n
    ]
    conn.executemany(
        "INSERT INTO tbl_correlaciones_padre (patron, event_class, n, fuerza) "
        "VALUES (?,?,?,?)", filas,
    )
    conn.commit()
    conn.close()
    stats = {"patrones_totales": len(conteo), "significativos": len(filas),
             "descartados": len(conteo) - len(filas)}
    logger.info(f"Correlaciones del Padre: {stats}")
    return stats


# ── Tabla de correlaciones de Omega ──────────────────────────────────────────
# Omega tiene su propia tabla de correlaciones, completamente independiente
# del Padre y de los otros bots. Esto permite evaluar su autonomía real.

CORRELACION_OMEGA_MIN_N = 30  # umbral más bajo: Omega es nuevo, necesita menos evidencia


def _patron_omega(f: dict) -> str:
    """
    Discretiza el vector de Omega en dominios activos.
    Omega observa el vector completo, igual que el Padre,
    pero su tabla de correlaciones es independiente.
    """
    flags = []
    kp = max(f.get("kp_max", 0) or 0, f.get("kp_max_72h", 0) or 0)
    bz = f.get("bz_min", 0) or 0
    prot = f.get("proton_max", 0) or 0
    sch = f.get("schumann_mean", 0) or 0
    if kp >= 4 or bz <= -8 or prot >= 100:
        flags.append("SOLAR")
    elif kp < 2 and abs(bz) < 3:
        flags.append("CALMA")
    if sch > 8.5:
        flags.append("SCHUMANN")  # resonancia Schumann elevada
    if (f.get("sismo_count_win", 0) or 0) >= 3 or \
       (f.get("sismo_max_mag_win", 0) or 0) >= 4.5:
        flags.append("SISMICO")
    if (f.get("so2_kt_win", 0) or 0) > 0 or (f.get("erupciones_win", 0) or 0) > 0:
        flags.append("DESGAS")
    if (f.get("btc_volatilidad", 0) or 0) >= 5:
        flags.append("FINANCIERO")
    fase = f.get("fase_lunar", -1) or -1
    if 0 <= fase <= 0.1 or fase >= 0.9:  # luna nueva
        flags.append("LUNA_NUEVA")
    elif 0.45 <= fase <= 0.55:           # luna llena
        flags.append("LUNA_LLENA")
    return "+".join(flags) if flags else "DIFUSO"


def construir_correlaciones_omega(db_path: str, min_n: int = CORRELACION_OMEGA_MIN_N) -> Dict:
    """
    Colapsa las firmas de Omega en su propia tabla de correlaciones.
    Es el equivalente de construir_correlaciones_padre pero SOLO para Omega.
    Se distingue por:
      - Umbral más bajo (min_n=30 vs 50 del Padre: Omega es nuevo).
      - Patrón incluye fase lunar y resonancia Schumann.
      - Tabla separada: tbl_correlaciones_omega.
    """
    import json as _json

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_correlaciones_omega ("
        "patron TEXT, event_class TEXT, n INTEGER, fuerza REAL, "
        "actualizada_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (patron, event_class))"
    )

    conteo: Dict[tuple, int] = {}
    for feats_json, clase, rec in conn.execute(
        "SELECT features_json, event_class, recurrencia "
        "FROM TBL_FIRMAS WHERE bot_name = 'omega'"
    ):
        try:
            patron = _patron_omega(_json.loads(feats_json))
        except Exception:
            continue
        conteo[(patron, clase)] = conteo.get((patron, clase), 0) + (rec or 1)

    total = sum(conteo.values()) or 1
    conn.execute("DELETE FROM tbl_correlaciones_omega")
    filas = [
        (p, c, n, round(n / total, 4))
        for (p, c), n in conteo.items() if n >= min_n
    ]
    conn.executemany(
        "INSERT INTO tbl_correlaciones_omega (patron, event_class, n, fuerza) "
        "VALUES (?,?,?,?)", filas,
    )
    conn.commit()
    conn.close()
    stats = {"patrones_totales": len(conteo), "significativos": len(filas),
             "descartados": len(conteo) - len(filas)}
    logger.info(f"Correlaciones de Omega: {stats}")
    return stats


# ── Sesgo de aprendizaje ──────────────────────────────────────────────────────

SESGO_MUESTRA = 400
SESGO_MAX_CASTIGOS_PADRE = 3
SESGO_MAX_CASTIGOS_OMEGA = 3  # mismo límite; Omega también se castiga si no aprende causal


def evaluar_sesgo_aprendizaje(
    db_path: str,
    muestra: int = SESGO_MUESTRA,
    aplicar_castigo: bool = True,
) -> Dict:
    """aplicar_castigo=False para mediciones de LÍNEA BASE (p. ej. el 'pre'
    del entrenamiento): mide realidad vs fantasía sin disciplinar al Padre."""
    import json as _json
    from sentinel_omega.core.firmas.signature_engine import (
        SIMILARITY_ALERT, extraer_features_ventana, similitud,
    )
    from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES
    from sentinel_omega.core.juez.pesos import castigar

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_sesgo_aprendizaje ("
        "bot TEXT PRIMARY KEY, n INTEGER, recon_insample REAL, recon_causal REAL, "
        "sesgo REAL, castigos INTEGER, evaluada_at TEXT DEFAULT (datetime('now')))"
    )

    # Incluye 'omega' en el dominio de evaluación aunque no esté en BOT_FEATURES
    # (Omega usa None como keys → vector completo)
    bots_evaluar = dict(BOT_FEATURES)
    if "omega" not in bots_evaluar:
        bots_evaluar["omega"] = None  # None → vector completo (igual que el Padre)

    # Firmas consolidadas por bot + timestamp más temprano de su memoria.
    # El t0 (primer avistamiento) sale de MIN(ts_evento) en la tabla hija —
    # antes se parseaba el array eventos_json entero solo para el mínimo.
    firmas: Dict[str, list] = {}
    for firma_id, bot, feats in conn.execute(
        "SELECT firma_id, bot_name, features_json FROM TBL_FIRMAS "
        "WHERE estado = 'consolidada'"
    ):
        try:
            f = _json.loads(feats)
            row = conn.execute(
                "SELECT MIN(ts_evento) FROM tbl_firma_eventos WHERE firma_id = ?",
                (firma_id,),
            ).fetchone()
            t0 = row[0] if row else None
        except Exception:
            continue
        firmas.setdefault(bot, []).append((f, t0))

    # Muestra de eventos repartida por toda la línea de tiempo
    todos = conn.execute(
        "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= 4.5 ORDER BY timestamp_blk"
    ).fetchall()
    if not todos:
        conn.close()
        return {"eventos": 0}
    paso = max(1, len(todos) // muestra)
    eventos = todos[::paso]

    conteo = {b: {"n": 0, "insample": 0, "causal": 0} for b in bots_evaluar}
    for ts, nodo in eventos:
        feats = extraer_features_ventana(conn, ts, nodo)
        if not feats:
            continue
        for bot, keys in bots_evaluar.items():
            fs = firmas.get(bot)
            if not fs:
                continue
            sub = feats if keys is None else {k: feats[k] for k in keys if k in feats}
            if not sub:
                continue
            best_all = max((similitud(sub, f) for f, _ in fs), default=0.0)
            best_causal = max(
                (similitud(sub, f) for f, t0 in fs if t0 and t0 < ts), default=0.0
            )
            c = conteo[bot]
            c["n"] += 1
            if best_all >= SIMILARITY_ALERT:
                c["insample"] += 1
            if best_causal >= SIMILARITY_ALERT:
                c["causal"] += 1

    resultado = {}
    for bot, c in conteo.items():
        if c["n"] == 0:
            continue
        insample = c["insample"] / c["n"]
        causal = c["causal"] / c["n"]
        sesgo = insample - causal
        castigos = 0
        # Padre y Omega se castigan si su reconocimiento causal es bajo
        # (solo en evaluaciones disciplinarias, no en líneas base 'pre')
        if aplicar_castigo and bot in ("padre", "omega"):
            max_cast = SESGO_MAX_CASTIGOS_PADRE if bot == "padre" else SESGO_MAX_CASTIGOS_OMEGA
            castigos = min(max_cast, round((1.0 - causal) * max_cast))
            for _ in range(castigos):
                castigar(conn, bot, es_padre=(bot == "padre"), gravedad=1.0)
        conn.execute(
            "INSERT OR REPLACE INTO tbl_sesgo_aprendizaje "
            "(bot, n, recon_insample, recon_causal, sesgo, castigos) "
            "VALUES (?,?,?,?,?,?)",
            (bot, c["n"], round(insample, 4), round(causal, 4), round(sesgo, 4), castigos),
        )
        resultado[bot] = {"insample": round(insample, 3), "causal": round(causal, 3),
                          "sesgo": round(sesgo, 3), "castigos": castigos}
    conn.commit()
    conn.close()
    logger.info(f"Sesgo de aprendizaje (realidad vs fantasía): {resultado}")
    return {"eventos": len(eventos), "por_bot": resultado}


# ── Orden de los precursores — ¿la secuencia importa? ────────────────────────
# El Padre ahora también ve el ORDEN en que se presentaron los dominios en la
# víspera de cada evento (p. ej. SOLAR→SISMICO→DESGAS vs DESGAS→SISMICO) y
# discierne, contando, si el orden hace diferencia o es indiferente: si para
# un mismo conjunto de dominios una secuencia domina claramente, el orden
# IMPORTA; si las permutaciones se reparten parejo, es INDIFERENTE.
ORDEN_MUESTRA = 300
ORDEN_MIN_N = 30          # conjunto con menos casos no alcanza veredicto
ORDEN_FRAC_DOMINANTE = 0.6  # una secuencia con ≥60% del conjunto = dominante
ORDEN_SEGMENTOS = 4       # la ventana de 14 días se parte en 4 tramos de 3.5d


def _orden_evento(conn, ts_evento: str, id_nodo: int) -> str:
    """Orden de activación de dominios en los 4 tramos de la víspera.

    Devuelve 'SOLAR→SISMICO' (activación secuencial), 'SOLAR+SISMICO'
    (mismo tramo) o '' si ningún dominio se activó.
    """
    horas_tramo = 336 // ORDEN_SEGMENTOS
    activacion = {}
    for seg in range(ORDEN_SEGMENTOS):
        ini = f"-{336 - seg * horas_tramo} hours"
        fin = f"-{336 - (seg + 1) * horas_tramo} hours"
        # SOLAR: tormenta geomagnética en el tramo
        kp = conn.execute(
            "SELECT MAX(kp_max) FROM tbl_clima_espacial_raw "
            "WHERE timestamp_blk >= datetime(?, ?) AND timestamp_blk < datetime(?, ?)",
            (ts_evento, ini, ts_evento, fin)).fetchone()[0]
        if kp is not None and kp >= 4 and "SOLAR" not in activacion:
            activacion["SOLAR"] = seg
        # SISMICO: actividad en el nodo del evento
        sis = conn.execute(
            "SELECT COUNT(*) FROM tbl_historico_sismico_raw WHERE id_nodo = ? "
            "AND timestamp_blk >= datetime(?, ?) AND timestamp_blk < datetime(?, ?)",
            (id_nodo, ts_evento, ini, ts_evento, fin)).fetchone()[0]
        if sis and "SISMICO" not in activacion:
            activacion["SISMICO"] = seg
        # DESGAS: erupción/SO2 global en el tramo
        des = conn.execute(
            "SELECT COUNT(*) FROM tbl_desgasificacion_raw "
            "WHERE timestamp_blk >= datetime(?, ?) AND timestamp_blk < datetime(?, ?)",
            (ts_evento, ini, ts_evento, fin)).fetchone()[0]
        if des and "DESGAS" not in activacion:
            activacion["DESGAS"] = seg
        # FINANCIERO: volatilidad BTC elevada en el tramo
        vol = conn.execute(
            "SELECT MAX(volatilidad_24h) FROM tbl_psique_financiera "
            "WHERE timestamp_blk >= datetime(?, ?) AND timestamp_blk < datetime(?, ?)",
            (ts_evento, ini, ts_evento, fin)).fetchone()[0]
        if vol is not None and vol >= 5 and "FINANCIERO" not in activacion:
            activacion["FINANCIERO"] = seg
    if not activacion:
        return ""
    por_seg: Dict[int, list] = {}
    for dom, seg in activacion.items():
        por_seg.setdefault(seg, []).append(dom)
    return "→".join(
        "+".join(sorted(por_seg[s])) for s in sorted(por_seg)
    )


def analizar_orden_precursores(db_path: str, muestra: int = ORDEN_MUESTRA) -> Dict:
    """Cuenta secuencias de activación y emite veredictos por conjunto.

    tbl_orden_precursores: (orden, event_class) -> n  (contar, no anotar)
    tbl_orden_veredictos:  conjunto -> ¿el orden importa o es indiferente?
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_orden_precursores ("
        "orden TEXT, event_class TEXT, n INTEGER, "
        "PRIMARY KEY (orden, event_class))")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_orden_veredictos ("
        "conjunto TEXT PRIMARY KEY, n_total INTEGER, orden_dominante TEXT, "
        "frac_dominante REAL, veredicto TEXT, "
        "actualizada_at TEXT DEFAULT (datetime('now')))")

    # TODOS los eventos naturales (no solo sismos): cada uno es una liberación
    # de energía cuya coreografía de precursores queremos leer.
    eventos = _catalogo_eventos_energia(conn)
    if not eventos:
        conn.close()
        return {"eventos": 0}
    paso = max(1, len(eventos) // muestra)
    eventos = eventos[::paso]

    conteo: Dict[tuple, int] = {}
    for ts, nodo, clase in eventos:
        orden = _orden_evento(conn, ts, nodo)
        if not orden:
            continue
        conteo[(orden, clase)] = conteo.get((orden, clase), 0) + 1

    conn.execute("DELETE FROM tbl_orden_precursores")
    conn.executemany(
        "INSERT INTO tbl_orden_precursores (orden, event_class, n) VALUES (?,?,?)",
        [(o, c, n) for (o, c), n in conteo.items()])

    # Veredicto por CONJUNTO de dominios: ¿domina una secuencia?
    por_conjunto: Dict[str, Dict[str, int]] = {}
    for (orden, _), n in conteo.items():
        doms = frozenset(orden.replace("→", "+").split("+"))
        clave = "+".join(sorted(doms))
        por_conjunto.setdefault(clave, {})
        por_conjunto[clave][orden] = por_conjunto[clave].get(orden, 0) + n

    conn.execute("DELETE FROM tbl_orden_veredictos")
    veredictos = {}
    for conjunto, ordenes in por_conjunto.items():
        total = sum(ordenes.values())
        dominante, n_dom = max(ordenes.items(), key=lambda kv: kv[1])
        frac = n_dom / total
        if total < ORDEN_MIN_N:
            ver = "SIN VEREDICTO (pocos casos)"
        elif len(ordenes) == 1:
            ver = "ORDEN UNICO OBSERVADO"
        elif frac >= ORDEN_FRAC_DOMINANTE:
            ver = "EL ORDEN IMPORTA"
        else:
            ver = "INDIFERENTE"
        conn.execute(
            "INSERT INTO tbl_orden_veredictos "
            "(conjunto, n_total, orden_dominante, frac_dominante, veredicto) "
            "VALUES (?,?,?,?,?)",
            (conjunto, total, dominante, round(frac, 3), ver))
        veredictos[conjunto] = {"n": total, "dominante": dominante,
                                "frac": round(frac, 3), "veredicto": ver}
    conn.commit()
    conn.close()
    logger.info(f"Orden de precursores: {len(conteo)} secuencias, "
                f"veredictos: { {k: v['veredicto'] for k, v in veredictos.items()} }")
    return {"eventos": len(eventos), "secuencias": len(conteo),
            "veredictos": veredictos}


# ── Secuencia de NODOS — la ruta por la que se mueve la energía ──────────────
# No basta con QUÉ nodos se activan: importa EN QUÉ ORDEN espacial. Para cada
# evento reconstruimos la secuencia de nodos que se activaron en la víspera (qué
# nodo emitió primero, luego cuál…) — la forma en que la energía se propaga por
# la malla. Contamos (+1) las secuencias recurrentes y las clasificamos:
#   GLOBAL  — la misma ruta precede a distintos TIPOS de evento → cimática
#             organizada: un sistema liberando energía con precursores/gatillos
#             identificables (nodos emisores + camino de propagación).
#   LOCAL   — la ruta es recurrente pero ligada a un solo tipo → causa específica
#             (eventos distintos con detonantes distintos).
SEC_NODOS_MUESTRA = 300
SEC_NODOS_VENTANA_H = 72     # víspera donde se observa la propagación
SEC_NODOS_MAX_LEN = 5        # ruta acotada (primeros nodos en activarse)
SEC_NODOS_MIN_FREC = 3       # una ruta con menos apariciones no es recurrente


def _catalogo_eventos_energia(conn) -> list:
    """TODO evento natural es una liberación de energía: sismos + volcanes +
    tormentas solares (y cualquier no-sísmico catalogado — blue jets/sprites
    entran cuando el escáner los persista históricamente). Devuelve
    [(timestamp_blk, id_nodo, event_class), ...] ordenado en el tiempo.

    Analizar la cimática de TODOS los tipos —y no solo sismos— es lo que deja
    ver rutas de propagación que cruzan dominios (una ruta que precede a un
    sismo Y a una erupción es una cimática global, no una coincidencia local).
    """
    eventos: list = []
    for ts, nodo, mag in conn.execute(
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw WHERE sismo_max_mag >= 4.5"
    ):
        clase = ("SISMO_M7" if mag >= 7 else "SISMO_M6" if mag >= 6
                 else "SISMO_M5" if mag >= 5 else "SISMO_M4")
        eventos.append((ts, nodo, clase))
    try:
        for ts, nodo, clase in conn.execute(
            "SELECT timestamp_blk, id_nodo, event_class "
            "FROM tbl_eventos_no_sismicos"
        ):
            eventos.append((ts, nodo, clase))
    except sqlite3.OperationalError:
        pass   # catálogo no-sísmico aún no derivado
    eventos.sort(key=lambda e: e[0])
    return eventos


def _secuencia_nodos_evento(conn, ts_evento: str, id_nodo_evento: int) -> str:
    """Ruta de nodos que se activaron en la víspera, en orden temporal.

    Devuelve 'nodo12>nodo45>nodoX' (X = nodo del evento, la culminación) o ''
    si no hubo una propagación de al menos 2 nodos.
    """
    ini = f"-{SEC_NODOS_VENTANA_H} hours"
    filas = conn.execute(
        "SELECT id_nodo FROM tbl_historico_sismico_raw "
        "WHERE timestamp_blk >= datetime(?, ?) AND timestamp_blk < ? "
        "AND sismo_count > 0 ORDER BY timestamp_blk",
        (ts_evento, ini, ts_evento)).fetchall()
    seq: list = []
    for (nodo,) in filas:
        if nodo not in seq:          # primera aparición = orden de activación
            seq.append(nodo)
        if len(seq) >= SEC_NODOS_MAX_LEN:
            break
    if id_nodo_evento not in seq:
        seq.append(id_nodo_evento)   # el evento culmina la ruta
    if len(seq) < 2:
        return ""
    return ">".join(f"nodo{n}" for n in seq[:SEC_NODOS_MAX_LEN])


def analizar_secuencia_nodos(db_path: str, muestra: int = SEC_NODOS_MUESTRA) -> Dict:
    """Cuenta rutas de propagación de energía por la malla y las clasifica
    como GLOBAL (cimática organizada) o LOCAL (causa específica).

    tbl_secuencia_nodos:    (secuencia, event_class) -> frecuencia  (contar)
    tbl_secuencia_veredictos: secuencia -> alcance + interpretación
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_secuencia_nodos ("
        "secuencia TEXT, event_class TEXT, frecuencia INTEGER, "
        "PRIMARY KEY (secuencia, event_class))")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_secuencia_veredictos ("
        "secuencia TEXT PRIMARY KEY, frecuencia_total INTEGER, "
        "n_clases INTEGER, n_nodos INTEGER, alcance TEXT, interpretacion TEXT, "
        "actualizada_at TEXT DEFAULT (datetime('now')))")

    # TODOS los eventos naturales (sismo, volcán, tormenta solar…), no solo sismos
    eventos = _catalogo_eventos_energia(conn)
    if not eventos:
        conn.close()
        return {"eventos": 0}
    paso = max(1, len(eventos) // muestra)
    eventos = eventos[::paso]

    conteo: Dict[tuple, int] = {}
    for ts, nodo, clase in eventos:
        seq = _secuencia_nodos_evento(conn, ts, nodo)
        if not seq:
            continue
        conteo[(seq, clase)] = conteo.get((seq, clase), 0) + 1

    conn.execute("DELETE FROM tbl_secuencia_nodos")
    conn.executemany(
        "INSERT INTO tbl_secuencia_nodos (secuencia, event_class, frecuencia) "
        "VALUES (?,?,?)", [(s, c, n) for (s, c), n in conteo.items()])

    # Veredicto por RUTA: ¿es global (varios tipos de evento) o local?
    por_ruta: Dict[str, Dict[str, int]] = {}
    for (seq, clase), n in conteo.items():
        por_ruta.setdefault(seq, {})
        por_ruta[seq][clase] = por_ruta[seq].get(clase, 0) + n

    conn.execute("DELETE FROM tbl_secuencia_veredictos")
    veredictos = {}
    for seq, clases in por_ruta.items():
        total = sum(clases.values())
        if total < SEC_NODOS_MIN_FREC:
            continue   # no recurrente — no concluimos nada
        n_nodos = seq.count(">") + 1
        if len(clases) >= 2:
            alcance = "GLOBAL"
            interp = ("cimática organizada: la misma ruta de propagación "
                      "precede a distintos tipos de evento — sistema liberando "
                      "energía con precursores/gatillos identificables")
        else:
            alcance = "LOCAL"
            interp = ("ruta recurrente pero ligada a un solo tipo de evento — "
                      "causa específica de ese nodo/región")
        conn.execute(
            "INSERT INTO tbl_secuencia_veredictos "
            "(secuencia, frecuencia_total, n_clases, n_nodos, alcance, "
            " interpretacion) VALUES (?,?,?,?,?,?)",
            (seq, total, len(clases), n_nodos, alcance, interp))
        veredictos[seq] = {"frecuencia": total, "clases": len(clases),
                           "alcance": alcance}
    conn.commit()
    conn.close()

    n_global = sum(1 for v in veredictos.values() if v["alcance"] == "GLOBAL")
    logger.info(
        f"Secuencia de nodos: {len(conteo)} rutas, {len(veredictos)} recurrentes "
        f"({n_global} GLOBALES — cimática organizada)")
    return {"eventos": len(eventos), "rutas": len(conteo),
            "recurrentes": len(veredictos), "globales": n_global,
            "veredictos": veredictos}
