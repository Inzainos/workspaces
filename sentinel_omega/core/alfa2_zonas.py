"""Cobertura satelital GLOBAL para alfa2, por rotación.

El problema (medido el 2026-10-02)
----------------------------------
`fetch_alfa2_data` pedía tres cajas mexicanas por defecto ---
`["guerrero_gap", "oaxaca_costa", "chiapas"]` --- mientras el Juez calificaba a
alfa2 contra el catálogo **mundial** de USGS. El bot no fallaba: miraba otra
cosa que la que se le exigía.

Por qué no basta con pedirlas todas
-----------------------------------
`compute_temporal_coverage` son DOS consultas al catálogo de Copernicus (S2 y
S1) y cuesta, medido en vivo:

    guerrero_gap        22,53 s
    ring_of_fire_japan  18,96 s

A ~20 s por zona, y con un ciclo de ~190 s:

    3 zonas (lo de hoy)     ~60 s     un tercio del ciclo
    10 zonas históricas    ~200 s     NO CABE
    50 nodos de la malla  ~1.000 s    17 min, imposible

Así que «global» no puede significar «todas cada ciclo».

La solución: rotación con memoria
---------------------------------
Cada ciclo mide las `ZONAS_POR_CICLO` zonas **más antiguas** (las que nunca se
midieron van primero), guarda su lectura, y los rasgos de alfa2 se agregan
sobre la ÚLTIMA lectura de TODAS las zonas. El coste por ciclo no cambia; la
cobertura sí.

La rotación no necesita un contador: «la más antigua primero» se autocorrige
sola si un ciclo falla, si se añade un nodo o si el sistema estuvo apagado.

Con 50 nodos y 3 por ciclo: barrido completo cada ~17 ciclos, poco menos de una
hora.

Qué NO hace
-----------
No inventa cobertura para una zona que nunca se midió: esa zona simplemente no
está en el agregado hasta que le toque su turno. Cero sintético.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cuántas zonas se miden por ciclo. Tres es el MISMO coste que el sistema ya
# pagaba (~60 s de los ~190 s del ciclo); subirlo no cabe, bajarlo alarga el
# barrido. Si el ciclo se acelera, esto se puede subir.
ZONAS_POR_CICLO = 3

TABLA = "tbl_alfa2_cobertura_zona"

SQL_TABLA = f"""
CREATE TABLE IF NOT EXISTS {TABLA} (
    zona              TEXT PRIMARY KEY,
    lat               REAL,
    lon               REAL,
    total_passes      INTEGER,
    s2_count          INTEGER,
    s1_count          INTEGER,
    clear_passes      INTEGER,
    muestras_nube     INTEGER,
    mean_revisit_days REAL,
    medido_at         TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def asegurar_tabla(conn: sqlite3.Connection) -> None:
    conn.execute(SQL_TABLA)
    conn.commit()


def puntaje_zona(
    total_passes: float,
    clear_passes: float,
    muestras_nube: float,
    mean_revisit_days: float,
) -> float:
    """El puntaje de cobertura de una zona, 0..1.

    La fórmula vivía suelta dentro de `launcher._build_live_features`. Está
    aquí para que el agregado global y el cálculo por zona usen LA MISMA, en
    vez de dos copias que se separan con el tiempo.

    Tres tercios: cuántas pasadas hubo (saturando en 8), qué fracción vino sin
    nubes, y qué tan seguido revisita (penalizando a partir de 12 días).
    """
    p = min(float(total_passes) / 8.0, 1.0) * 0.4
    p += (float(clear_passes) / max(float(muestras_nube), 1.0)) * 0.3
    p += max(0.0, 1.0 - float(mean_revisit_days) / 12.0) * 0.3
    return p


def zonas_a_medir(conn: sqlite3.Connection, n: int = ZONAS_POR_CICLO) -> List[str]:
    """Las `n` zonas que llevan más tiempo sin medirse. Nunca medidas primero.

    Es la rotación entera: no hay cursor ni estado aparte que pueda
    desincronizarse.
    """
    from sentinel_omega.infrastructure.api.esa_sentinel import zonas_de_la_malla

    todas = list(zonas_de_la_malla())
    if conn is None:
        return todas[:n]
    try:
        asegurar_tabla(conn)
        vistas = {z: ts for z, ts in conn.execute(
            f"SELECT zona, medido_at FROM {TABLA}").fetchall()}
    except sqlite3.Error as e:
        logger.warning("No se pudo leer la rotación de alfa2 (%s): se usan "
                       "las primeras %d zonas", e, n)
        return todas[:n]
    # Sin lectura previa -> cadena vacía, que ordena antes que cualquier fecha.
    return sorted(todas, key=lambda z: vistas.get(z) or "")[:n]


def guardar_cobertura(
    conn: sqlite3.Connection,
    zona: str,
    cov: Dict[str, Any],
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> None:
    """Persiste la lectura de una zona. Sobreescribe la anterior A PROPÓSITO:
    lo que interesa es la foto más reciente de cada sitio, y la serie histórica
    completa vive en `tbl_cobertura_satelital_historico`."""
    nubes = cov.get("s2_cloud_covers") or []
    claras = sum(1 for c in nubes if c is not None and float(c) < 20.0)
    try:
        asegurar_tabla(conn)
        conn.execute(
            f"INSERT INTO {TABLA} (zona, lat, lon, total_passes, s2_count, "
            " s1_count, clear_passes, muestras_nube, mean_revisit_days, "
            " medido_at) VALUES (?,?,?,?,?,?,?,?,?,datetime('now')) "
            "ON CONFLICT(zona) DO UPDATE SET "
            "  lat=excluded.lat, lon=excluded.lon, "
            "  total_passes=excluded.total_passes, s2_count=excluded.s2_count, "
            "  s1_count=excluded.s1_count, clear_passes=excluded.clear_passes, "
            "  muestras_nube=excluded.muestras_nube, "
            "  mean_revisit_days=excluded.mean_revisit_days, "
            "  medido_at=excluded.medido_at",
            (zona, lat, lon,
             int(cov.get("total_passes") or 0),
             int(cov.get("s2_count") or 0),
             int(cov.get("s1_count") or 0),
             claras, len(nubes),
             float(cov.get("mean_revisit_days") or 0.0)),
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.warning("No se pudo guardar la cobertura de %s (%s)", zona, e)


def agregado_global(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """Los rasgos de alfa2 sobre la última lectura de TODAS las zonas medidas.

    Devuelve None si no hay ninguna --- faltante es faltante, no cero.
    """
    if conn is None:
        return None
    try:
        asegurar_tabla(conn)
        filas = conn.execute(
            f"SELECT zona, total_passes, clear_passes, muestras_nube, "
            f"mean_revisit_days FROM {TABLA}").fetchall()
    except sqlite3.Error as e:
        logger.warning("No se pudo leer el agregado de alfa2 (%s)", e)
        return None
    if not filas:
        return None
    puntajes = [puntaje_zona(f[1] or 0, f[2] or 0, f[3] or 0, f[4] or 0.0)
                for f in filas]
    return {
        "zonas": len(filas),
        "satellite_coverage_score": round(sum(puntajes) / len(puntajes), 4),
        "satellite_clear_passes": float(sum(f[2] or 0 for f in filas)),
        "pasadas_totales": int(sum(f[1] or 0 for f in filas)),
    }
