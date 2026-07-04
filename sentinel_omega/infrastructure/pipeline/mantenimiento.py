"""
Mantenimiento — barrido diario del historial operativo.

Los ciclos escriben todo el día en las tablas operativas (cada ~2h). Una vez
al día, el barrido se queda con lo SIGNIFICANTE y bota el bulto:

  - Resumen del día  -> tbl_resumen_diario (una fila por día: fantasma máx/
    media, breaches, alertas, señal dominante).
  - Ciclos: se conservan los significativos (HIGH/CRITICAL o con breach); los
    ciclos de calma anteriores a la ventana de retención se botan (su esencia
    ya quedó en el resumen).
  - Detecciones: se colapsan a una por (día, tipo, muro) con la confianza más
    alta — las mismas detecciones repetidas cada ciclo dejan de acumularse.

Mismo principio que las referencias legacy: aprender/registrar la esencia,
soltar el crudo. Se corre 1×/día (lo dispara el vigilante).
"""

import logging
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict

logger = logging.getLogger(__name__)

DIAS_RETENCION_FULL = 7  # días recientes que se conservan a resolución de ciclo


def _dia_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def barrido_diario(db_path: str, dias_full: int = DIAS_RETENCION_FULL) -> Dict:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_resumen_diario ("
        "dia TEXT PRIMARY KEY, n_ciclos INTEGER, fantasma_max REAL, "
        "fantasma_media REAL, nivel_max TEXT, breaches INTEGER, alertas INTEGER, "
        "senal_dominante TEXT, creada_at TEXT DEFAULT (datetime('now')))"
    )

    hoy = datetime.now(timezone.utc).date()
    corte = hoy - timedelta(days=dias_full)
    corte_ts = datetime(
        corte.year, corte.month, corte.day, tzinfo=timezone.utc
    ).timestamp()
    hoy_ts = datetime(hoy.year, hoy.month, hoy.day, tzinfo=timezone.utc).timestamp()

    NIVEL_ORD = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
    stats = {"dias_resumidos": 0, "ciclos_botados": 0, "detecciones_colapsadas": 0}

    # ── 1) Resumen de días anteriores al corte, aún no resumidos ──
    ya = {r[0] for r in conn.execute("SELECT dia FROM tbl_resumen_diario")}
    por_dia: Dict[str, list] = {}
    for row in conn.execute(
        "SELECT timestamp, fantasma, nivel_riesgo, muro_breach, geo_signal "
        "FROM TBL_CICLOS WHERE timestamp < ?", (corte_ts,)
    ):
        d = _dia_utc(row[0])
        if d not in ya:
            por_dia.setdefault(d, []).append(row)

    for dia, filas in por_dia.items():
        fant = [f[1] for f in filas if f[1] is not None]
        niveles = [f[2] for f in filas if f[2]]
        senales = [f[4] for f in filas if f[4]]
        conn.execute(
            "INSERT OR REPLACE INTO tbl_resumen_diario "
            "(dia, n_ciclos, fantasma_max, fantasma_media, nivel_max, breaches, "
            " alertas, senal_dominante) VALUES (?,?,?,?,?,?,?,?)",
            (dia, len(filas), round(max(fant), 2) if fant else None,
             round(sum(fant) / len(fant), 2) if fant else None,
             max(niveles, key=lambda n: NIVEL_ORD.get(n, 0)) if niveles else None,
             sum(1 for f in filas if f[3]),
             sum(1 for s in senales if s == "alert"),
             Counter(senales).most_common(1)[0][0] if senales else None),
        )
        stats["dias_resumidos"] += 1

    # ── 2) Botar ciclos de calma anteriores al corte (los significativos se
    #        quedan: HIGH/CRITICAL o con breach) ──
    stats["ciclos_botados"] = conn.execute(
        "DELETE FROM TBL_CICLOS WHERE timestamp < ? "
        "AND muro_breach = 0 AND nivel_riesgo NOT IN ('HIGH','CRITICAL')",
        (corte_ts,),
    ).rowcount
    conn.execute(
        "DELETE FROM TBL_PRECURSORES_COSMICOS WHERE timestamp < ? AND fantasma < 15",
        (corte_ts,),
    )

    # ── 3) Colapsar detecciones repetidas de días ya cerrados: una por
    #        (día, tipo, muro) con la confianza más alta ──
    dets = conn.execute(
        "SELECT id, timestamp, tipo, wall_name, confidence "
        "FROM TBL_DETECCIONES WHERE timestamp < ?", (hoy_ts,)
    ).fetchall()
    mejor: Dict[tuple, tuple] = {}
    for did, ts, tipo, muro, conf in dets:
        clave = (_dia_utc(ts), tipo, muro)
        if clave not in mejor or (conf or 0) > (mejor[clave][1] or 0):
            mejor[clave] = (did, conf)
    conservar = {v[0] for v in mejor.values()}
    a_botar = [d[0] for d in dets if d[0] not in conservar]
    if a_botar:
        conn.executemany(
            "DELETE FROM TBL_DETECCIONES WHERE id = ?", [(i,) for i in a_botar]
        )
        stats["detecciones_colapsadas"] = len(a_botar)

    conn.commit()
    conn.close()
    logger.info(f"Barrido diario: {stats}")
    return stats
