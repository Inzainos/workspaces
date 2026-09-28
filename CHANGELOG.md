# Changelog — Sentinel Omega

## [Unreleased] - 2026-09-28 - Dashboard v3: rediseño + seis datos que mentían

Sin commit, sin push. Trabajo sobre el dashboard React (`:5173` → API `:8787`).
Verificado de punta a punta contra la DB de producción en modo lectura y en
navegador real (Comet vía CDP): 7/7 pestañas, consola sin errores, sin overflow
horizontal en 1920/1280/768/390.

### Fixed — datos incorrectos que el tablero presentaba como buenos

Seis hallazgos. Los cuatro primeros son la misma familia: **el default benigno
convirtiendo "no tengo el dato" en un número plausible** (regla dura 8).

- **`/api/health/apis` descartaba 5 de 6 fuentes en silencio.**
  `tbl_locf_cache.updated_at` es `REAL` (epoch), pero el endpoint le aplicaba
  `strptime` (espera `str`) dentro de un `try/except: pass`. Resultado:
  `TypeError` para alfa1/alfa2/beta1/beta2/delta y el strip del encabezado
  mostraba **dos** chips (usgs, beta1) como si ése fuera el inventario
  completo. Nuevo helper `_edad_horas` acepta epoch y texto; lo ilegible sale
  como `DESCONOCIDO`, nunca omitido. Verificado: de 2 chips a 6.
- **Schumann congelado se reportaba `LIVE`.** `tbl_schumann_vivo` tiene **25
  filas con un solo valor distinto** (8.26 Hz / 21.46) desde el 25-sep: Tomsk
  sirve una imagen estática y el registro se reescribe cada hora, así que por
  frescura parecía vivo. Nuevo estado **`CONGELADO`** cuando la serie no varía
  en la ventana, con la nota explicando que la fuente "se refresca pero no
  mide". Frescura ≠ validez.
- **`viva_real` contaminada con 603 veredictos duplicados.** La vista sólo
  filtra `fase='viva'`; no excluye los `en_vivo=0` marcados el 27-sep (los dos
  Sentinel escribiendo a la vez). Añadido `COALESCE(en_vivo,1)=1` a las **5**
  consultas de asertividad (`aciertos`, `counts`, Molchan de `/api/aciertos` y
  `/api/bots`, y las series diarias de `/api/aprendizaje`).
- **`biblioteca_n: 0` con la tabla ausente.** Ausente y vacía se veían igual:
  el tablero pintaba «BIBLIOTECA 0» junto a «PATRONES 296.818», que se lee como
  una biblioteca vaciada. Ahora `biblioteca_n` es `None` y va acompañado de
  `biblioteca_presente`; el front dice "tabla ausente, no es una biblioteca
  vacía".
- **Barra de veredictos mezclaba dos universos.** `aciertos_total` (138.068) es
  la suma **por bot** de `TBL_PESOS_BOTS` —cada ventana contada una vez por
  cada bot que opinó— mientras que los falsos positivos (1.651) son del
  sistema. Dibujar la proporción con ambos daba **0 % de falsas alarmas**.
  Nuevo `veredictos_sistema` con los tres del mismo universo (`viva_real`,
  `en_vivo=1`): 21.400 / 1.651 / 313, que coincide exactamente con la DB.
- **El tab Reportes pintaba el correo en verde y "activo".** Es falso desde el
  2026-09-15: `correo.py` se borró, las SMTP están comentadas y **cero código
  lee `tbl_correo_salida`** (verificado por grep). `enviar_correos.py` despacha
  por Telegram pese al nombre. Ahora aparece tachado como "retirado" con la
  explicación. Un canal muerto en verde es peor que no mencionarlo.

### Changed — rediseño del tablero

Sistema nuevo en `web/src/index.css` + `web/src/components/ui/data.tsx`.
Documentado en `infrastructure/dashboard/README.md`.

- **El color saturado significa riesgo, y nada más.** Rampa de riesgo en oklch
  con luminancia pareja (~0.72 L) para que ninguno grite más por accidente; el
  cromo en neutros fríos; las series de gráfica en azules/teales desaturados
  para que una línea de datos no se confunda con un estado. El indigo genérico
  deja de ser decoración y queda sólo como acento de interfaz (foco, tab
  activo).
