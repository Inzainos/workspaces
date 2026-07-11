"""
Verificación del Juez — real vs predicción, cada 4 horas.

El ciclo del Padre (cada 2 h) solo REGISTRA su estado; el Juez pasa cada
4 horas a confrontar las predicciones vivas expiradas contra el catálogo
USGS real (verdad POR FILA: ventana propia de 72 h + nodos de la propia
predicción, o los nodos reales de la malla para los silencios).

El ritmo se auto-impone: si la última resolución viva tiene menos de
RITMO_HORAS, la pasada se salta (así ningún llamador — launcher continuo o
vigilante en Actions — puede acelerar el ritmo por accidente).
"""

import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RITMO_HORAS = 4


def _ultima_resolucion_ts(conn: sqlite3.Connection) -> Optional[float]:
    fila = conn.execute(
        "SELECT MAX(resuelto_at) FROM TBL_JUEZ_AUDITORIA WHERE fase = 'viva'"
    ).fetchone()
    if not fila or not fila[0]:
        return None
    try:
        return datetime.strptime(fila[0], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def verificar_juez(
    conn: sqlite3.Connection,
    forzar: bool = False,
    tracker=None,
) -> Dict[str, Any]:
    """Pasa el Juez: resuelve pendientes vivas contra USGS (verdad por fila).

    forzar=True ignora el ritmo de 4 h (para el paso agendado del vigilante).
    tracker: AssertivityTracker opcional — se alimenta con los eventos para
    la ganancia de Molchan en vivo.
    """
    from sentinel_omega.core.juez.juez import Juez

    ahora = time.time()
    ultima = _ultima_resolucion_ts(conn)
    if not forzar and ultima and (ahora - ultima) < RITMO_HORAS * 3600:
        faltan = (RITMO_HORAS * 3600 - (ahora - ultima)) / 3600
        logger.info(
            f"Juez: última verificación hace <{RITMO_HORAS}h "
            f"(próxima en ~{faltan:.1f}h) — se respeta el ritmo"
        )
        return {"saltada": True}

    from sentinel_omega.infrastructure.api.usgs import fetch_earthquakes
    eq = fetch_earthquakes(min_magnitude=4.5, days=7)
    if eq is None:
        # USGS caído: NO resolver con "sin eventos" falso.
        logger.warning("Juez: USGS sin respuesta — verificación pospuesta")
        return {"saltada": True, "motivo": "usgs_caido"}

    eventos: List[Dict[str, Any]] = []
    for _, ev in eq.iterrows():
        try:
            eventos.append({
                "epoch": ev["time"].timestamp(),
                "lat": ev["latitude"],
                "lon": ev["longitude"],
                "magnitude": ev["magnitude"],
            })
        except (KeyError, AttributeError, TypeError):
            continue

    zonas = [
        (z[0], z[1]) for z in conn.execute(
            "SELECT lat, lon FROM TBL_NODOS_TOPOLOGIA "
            "WHERE tipo = 'real' AND activo = 1").fetchall()
    ]

    juez = Juez(conn)
    resueltos = juez.evaluar_pendientes(
        evento_ocurrido=False,          # ignorado: `eventos` manda por fila
        eventos=eventos,
        zonas=zonas or None,
        fase="viva",
    )

    # Resumen real vs predicción de esta pasada
    conteo: Dict[str, int] = {}
    for r in resueltos:
        conteo[r["resultado"]] = conteo.get(r["resultado"], 0) + 1
    viva = dict(conn.execute(
        "SELECT resultado, COUNT(*) FROM viva_real GROUP BY resultado"
    ).fetchall())
    logger.info(
        f"JUEZ verificó: {len(resueltos)} resueltas {conteo or ''} — "
        f"acumulado viva: {viva}"
    )

    # Molchan en vivo si hay tracker alimentado
    if tracker is not None and eventos and tracker.prediction_count:
        try:
            tracker.ingest_events([
                {"latitude": e["lat"], "longitude": e["lon"],
                 "magnitude": e["magnitude"], "time": e["epoch"]}
                for e in eventos
            ])
            res_a, base_a = tracker.validate_with_baseline()
            logger.info(
                f"Molchan vivo: hit={res_a.hit_rate:.0%} "
                f"base={base_a.base_rate:.0%} ganancia={base_a.gain} — "
                f"{base_a.veredicto}"
            )
        except Exception as e:
            logger.warning(f"Molchan vivo falló (non-blocking): {e}")

    return {"saltada": False, "resueltas": len(resueltos),
            "conteo": conteo, "viva": viva}
