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
    commit: bool = True,
    silencioso: bool = False,
) -> Tuple[int, bool, int]:
    """Registra el snapshot: alta con telemetría completa si es nuevo,
    frecuencia+1 si ya existe. Devuelve (patron_id, es_nuevo, frecuencia).

    commit=False y silencioso=True para barridos masivos (entrenamiento
    histórico): el llamador controla el commit y no se inunda el log.
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
        if commit:
            conn.commit()
        if not silencioso:
            logger.info(
                f"CIMÁTICA: patrón NUEVO ({ambito}"
                f"{f', nodo {id_nodo}' if id_nodo else ''}) — telemetría "
                f"completa guardada"
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
    if commit:
        conn.commit()
    frecuencia += 1
    if frecuencia == FRECUENCIA_CONSISTENTE and not silencioso:
        logger.warning(
            f"CIMÁTICA CONSISTENTE: patrón {patron_id} ({ambito}) alcanzó "
            f"frecuencia {frecuencia}"
            + (f" — asociado a {nueva_ec}" if nueva_ec else "")
        )
    return (patron_id, False, frecuencia)


def entrenar_cimatica(
    db_path: str,
    max_eventos: Optional[int] = None,
) -> Dict[str, int]:
    """Entrenamiento cimático: graba en tbl_cimatica_patrones la telemetría
    de la víspera de CADA evento histórico (sísmico y no sísmico), con las
    frecuencias ya contadas — para no esperar meses de ciclos vivos.

    Usa exactamente la misma extracción de features de la Fase 1
    (extraer_features_ventana): la cimática histórica y la viva hablan el
    mismo idioma y caen en las mismas claves.
    """
    import sqlite3 as _sq
    from sentinel_omega.core.firmas.signature_engine import (
        extraer_features_ventana,
    )
    from sentinel_omega.infrastructure.pipeline.entrenamiento import (
        MIN_MAGNITUD_OBSERVAR, _event_class,
    )

    conn = _sq.connect(db_path)
    eventos = conn.execute(
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw WHERE sismo_max_mag >= ? "
        "ORDER BY timestamp_blk", (MIN_MAGNITUD_OBSERVAR,),
    ).fetchall()
    no_sismicos = []
    try:
        no_sismicos = conn.execute(
            "SELECT timestamp_blk, id_nodo, event_class "
            "FROM tbl_eventos_no_sismicos ORDER BY timestamp_blk"
        ).fetchall()
    except _sq.OperationalError:
        pass
    if max_eventos:
        eventos = eventos[:max_eventos]

    stats = {"eventos": 0, "patrones_nuevos": 0, "incrementos": 0,
             "sin_datos": 0}
    logger.info(
        f"=== ENTRENAMIENTO CIMÁTICO: {len(eventos)} eventos sísmicos + "
        f"{len(no_sismicos)} no sísmicos ==="
    )

    def _procesar(ts, id_nodo, clase):
        features = extraer_features_ventana(conn, ts, id_nodo)
        if features is None:
            stats["sin_datos"] += 1
            return
        stats["eventos"] += 1
        for nodo_reg in (None, id_nodo):     # general + por nodo
            _, es_nuevo, _ = registrar_snapshot(
                conn, features, id_nodo=nodo_reg, event_class=clase,
                commit=False, silencioso=True,
            )
            stats["patrones_nuevos" if es_nuevo else "incrementos"] += 1
        if stats["eventos"] % 1000 == 0:
            conn.commit()
            logger.info(
                f"  Cimática: {stats['eventos']} eventos — "
                f"{stats['patrones_nuevos']} patrones nuevos, "
                f"{stats['incrementos']} incrementos"
            )

    for ts, id_nodo, mag in eventos:
        _procesar(ts, id_nodo, _event_class(mag))
    for ts, id_nodo, clase in no_sismicos:
        _procesar(ts, id_nodo, clase)

    conn.commit()
    logger.info(f"Entrenamiento cimático completo: {stats}")
    conn.close()
    return stats


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
