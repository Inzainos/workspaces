#!/usr/bin/env python3
"""Backfill de tbl_astronomia_cinematica: fase lunar, sicigia y distancia lunar.

Contexto (auditoría 2026-09-20): `backcast.py` crea esta tabla insertando SOLO
`timestamp_blk`, así que sus 280.352 filas son un esqueleto de fechas y las
columnas `fase_lunar_pct`, `es_sicigia` y `distancia_lunar_km` quedaron 100%
muertas. `signature_engine.extraer_features_ventana` las lee para construir las
features `fase_lunar` y `es_sicigia` de omega, que entrenaba con ceros
constantes.

NO es dato sintético: la posición lunar para una fecha dada es un hecho
astronómico calculable (PyEphem), no una estimación inventada.

`lod_ms` NO se rellena: es una MEDICIÓN del IERS (duración del día), no se puede
derivar. Se deja NULL — faltante es NULL, nunca cero inventado.

Escala: `fase_lunar_pct` se guarda como phase_fraction 0-1 (0=nueva, 0.5=llena),
la MISMA que usa el dato vivo en TBL_PRECURSORES_COSMICOS.fase_lunar, para que
histórico y vivo sean comparables.

Uso:
    python scripts/db_backfill_astronomia.py --dry-run   # muestra sin escribir
    python scripts/db_backfill_astronomia.py
"""
import argparse
import bisect
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

AU_KM = 149_597_870.7
SICIGIA_DIAS = 1.0  # ventana ±1 día alrededor de luna nueva/llena

DB = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"


def _eventos_lunares(ini: datetime, fin: datetime):
    """Novilunios y plenilunios del rango, como floats de ephem.Date."""
    import ephem
    nuevas, llenas = [], []
    d = ephem.Date(ini)
    limite = ephem.Date(fin)
    while d < limite:
        d = ephem.next_new_moon(d)
        nuevas.append(float(d))
    d = ephem.Date(ini)
    while d < limite:
        d = ephem.next_full_moon(d)
        llenas.append(float(d))
    return nuevas, llenas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        import ephem
    except ImportError:
        print("ephem no está instalado: no se puede calcular sin inventar. Abortado.",
              file=sys.stderr)
        return 1

    con = sqlite3.connect(str(DB), timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    cur = con.cursor()

    filas = cur.execute(
        "SELECT timestamp_blk FROM tbl_astronomia_cinematica ORDER BY timestamp_blk"
    ).fetchall()
    if not filas:
        print("tabla vacía, nada que hacer")
        return 0

    def parse(s):
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    ini, fin = parse(filas[0][0]), parse(filas[-1][0])
    print(f"filas={len(filas):,}  rango={ini:%Y-%m-%d} … {fin:%Y-%m-%d}")

    # margen de un ciclo a cada lado para interpolar los extremos
    nuevas, llenas = _eventos_lunares(
        ini.replace(tzinfo=None), fin.replace(tzinfo=None)
    )
    d0 = ephem.Date(ini.replace(tzinfo=None))
    nuevas.insert(0, float(ephem.previous_new_moon(d0)))
    llenas.insert(0, float(ephem.previous_full_moon(d0)))
    print(f"novilunios={len(nuevas)}  plenilunios={len(llenas)}")

    updates = []
    for (ts_str,) in filas:
        t = parse(ts_str).replace(tzinfo=None)
        td = float(ephem.Date(t))

        # fracción del ciclo entre el novilunio previo y el siguiente
        i = bisect.bisect_right(nuevas, td) - 1
        if i < 0 or i + 1 >= len(nuevas):
            continue
        prev_n, next_n = nuevas[i], nuevas[i + 1]
        ciclo = next_n - prev_n
        frac = (td - prev_n) / ciclo if ciclo > 0 else None
        if frac is None:
            continue

        # sicigia: a ±SICIGIA_DIAS de una luna nueva o llena
        j = bisect.bisect_right(llenas, td) - 1
        cerca_llena = min(
            (abs(td - llenas[k]) for k in (j, j + 1) if 0 <= k < len(llenas)),
            default=99.0,
        )
        cerca_nueva = min(abs(td - prev_n), abs(next_n - td))
        sicigia = int(min(cerca_nueva, cerca_llena) <= SICIGIA_DIAS)

        dist_km = float(ephem.Moon(t).earth_distance) * AU_KM
        updates.append((round(frac, 4), sicigia, round(dist_km, 1), ts_str))

    print(f"calculadas {len(updates):,} filas")
    if updates:
        m = updates[len(updates) // 2]
        print(f"  muestra: {m[3]} → fase={m[0]} sicigia={m[1]} dist={m[2]:,.0f} km")
        sic = sum(u[1] for u in updates)
        print(f"  sicigias: {sic:,} ({sic / len(updates) * 100:.1f}% — esperado ~13%)")

    if args.dry_run:
        print("\n--dry-run: no se escribió nada")
        return 0

    cur.executemany(
        "UPDATE tbl_astronomia_cinematica SET fase_lunar_pct=?, es_sicigia=?, "
        "distancia_lunar_km=? WHERE timestamp_blk=?",
        updates,
    )
    con.commit()
    vivas = cur.execute(
        "SELECT COUNT(*) FROM tbl_astronomia_cinematica WHERE fase_lunar_pct IS NOT NULL"
    ).fetchone()[0]
    print(f"\nescritas. filas con fase_lunar_pct: {vivas:,}")
    print("lod_ms sigue NULL a propósito (medición IERS, no derivable)")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
