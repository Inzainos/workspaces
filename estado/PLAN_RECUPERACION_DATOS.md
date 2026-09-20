# Plan de recuperación de datos — Sentinel Omega

*2026-09-15 · diagnóstico verificado contra la DB en vivo*

## Diagnóstico (verificado)
- **4/7 fuentes vivas muertas**: delta/BTC 258 d · omega/IERS 258 d · beta2/SO₂ 46 d · USGS operativa 30 d.
- `protones` = 2422/2422 en **cero** (nunca se ingesta).
- `tbl_locf_cache` = **0 filas** (el fallback existe pero nunca se activó en el pipeline vivo).
- `alfa1` castigado por el Juez a **peso 0.3** (el Juez no puede verificar sin sismos frescos).
- Fantasma CRÍTICO (~61) es **legítimo** (`|Bz|²=52 + viento=8.6 + schumann=0.3`), pero se apoya en pocas señales vivas.
- Refetch USGS **ya corrido**: 2208 sismos frescos en la tabla *fuente* (`tbl_eventos_sismicos_fuente`), pero la *operativa* `TBL_HISTORICO_SISMICO` (la que lee el Juez) sigue estancada — la alimenta el fetch vivo del launcher, que es la raíz.

## Reglas duras (no romper)
Cero datos sintéticos (faltante=NULL, LOCF **solo desde reales**) · migración forward-only (`EXPECTED_COLUMNS`/`_migrate_add_missing_columns`) · secretos por env · tests antes de commit · no push a `main`.

---

## P0 — Activar LOCF  *(Concilio implementa · yo verifico)*
El patch ya existe (`data_pipeline_locf_patch.py`; el refetch loguea "SentinelRepository patched with persistent LOCF"), pero **el launcher vivo no lo activa**.
1. `repository.py`: `update_locf_cache(fuente, clave, valor, ts)` y `get_locf_cache(fuente, clave)` sobre `tbl_locf_cache` (leer schema real; forward-only si faltan columnas).
2. `data_pipeline.py`: tras cada fetch **exitoso** por fuente (alfa1/beta1/beta2/delta/omega) → `update_locf_cache`; si el fetch falla o devuelve NULL → `get_locf_cache` como fallback. **Nunca** escribir LOCF desde un valor sintético.
3. Verificación: tras un ciclo, `SELECT COUNT(*) FROM tbl_locf_cache > 0`.

## P1 — Reparar conectores vivos
- **USGS → `TBL_HISTORICO_SISMICO`: ✅ RESUELTO 2026-09-15** (el elefante). El ciclo vivo descartaba los sismos; fix en `data_pipeline.py`/`layer_runners.py` (activa al reiniciar) + backfill ya ejecutado (operativa 552→3381, hasta hoy). Ver `estado/HANDOFF_2026-09-15.md`.
- **delta**: fix `_persist_delta` ya en el árbol sin commitear (activa al reiniciar); su fuente `delta_enriched.fetch_all` viene vacía → validar tras reinicio.
- **omega** (IERS LOD/lunar), **beta2** (NASA SO₂): pendientes de diagnóstico.

## P2 — Columnas muertas: el dato existe pero no se cablea  *(auditoría 2026-09-15)*
Auditoría de integridad: DB **sin** formatos mixtos/duplicados/NULLs de tiempo (los ETL sí limpian dentro de cada tabla). Los huecos reales son columnas que el ETL nunca llena — pero el dato **ya existe en la DB** en 2/3 casos:
- **`protones`** (`TBL_PRECURSORES_COSMICOS` = 0/2427): el dato real vive en `tbl_clima_espacial_raw.proton_flux_10mev` (270368/280377 = 96%). Causa: `repository.py:53` usa `protones: float = 0.0` por default y el llamador no lo pasa. Fix: mapear `proton_flux_10mev → protones` al escribir el precursor. **No** sintético.
- **`bz_derivada`** (`tbl_clima_espacial_raw` = 0/280377): derivable de `bz_promedio` (real, 280353/280377). Solo la calcula `backcast.py:387` (`.diff()`); el fetch vivo no. Fix: derivar en el ETL vivo + backfill `UPDATE bz_derivada = bz_promedio - lag(bz_promedio)`. Transformación determinista, no sintético.
- **delta coupling** (`cross_coupling`, `geomagnetic_coupling`, `schumann_coupling`, `geo_kp_max_3d`, `geo_storm_active` en `tbl_delta_cross` = 0/59): **NULL honesto**, no cero. `data_pipeline.py:394` no escribe si `data_completeness==0 or not enriched.cross`. Raíz: `core/delta_enriched/fetchers.fetch_all(days=14)` viene vacío → **es P1** (delta caído), no un fix de mapeo.

## P2-bis — Limpieza de tablas basura  *(pendiente de OK del usuario · escritura a prod)*
6 tablas residuo de migración (`*_pre_c2e09d5a05b445aa_*`, `*_orphans_20260913_*`, ~131k filas, la mayor `tbl_cimatica_patrones_nodo_pre_*` 114k). Ningún código las referencia. Script listo: `scripts/db_limpieza_tablas_basura.py`. Backup previo en scratchpad. VACUUM aparte, con launcher detenido.

## P3 — APIHealthTracker → dashboard  *(Concilio implementa · yo integro)*
- Clase `APIHealthTracker` (lag por fuente) en `layer_runners.py`; persistir `api_health_json` en `tbl_salud_sistema`.
- Exponer en `/api/health` (dashboard `api.py`); renderizar tira de estado en el dashboard nuevo (Presentación/Principal).

## P4 — Auto-refetch en el barrido diario  *(Concilio implementa · yo verifico)*
`mantenimiento.py`: si el lag de una fuente > 7 días → disparar su refetch (USGS `sismos_refetch_recent`, clima `clima_gapfill_2026`, stub delta/psique).

---

## Orden sugerido
1. **P0 (LOCF)** — foundational, autocontenido, el patch ya existe → primera tarea al Concilio.
2. **P1 (USGS vivo)** — la raíz para el Juez → yo diagnostico.
3. **P3 (health en dashboard)** — encaja con el rediseño en curso.
4. **P2, P4** — cierre.
