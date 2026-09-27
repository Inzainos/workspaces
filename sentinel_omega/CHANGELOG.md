## 2026-09-27 — El cero de «no lo sé»: 792 falsas alarmas de alfa1 y el latido silenciado

Cinco defectos de la misma familia — un número que NO es una medición ocupando la
posición de un rasgo — encontrados y medidos contra la base en producción. Los
cuatro primeros son instancias de reglas duras que ya estaban escritas en
`AGENTS.md` (7, 8, 9, 10); se anotan con su número para no volver a presentarlas
como hallazgos nuevos.

### Changed — comportamiento de pipeline

- **`layers/geodynamic/alfa1/agent.py`** — se quita su inferencia ONNX propia.
  `omni_dataframe` se arma solo con magnetómetro y viento y **nunca ha tenido
  columna `kp_index`**, así que `agregados_omni` no producía Kp, `vector_para`
  ponía 0,0 y el modelo leía ese 0,0 como «Kp CERO»: quietud extrema. Mismo
  modelo, ciclo 14419: con Kp real → `NO_SIGNAL 0.3114`; sin Kp → `WATCH 0.7165`
  (la respuesta al dato ausente pesaba el doble, así que ganaba el consenso).
  En el Juez: **792 `watch` FALSO_POSITIVO contra 5 ACIERTO**, todos de esa rama;
  cero desde la rama de reglas. Ahora el modelo opina en un solo sitio,
  `_aplicar_modelos`, con el vector canónico — **el que el Juez registra**.
  (Regla 7: desconfía del default benigno.)
- **`launcher.py`** — los conteos sísmicos se calculan como los calcula la firma:
  del **nodo** y en 336 h / 72 h desde `tbl_historico_sismico_raw`, máximo sobre
  nodos. Antes era `len()` del catálogo global de USGS, topado a `limit=500` (el
  conteo real es 1.967), así que valían **500 constante en todos los ciclos**.
  Contra la distribución entrenada — mediana 7, p75 14, p99 244 — eso ponía al
  modelo por encima del percentil 99,8 en cada ciclo. Verificado en vivo (ciclo
  14432): **500/500 → 99/27**. Sin conexión el rasgo se omite, no se inventa.
  (Regla 9: verifica el índice contra el dato.)
- **`infrastructure/pipeline/layer_runners.py`** — `_aplicar_modelos` sustituye
  también el `reasoning`. Antes cambiaba señal y confianza y dejaba el texto de
  la regla, así que el Juez guardaba filas como `beta1 watch 0.735 "Normal
  spectral distribution"`: el texto describe la regla y el veredicto es del
  modelo. Ahora conserva los dos y dice cuál mandó. Con `None` del modelo el
  texto de la regla queda intacto. (Regla 10: una sustitución silenciosa esconde
  lo que pasó.)
- **`models/train_onnx_from_db.py`** — `purgar_no_medidos()`: una media sin su
  desviación no salió de una ventana de muestras. Saca el `schumann_mean = 8.26`
  congelado (`7.83 + 21.46×0.02`) de las 387 filas del `detalles_json` y de las
  72 de `tbl_juez_rasgos_reconstruidos` — tabla MATERIALIZADA que se llenó antes
  de que existiera la bandera `en_vivo`; **un filtro correcto no limpia lo que ya
  se guardó sin él**. 451 muestras purgadas, 0 apariciones del 8,26 en los
  vectores. El criterio es la forma, no el nombre ni el valor: una lectura real
  futura traerá las dos y pasará intacta.
- **`infrastructure/api/telegram.py`** — `hz_schumann_valido()` (1–60 Hz): la
  fundamental es 7,83 y los armónicos llegan a 33,8; nada bajo 1 Hz es esa señal.
  El formateador publicaba la fracción de WPC como «0,21 Hz» si alguien se la
  pasaba; la defensa vivía solo en `orchestrator.py`. **Cambio de comportamiento:**
  un `0.0` medido ya no se publica — cero hercios no es una lectura de la cavidad.
  Nota de prioridad: `AGENTS.md` dice «canal: correo, Telegram en pausa», o sea
  esto endurece el canal pausado. El de correo se revisó y **no** tiene el
  defecto (`generar_reporte.py` lee la columna `schumann_hz`, que
  `launcher.py:443` escribe NULL sin dato).
