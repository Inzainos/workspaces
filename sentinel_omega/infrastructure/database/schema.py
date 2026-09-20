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
        return init_fn(db_path)
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        logger.warning(
            "DB lock detectado en init_database(%s); usando conexión directa sin DDL",
            db_path,
        )
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
