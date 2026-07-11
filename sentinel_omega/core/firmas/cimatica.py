"""
Cimática — snapshot de patrones de telemetría con conteo de frecuencia.

Idea (de Elán): cada ciclo se toma un snapshot del sistema y sus parámetros.
Primero se compara contra los patrones ya vistos:
  - Si es NUEVO → se guarda la telemetría COMPLETA (con el tiempo aparecerán
    los patrones).
  - Si YA EXISTE → solo se suma +1 a la frecuencia del patrón (contar, no
    anotar — igual que las correlaciones del Padre).

Así se va distinguiendo la cimática dentro de la telemetría, por nodo o
general, cuando resulta consistente para algún tipo de evento. Cualquier
alta o incremento dispara la revisión del Padre (trigger en Python); si el
patrón es consistente y está asociado a un tipo de evento, se encola una
alerta por correo.

La huella (clave) se construye con bandas logarítmicas con signo: es libre
de escala, agrupa estados parecidos bajo la misma clave y no necesita
configuración por variable.
"""

import json
import logging
import math
import sqlite3
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Frecuencia a partir de la cual un patrón se considera CONSISTENTE
# (cimática establecida, ya no coincidencia).
FRECUENCIA_CONSISTENTE = 3


def banda(v: float) -> int:
    """Banda logarítmica con signo: 0 para |v|<0.5, crece con la magnitud.

    Ej.: 0.3→0, 3→3, 8→4, 30→6, 300→10, -8→-4. Estados con magnitudes
    parecidas caen en la misma banda; el signo se conserva (Bz negativo
    NO es lo mismo que positivo).
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0
    av = abs(v)
    if av < 0.5:
        return 0
    b = int(round(4 * math.log10(1 + av)))
    return b if v > 0 else -b


def clave_patron(features: Dict[str, Any]) -> str:
    """Huella discretizada y determinista de la telemetría."""
    partes = []
    for k in sorted(features):
        v = features[k]
        if isinstance(v, (int, float)):
            partes.append(f"{k}:{banda(float(v))}")
    return "|".join(partes)


def registrar_snapshot(
    conn: sqlite3.Connection,
    features: Dict[str, Any],
    id_nodo: Optional[int] = None,
    event_class: Optional[str] = None,
) -> Tuple[int, bool, int]:
    """Registra el snapshot: alta con telemetría completa si es nuevo,
    frecuencia+1 si ya existe. Devuelve (patron_id, es_nuevo, frecuencia).
    """
    clave = clave_patron(features)
    if not clave:
        return (0, False, 0)
    ambito = "nodo" if id_nodo is not None else "general"

    fila = conn.execute(
        "SELECT patron_id, frecuencia, event_class FROM tbl_cimatica_patrones "
        "WHERE clave = ? AND ambito = ? AND id_nodo IS ?",
        (clave, ambito, id_nodo),
    ).fetchone()

    if fila is None:
        cur = conn.execute(
            "INSERT INTO tbl_cimatica_patrones "
            "(clave, ambito, id_nodo, event_class, telemetria_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (clave, ambito, id_nodo, event_class,
             json.dumps(features, default=float)),
        )
        conn.commit()
        logger.info(
            f"CIMÁTICA: patrón NUEVO ({ambito}"
            f"{f', nodo {id_nodo}' if id_nodo else ''}) — telemetría completa "
            f"guardada"
        )
        return (cur.lastrowid, True, 1)

    patron_id, frecuencia, ec_previa = fila
    # Etiquetar el tipo de evento si antes no lo tenía y ahora sí se conoce
    nueva_ec = ec_previa or event_class
    conn.execute(
        "UPDATE tbl_cimatica_patrones SET frecuencia = frecuencia + 1, "
        "event_class = ?, ultima_vez = datetime('now') WHERE patron_id = ?",
        (nueva_ec, patron_id),
    )
    conn.commit()
    frecuencia += 1
    if frecuencia == FRECUENCIA_CONSISTENTE:
        logger.warning(
            f"CIMÁTICA CONSISTENTE: patrón {patron_id} ({ambito}) alcanzó "
            f"frecuencia {frecuencia}"
            + (f" — asociado a {nueva_ec}" if nueva_ec else "")
        )
    return (patron_id, False, frecuencia)


def patrones_consistentes(
    conn: sqlite3.Connection,
    min_frecuencia: int = FRECUENCIA_CONSISTENTE,
    limite: int = 20,
) -> list:
    """Patrones con frecuencia significativa, para reportes y el Padre."""
    return conn.execute(
        "SELECT patron_id, ambito, id_nodo, event_class, frecuencia, "
        "primera_vez, ultima_vez FROM tbl_cimatica_patrones "
        "WHERE frecuencia >= ? ORDER BY frecuencia DESC LIMIT ?",
        (min_frecuencia, limite),
    ).fetchall()