- **`infrastructure/api/usgs.py`** — `MAX_RESULTS` expuesto y
  `count_earthquakes()` contra el endpoint `count` de FDSN (sin tope). No se usa
  en el ciclo — los conteos salen del histórico por nodo — pero deja medible que
  500 era un tope.
- **`infrastructure/pipeline/data_pipeline.py`** — expone `proton_flux_max`.
  `proton_max` llegaba siempre vacío al vector de alfa1. **No cambia nada hoy y
  conviene decirlo**: medido, el modelo responde igual con `proton_max` en 0, en
  0,29 o en 120 — nunca aprendió a usarlo. Sirve para el próximo reentrenamiento.
- **`infrastructure/pipeline/entrenamiento.py`** — `BOT_FEATURES["delta"]` suma
  `vix`. El bot FINANCIERO no llevaba el índice del miedo en sus firmas (0 de
  676) mientras loki, geofísico, sí. Las firmas del próximo rebuild lo llevarán;
  hasta entonces **no** entra al vector.

### Descubierto al verificar

- **El 500 estaba silenciando al latido.** Sensibilidad de beta1 con todo lo
  demás fijo: `win=500 → NO_SIGNAL 0.2000`, y **WATCH 0.73–0.79 en 0, 3, 7, 27,
  99, 100 y 244**. Durante todos los ciclos vivos el modelo de beta1 quedaba
  anulado por un tope de catálogo — y beta1 es *el latido*. Es el espejo del
  fantasma de alfa1: allí un rasgo ausente fabricaba una alarma, aquí un tope la
  suprimía. No se veía por lo que ya dice `test_expertos_onnx.py`: **«el que no
  alarma no puede ser castigado por alarmar»**.
- **`juez_cycle_register.py` no persiste `sig.data`.** Los campos `onnx_senal` /
  `regla_senal` que `_aplicar_modelos` calcula «para que el Juez pueda comparar
  después quién acertaba» (su propio docstring) **no llegan**: 0 filas de
  `TBL_JUEZ_AUDITORIA` los tienen. En todo el histórico no hay forma estructurada
  de saber si un veredicto lo dio el modelo o la regla. Es la señal medida y no
  conectada, en el camino de auditoría.
- **El peso vivo contra el histórico ya no es una pregunta de diseño.** alfa1
  caía al suelo 0,300 en vivo y cada rebuild lo devolvía a 1,425: el vivo estaba
  castigando el fantasma y el histórico era ciego porque las firmas no pasan por
  ese vector. El rebuild no borraba aprendizaje — borraba el único sitio donde el
  defecto se veía. Toca **volver a medirlo** tras el reinicio, no cambiar la regla.

### Verificación

Rebuild en SERIE 01:24:40→02:55:58, código 0. Matriz viva del motor de firmas
medida contra la corrida de la mañana en la misma máquina: **7.404 s → 5.322 s**,
total **126 → 91 min (1,39×)**. 19.578 firmas, **sin rasgo de Schumann** (397→0,
verificado contra el respaldo). Los 8 ONNX reentrenados con los arreglos dentro;
auditoría de los 8 vectores: **cero desajustes del tipo fantasma** (los 7 de
Schumann que quedan están alineados, 0,0 en los dos lados). Reinicio del operador
04:56:10; ciclo 14432 verificado contra la base, no contra el log.

### Pendiente (propuesto, no hecho)

1. Conectar los campos `onnx_*` al `detalles` del Juez (dos líneas; vuelve la
   comparación consultable con `json_extract`).
2. Rematerializar `tbl_juez_rasgos_reconstruidos` — raíz del 8,26; la purga es el
   cinturón.
3. Codificar la ausencia aparte del valor (bandera «kp presente»). El fantasma
   sigue DENTRO del modelo —sin Kp responde WATCH 0,726— pero ya no tiene ruta.
   Mientras el vector no pueda decir «no lo sé», cada 0,0 es un fantasma esperando.
