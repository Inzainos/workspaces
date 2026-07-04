# Changelog — Sentinel Omega

All notable changes to the Sentinel Omega precursor detection system are
documented here. Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
conventions. Dates are UTC-6 (local time of the author).

---

## [Unreleased] — 2026-07-04

### Added

#### Package `sentinel_omega/core/delta_enriched/` (ex `staging/snt_delta/`)
- **`delta_engine.py`** — Adapter wrapping `SatellizationEngine` → exposes
  `DeltaSignal` dataclass (`hub`, `shadow`, `market`, `b`, `anomaly_score`,
  `confidence`, `regime`, `direction`, `r_squared`, `n`) and the
  `analyze_pair(hub, shadow, market, df)` function needed by `composite.py`.
- **`market_mapping.py`** — Stub with `CRYPTO_TICKERS`, `EQUITY_TICKERS`,
  `ALL_TICKERS` so composite can enumerate the asset universe.
- **`fetchers.py`** — Production copy of `staging/snt_delta/delta_fetchers.py`
  with self-import corrected to `sentinel_omega.core.delta_enriched.fetchers`.
- **`cross.py`** — Pure-NumPy cross-correlation module (no changes needed from
  staging); `compute_cross(data, window_days)` → `CrossResult` with
  `composite_coupling`, `geomagnetic_coupling`, `schumann_coupling`,
  `dominant_driver`, `dominant_target`, `dominant_r`, `dominant_lag`.
- **`composite.py`** — Production copy of `staging/snt_delta/delta_composite.py`
  with all four imports fixed to `sentinel_omega.core.delta_enriched.*`;
  `run_composite(data, window_days=14)` → `DeltaCompositeSignal`.
- **`__init__.py`** — Package init; re-exports all public symbols for clean
  external imports.

#### Database schema v5 (`sentinel_omega/infrastructure/database/schema.py`)
- Bumped `SCHEMA_VERSION` from 4 → 5.
- **`tbl_cobertura_satelital`** — Satellite coverage per cycle per zone:
  `id`, `timestamp_blk`, `zona`, `coverage_score`, `thermal_anomalies`,
  `clear_passes`, `total_passes`, `revisit_days`, `notas`.
  Used by `launcher.py` after each alfa2 run and by `extraer_features_ventana`
  when building training firma vectors from live data.
- **`tbl_delta_cross`** — Cross-correlation results per cycle:
  `id`, `timestamp_blk`, `composite_coupling`, `geomagnetic_coupling`,
  `schumann_coupling`, `dominant_driver`, `dominant_target`, `dominant_r`,
  `dominant_lag`, `delta_composite_score`, `delta_regime_label`,
  `delta_confidence`, `notas`.
  Populated by `launcher.py` after each delta-enriched pass.
- Both tables added to `EXPECTED_COLUMNS` for forward-only column migration.

#### Repository methods (`sentinel_omega/infrastructure/database/repository.py`)
- `insert_cobertura_satelital(ts, zona, coverage_score, thermal_anomalies,
  clear_passes, total_passes, revisit_days, notas)` → upsert into
  `tbl_cobertura_satelital`.
- `insert_delta_cross(ts, composite_coupling, geomagnetic_coupling,
  schumann_coupling, dominant_driver, dominant_target, dominant_r,
  dominant_lag, delta_composite_score, delta_regime_label,
  delta_confidence, notas)` → upsert into `tbl_delta_cross`.

### Changed

#### Delta pipeline now connected to production
- `sentinel_omega/infrastructure/pipeline/data_pipeline.py`
  `fetch_delta_data()` now calls `fetch_all()` + `run_composite()` from the
  new `delta_enriched` package after the standard delta fetch.  
  Cache dict receives: `cross_coupling`, `geo_coupling`, `schumann_coupling`,
  `delta_composite_score`, `delta_regime_label`, `delta_narrative`,
  `delta_confidence`, `delta_data_completeness`, `geo_kp_max_3d`,
  `geo_storm_active`, `geo_schumann_deviation`.