- **Superficie antes que composición.** Cada pestaña se diseñó contra una:
  Principal/Predicciones/Señales = **Monitor**, Modelos = **Compare**,
  Mapas/Reportes = **Explore**, Presentación = **Decide/Learn** (la única donde
  un hero es correcto). Principal pierde el hero y la rejilla de 7 KPIs
  equivalentes; gana una franja de estado (Fantasma sobre su escala real con
  los umbrales dibujados, Muro como 5 segmentos, telemetría) que se lee de
  reojo.
- **La asertividad ya no se puede leer sola.** Va en el mismo panel que la
  ganancia de Molchan y la barra de veredictos, con una nota que explica la
  contradicción aparente: 97,7 % junto a 0,84× significa "acierta casi siempre
  porque casi siempre está en calma, y sus alarmas todavía no superan a alertar
  a ciegas".
- **Gráficas con escala.** `LineSpark`/`SimpleBars` ahora rotulan eje Y,
  aceptan líneas de referencia (15/30 del Fantasma, 7.83 Hz de Schumann, 0.6 de
  delta) y manejan el caso de serie constante — antes el Schumann plano rotulaba
  "8.0 / 8.0 / 7.0" por colapso del dominio.
- **Tipografía elegida, no heredada.** IBM Plex Sans/Mono por su `0` rebanado y
  `1` con base: a 11px distinguen un `0.01` de un `0.07`. Cifras comparables en
  `tabular-nums`; `DataTable` alinea a la derecha las columnas numéricas.
- Primitivas nuevas: `Panel`, `Metrica`, `Cifra`, `EscalaRiesgo`,
  `SegmentosMuro`, `BarraVeredictos`, `ChipFuente`, `SinDatos`, `BannerError`.
  `<Cifra>` distingue sola "sin lectura" de "midió cero" con `.dato-ausente`.
- `MapasTab`: `Number(sat ?? 0)` marcaba como 0.00 los nodos **sin medición**,
  indistinguibles de los medidos en reposo. Ahora se separan (88 de 125 estaban
  en cero) y los no medidos quedan fuera del ranking.
- `SenalesTab`: las series filtran nulos en vez de dibujarlos como cero, y
  reportan cuántas lecturas faltaron.
- Accesibilidad: skip-link, `:focus-visible` real, 44px de objetivo táctil en
  punteros gruesos, `prefers-reduced-motion` respetado.

### Verified

- `npx tsc -b` limpio · `npm run build` 67 módulos, 333 KB / 102 KB gzip.
- Navegador real (Comet/CDP, 1600×1000): 7/7 pestañas renderizan, **0 errores
  de consola**, sin `NaN`/`undefined`/`Infinity` en el texto de ningún panel.
- Responsive sin overflow horizontal: 1920×1080, 1280×800, 768×1024, 390×844.
- `/api/health/apis` → 6 fuentes (antes 2), `beta1: CONGELADO` con nota.
- `/api/bots` → `veredictos_sistema` = 21.400 / 1.651 / 313, contrastado contra
  `SELECT resultado, COUNT(*) FROM viva_real WHERE COALESCE(en_vivo,1)=1`.
- `PRAGMA integrity_check` = `ok`; `TBL_CICLOS` = 3.660 al inicio de la sesión.

### Pendiente

- La DB no tiene tabla de métricas ONNX; el tab lo dice en vez de inventar
  curvas.
- `tbl_schumann_vivo` seguirá `CONGELADO` hasta que se arregle la ingesta de
  Tomsk. El tablero ya lo avisa; el dato sigue entrando como NULL al Fantasma.


## [Unreleased] - 2026-09-27 - Una sola instancia (usuario), Schumann WPC, ONNX solo en_vivo, túnel cerrado

Sin commit, sin push. Detalle: `estado/BITACORA_2026-09-26.md`, `estado/OPERACIONES_2026-09-27.md` (C),
`estado/TELEGRAM_2026-09-27.md` (T), `bridge/TERMUX.md` (A), `deploy/DEPLOY.md`, `CANAL_CLAUDE.md`.

### Fixed
- **Dos Sentinel escribiendo a la vez** (usuario + sistema/root). Unidades de sistema `sentinel-omega` y
  `sentinel-omega-watchdog` en `masked` (~20:05); decisión del Capitán 20:37: corre la unidad de **usuario**.
  594 veredictos del proceso viejo/duplicados marcados `en_vivo=0` (20:14:43, con respaldo).
