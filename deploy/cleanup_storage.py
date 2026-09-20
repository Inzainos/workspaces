#!/usr/bin/env python3
"""
Limpieza segura de almacenamiento para Sentinel Omega.

Modo por defecto: DRY-RUN (no borra nada).
Para aplicar borrado real: --apply

Alcance conservador:
- data/backups/*.copy-* antiguos (con retención por días y keep-last)
- logs rotados sentinel_omega.log.N (keep-last)
- sentinel_omega.log.prev (si excede antigüedad)
- estado/entrenamiento_inicial.log (si excede antigüedad)

NO toca:
- SENTINEL_OMEGA_PRO.db ni sus archivos WAL/SHM
- sentinel_omega.log activo
- reportes de estado/historial
- modelos ONNX
"""

from __future__ import annotations

import argparse
import fnmatch
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

WORKSPACES = Path('/home/deamon/workspaces')
DATA_DIR = WORKSPACES / 'sentinel_omega' / 'data'
BACKUP_DIR = DATA_DIR / 'backups'
ESTADO_DIR = WORKSPACES / 'estado'

ALLOWED_DELETE_PATTERNS = [
    str(BACKUP_DIR / 'SENTINEL_OMEGA_PRO.db.copy-*'),
    str(DATA_DIR / 'sentinel_omega.log.prev'),
    str(DATA_DIR / 'sentinel_omega.log.[0-9]*'),
    str(ESTADO_DIR / 'entrenamiento_inicial.log'),
]


@dataclass
class Candidate:
    path: Path
    size: int
    age_days: float
    reason: str


def _age_days(p: Path) -> float:
    now = datetime.now(timezone.utc).timestamp()
    return (now - p.stat().st_mtime) / 86400.0


def _human(n: int) -> str:
    x = float(n)
    for u in ('B', 'KB', 'MB', 'GB', 'TB'):
        if x < 1024.0 or u == 'TB':
            return f'{x:.1f}{u}' if u != 'B' else f'{int(x)}B'
        x /= 1024.0
    return f'{n}B'


def _is_allowed_target(path: Path) -> bool:
    full = str(path.resolve())
    return any(fnmatch.fnmatch(full, pattern) for pattern in ALLOWED_DELETE_PATTERNS)


def _extract_type(path: Path) -> str:
    name = path.name
    if name.startswith('SENTINEL_OMEGA_PRO.db.copy-'):
        return 'db-backup-copy'
    if name == 'sentinel_omega.log.prev':
        return 'log-prev'
    if name.startswith('sentinel_omega.log.') and name.rsplit('.', 1)[-1].isdigit():
        return 'log-rotated'
    if name == 'entrenamiento_inicial.log':
        return 'estado-log'
    return 'unknown'


def collect_candidates(
    keep_backups: int,
    min_backup_age_days: int,
    keep_rotated_logs: int,
    min_prev_log_age_days: int,
    min_estado_log_age_days: int,
) -> List[Candidate]:
    out: List[Candidate] = []

    # 1) Backups antiguos (mantener los N más recientes)
    backups = sorted(
        [p for p in BACKUP_DIR.glob('SENTINEL_OMEGA_PRO.db.copy-*') if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for idx, p in enumerate(backups):
        age = _age_days(p)
        if idx >= keep_backups and age >= min_backup_age_days:
            out.append(Candidate(p, p.stat().st_size, age, f'backup viejo (keep={keep_backups}, age>={min_backup_age_days}d)'))

    # 2) Logs rotados sentinel_omega.log.N (mantener N más recientes)
    rotated = []
    for p in DATA_DIR.glob('sentinel_omega.log.*'):
        if p.is_file() and p.name.rsplit('.', 1)[-1].isdigit():
            rotated.append(p)
    rotated = sorted(rotated, key=lambda p: p.stat().st_mtime, reverse=True)
    for idx, p in enumerate(rotated):
        if idx >= keep_rotated_logs:
            out.append(Candidate(p, p.stat().st_size, _age_days(p), f'log rotado excedente (keep={keep_rotated_logs})'))

    # 3) .prev viejo
    prev = DATA_DIR / 'sentinel_omega.log.prev'
    if prev.exists() and prev.is_file():
        age = _age_days(prev)
        if age >= min_prev_log_age_days:
            out.append(Candidate(prev, prev.stat().st_size, age, f'log .prev viejo (age>={min_prev_log_age_days}d)'))

    # 4) entrenamiento_inicial.log viejo en estado/
    ent = ESTADO_DIR / 'entrenamiento_inicial.log'
    if ent.exists() and ent.is_file():
        age = _age_days(ent)
        if age >= min_estado_log_age_days:
            out.append(Candidate(ent, ent.stat().st_size, age, f'log entrenamiento viejo (age>={min_estado_log_age_days}d)'))

    # dedupe por path
    uniq = {}
    for c in out:
        uniq[str(c.path)] = c
    return sorted(uniq.values(), key=lambda c: c.size, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser(description='Limpieza segura de almacenamiento Sentinel Omega')
    ap.add_argument('--apply', action='store_true', help='aplicar borrado real (por defecto dry-run)')
    ap.add_argument('--keep-backups', type=int, default=2)
    ap.add_argument('--min-backup-age-days', type=int, default=7)
    ap.add_argument('--keep-rotated-logs', type=int, default=2)
    ap.add_argument('--min-prev-log-age-days', type=int, default=7)
    ap.add_argument('--min-estado-log-age-days', type=int, default=30)
    args = ap.parse_args()

    candidates = collect_candidates(
        keep_backups=args.keep_backups,
        min_backup_age_days=args.min_backup_age_days,
        keep_rotated_logs=args.keep_rotated_logs,
        min_prev_log_age_days=args.min_prev_log_age_days,
        min_estado_log_age_days=args.min_estado_log_age_days,
    )

    allowed = [c for c in candidates if _is_allowed_target(c.path)]
    blocked = [c for c in candidates if not _is_allowed_target(c.path)]

    total = sum(c.size for c in allowed)
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'[cleanup_storage] mode={mode} allowed={len(allowed)} blocked={len(blocked)} reclaimable={_human(total)}')

    if blocked:
        print('! BLOQUEADOS por whitelist (NO se borrarán):')
        for c in blocked:
            print(f'  - {_human(c.size):>10} | {c.path} | tipo={_extract_type(c.path)}')

    if not allowed:
        print('Nada que limpiar con la política actual.')
        return 0

    print('Tipos permitidos en esta corrida:')
    seen_types = sorted({_extract_type(c.path) for c in allowed})
    for t in seen_types:
        print(f'  - {t}')

    for c in allowed:
        print(f'- {_human(c.size):>10} | age={c.age_days:6.1f}d | {c.reason} | {c.path}')

    if not args.apply:
        print('No se borró nada (dry-run). Usa --apply para ejecutar.')
        return 0

    deleted = 0
    freed = 0
    failed = 0
    for c in allowed:
        try:
            # Doble verificación en tiempo de borrado
            if not _is_allowed_target(c.path):
                failed += 1
                print(f'! BLOQUEADO en delete-time: {c.path}')
                continue
            c.path.unlink(missing_ok=False)
            deleted += 1
            freed += c.size
        except Exception as e:
            failed += 1
            print(f'! ERROR borrando {c.path}: {e}')

    print(f'[cleanup_storage] deleted={deleted} failed={failed} freed={_human(freed)}')
    return 0 if failed == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
