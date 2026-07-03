# AGENTS.md — Estándar de trabajo (Fractal Core Research)

Este archivo define cómo trabajamos aquí — sea una persona o una IA. Léelo antes
de tocar código. Es el estándar del workspace Fractal Core Research y aplica a
proyectos como Sentinel Omega y DAEMON-X.

> Referencia: espejo del repo `The-shadow-Node-Theory` (ver `CONTRIBUTING.md`).

## Principios (rápido y claro)

- La verdad técnica manda: lo que compartas debe poder reproducirse desde
  scripts y fuentes primarias.
- Datos reales, nada de datos inventados en producción. Si derivaste algo,
  cita la fuente.
- No subir cosas frágiles a `main`. Prueba en ramas, integra solo lo verificado.

## Flujo de trabajo

1. Crea una rama desde `main` con nombre descriptivo (ej: `claude/nueva-capa`).
   No trabajes directo en `main`.
2. Cambios chicos y enfocados: docstrings, tests y reproducibilidad.
3. Actualiza `CHANGELOG.md` si hay cambios relevantes.
4. Corre las pruebas en tu máquina antes de pushear.
5. Abre un PR hacia `main` y explica qué y por qué.
6. No se mergea hasta que CI esté verde.

### Revisión de Pull Requests

Incluye en cada PR un checklist para el revisor:
- [ ] ¿Actualizaste las fuentes/documentación primaria?
- [ ] ¿Pasaron las pruebas localmente?
- [ ] ¿No hay secretos ni datos crudos en el diff?
- [ ] ¿README/docstrings/CHANGELOG actualizados?

Si no hay respuesta en 48 horas, se puede hacer un ping amable.

## Convención de commits — 简单 (Conventional Commits)

Usamos asunto en inglés con prefijo:
- `feat:` nueva funcionalidad
- `fix:` corrección
- `docs:` documentación
- `data:` cambios en datasets
- `refactor:` reorganización sin cambiar comportamiento
- `chore:` mantenimiento
- `test:` tests

Ej: `feat: add crypto layer consensus engine`

## Estándares de código

- Python >= 3.10. Sigue PEP 8 y añade docstrings en módulos y funciones.
- Linter: `flake8` (config en `.flake8`).
- Formato automático: `black` e `isort`.

Antes de commitear, corre:

```bash
isort .
black .
flake8 .
```

Notebooks: limpia outputs (jupyter nbconvert --clear-output) y, cuando puedas,
convierte a scripts .py para facilitar diffs.

Documenta las fuentes de datos primarias en el script o en un `sources.md`.

## Tests y calidad

- Usamos `pytest`. Añade tests unitarios o de integración según corresponda.
- Cobertura mínima objetivo: 80% (pytest-cov).

Ejecuta:

```bash
pytest tests/ --cov=. --cov-report=term
```

Corre todo localmente antes de abrir PR; CI lo volverá a ejecutar.

## Dependencias y entornos

- Declara deps en `requirements.txt` o `pyproject.toml`.
- No subas entornos virtuales (.venv/, env/).
- Para añadir librerías: instala con `pip`/`poetry` y actualiza el archivo de
  dependencias acordado.
- Usa un entorno virtual (venv/conda).

## Seguridad — NUNCA commitear

- Secretos (API keys, tokens, credenciales). `.env` debe estar en `.gitignore`.
- PHI o datos propietarios.
- Bases de datos generadas en runtime (*.db, *.sqlite).
- No poner SNT_LOG_LEVEL en DEBUG en producción.

Recomendamos hooks de pre-commit con `detect-secrets` o `gitleaks`.

## Datos grandes / binarios

- No subir archivos >100 MB al repo. Usa Git LFS o DVC para datos pesados.
- Deja un `README` o `sources.md` explicando dónde obtener los datos y cómo
  reproducirlos.

## Versionado y releases

- Versionado semántico: `vMAJOR.MINOR.PATCH`.
- Mantén `CHANGELOG.md` con formato Keep a Changelog.

## Seguimiento y trazabilidad

- Código en GitHub + tareas en Asana + docs en Notion.
- Cada PR debe referenciar issue/tarea (ej. `Closes #123` o `Relates to ASANA-456`).
- Nombra ramas para conectar con la tarea si es posible.

## Reporte de seguridad

No abras un issue público para vulnerabilidades. Contacta a:
elan.zainos.corona@gmail.com

## Pre-commit (recomendado)

Instala hooks con `.pre-commit-config.yaml` similar al siguiente:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

Instálalos con `pre-commit install` y, si quieres, ejecuta `pre-commit run --all-files`.

---

Si quieres que lo haga aún más casual o que cambie el tono (por ejemplo usar "vos"
u otro registro), dime y lo ajusto. Este archivo está ubicado ahora en
`sentinel_omega/AGENTS.md` para que esté dentro del paquete principal.