4. alfa2 con rasgos de ESA: `tbl_frp_detecciones` lleva **una fila** (S3B del
   2026-09-26, guerrero_gap, 5,68 MW, confianza 75). Su límite de 3 features está
   documentado en `AGENTS.md` como decisión deliberada; el vector cambia cuando
   haya historia.

### Nota de documentación — y una corrección de criterio

La entrada del 2026-09-15 dice «Email removido … Telegram»; `AGENTS.md`
(2026-09-24) decía «canal: correo, Telegram en pausa». Concluí que **manda el más
reciente** y me equivoqué: la deriva estaba en el archivo MÁS NUEVO. Verificado
contra el código —`correo.py` no existe, `enviar_correos.py` despacha por
Telegram, `tbl_correo_salida` tiene cero referencias, variables SMTP comentadas
por el operador— el canal es **Telegram**. `AGENTS.md` corregido.

**El más nuevo no es el correcto: el código es la autoridad.** Es la Regla 0
—«verifícalo contra el código»— y la apliqué a los rasgos y no a los documentos.

---

## 2026-09-15 — Email removido, ONNX full suite, Telegram Mini App, lag en horas

- **Email removido:** eliminado `infrastructure/api/correo.py`; `deploy/enviar_correos.py` ahora flushea digest horario por Telegram; `reporte_ejecutivo.py` y `reporte_periodico.py` usan AlertService → Telegram. Variables SMTP/MAIL eliminadas de docs.
- **ONNX full suite:** entrenados `loki_unificado_rf.onnx` (18KB) y `jupiter_attention_rf.onnx` (24KB) desde firmas + Juez feedback. `BOT_DIMS` y `FEATURE_ORDER` actualizados (8 features c/u). Todos 8 modelos con datos históricos.
- **Arquitectura 8+3 agentes:** docs actualizados (README/CLAUDE/AGENTS): 8 SNT + Omega + Loki + Padre. Jupiter, Omega, Loki con roles documentados.
- **Telegram Mini App:** reportes horarios e inmediatos incluyen URL `TELEGRAM_WEBAPP_URL` (HTTPS público) y botón WebApp. `consenso_vigilante.py` muestra "🔗 Mini App: https://..." en digest.
- **Lag en horas:** hourly digest y precursores muestran `SISMO_M4: ~192h` (antes días). `get_model_status()` agrega tabla de lag al reporte.
- **Model status en digest:** hourly report incluye `✅ ALFA1 (333KB) ... ✅ LOKI (18KB) ✅ JUPITER (24KB)` + lag table.
- **Dashboard bind 0.0.0.0:** `sentinel-omega-dashboard-api.service` y `-web.service` habilitados LAN.
- **Tests:** 446 passing.

## 2026-09-14 — Contrato documentación↔pipeline (script-by-script)

- **Docs:** se amplió mapa de `infrastructure/pipeline/` en `README.md` (flat + nested) con scripts runtime, batch y one-shot.
- **Docs:** nueva sección **"Scripts auxiliares del pipeline (auditados)"** en README con tipo de script y uso esperado.
- **Docs:** `CLAUDE.md` (flat + nested) ahora incluye **"Pipeline scripts (operational map)"**.
- **Docs/Regla:** `AGENTS.md` incorpora contrato operativo para mantener sincronía código↔README/CLAUDE/CHANGELOG.
- **Auditoría:** generado `docs/audits/pipeline_script_by_script_contract_20260914_021102.{md,json}`.
- **Auditoría total consolidada:** `docs/audits/AUDITORIA_TOTAL_2026-09-14.md` con alcance, métricas, tests globales y deuda operativa.
- **Dashboard moderno persistente (user services):** `~/.config/systemd/user/sentinel-omega-dashboard-api.service` (`:8787`) y `sentinel-omega-dashboard-web.service` (`:5173`) habilitados con `systemctl --user enable --now`, ahora bind en `0.0.0.0` para acceso LAN.
- **Fix UI React:** componentes faltantes agregados (`HealthStrip.tsx`, `TelemetryStrip.tsx`, `AskBox.tsx`) para eliminar errores de import en Vite.

