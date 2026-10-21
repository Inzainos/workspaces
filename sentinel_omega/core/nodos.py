"""Nodos: EL formato canónico de sitio y EL lag restante por señal.

Pedido del operador (2026-10-20): «ya no quiero que me llega solo el número
de los nodos: primero el nombre del sitio, después el número de nodo y su
longitud y latitud, evento detectado y el lag del evento — restándose si la
señal es persistente».

- `sitio_nodo()`: «Tonga-Kermadec (Nodo 26 · 19.9, -175.1)» — UNA sola
  fuente de verdad del formato; alertas, plantillas, reportes y MiniApp
  lo comparten (grep por sitio_nodo).
- `lag_restante_h()`: el COUNTDOWN. El ancla es la PRIMERA detección
  continua de esa (nodo, clase) en el historial del padre — derivada de
  la DB, no de estado en memoria: sobrevive reinicios y no re-proyecta
  desde ahora en cada ciclo (misma disciplina que el muro de lags).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional, Tuple


def sitio_nodo(
    nombre: Optional[str],
    id_nodo,
    lat=None,
    lon=None,
) -> str:
    """«Tlaxcala (Nodo 0 · 19.31, -98.23)» — nombre primero, SIEMPRE.

    Sin nodo: devuelve lo que haya sin inventar (regla 7/8: la ausencia se
    ve, no se disfraza de 'desconocido 0,0').
    """
    if id_nodo is None:
        return str(nombre) if nombre else "—"
    base = f"{nombre} (Nodo {id_nodo}" if nombre else f"Nodo {id_nodo}"
    if lat is None or lon is None:
        return base + ")"
    try:
        return f"{base} · {float(lat):.1f}, {float(lon):.1f})"
    except (TypeError, ValueError):
        return base + ")"


def sitio_nodo_desde_fila(conn: sqlite3.Connection, id_nodo) -> str:
    """El formato completo a partir del node_id, mirando la topología."""
    try:
        row = conn.execute(
            "SELECT nombre, lat, lon FROM TBL_NODOS_TOPOLOGIA "
            "WHERE node_id = ?",
            (id_nodo,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    if not row:
        return f"Nodo {id_nodo}"
    return sitio_nodo(row[0], id_nodo, row[1], row[2])


# ── Countdown del lag ────────────────────────────────────────────────────────
# Ventana máxima (h) hacia atrás en la que una detección sigue contando como
# «la misma señal persistente» si reaparece con huecos de a lo mucho un ciclo
# largo (el Padre corre cada ~2 h con registro en el Juez).
_HUECO_MAX_H = 4.0


def lag_restante_h(
    conn: sqlite3.Connection,
    *,
    ventana_tipica_h: Optional[float],
    ahora_ts: float,
    id_nodo=None,
    event_class: str = "",
    timestamp_actual: float = 0.0,
) -> Tuple[Optional[float], Optional[float]]:
    """(lag_restante_h, ancla_ts) del evento que esta señal anuncia.

    El ancla: la detección continua MÁS ANTIGUA de la misma (nodo, clase)
    en el registro del padre (`TBL_JUEZ_AUDITORIA`, bot_name='padre',
    detalles_json → firma_matches). Con el ancla fija, el lag RESTA con el
    paso del reloj aunque la señal reaparezca cada ciclo — «restandose si
    la señal es persistente». Negativo = ventana vencida (se reporta tal
    cual: la ventana pasó y no hubo evento, eso es información).

    Sin ventana típica medida o sin historial del padre → (None, None):
    NO se inventa countdown (regla 7/8).
    """
    if ventana_tipica_h is None or ventana_tipica_h <= 0:
        return None, None

    ancla: Optional[float] = None
    if id_nodo is not None and event_class:
        filas = conn.execute(
            "SELECT timestamp, detalles_json FROM TBL_JUEZ_AUDITORIA "
            "WHERE bot_name = 'padre' AND detalles_json LIKE '%firma_matches%' "
            "  AND timestamp >= ? ORDER BY timestamp ASC",
            (ahora_ts - ventana_tipica_h / 24.0 * 86400.0 * 2.0
             - _HUECO_MAX_H * 3600.0,),
        ).fetchall()
        ultimo_visto: Optional[float] = None
        for ts, dj in filas:
            try:
                det = json.loads(dj or "{}")
            except json.JSONDecodeError:
                continue
            for m in det.get("firma_matches", []):
                if m.get("id_nodo") == id_nodo and \
                        str(m.get("event_class", "")) == str(event_class):
                    if ultimo_visto is None or \
                            ts - ultimo_visto <= _HUECO_MAX_H * 3600.0:
                        ancla = ts if ancla is None else min(ancla, ts)
                        ultimo_visto = ts
                    else:  # hueco: la señal anterior ya no es «continua»
                        ancla = ts
                        ultimo_visto = ts
    if ancla is None:
        # Señal sin historial continuo previo: el ancla es AHORA —
        # primera vez que la vemos, el countdown nace de su ventana.
        ancla = float(timestamp_actual) if timestamp_actual else ahora_ts
    restante = float(ventana_tipica_h) - (ahora_ts - ancla) / 3600.0
    return restante, ancla


def formato_lag(lag_h: Optional[float]) -> str:
    """«~132 h (5.5 d)» o «vencida hace 6 h» o «—» si no hay dato."""
    if lag_h is None:
        return "—"
    if lag_h >= 0:
        d = lag_h / 24.0
        return f"~{lag_h:.0f} h ({d:.1f} d)" if d >= 1 else f"~{lag_h:.0f} h"
    return f"ventana vencida hace {abs(lag_h):.0f} h"
