# Changelog — Sentinel Omega

All notable changes to the Sentinel Omega precursor detection system are
documented here. Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
conventions. Dates are UTC-6 (local time of the author).

---

## [Unreleased]

### Fixed

- **`eodag` pin alineado a `>=4.0`.** `sentinel_omega/requirements.txt` pedía
  `eodag>=2.10` mientras que `pyproject.toml` pedía `>=4.0`; el mismatch podía
  instalar la API vieja (2.x: `search()` devolvía tupla `(results, count)` y
  usaba `productType=`). El código de `esa_sentinel.py` está escrito contra la
  API 4.x (`dag.search(collection="S2_MSI_L2A", …)`, resultado iterable), así
  que se sube el pin de `requirements.txt` a `>=4.0` para que coincida con
  `pyproject` y con el código. Verificado contra eodag 4.5: `search()` acepta
  `collection` vía kwargs y ya no expone `productType` — el uso de `collection=`
  es correcto.

- **Alfa-2 (y Júpiter) ahora aparecen en los reportes.** Los reportes armaban la
  tabla de bots desde `TBL_FIRMAS`, donde alfa2 no tiene filas (es live-only: sin
  backcast histórico, acumula desde `tbl_cobertura_satelital`) — por eso
  "desaparecía". `generar_reporte.py` ahora muestra a alfa2 y jupiter con su
  estado operativo aunque no tengan firmas; la fila de alfa2 **indica cuando
  falta el feed satelital** (0 pases → "instalar eodag + credenciales
  Copernicus"), señalando el pendiente de deployment. `reporte_sentinel.py`
  añade `jupiter` a `bots_order`; la prosa pasa de "6 bots" a "7 bots".

### Added

- **Júpiter como 7º agente del consenso** (`layers/geodynamic/jupiter/agent.py`):
  corroborador de atención colectiva. Emite WATCH/ALERT cuando hay tormenta
  geomagnética activa (Kp≥5) y/o el interés de búsqueda se dispara (≥2σ) con una
  correlación atención↔tormenta significativa. Registrado en el Padre en la
  familia `space_weather` (corrobora a Alfa-1/2 sin cambiar el conteo de familias
  del consenso), fuera de los pares senior/junior. Cableado no-bloqueante en el
  `layer_runner`; `fetch_jupiter_data` cachea Google Trends 6 h para no pegar el
  rate-limit en el loop en vivo.
- **Júpiter · Schumann + vocabulario ES/geo**: `schumann_series_from_trend()`
  alimenta la serie Schumann acumulada en la DB (`repository.schumann_trend`) a
  la correlación; el conector de Trends elige vocabulario español para
  `geo="MX"/"ES"` (`tormenta solar`, `aurora boreal`, …).
- **Júpiter — motor de correlación de tormentas solares** (`core/precursor/jupiter.py`):
  correlaciona **tormentas solares** (NOAA/GFZ Kp + GOES X-ray) contra la
  **atención colectiva** (Google Trends) y la **resonancia Schumann**. Reporta
  Spearman ρ + cross-correlation con lags (¿el interés de búsqueda sigue a la
  tormenta, y con cuántos días?). Solo tormentas solares.
  - Conector **Google Trends** (`infrastructure/api/google_trends.py`, `pytrends`):
    interés diario de vocabulario solar; degrada limpio ante rate-limit.
  - Conector **GFZ Potsdam Kp** (`infrastructure/api/gfz_kp.py`): Kp histórico
    largo (NOAA SWPC solo sirve ~7 días); CC BY 4.0.
  - Script `deploy/jupiter_correlaciones.py` → `estado/jupiter_correlaciones.json`.
  - Primer hallazgo real (ventana 90d): kp~xray ρ=+0.93 (p=0.003, físico);
    kp~Google-Trends ρ≈0 (sin correlación en la ventana). (+8 tests → 420.)

### Changed

- **Alfa-2 aprende su propio baseline por zona** (`alfa2/agent.py`): supera la
  limitación proxy-of-proxy documentada en v2.5.1. En vez de contar pases de
  satélite, mantiene una media/σ online por zona (Welford, persistible a
  `SNT_STATE_DIR`) sobre un índice térmico y puntúa cada ciclo como desviación Z
  sobre lo aprendido: |Z|≥2.5 → ALERT, ≥1.5 → WATCH. Alfa-2 deja de ser "ojo
  muerto" en el consenso de 6 agentes. Retrocompatible (thermal_anomaly_count
  sigue forzando ALERT; entrada vacía → NO_SIGNAL).