## 2026-09-13 — Duelo launcher cerrado, watchdog/ops, Schumann/Alfa2 tests

- **Fixed:** `sentinel-omega-scheduler` disabled — dejaba de matar al launcher de `sentinel-omega` (alertas Telegram desbloqueadas). Watchdog ya no re-enable el scheduler.
- **Ops:** dashboard Sentinel `:8510` active; Ollama = Windows `ollama.exe` (unit Kali disabled); backup offbox catch-up `watchdog_2026-09-13_1253.tar.gz` (hueco 12-sep irrecuperable).
- **Tests:** Schumann connector tests alineados a ingest None (6/6); `pytrends` en venv; Alfa2 7 passed (Agente-T).
- **Docs:** `docs/SESSION_2026-09-13.md`, `docs/SYSTEM_HEALTH_2026-09-13.md`.

## 2026-09-10/11 — Dashboard 6 tabs, ingest Schumann/Delta, ONNX retrain

- Dashboard React: exactamente 6 tabs; APIs RO schumann_vivo/delta/clima_espacial; promovido Dev→Test→Prod.
- Telegram messaging: eliminado copy "lotería" de alertas/digest.
- Ingest: WPC Tomsk (linaje Drive extractor_vision_schumann); sin fallback falso 7.83/0; Schumann vivo 8.26/21.46; clima 2026 gapfill; sismos refetch; Delta no escribe all-zero.
- ONNX: wipe+retrain; Prod deja bootstrap-only y gana Loki.
- Docs: SESSION_2026-09-10.md, SYSTEM_HEALTH, INGEST_FIX, TRAIN_RESTART, DASHBOARD_6TABS_DONE.
- No corrido: launcher --entrenar firmas.

# Changelog - Sentinel Omega

## [Unreleased] - 2026-09-10 - Dashboard 6 tabs → Prod + lottery scrub + health/ingest docs

### Changed
- Promocion Dev→Prod (flat + nested) del dashboard React 6 tabs + api.py/README/package.json (puerto 5174).
- Messaging loteria scrub (0 matches en Prod); restart ~18:06 CST.
- Docs: SYSTEM_HEALTH_2026-09-10.md, DASHBOARD_6TABS_DONE.md, INGEST_FIX_2026-09-10.md stub (pending).

### Notes
- Health OK. DB empty/flat (correlaciones vacias / frescura) documentado; DB file no escrita en esta pasada.
- Blockers: correlaciones vacias, ONNX placeholder, tsc shim, prod gate firmas, ingest PENDING.
- NO se habilito entrenar/firmas/remapeo. Streamlit 8501 legacy sin tocar.

---


## [2.5.4] - 2026-09-04 - Fixes: Vite/Health/Telegram — documentado

### Fixed
- **Vite dev WSL→Windows (ERR_CONNECTION_REFUSED)**:  host  aislado de WSL no ruteaba a Windows. Fix:  +  en  local (gitignored). Verificado Microsoft Windows [Versi¢n 10.0.26340.9233]
(c) Microsoft Corporation. Todos los derechos reservados.

C:\Windows\System32> y  ambos 200 desde Windows.  también en  con CORS para 5173/5174.
- **Dashboard DB desconectada (falso negativo)**: frontend esperaba  pero  devolvía  sin wrapper. KPI "DB Conectada" salía No/rojo aunque DB 834M/11259 ciclos estaba OK. Fix:  ahora envuelve  →  vía . Verificado .
- **Launcher crash loop **:  importaba  solo dentro de , pero lo usaba fuera. Cada ciclo (211s) fallaba. Fix:  arriba de , pycache limpiado.
- **Servicios colgados**:  stale 1 día (duplicado) y  15h 98% CPU → /.

### Added
- **Build prod estático**:  1.01s 63 módulos 282KB/85KB gzip  como fallback sin depender de vite dev.

### Docs
- README sección Dashboard dev/troubleshooting, CLAUDE arquitectura dashboard, este CHANGELOG.

## [2.5.4] - 2026-09-04 - Compat Layer + API/React + Health