- **Schumann WPC**: `shm.jpg` de Tomsk era imagen estática (1-sep-2025, 8.26 Hz / 25.0). Revisión por
  `Last-Modified` + valor repetido; PREC queda NULL/NULL sin lectura viva (C, aprobado T, 77/77 tests).
- **`train_onnx_from_db.py`**: etiquetas del Juez filtran `COALESCE(en_vivo,1)=1` (antes solo `fase='viva'`);
  esperado 23 283 etiquetas en vez de 23 670 (C, aprobado T, 64/64).
- **Token de Telegram**: `deploy/.env` tenia el token viejo de SismoBio_Bot (401); cambiado al valido a las 19:42, permisos `600` y respaldo (detalle en `estado/TELEGRAM_2026-09-27.md`, T).

### Changed
- `deploy/install.sh` y `.service`: unidades de usuario (`%h/workspaces`, `default.target`, linger),
  marcadores `__REPO_DIR__`/`__RUN_USER__`/`__RUN_UID__`; `mantenimiento` y `onnx-retrain` con `User=`;
  `dashboard-web` fuera de `USER_UNITS`. `network_watchdog.py` usa `systemctl --user`.
- SSH: solo llave; `authorized_keys` con `restrict,port-forwarding,permitopen="127.0.0.1:11434"`;
  `AllowTcpForwarding local` (21:00). Prueba `-R` rechazada y "Nodo OK" (21:09).
- `chown` de `sentinel_omega/` a deamon (353 archivos de root); timer de mantenimiento parado esta noche.

### Pendiente
- Rebuild + ONNX de Claude en curso (desde 20:27:55); arranque `--user`, marcado Schumann 534/541 y PREC.
- Con sudo: reinstalar `mantenimiento`/`onnx-retrain` antes del 4-oct; unidad `rutinas` como root.
- Regla (e) de subir/bajar alarmas: decisión del Capitán.


## [Unreleased] - 2026-09-03 - Consenso Telegram: digest horario + solo sin precedentes

### Added
- `infrastructure/messaging/consenso_vigilante.py` — el Padre (bot de consenso) agrupa avisos de los demás bots.
  - **Reporte horario SIEMPRE** (`TG_DIGEST_MINUTES=60`): Fantasma+nivel, muro n/5, telemetría one-liners, top precursores, loop vivo/muerto, botón Mini App. No se salta la hora aunque esté calma. No es un montón de pings "precursores revisar".
  - **Telegram inmediato SOLO si `is_unprecedented`**: sin registro previo en el sistema. Califica: cimática NUEVO (`tbl_cimatica_patrones.frecuencia==1`), firma nunca vista (`TBL_FIRMAS` estado=`nueva` / recurrencia≤1), tipo de muro breach nuevo, `SYSTEM_DEAD` (loop muerto). Firmas recurrentes y precursores de siempre → solo el reporte horario. El cooldown `send_alert_gated` (1800s) se conserva en el path inmediato para no spamear el mismo tipo.
  - Mini App: `infrastructure/dashboard/static/mini.html` servida por FastAPI en `/mini`. Botón `web_app` si `TELEGRAM_WEBAPP_URL` es HTTPS público. No se fabrica túnel.
- Templates nuevos/enriquecidos (español, captions de qué significa el número, sin claims de lotería): `cimatica_nuevo`, `firma_nueva`, `muro_breach`, `sin_precedente`.
- Tests: `tests/test_consenso_vigilante.py` (buffer vs immediate, digest vacío, cooldown, DB firmas/cimática, dry_run, cero red).

### Changed
- `AlertService.dispatch` canal Telegram pasa por el vigilante; correo y log siguen igual.
- `orchestrator.py` ya no dispara `send_alert_gated`/`send_photo` por cada precursor ≥0.5; ingesta al vigilante y `maybe_flush` al cierre de ciclo.
- `dispatch_cycle_alerts` y cimática consistente dejan de pagear; cimática NUEVO sí (sin precedentes).
- Env: `TG_DIGEST_MINUTES` (default 60), `TELEGRAM_WEBAPP_URL` (HTTPS), `SENTINEL_DRY_RUN`.

### Policy (Elán)
Digest horario siempre. Immediate = solo lo que no tiene registro. No hay page por rojo/naranja rutinario.

