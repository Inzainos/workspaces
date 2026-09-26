"""Serie viva de Schumann con bandera en vivo / arrastrado.

Regla del Capitán (2026-09-26): si la API de Tomsk no responde, se usa el
último valor bueno hasta que vuelva, sin límite de edad. Pero cada fila dice
de dónde salió, para que el sistema sepa si está en vivo o si la API está
caída:

- ``en_vivo``         1 = llegó de la API en este ciclo; 0 = arrastrado.
- ``ultimo_vivo_ts``  bloque (UTC) del último valor real.
- ``atraso_horas``    horas entre ese valor real y este bloque.

El arrastre solo se toma de filas ``en_vivo=1``. Si se tomara también de las
arrastradas, el valor se alimentaría a sí mismo (así se congelaron 38 bloques
en 8,26 Hz / 21,46 % hasta el 2026-09-26).

Quien use la serie como historia o entrenamiento (volcado al enjambre, cruces,
rasgos del Juez) debe filtrar con :func:`filtro_en_vivo`: un valor arrastrado
no es una medición nueva. Los ONNX siguen recibiendo el mismo vector; la
bandera y el atraso entran como rasgos en el próximo rebuild.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, Optional

TABLA = "tbl_schumann_vivo"
FMT_BLK = "%Y-%m-%d %H:00"

_COLUMNAS_NUEVAS = (
    ("en_vivo", "INTEGER DEFAULT 1"),
    ("ultimo_vivo_ts", "TEXT"),
    ("atraso_horas", "REAL"),
)


def _columnas(conn: sqlite3.Connection) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({TABLA})")}


def asegurar_tabla(conn: sqlite3.Connection) -> None:
    """Crea la tabla o le añade las columnas de bandera. Idempotente.

    Las filas viejas quedan con ``en_vivo=1`` por el DEFAULT.
    """
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLA} ("
        "timestamp_blk TEXT PRIMARY KEY, schumann_hz REAL, "
        "schumann_activity REAL, creada_at TEXT DEFAULT (datetime('now')))"
    )
    cols = _columnas(conn)
    for nombre, tipo in _COLUMNAS_NUEVAS:
        if nombre not in cols:
            conn.execute(f"ALTER TABLE {TABLA} ADD COLUMN {nombre} {tipo}")


def filtro_en_vivo(conn: sqlite3.Connection, alias: str = "") -> str:
    """``" AND COALESCE(en_vivo,1)=1"`` si la columna existe; ``""`` si no.

    Sirve para bases que todavía no pasaron por :func:`asegurar_tabla`.
    """
    try:
        if "en_vivo" in _columnas(conn):
            pref = f"{alias}." if alias else ""
            return f" AND COALESCE({pref}en_vivo,1)=1"
    except sqlite3.Error:
        pass
    return ""


def _as_float(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def es_senal_muerta(hz: Any, act: Any) -> bool:
    """Sin señal: falta un valor, o activity exactamente 0 (el falso clásico)."""
    hz_f, act_f = _as_float(hz), _as_float(act)
    return hz_f is None or act_f is None or act_f == 0.0


def _horas_entre(desde: str, hasta: str) -> float:
    a = datetime.strptime(desde[:16], "%Y-%m-%d %H:%M")
    b = datetime.strptime(hasta[:16], "%Y-%m-%d %H:%M")
    return round((b - a).total_seconds() / 3600.0, 2)


def registrar(
    conn: sqlite3.Connection,
    hz: Any,
    act: Any,
    ahora: Optional[float] = None,
) -> Dict[str, Any]:
    """Guarda la lectura de este ciclo, o el arrastre marcado si no hay señal.

    Devuelve ``{"estado", "timestamp_blk", "schumann_hz", "schumann_activity",
    "en_vivo", "ultimo_vivo_ts", "atraso_horas"}`` con estado ``"en_vivo"``,
    ``"arrastrado"`` o ``"desconocido"`` (la API falla y nunca hubo lectura
    real: no se inventa nada).
    """
    asegurar_tabla(conn)
    ts_blk = time.strftime(FMT_BLK, time.gmtime(time.time() if ahora is None else ahora))

    if not es_senal_muerta(hz, act):
        conn.execute(
            f"INSERT OR REPLACE INTO {TABLA} "
            "(timestamp_blk, schumann_hz, schumann_activity, creada_at, "
            " en_vivo, ultimo_vivo_ts, atraso_horas) "
            "VALUES (?,?,?,datetime('now'),1,?,0)",
            (ts_blk, float(hz), float(act), ts_blk),
        )
        conn.commit()
        return {"estado": "en_vivo", "timestamp_blk": ts_blk,
                "schumann_hz": float(hz), "schumann_activity": float(act),
                "en_vivo": 1, "ultimo_vivo_ts": ts_blk, "atraso_horas": 0.0}

    ult = conn.execute(
        f"SELECT schumann_hz, schumann_activity, timestamp_blk FROM {TABLA} "
        "WHERE COALESCE(en_vivo,1)=1 "
        "AND schumann_hz IS NOT NULL "
        "AND schumann_activity IS NOT NULL AND schumann_activity != 0 "
        "AND timestamp_blk <= ? "
        "ORDER BY timestamp_blk DESC LIMIT 1",
        (ts_blk,),
    ).fetchone()
    if not ult:
        return {"estado": "desconocido", "timestamp_blk": ts_blk,
                "schumann_hz": None, "schumann_activity": None,
                "en_vivo": 0, "ultimo_vivo_ts": None, "atraso_horas": None}

    u_hz, u_act, u_ts = float(ult[0]), float(ult[1]), ult[2]
    if u_ts[:13] == ts_blk[:13]:
        # Ya hay lectura real de esta misma hora (un ciclo anterior): se queda.
        return {"estado": "en_vivo", "timestamp_blk": ts_blk,
                "schumann_hz": u_hz, "schumann_activity": u_act,
                "en_vivo": 1, "ultimo_vivo_ts": u_ts, "atraso_horas": 0.0}

    atraso = _horas_entre(u_ts, ts_blk)
    # Nunca pisa una fila en vivo; sí actualiza un arrastre previo del bloque.
    conn.execute(
        f"INSERT INTO {TABLA} "
        "(timestamp_blk, schumann_hz, schumann_activity, creada_at, "
        " en_vivo, ultimo_vivo_ts, atraso_horas) "
        "VALUES (?,?,?,datetime('now'),0,?,?) "
        "ON CONFLICT(timestamp_blk) DO UPDATE SET "
        " schumann_hz=excluded.schumann_hz, "
        " schumann_activity=excluded.schumann_activity, "
        " ultimo_vivo_ts=excluded.ultimo_vivo_ts, "
        " atraso_horas=excluded.atraso_horas "
        "WHERE COALESCE(en_vivo,1)=0",
        (ts_blk, u_hz, u_act, u_ts, atraso),
    )
    conn.commit()
    return {"estado": "arrastrado", "timestamp_blk": ts_blk,
            "schumann_hz": u_hz, "schumann_activity": u_act,
            "en_vivo": 0, "ultimo_vivo_ts": u_ts, "atraso_horas": atraso}


def estado_actual(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Última fila con su bandera, para Telegram y el dashboard."""
    try:
        if "en_vivo" not in _columnas(conn):
            return {"estado": "sin_bandera"}
        r = conn.execute(
            f"SELECT timestamp_blk, schumann_hz, schumann_activity, "
            f"COALESCE(en_vivo,1), ultimo_vivo_ts, atraso_horas FROM {TABLA} "
            "ORDER BY timestamp_blk DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return {"estado": "sin_tabla"}
    if not r:
        return {"estado": "sin_datos"}
    return {"estado": "en_vivo" if r[3] == 1 else "arrastrado",
            "timestamp_blk": r[0], "schumann_hz": r[1], "schumann_activity": r[2],
            "en_vivo": int(r[3]), "ultimo_vivo_ts": r[4], "atraso_horas": r[5]}
