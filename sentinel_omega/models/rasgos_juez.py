"""Reconstruir los rasgos de una ventana pasada desde la telemetría guardada.

Por qué existe (medido el 2026-09-26, después del rebuild)
----------------------------------------------------------
`TBL_JUEZ_AUDITORIA` tiene 21.204 filas vivas ya juzgadas. De ellas, **19.791
llevan `features_generales` como un diccionario VACÍO**: la clave se creó el
2026-08-20, pero el lanzador no le pasaba nada hasta el arreglo del 2026-09-25
17:38. Sólo 1.422 traen rasgos de verdad.

Eso deja al reentrenamiento aprendiendo de 1.056 muestras en vez de 21.000. Y
lo peor no es el volumen: **los 313 FALLO vivos están TODOS en el lote vacío**.
El FALLO es la única casilla que pesa 10 --- callarse y que pase algo --- así
que el entrenamiento se quedaba sin una sola ventana con evento y la asimetría
de coste no tenía de qué morder. La señal estaba conectada; faltaba el dato.

Qué hace y qué NO hace
----------------------
Lee la telemetría que la propia base ya guarda por bloques horarios y recompone
los agregados de la ventana de 72 h que termina en el instante de la fila. Es
**dato real medido**, consultado a posteriori; no se inventa nada:

  * una tabla que no cubre ese instante NO aporta su rasgo --- la clave queda
    ausente, nunca en 0.0, porque 0.0 le dice al modelo «Bz cero», no «no lo sé»
  * lo reconstruido se guarda en su propia tabla, no dentro de la auditoría:
    «lo que el bot vio» y «lo que la telemetría decía» no se mezclan jamás

En la ventana del 2026-09-08 al 26 la base cubre clima espacial (294 h de 432),
sismicidad, cobertura satelital, rayos X y tendencias. **No** cubre
desgasificación (última 2026-07-31), finanzas (2026-01-01) ni astronomía
(2025-12-31), así que beta2, delta y la fase lunar se quedan sin rasgos: se
anotan como fuente faltante y se ven en el resumen.

Nada de esto se dio por bueno: se validó contra las 1.422 filas que SÍ traen
rasgos, comparando lo reconstruido con lo que el bot vio de verdad. Esa
comparación decidió dos cosas.

**La ventana viva son 24 h, no 72.** Barriendo longitudes contra esas 1.422
filas, el error relativo mediano de `bz_min` pasa de 0,400 (72 h) a **0,000**
(24 h) y el de `bz_mean` de 0,508 a 0,092. El comentario de `features_onnx.py`
que dice «la ventana de alfa1 son 72 h» describe el diseño, no lo que el ciclo
hace. Aquí manda lo medido.

**Un rasgo que no se reproduce, no se escribe.** Sólo se conservan los que la
validación respalda (`RASGOS_VALIDADOS`). Se quedaron fuera, con su motivo:

  * `fase_lunar`, `es_sicigia`: `tbl_astronomia_cinematica` se paró el
    2025-12-31, así que la fila «más reciente» tiene nueve meses. En vivo la
    fase la calcula la efeméride del propio ciclo, no esta tabla
  * `sismo_count_win`, `sismo_count_72h`: en vivo valen **500 constante** ---
    el catálogo viene recortado a 500 registros --- y reconstruidos dan ~128.
    No es el mismo número, y el vivo además no informa de nada al ser constante
  * `bz_deriv_std`: la tabla horaria promedia el Bz; la desviación de las
    diferencias entre horas no significa lo mismo que la del muestreo crudo
  * `kp_max_72h`: el ciclo lo saca de las últimas 24 muestras de la serie Kp,
    no de esta tabla, y no coincidió

Por eso el tope de antigüedad: sin él, una fuente parada devuelve su última
fila como si fuera de ahora. Es el mismo error de fondo que se arregló con el
LOCF de Schumann --- un valor viejo presentado como actual --- y aquí habría
entrado disfrazado de dato.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("rasgos_juez")

# Medida contra las 1.422 filas con rasgos reales, no elegida de memoria.
VENTANA_H = 24

# Cuánto puede tener una fuente de «última fila» para seguir valiendo. Pasado
# eso no se usa: un dato viejo presentado como actual es peor que no tenerlo.
ANTIGUEDAD_MAX_H = {
    "satelital": 48,
    "xray": 24,
    "trends": 24 * 7,
    "lunar": 24,
}

# Los rasgos que la reconstrucción SÍ reproduce (error relativo mediano contra
# lo que el bot vio, con ventana de 24 h). Lo que no está aquí no se escribe.
RASGOS_VALIDADOS = {
    "bz_mean": 0.092,
    "bz_mean_72h": 0.092,
    "bz_min": 0.000,
    "viento_avg": 0.012,
    "viento_max": 0.001,
    "kp_mean": 0.127,
    "kp_max": 0.000,
    "proton_max": None,          # sin contraparte viva que comparar
    "sismo_max_mag_win": 0.061,
    "satellite_coverage_score": 0.000,
    "satellite_thermal_anomalies": 0.000,
    "satellite_clear_passes": 0.000,
    "schumann_mean": 0.000,
    "schumann_std": None,
    "xray_mean": 0.113,
    "xray_max": 0.083,
    "trends_mean": 0.000,
    # De aquí abajo, `None` = no hubo con qué compararlos porque su fuente no
    # cubre la ventana viva. Quedan admitidos a propósito: el tope de
    # antigüedad es quien decide si entran, así que el día que la fuente vuelva
    # a alimentarse funcionan solos, sin tener que acordarse de esta lista.
    # Hoy ninguno entra, y el resumen del relleno lo deja ver.
    "fase_lunar": None,
    "es_sicigia": None,
    # La marea se calcula, no se consulta: no hay «lo que el bot vio» de antes
    # del 2026-09-26 con que compararla, pero es determinista --- la misma
    # función devuelve lo mismo en vivo y reconstruida. Eso la valida.
    "marea_total": None,
    "marea_luna": None,
    "marea_sol": None,
    "marea_sicigia": None,
    "marea_dist_luna": None,
    "marea_rango_24h": None,
    "marea_max_24h": None,
    "marea_deriv": None,
    "btc_volatilidad": None,
    "btc_vol_max": None,
    "btc_vol_72h": None,
    "vix": None,
    "erupciones_win": None,
    "so2_kt_win": None,
    "erupciones_90d": None,
    "so2_kt_90d": None,
}

SQL_TABLA = """
CREATE TABLE IF NOT EXISTS tbl_juez_rasgos_reconstruidos (
    juez_id      INTEGER PRIMARY KEY,
    ts_blk       TEXT    NOT NULL,
    rasgos_json  TEXT    NOT NULL,
    fuentes      TEXT    NOT NULL,
    creado_at    TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""
SQL_INDICE = (
    "CREATE INDEX IF NOT EXISTS idx_rasgos_recon_ts "
    "ON tbl_juez_rasgos_reconstruidos(ts_blk)"
)


def asegurar_tabla(conn: sqlite3.Connection) -> None:
    """Migración forward-only: crea la tabla y su índice si no están."""
    conn.execute(SQL_TABLA)
    conn.execute(SQL_INDICE)
    conn.commit()


# ─── Lectores de telemetría, uno por fuente ──────────────────────────────────
#
# Todos reciben la ventana [inicio, fin] en texto 'YYYY-MM-DD HH:MM' porque así
# está guardado `timestamp_blk`, y todos devuelven {} cuando la fuente no cubre
# ese tramo. Ninguno rellena.


def _no_muy_vieja(ts_fila: Optional[str], fin: str, horas: float) -> bool:
    """¿La fila es lo bastante reciente para representar a `fin`?"""
    if not ts_fila:
        return False
    import datetime as _dt
    try:
        a = _dt.datetime.strptime(str(ts_fila)[:16], "%Y-%m-%d %H:%M")
        b = _dt.datetime.strptime(fin[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        try:  # las tablas de fecha suelta guardan sólo el día
            a = _dt.datetime.strptime(str(ts_fila)[:10], "%Y-%m-%d")
            b = _dt.datetime.strptime(fin[:10], "%Y-%m-%d")
        except ValueError:
            return False
    return 0 <= (b - a).total_seconds() / 3600.0 <= horas


def _clima(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    filas = conn.execute(
        "SELECT bz_promedio, bz_min, viento_solar_avg, viento_solar_max, "
        "       kp_promedio, kp_max, proton_flux_10mev "
        "FROM tbl_clima_espacial_raw "
        "WHERE timestamp_blk >= ? AND timestamp_blk <= ? "
        "ORDER BY timestamp_blk",
        (ini, fin),
    ).fetchall()
    if not filas:
        return {}
    arr = np.array(
        [[np.nan if v is None else float(v) for v in f] for f in filas], dtype=float
    )

    def col(i: int) -> np.ndarray:
        v = arr[:, i]
        return v[np.isfinite(v)]

    fuera: Dict[str, float] = {}
    bz, bzmin = col(0), col(1)
    vavg, vmax = col(2), col(3)
    kpm, kpx = col(4), col(5)
    prot = col(6)
    if bz.size:
        fuera["bz_mean"] = float(np.mean(bz))
        fuera["bz_mean_72h"] = float(np.mean(bz))
    if bzmin.size:
        fuera["bz_min"] = float(np.min(bzmin))
    if vavg.size:
        fuera["viento_avg"] = float(np.mean(vavg))
    if vmax.size:
        fuera["viento_max"] = float(np.max(vmax))
    if kpm.size:
        fuera["kp_mean"] = float(np.mean(kpm))
    if kpx.size:
        fuera["kp_max"] = float(np.max(kpx))
    if prot.size:
        fuera["proton_max"] = float(np.max(prot))
    return fuera


def _sismos(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    fila = conn.execute(
        "SELECT SUM(sismo_count), MAX(sismo_max_mag) "
        "FROM tbl_historico_sismico_raw "
        "WHERE timestamp_blk >= ? AND timestamp_blk <= ?",
        (ini, fin),
    ).fetchone()
    if not fila or fila[0] is None:
        return {}
    if fila[1] is None:
        return {}
    return {"sismo_max_mag_win": float(fila[1])}


def _satelital(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    ultimo = conn.execute(
        "SELECT MAX(timestamp_blk) FROM tbl_cobertura_satelital_historico "
        "WHERE timestamp_blk <= ?", (fin,)
    ).fetchone()
    if not ultimo or not _no_muy_vieja(ultimo[0], fin, ANTIGUEDAD_MAX_H["satelital"]):
        return {}
    filas = conn.execute(
        "SELECT coverage_score, thermal_anomalies, clear_passes "
        "FROM tbl_cobertura_satelital_historico WHERE timestamp_blk = ?",
        (ultimo[0],),
    ).fetchall()
    filas = [f for f in filas if f[0] is not None]
    if not filas:
        return {}
    return {
        "satellite_coverage_score": float(np.mean([f[0] for f in filas])),
        "satellite_thermal_anomalies": float(sum(f[1] or 0 for f in filas)),
        "satellite_clear_passes": float(sum(f[2] or 0 for f in filas)),
    }


def _filtro_en_vivo(conn) -> str:
    """Solo lecturas medidas; los arrastres (en_vivo=0) no entran al Juez.

    Así el vector que reciben los ONNX es el mismo que antes de la bandera:
    hasta el 2026-09-26 los arrastres no se guardaban.
    """
    try:
        from sentinel_omega.core.schumann_vivo import filtro_en_vivo
        return filtro_en_vivo(conn)
    except Exception:  # noqa: BLE001
        return ""


def _schumann(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    filas = conn.execute(
        "SELECT schumann_hz FROM tbl_schumann_vivo "
        "WHERE timestamp_blk >= ? AND timestamp_blk <= ?"
        + _filtro_en_vivo(conn),
        (ini, fin),
    ).fetchall()
    v = np.array([f[0] for f in filas if f[0] is not None], dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {}
    fuera = {"schumann_mean": float(np.mean(v))}
    if v.size > 1:
        fuera["schumann_std"] = float(np.std(v))
    return fuera


def _xray(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    fila = conn.execute(
        "SELECT flux_avg, flux_max, timestamp_blk FROM tbl_xray_vivo "
        "WHERE timestamp_blk <= ? ORDER BY timestamp_blk DESC LIMIT 1",
        (fin,),
    ).fetchone()
    if not fila or fila[0] is None:
        return {}
    if not _no_muy_vieja(fila[2], fin, ANTIGUEDAD_MAX_H["xray"]):
        return {}
    return {"xray_mean": float(fila[0]), "xray_max": float(fila[1] or fila[0])}


def _trends(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    fila = conn.execute(
        "SELECT solar_interest, fecha FROM tbl_trends_vivo "
        "WHERE fecha <= ? ORDER BY fecha DESC LIMIT 1",
        (fin[:10],),
    ).fetchone()
    if not fila or fila[0] is None:
        return {}
    if not _no_muy_vieja(fila[1], fin, ANTIGUEDAD_MAX_H["trends"]):
        return {}
    return {"trends_mean": float(fila[0])}


def _lunar(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    fila = conn.execute(
        "SELECT fase_lunar_pct, es_sicigia, timestamp_blk "
        "FROM tbl_astronomia_cinematica "
        "WHERE timestamp_blk <= ? ORDER BY timestamp_blk DESC LIMIT 1",
        (fin,),
    ).fetchone()
    if not fila or fila[0] is None:
        return {}
    # Con la tabla parada el 2025-12-31, esto devuelve {} para toda la ventana
    # viva. Es lo correcto: en vivo la fase la calcula la efeméride del ciclo.
    if not _no_muy_vieja(fila[2], fin, ANTIGUEDAD_MAX_H["lunar"]):
        return {}
    fase = float(fila[0])
    if fase > 1.0:  # la tabla guarda porcentaje; el vector espera 0-1
        fase /= 100.0
    fuera = {"fase_lunar": fase}
    if fila[1] is not None:
        fuera["es_sicigia"] = float(fila[1])
    return fuera


def _volcanes(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    fila = conn.execute(
        "SELECT COUNT(*), SUM(so2_kt) FROM tbl_desgasificacion_raw "
        "WHERE timestamp_blk >= ? AND timestamp_blk <= ?",
        (ini, fin),
    ).fetchone()
    if not fila or not fila[0]:
        return {}
    n = float(fila[0])
    kt = float(fila[1] or 0.0)
    return {
        "erupciones_win": n, "so2_kt_win": kt,
        "erupciones_90d": n, "so2_kt_90d": kt,
    }


def _marea(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    """La marea NO se consulta: se calcula. Por eso cubre el 100 % de las filas.

    No toca la base --- `conn` está por firma, para que todas las fuentes se
    llamen igual. Es la única que nunca devuelve {} por falta de datos.
    """
    import datetime as _dt

    from sentinel_omega.core.mareas import marea_ventana

    try:
        momento = _dt.datetime.strptime(fin[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return {}
    return marea_ventana(momento, horas=24)


def _finanzas(conn: sqlite3.Connection, ini: str, fin: str) -> Dict[str, float]:
    filas = conn.execute(
        "SELECT volatilidad_24h, vix FROM tbl_psique_financiera "
        "WHERE timestamp_blk >= ? AND timestamp_blk <= ? ORDER BY timestamp_blk",
        (ini, fin),
    ).fetchall()
    vol = np.array([f[0] for f in filas if f[0] is not None], dtype=float)
    vol = vol[np.isfinite(vol)]
    fuera: Dict[str, float] = {}
    if vol.size:
        fuera["btc_volatilidad"] = float(vol[-1])
        fuera["btc_vol_max"] = float(np.max(vol))
        fuera["btc_vol_72h"] = float(np.mean(vol))
    vix = [f[1] for f in filas if f[1] is not None]
    if vix:
        fuera["vix"] = float(vix[-1])
    return fuera


FUENTES = {
    "clima": _clima,
    "sismos": _sismos,
    "satelital": _satelital,
    "schumann": _schumann,
    "xray": _xray,
    "trends": _trends,
    "lunar": _lunar,
    "volcanes": _volcanes,
    "finanzas": _finanzas,
    "marea": _marea,
}


def rasgos_en(
    conn: sqlite3.Connection,
    ts_fin: str,
    ventana_h: int = VENTANA_H,
) -> Tuple[Dict[str, float], List[str]]:
    """Los rasgos de la ventana que termina en `ts_fin` y qué fuentes aportaron.

    Devuelve `({}, [])` si ninguna fuente cubre el instante. Cada fuente que no
    cubre simplemente no aparece: su rasgo queda ausente, no en cero.
    """
    import datetime as _dt

    fin = _dt.datetime.strptime(ts_fin[:16], "%Y-%m-%d %H:%M")
    ini = (fin - _dt.timedelta(hours=ventana_h)).strftime("%Y-%m-%d %H:%M")
    fin_s = fin.strftime("%Y-%m-%d %H:%M")
    rasgos: Dict[str, float] = {}
    aportaron: List[str] = []
    for nombre, lector in FUENTES.items():
        try:
            parcial = lector(conn, ini, fin_s)
        except sqlite3.Error as e:
            logger.warning("fuente %s no disponible: %s", nombre, e)
            continue
        parcial = {k: v for k, v in parcial.items() if k in RASGOS_VALIDADOS}
        if parcial:
            rasgos.update(parcial)
            aportaron.append(nombre)
    return rasgos, aportaron


def reconstruir_faltantes(
    conn: sqlite3.Connection,
    solo_fase: str = "viva",
    limite: Optional[int] = None,
    escribir: bool = True,
) -> Dict[str, object]:
    """Rellena los rasgos de las filas del Juez que no los traen.

    Recorre la auditoría de `solo_fase`, se salta las que ya tienen
    `features_generales` con contenido (lo que el bot vio manda siempre sobre lo
    reconstruido) y para el resto escribe en `tbl_juez_rasgos_reconstruidos`.
    Con `escribir=False` sólo mide, sin tocar nada.
    """
    import datetime as _dt

    asegurar_tabla(conn)
    ya = {
        r[0] for r in conn.execute(
            "SELECT juez_id FROM tbl_juez_rasgos_reconstruidos"
        )
    }
    sql = (
        "SELECT id, timestamp, detalles_json FROM TBL_JUEZ_AUDITORIA "
        "WHERE fase = ? ORDER BY id"
    )
    filas = conn.execute(sql, (solo_fase,)).fetchall()

    resumen = {
        "revisadas": 0, "ya_tenian": 0, "ya_reconstruidas": 0,
        "reconstruidas": 0, "sin_telemetria": 0,
        "fuentes": {}, "rasgos": {},
    }
    pendientes: List[Tuple[int, str, str, str]] = []
    cache: Dict[str, Tuple[Dict[str, float], List[str]]] = {}

    for _id, ts, det_json in filas:
        resumen["revisadas"] += 1
        try:
            det = json.loads(det_json) if det_json else {}
        except json.JSONDecodeError:
            det = {}
        g = det.get("features_generales") if isinstance(det, dict) else None
        if isinstance(g, dict) and g:
            resumen["ya_tenian"] += 1
            continue
        if _id in ya:
            resumen["ya_reconstruidas"] += 1
            continue
        try:
            blk = _dt.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError, OSError):
            resumen["sin_telemetria"] += 1
            continue
        # El bloque es el mismo para todos los bots de un ciclo: se consulta una
        # vez. Sin esto, 19.791 filas serían 19.791 barridos de 24 h.
        if blk not in cache:
            cache[blk] = rasgos_en(conn, blk)
        rasgos, fuentes = cache[blk]
        if not rasgos:
            resumen["sin_telemetria"] += 1
            continue
        resumen["reconstruidas"] += 1
        for f in fuentes:
            resumen["fuentes"][f] = resumen["fuentes"].get(f, 0) + 1
        for k in rasgos:
            resumen["rasgos"][k] = resumen["rasgos"].get(k, 0) + 1
        pendientes.append((_id, blk, json.dumps(rasgos), ",".join(fuentes)))
        if limite and len(pendientes) >= limite:
            break

    if escribir and pendientes:
        conn.executemany(
            "INSERT OR REPLACE INTO tbl_juez_rasgos_reconstruidos "
            "(juez_id, ts_blk, rasgos_json, fuentes) VALUES (?,?,?,?)",
            pendientes,
        )
        conn.commit()
    resumen["bloques_distintos"] = len(cache)
    resumen["escrito"] = bool(escribir and pendientes)
    return resumen


def cargar_reconstruidos(db_path: str) -> Dict[int, Dict[str, float]]:
    """{juez_id: rasgos} para que el reentrenamiento los use como respaldo."""
    conn = sqlite3.connect(db_path)
    try:
        filas = conn.execute(
            "SELECT juez_id, rasgos_json FROM tbl_juez_rasgos_reconstruidos"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()
    fuera: Dict[int, Dict[str, float]] = {}
    for jid, rj in filas:
        try:
            d = json.loads(rj)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict):
            fuera[int(jid)] = {
                k: float(v) for k, v in d.items() if isinstance(v, (int, float))
            }
    return fuera


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Reconstruir los rasgos de las filas del Juez que no los traen"
    )
    ap.add_argument("--db-path", required=True)
    ap.add_argument("--fase", default="viva")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--medir", action="store_true",
                    help="sólo medir, no escribir nada")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [RASGOS_JUEZ] %(levelname)s %(message)s")
    conn = sqlite3.connect(args.db_path)
    try:
        r = reconstruir_faltantes(conn, solo_fase=args.fase,
                                  limite=args.limite, escribir=not args.medir)
    finally:
        conn.close()
    print(json.dumps(r, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
