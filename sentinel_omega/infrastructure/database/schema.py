"""
Sentinel Omega — SQLite Schema & Migrations (v11, self-expanding)

Full DDL lives in schema_parts/*.b64 (zlib+base64).
On import, parts are joined, decompressed, and executed in this module namespace.
"""
from __future__ import annotations

import base64
import logging
import sqlite3
import zlib
from pathlib import Path
from typing import Callable, Optional, cast

logger = logging.getLogger(__name__)

_PARTS_DIR = Path(__file__).resolve().parent / "schema_parts"

def _load_expanded() -> str:
    parts = sorted(_PARTS_DIR.glob("schema_part_*.b64"))
    if not parts:
        raise RuntimeError(f"schema_parts missing under {_PARTS_DIR}")
    b64 = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    return zlib.decompress(base64.b64decode(b64)).decode("utf-8")

_src = _load_expanded()
exec(compile(_src, "schema_expanded", "exec"), globals())


# NOTE:
# El módulo expandido define get_connection() como alias directo de init_database(),
# lo que vuelve a ejecutar migraciones DDL en cada conexión. Si otro proceso tiene
# write-lock (launcher vivo + watchdog/reportes), eso dispara OperationalError
# "database is locked" en llamadas de solo lectura.
#
# Aquí hacemos un wrapper resiliente: intentamos init_database() primero (camino
# normal), y si la DB está bloqueada caemos a una conexión directa con PRAGMAs de
# runtime sin DDL.
_init_database_expanded = globals().get("init_database")


# Cuánto espera una ESCRITURA VIVA por el candado, en segundos.
#
# El defecto de SQLite son 5 s, y no alcanzan. Medido el 2026-09-28 sobre el
# ciclo en producción: SEIS escrituras por ciclo se perdían con «database is
# locked» --- el LOCF de alfa1, beta1, beta2 y delta, la persistencia sísmica y
# la del clima horario --- y las seis son fail-soft, así que el ciclo terminaba
# «bien» y nadie se enteraba. La consecuencia visible: `tbl_clima_espacial_raw`
# dejó de crecer a las 02:00, las ventanas de 336 h y 72 h del Kp se congelaron
# en ese borde, y beta1 devolvió la MISMA confianza (0,3665) doce ciclos
# seguidos. El operador lo vio antes que cualquier alerta: «beta1 se refresca
# pero repite el mismo valor».
#
# La contención no es accidental: `sentinel-omega-rutinas.service` corre cada
# 15 min y tarda ~5, así que se solapa con el ciclo casi siempre.
#
# 120 s es el mismo presupuesto que ya usan los lotes (`entrenamiento.py`,
# `mantenimiento.py`). Un ciclo dura ~300 s, así que esperar cabe; perder el
# dato, no. Es la regla dura 10: un descarte silencioso esconde el fallo
# indefinidamente.
ESPERA_CANDADO_S = 120.0


def _con_espera(conn: sqlite3.Connection) -> sqlite3.Connection:
    """`busy_timeout` en la conexión, venga de donde venga.

    Se pone por PRAGMA y no por `timeout=` del `connect` porque la ruta normal
    devuelve una conexión creada dentro del esquema auto-expandido, donde no se
    puede pasar el argumento.
    """
    try:
        conn.execute(f"PRAGMA busy_timeout={int(ESPERA_CANDADO_S * 1000)}")
    except sqlite3.Error as exc:  # noqa: BLE001 — nunca bloquea el arranque
        logger.warning("No se pudo fijar busy_timeout: %s", exc)
    return conn


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get DB connection with lock-tolerant fallback.

    1) Prefer init_database() to keep forward-only migrations.
    2) If DB is temporarily write-locked, open direct connection and continue.
    """
    if db_path is None:
        db_path = str(
            Path(__file__).parent.parent.parent / "data" / "SENTINEL_OMEGA_PRO.db"
        )
    try:
        if not callable(_init_database_expanded):
            raise RuntimeError("init_database no disponible tras expandir schema")
        init_fn = cast(Callable[[str], sqlite3.Connection], _init_database_expanded)
        return _con_espera(init_fn(db_path))
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        logger.warning(
            "DB lock detectado en init_database(%s); usando conexión directa sin DDL",
            db_path,
        )
        conn = sqlite3.connect(str(db_path), timeout=ESPERA_CANDADO_S)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return _con_espera(conn)
