# Workspaces

Repositorio base para **todos los proyectos** del workspace.  
Actualmente contiene como proyecto principal **Sentinel Omega** y su operación
completa (código, despliegue, reportes y automatizaciones).

## Reglas operativas (AGENTS.md)

Este repositorio usa las reglas de `AGENTS.md` como guía central para agentes y
colaboradores. Puntos clave:

- Secretos solo por variables de entorno (nunca hardcodeados).
- Cero datos sintéticos: faltantes como `NULL` y datos derivados etiquetados.
- `sentinel_omega/data/` no se versiona y puede no existir en entornos limpios.
- Reportes versionados en `estado/historial/` (no sobrescribir historial).
- Migraciones de esquema solo forward-only.
- Antes de commitear cambios de código, los tests deben pasar.

## Estructura actual del repositorio

```text
workspaces/
├── AGENTS.md
├── CHANGELOG.md
├── LICENSE
├── README.md
├── .github/
│   └── workflows/
│       ├── bandit.yml
│       ├── codeql.yml
│       ├── copy-delta-to-snt.yml
│       └── roy-vigilante.yml
├── deploy/
│   ├── .env.example
│   ├── ATAJO_IOS.md
│   ├── DEPLOY.md
│   ├── generar_reporte.py
│   ├── install.sh
│   ├── run_windows.bat
│   ├── sentinel-omega-dashboard.service
│   └── sentinel-omega.service
├── estado/
│   ├── REPORTE.md
│   └── historial/
│       └── 2026/
├── sentinel_omega/
│   ├── CLAUDE.md
│   ├── README.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── launcher.py
│   ├── reboot.py
│   ├── shutdown.py
│   ├── orchestrator.py
│   ├── config/
│   ├── core/
│   ├── docs/
│   ├── infrastructure/
│   ├── layers/
│   ├── models/
│   ├── notebooks/
│   └── tests/
└── staging/
```

## Qué contiene hoy

- Plataforma Sentinel Omega para detección de precursores de eventos naturales.
- Pipeline de adquisición/procesamiento, entrenamiento y consenso multiagente.
- **Entrenamiento multi-evento** (Fase 1b): sísmico + volcánico + solar + financiero.
- **delta_enriched**: acoplamiento geofísico-financiero (cross-correlation crypto/BTC).
- **Omega bot**: memoria del ritmo cósmico (luna, Schumann, correlaciones históricas).
- Scripts de despliegue local/servidor, dashboard y rebuild completo.
- Publicación y versionado de reportes operativos.
- Workflows de seguridad, análisis y ejecución automática en GitHub Actions.

## Rebuild Completo

Para reconstruir la base de datos con entrenamiento de punta a punta:

```bash
# En server con virtualenv activado:
nohup python deploy/rebuild_completo.py > estado/rebuild.log 2>&1 &
```

El script:
1. Para launcher activo
2. Vacía memoria aprendida (conserva backcast + fase viva del Juez)
3. Migración DB v6 + índices + vistas
4. Tuning (ANALYZE + PRAGMA optimize)
5. Entrenamiento: Fase 1 + 1b (multi-evento) + Fase 2 + lags + correlaciones
6. Disciplina de trasfondo + barrido diario
7. VACUUM + compactación
8. Genera reportes (REPORTE.md + REPORTE_EJECUTIVO.md)

Reporte final en `estado/REPORTE_REBUILD.md`.