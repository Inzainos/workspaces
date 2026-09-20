# Auditoría de scripts Sentinel Omega

- Fecha UTC: 2026-09-14T07:32:52.309225Z
- Total scripts .py auditados: 261
- Entrypoints (__main__): 24
- Sintaxis OK: 261 | Con error: 0
- Riesgo HIGH: 0 | MEDIUM: 14 | LOW: 247
- Patrones tipo secreto: 0 archivos
- Uso eval/exec: 2 archivos
- Uso shell/os.system: 0 archivos
- Grupos de duplicados exactos: 106

## Top 25 por riesgo_score

| file | risk | score | shell_true | os_system | eval | exec | bare_except | except Exception | secret_hits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| launcher.py | MEDIUM | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 0 |
| launcher_fixed.py | MEDIUM | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 0 |
| infrastructure/messaging/consenso_vigilante.py | MEDIUM | 15 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| sentinel_omega/infrastructure/messaging/consenso_vigilante.py | MEDIUM | 15 | 0 | 0 | 0 | 0 | 0 | 15 | 0 |
| core/delta_enriched/fetchers.py | MEDIUM | 13 | 0 | 0 | 0 | 0 | 0 | 13 | 0 |
| sentinel_omega/core/delta_enriched/fetchers.py | MEDIUM | 13 | 0 | 0 | 0 | 0 | 0 | 13 | 0 |
| infrastructure/dashboard/api.py | MEDIUM | 12 | 0 | 0 | 0 | 0 | 0 | 12 | 0 |
| sentinel_omega/infrastructure/dashboard/api.py | MEDIUM | 12 | 0 | 0 | 0 | 0 | 0 | 12 | 0 |
| infrastructure/pipeline/data_pipeline.py | MEDIUM | 10 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| sentinel_omega/infrastructure/pipeline/data_pipeline.py | MEDIUM | 10 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| infrastructure/messaging/alert_enrichment.py | MEDIUM | 9 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| sentinel_omega/infrastructure/messaging/alert_enrichment.py | MEDIUM | 9 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| infrastructure/database/schema.py | MEDIUM | 8 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| sentinel_omega/infrastructure/database/schema.py | MEDIUM | 8 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| infrastructure/pipeline/backcast.py | LOW | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| sentinel_omega/infrastructure/pipeline/backcast.py | LOW | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| infrastructure/watchdog/network_watchdog.py | LOW | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| sentinel_omega/infrastructure/watchdog/network_watchdog.py | LOW | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| infrastructure/messaging/agent_bridge.py | LOW | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| sentinel_omega/infrastructure/messaging/agent_bridge.py | LOW | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| infrastructure/pipeline/mantenimiento.py | LOW | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| sentinel_omega/infrastructure/pipeline/mantenimiento.py | LOW | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| infrastructure/api/telegram.py | LOW | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| sentinel_omega/infrastructure/api/telegram.py | LOW | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| orchestrator.py | LOW | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |