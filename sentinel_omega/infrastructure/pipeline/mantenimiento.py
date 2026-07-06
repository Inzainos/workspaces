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


def evaluar_sesgo_aprendizaje(db_path: str, muestra: int = SESGO_MUESTRA) -> Dict:
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

    # Firmas consolidadas por bot + timestamp más temprano de su memoria
    firmas: Dict[str, list] = {}
    for bot, feats, evs in conn.execute(
        "SELECT bot_name, features_json, eventos_json FROM TBL_FIRMAS "
        "WHERE estado = 'consolidada'"
    ):
        try:
            f = _json.loads(feats)
            refs = _json.loads(evs) if evs else []
            t0 = min((r.split("|")[0] for r in refs), default=None)
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
        if bot in ("padre", "omega"):
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