---
All notable changes to the Sentinel Omega precursor detection system are
documented here. Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
conventions. Dates are UTC-6 (local time of the author).

---
## [Unreleased] - 2026-09-01 - Fixes operativos + corrección 125 nodos UVG

### Fixed
- `sentinel_omega/launcher_hex/h00..h11.hex`: `_check_already_running` ahora captura `PermissionError` (pid de root visto desde deamon) → `return True` en vez de traceback; `_clear_pid` resiliente a `OSError`. Backup en `launcher_hex_backup_1788196565/`. Verificado: `launcher.py --once` con pid root ahora responde `ERROR already running` limpio.
- `sentinel_omega/shutdown.py`: `_process_alive` captura `PermissionError` → `True`; `shutdown()` detecta pid de otro usuario y sugiere `sudo kill -TERM <pid> && sudo rm data/sentinel_omega.pid` en vez de colgarse 30s.
- `deploy/generar_reporte.py`: detecciones deduplicadas por `GROUP BY tipo` con `MAX(id)` + rehidratación → 6 tipos distintos en lugar de 8 filas duplicadas (SEISMIC_CLUSTER/SILENT_TRIGGER x4); texto Molchan corregido `50 nodos reales` → `125 nodos UVG (75 reales + 50 Ghost)` con dispersión global nodal. Reporte regenerado `2026-09-01_09-00_MX.md`.

### Verified
- `python sentinel_omega/launcher.py --once` con pid root → exit 1 controlado
- `python sentinel_omega/shutdown.py` con pid root → mensaje sudo claro
- `python deploy/generar_reporte.py` → REPORTE.md con 6 precursores distintos y texto 125 nodos
- `pytest test_precursor / test_schumann_filter` → PASS

## [Unreleased] - 2026-08-29 - Alertas enriquecidas Telegram (v2.5.3 - graficas, tablas, cimatica)

### Added
- `infrastructure/api/telegram.py`: `send_photo(path, caption)` y `send_document(path)` - envio de PNG/PDF a Telegram (caption HTML 1000 chars, timeout 20s, usa TELEGRAM_BOT_TOKEN/CHAT_ID).
- `infrastructure/messaging/charts.py` (95 lineas, nuevo): generador de graficas con `matplotlib Agg` (sin display) en `/tmp/sentinel_charts/` (env `SENTINEL_CHARTS_DIR`):
  - `fantasma_timeline(valores, labels, titulo)` - linea Fantasma con bandas AMARILLO 15 / ROJO 30, punto final rojo si activo, 36K PNG verificado.
  - `cimatica_bars(patrones, titulo)` - barras frecuencia por patron_id (verde si tiene event_class).
  - `precursores_tabla_png(filas, titulo)` - tabla precursores como imagen.
- `infrastructure/messaging/alert_service.py`: nuevos templates `AlertTemplates.cimatica_consistente()` (patron 3x, tabla + que significa) y `AlertTemplates.reporte_resumen()` (tabla 5 precursores + Fantasma/Muro/Consenso).
- `core/firmas/cimatica.py`: al alcanzar `frecuencia==3` dispara `AlertService.dispatch(telegram+log)` + envia `cimatica_bars` (top-5 `frecuencia>=2`) como foto via `send_photo` (no bloqueante, fail silencioso).
- `orchestrator.py`: enriquecimiento de alertas precursor - descripcion por tipo (schumann/sismo_cluster/solar/volcanic/cosmic/silent_trigger), tabla de todos los activos, cimatica top-3 (`tbl_cimatica_patrones WHERE frecuencia>=2`). Si `fantasma>5` genera `fantasma_timeline` (ultimos 10 de `tbl_salud_sistema`) y envia como foto con caption `Fantasma X | display_name`.

### Changed
- `orchestrator.py`: umbral precursor `0.7 -> 0.5` (mas cobertura, antes se perdian debiles).
- `sentinel_omega/README.md`: seccion `## Observabilidad y Resilience (v2.5.3)` con subseccion `### Alertas enriquecidas Telegram (v2.5.3)` documentando fotos, charts, templates y wire cimatica.

