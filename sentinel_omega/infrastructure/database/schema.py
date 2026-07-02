"""
Sentinel Omega — SQLite Schema & Migrations

Tables (from base_geo.docx architecture):
  TBL_PRECURSORES_COSMICOS — Cosmic/geophysical precursor snapshots per cycle
  TBL_NODOS_TOPOLOGIA      — 125-node N-Body topology (real + ghost + geobatteries)
  TBL_HISTORICO_SISMICO     — Historical seismic catalog (USGS ingest)
  TBL_DETECCIONES           — Precursor detections from scanner
  TBL_CICLOS                — Orchestrator cycle log with consensus + risk
  TBL_MURO_EVENTOS          — Muro de los 5 Eventos breach history
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4

SCHEMA_SQL = """
-- ─── Precursores Cósmicos ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_PRECURSORES_COSMICOS (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    bz_nT           REAL    DEFAULT 0.0,
    viento_km_s     REAL    DEFAULT 0.0,
    protones        REAL    DEFAULT 0.0,
    kp              REAL    DEFAULT 0.0,
    lod_ms          REAL    DEFAULT 0.0,
    schumann_hz     REAL    DEFAULT 7.83,
    schumann_activity REAL  DEFAULT 0.0,
    fase_lunar      REAL    DEFAULT 0.0,
    presion_hpa     REAL    DEFAULT 1013.0,
    fantasma        REAL    DEFAULT 0.0,
    nivel_riesgo    TEXT    DEFAULT 'LOW',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_precursores_ts
    ON TBL_PRECURSORES_COSMICOS(timestamp);
CREATE INDEX IF NOT EXISTS idx_precursores_riesgo
    ON TBL_PRECURSORES_COSMICOS(nivel_riesgo);

-- ─── Nodos Topología (125 nodos N-Body) ────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_NODOS_TOPOLOGIA (
    node_id                 INTEGER PRIMARY KEY,
    nombre                  TEXT    NOT NULL,
    lat                     REAL    NOT NULL,
    lon                     REAL    NOT NULL,
    tipo                    TEXT    NOT NULL CHECK(tipo IN ('real', 'ghost', 'geobattery')),
    conductividad_telurica  REAL    DEFAULT 0.0,
    energia_acumulada       REAL    DEFAULT 0.0,
    saturacion              REAL    DEFAULT 0.0,
    region                  TEXT    DEFAULT '',
    activo                  INTEGER DEFAULT 1,
    updated_at              TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_nodos_tipo
    ON TBL_NODOS_TOPOLOGIA(tipo);
CREATE INDEX IF NOT EXISTS idx_nodos_region
    ON TBL_NODOS_TOPOLOGIA(region);

-- Trigger: cap saturation at 1.0
CREATE TRIGGER IF NOT EXISTS trg_nodo_saturacion
    AFTER UPDATE OF saturacion ON TBL_NODOS_TOPOLOGIA
    WHEN NEW.saturacion > 1.0
BEGIN
    UPDATE TBL_NODOS_TOPOLOGIA SET saturacion = 1.0 WHERE node_id = NEW.node_id;
END;

-- ─── Histórico Sísmico ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_HISTORICO_SISMICO (
    event_id        TEXT    PRIMARY KEY,
    timestamp       REAL    NOT NULL,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    depth_km        REAL    DEFAULT 0.0,
    magnitude       REAL    NOT NULL,
    mag_type        TEXT    DEFAULT '',
    region          TEXT    DEFAULT '',
    source          TEXT    DEFAULT 'USGS',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sismico_ts
    ON TBL_HISTORICO_SISMICO(timestamp);
CREATE INDEX IF NOT EXISTS idx_sismico_mag
    ON TBL_HISTORICO_SISMICO(magnitude);
CREATE INDEX IF NOT EXISTS idx_sismico_region
    ON TBL_HISTORICO_SISMICO(region);

-- ─── Detecciones de Precursores ────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_DETECCIONES (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    cycle_id        INTEGER,
    tipo            TEXT    NOT NULL,
    display_name    TEXT    NOT NULL,
    station         TEXT    DEFAULT '',
    lat             REAL,
    lon             REAL,
    confidence      REAL    NOT NULL,
    values_json     TEXT    DEFAULT '{}',
    wall_name       TEXT    DEFAULT '',
    created_at      TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (cycle_id) REFERENCES TBL_CICLOS(id)
);

CREATE INDEX IF NOT EXISTS idx_detecciones_ts
    ON TBL_DETECCIONES(timestamp);
CREATE INDEX IF NOT EXISTS idx_detecciones_tipo
    ON TBL_DETECCIONES(tipo);
CREATE INDEX IF NOT EXISTS idx_detecciones_cycle
    ON TBL_DETECCIONES(cycle_id);

-- ─── Ciclos del Orquestador ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_CICLOS (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           REAL    NOT NULL,
    geo_signal          TEXT    DEFAULT 'no_signal',
    geo_confidence      REAL    DEFAULT 0.0,
    geo_consensus       INTEGER DEFAULT 0,
    fantasma            REAL    DEFAULT 0.0,
    nivel_riesgo        TEXT    DEFAULT 'LOW',
    precursors_count    INTEGER DEFAULT 0,
    precursor_types     TEXT    DEFAULT '[]',
    muro_walls_active   INTEGER DEFAULT 0,
    muro_breach         INTEGER DEFAULT 0,
    alerts_dispatched   INTEGER DEFAULT 0,
    created_at          TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ciclos_ts
    ON TBL_CICLOS(timestamp);

-- ─── Muro de los 5 Eventos ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_MURO_EVENTOS (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           REAL    NOT NULL,
    cycle_id            INTEGER,
    walls_active        INTEGER NOT NULL,
    total_walls         INTEGER DEFAULT 5,
    correlation_score   REAL    DEFAULT 0.0,
    muro_breach         INTEGER DEFAULT 0,
    risk_label          TEXT    DEFAULT 'NORMAL',
    wall_geofisico      INTEGER DEFAULT 0,
    wall_atmosferico    INTEGER DEFAULT 0,
    wall_oceanico       INTEGER DEFAULT 0,
    wall_solar          INTEGER DEFAULT 0,
    wall_financiero     INTEGER DEFAULT 0,
    active_types_json   TEXT    DEFAULT '[]',
    created_at          TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (cycle_id) REFERENCES TBL_CICLOS(id)
);

CREATE INDEX IF NOT EXISTS idx_muro_ts
    ON TBL_MURO_EVENTOS(timestamp);
CREATE INDEX IF NOT EXISTS idx_muro_breach
    ON TBL_MURO_EVENTOS(muro_breach);

-- ─── Historical Backcast Tables (1H resolution) ──────────────────
CREATE TABLE IF NOT EXISTS tbl_clima_espacial_raw (
    timestamp_blk    TEXT PRIMARY KEY,
    bz_promedio     REAL,
    bz_derivada     REAL,
    bz_min          REAL,
    bz_max          REAL,
    viento_solar_avg REAL,
    viento_solar_max REAL,
    kp_max          REAL,
    kp_promedio     REAL,
    proton_flux_10mev REAL
);

CREATE TABLE IF NOT EXISTS tbl_astronomia_cinematica (
    timestamp_blk        TEXT PRIMARY KEY,
    lod_ms              REAL DEFAULT 0.0,
    fase_lunar_pct      REAL DEFAULT 0.0,
    distancia_lunar_km  REAL DEFAULT 384400.0,
    es_sicigia          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tbl_historico_sismico_raw (
    timestamp_blk    TEXT NOT NULL,
    id_nodo         INTEGER NOT NULL,
    sismo_count     INTEGER DEFAULT 0,
    sismo_max_mag   REAL DEFAULT 0.0,
    PRIMARY KEY (timestamp_blk, id_nodo)
);

CREATE TABLE IF NOT EXISTS tbl_psique_financiera (
    timestamp_blk    TEXT PRIMARY KEY,
    btc_precio_usd  REAL,
    volatilidad_24h REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS tbl_enjambre_telemetria (
    timestamp_blk    TEXT NOT NULL,
    id_nodo         INTEGER NOT NULL,
    schumann_hz     REAL DEFAULT 7.83,
    PRIMARY KEY (timestamp_blk, id_nodo)
);

CREATE TABLE IF NOT EXISTS tbl_desgasificacion_raw (
    timestamp_blk    TEXT NOT NULL,
    id_nodo         INTEGER NOT NULL,
    volcan          TEXT NOT NULL DEFAULT '',
    tipo_erupcion   TEXT DEFAULT '',
    vei             REAL,
    so2_kt          REAL DEFAULT 0.0,
    PRIMARY KEY (timestamp_blk, id_nodo, volcan)
);

CREATE TABLE IF NOT EXISTS tbl_nodo_estado_dinamico (
    timestamp_blk            TEXT NOT NULL,
    id_nodo                 INTEGER NOT NULL,
    carga_tension_actual    REAL DEFAULT 0.0,
    PRIMARY KEY (timestamp_blk, id_nodo)
);

CREATE TRIGGER IF NOT EXISTS trg_procesar_saturacion
    AFTER UPDATE OF carga_tension_actual ON tbl_nodo_estado_dinamico
    WHEN NEW.carga_tension_actual > 1.0
BEGIN
    UPDATE tbl_nodo_estado_dinamico
    SET carga_tension_actual = 1.0
    WHERE timestamp_blk = NEW.timestamp_blk AND id_nodo = NEW.id_nodo;
END;

-- ─── Firmas (memoria de patrones por bot) ────────────────────────
-- Cada bot mantiene firmas aprendidas del histórico. Estado epistemológico:
-- nueva -> observada -> recurrente -> consolidada (por recurrencia).
-- Solo las consolidadas son conocimiento exigible (castigable por el Juez).
CREATE TABLE IF NOT EXISTS TBL_FIRMAS (
    firma_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_name        TEXT    NOT NULL,
    event_class     TEXT    NOT NULL,
    id_nodo         INTEGER,
    features_json   TEXT    NOT NULL,
    ventana_horas   INTEGER DEFAULT 336,
    recurrencia     INTEGER DEFAULT 1,
    estado          TEXT    DEFAULT 'nueva'
                    CHECK(estado IN ('nueva','observada','recurrente','consolidada')),
    primera_vista   TEXT,
    ultima_vista    TEXT,
    eventos_json    TEXT    DEFAULT '[]',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_firmas_bot ON TBL_FIRMAS(bot_name);
CREATE INDEX IF NOT EXISTS idx_firmas_estado ON TBL_FIRMAS(estado);
CREATE INDEX IF NOT EXISTS idx_firmas_class ON TBL_FIRMAS(event_class);

-- ─── Juez (auditoría disciplinaria, separado del Padre) ──────────
CREATE TABLE IF NOT EXISTS TBL_JUEZ_AUDITORIA (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    bot_name        TEXT    NOT NULL,
    prediccion      TEXT    NOT NULL,
    confianza       REAL    DEFAULT 0.0,
    ventana_h       INTEGER DEFAULT 72,
    verdad          TEXT    DEFAULT '',
    resultado       TEXT    DEFAULT 'PENDIENTE'
                    CHECK(resultado IN ('PENDIENTE','ACIERTO','FALLO','FALSO_POSITIVO')),
    severidad       REAL    DEFAULT 0.0,
    reincidencia    INTEGER DEFAULT 0,
    detalles_json   TEXT    DEFAULT '{}',
    resuelto_at     TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_juez_bot ON TBL_JUEZ_AUDITORIA(bot_name);
CREATE INDEX IF NOT EXISTS idx_juez_resultado ON TBL_JUEZ_AUDITORIA(resultado);
CREATE INDEX IF NOT EXISTS idx_juez_ts ON TBL_JUEZ_AUDITORIA(timestamp);

-- ─── Pesos de credibilidad por bot (ajustados por el castigo) ─────
-- El Padre pondera cada bot en el consenso con su peso. La Fase 2 del
-- entrenamiento castiga (hijo x1, Padre x2) o refuerza estos pesos.
CREATE TABLE IF NOT EXISTS TBL_PESOS_BOTS (
    bot_name        TEXT    PRIMARY KEY,
    peso            REAL    DEFAULT 1.0,
    aciertos        INTEGER DEFAULT 0,
    fallos          INTEGER DEFAULT 0,
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- ─── Schema Version ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_SCHEMA_VERSION (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT    DEFAULT (datetime('now'))
);
"""


# Columns expected per operational table. Used to migrate older databases
# created before a column was added (CREATE TABLE IF NOT EXISTS never alters
# an existing table, so new columns must be added explicitly).
EXPECTED_COLUMNS = {
    "TBL_CICLOS": {
        "precursor_types": "TEXT DEFAULT '[]'",
    },
}


def _migrate_add_missing_columns(conn: sqlite3.Connection) -> None:
    """Add any columns missing from existing tables (forward-only migration)."""
    for table, columns in EXPECTED_COLUMNS.items():
        try:
            existing_cols = {
                row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
        except sqlite3.OperationalError:
            continue  # table doesn't exist yet; executescript will create it
        if not existing_cols:
            continue
        for col_name, col_def in columns.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                logger.info(f"Migration: added {table}.{col_name}")
    conn.commit()


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize database with full schema. Idempotent (IF NOT EXISTS)."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript(SCHEMA_SQL)
    _migrate_add_missing_columns(conn)

    existing = conn.execute(
        "SELECT version FROM TBL_SCHEMA_VERSION ORDER BY version DESC LIMIT 1"
    ).fetchone()

    if not existing or existing[0] < SCHEMA_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO TBL_SCHEMA_VERSION(version) VALUES(?)",
            (SCHEMA_VERSION,),
        )
        conn.commit()
        logger.info(f"Database initialized at {db_path} (schema v{SCHEMA_VERSION})")
    else:
        logger.info(f"Database at {db_path} already at schema v{existing[0]}")

    return conn


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get or create connection to the Sentinel Omega database."""
    if db_path is None:
        db_path = str(
            Path(__file__).parent.parent.parent / "data" / "SENTINEL_OMEGA_PRO.db"
        )
    return init_database(db_path)
