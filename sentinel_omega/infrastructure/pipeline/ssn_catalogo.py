"""Catalogo SSN Mexico → tbl_eventos_sismicos_fuente.

Empata con filas USGS existentes por tiempo UTC (±90 s), lat/lon (±0.25°)
y magnitud (±0.3). MATCH actualiza status desde Estatus; place y depth_km
(y segmento derivado) solo se rellenan si el valor USGS existente esta
vacio/NULL — no se sobrescribe profundidad USGS ya presente. Conserva
usgs_id. NO MATCH inserta con prefijo ssnmx: — nunca ids USGS inventados
(usXXXX).

Encoding del CSV: el archivo real del SSN viene en latin-1 (acentos en
"Referencia de localizacion"). Se intenta utf-8 estricto sobre una muestra;
si falla, se abre con latin-1.

--min-mag por defecto 4.5 (alineado a tabla M4.5+). Pasar --min-mag 0
para el catalogo completo.

Por defecto es dry-run. Hace falta --apply explicito para escribir.
Tras cargar, conviene recalcular id_nodo con topologia_cascada
(--solo-recalcular): los INSERT nuevos salen con id_nodo=0 y
topologia_version='pending_ssnmx' salvo que se inyecte un resolver.
"""
from __future__ import annotations

import argparse
import csv
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sentinel_omega.infrastructure.pipeline.usgs_catalogo import (
    asegurar_columnas,
    segmento_de,
)

TOL_SEGUNDOS = 90.0
TOL_LATLON = 0.25
TOL_MAG = 0.3
META_LINEAS = 4
TOPOLOGIA_PENDIENTE = "pending_ssnmx"
ID_NODO_PENDIENTE = 0
DEFAULT_MIN_MAG = 4.5
_SAMPLE_BYTES = 8192


