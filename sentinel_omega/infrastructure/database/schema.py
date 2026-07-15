"""
Sentinel Omega — SQLite Schema & Migrations

Tables (from base_geo.docx architecture):
  TBL_PRECURSORES_COSMICOS — Cosmic/geophysical precursor snapshots per cycle
  TBL_NODOS_TOPOLOGIA      — 125-node N-Body topology (real + ghost + geobatteries)
  TBL_HISTORICO_SISMICO     — Historical seismic catalog (USGS ingest)
  TBL_DETECCIONES           — Precursor detections from scanner
  TBL_CICLOS                — Orchestrator cycle log with consensus + risk
  TBL_MURO_EVENTOS          — Muro de los 5 Eventos breach history

v5 additions:
  tbl_cobertura_satelital  — Cobertura satelital alfa2 (ESA Sentinel) por ciclo;
                             permite que alfa2 acumule firmas desde datos en vivo.
  tbl_delta_cross          — Resultados de correlación cruzada delta_enriched por ciclo.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 6

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
-- Composite: covers the barrido_diario collapse query (timestamp + tipo + wall_name)
CREATE INDEX IF NOT EXISTS idx_detecciones_colapso
    ON TBL_DETECCIONES(timestamp, tipo, wall_name);

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
-- Composite: covers barrido_diario DELETE (muro_breach=0 AND nivel_riesgo NOT IN ...)
CREATE INDEX IF NOT EXISTS idx_ciclos_barrido
    ON TBL_CICLOS(timestamp, muro_breach, nivel_riesgo);

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
-- Index for magnitude filter used heavily in training and sesgo evaluation
CREATE INDEX IF NOT EXISTS idx_sismico_raw_mag
    ON tbl_historico_sismico_raw(sismo_max_mag);

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
-- Composite: covers common queries (bot_name + estado) used in firmas lookups
CREATE INDEX IF NOT EXISTS idx_firmas_bot_estado ON TBL_FIRMAS(bot_name, estado);
-- Composite HOT PATH: FirmaMemoria.registrar() filtra por (bot_name, event_class)
-- en CADA evento del entrenamiento. Sin este índice, SQLite trae todas las
-- firmas del bot y filtra la clase a mano (para el Padre son miles de filas por
-- evento) — es el costo que crece a medida que la memoria engorda. Con el
-- compuesto salta directo al bucket exacto.
CREATE INDEX IF NOT EXISTS idx_firmas_bot_class ON TBL_FIRMAS(bot_name, event_class);

-- ─── Normalización 1NF: eventos de cada firma (tabla hija) ────────
-- El array `eventos_json` de TBL_FIRMAS era un grupo repetido (viola 1NF) y
-- se reescribía ENTERO en cada recurrencia — costo O(n²) (la firma más
-- recurrente llegó a 774 KB reescritos 24,719 veces). Aquí cada avistamiento
-- es una FILA: append O(1), MIN(ts) por índice, muestra por LIMIT. La columna
-- eventos_json queda como legado (se llena la hija y se deja de reescribir).
CREATE TABLE IF NOT EXISTS tbl_firma_eventos (
    firma_id    INTEGER NOT NULL,
    evento_ref  TEXT    NOT NULL,
    ts_evento   TEXT,
    orden       INTEGER,
    PRIMARY KEY (firma_id, evento_ref),
    FOREIGN KEY (firma_id) REFERENCES TBL_FIRMAS(firma_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_firma_eventos_fid
    ON tbl_firma_eventos(firma_id, ts_evento);

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
    fase            TEXT    DEFAULT 'viva',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_juez_bot ON TBL_JUEZ_AUDITORIA(bot_name);
CREATE INDEX IF NOT EXISTS idx_juez_resultado ON TBL_JUEZ_AUDITORIA(resultado);
CREATE INDEX IF NOT EXISTS idx_juez_ts ON TBL_JUEZ_AUDITORIA(timestamp);
-- El índice idx_juez_fase y la vista viva_real se crean en init_database
-- DESPUÉS de la migración (la columna fase puede no existir aún en DBs viejas).

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

-- ─── Cobertura Satelital alfa2 (v5) ───────────────────────────────
-- Almacena métricas de cobertura ESA Sentinel por ciclo por zona.
-- Permite que alfa2 acumule firmas históricas a partir de datos en vivo
-- (no hay backcast satelital de 14 años, así que alfa2 entrena desde hoy).
CREATE TABLE IF NOT EXISTS tbl_cobertura_satelital (
    timestamp_blk        TEXT    NOT NULL,
    zona                 TEXT    NOT NULL,
    coverage_score       REAL    DEFAULT 0.0,    -- cobertura compuesta [0,1]
    thermal_anomalies    INTEGER DEFAULT 0,       -- conteo de anomalías térmicas
    clear_passes         INTEGER DEFAULT 0,       -- pases sin nube
    total_passes         INTEGER DEFAULT 0,       -- pases totales
    revisit_days         REAL    DEFAULT 0.0,     -- promedio días entre revisitas
    PRIMARY KEY (timestamp_blk, zona)
);
CREATE INDEX IF NOT EXISTS idx_cobertura_ts
    ON tbl_cobertura_satelital(timestamp_blk);

-- ─── Correlación cruzada delta_enriched (v5) ──────────────────────
-- Resultados del pipeline delta_enriched (geofísica ↔ financiero).
-- Una fila por ciclo con los scores de acoplamiento.
CREATE TABLE IF NOT EXISTS tbl_delta_cross (
    timestamp_blk            TEXT    PRIMARY KEY,
    cross_coupling           REAL    DEFAULT 0.0,
    geomagnetic_coupling     REAL    DEFAULT 0.0,
    schumann_coupling        REAL    DEFAULT 0.0,
    sentiment_coupling       REAL    DEFAULT 0.0,
    composite_score          REAL    DEFAULT 0.0,
    regime_label             TEXT    DEFAULT '',
    confidence               REAL    DEFAULT 0.0,
    data_completeness        REAL    DEFAULT 0.0,
    geo_kp_max_3d            REAL,
    geo_storm_active         INTEGER DEFAULT 0,
    geo_schumann_deviation   REAL
);

-- ─── Eventos No Sísmicos (volcánicos + tormentas solares) ────────
-- Catálogo derivado de tbl_desgasificacion_raw (VEI≥3) y
-- tbl_clima_espacial_raw (Kp≥6 onset). Alimenta el entrenamiento
-- multi-evento para que los bots aprendan firmas de erupciones y
-- tormentas solares, no solo sismos.
CREATE TABLE IF NOT EXISTS tbl_eventos_no_sismicos (
    timestamp_blk TEXT    NOT NULL,
    id_nodo       INTEGER NOT NULL,
    event_class   TEXT    NOT NULL,
    fuente        TEXT    DEFAULT '',
    intensidad    REAL    DEFAULT 0.0,
    PRIMARY KEY (timestamp_blk, id_nodo, event_class)
);
CREATE INDEX IF NOT EXISTS idx_eventos_no_sismicos_class
    ON tbl_eventos_no_sismicos(event_class);
CREATE INDEX IF NOT EXISTS idx_eventos_no_sismicos_ts
    ON tbl_eventos_no_sismicos(timestamp_blk);

-- ─── Patrones de correlación (mapa de calor) ──────────────────
-- Matriz feature × event_class calculada tras el entrenamiento.
-- Para cada par (tipo_evento, variable), guarda el valor medio de
-- esa variable en las firmas de ese tipo y cuántas veces supera
-- (ratio) el promedio global. ratio > 1 = la variable está elevada
-- antes de ese tipo de evento.
CREATE TABLE IF NOT EXISTS tbl_patrones_correlacion (
    event_class   TEXT    NOT NULL,
    feature       TEXT    NOT NULL,
    media         REAL    DEFAULT 0.0,
    global_media  REAL    DEFAULT 0.0,
    ratio         REAL    DEFAULT 1.0,
    n_firmas      INTEGER DEFAULT 0,
    updated_at    TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (event_class, feature)
);
CREATE INDEX IF NOT EXISTS idx_patrones_corr_class
    ON tbl_patrones_correlacion(event_class);

-- ─── Cimática: snapshot de patrones de telemetría ─────────────────
-- Cada ciclo toma un snapshot del sistema (huella discretizada de la
-- telemetría). Si el patrón es NUEVO se guarda la telemetría completa;
-- si ya existe solo se suma +1 a su frecuencia. Con el tiempo la
-- frecuencia distingue la cimática consistente (por nodo o general)
-- asociada a cada tipo de evento. Todo registro/actualización dispara
-- la revisión del Padre (trigger en Python, no en SQL).
CREATE TABLE IF NOT EXISTS tbl_cimatica_patrones (
    patron_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    clave           TEXT    NOT NULL,
    ambito          TEXT    NOT NULL DEFAULT 'general'
                    CHECK(ambito IN ('general','nodo')),
    id_nodo         INTEGER,
    event_class     TEXT,
    telemetria_json TEXT    NOT NULL DEFAULT '{}',
    frecuencia      INTEGER NOT NULL DEFAULT 1,
    primera_vez     TEXT    DEFAULT (datetime('now')),
    ultima_vez      TEXT    DEFAULT (datetime('now')),
    UNIQUE(clave, ambito, id_nodo)
);
CREATE INDEX IF NOT EXISTS idx_cimatica_clave
    ON tbl_cimatica_patrones(clave);
CREATE INDEX IF NOT EXISTS idx_cimatica_frecuencia
    ON tbl_cimatica_patrones(frecuencia DESC);

-- ─── Correo de salida (sin Telegram) ──────────────────────────────
-- Outbox de alertas y reportes por email. El envío real usa SMTP con
-- credenciales por variables de entorno; sin credenciales el correo
-- queda PENDIENTE (fail-soft, nunca se pierde ni se finge enviado).
CREATE TABLE IF NOT EXISTS tbl_correo_salida (
    correo_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    destinatario  TEXT    NOT NULL DEFAULT 'elan.zainos.corona@gmail.com',
    tipo          TEXT    NOT NULL DEFAULT 'ALERTA'
                  CHECK(tipo IN ('ALERTA','REPORTE')),
    asunto        TEXT    NOT NULL,
    cuerpo        TEXT    NOT NULL,
    adjuntos_json TEXT    DEFAULT '[]',
    estado        TEXT    NOT NULL DEFAULT 'PENDIENTE'
                  CHECK(estado IN ('PENDIENTE','ENVIADO','FALLIDO')),
    intentos      INTEGER DEFAULT 0,
    creado_at     TEXT    DEFAULT (datetime('now')),
    enviado_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_correo_estado
    ON tbl_correo_salida(estado);

-- ─── Schumann en vivo (serie acumulada, no hay backcast) ──────────
-- La resonancia Schumann de Tomsk se mide por WPC (White Pixel Count =
-- "conteo de bits en blanco" del espectrograma) en CADA corrida de 2 h, en
-- tiempo real cuando el Padre corre. No existe backcast de 30 años, así que
-- —igual que alfa2— la serie se ACUMULA en vivo aquí y con el tiempo alimenta
-- los cruces (dominio SCHUMANN del orden de precursores) cuando ya hay datos.
CREATE TABLE IF NOT EXISTS tbl_schumann_vivo (
    timestamp_blk     TEXT PRIMARY KEY,
    schumann_hz       REAL,
    schumann_activity REAL,       -- % de excitación medido (WPC)
    creada_at         TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_schumann_vivo_ts
    ON tbl_schumann_vivo(timestamp_blk);

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
    "TBL_FIRMAS": {
        # Per-signature anticipation: this firma's own typical lead time
        "lag_promedio_h": "REAL",
        "lag_n": "INTEGER DEFAULT 0",
    },
    # v6: fase ESTRICTA de auditoría (columna real, no dentro del JSON).
    # 'viva' = predicción en operación (la única que cuenta para asertividad
    # viva); 'reconocimiento'/'backtest'/'observacion' = entrenamiento.
    "TBL_JUEZ_AUDITORIA": {
        "fase": "TEXT DEFAULT 'viva'",
    },
    # v5: cobertura satelital — nueva tabla (creada por SCHEMA_SQL con IF NOT EXISTS;
    # se incluye aquí para que _migrate_add_missing_columns no falle en DBs antiguas
    # que no tengan la tabla — el try/except la ignora si no existe aún).
    "tbl_cobertura_satelital": {
        "coverage_score": "REAL DEFAULT 0.0",
        "thermal_anomalies": "INTEGER DEFAULT 0",
        "clear_passes": "INTEGER DEFAULT 0",
        "total_passes": "INTEGER DEFAULT 0",
        "revisit_days": "REAL DEFAULT 0.0",
    },
    "tbl_delta_cross": {
        "cross_coupling": "REAL DEFAULT 0.0",
        "geomagnetic_coupling": "REAL DEFAULT 0.0",
        "schumann_coupling": "REAL DEFAULT 0.0",
        "sentiment_coupling": "REAL DEFAULT 0.0",
        "composite_score": "REAL DEFAULT 0.0",
        "regime_label": "TEXT DEFAULT ''",
        "confidence": "REAL DEFAULT 0.0",
        "data_completeness": "REAL DEFAULT 0.0",
        "geo_kp_max_3d": "REAL",
        "geo_storm_active": "INTEGER DEFAULT 0",
        "geo_schumann_deviation": "REAL",
    },
    # v6: eventos no sísmicos y matriz de correlaciones
    "tbl_eventos_no_sismicos": {
        "fuente": "TEXT DEFAULT ''",
        "intensidad": "REAL DEFAULT 0.0",
    },
    "tbl_patrones_correlacion": {
        "media": "REAL DEFAULT 0.0",
        "global_media": "REAL DEFAULT 0.0",
        "ratio": "REAL DEFAULT 1.0",
        "n_firmas": "INTEGER DEFAULT 0",
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
                # Backfill de fase (v6): las filas viejas traen la fase dentro
                # del JSON; reclasificarlas para que el DEFAULT 'viva' no
                # contamine la vara viva con filas de entrenamiento.
                if table == "TBL_JUEZ_AUDITORIA" and col_name == "fase":
                    for tag in ("backtest", "reconocimiento", "observacion"):
                        conn.execute(
                            "UPDATE TBL_JUEZ_AUDITORIA SET fase = ? "
                            "WHERE detalles_json LIKE ?",
                            (tag, f'%"fase": "{tag}"%'),
                        )
                    logger.info("Migration: TBL_JUEZ_AUDITORIA.fase backfilled")
    conn.commit()


def _migrate_firma_eventos(conn: sqlite3.Connection) -> None:
    """Normaliza el array legado eventos_json → tabla hija tbl_firma_eventos.

    Idempotente y no destructivo del dato: rellena la hija para las firmas que
    aún no tienen filas, luego vacía eventos_json (la hija pasa a ser la fuente
    de verdad). El espacio de los arrays viejos se recupera con VACUUM aparte.
    """
    try:
        pendientes = conn.execute(
            "SELECT firma_id, eventos_json FROM TBL_FIRMAS "
            "WHERE eventos_json IS NOT NULL AND eventos_json != '[]'"
        ).fetchall()
    except sqlite3.OperationalError:
        return  # tabla aún no existe

    # Solo se conserva una MUESTRA de eventos por firma (el conteo fiel vive
    # en recurrencia). Importar CAP aquí evita duplicar la constante.
    from sentinel_omega.core.firmas.signature_engine import CAP_EVENTOS_MUESTRA

    migradas = 0
    for fid, evs in pendientes:
        ya = conn.execute(
            "SELECT 1 FROM tbl_firma_eventos WHERE firma_id = ? LIMIT 1", (fid,)
        ).fetchone()
        if ya:
            continue
        try:
            refs = json.loads(evs)
        except (ValueError, TypeError):
            continue
        muestra = refs[:CAP_EVENTOS_MUESTRA]   # los primeros = los más viejos
        conn.executemany(
            "INSERT OR IGNORE INTO tbl_firma_eventos "
            "(firma_id, evento_ref, ts_evento, orden) VALUES (?, ?, ?, ?)",
            [(fid, ref, ref.split("|")[0] if "|" in ref else None, i + 1)
             for i, ref in enumerate(muestra)],
        )
        conn.execute(
            "UPDATE TBL_FIRMAS SET eventos_json = '[]' WHERE firma_id = ?", (fid,)
        )
        migradas += 1
    if migradas:
        conn.commit()
        logger.info(f"Migración 1NF: {migradas} firmas normalizadas (muestra "
                    f"de {CAP_EVENTOS_MUESTRA} + conteo en recurrencia)")
        # Recuperar el espacio en disco de los arrays viejos (best-effort:
        # VACUUM necesita ~tamaño de la base libre; si no hay, se omite sin
        # romper el arranque).
        try:
            conn.execute("VACUUM")
            logger.info("Migración 1NF: VACUUM completado — disco recuperado")
        except sqlite3.OperationalError as e:
            logger.warning(f"Migración 1NF: VACUUM omitido ({e})")


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize database with full schema. Idempotent (IF NOT EXISTS)."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")   # safe with WAL; faster than FULL
    conn.execute("PRAGMA cache_size=-8000")      # 8 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")     # temp tables/indexes in RAM

    conn.executescript(SCHEMA_SQL)
    _migrate_add_missing_columns(conn)
    _migrate_firma_eventos(conn)   # normaliza eventos_json → tabla hija (1NF)

    # Post-migración (la columna fase ya existe seguro): índice + vista
    # canónica de la operación viva. viva_real es la ÚNICA vara para la
    # asertividad viva — jamás incluye filas de entrenamiento.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_juez_fase ON TBL_JUEZ_AUDITORIA(fase)"
    )
    conn.execute("DROP VIEW IF EXISTS viva_real")
    conn.execute(
        "CREATE VIEW viva_real AS "
        "SELECT * FROM TBL_JUEZ_AUDITORIA WHERE fase = 'viva'"
    )

    # Vista de compatibilidad: reconstruye la forma vieja `eventos_json` a
    # partir de la tabla hija normalizada tbl_firma_eventos. Cualquier código
    # o reporte que quiera el array completo lo obtiene aquí, sin que la tabla
    # base cargue el grupo repetido.
    conn.execute("DROP VIEW IF EXISTS v_firma_eventos_json")
    conn.execute(
        "CREATE VIEW v_firma_eventos_json AS "
        "SELECT firma_id, json_group_array(evento_ref) AS eventos_json, "
        "MIN(ts_evento) AS ts_primero, COUNT(*) AS n_eventos "
        "FROM tbl_firma_eventos GROUP BY firma_id"
    )
    conn.commit()

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
