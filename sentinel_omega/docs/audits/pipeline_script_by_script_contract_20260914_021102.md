# Pipeline script-by-script contract audit (20260914_021102)

Fuente contrato: README.md, AGENTS.md, CLAUDE.md, CHANGELOG.md (raíz y espejo sentinel_omega/).

| Script | Estado | Ref docs | Evidencia de implementación | Riesgo rápido |
|---|---|---:|---|---|
| infrastructure/pipeline/backcast.py | OK | 2 | main, db, net, sched | except Exception=7 |
| infrastructure/pipeline/clima_gapfill_2026.py | SIN_CONTRATO_DIRECTO | 0 | main, cli, db, net | except Exception=6 |
| infrastructure/pipeline/data_pipeline.py | OK | 6 | db, net | except Exception=10 |
| infrastructure/pipeline/data_pipeline_locf_patch.py | SIN_CONTRATO_DIRECTO | 0 | - | except Exception=4 |
| infrastructure/pipeline/entrenamiento.py | SIN_CONTRATO_DIRECTO | 0 | db, net | except Exception=5 |
| infrastructure/pipeline/entrenar_paralelo.py | SIN_CONTRATO_DIRECTO | 0 | db | except Exception=0 |
| infrastructure/pipeline/juez_cycle_register.py | SIN_CONTRATO_DIRECTO | 0 | - | except Exception=1 |
| infrastructure/pipeline/layer_runners.py | OK | 2 | - | except Exception=5 |
| infrastructure/pipeline/legacy_loader.py | OK | 2 | db | except Exception=0 |
| infrastructure/pipeline/mantenimiento.py | SIN_CONTRATO_DIRECTO | 0 | db | except Exception=6 |
| infrastructure/pipeline/reporte_engine.py | SIN_CONTRATO_DIRECTO | 0 | db | except Exception=1 |
| infrastructure/pipeline/reporte_sentinel.py | SIN_CONTRATO_DIRECTO | 0 | db, sched | except Exception=3 |
| infrastructure/pipeline/scheduler_reportes.py | SIN_CONTRATO_DIRECTO | 0 | main, sched | except Exception=1 |
| infrastructure/pipeline/sismos_refetch_recent.py | SIN_CONTRATO_DIRECTO | 0 | main, cli, db, net | except Exception=1 |
| infrastructure/pipeline/topologia_cascada.py | SIN_CONTRATO_DIRECTO | 0 | main, cli, db, net, sched | except Exception=3 |
| infrastructure/pipeline/verificacion.py | OK | 2 | db | except Exception=3 |