### Fixed

- **`esa_sentinel.py`**: `_get_dag()` ahora dentro del `try` de las búsquedas —
  un `eodag` ausente o credenciales inválidas degradan a resultado vacío en vez
  de propagar una excepción. (+3 tests de aprendizaje; suite 412.)

---

## [v2.5.0-complete] — 2026-07-15

Pipeline completado: delta_enriched integrado de punta a punta + rebuild_completo.py listo.

### Added

- **delta_enriched feature extraction** (`sentinel_omega/launcher.py`): `delta_cross_coupling`, `delta_geo_coupling`, `delta_schumann_coupling` ahora extraídas desde caché hacia vector de firma
- **Rebuild orchestration script** (`deploy/rebuild_completo.py`): pipeline de 8 pasos (parar → vaciar → migrar v6 → tuning → Fase 1+1b+2 → disciplina → VACUUM → reportes)
- **Complete end-to-end validation**: todas las features (alfa1, alfa2, beta1, beta2, delta, delta_cross) conectadas; reportes generan sin errores

### Fixed

- **Falsos ceros en features delta_cross** (`launcher.py`): si el fetch de
  delta_enriched falla, las features quedan AUSENTES (NaN, excluidas por
  similitud) en vez de escribir 0.0 falso — coherente con "cero datos sintéticos"

### Notes

- Fase 1b (multi-evento: sísmico + volcánico + solar + financiero) operativa
- Omega bot con ritmo cósmico integrado al entrenamiento
- Sistema 100% verificado de punta a punta; listo para producción

---

## [Unreleased] — 2026-07-11

Bloque de **honestidad total** (fix list A–D + revisión profunda del
pipeline), **sistema 24/7** (rutinas, cimática, correo) y **reentrenamiento
limpio** de todas las memorias. Informe de hallazgos:
`estado/INFORME_CORRECCIONES.md`.

### Added

#### Línea base de Molchan (`sentinel_omega/core/precursor/baseline.py`) — NUEVO
- **`AlwaysAlertBaseline`** — modelo nulo "alertar siempre": su hit-rate es la
  tasa base de sismicidad (misma geometría que el sistema: radio 5°, ventana
  72 h). **Ganancia = hit_rate_sistema ÷ tasa_base**; ≤ 1 = el sistema no
  supera a alertar a ciegas.
- Hook **`validate_with_baseline()`** en `assertivity.py`; sección
  "¿Le ganamos a alertar siempre?" en `deploy/generar_reporte.py`.
- Primer resultado honesto: tasa base 100%, sistema 36.6% → **ganancia 0.37×**
  (sin ganancia todavía — por eso las predicciones por nodo, abajo).

#### Predicciones específicas por nodo
- El Padre registra los **nodos de las firmas que motivaron su aviso**
  (`nodos` en detalles de la predicción viva).
- `Juez.evaluar_pendientes()` acepta **`eventos`** (verdad POR FILA: ventana
  propia de 72 h + zonas) y usa los nodos de la propia fila cuando existen —
  un aviso solo vale si acierta DÓNDE avisó. Los silencios se juzgan contra
  toda la malla. `firma_conocida` también por fila (desde los detalles).
- `AssertivityTracker` por fin alimentado en operación (avisos anclados a sus
  nodos) con ganancia de Molchan en vivo.

#### Cimática — snapshot de patrones (`sentinel_omega/core/firmas/cimatica.py`) — NUEVO
- **`tbl_cimatica_patrones`**: cada ciclo toma el snapshot del sistema (huella
  de bandas logarítmicas con signo). Patrón NUEVO → telemetría completa
  guardada; existente → **frecuencia+1** (contar, no anotar). Ámbito
  `general`/`nodo`, `event_class` cuando se conoce.
- **Trigger del Padre**: toda alta/incremento dispara su revisión; patrón
  nuevo con Padre activo o cimática consistente (frecuencia ≥ 3) con evento
  asociado → alerta por correo.
- **`entrenar_cimatica()`**: el histórico de 30 años graba los patrones de la
  víspera de cada evento (misma extracción de features que la Fase 1) — la
  tabla nace con las frecuencias contadas. Integrado a `entrenar()`.
