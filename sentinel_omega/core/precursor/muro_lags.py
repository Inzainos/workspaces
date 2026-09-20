"""
Muro de Lags — convergencia temporal de firmas matcheadas, CON memoria.

Extensión del Muro de los 5 Eventos al eje del TIEMPO: cada firma matcheada
en vivo trae su propia ventana típica de presentación (su lag aprendido).
Si varias firmas independientes convergen en la misma ventana de fechas,
el muro se activa: no solo "hay señal", sino "varias memorias distintas
apuntan a las MISMAS fechas".

Ventana por match: [0.5 x lag, 1.5 x lag] días desde ahora (la mitad y el
150% de su tiempo típico). Breach cuando >= 3 firmas se traslapan.

MEMORIA (2026-09-15): la primera vez que una convergencia se activa se ANCLA
—se fijan las fechas absolutas de inicio/fin— y se persiste. Mientras las
MISMAS firmas sigan convergiendo en ciclos siguientes, la ventana NO se vuelve
a proyectar desde ahora: se conserva el ancla y se reportan los **días
restantes** (fecha_fin − hoy), que van bajando. Así el tiempo se descuenta en
vez de deslizarse siempre hacia adelante.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import json

MIN_CONVERGENCIA = 3
# Cuántas firmas deben seguir compartidas para considerar que es la MISMA señal.
MIN_SOLAPE_PERSISTENCIA = 3


def _now(ahora: Optional[datetime]) -> datetime:
    return ahora or datetime.now(timezone.utc)


def evaluar_muro_lags(
    matches: List[Dict[str, Any]],
    ahora: Optional[datetime] = None,
    min_convergencia: int = MIN_CONVERGENCIA,
    estado_previo: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate temporal convergence of matched signatures' expected windows.

    Each match needs "ventana_tipica_dias" (its firma's learned lag) and
    "firma_id". If `estado_previo` describes an active window whose firmas still
    converge now, the ORIGINAL anchor (fecha_inicio/fin) is kept and only the
    remaining days are recomputed — so the countdown decreases.
    """
    now = _now(ahora)

    intervalos = []
    for m in matches:
        lag = m.get("ventana_tipica_dias")
        if not lag or lag <= 0:
            continue
        intervalos.append({
            "ini": 0.5 * lag,
            "fin": 1.5 * lag,
            "firma_id": m.get("firma_id"),
            "event_class": m.get("event_class"),
            "similitud": m.get("similitud", 0.0),
        })

    base = {
        "activo": False,
        "firmas_convergentes": 0,
        "firmas_con_ventana": len(intervalos),
    }
    if len(intervalos) < min_convergencia:
        return base

    # Sweep: the day-offset covered by the most windows simultaneously
    puntos = sorted(
        {i["ini"] for i in intervalos} | {i["fin"] for i in intervalos}
    )
    mejor_punto, mejor_n = None, 0
    for p in puntos:
        n = sum(1 for i in intervalos if i["ini"] <= p <= i["fin"])
        if n > mejor_n:
            mejor_n, mejor_punto = n, p

    if mejor_n < min_convergencia:
        base["firmas_convergentes"] = mejor_n
        return base

    dentro = [i for i in intervalos if i["ini"] <= mejor_punto <= i["fin"]]
    ini = max(i["ini"] for i in dentro)
    fin = min(i["fin"] for i in dentro)
    firmas_ahora = {i["firma_id"] for i in dentro if i["firma_id"] is not None}
    clases = sorted({i["event_class"] for i in dentro if i["event_class"]})
    similitud_max = max(i["similitud"] for i in dentro)

    # ── ¿Es la MISMA señal persistente del ciclo anterior? ────────────────
    persistente = False
    if estado_previo and estado_previo.get("activo"):
        firmas_prev = set(estado_previo.get("firmas_ids") or [])
        if len(firmas_ahora & firmas_prev) >= min(MIN_SOLAPE_PERSISTENCIA, min_convergencia):
            persistente = True

    if persistente:
        # Conserva el ancla original; solo descuenta el tiempo.
        detectado_en = estado_previo["detectado_en"]
        fecha_inicio = estado_previo["fecha_inicio"]
        fecha_fin = estado_previo["fecha_fin"]
    else:
        # Nueva activación: ancla en AHORA.
        detectado_en = now.strftime("%Y-%m-%d %H:%M")
        fecha_inicio = (now + timedelta(days=ini)).strftime("%Y-%m-%d")
        fecha_fin = (now + timedelta(days=fin)).strftime("%Y-%m-%d")

    hoy = now.date()
    try:
        d_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        d_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        t0 = datetime.strptime(detectado_en, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        d_ini, d_fin, t0 = hoy, hoy, now.replace(tzinfo=None)
    dias_restantes_ini = max(0, (d_ini - hoy).days)
    dias_restantes_fin = max(0, (d_fin - hoy).days)
    dias_transcurridos = max(0, (now.replace(tzinfo=None) - t0).days)

    return {
        "activo": True,
        "persistente": persistente,
        "firmas_convergentes": mejor_n,
        "firmas_con_ventana": len(intervalos),
        "firmas_ids": sorted(firmas_ahora),
        "ventana_dias": [round(ini, 1), round(fin, 1)],
        "detectado_en": detectado_en,
        "dias_transcurridos": dias_transcurridos,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "dias_restantes": [dias_restantes_ini, dias_restantes_fin],
        "clases": clases,
        "similitud_max": similitud_max,
    }


# ── Persistencia (tabla creada on-demand; singleton id=1) ─────────────────

def _ensure_tabla(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_muro_lags_estado ("
        "id INTEGER PRIMARY KEY CHECK(id=1), activo INTEGER, firmas_ids TEXT, "
        "clases TEXT, detectado_en TEXT, fecha_inicio TEXT, fecha_fin TEXT, "
        "ventana_ini REAL, ventana_fin REAL, similitud_max REAL, "
        "actualizado TEXT DEFAULT (datetime('now')))"
    )


def cargar_estado_muro_lags(conn) -> Optional[Dict[str, Any]]:
    """Lee el estado persistido de la convergencia activa (o None)."""
    try:
        _ensure_tabla(conn)
        row = conn.execute(
            "SELECT activo, firmas_ids, clases, detectado_en, fecha_inicio, "
            "fecha_fin, ventana_ini, ventana_fin, similitud_max "
            "FROM tbl_muro_lags_estado WHERE id = 1"
        ).fetchone()
    except Exception:
        return None
    if not row or not row[0]:
        return None
    return {
        "activo": bool(row[0]),
        "firmas_ids": json.loads(row[1] or "[]"),
        "clases": json.loads(row[2] or "[]"),
        "detectado_en": row[3],
        "fecha_inicio": row[4],
        "fecha_fin": row[5],
        "ventana_dias": [row[6], row[7]],
        "similitud_max": row[8],
    }


def guardar_estado_muro_lags(conn, resultado: Dict[str, Any]) -> None:
    """Persiste (o limpia) el estado de la convergencia activa."""
    try:
        _ensure_tabla(conn)
        if not resultado.get("activo"):
            conn.execute(
                "INSERT INTO tbl_muro_lags_estado (id, activo, actualizado) "
                "VALUES (1, 0, datetime('now')) "
                "ON CONFLICT(id) DO UPDATE SET activo=0, actualizado=datetime('now')"
            )
        else:
            v = resultado.get("ventana_dias", [None, None])
            conn.execute(
                "INSERT INTO tbl_muro_lags_estado "
                "(id, activo, firmas_ids, clases, detectado_en, fecha_inicio, "
                " fecha_fin, ventana_ini, ventana_fin, similitud_max, actualizado) "
                "VALUES (1, 1, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')) "
                "ON CONFLICT(id) DO UPDATE SET activo=1, firmas_ids=excluded.firmas_ids, "
                "clases=excluded.clases, detectado_en=excluded.detectado_en, "
                "fecha_inicio=excluded.fecha_inicio, fecha_fin=excluded.fecha_fin, "
                "ventana_ini=excluded.ventana_ini, ventana_fin=excluded.ventana_fin, "
                "similitud_max=excluded.similitud_max, actualizado=datetime('now')",
                (
                    json.dumps(resultado.get("firmas_ids", [])),
                    json.dumps(resultado.get("clases", [])),
                    resultado.get("detectado_en"),
                    resultado.get("fecha_inicio"),
                    resultado.get("fecha_fin"),
                    v[0], v[1],
                    resultado.get("similitud_max", 0.0),
                ),
            )
        conn.commit()
    except Exception:
        pass


def format_muro_lags(resultado: Dict[str, Any]) -> str:
    if not resultado.get("activo"):
        return (
            f"Muro de Lags: sin convergencia "
            f"({resultado.get('firmas_convergentes', 0)} firmas)"
        )
    rest = resultado.get("dias_restantes")
    if rest:
        cuenta = (
            f"faltan ~{rest[0]}-{rest[1]} días"
            if rest[1] > 0 else "ventana en curso/vencida"
        )
    else:
        cuenta = f"ventana {resultado['ventana_dias'][0]}-{resultado['ventana_dias'][1]} días"
    persist = ""
    if resultado.get("persistente"):
        persist = f" · persistente hace {resultado.get('dias_transcurridos', 0)}d"
    return (
        f"🕐 MURO DE LAGS ACTIVO: {resultado['firmas_convergentes']} firmas "
        f"convergen — {cuenta} (ventana {resultado['fecha_inicio']} → "
        f"{resultado['fecha_fin']}){persist} | clases: "
        f"{', '.join(resultado['clases'])}"
    )
