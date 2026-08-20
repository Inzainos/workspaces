# Changelog — Sentinel Omega

All notable changes to the Sentinel Omega precursor detection system are
documented here. Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
conventions. Dates are UTC-6 (local time of the author).

---

## [Unreleased] — 2026-08-19

> **Detalle completo:** [`CHANGELOG_2026-08-19.md`](CHANGELOG_2026-08-19.md)

Sesión de cableado end-to-end hacia pipeline 100% operativo.

### Added (resumen)
- **Schema v11** — `tbl_locf_cache`, `tbl_eventos_catalogo`, DDL self-expanding (`schema_parts/`)
- **LOCF persistente** — último valor real en DB si falla la API (`locf_store` + patch pipeline)
- **ONNX multi-agente** — mixin + train bootstrap/DB para alfa1/2, beta1/2, delta, omega
- **Juez 2h + agent_signals** — `register_cycle_predictions`: Padre + cada bot; `ventana_h` adaptativa
- **Launcher self-expanding** — `launcher_hex/h00..h11.hex` + cableado a `juez_cycle_register`
- **Omega dual-ask** — referencia por asertividad en el Padre
- **Telegram Centinela V2** — gate 30 min, credenciales solo por env
- **Volcado 24h** — telemetría viva → histórico en cascada
- **Dashboard** — pestañas Alfas / Betas / Omega / Padre / Juez / Eventos

### Changed / Fixed (resumen)
- Castigo/refuerzo del Juez a **todos** los bots (antes solo Padre)
- `ventana_h` ya no fija en 72 h (piso 2 h → lag empírico → tope 90 d)
- Cero sintéticos: NULL + LOCF en fallos de API
- Patrón self-expanding para archivos grandes (schema + launcher)

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

> **Historial anterior** (2026-07-11, 2026-07-05, 2026-07-04, honestidad total,
> cimática, correo, multi-evento, delta_enriched): conservado en el historial
> de commits de este archivo. Para el detalle de la sesión más reciente ver
> [`CHANGELOG_2026-08-19.md`](CHANGELOG_2026-08-19.md).
