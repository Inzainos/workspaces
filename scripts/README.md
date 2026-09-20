# scripts/ — utilidades manuales (fuera de la suite de tests)

Probes manuales de conectividad/latencia contra **fuentes de datos reales** y
canales de salida. **No son tests unitarios**: golpean la red / servicios y por
eso viven fuera de `sentinel_omega/tests/` (que es `testpaths` de pytest) y usan
prefijo `probe_` para que pytest no los recoja.

> Regla del repo: cero datos sintéticos en producción. Estos probes solo
> **leen** de las fuentes reales para verificar que responden; no escriben en la
> DB. Ejecuta siempre desde la raíz del workspace para que `sentinel_omega` sea
> importable.

## smoke_fetch/ — fuentes de ingesta

Cada probe llama al fetcher real e imprime latencia + resultado:

| Script | Fuente / función |
|--------|------------------|
| `probe_kp_index.py`      | `fetch_kp_index` (NOAA SWPC Kp) |
| `probe_earthquakes.py`   | `fetch_earthquakes` (USGS FDSN) |
| `probe_schumann.py`      | `fetch_schumann_resonance` (Tomsk) |
| `probe_lod.py`           | `fetch_lod_series` (IERS LOD) |
| `probe_lunar_phase.py`   | `compute_lunar_phase_series` (efemérides) |
| `probe_beta1_pipeline.py`| `GeodynamicPipeline.fetch_beta1_data` (integración) |
| `probe_neo_hazard.py`    | `fetch_neo_hazard_summary` (NASA NEO) |

```bash
# desde /home/deamon/workspaces con el venv activo
python scripts/smoke_fetch/probe_kp_index.py
```

## smoke_telegram/ — canal Telegram

| Script | Qué verifica |
|--------|--------------|
| `probe_telegram_dryrun.py` | `send_heartbeat` / `send_alert` en modo dry-run (sin token, no llama a la API) |

```bash
python scripts/smoke_telegram/probe_telegram_dryrun.py
```

---

*Origen: estos archivos estaban sueltos en la raíz del repo como `test_fetch*.py`
/ `test_telegram.py`. Se reubicaron y renombraron el 2026-09-14. Los scripts
de un solo uso y rotos (`add_test.py`, `fix_pipeline.py`, `fix_test.py`,
`debug_test.py`, `test_runner*.py`) se eliminaron por estar superados por la
suite real en `sentinel_omega/tests/`.*
