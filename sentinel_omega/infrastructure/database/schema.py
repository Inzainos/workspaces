"""
Sentinel Omega — SQLite Schema & Migrations
SCHEMA_VERSION = 11 (locf, catalogo, lags via migrate_v11)
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 11

# Full DDL lives in SCHEMA_SQL on repo; v11 tables also applied by migrate_v11.apply_v11
# See sentinel_omega/infrastructure/database/migrate_v11.py for deltas.

def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize or open SQLite DB and ensure schema is up to date."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Import full SCHEMA_SQL from package if present in module body below
    try:
        # Prefer package SCHEMA_SQL constant if defined in this file after rewrite
        from sentinel_omega.infrastructure.database import schema as _self
        sql = getattr(_self, "SCHEMA_SQL", None)
        if sql:
            conn.executescript(sql)
    except Exception as e:
        logger.warning(f"SCHEMA_SQL apply: {e}")

    try:
        from sentinel_omega.infrastructure.database.migrate_v11 import apply_v11
        apply_v11(conn)
    except Exception as e:
        logger.warning(f"migrate_v11: {e}")

    try:
        existing = conn.execute(
            "SELECT version FROM TBL_SCHEMA_VERSION ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if not existing or existing[0] < SCHEMA_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO TBL_SCHEMA_VERSION(version) VALUES(?)",
                (SCHEMA_VERSION,),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.warning(f"schema version stamp: {e}")

    logger.info(f"Database initialized at {db_path} (schema v{SCHEMA_VERSION})")
    return conn


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if not db_path:
        db_path = str(
            Path(__file__).parent.parent.parent / "data" / "SENTINEL_OMEGA_PRO.db"
        )
    return init_database(db_path)