### Dashboard (v2.5.3)
- `infrastructure/database/repository.py`: `cimatica_top_patrones(limit=20)`, `cimatica_stats()`, `fantasma_timeline(limit=50)` - queries `tbl_cimatica_patrones` / `tbl_salud_sistema`.
- `infrastructure/dashboard/app.py` (11 tabs, +96 lineas): nueva pestaña 10 `Cimatica` con `render_cimatica()` (metricas, barras plotly, tabla 20, pie por clase, PNG Telegram) + pestaña 1 enriquecida con `Timeline Fantasma 50 ciclos` (bandas 15/30, scatter + hline) + vista previa Telegram.
- `sentinel_omega/README.md`: seccion Dashboard 9->11 tabs con tabla actualizada y bloque "Novedades v2.5.3".

### Verified
- `registrar_snapshot` x3 -> frecuencia 3 dispara Telegram OK (log "CIMATICA CONSISTENTE").
- `fantasma_timeline([3,5,8,12])` -> 36K PNG en `/tmp/sentinel_charts/fantasma.png` OK.
- `AlertTemplates.cimatica_consistente(1, "bz:-2|wind:4", 3, "SISMO_M5")` -> `CIMATICA` OK.
- `pytest sentinel_omega/tests/test_cimatica_correo.py` 23 passed; suite completa 389 passed (--ignore=test_pipeline.py).

## [Unreleased] - 2026-08-29 - Mejoras Estructurales (Observabilidad + Resilience + Config)

### Added
- **Config declarativa YAML** (config/sentinel.yaml, 60 lineas): defaults versionados (app, database, logging, api, telegram, pipeline, models, precursor, consensus, scheduler). config/sentinel_config.py con load_config(yaml_path) que mergea YAML + env vars (env gana), HAS_YAML fallback, seccion circuit_breaker en api.
- **Logging estructurado JSON** (infrastructure/logging/formatter.py, 50 lineas + __init__.py): JSONFormatter (timestamp UTC ISO, level, logger, module/func/line, extras, exception), setup_logging(level, log_file, fmt, max_bytes, backup_count) con RotatingFileHandler (10MB x 5) + console. Silencia urllib3/requests/httpx. Configurable json/text via sentinel.yaml (logging.format).
- **Health checks** (infrastructure/health/checks.py, 95 lineas + __init__.py): HealthChecker con 4 checks - database (SELECT name FROM sqlite_master, 5 tablas), disk (shutil.disk_usage, free_gb), apis (NOAA SWPC 200, latency_ms), pipeline (MAX(ts) en tbl_salud_sistema, age_hours; ok<2h/warn<6h/fail>6h). get_health() dict, CLI python -m sentinel_omega.infrastructure.health.checks. Estado: DB ok, disk 7% (949GB free), APIs ok (200ms), pipeline FAIL (294h sin ciclo).
- **Circuit breaker** (infrastructure/api/circuit_breaker.py, 95 lineas): CircuitConfig (failure_threshold=5, recovery_timeout=60, half_open_max_calls=3, success_threshold=2), CircuitBreaker thread-safe (CLOSED->OPEN->HALF_OPEN->CLOSED), registry global, decorador @circuit(name). Wireado a noaa.py (5 fetches), usgs.py, nasa_neo.py.
- **Resilience HTTP** (infrastructure/api/_http.py +10 lineas): tenacity (retry_api: 3 intentos, wait_exponential 1->10s, retry_if_exception_type(ConnectionError,Timeout), before_sleep_log) + fetch_with_retry(fn) ademas del urllib3 Retry (429/500/502/503/504, backoff 1s->4s).
- **Tooling centralizado** (pyproject.toml +24 lineas): dependencies +pyyaml, +tenacity, +python-dotenv; [tool.pytest] (testpaths, strict-markers, slow), [tool.ruff] (line-length 100, py310), [tool.mypy] (py310, ignore_missing_imports).
- **requirements.txt** +3 deps: tenacity>=8.2, pyyaml>=6.0, python-dotenv>=1.0; .gitignore +.env+logs/.

### Changed
- infrastructure/api/_http.py: import logging + tenacity, logger centralizado, wrapper fetch_with_retry.
- config/sentinel_config.py: +41 lineas (Path, yaml, load_config()), config = load_config() lazy YAML.
- sentinel_omega/.env.example: +NASA_API_KEY, LOG_LEVEL/FORMAT, CB_*.

### Fixed
- infrastructure/health/checks.py: WHERE type=table -> type=single-quoted table (syntax error), MAX(timestamp) -> MAX(ts) (columna real tbl_salud_sistema.ts), f-string join fix.
- infrastructure/api/_http.py: orden de imports (logging antes de requests, logger antes de retry_api).