### Added
- **FastAPI compat layer** (): 13 alias sin prefijo  para el frontend React (, , , , , , ) — resuelven contra  reales con fallback sintético; verificados 13/13 con  (200).
- **Dependencias API**: , ,  en .
- **Dashboard React** (): 6 tabs (Principal/Telemetría/Consenso/Análisis/Agentes/Sistema),  63 módulos 282KB/85KB gzip.

### Fixed
- **Health DB path**:  symlink a  para que  resuelva  desde layout nested.
- **Imports dual-layout**:  y  sincronizados flat↔nested; Obtaining file:///C:/WINDOWS/system32 reinstalado.

### Changed
- **Versión**:  2.5.0 → 2.5.4.
- **Docs**:  (dashboard React 6 tabs + Streamlit 11 legacy, 8 agentes),  (8 agentes).

---

## [Unreleased] - 2026-09-04 - The Third Act: Loki & SNT Evolution

### Added
- **Loki Agent (Act 3)**: Implementation of the Unified Field Theory (Fractal-Bayesian).
  - Logic: Gauss-Jordan Cleaning -> Fourier Frequency Scan -> Bayesian Probability Update.
  - Base Node: Tlaxcala, Mexico.
- **SNT Evolution**:
  - **Delta (Financial)**: Removed WATCH ceiling. Delta now emits ALERT for extreme financial stress.
  - **Beta-1 (The Artist)**: Reprogrammed to generate "Cymatic Figures" (system vibration snapshots).
  - **Beta-2 (The Analyst)**: Reprogrammed to interpret figures, search for historical replicas by magnitude, and weigh against atmospheric stress.
  - **Alfa-2 (Satellite)**: ELIMINATED LIVE TRAINING. Now forces use of historical baseline to prevent adaptation to cycle noise.
- **Consensus Hierarchy**: Updated pipeline to SNT -> Omega -> Loki.
- **AGENTS.md**: Created the formal registry of agent roles and the consensus ladder.

### Changed
- **Consensus Logic**: The Father now acts as a tiered validator across the three acts.
- **Alfa-2**: Transitioned from online learning to historical baseline deviation analysis.

---

## [Unreleased] - 2026-09-04 - Consensus Hierarchy & Juez Law

### Changed
- **Padre Agent (GeodynamicPadre)**: Implemented Three-Act Consensus Hierarchy.
  - Act 1: SNT Families (Alfa/Beta/Delta) cross-validation with Schumann correlation.
  - Act 2: Omega spatial/cosmic corroboration.
  - Act 3: Loki Bayesian probability collapse (threshold 0.8).
  - Decision logic: THREE ACTS ALIGNED = MAX CONFIDENCE ALERT (0.98).
  - Veto logic: Loki probability below threshold blocks full confirmation.
- **Juez (Disciplinary Engine)**: Implemented Asymmetric Punishment Law.
  - **JUEZ LAW**: If Padre fails corroboration (Miss on real event), punishment is DOUBLE for Padre AND the originating bots that alerted.
  - Severity scaling: Exponential (gravity^2) for false negatives.
  - Recidivism tracking per bot.
  - Fase separation: viva (live ops) vs reconocimiento/backtest/observacion (training) to prevent contamination.

### Technical Details
- Padre now extracts Omega and Loki signals separately for hierarchical evaluation.
- Loki validation requires probability >= 0.8 for final confirmation.
- Juez applies extra severity (SEVERIDAD_FALLO_BASE) to both Padre and originating bots on corroboration failure.

## [Unreleased] - 2026-09-04 - Padre & Juez Implementation Complete

### Added
- **Padre Agent (GeodynamicPadre)**: Full Three-Act Consensus Hierarchy implemented.
  - Act 1: SNT Families (Alfa/Beta/Delta) cross-validation with Schumann correlation (>0.3).
  - Act 2: Omega spatial/cosmic corroboration required.
  - Act 3: Loki Bayesian probability collapse (threshold >= 0.8) for final confirmation.
  - Decision matrix: THREE ACTS ALIGNED = MAX CONFIDENCE ALERT (0.98).
  - Veto logic: Loki below threshold blocks full confirmation; SNT+Omega can alert without Loki.
  - Loki signals extracted and validated separately in hierarchical evaluation.
  - Omega elevation logic preserved for reference scenarios.
  