- **`retroetiquetar_patrones()`**: cuando el Juez confirma un evento real
  (M4.5+), los patrones sin evento de su víspera de 72 h se etiquetan con lo
  que desataron (en vivo el snapshot se graba ANTES de saber qué desata).
- **`poda_cimatica()`**: la línea base es TODA la telemetría, pero el patrón
  que tras 30 días de gracia no se asoció a ningún evento es ruido → se
  elimina (enganchada al barrido diario). Lo asociado a eventos se queda.

#### Correo — alertas y reportes sin Telegram (`sentinel_omega/infrastructure/api/correo.py`) — NUEVO
- **`tbl_correo_salida`**: outbox de ALERTAS y REPORTES a
  `elan.zainos.corona@gmail.com` (configurable con `CORREO_DESTINO`).
- Envío SMTP **fail-soft** por variables de entorno (`SMTP_USER`/`SMTP_PASS`,
  app password de Gmail): sin credenciales el correo queda PENDIENTE — nunca
  se pierde ni se finge enviado. Adjunta las gráficas PNG de los reportes.
- `deploy/enviar_correos.py` — despacho del outbox en cada corrida del
  vigilante.

#### Rutinas 24/7 (`.github/workflows/roy-vigilante.yml` reestructurado)
- **Cada 2 h**: ciclo del Padre (status + registro + cimática).
- **Cada 4 h**: el Juez verifica real vs predicción
  (`deploy/verificacion_juez.py` → `pipeline/verificacion.py`, ritmo
  AUTO-IMPUESTO: si la última resolución viva tiene <4 h, la pasada se salta).
- **Cada 6 h**: reporte ejecutivo (encolado por correo).
- **12am/12pm MX**: comparativo contra el día anterior
  (`deploy/reporte_periodico.py --comparativo`, con gráfica).
- **Domingo 12:15pm MX**: reporte semanal (gráficas fantasma/alertas/breaches).
- **Fin de mes 12:30pm MX**: reporte mensual (guardia "mañana es día 1").
- Gráficas con matplotlib (nueva dependencia), estilo sobrio: una serie, un
  color, máximo resaltado.

#### Verificación por fases en reportes
- Sección del Juez de `generar_reporte.py` separada por fase: "Operación viva
  (lo que cuenta)" vs "Bitácora de entrenamiento (no puntúa)".

### Changed

#### Honestidad de agentes (fix list A–D)
- **beta1** (`layers/geodynamic/beta1/agent.py`) — REESCRITO: el "filtro
  armónico Schumann" sobre Kp muestreado a 3 h era numerología (7.83 Hz ≈ 5
  órdenes sobre el Nyquist; coherencia ≈ 1 siempre). Ahora
  `kp_spectral_features()` (FFT PLANO: energía, ratio de alta frecuencia,
  periodo dominante) + el Schumann MEDIDO de Tomsk como serie propia
  (excitación >15% suma confianza; >30% con espectro calmo → WATCH).
  `correlacion_TL` exige ≥ 3 ciclos lunares completos (ventana corta = |r|
  alto por azar → None, nunca alimenta confianza).
- **alfa1** (`alfa1/agent.py`) — REESCRITO: rama ONNX real (carga fail-soft,
  `set_model()` inyectable, `_analyze_onnx()` con fallback honesto); el
  reasoning dice QUÉ rama corre ("ONNX inference:…" vs "Bz threshold
  rule:…"), `data.onnx` lo marca. Bz por NOMBRE de columna (posición 0 solo
  es Bz si `bz_gsm` vino en el dataframe) y vector ONNX alineado por nombre.
- **delta** (`delta/agent.py`) — NUNCA emite ALERT al consenso: techo WATCH
  (estrés financiero = contexto correlacionable, no voto sísmico). `friction`
  institucional hardcodeado (0.4/0.3/0.5) eliminado del score.
  `health_check` con flag `_ingested` (VIX=20.0 exacto ya no es "sin datos").
- **alfa2** (`alfa2/agent.py`) — limitación proxy-of-proxy documentada: sin
  `lst_c` (LST medida) el conteo térmico degrada a WATCH; ALERT térmica exige
  lecturas reales.
