# Revisión carpeta por carpeta — Sentinel + deploy + Concilio


## ROOT: /home/deamon/workspaces/sentinel_omega
- directorios revisados: 106
- docs revisados: 64
- scripts py revisados: 258
- syntax fail: 0

### 1. .
- docs:9 py:6 otros:4
- señales d/w/t: 9/4/9
- docs:
  - AGENTS.md: Sentinel Omega — Agents Registry (v2.5.4) [telegram]
  - CHANGELOG.md: 2026-09-13 — Duelo launcher cerrado, watchdog/ops, Schumann/Alfa2 tests [dashboard,watchdog,telegram]
  - CLAUDE.md: Sentinel Omega [dashboard,watchdog,telegram]
  - LAUNCHER_AGENT_SIGNALS_PATCH.md: Parche launcher — agent_signals + ventana adaptativa [telegram]
  - README.md: Sentinel Omega v2.5.4 — The Third Act [dashboard,watchdog,telegram]
  - alfa2_baseline_historical.json: {
  - api_log.txt: 
  - pyproject.toml: [build-system] [dashboard]
  - requirements.txt: Sentinel Omega — dependencias core [dashboard]
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - launcher.py: syntax=ok, exceptE=18, bare=0, main=1
  - launcher_fixed.py: syntax=ok, exceptE=18, bare=0, main=1
  - orchestrator.py: syntax=ok, exceptE=6, bare=0, main=0
  - reboot.py: syntax=ok, exceptE=0, bare=0, main=1
  - shutdown.py: syntax=ok, exceptE=0, bare=0, main=1

### 2. _archive
- docs:0 py:0 otros:0
- señales d/w/t: 0/0/0

### 3. _archive/20260913
- docs:1 py:0 otros:0
- señales d/w/t: 0/0/0
- docs:
  - README.md: Archive 2026-09-13 (Agente-C)

### 4. _archive/20260913/models_nested
- docs:1 py:0 otros:6
- señales d/w/t: 0/0/1
- docs:
  - models_meta.json: { [telegram]

### 5. _archive/20260913/schema
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 6. config
- docs:1 py:3 otros:0
- señales d/w/t: 2/0/3
- docs:
  - sentinel.yaml: app: [dashboard,telegram]
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - onnx_config.py: syntax=ok, exceptE=0, bare=0, main=0
  - sentinel_config.py: syntax=ok, exceptE=2, bare=0, main=0

### 7. core
- docs:0 py:3 otros:0
- señales d/w/t: 1/0/2
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - onnx_engine.py: syntax=ok, exceptE=4, bare=0, main=0
  - onnx_mixin.py: syntax=ok, exceptE=2, bare=0, main=0

### 8. core/delta_enriched
- docs:0 py:7 otros:0
- señales d/w/t: 7/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - composite.py: syntax=ok, exceptE=1, bare=0, main=1
  - cross.py: syntax=ok, exceptE=2, bare=0, main=0
  - delta_engine.py: syntax=ok, exceptE=1, bare=0, main=0
  - fetchers.py: syntax=ok, exceptE=13, bare=0, main=0
  - historico.py: syntax=ok, exceptE=3, bare=0, main=1
  - market_mapping.py: syntax=ok, exceptE=0, bare=0, main=0

### 9. core/firmas
- docs:0 py:3 otros:0
- señales d/w/t: 2/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - cimatica.py: syntax=ok, exceptE=2, bare=0, main=0
  - signature_engine.py: syntax=ok, exceptE=2, bare=0, main=0

### 10. core/juez
- docs:0 py:3 otros:0
- señales d/w/t: 0/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - juez.py: syntax=ok, exceptE=0, bare=0, main=0
  - pesos.py: syntax=ok, exceptE=0, bare=0, main=0

### 11. core/precursor
- docs:0 py:9 otros:0
- señales d/w/t: 2/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - assertivity.py: syntax=ok, exceptE=0, bare=0, main=0
  - baseline.py: syntax=ok, exceptE=0, bare=0, main=0
  - jupiter.py: syntax=ok, exceptE=1, bare=0, main=0
  - muro_cinco_eventos.py: syntax=ok, exceptE=0, bare=0, main=0
  - muro_lags.py: syntax=ok, exceptE=0, bare=0, main=0
  - precursor_types.py: syntax=ok, exceptE=0, bare=0, main=0
  - risk_calculator.py: syntax=ok, exceptE=0, bare=0, main=0
  - scanner.py: syntax=ok, exceptE=0, bare=0, main=0

### 12. core/shared
- docs:0 py:4 otros:0
- señales d/w/t: 1/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent_base.py: syntax=ok, exceptE=0, bare=0, main=0
  - data_pipeline.py: syntax=ok, exceptE=0, bare=0, main=0
  - geometria_uvg.py: syntax=ok, exceptE=0, bare=0, main=0

### 13. core/snt_engine
- docs:0 py:6 otros:0
- señales d/w/t: 2/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - asi.py: syntax=ok, exceptE=0, bare=0, main=0
  - corpus.py: syntax=ok, exceptE=0, bare=0, main=0
  - friction.py: syntax=ok, exceptE=0, bare=0, main=0
  - nbody.py: syntax=ok, exceptE=0, bare=0, main=0
  - satellization.py: syntax=ok, exceptE=0, bare=0, main=0

### 14. docs
- docs:9 py:0 otros:1
- señales d/w/t: 8/8/5
- docs:
  - DASHBOARD_6TABS_DONE.md: Dashboard 6 tabs DONE [dashboard,watchdog]
  - INGEST_FIX_2026-09-10.md: Ingest Fix — 2026-09-10 [dashboard,watchdog]
  - SESSION_2026-09-10.md: Sesión Sentinel Omega / Concilio — 2026-09-10 → 11 [dashboard,watchdog,telegram]
  - SESSION_2026-09-13.md: Sesión Sentinel Omega — 2026-09-11 → 13 [dashboard,watchdog,telegram]
  - SYSTEM_HEALTH_2026-09-10.md: System Health — 2026-09-10/11 [dashboard,watchdog,telegram]
  - SYSTEM_HEALTH_2026-09-13.md: System Health — 2026-09-13 [dashboard,watchdog,telegram]
  - TRAIN_INGEST_VERDICT_2026-09-10.md: TRAIN / INGEST VERDICT — 2026-09-10 (America/Mexico_City) [dashboard,watchdog]
  - TRAIN_RESTART_2026-09-10.md: TRAIN RESTART — 2026-09-10 [dashboard,watchdog,telegram]
  - WEIGHTS_BACKUP_LIST_PROD_2026-09-10.md: Prod ONNX before wipe 2026-09-10

### 15. docs/audit
- docs:5 py:0 otros:0
- señales d/w/t: 4/0/0
- docs:
  - 00_README.md: Pipeline de auditoría — Sistema Omega
  - 01_pgbouncer_pooling.md: Auditoría — Pooling de conexiones (PgBouncer) [dashboard]
  - 02_cold_storage_export.md: Auditoría — Exportación a almacenamiento frío [dashboard]
  - 03_incident_runbook.md: Auditoría — Runbook de incidentes [dashboard]
  - 04_investigation_queries.md: Auditoría — Consultas de investigación [dashboard]

### 16. docs/audits
- docs:9 py:0 otros:2
- señales d/w/t: 9/9/9
- docs:
  - component_audit_dashboard_watchdog_telegram_20260914_073641.json: [ [dashboard,watchdog,telegram]
  - component_audit_dashboard_watchdog_telegram_20260914_073641.md: Auditoría enfocada: dashboard + watchdog + bot telegram [dashboard,watchdog,telegram]
  - folder_by_folder_review_20260914_073903.json: [ [dashboard,watchdog,telegram]
  - folder_by_folder_review_20260914_073903.md: Revisión carpeta por carpeta (Sentinel Omega) [dashboard,watchdog,telegram]
  - scripts_audit_20260914_073252.json: [ [dashboard,watchdog,telegram]
  - scripts_audit_full_20260914.md: Auditoría completa por script (Sentinel Omega) [dashboard,watchdog,telegram]
  - scripts_audit_summary_20260914_073252.md: Auditoría de scripts Sentinel Omega [dashboard,watchdog,telegram]
  - scripts_audit_with_deploy_20260914_073329.json: [ [dashboard,watchdog,telegram]
  - scripts_audit_with_deploy_20260914_073329.md: Auditoría completa Sentinel Omega + deploy [dashboard,watchdog,telegram]

### 17. infrastructure
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 18. infrastructure/api
- docs:0 py:17 otros:0
- señales d/w/t: 14/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - _http.py: syntax=ok, exceptE=0, bare=0, main=0
  - bolsa.py: syntax=ok, exceptE=1, bare=0, main=0
  - circuit_breaker.py: syntax=ok, exceptE=1, bare=0, main=0
  - correo.py: syntax=ok, exceptE=2, bare=0, main=0
  - crypto.py: syntax=ok, exceptE=5, bare=0, main=0
  - esa_sentinel.py: syntax=ok, exceptE=2, bare=0, main=0
  - geophysical.py: syntax=ok, exceptE=1, bare=0, main=0
  - gfz_kp.py: syntax=ok, exceptE=1, bare=0, main=0
  - google_trends.py: syntax=ok, exceptE=1, bare=0, main=0
  - nasa_neo.py: syntax=ok, exceptE=1, bare=0, main=0
  - noaa.py: syntax=ok, exceptE=5, bare=0, main=0
  - noaa_hazards.py: syntax=ok, exceptE=2, bare=0, main=0
  - openweathermap.py: syntax=ok, exceptE=2, bare=0, main=0
  - schumann.py: syntax=ok, exceptE=3, bare=0, main=0
  - telegram.py: syntax=ok, exceptE=6, bare=0, main=0
  - usgs.py: syntax=ok, exceptE=1, bare=0, main=0

### 19. infrastructure/dashboard
- docs:1 py:5 otros:0
- señales d/w/t: 5/2/4
- docs:
  - README.md: Sentinel Omega Dashboard [dashboard,telegram]
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent_tab.py: syntax=ok, exceptE=3, bare=0, main=0
  - api.py: syntax=ok, exceptE=12, bare=0, main=0
  - app.py: syntax=ok, exceptE=4, bare=0, main=1
  - ask_faq.py: syntax=ok, exceptE=0, bare=0, main=0

### 20. infrastructure/dashboard/static
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 21. infrastructure/dashboard/web
- docs:6 py:0 otros:5
- señales d/w/t: 5/0/1
- docs:
  - components.json: { [dashboard]
  - package-lock.json: { [dashboard,telegram]
  - package.json: { [dashboard]
  - tsconfig.json: {
  - tsconfig.node.json: { [dashboard]
  - web_log.txt: npm notice run sentinel-omega-dashboard@0.1.0 dev [dashboard]

### 22. infrastructure/dashboard/web/dist
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 23. infrastructure/dashboard/web/dist/assets
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 24. infrastructure/dashboard/web/public
- docs:0 py:0 otros:1
- señales d/w/t: 0/0/0

### 25. infrastructure/dashboard/web/src
- docs:0 py:0 otros:4
- señales d/w/t: 0/0/0

### 26. infrastructure/dashboard/web/src/components
- docs:0 py:0 otros:4
- señales d/w/t: 0/0/0

### 27. infrastructure/dashboard/web/src/components/charts
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 28. infrastructure/dashboard/web/src/components/maps
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 29. infrastructure/dashboard/web/src/components/tabs
- docs:0 py:0 otros:11
- señales d/w/t: 0/0/0

### 30. infrastructure/dashboard/web/src/components/ui
- docs:0 py:0 otros:3
- señales d/w/t: 0/0/0

### 31. infrastructure/dashboard/web/src/hooks
- docs:0 py:0 otros:1
- señales d/w/t: 0/0/0

### 32. infrastructure/dashboard/web/src/lib
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 33. infrastructure/database
- docs:2 py:6 otros:0
- señales d/w/t: 2/2/1
- docs:
  - RESTORE_SCHEMA_V11.md: PLACEHOLDER
  - referencia_legacy.json: {
- py:
  - __init__.py: syntax=ok, exceptE=1, bare=0, main=0
  - locf_store.py: syntax=ok, exceptE=4, bare=0, main=0
  - migrate_v11.py: syntax=ok, exceptE=0, bare=0, main=0
  - repository.py: syntax=ok, exceptE=0, bare=0, main=0
  - schema.py: syntax=ok, exceptE=0, bare=0, main=0
  - seed_nodos.py: syntax=ok, exceptE=0, bare=0, main=0

### 34. infrastructure/database/audit
- docs:0 py:0 otros:6
- señales d/w/t: 0/0/0

### 35. infrastructure/database/schema_parts
- docs:0 py:0 otros:4
- señales d/w/t: 0/0/0

### 36. infrastructure/health
- docs:0 py:2 otros:0
- señales d/w/t: 0/2/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - checks.py: syntax=ok, exceptE=5, bare=0, main=1

### 37. infrastructure/logging
- docs:0 py:2 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - formatter.py: syntax=ok, exceptE=1, bare=0, main=0

### 38. infrastructure/messaging
- docs:0 py:6 otros:0
- señales d/w/t: 2/2/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent_bridge.py: syntax=ok, exceptE=7, bare=0, main=0
  - alert_enrichment.py: syntax=ok, exceptE=9, bare=0, main=0
  - alert_service.py: syntax=ok, exceptE=3, bare=0, main=0
  - charts.py: syntax=ok, exceptE=3, bare=0, main=0
  - consenso_vigilante.py: syntax=ok, exceptE=15, bare=0, main=0

### 39. infrastructure/pipeline
- docs:0 py:17 otros:1
- señales d/w/t: 12/1/9
- py:
  - __init__.py: syntax=ok, exceptE=2, bare=0, main=0
  - backcast.py: syntax=ok, exceptE=7, bare=0, main=1
  - clima_gapfill_2026.py: syntax=ok, exceptE=6, bare=0, main=1
  - data_pipeline.py: syntax=ok, exceptE=10, bare=0, main=0
  - data_pipeline_locf_patch.py: syntax=ok, exceptE=4, bare=0, main=0
  - entrenamiento.py: syntax=ok, exceptE=5, bare=0, main=0
  - entrenar_paralelo.py: syntax=ok, exceptE=0, bare=0, main=0
  - juez_cycle_register.py: syntax=ok, exceptE=1, bare=0, main=0
  - layer_runners.py: syntax=ok, exceptE=5, bare=0, main=0
  - legacy_loader.py: syntax=ok, exceptE=0, bare=0, main=0
  - mantenimiento.py: syntax=ok, exceptE=6, bare=0, main=0
  - reporte_engine.py: syntax=ok, exceptE=1, bare=0, main=0
  - reporte_sentinel.py: syntax=ok, exceptE=3, bare=0, main=0
  - scheduler_reportes.py: syntax=ok, exceptE=1, bare=0, main=1
  - sismos_refetch_recent.py: syntax=ok, exceptE=1, bare=0, main=1
  - topologia_cascada.py: syntax=ok, exceptE=3, bare=0, main=1
  - verificacion.py: syntax=ok, exceptE=3, bare=0, main=0

### 40. infrastructure/pipeline/logs
- docs:0 py:0 otros:82
- señales d/w/t: 0/0/0

### 41. infrastructure/telegram
- docs:0 py:2 otros:0
- señales d/w/t: 0/0/2
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - bot.py: syntax=ok, exceptE=2, bare=0, main=0

### 42. infrastructure/watchdog
- docs:0 py:2 otros:0
- señales d/w/t: 1/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - network_watchdog.py: syntax=ok, exceptE=7, bare=0, main=1

### 43. launcher_hex
- docs:0 py:0 otros:13
- señales d/w/t: 0/0/0

### 44. layers
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 45. layers/geodynamic
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 46. layers/geodynamic/alfa1
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=3, bare=0, main=0

### 47. layers/geodynamic/alfa2
- docs:0 py:2 otros:0
- señales d/w/t: 1/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=1, bare=0, main=0

### 48. layers/geodynamic/beta1
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 49. layers/geodynamic/beta2
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 50. layers/geodynamic/delta
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 51. layers/geodynamic/jupiter
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 52. layers/geodynamic/loki
- docs:0 py:1 otros:0
- señales d/w/t: 1/1/0
- py:
  - agent.py: syntax=ok, exceptE=3, bare=0, main=0

### 53. layers/geodynamic/omega
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=2, bare=0, main=0

### 54. layers/geodynamic/padre
- docs:0 py:2 otros:0
- señales d/w/t: 1/0/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 55. layers/lottery_standalone
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 56. logs
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 57. notebooks
- docs:2 py:0 otros:1
- señales d/w/t: 2/1/1
- docs:
  - README.md: Sentinel Omega — Jupyter Notebooks [dashboard,watchdog,telegram]
  - requirements_jupyter.txt: Sentinel Omega — Jupyter Requirements [dashboard]

### 58. sentinel_omega
- docs:5 py:1 otros:0
- señales d/w/t: 5/3/3
- docs:
  - CHANGELOG.md: Changelog - Sentinel Omega [dashboard,watchdog,telegram]
  - CLAUDE.md: Sentinel Omega [dashboard,watchdog,telegram]
  - README.md: Sentinel Omega v2.5.4 — The Third Act [dashboard,watchdog,telegram]
  - pyproject.toml: [build-system] [dashboard]
  - requirements.txt: Sentinel Omega — dependencias core [dashboard]
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 59. sentinel_omega/config
- docs:1 py:3 otros:0
- señales d/w/t: 2/0/3
- docs:
  - sentinel.yaml: app: [dashboard,telegram]
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - onnx_config.py: syntax=ok, exceptE=0, bare=0, main=0
  - sentinel_config.py: syntax=ok, exceptE=2, bare=0, main=0

### 60. sentinel_omega/core
- docs:0 py:3 otros:0
- señales d/w/t: 1/0/2
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - onnx_engine.py: syntax=ok, exceptE=4, bare=0, main=0
  - onnx_mixin.py: syntax=ok, exceptE=2, bare=0, main=0

### 61. sentinel_omega/core/delta_enriched
- docs:0 py:7 otros:0
- señales d/w/t: 7/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - composite.py: syntax=ok, exceptE=1, bare=0, main=1
  - cross.py: syntax=ok, exceptE=2, bare=0, main=0
  - delta_engine.py: syntax=ok, exceptE=1, bare=0, main=0
  - fetchers.py: syntax=ok, exceptE=13, bare=0, main=0
  - historico.py: syntax=ok, exceptE=3, bare=0, main=1
  - market_mapping.py: syntax=ok, exceptE=0, bare=0, main=0

### 62. sentinel_omega/core/firmas
- docs:0 py:3 otros:0
- señales d/w/t: 2/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - cimatica.py: syntax=ok, exceptE=2, bare=0, main=0
  - signature_engine.py: syntax=ok, exceptE=2, bare=0, main=0

### 63. sentinel_omega/core/juez
- docs:0 py:3 otros:0
- señales d/w/t: 0/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - juez.py: syntax=ok, exceptE=0, bare=0, main=0
  - pesos.py: syntax=ok, exceptE=0, bare=0, main=0

### 64. sentinel_omega/core/precursor
- docs:0 py:9 otros:0
- señales d/w/t: 2/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - assertivity.py: syntax=ok, exceptE=0, bare=0, main=0
  - baseline.py: syntax=ok, exceptE=0, bare=0, main=0
  - jupiter.py: syntax=ok, exceptE=1, bare=0, main=0
  - muro_cinco_eventos.py: syntax=ok, exceptE=0, bare=0, main=0
  - muro_lags.py: syntax=ok, exceptE=0, bare=0, main=0
  - precursor_types.py: syntax=ok, exceptE=0, bare=0, main=0
  - risk_calculator.py: syntax=ok, exceptE=0, bare=0, main=0
  - scanner.py: syntax=ok, exceptE=0, bare=0, main=0

### 65. sentinel_omega/core/shared
- docs:0 py:4 otros:0
- señales d/w/t: 1/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent_base.py: syntax=ok, exceptE=0, bare=0, main=0
  - data_pipeline.py: syntax=ok, exceptE=0, bare=0, main=0
  - geometria_uvg.py: syntax=ok, exceptE=0, bare=0, main=0

### 66. sentinel_omega/core/snt_engine
- docs:0 py:6 otros:0
- señales d/w/t: 2/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - asi.py: syntax=ok, exceptE=0, bare=0, main=0
  - corpus.py: syntax=ok, exceptE=0, bare=0, main=0
  - friction.py: syntax=ok, exceptE=0, bare=0, main=0
  - nbody.py: syntax=ok, exceptE=0, bare=0, main=0
  - satellization.py: syntax=ok, exceptE=0, bare=0, main=0

### 67. sentinel_omega/docs
- docs:4 py:0 otros:0
- señales d/w/t: 4/4/2
- docs:
  - DASHBOARD_6TABS_DONE.md: Dashboard 6 tabs DONE [dashboard,watchdog]
  - INGEST_FIX_2026-09-10.md: Ingest Fix — 2026-09-10 [dashboard,watchdog]
  - SESSION_2026-09-10.md: Sesión Sentinel Omega / Concilio — 2026-09-10 → 11 [dashboard,watchdog,telegram]
  - SYSTEM_HEALTH_2026-09-10.md: System Health — 2026-09-10/11 [dashboard,watchdog,telegram]

### 68. sentinel_omega/infrastructure
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 69. sentinel_omega/infrastructure/api
- docs:0 py:17 otros:0
- señales d/w/t: 14/0/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - _http.py: syntax=ok, exceptE=0, bare=0, main=0
  - bolsa.py: syntax=ok, exceptE=1, bare=0, main=0
  - circuit_breaker.py: syntax=ok, exceptE=1, bare=0, main=0
  - correo.py: syntax=ok, exceptE=2, bare=0, main=0
  - crypto.py: syntax=ok, exceptE=5, bare=0, main=0
  - esa_sentinel.py: syntax=ok, exceptE=2, bare=0, main=0
  - geophysical.py: syntax=ok, exceptE=1, bare=0, main=0
  - gfz_kp.py: syntax=ok, exceptE=1, bare=0, main=0
  - google_trends.py: syntax=ok, exceptE=1, bare=0, main=0
  - nasa_neo.py: syntax=ok, exceptE=1, bare=0, main=0
  - noaa.py: syntax=ok, exceptE=5, bare=0, main=0
  - noaa_hazards.py: syntax=ok, exceptE=2, bare=0, main=0
  - openweathermap.py: syntax=ok, exceptE=2, bare=0, main=0
  - schumann.py: syntax=ok, exceptE=3, bare=0, main=0
  - telegram.py: syntax=ok, exceptE=6, bare=0, main=0
  - usgs.py: syntax=ok, exceptE=1, bare=0, main=0

### 70. sentinel_omega/infrastructure/dashboard
- docs:1 py:5 otros:0
- señales d/w/t: 5/2/4
- docs:
  - README.md: Sentinel Omega Dashboard [dashboard,telegram]
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent_tab.py: syntax=ok, exceptE=3, bare=0, main=0
  - api.py: syntax=ok, exceptE=12, bare=0, main=0
  - app.py: syntax=ok, exceptE=4, bare=0, main=1
  - ask_faq.py: syntax=ok, exceptE=0, bare=0, main=0

### 71. sentinel_omega/infrastructure/dashboard/static
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 72. sentinel_omega/infrastructure/dashboard/web
- docs:5 py:0 otros:4
- señales d/w/t: 4/0/1
- docs:
  - components.json: { [dashboard]
  - package-lock.json: { [dashboard,telegram]
  - package.json: { [dashboard]
  - tsconfig.json: {
  - tsconfig.node.json: { [dashboard]

### 73. sentinel_omega/infrastructure/dashboard/web/dist
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 74. sentinel_omega/infrastructure/dashboard/web/dist/assets
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 75. sentinel_omega/infrastructure/dashboard/web/public
- docs:0 py:0 otros:1
- señales d/w/t: 0/0/0

### 76. sentinel_omega/infrastructure/dashboard/web/src
- docs:0 py:0 otros:4
- señales d/w/t: 0/0/0

### 77. sentinel_omega/infrastructure/dashboard/web/src/components
- docs:0 py:0 otros:4
- señales d/w/t: 0/0/0

### 78. sentinel_omega/infrastructure/dashboard/web/src/components/charts
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 79. sentinel_omega/infrastructure/dashboard/web/src/components/maps
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 80. sentinel_omega/infrastructure/dashboard/web/src/components/tabs
- docs:0 py:0 otros:11
- señales d/w/t: 0/0/0

### 81. sentinel_omega/infrastructure/dashboard/web/src/components/ui
- docs:0 py:0 otros:3
- señales d/w/t: 0/0/0

### 82. sentinel_omega/infrastructure/dashboard/web/src/hooks
- docs:0 py:0 otros:1
- señales d/w/t: 0/0/0

### 83. sentinel_omega/infrastructure/dashboard/web/src/lib
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 84. sentinel_omega/infrastructure/database
- docs:2 py:6 otros:0
- señales d/w/t: 2/2/1
- docs:
  - RESTORE_SCHEMA_V11.md: PLACEHOLDER
  - referencia_legacy.json: {
- py:
  - __init__.py: syntax=ok, exceptE=1, bare=0, main=0
  - locf_store.py: syntax=ok, exceptE=4, bare=0, main=0
  - migrate_v11.py: syntax=ok, exceptE=0, bare=0, main=0
  - repository.py: syntax=ok, exceptE=0, bare=0, main=0
  - schema.py: syntax=ok, exceptE=0, bare=0, main=0
  - seed_nodos.py: syntax=ok, exceptE=0, bare=0, main=0

### 85. sentinel_omega/infrastructure/database/audit
- docs:0 py:0 otros:6
- señales d/w/t: 0/0/0

### 86. sentinel_omega/infrastructure/database/schema_parts
- docs:0 py:0 otros:4
- señales d/w/t: 0/0/0

### 87. sentinel_omega/infrastructure/health
- docs:0 py:2 otros:0
- señales d/w/t: 0/2/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - checks.py: syntax=ok, exceptE=5, bare=0, main=1

### 88. sentinel_omega/infrastructure/logging
- docs:0 py:2 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - formatter.py: syntax=ok, exceptE=1, bare=0, main=0

### 89. sentinel_omega/infrastructure/messaging
- docs:0 py:6 otros:0
- señales d/w/t: 2/2/3
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent_bridge.py: syntax=ok, exceptE=7, bare=0, main=0
  - alert_enrichment.py: syntax=ok, exceptE=9, bare=0, main=0
  - alert_service.py: syntax=ok, exceptE=3, bare=0, main=0
  - charts.py: syntax=ok, exceptE=3, bare=0, main=0
  - consenso_vigilante.py: syntax=ok, exceptE=15, bare=0, main=0

### 90. sentinel_omega/infrastructure/pipeline
- docs:0 py:17 otros:1
- señales d/w/t: 12/1/9
- py:
  - __init__.py: syntax=ok, exceptE=2, bare=0, main=0
  - backcast.py: syntax=ok, exceptE=7, bare=0, main=1
  - clima_gapfill_2026.py: syntax=ok, exceptE=6, bare=0, main=1
  - data_pipeline.py: syntax=ok, exceptE=10, bare=0, main=0
  - data_pipeline_locf_patch.py: syntax=ok, exceptE=4, bare=0, main=0
  - entrenamiento.py: syntax=ok, exceptE=5, bare=0, main=0
  - entrenar_paralelo.py: syntax=ok, exceptE=0, bare=0, main=0
  - juez_cycle_register.py: syntax=ok, exceptE=1, bare=0, main=0
  - layer_runners.py: syntax=ok, exceptE=5, bare=0, main=0
  - legacy_loader.py: syntax=ok, exceptE=0, bare=0, main=0
  - mantenimiento.py: syntax=ok, exceptE=6, bare=0, main=0
  - reporte_engine.py: syntax=ok, exceptE=1, bare=0, main=0
  - reporte_sentinel.py: syntax=ok, exceptE=3, bare=0, main=0
  - scheduler_reportes.py: syntax=ok, exceptE=1, bare=0, main=1
  - sismos_refetch_recent.py: syntax=ok, exceptE=1, bare=0, main=1
  - topologia_cascada.py: syntax=ok, exceptE=3, bare=0, main=1
  - verificacion.py: syntax=ok, exceptE=3, bare=0, main=0

### 91. sentinel_omega/infrastructure/pipeline/logs
- docs:0 py:0 otros:57
- señales d/w/t: 0/0/0

### 92. sentinel_omega/infrastructure/telegram
- docs:0 py:2 otros:0
- señales d/w/t: 0/0/2
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - bot.py: syntax=ok, exceptE=2, bare=0, main=0

### 93. sentinel_omega/infrastructure/watchdog
- docs:0 py:2 otros:0
- señales d/w/t: 1/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - network_watchdog.py: syntax=ok, exceptE=7, bare=0, main=1

### 94. sentinel_omega/layers
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 95. sentinel_omega/layers/geodynamic
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 96. sentinel_omega/layers/geodynamic/alfa1
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=3, bare=0, main=0

### 97. sentinel_omega/layers/geodynamic/alfa2
- docs:0 py:2 otros:0
- señales d/w/t: 1/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=1, bare=0, main=0

### 98. sentinel_omega/layers/geodynamic/beta1
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 99. sentinel_omega/layers/geodynamic/beta2
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 100. sentinel_omega/layers/geodynamic/delta
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 101. sentinel_omega/layers/geodynamic/jupiter
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 102. sentinel_omega/layers/geodynamic/loki
- docs:0 py:1 otros:0
- señales d/w/t: 1/1/0
- py:
  - agent.py: syntax=ok, exceptE=3, bare=0, main=0

### 103. sentinel_omega/layers/geodynamic/omega
- docs:0 py:2 otros:0
- señales d/w/t: 0/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=2, bare=0, main=0

### 104. sentinel_omega/layers/geodynamic/padre
- docs:0 py:2 otros:0
- señales d/w/t: 1/0/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - agent.py: syntax=ok, exceptE=0, bare=0, main=0

### 105. sentinel_omega/layers/lottery_standalone
- docs:0 py:1 otros:0
- señales d/w/t: 0/0/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0

### 106. tests
- docs:0 py:15 otros:0
- señales d/w/t: 9/5/8
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_agents.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_api_connectors.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_cimatica_correo.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_consenso_vigilante.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_entrenar_paralelo.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_firmas.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_infrastructure.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_jupiter.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_normalizacion.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_pipeline.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_precursor.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_reporte_agentes.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_schumann_filter.py: syntax=ok, exceptE=0, bare=0, main=0
  - test_snt_engine.py: syntax=ok, exceptE=1, bare=0, main=0

## ROOT: /home/deamon/workspaces/deploy
- directorios revisados: 1
- docs revisados: 2
- scripts py revisados: 10
- syntax fail: 0

### 1. .
- docs:2 py:10 otros:20
- señales d/w/t: 7/1/7
- docs:
  - ATAJO_IOS.md: Atajos de iOS — Roy en el bolsillo [dashboard]
  - DEPLOY.md: Despliegue de Sentinel Omega — servidor permanente [dashboard,watchdog,telegram]
- py:
  - aciertos_reporte.py: syntax=ok, exceptE=2, bare=0, main=1
  - bootstrap_omega.py: syntax=ok, exceptE=0, bare=0, main=1
  - enviar_correos.py: syntax=ok, exceptE=0, bare=0, main=1
  - generar_reporte.py: syntax=ok, exceptE=2, bare=0, main=1
  - jupiter_correlaciones.py: syntax=ok, exceptE=1, bare=0, main=1
  - rebuild_completo.py: syntax=ok, exceptE=2, bare=0, main=1
  - reporte_ejecutivo.py: syntax=ok, exceptE=3, bare=0, main=1
  - reporte_periodico.py: syntax=ok, exceptE=1, bare=0, main=1
  - tuning_db.py: syntax=ok, exceptE=0, bare=0, main=1
  - verificacion_juez.py: syntax=ok, exceptE=0, bare=0, main=1

## ROOT: /home/deamon/consensus-expert-agent
- directorios revisados: 10
- docs revisados: 12
- scripts py revisados: 28
- syntax fail: 0

### 1. .
- docs:7 py:6 otros:11
- señales d/w/t: 11/9/10
- docs:
  - AGENTS.md: AGENTS.md — consensus-expert-agent (Concilio) [dashboard,watchdog,telegram]
  - CHANGELOG.md: [docs] - 2026-09-13 — Auditoría GitHub (Claude/Copilot) [dashboard,watchdog,telegram]
  - CONCILIO.md: Sequential Concilio [dashboard,watchdog,telegram]
  - README.md: Consenso de Expertos Multi-Modelo — Concilio [dashboard,watchdog,telegram]
  - TELEGRAM_BOT_README.md: Telegram Bot — Consensus Expert Agent + Sentinel Omega Bridge [dashboard,watchdog,telegram]
  - config.yaml: ============================================================================= [dashboard,watchdog,telegram]
  - requirements.txt: rich>=13.7.0 [dashboard,telegram]
- py:
  - alert_queue.py: syntax=ok, exceptE=2, bare=0, main=1
  - cli.py: syntax=ok, exceptE=1, bare=0, main=0
  - main.py: syntax=ok, exceptE=1, bare=0, main=1
  - smoke_fast.py: syntax=ok, exceptE=0, bare=0, main=0
  - telegram_bot.py: syntax=ok, exceptE=16, bare=0, main=1
  - web_ui.py: syntax=ok, exceptE=6, bare=0, main=0

### 2. agents
- docs:0 py:5 otros:0
- señales d/w/t: 3/0/0
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - base_agent.py: syntax=ok, exceptE=3, bare=0, main=0
  - coder.py: syntax=ok, exceptE=0, bare=0, main=0
  - optimizer.py: syntax=ok, exceptE=0, bare=0, main=0
  - researcher.py: syntax=ok, exceptE=0, bare=0, main=0

### 3. deploy
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 4. docs
- docs:4 py:0 otros:0
- señales d/w/t: 4/4/4
- docs:
  - CONCILIO.md: Sequential Concilio [dashboard,watchdog,telegram]
  - FUNCIONAMIENTO_TELEGRAM.md: Funcionamiento — Bot Telegram + Mini App (Consensus / Concilio) [dashboard,watchdog,telegram]
  - HANDOFF_GEMMA_MEMORIA.md: Handoff — Cargar memoria al modelo Gemma (árbitro del Concilio) [dashboard,watchdog,telegram]
  - TELEGRAM_CONSENSUS_TODO.md: Telegram + Consensus — trabajo pendiente (cuando X-Deamon esté online) [dashboard,watchdog,telegram]

### 5. engine
- docs:0 py:6 otros:3
- señales d/w/t: 1/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - concilio_session.py: syntax=ok, exceptE=0, bare=0, main=0
  - model_lifecycle.py: syntax=ok, exceptE=4, bare=0, main=0
  - ollama_lifecycle.py: syntax=ok, exceptE=4, bare=0, main=0
  - orchestrator.py: syntax=ok, exceptE=8, bare=0, main=0
  - router.py: syntax=ok, exceptE=0, bare=0, main=0

### 6. logs
- docs:0 py:0 otros:2
- señales d/w/t: 0/0/0

### 7. memory
- docs:0 py:10 otros:0
- señales d/w/t: 8/1/1
- py:
  - __init__.py: syntax=ok, exceptE=0, bare=0, main=0
  - anti_injection.py: syntax=ok, exceptE=0, bare=0, main=0
  - blackboard.py: syntax=ok, exceptE=1, bare=0, main=0
  - concilio_session.py: syntax=ok, exceptE=0, bare=0, main=0
  - concilio_store.py: syntax=ok, exceptE=0, bare=0, main=0
  - memory_pack.py: syntax=ok, exceptE=0, bare=0, main=0
  - persistent_store.py: syntax=ok, exceptE=0, bare=0, main=0
  - repository_context.py: syntax=ok, exceptE=2, bare=0, main=0
  - session_store.py: syntax=ok, exceptE=0, bare=0, main=0
  - shared_context.py: syntax=ok, exceptE=0, bare=0, main=0

### 8. modelfiles
- docs:1 py:0 otros:9
- señales d/w/t: 0/0/0
- docs:
  - README.md: Thin Modelfiles (Concilio)

### 9. scripts
- docs:0 py:1 otros:2
- señales d/w/t: 1/0/0
- py:
  - build_memory_pack.py: syntax=ok, exceptE=0, bare=0, main=1

### 10. static
- docs:0 py:0 otros:1
- señales d/w/t: 0/0/0
