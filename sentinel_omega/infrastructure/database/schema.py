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

SCHEMA_VERSION = 11

SCHEMA_SQL = """
-- ─── Precursores Cósmicos ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TBL_PRECURSORES_COSMICOS (