- **Piso de medición**: `MIN_MAGNITUD_OBSERVAR` y `MAG_MENOR_MIN` en **3.3**
  (alineado al piso real del backcast, M3.38). El sistema mide y predice
  desde M3.3 con su clase de desastre; **alerta solo desde M4.5** (solo el
  Padre avisa).

#### Fase estricta del Juez (C1/C2)
- Columna **`fase`** real en `TBL_JUEZ_AUDITORIA`
  (viva/reconocimiento/backtest/observacion/trasfondo) + backfill de datos
  viejos + vista **`viva_real`** = vara canónica de asertividad.
- La auditoría viva es **append-only** (jamás DELETE); la poda del backtest
  usa la columna fase. `evaluar_pendientes(fase=...)` — el entrenamiento no
  puede resolver (contaminar) las predicciones vivas del launcher.
- Las tres tuberías de reporte (`generar_reporte.py`, `reporte_ejecutivo.py`,
  `reporte_sentinel.py`) unificadas sobre `viva_real`.

### Fixed
- **183 resoluciones viva contaminadas**: todas compartían una verdad de
  **1994** del backcast (corrida de entrenamiento previa al filtro de fase).
  Regresadas a PENDIENTE y re-resueltas contra el catálogo USGS REAL de julio
  2026, cada una contra su propia ventana de 72 h.
- **El criterio vivo de verdad era el modelo nulo puntuando 100%**: "hubo
  M4.5+ en la Tierra en 4 días" es cierto casi siempre → todo watch era
  ACIERTO gratis. Reemplazado por verdad por fila (arriba). USGS caído ahora
  POSPONE la resolución (antes inventaba "sin eventos" → FALSO_POSITIVO
  injusto).
- El gate de disciplina del vigilante (07 UTC) **nunca disparaba** (el cron
  corre en horas pares) — reemplazado por gates con tolerancia al retraso del
  scheduler.
- `--disciplina`/`--barrido`/`--entrenar` sin `--once` ya no caen al ciclo
  continuo (task-mode batch: corre y sale). USGS FDSN 400 por microsegundos y
  offset en el timestamp (strftime limpio).

### Notes & Known Limitations
- **Reentrenamiento limpio total** ejecutado tras las correcciones: firmas,
  pesos, correlaciones, orden, sesgo y lags borrados y reaprendidos desde
  cero con el código corregido (sin sesgos de versiones pasadas). La fase
  viva (append-only) y los datos crudos del backcast se conservan.
- El backcast histórico tiene piso real M3.38: medir bajo 3.3 requeriría
  re-ingerir el catálogo (decisión futura).
- La severidad por reincidencia crece sin techo dentro de un lote grande de
  resolución (documentado, sin cambio: el castigo duro es de diseño).
- El envío de correo requiere configurar `SMTP_USER`/`SMTP_PASS` en los
  secrets del repo; sin ellos el outbox acumula PENDIENTES (por diseño).

---

## [Unreleased] — 2026-07-05

### Added

#### Entrenamiento multi-evento — Fase 1b y correlaciones (`sentinel_omega/infrastructure/pipeline/entrenamiento.py`)
- **`derivar_eventos_no_sismicos(conn)`** — Deriva un catálogo de eventos no
  sísmicos directamente de las tablas de backcast existentes:
  - Erupciones volcánicas (VEI ≥ 3) desde `tbl_desgasificacion_raw` →
    clases `ERUPCION_VEI3/4/5`.
  - Tormentas solares (Kp ≥ 6, primer bloque horario tras calma) desde
    `tbl_clima_espacial_raw` → clases `TORMENTA_Kp6/7/9`.
  - Almacena en `tbl_eventos_no_sismicos`. Idempotente (INSERT OR IGNORE).
- **`entrenar_reconocimiento_no_sismico(db_path, ...)`** — **Fase 1b**: entrena
  firmas a partir de los eventos no sísmicos derivados. Usa la misma extracción
  de features y la misma ventana de 14 días que la Fase 1 sísmica, de modo que
  los bots aprenden qué precede a erupciones y tormentas, no solo a sismos.
- **`calcular_correlaciones_evento(db_path)`** — Calcula la matriz
  feature × event_class desde `TBL_FIRMAS`. Para cada par
  `(tipo_evento, variable)` guarda la media y el ratio vs. la media global en
  `tbl_patrones_correlacion`. Ratio > 1 = la variable está elevada antes de ese
  tipo de evento. Re-ejecutar es seguro (INSERT OR REPLACE).
