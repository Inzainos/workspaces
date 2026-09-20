# Pipeline doc-contract check 20260914_020933

Verifica que scripts cumplan lo documentado en README/AGENTS/CLAUDE/CHANGELOG.

| Check | Doc claim | Impl | Status |
|---|---:|---:|---|
| launcher batch flags run-and-exit | yes | yes | OK |
| scheduler intervals 2h/6h | yes | yes | OK |
| watchdog should not restart scheduler (changelog) | yes | yes | OK |
| report versioning in estado/historial | no/weak | yes | OK |
| training in phases (1,1b,2) | yes | yes | OK |

## Runtime notes
- systemctl: sentinel-omega-scheduler = disabled/inactive (alineado a CHANGELOG).
- health.checks pipeline = ok (último ciclo reciente).
- warning recurrente observado: `database is locked` en escrituras auxiliares (no bloqueante).