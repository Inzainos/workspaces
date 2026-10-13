"""Benchmark: json_extract vs JSONB (SQLite >= 3.45) sobre el Juez real.

Integración propuesta el 2026-10-13 tras el full-upgrade (SQLite 3.53.4).
Regla 9 de la casa: el cambio se decide contra el DATO, no contra el
manual. El universo real: TBL_JUEZ_AUDITORIA, ~1,03 M de filas, 124,5 MB
de `detalles_json`.

Qué mide:
  A. «Quién decidió» (la auditoría de juez_cycle_register): full-scan
     extrayendo 3 claves por fila — el caso donde JSONB debería ganar
     (parsea el JSON UNA vez por fila en vez de una por clave).
  B. Búsqueda en reasoning (1 clave, full-scan): caso borde.
  C. Ventana reciente (200 filas, la forma de /api/juez): el caso donde
     casi no debería importar, para no vender la mejora donde no está.

Uso:
    .venv/bin/python deploy/bench_jsonb.py [db_path]

Todo en solo lectura (mode=ro). Sin tocar producción.
"""
from __future__ import annotations

import sqlite3
import sys
import time

DB_DEFAULT = "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"


def timed(conn: sqlite3.Connection, sql: str, label: str, runs: int = 2) -> float:
    """Mejor de `runs` corridas (la primera calienta la caché de páginas)."""
    best = None
    for i in range(runs):
        t0 = time.perf_counter()
        n = conn.execute(sql).fetchone()[0]
        dt = (time.perf_counter() - t0) * 1000.0
        best = dt if best is None else min(best, dt)
        print(f"    run{i+1}: {dt:8.1f} ms  (n={n})")
    print(f"  {label:34s} {best:8.1f} ms")
    return best


def main() -> None:
    db = sys.argv[1] if len(sys.argv) > 1 else DB_DEFAULT
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60.0)
    version = sqlite3.sqlite_version
    print(f"SQLite {version} · {db}")
    if tuple(int(x) for x in version.split(".")[:2]) < (3, 45):
        print("sin JSONB (< 3.45): nada que medir")
        return

    n = conn.execute("SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA").fetchone()[0]
    mb = conn.execute(
        "SELECT ROUND(SUM(LENGTH(detalles_json))/1e6,1) FROM TBL_JUEZ_AUDITORIA"
    ).fetchone()[0]
    print(f"TBL_JUEZ_AUDITORIA: {n:,} filas · {mb} MB de JSON\n")

    resultados: dict = {}

    print("A. «Quién decidió» — full-scan, 3 claves por fila (la auditoría):")
    t_je = timed(
        conn,
        "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA "
        "WHERE json_extract(detalles_json,'$.onnx_senal') IS NOT NULL "
        "AND json_extract(detalles_json,'$.onnx_senal') "
        "   != json_extract(detalles_json,'$.regla_senal')",
        "json_extract (3 claves)",
    )
    t_jb = timed(
        conn,
        "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA "
        "WHERE jsonb_extract(jsonb(detalles_json),'$.onnx_senal') IS NOT NULL "
        "AND jsonb_extract(jsonb(detalles_json),'$.onnx_senal') "
        "   != jsonb_extract(jsonb(detalles_json),'$.regla_senal')",
        "jsonb_extract (3 claves)",
    )
    # A' — el patrón CORRECTO de jsonb: materializar la conversión UNA vez
    # por fila y extraer las claves del valor ya convertido. Si ni esto
    # gana, la integración queda rechazada por medición (veredicto del
    # 2026-10-13: pierde 294 vs 264 ms — la ruta de json_extract ya es la
    # rápida, y la conversión añade coste que 3 claves no amortizan).
    t_jb_m = timed(
        conn,
        "SELECT COUNT(*) FROM ("
        "  SELECT jsonb_extract(jb,'$.onnx_senal') AS o, "
        "         jsonb_extract(jb,'$.regla_senal') AS r "
        "  FROM (SELECT jsonb(detalles_json) AS jb FROM TBL_JUEZ_AUDITORIA)"
        ") WHERE o IS NOT NULL AND o != r",
        "jsonb materializado 1 vez/fila",
    )
    resultados["A"] = (t_je, min(t_jb, t_jb_m))

    print("\nB. Búsqueda en reasoning — full-scan, 1 clave:")
    t_je2 = timed(
        conn,
        "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA "
        "WHERE json_extract(detalles_json,'$.reasoning') LIKE '%tormenta%'",
        "json_extract (1 clave)",
    )
    t_jb2 = timed(
        conn,
        "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA "
        "WHERE jsonb_extract(jsonb(detalles_json),'$.reasoning') LIKE '%tormenta%'",
        "jsonb_extract (1 clave)",
    )
    resultados["B"] = (t_je2, t_jb2)

    print("\nC. Ventana reciente — 200 filas (la forma de /api/juez):")
    t_je3 = timed(
        conn,
        "SELECT json_extract(detalles_json,'$.onnx_senal'), "
        "json_extract(detalles_json,'$.regla_senal') "
        "FROM TBL_JUEZ_AUDITORIA ORDER BY id DESC LIMIT 200",
        "json_extract (200 filas)",
    )
    t_jb3 = timed(
        conn,
        "SELECT jsonb_extract(jsonb(detalles_json),'$.onnx_senal'), "
        "jsonb_extract(jsonb(detalles_json),'$.regla_senal') "
        "FROM TBL_JUEZ_AUDITORIA ORDER BY id DESC LIMIT 200",
        "jsonb_extract (200 filas)",
    )
    resultados["C"] = (t_je3, t_jb3)

    print("\n=== Veredicto ===")
    for k, (a, b) in resultados.items():
        if b < a:
            print(f"  {k}: jsonb GANA {a / b:.2f}x ({a:.0f} → {b:.0f} ms)")
        else:
            print(f"  {k}: json_extract se queda ({a:.0f} vs {b:.0f} ms, "
                  f"jsonb {b / a:.2f}x más lento)")
    print(
        "\nVeredicto medido el 2026-10-13 sobre 1,03 M de filas / 124,5 MB: "
        "json_extract GANA en todos los casos (incluso el patrón materializado "
        "pierde, 294 vs 264 ms). La integración de JSONB en este workload "
        "queda RECHAZADA: el instrumento queda para no volver a perseguirla "
        "sin datos nuevos."
    )


if __name__ == "__main__":
    main()