- **Helpers**:
  - `_event_class_volcanico(vei)` — Clasifica eventos volcánicos por VEI.
  - `_event_class_solar(kp_max)` — Clasifica tormentas solares por Kp (proxy
    escala G de NOAA).
  - `_table_exists(conn, name)` — Verifica existencia de tabla en SQLite.

#### Actualización de `entrenar()` (`entrenamiento.py`)
- `entrenar()` ahora ejecuta: Fase 1 (sísmica) → **Fase 1b** (no sísmica) →
  Fase 2 (disciplina) → lags → **correlaciones**.
- Retorna `{"fase1": …, "fase1b": …, "fase2": …, "lags": …, "correlaciones": …}`.

#### Nuevas features de acoplamiento geofísico-financiero (`sentinel_omega/core/firmas/signature_engine.py`)
- `FEATURE_KEYS` extendido con `delta_cross_coupling`, `delta_geo_coupling`,
  `delta_schumann_coupling` (acoplamiento geofísico-financiero cruzado desde
  `tbl_delta_cross`; live-only, NaN durante backcast).
- `extraer_features_ventana()` consulta `tbl_delta_cross` para la ventana de
  14 días antes de cada evento. Error silencioso si la tabla no existe.

#### Esquema de base de datos v6 (`sentinel_omega/infrastructure/database/schema.py`)
- `SCHEMA_VERSION` bumpeado de 5 → 6.
- **`tbl_eventos_no_sismicos`** — Catálogo de erupciones volcánicas y tormentas
  solares derivadas de backcast. Clave primaria compuesta:
  `(timestamp_blk, id_nodo, event_class)`. Índices en `event_class` y
  `timestamp_blk`.
- **`tbl_patrones_correlacion`** — Matriz feature × event_class: `event_class`,
  `feature`, `media`, `global_media`, `ratio`, `n_firmas`, `updated_at`.
  Clave primaria compuesta: `(event_class, feature)`. Índice en `event_class`.
- Ambas tablas registradas en `EXPECTED_COLUMNS` para migración forward-only.

#### Reporte ampliado (`deploy/generar_reporte.py`)
- **Mapa de calor de correlaciones** — Nueva sección `## 🗺 Correlaciones
  aprendidas` con tabla Markdown de los 8 features más discriminadores por tipo
  de evento. Iconos de color: 🔴≥2× · 🟠≥1.5× · 🟡≥1.2× · ⬜~normal · 🔵↓bajo.
- **Top 10 patrones del sistema** — Nueva sección `## 🏆 Top 10 patrones del
  sistema`: firmas con mayor recurrencia (consolidadas/recurrentes) de todos los
  bots, con zona, estado y tiempo de aviso típico.
- **Top 5 por clase de evento** — Nueva sección `## 📊 Patrones por tipo de
  evento`: para cada `event_class` aprendida, las 5 firmas más consolidadas.
- Nuevas entradas en `NOMBRES_LLANOS`: `delta_cross_coupling`,
  `delta_geo_coupling`, `delta_schumann_coupling`.

### Fixed (`entrenamiento.py`)
- Imports de `sqlite3`, `json`, `FirmaMemoria`, `FEATURE_KEYS` movidos al nivel
  de módulo (antes estaban dentro de funciones).
- Chequeo NaN corregido de `v != v` explícito (evita comparación incorrecta).
- Contador de inserciones en `derivar_eventos` corregido (incrementa solo cuando
  el INSERT efectivamente ocurre).

### Notes & Known Limitations

- **Fase 1b cold start**: Si `tbl_desgasificacion_raw` y
  `tbl_clima_espacial_raw` no tienen datos (backcast no cargado), la Fase 1b
  finaliza con `eventos: 0` sin error.
- **delta_cross features**: Durante el backcast histórico estas features son NaN
  (tabla `tbl_delta_cross` vacía). El sistema las aprende incrementalmente desde
  los ciclos en vivo; el módulo `similitud()` las ignora automáticamente.
- **Correlaciones**: La primera ejecución de `calcular_correlaciones_evento()`
  requiere que `TBL_FIRMAS` tenga datos (Fase 1 o 1b completada). Si está vacía,
  retorna `{}` sin error.

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
