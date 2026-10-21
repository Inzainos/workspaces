"""Plantillas cascada del Concilio (pedido del operador, 2026-10-20).

Cuatro plantillas con la MISMA dinámica de agregación que los reportes del
sistema, pero en ventanas de horas y para el teléfono:

- **P2H** (cada 3 h): el ESTADO de la Tierra — solo lo que la API ve AHORA.
  Fantasma, muro, telemetría, GOES, térmico, precursores activos con su
  sitio (nombre → nodo → coords) y su lag RESTÁNDOSE. Es el snapshot.
- **P6H** (cada 6 h): el COMPORTAMIENTO — junta las dos P2H anteriores más
  la del momento: hacia dónde va el fantasma, qué señales entraron o
  salieron, tendencias. El reporte detallado.
- **P12H** (cada 12 h): el COMPARATIVO de medio día — contra la P6H
  anterior.
- **P24H** (cada 24 h): el comparativo del día.

Mecánica de la cascada: cada P2H persiste su SNAPSHOT en JSON
(`estado/plantillas/`); las mayores leen los snapshot de las menores y
comparan. La marca de cadencia vive en `data/estado_plantillas.json`
(mismo patrón que el digesto: sobrevive procesos, una sola fuente de
verdad). El texto sale por la cola de Telegram (el canal del Concilio)
y el JSON queda para que el Concilio lo lea en su próxima sesión.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sentinel_omega.core.nodos import (
    formato_lag,
    lag_restante_h,
    sitio_nodo_desde_fila,
)

logger = logging.getLogger(__name__)

DIR_PLANTILLAS = Path(
    "/home/deamon/workspaces/estado/plantillas"
)
ESTADO_FILE = "estado_plantillas.json"


# ── Cadencia ────────────────────────────────────────────────────────────────

def _cargar_estado(db_path: str) -> Dict[str, float]:
    ruta = Path(db_path).parent / ESTADO_FILE
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _guardar_estado(db_path: str, estado: Dict[str, float]) -> None:
    ruta = Path(db_path).parent / ESTADO_FILE
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(estado), encoding="utf-8")
        os.replace(tmp, ruta)
    except OSError as exc:
        logger.warning("plantillas: no se pudo guardar la marca: %s", exc)


def debidas(ahora_ts: Optional[float] = None, db_path: str = "") -> List[str]:
    """Qué plantillas tocan AHORA (['p2h'], ['p2h','p6h'], ...).

    La cadencia vive en la HORA LOCAL del sistema (el operador lee su
    teléfono en MX): P2H en horas múltiplo de 3, P6H de 6, P12H de 12,
    P24H a medianoche. La marca en disco evita dobles corridas del mismo
    tramo horario.
    """
    ahora = datetime.fromtimestamp(ahora_ts or time.time(),
                                  tz=timezone.utc)
    # hora local MX (UTC-6, sin DST) para que los cortes coincidan con lo
    # que el operador espera ver en su teléfono.
    hora_local = (ahora.hour - 6) % 24
    estado = _cargar_estado(db_path)
    tramo = int(time.time() // 3600)  # tramo horario único
    debidas: List[str] = []
    tipos_hora = [("p2h", 3), ("p6h", 6), ("p12h", 12), ("p24h", 24)]
    for tipo, cada in tipos_hora:
        toca = (hora_local % cada == 0) if tipo != "p24h" else (hora_local == 0)
        if toca and estado.get(tipo, 0) != tramo:
            debidas.append(tipo)
    return debidas


def marcar(db_path: str, tipo: str) -> None:
    estado = _cargar_estado(db_path)
    estado[tipo] = int(time.time() // 3600)
    _guardar_estado(db_path, estado)


# ── Snapshot (la P2H es su versión serializable) ─────────────────────────────

def _fila(r, *campos):
    d = dict(r) if r is not None else {}
    return {c: d.get(c) for c in campos}


def snapshot_2h(conn: sqlite3.Connection) -> Dict[str, Any]:
    """El estado de la Tierra AHORA — la base de toda la cascada."""
    conn.row_factory = sqlite3.Row
    ahora = time.time()
    snap: Dict[str, Any] = {"ts": ahora}

    ciclo = conn.execute(
        "SELECT timestamp, geo_signal, geo_confidence, fantasma, nivel_riesgo, "
        "precursors_count, precursor_types, muro_walls_active, muro_breach "
        "FROM TBL_CICLOS ORDER BY id DESC LIMIT 1"
    ).fetchone()
    snap["ciclo"] = _fila(ciclo, "timestamp", "geo_signal", "geo_confidence",
                          "fantasma", "nivel_riesgo", "precursors_count",
                          "precursor_types", "muro_walls_active", "muro_breach")

    tele = conn.execute(
        "SELECT bz_nT, viento_km_s, kp, presion_hpa, schumann_activity "
        "FROM TBL_PRECURSORES_COSMICOS ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    snap["telemetria"] = _fila(tele, "bz_nT", "viento_km_s", "kp",
                              "presion_hpa", "schumann_activity")

    try:
        row = conn.execute(
            "SELECT MAX(flux_max) FROM tbl_xray_vivo "
            "WHERE timestamp_blk >= datetime('now','-24 hours')"
        ).fetchone()
        fx = float(row[0]) if row and row[0] is not None else None
        snap["goes_flux_max_24h"] = fx
        snap["goes_clase"] = ("X" if fx and fx >= 1e-4 else
                              "M" if fx and fx >= 1e-5 else
                              "C" if fx and fx >= 1e-6 else None)
    except sqlite3.Error:
        snap["goes_clase"] = None
        snap["goes_flux_max_24h"] = None

    try:
        row = conn.execute(
            "SELECT COUNT(*), MAX(thermal_anomalies) FROM tbl_cobertura_satelital "
            "WHERE timestamp_blk=(SELECT MAX(timestamp_blk) FROM tbl_cobertura_satelital) "
            "AND thermal_anomalies>0"
        ).fetchone()
        snap["termico"] = {"zonas": int(row[0]), "max": int(row[1] or 0)} \
            if row else {"zonas": 0, "max": 0}
    except sqlite3.Error:
        snap["termico"] = None

    # Firma matches del último registro del padre → señales VIVAS con countdown
    señales: List[Dict[str, Any]] = []
    try:
        reg = conn.execute(
            "SELECT timestamp, detalles_json FROM TBL_JUEZ_AUDITORIA "
            "WHERE bot_name='padre' AND detalles_json LIKE '%firma_matches%' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if reg:
            det = json.loads(reg["detalles_json"] or "{}")
            for m in det.get("firma_matches", [])[:6]:
                vh = m.get("ventana_tipica_h")
                rest, ancla = lag_restante_h(
                    conn, ventana_tipica_h=vh, ahora_ts=ahora,
                    id_nodo=m.get("id_nodo"),
                    event_class=str(m.get("event_class") or ""),
                    timestamp_actual=reg["timestamp"],
                )
                señales.append({
                    "sitio": sitio_nodo_desde_fila(conn, m.get("id_nodo")),
                    "id_nodo": m.get("id_nodo"),
                    "evento": m.get("event_class"),
                    "similitud": m.get("similitud"),
                    "recurrencia": m.get("recurrencia"),
                    "lag_inicial_h": vh,
                    "lag_restante_h": round(rest, 1) if rest is not None else None,
                    "ancla_ts": ancla,
                })
    except Exception as exc:  # noqa: BLE001 — la plantilla sale igual
        logger.warning("plantillas: firma matches ilegibles: %s", exc)
    snap["senales"] = señales

    try:
        ml = conn.execute(
            "SELECT clases, detectado_en, fecha_inicio, fecha_fin "
            "FROM tbl_muro_lags_estado WHERE id=1 AND activo=1"
        ).fetchone()
        # dias_restantes NO es columna: se calcula en lectura igual que
        # /api/muro_lags (api.py). El SELECT original pedía una columna
        # inexistente y el except lo tragaba en silencio → None eterno.
        if ml:
            ml = dict(ml)
            try:
                hoy = datetime.now(timezone.utc).date()
                dini = datetime.strptime(ml["fecha_inicio"], "%Y-%m-%d").date()
                dfin = datetime.strptime(ml["fecha_fin"], "%Y-%m-%d").date()
                ml["dias_restantes"] = [
                    max(0, (dini - hoy).days), max(0, (dfin - hoy).days)
                ]
            except (KeyError, TypeError, ValueError):
                ml["dias_restantes"] = None
        snap["muro_lags"] = ml if ml else None
    except sqlite3.Error:
        snap["muro_lags"] = None

    return snap


# ── Render ───────────────────────────────────────────────────────────────────

def _f(v, dec=1):
    try:
        return f"{float(v):.{dec}f}"
    except (TypeError, ValueError):
        return "—"


def _render_p2h(snap: Dict[str, Any]) -> str:
    c = snap.get("ciclo") or {}
    t = snap.get("telemetria") or {}
    L = ["<b>🌱 ESTADO DE LA TIERRA — P2H</b>"]
    L.append(f"<i>{datetime.now(timezone.utc).strftime('%H:%M')} UTC</i>")
    L.append("")
    L.append(f"👻 Fantasma <code>{_f(c.get('fantasma'))}</code> · "
             f"{str(c.get('nivel_riesgo') or '—').upper()} · "
             f"muro <code>{c.get('muro_walls_active')}/5</code>"
             + (" 🚨 BREACH" if c.get("muro_breach") else ""))
    tel = []
    if t.get("bz_nT") is not None:
        tel.append(f"Bz {_f(t['bz_nT'])} nT")
    if t.get("viento_km_s") is not None:
        tel.append(f"viento {_f(t['viento_km_s'], 0)} km/s")
    if t.get("kp") is not None:
        tel.append(f"Kp {_f(t['kp'])}")
    if t.get("presion_hpa") is not None:
        tel.append(f"presión {_f(t['presion_hpa'], 0)} hPa")
    if tel:
        L.append("🛰 " + " · ".join(tel))
    if snap.get("goes_clase"):
        L.append(f"☀️ GOES clase <code>{snap['goes_clase']}</code> "
                 f"(máx 24 h: {snap.get('goes_flux_max_24h'):.1e} W/m²)"
                 if snap.get("goes_flux_max_24h") else
                 f"☀️ GOES clase <code>{snap['goes_clase']}</code>")
    term = snap.get("termico")
    if term and term.get("zonas"):
        L.append(f"🛰️ Térmico Alfa-2: {term['zonas']} zona(s) sin precedente (máx {term['max']})")
    L.append("")
    sen = snap.get("senales") or []
    if sen:
        L.append("<b>📡 Señales vivas (lag restándose):</b>")
        for s in sen:
            lag = formato_lag(s.get("lag_restante_h"))
            L.append(f"  · <b>{s['evento']}</b> — {s['sitio']}")
            L.append(f"      parecido {_f(s.get('similitud'), 2) if isinstance(s.get('similitud'), float) else '—'}"
                     f" · visto {s.get('recurrencia') or '—'}× · lag <code>{lag}</code>")
    else:
        L.append("📡 Sin señales de firma activas ahora.")
    ml = snap.get("muro_lags")
    if ml:
        dr = ml.get("dias_restantes")
        if isinstance(dr, (list, tuple)) and len(dr) == 2:
            L.append("")
            L.append(f"🕐 Convergencia: faltan ~{dr[0]}–{dr[1]} d "
                     f"({ml.get('fecha_inicio')} → {ml.get('fecha_fin')}) · "
                     f"{', '.join(json.loads(ml.get('clases') or '[]'))}")
    L.append("")
    L.append("<i>Snapshot P2H — la P6H lo junta con los anteriores.</i>")
    return "\n".join(L)


def _leer_snapshots(tipo: str, n: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        archivos = sorted(DIR_PLANTILLAS.glob(f"{tipo}_*.json"),
                          reverse=True)[:n]
        for a in archivos:
            try:
                out.append(json.loads(a.read_text(encoding="utf-8")))
            except Exception:
                continue
    except FileNotFoundError:
        pass
    return out


def _render_comparativo(titulo: str, emojí: str, previos: List[Dict],
                         actual: Dict) -> str:
    """La dinámica compartida de P6H/P12H/P24H: antes vs ahora, y hacia dónde."""
    L = [f"<b>{emojí} {titulo}</b>",
         f"<i>{datetime.now(timezone.utc).strftime('%H:%M')} UTC</i>", ""]

    def fant(s):
        c = s.get("ciclo") or {}
        try:
            return float(c.get("fantasma"))
        except (TypeError, ValueError):
            return None

    f_now = fant(actual)
    f_prev = [fant(p) for p in previos if fant(p) is not None]
    if f_now is not None and f_prev:
        delta = f_now - f_prev[0]
        flecha = "▲ sube" if delta > 0.5 else ("▼ baja" if delta < -0.5 else "＝ estable")
        serie = " · ".join(_f(v) for v in
                           [fant(p) for p in reversed(previos)] + [f_now]
                           if v is not None)
        L.append(f"👻 Fantasma: {serie} → <b>{flecha}</b> "
                 f"({delta:+.1f} en la ventana)")

    eventos_prev: set = set()
    for p in previos:
        for s in p.get("senales") or []:
            eventos_prev.add((s.get("id_nodo"), s.get("evento")))
    eventos_now = {(s.get("id_nodo"), s.get("evento"))
                   for s in actual.get("senales") or []}
    entraron = eventos_now - eventos_prev
    salieron = eventos_prev - eventos_now
    if entraron:
        L.append("")
        L.append("🆕 <b>Señales que ENTRARON:</b>")
        for s in actual.get("senales") or []:
            if (s.get("id_nodo"), s.get("evento")) in entraron:
                L.append(f"  · {s['evento']} — {s['sitio']} · "
                         f"lag {formato_lag(s.get('lag_restante_h'))}")
    if salieron:
        L.append("")
        L.append("🏁 <b>Señales que SALIERON</b> (ventana vencida o patrón disipado):")
        prev_map = {(s.get("id_nodo"), s.get("evento")): s
                    for p in previos for s in p.get("senales") or []}
        for key in salieron:
            s = prev_map.get(key, {})
            L.append(f"  · {key[1]} — {s.get('sitio', f'nodo {key[0]}')} "
                     f"(quedaba {formato_lag(s.get('lag_restante_h'))})")
    persistentes = eventos_prev & eventos_now
    if persistentes:
        L.append("")
        L.append("🔁 <b>Persistentes (el lag sigue restándose):</b>")
        for s in actual.get("senales") or []:
            if (s.get("id_nodo"), s.get("evento")) in persistentes:
                L.append(f"  · {s['evento']} — {s['sitio']} · "
                         f"lag <code>{formato_lag(s.get('lag_restante_h'))}</code>")

    # Tendencias de telemetría en la ventana
    def tel(key, dec=1):
        vals = []
        for p in reversed(previos):
            v = (p.get("telemetria") or {}).get(key)
            if v is not None:
                vals.append(float(v))
        v_now = (actual.get("telemetria") or {}).get(key)
        if v_now is not None:
            vals.append(float(v_now))
        return vals

    kp = tel("kp")
    bz = tel("bz_nT")
    bits = []
    if len(kp) >= 2:
        bits.append(f"Kp {min(kp):.1f}→{kp[-1]:.1f}")
    if len(bz) >= 2:
        bits.append(f"Bz {bz[0]:.1f}→{bz[-1]:.1f} nT")
    if bits:
        L.append("")
        L.append("🛰 " + " · ".join(bits))
    gc = [p.get("goes_clase") for p in previos] + [actual.get("goes_clase")]
    clases = {c for c in gc if c}
    if clases:
        L.append(f"☀️ GOES en la ventana: {', '.join(sorted(clases))}")
    L.append("")
    L.append("<i>Para el Concilio: estado, comportamiento y convergencias "
             "de la ventana.</i>")
    return "\n".join(L)


# ── Orquestación de una corrida ──────────────────────────────────────────────

def generar_y_enviar(tipo: str, conn: sqlite3.Connection, db_path: str) -> bool:
    """Genera la plantilla debida, la persiste y la encola (Telegram)."""
    DIR_PLANTILLAS.mkdir(parents=True, exist_ok=True)
    snap = snapshot_2h(conn)
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if tipo == "p2h":
        texto = _render_p2h(snap)
    elif tipo == "p6h":
        previos = _leer_snapshots("p2h", 2)
        texto = _render_comparativo("COMPORTAMIENTO DE LA TIERRA — P6H", "🌍",
                                    previos, snap)
    elif tipo == "p12h":
        previos = _leer_snapshots("p6h", 1) or _leer_snapshots("p2h", 4)
        texto = _render_comparativo("COMPARATIVO MEDIO DÍA — P12H", "🌗",
                                    previos, snap)
    elif tipo == "p24h":
        previos = _leer_snapshots("p12h", 1) or _leer_snapshots("p6h", 2)
        texto = _render_comparativo("COMPARATIVO DEL DÍA — P24H", "📅",
                                    previos, snap)
    else:
        return False

    # Snapshot JSON (cadena de la cascada) + MD legible
    (DIR_PLANTILLAS / f"{tipo}_{ts_tag}.json").write_text(
        json.dumps(snap, default=str), encoding="utf-8")
    (DIR_PLANTILLAS / f"{tipo.upper()}_{ts_tag}.md").write_text(
        texto.replace("<b>", "**").replace("</b>", "**")
             .replace("<code>", "`").replace("</code>", "`")
             .replace("<i>", "*").replace("</i>", "*"),
        encoding="utf-8")

    marcar(db_path, tipo)
    try:
        from sentinel_omega.infrastructure.api.telegram import send_alert
        ok = send_alert(texto)
        logger.info("PLANTILLA %s %s (%d señales)", tipo.upper(),
                    "enviada" if ok else "encolada/falló",
                    len(snap.get("senales") or []))
        return ok
    except Exception as exc:  # noqa: BLE001 — persistida aunque no vuele
        logger.warning("PLANTILLA %s persistida pero no enviada: %s", tipo, exc)
        return False


# ── Snapshot para la MiniApp (fresco cada ciclo, ≤5 min) ─────────────────────

MINIAPP_JSON = Path("/home/deamon/workspaces/estado/miniapp_estado.json")


def snapshot_miniapp(conn: sqlite3.Connection) -> Dict[str, Any]:
    """TODO lo que la MiniApp sirve, calculado con el código de ESTE repo.

    El endpoint del Concilio (otro proyecto, otro proceso) solo lee el
    JSON — así el formato de nodo, el countdown del lag y la ganancia del
    Juez viven UNA sola vez (regla del repo), y la MiniApp queda fresca
    a ≤5 min sin algoritmos duplicados. El countdown lo TICKA el cliente
    con `lag_restante_h` + `ts`.
    """
    snap = snapshot_2h(conn)
    conn.row_factory = sqlite3.Row

    # Auditoría del Juez (fase viva, sin duplicados) + ganancia
    aud = {"aciertos": 0, "fallos": 0, "falsos_positivos": 0}
    _mapa = {"ACIERTO": "aciertos", "FALLO": "fallos",
             "FALSO_POSITIVO": "falsos_positivos"}
    ganancia = asertividad = asertividad_muda = None
    try:
        filas = conn.execute(
            "SELECT resultado, COUNT(*) n FROM viva_real "
            "WHERE COALESCE(en_vivo,1)=1 AND resultado != 'PENDIENTE' "
            "GROUP BY resultado"
        ).fetchall()
        for r in filas:
            clave = _mapa.get(str(r["resultado"]).upper())
            if clave:
                aud[clave] = int(r["n"])
        from sentinel_omega.core.precursor.baseline import evaluar_veredictos
        pares = conn.execute(
            "SELECT verdad, resultado FROM viva_real "
            "WHERE COALESCE(en_vivo,1)=1 AND resultado != 'PENDIENTE' "
            "AND verdad != ''"
        ).fetchall()
        m = evaluar_veredictos([(p[0], p[1]) for p in pares])
        if m is not None:
            ganancia = m.ganancia
            asertividad = m.asertividad
            asertividad_muda = m.asertividad_muda
    except Exception as exc:  # noqa: BLE001 — la MiniApp sirve lo que haya
        logger.warning("miniapp: auditoría ilegible: %s", exc)
    snap["auditoria"] = {
        **aud,
        "ganancia": ganancia,
        "asertividad": asertividad,
        "asertividad_muda": asertividad_muda,
    }

    # Cimática
    try:
        n = conn.execute("SELECT COUNT(*) FROM tbl_cimatica_patrones").fetchone()
        snap["cimatica_total"] = int(n[0]) if n else 0
        snap["cimatica_top"] = [
            {"frecuencia": r[0], "event_class": r[1], "ambito": r[2]}
            for r in conn.execute(
                "SELECT frecuencia, event_class, ambito FROM tbl_cimatica_patrones "
                "ORDER BY frecuencia DESC LIMIT 6"
            ).fetchall()
        ]
    except sqlite3.Error:
        snap["cimatica_total"] = None
        snap["cimatica_top"] = []

    # Serie fantasma (últimos 48 ciclos) + nivel para colorear
    try:
        snap["serie_fantasma"] = [
            {"ts": r[0], "fantasma": r[1], "nivel": r[2]}
            for r in conn.execute(
                "SELECT timestamp, fantasma, nivel_riesgo FROM TBL_CICLOS "
                "ORDER BY id DESC LIMIT 48"
            ).fetchall()
        ][::-1]
    except sqlite3.Error:
        snap["serie_fantasma"] = []

    # Sismos recientes M4.5+
    try:
        snap["sismos_recientes"] = [
            {"ts": r[0], "mag": r[1], "lugar": r[2]}
            for r in conn.execute(
                "SELECT timestamp, magnitude, place FROM TBL_HISTORICO_SISMICO "
                "WHERE magnitude >= 4.5 ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
        ]
    except sqlite3.Error:
        snap["sismos_recientes"] = []

    return snap


def refrescar_miniapp(conn: sqlite3.Connection) -> None:
    """Persiste el snapshot de la MiniApp (lo llama el launcher cada ciclo)."""
    try:
        snap = snapshot_miniapp(conn)
        tmp = MINIAPP_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(snap, default=str), encoding="utf-8")
        os.replace(tmp, MINIAPP_JSON)
    except Exception as exc:  # noqa: BLE001 — nunca tumba el ciclo
        logger.warning("miniapp: no se pudo refrescar el snapshot: %s", exc)


def correr_debidas(conn: sqlite3.Connection, db_path: str) -> List[str]:
    """Punto de entrada del ciclo: genera todo lo que toca."""
    hechas: List[str] = []
    for tipo in debidas(db_path=db_path):
        try:
            generar_y_enviar(tipo, conn, db_path)
            hechas.append(tipo)
        except Exception as exc:  # noqa: BLE001
            logger.warning("plantilla %s falló: %s", tipo, exc)
    return hechas