#### alfa2 persistence + live accumulation
- `sentinel_omega/infrastructure/pipeline/layer_runners.py` — alfa2 block now
  sets `self._last_alfa2_data` after each cycle so `launcher.py` can persist it.
- `sentinel_omega/launcher.py` — After `_auditar_ciclo()` two new persistence
  blocks: (1) alfa2 zone coverages → `tbl_cobertura_satelital` via
  `repo.insert_cobertura_satelital()`; (2) delta cross results →
  `tbl_delta_cross` via `repo.insert_delta_cross()`.

#### `_build_live_features()` fully connected (`sentinel_omega/launcher.py`)
Previously only alfa1, beta1, and delta features were extracted for live firma
matching.  Now also extracts:
- **beta2** (volcanic degassing proxy): reads `global_node_scan` from
  the OpenWeatherMap layer; counts VOLCAN/TECTONICO nodes with SO2 > threshold
  as `erupciones_win`; sums excess SO2 (scaled × 1e-4 μg/m³ → ~kt) as
  `so2_kt_win`.  Rationale: the trained features use NASA MSVOLSO2L4 kilotonne
  units; the scale factor is chosen so that `similitud()` correctly discriminates
  "quiet" (0) from "active" (>0) states using relative differences.  The 90-day
  window (`erupciones_90d`, `so2_kt_90d`) is approximated from the 14-day
  window — conservative (understates background load).
- **alfa2** (satellite coverage): reads `_last_alfa2_data` from the runner;
  computes a composite coverage score [0,1] per zone from `total_passes`,
  `s2_cloud_covers`, and `mean_revisit_days`; stores mean as
  `satellite_coverage_score`, thermal anomaly count as
  `satellite_thermal_anomalies`, clear pass count as `satellite_clear_passes`.

#### Signature engine (`sentinel_omega/core/firmas/signature_engine.py`)
- `FEATURE_KEYS` extended with `satellite_coverage_score`,
  `satellite_thermal_anomalies`, `satellite_clear_passes` (appended at end →
  backward-compatible with existing firma vectors whose new dimensions become
  NaN and are excluded by `similitud()`).
- `extraer_features_ventana()` now queries `tbl_cobertura_satelital` for the
  14-day window before each training event.  `OperationalError` / any exception
  is silently ignored (table absent = features absent = NaN).

#### Training pipeline (`sentinel_omega/infrastructure/pipeline/entrenamiento.py`)
- `BOT_FEATURES` gains `"alfa2": ["satellite_coverage_score",
  "satellite_thermal_anomalies", "satellite_clear_passes"]`.
- `MIN_FEATURES_POR_BOT` gains `"alfa2": 2`.
- `BOT_DESDE` unchanged for alfa2 — there is no fixed start date because
  alfa2 trains only from live-accumulated data in `tbl_cobertura_satelital`.
- New constant `BOTS_LIVE_ONLY = {"alfa2"}` — bots that have no backcast source.
  Fase 1 (`fase1_reconocimiento`) and `disciplina_trasfondo` now skip
  `BOTS_LIVE_ONLY` to avoid generating empty firma vectors during initial
  historical re-training.

### Notes & Known Limitations

- **alfa2 cold start**: Firma memory for alfa2 starts empty and accumulates
  organically with each live cycle.  Until it reaches the `consolidada`
  threshold (5 recurrences) its alerts are suppressed by the Juez.  This is
  intentional — accuracy over speed.
- **beta2 unit mismatch**: The live proxy (OWM μg/m³ × 1e-4 ≈ kt) is an
  approximation.  If a strong volcanic event occurs the proxy will score it as
  "active" even if the absolute kt value differs from the historical training
  data.  This is acceptable because `similitud()` uses relative differences and
  the key discriminant is zero vs. non-zero.
- **delta_enriched cold start**: `fetch_all()` falls back gracefully if any
  ticker fetch fails (network, rate-limit).  `run_composite()` returns a
  neutral signal (`delta_composite_score = 0.5`) when fewer than 7 days of
  cross-correlation data are available.
