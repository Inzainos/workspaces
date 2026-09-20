#!/usr/bin/env python3
"""Elimina tablas basura de migración (_pre_<hash>/_orphans_<fecha>) de la DB.

Son snapshots automáticos de migraciones/dedup pasadas: ningún código las
referencia por nombre. Auditado 2026-09-15: 6 tablas, ~131k filas.

Seguro de correr con el launcher vivo (busy_timeout alto, solo metadata).
NO hace VACUUM (tomaría lock exclusivo largo). Para recuperar el espacio en
disco, correr `VACUUM` aparte CON EL LAUNCHER DETENIDO.

Backup previo recomendado (ya existe uno en scratchpad del 2026-09-15).
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"
PATRONES = ("_pre_c2e09d5a05b445aa", "_orphans_20260913")


def main() -> int:
    if not DB.exists():
        print(f"No existe la DB: {DB}", file=sys.stderr)
        return 1
    db = sqlite3.connect(str(DB), timeout=30)
    db.execute("PRAGMA busy_timeout=30000")
    c = db.cursor()
    junk = [
        r[0]
        for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if any(p in r[0] for p in PATRONES)
    ]
    if not junk:
        print("No hay tablas basura. Nada que hacer.")
        return 0
    print("A eliminar:", junk)
    for t in junk:
        n = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        c.execute(f'DROP TABLE IF EXISTS "{t}"')
        print(f"  DROP {t} ({n} filas)")
    db.commit()
    rest = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    print(f"Tablas restantes: {rest}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