- **Juez Agent (Disciplinary Engine)**: Asymmetric Punishment Law implemented.
  - **JUEZ LAW**: If Padre fails corroboration on real event (MISSED_EVENT), punishment is DOUBLE for Padre AND originating bots that alerted (informant bonus for those who were right).
  - Severity scaling: Exponential (gravity^2) for false negatives.
  - Recidivism tracking per bot in TBL_PESOS_BOTS.
  - Phase separation: viva (live ops) vs reconocimiento/backtest/observacion (training) to prevent contamination.
  - Weight floor at 0.2 to maintain voting diversity.
  - Informant bonus (+0.1) for bots that correctly alerted while Padre ignored.

- **Loki Integration in Pipeline**: 
  - GeodynamicLayerRunner now instantiates and runs LokiAgent.
  - Loki ingests Bz, Solar Wind, Schumann, VIX, LOD data.
  - Loki signal passed to Padre for Three-Act evaluation.

### Technical Details
- Padre extracts Omega and Loki signals separately for hierarchical evaluation.
- Loki validation requires probability >= 0.8 for final confirmation.
- Juez applies double severity to both Padre and originating bots on corroboration failure.
- Audit trail stored in TBL_JUEZ_AUDITORIA with full cycle reconstruction.

## [Unreleased] - 2026-09-04 - Loki Pipeline Integration

### Added
- **GeodynamicLayerRunner**: Full Loki integration into the execution pipeline.
  - LokiAgent instantiated in __init__ as part of the core agent suite.
  - Loki data extraction from pipeline: Bz GSM, Solar Wind, Schumann Resonance, VIX, LOD.
  - Loki ingestion and analysis executed in run() cycle before Padre consensus.
  - Loki signal appended to the signals list passed to Padre for Three-Act evaluation.
  - Logging of Loki signal type and confidence for telemetry.

### Technical Details
- Runner now imports LokiAgent from sentinel_omega.layers.geodynamic.loki.agent.
- Loki receives real-time space weather, Schumann, financial, and rotational data.
- Loki's Bayesian probability collapse result feeds directly into Padre's hierarchical consensus.
- All agents now execute in the correct order: SNT Families -> Omega -> Loki -> Padre.

## [Unreleased] - 2026-09-04 - Dev Retraining Complete & Back-end Validated

### Added
- **ONNX Models Retrained (Bootstrap)**: All 6 agents retrained on synthetic data (2500 samples each)
  - alfa1_spaceweather_rf.onnx (785,805 bytes) — Space Weather (30 yr)
  - alfa2_satellite_cnn.onnx (32,222 bytes) — Satellite Thermal (14 yr)
  - beta1_schumann_fft.onnx (466,483 bytes) — Cymatic Artist (30 yr)
  - beta2_atmospheric_cnn.onnx (30,834 bytes) — Atmospheric Analyst (14 yr)
  - delta_financial_lstm.onnx (80,330 bytes) — Financial Sentiment (10 yr)
  - omega_espacial_rf.onnx (259,110 bytes) — Cosmic Correlator (30 yr)
- **Alfa-2 Historical Baseline**: Computed from 2,301 satellite records (tbl_cobertura_satelital)
  - 3 zones: guerrero_gap, oaxaca_costa, chiapas
  - Stored at 
  - Alfa-2 now loads baseline on startup — ZERO live training

### Validated
- All agents import and instantiate correctly
- All ONNX models load and infer (confidence + signal outputs verified)
- GeodynamicLayerRunner integrates Loki Agent in pipeline
- Padre consensus hierarchy: SNT Families → Omega → Loki (Three Acts)
- Juez asymmetric discipline engine operational (TBL_JUEZ_AUDITORIA: 901,852 records)
- Alfa-2 historical baseline loaded at runtime (no live training)

### Status
**BACK-END v2.5.4 COMPLETE** — Ready for dashboard/frontend simplification (19 → 6 tabs)