## Referencias documentales por script
### infrastructure/pipeline/backcast.py — OK
- module_doc: Historical Backcast Pipeline — ONE-TIME initial load. Loads 32 years of real data (1994-2026) from scientific APIs into SQLite. Once loaded, this script never runs again (idempoten
- note: -
- refs:
  - README.md:426 -> │   │   ├── backcast.py                  # Carga histórica one-time (1994-2025, 1H)
  - sentinel_omega/README.md:426 -> │   │   ├── backcast.py                  # Carga histórica one-time (1994-2025, 1H)

### infrastructure/pipeline/clima_gapfill_2026.py — SIN_CONTRATO_DIRECTO
- module_doc: (sin docstring inicial)
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/data_pipeline.py — OK
- module_doc: Data Pipeline — fetches from real APIs and formats for agent ingest(). Single pipeline: all 6 agents are part of one system. Agent data mapping: - Alfa-1: NOAA OMNI (Bz, solar wind
- note: -
- refs:
  - README.md:381 -> │   │   ├── data_pipeline.py             # Pipeline base para ingesta de datos
  - README.md:424 -> │   │   ├── data_pipeline.py             # Pipeline maestro con LOCF
  - CLAUDE.md:176 -> │   │   ├── data_pipeline.py     # Pipeline base class
  - sentinel_omega/README.md:381 -> │   │   ├── data_pipeline.py             # Pipeline base para ingesta de datos
  - sentinel_omega/README.md:424 -> │   │   ├── data_pipeline.py             # Pipeline maestro con LOCF
  - sentinel_omega/CLAUDE.md:176 -> │   │   ├── data_pipeline.py     # Pipeline base class

### infrastructure/pipeline/data_pipeline_locf_patch.py — SIN_CONTRATO_DIRECTO
- module_doc: Upgrade GeodynamicPipeline LOCF to persistent DB (tbl_locf_cache). Import once (launcher / data_pipeline package) to patch _locf_get/_locf_set and add bind_repository.
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/entrenamiento.py — SIN_CONTRATO_DIRECTO
- module_doc: Entrenamiento de firmas — two-phase training over the 30-year backcast. Fase 1 (reconocimiento, sin castigo): For every significant event in the historical catalog, extract the pre
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/entrenar_paralelo.py — SIN_CONTRATO_DIRECTO
- module_doc: Entrenamiento paralelo por BOT — mismo resultado que el secuencial, en fracción del tiempo. Idea (de Elán, con el eje correcto): partir el trabajo y unir al final. El eje que NO fr
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/juez_cycle_register.py — SIN_CONTRATO_DIRECTO
- module_doc: Register Juez predictions for Padre + every agent in agent_signals. Called from launcher after consensus. Ventana adaptativa (2h floor, lag empírica, tope 90d).
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/layer_runners.py — OK
- module_doc: Layer Runner — orchestrates fetch → ingest → analyze → consensus. Agents: Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Jupiter, Omega, Loki, Padre. Hierarchical validation: 1. All agents
- note: -
- refs:
  - README.md:425 -> │   │   ├── layer_runners.py             # GeodynamicLayerRunner (8 agentes: SNT×5 + Omega + Loki + Padre)
  - sentinel_omega/README.md:425 -> │   │   ├── layer_runners.py             # GeodynamicLayerRunner (8 agentes: SNT×5 + Omega + Loki + Padre)

### infrastructure/pipeline/legacy_loader.py — OK
- module_doc: Legacy Data Loader — imports from CEREBRO_GOD.db and TITAN_MEMORY.db for SNT backtesting and historical analysis. CEREBRO_GOD.db schema: - historicos: 11,374 rows (1994–2026), dail
- note: -
- refs:
  - README.md:427 -> │   │   └── legacy_loader.py             # Cargador de datos TITAN legacy
  - sentinel_omega/README.md:427 -> │   │   └── legacy_loader.py             # Cargador de datos TITAN legacy

### infrastructure/pipeline/mantenimiento.py — SIN_CONTRATO_DIRECTO
- module_doc: Mantenimiento — barrido diario del historial operativo. Los ciclos escriben todo el día en las tablas operativas (cada ~2h). Una vez al día, el barrido se queda con lo SIGNIFICANTE
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/reporte_engine.py — SIN_CONTRATO_DIRECTO
- module_doc: Sentinel Omega — ReportEngine unificado (refactor) Capa DRY sobre reporte_sentinel.py — mantiene compatibilidad total. Uso nuevo (recomendado): from sentinel_omega.infrastructure.p
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/reporte_sentinel.py — SIN_CONTRATO_DIRECTO
- module_doc: Sentinel Omega — Generador de Reportes ======================================= Tres reportes independientes: 1. reporte_general(db_path) → resumen global de TODOS los bots (cada 2h
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/scheduler_reportes.py — SIN_CONTRATO_DIRECTO
- module_doc: Sentinel Omega — Scheduler de Reportes ======================================= Corre en background junto al launcher principal. Frecuencias según los docstrings de reporte_sentinel
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/sismos_refetch_recent.py — SIN_CONTRATO_DIRECTO
- module_doc: (sin docstring inicial)
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/topologia_cascada.py — SIN_CONTRATO_DIRECTO
- module_doc: (sin docstring inicial)
- note: No referencia explícita por nombre en README/AGENTS/CLAUDE/CHANGELOG.
- refs: ninguna explícita por nombre

### infrastructure/pipeline/verificacion.py — OK
- module_doc: Verificación del Juez — real vs predicción, cada 2 horas (mismo ritmo del ciclo). Cada ciclo del Padre (~2 h) registra predicciones; el Juez confronta las pendientes cuya ventana y
- note: -
- refs:
  - CLAUDE.md:231 -> por fila; ritmo auto-impuesto en `pipeline/verificacion.py`).
  - sentinel_omega/CLAUDE.md:231 -> por fila; ritmo auto-impuesto en `pipeline/verificacion.py`).