### Verified
- pytest sentinel_omega/tests/ --ignore=test_pipeline.py: 389 tests OK. health, logging, circuit_breaker, _http, sentinel_config.load_config() imports OK desde workspaces.



## [Unreleased] — 2026-08-22

### Added
- **AlertService unificado** (sentinel_omega/infrastructure/messaging/alert_service.py, 137 lineas): centraliza reportes/alertas/mensajes Telegram/Correo/Log. Severity tipado ROJO/AMARILLO/VERDE/AZUL, FormattedMessage, AlertTemplates 7 templates puros (centinela_critico/grieta/tormenta/advertencia, precursor, consenso, sistema_online/dead, heartbeat) y AlertService.dispatch multi-canal con dry_run, gate anti-spam y outbox tbl_correo_salida fail-soft. Reemplaza 6 origenes dispersos; telegram.py/correo.py quedan como adapters intactos.
- **ReportEngine unificado** (sentinel_omega/infrastructure/pipeline/reporte_engine.py, 120 lineas): ReportEngine con render(tipo,filtros) y render_to_file versionando en estado/historial/AAAA/MM/ + actualizando estado/REPORTE.md. Delega a reporte_sentinel.py existente (871 lineas intactas), mantiene wrappers para scheduler_reportes.py sin cambios.
- **Dashboard pestana Agente** (sentinel_omega/infrastructure/messaging/agent_bridge.py 87 lineas + sentinel_omega/infrastructure/dashboard/agent_tab.py 100 lineas): agent_health lee config.yaml + data/shared_memory.db + ollama sin bloquear; agent_run_audit/agent_run_task via subprocess. render_agent_tab muestra metricas Root/DB/Ollama/Umbral 85, modelos, ultimos consensos e historial. Patch dashboard/app.py: 10a pestana Agente.
- **consensus-expert-agent fix contexto y consenso** (/home/deamon/consensus-expert-agent): repository_context prioriza estado/HANDOFF.md+INFORME_CORRECCIONES.md, shared_context.research_context, orchestrator loop while true hasta umbral 85, threshold 85 max_refinement_rounds 0, flags --audit/--focus/--check/--web. Validado qwen2.5:1.5b 95-100/100.

### Changed
- infrastructure/messaging nuevo paquete; infrastructure/pipeline/reporte_engine.py nueva capa DRY; infrastructure/dashboard/app.py 9 a 10 pestanas.
- **Autostart + Watchdog** (deploy/sentinel-omega-watchdog.service + sentinel_omega/infrastructure/watchdog/network_watchdog.py, 124 lineas): servicio systemd Restart=always con StartLimitInterval 300s, chequea red cada 60s (socket 8.8.8.8/1.1.1.1 + http fallback) y health del agente via agent_bridge; si falla 3 veces seguidas y hay red pero agente mal => systemctl restart sentinel-omega/scheduler; si vuelve red => notifica via AlertService y re-levanta servicios caidos. sentinel-omega.service ahora RestartSec 10 + StartLimit. install.sh instala y habilita watchdog.

### Fixed
- Dispersion de formatos de alerta (6 origenes) y duplicacion de severidad/cooldown; single source of truth testeable.

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

## [Unreleased] — 2026-09-15 (Persistencia y Resiliencia)

- **LOCF (Last Observation Carried Forward) Persistente**: Se migró el cache en memoria a la tabla 	bl_locf_cache de SQLite en data_pipeline.py y 
epository.py garantizando la continuidad de los precursores en caso de caída de las APIs de origen o reinicio del sistema.
- **Refetch Automático Diario**: Implementado check_and_refetch_stale_apis en mantenimiento.py para correr de manera automática los scripts de backfill (sismos_refetch_recent.py y clima_gapfill_2026.py) si detectan un lag mayor a 7 días.
- **Salud de APIs (Endpoint /api/health/apis)**: Dashboard enriquecido con una ruta para observar en tiempo real la latencia y el estado (*LIVE*, *LOCF_ACTIVE*, *STALE*) de todas las integraciones subyacentes.
- **Backfill Manual Ejecutado**: Recuperados 2,203 sismos de USGS correspondientes a los últimos 30 días para sincronizar TBL_HISTORICO_SISMICO con la operación en tiempo real.
