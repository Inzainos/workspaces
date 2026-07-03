# Fractal Core Research — Workspaces (resumen)

Este repo agrupa los proyectos del workspace Fractal Core Research, sobre todo
Sentinel Omega. Aquí encuentras los agentes, la orquestación y los conectores
de datos.

IMPORTANTE: Lee `sentinel_omega/AGENTS.md` antes de contribuir — ahí está el
estándar de trabajo obligatorio.

Estado y ramas

- Rama principal: `main` (solo código verificado)
- Desarrollo en ramas por proyecto: `feature/...`, `claude/...`, `docs/...`.

Requisitos rápidos

- Python >= 3.10
- Instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r sentinel_omega/requirements.txt
```

Cómo ejecutar (rápido)

- Tests:

```bash
pytest tests/ --cov=. --cov-report=term
```

- Para ver cómo se lanza el sistema, revisa `sentinel_omega/launcher.py`.

Contribuciones

- Estándar de trabajo: `sentinel_omega/AGENTS.md` (léelo antes de hacer cambios).
- Abre PRs desde ramas descriptivas y sigue el checklist.

Licencia

Revisa `LICENSE` en la raíz para los términos.