def _texto(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto == "":
        return None
    return texto


def _numero(valor):
    if valor is None or valor == "":
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return numero


def default_db_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "SENTINEL_OMEGA_PRO.db"


def detectar_encoding_ssn(path: Path) -> str:
    """utf-8 estricto sobre muestra; si falla → latin-1 (CSV real SSN)."""
    raw = Path(path).read_bytes()[:_SAMPLE_BYTES]
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def parse_ssn_time_utc(fecha_utc: str, hora_utc: str) -> datetime | None:
    """Fecha UTC + Hora UTC del CSV SSN → datetime aware UTC."""
    fecha = _texto(fecha_utc)
    hora = _texto(hora_utc)
    if not fecha or not hora:
        return None
    hora = hora.split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            momento = datetime.strptime(f"{fecha} {hora}", fmt)
            return momento.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def time_utc_str(momento: datetime) -> str:
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    momento = momento.astimezone(timezone.utc)
    return momento.strftime("%Y-%m-%d %H:%M:%S.%f")


def make_ssnmx_id(momento: datetime, lat: float, lon: float, mag: float) -> str:
    """Id estable no-USGS: ssnmx:YYYYMMDDTHHMMSSZ_lat_lon_mag."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    stamp = momento.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"ssnmx:{stamp}_{lat:.4f}_{lon:.4f}_{mag:.1f}"


def parse_db_time(valor) -> datetime | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                momento = datetime.strptime(texto, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def fila_de_ssn(row: dict) -> dict | None:
    """Una fila SSN normalizada, o None si falta lo esencial."""
    momento = parse_ssn_time_utc(row.get("Fecha UTC"), row.get("Hora UTC"))
    lat = _numero(row.get("Latitud"))
    lon = _numero(row.get("Longitud"))
    mag = _numero(row.get("Magnitud"))
    if momento is None or lat is None or lon is None or mag is None:
        return None
    depth_km = _numero(row.get("Profundidad"))
    return {
        "time_utc": time_utc_str(momento),
        "momento": momento,
        "lat": lat,
        "lon": lon,
        "mag": mag,
        "depth_km": depth_km,
        "place": _texto(row.get("Referencia de localizacion")),
        "status": _texto(row.get("Estatus")),
        "event_type": "earthquake",
        "mag_type": "ssn",
        "segmento": segmento_de(depth_km),
        "ssnmx_id": make_ssnmx_id(momento, lat, lon, mag),
    }


def leer_catalogo_ssn(csv_path, min_mag: float = DEFAULT_MIN_MAG, limit: int | None = None):
    """Lee el CSV SSN (4 lineas meta + header). Devuelve (filas, skipped_bad).

    Encoding: utf-8 estricto en muestra, si no latin-1 (CSV real SSN).
    """
    filas = []
    skipped_bad = 0
    path = Path(csv_path)
    encoding = detectar_encoding_ssn(path)
    with path.open("r", encoding=encoding, newline="") as fh:
        for _ in range(META_LINEAS):
            if not fh.readline():
                break
        reader = csv.DictReader(fh)
        for row in reader:
            if limit is not None and len(filas) >= limit:
                break
            fila = fila_de_ssn(row)
            if fila is None:
                skipped_bad += 1
                continue
            if fila["mag"] < min_mag:
                continue
            filas.append(fila)
    return filas, skipped_bad


def _dentro_tol(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def score_match(ssn: dict, cand: dict) -> float | None:
    dt = abs((ssn["momento"] - cand["momento"]).total_seconds())
    if dt > TOL_SEGUNDOS:
        return None
    if not _dentro_tol(ssn["lat"], cand["lat"], TOL_LATLON):
        return None
    if not _dentro_tol(ssn["lon"], cand["lon"], TOL_LATLON):
        return None
    if not _dentro_tol(ssn["mag"], cand["mag"], TOL_MAG):
        return None
    return (
        (dt / TOL_SEGUNDOS) ** 2
        + ((ssn["lat"] - cand["lat"]) / TOL_LATLON) ** 2
        + ((ssn["lon"] - cand["lon"]) / TOL_LATLON) ** 2
        + ((ssn["mag"] - cand["mag"]) / TOL_MAG) ** 2
    )


def construir_indice(conn: sqlite3.Connection) -> dict:
    """Indice por minuto UTC para candidatos de empate."""
    indice: dict[int, list] = defaultdict(list)
    rows = conn.execute(
        """SELECT usgs_id, time_utc, lat, lon, mag, place, depth_km, status
           FROM tbl_eventos_sismicos_fuente"""
    ).fetchall()
    for usgs_id, time_utc, lat, lon, mag, place, depth_km, status in rows:
        momento = parse_db_time(time_utc)
        if momento is None:
            continue
        bucket = int(momento.timestamp()) // 60
        indice[bucket].append(
            {
                "usgs_id": usgs_id,
                "momento": momento,
                "lat": float(lat),
                "lon": float(lon),
                "mag": float(mag),
                "place": place,
                "depth_km": depth_km,
                "status": status,
            }
        )
    return indice


def buscar_match(ssn: dict, indice: dict) -> dict | None:
    bucket = int(ssn["momento"].timestamp()) // 60
    mejor = None
    mejor_score = None
    for b in (bucket - 1, bucket, bucket + 1):
        for cand in indice.get(b, ()):
            # No empatar un ssnmx: consigo mismo en re-cargas vía mag/geo
            # (sí se puede enriquecer un USGS).
            sc = score_match(ssn, cand)
            if sc is None:
                continue
            if mejor_score is None or sc < mejor_score:
                mejor_score = sc
                mejor = cand
    return mejor


def actualizar_match(conn: sqlite3.Connection, usgs_id: str, ssn: dict) -> None:
    """Enriquece fila USGS existente; no toca usgs_id ni id_nodo.

    place y depth_km/segmento: fill-only (solo si vacio/NULL).
    status: siempre desde Estatus SSN si viene.
    """
    fila = conn.execute(
        """SELECT place, depth_km, status, segmento
           FROM tbl_eventos_sismicos_fuente WHERE usgs_id=?""",
        (usgs_id,),
    ).fetchone()
    if fila is None:
        return
    place_old, depth_old, status_old, segmento_old = fila
    place_new = place_old if _texto(place_old) else ssn["place"]
    # depth fill-only: solo escribir si USGS depth_km IS NULL
    if depth_old is None and ssn["depth_km"] is not None:
        depth_new = ssn["depth_km"]
        segmento_new = segmento_de(depth_new)
    else:
        depth_new = depth_old
        segmento_new = segmento_old
    status_new = ssn["status"] if ssn["status"] is not None else status_old
    conn.execute(
        """UPDATE tbl_eventos_sismicos_fuente
           SET depth_km=?, place=?, status=?, segmento=?,
               updated_at=datetime('now')
           WHERE usgs_id=?""",
        (depth_new, place_new, status_new, segmento_new, usgs_id),
    )


def insertar_ssnmx(
    conn: sqlite3.Connection,
    ssn: dict,
    id_nodo: int = ID_NODO_PENDIENTE,
    topologia_version: str = TOPOLOGIA_PENDIENTE,
) -> None:
    conn.execute(
        """INSERT INTO tbl_eventos_sismicos_fuente
           (usgs_id, time_utc, lat, lon, mag, id_nodo, topologia_version,
            depth_km, mag_type, event_type, place, status, tsunami, alert,
            mmi, cdi, felt, sig, segmento)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(usgs_id) DO UPDATE SET
               time_utc=excluded.time_utc,
               lat=excluded.lat, lon=excluded.lon, mag=excluded.mag,
               depth_km=excluded.depth_km,
               mag_type=excluded.mag_type,
               event_type=excluded.event_type,
               place=excluded.place,
               status=excluded.status,
               segmento=excluded.segmento,
               updated_at=datetime('now')""",
        (
            ssn["ssnmx_id"],
            ssn["time_utc"],
            ssn["lat"],
            ssn["lon"],
            ssn["mag"],
            id_nodo,
            topologia_version,
            ssn["depth_km"],
            ssn["mag_type"],
            ssn["event_type"],
            ssn["place"],
            ssn["status"],
            None,
            None,
            None,
            None,
            None,
            None,
            ssn["segmento"],
        ),
    )


def resolver_nodo_default(lat: float, lon: float):
    """Intenta geometria_uvg; si falla, id_nodo=0 + pending_ssnmx."""
    try:
        from sentinel_omega.core.shared.geometria_uvg import nodo_mas_cercano
        from sentinel_omega.infrastructure.pipeline.topologia_cascada import (
            calcular_version_topologia,
        )

        nodo = nodo_mas_cercano(lat, lon)
        return int(nodo["id"]), calcular_version_topologia()
    except Exception:
        return ID_NODO_PENDIENTE, TOPOLOGIA_PENDIENTE


def cargar_ssn(
    csv_path,
    conn: sqlite3.Connection,
    *,
    min_mag: float = DEFAULT_MIN_MAG,
    limit: int | None = None,
    apply: bool = False,
    resolver_nodo=None,
) -> dict:
    """Carga el catalogo. apply=False → solo cuenta, sin escribir."""
    if resolver_nodo is None:
        resolver_nodo = resolver_nodo_default
    resumen = {
        "read": 0,
        "matched_update": 0,
        "inserted_ssnmx": 0,
        "skipped_bad": 0,
        "errors": 0,
        "apply": bool(apply),
    }
    try:
        filas, skipped = leer_catalogo_ssn(csv_path, min_mag=min_mag, limit=limit)
    except Exception:
        resumen["errors"] += 1
        raise
    resumen["skipped_bad"] = skipped
    resumen["read"] = len(filas)

    if apply:
        asegurar_columnas(conn)

    indice = construir_indice(conn) if filas else {}

    for ssn in filas:
        try:
            match = buscar_match(ssn, indice)
            if match is not None:
                resumen["matched_update"] += 1
                if apply:
                    actualizar_match(conn, match["usgs_id"], ssn)
                continue
            resumen["inserted_ssnmx"] += 1
            if apply:
                id_nodo, topo = resolver_nodo(ssn["lat"], ssn["lon"])
                insertar_ssnmx(conn, ssn, id_nodo=id_nodo, topologia_version=topo)
                # Indexar el nuevo para no duplicar dentro del mismo CSV
                bucket = int(ssn["momento"].timestamp()) // 60
                indice[bucket].append(
                    {
                        "usgs_id": ssn["ssnmx_id"],
                        "momento": ssn["momento"],
                        "lat": ssn["lat"],
                        "lon": ssn["lon"],
                        "mag": ssn["mag"],
                        "place": ssn["place"],
                        "depth_km": ssn["depth_km"],
                        "status": ssn["status"],
                    }
                )
        except Exception:
            resumen["errors"] += 1

    if apply:
        conn.commit()
    return resumen


def _imprimir_resumen(resumen: dict) -> None:
    modo = "APPLY" if resumen.get("apply") else "DRY-RUN"
    print(
        f"[{modo}] read={resumen['read']} matched_update={resumen['matched_update']} "
        f"inserted_ssnmx={resumen['inserted_ssnmx']} skipped_bad={resumen['skipped_bad']} "
        f"errors={resumen['errors']}"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Carga catalogo SSN Mexico a tbl_eventos_sismicos_fuente (dry-run por defecto)."
    )
    p.add_argument("--csv", required=True, help="Ruta al CSV SSNMX")
    p.add_argument(
        "--db",
        default=str(default_db_path()),
        help="SQLite Sentinel (default: data/SENTINEL_OMEGA_PRO.db)",
    )
    p.add_argument(
        "--min-mag",
        type=float,
        default=DEFAULT_MIN_MAG,
        help=f"Magnitud minima a cargar (default: {DEFAULT_MIN_MAG}; usar 0 para catalogo completo)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="No escribe (defecto si no hay --apply)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Escribe en la DB (requiere confirmacion explicita)",
    )
    p.add_argument("--limit", type=int, default=None, help="Max filas SSN a procesar")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    # --dry-run gana si ambos; sin --apply nunca escribe
    apply = bool(args.apply) and not bool(args.dry_run)
    conn = sqlite3.connect(args.db)
    try:
        resumen = cargar_ssn(
            args.csv,
            conn,
            min_mag=args.min_mag,
            limit=args.limit,
            apply=apply,
        )
    finally:
        conn.close()
    _imprimir_resumen(resumen)
    return 1 if resumen["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
