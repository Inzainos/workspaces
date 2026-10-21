"""Puerto de localización de la DB — UNA sola fuente de verdad.

Historia (2026-10-20, ítem 2 del plan de mejoras con la biblioteca
~/conocimiento — Cosmic Python, dependency inversion): la ruta canónica
vivía repetida como default hardcodeado en tres módulos (dashboard api,
consenso_vigilante, orchestrator). El bug del 10-19 nació justo de eso:
el orquestador inventó `config.database_path` porque no había un puerto
común, y la alerta de fulguración no despachó nunca.

Contrato:
- `SENTINEL_DB` gana (tests y overrides).
- Si no, la DB de producción.
- Si no existe, la del árbol que contiene este paquete (dev checkout),
  PERO nunca una bajo workspaces-dev salvo que SENTINEL_DB lo diga
  explícitamente: una sesión de dev leyendo la DB de dev sin querer es
  el falso "todo funciona" clásico (CLAUDE.md, reglas del tablero).

Read-only por diseño: los consumidores de mensajería/orquestación abren
SIEMPRE con `abrir_readonly()` (URI mode=ro) — nunca escribir por aquí.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_PROD = Path("/home/deamon/workspaces/sentinel_omega/data/SENTINEL_OMEGA_PRO.db")
# .../sentinel_omega/infrastructure/database/ruta_db.py → package raíz
_PKG_ROOT = Path(__file__).resolve().parents[2]


def ruta_db_canonica() -> Path:
    """La ruta a la DB operativa: SENTINEL_DB → prod → árbol actual."""
    import os

    env = os.environ.get("SENTINEL_DB")
    if env:
        return Path(env)
    for cand in (_PROD, _PKG_ROOT / "data" / "SENTINEL_OMEGA_PRO.db"):
        if "workspaces-dev" in str(cand):
            continue
        if cand.exists():
            return cand
    return _PROD


def abrir_readonly(timeout_s: float = 5.0) -> sqlite3.Connection:
    """Conexión read-only contra la DB canónica (o None si no existe).

    El patrón de todos los lectores de mensajería/orquestación: sin
    candados de escritor, sin crear la DB si falta (regla 7: ausencia
    es ausencia). `conn.row_factory` queda en Row para llamadores de
    dict-style; si no la quieren, la reasignan.
    """
    ruta = ruta_db_canonica()
    if not ruta.exists():
        return None  # type: ignore[return-value]
    conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=timeout_s)
    conn.row_factory = sqlite3.Row
    return conn
