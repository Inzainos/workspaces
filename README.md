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
- Scripts de despliegue local/servidor y dashboard.
- Publicación y versionado de reportes operativos.
- Workflows de seguridad, análisis y ejecución automática en GitHub Actions.