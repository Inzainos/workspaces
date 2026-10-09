# Sentinel Omega

Precursor detection platform for natural events.
Author: Elan Zainos Corona (Fractal Core Research)

## ⛔ REGLA #0 — nunca asumas, siempre revisa

No des nada por hecho ni por "conectado" sin verificarlo contra el código y,
cuando aplique, **corriendo el flujo de punta a punta** — que pasen los tests
unitarios NO prueba que el pipeline completo quede conectado. Antes de decir
"ya está": ¿la tabla se pobló?, ¿el reporte lee la sección?, ¿el script corre
sin error real? Si no lo verificaste, no lo afirmes; di qué falta comprobar.
Esta regla manda sobre todo lo demás.

## What this project does

Sentinel Omega detects **precursors of natural events** (earthquakes, volcanic activity, solar storms, tsunamis, etc.) using real-time geophysical data from NOAA, USGS, ESA, and other sources. It uses Shadow Node Theory (SNT) **only as the mathematical framework** (power law R(t) = a·t^b), not as the system's core purpose.

The system is the successor to the TITAN V32/V46/V53 bot family.

## Architecture — 8 Agents (SNT 5 + Omega + Loki + Padre), Single System

```
Orchestrator → GeodynamicLayerRunner → 8 Agents (SNT×5 + Omega + Loki) → Padre Consensus
│
├── Alfa-1 (Geodynamic: Bz, solar wind, seismic) — 30yr training
│       ↑ validates
├── Alfa-2 (Satellite: ESA Sentinel) — 14yr training
│
├── Beta-1 (The Artist — Cymatic Figure) — 30yr training  ← HEARTBEAT
│       ↑ validates
├── Beta-2 (The Analyst — réplica histórica + gas/presión) — 14yr training
│
├── Delta  (Fin stress — WATCH si combined>0.6; NUNCA ALERT) — 10yr training
│
├── Loki  (Fractal-Bayesiano: Gauss-Jordan→Fourier→Bayes, nodo Tlaxcala)
├── Omega  (Memoria/correlación: ritmo cósmico — luna, Schumann, envolvente
│           solar, acoplamiento Schumann↔mercado) — 30yr, NO es agente en vivo
│
└── Padre  (Hierarchical cross-family validator)
        ├── TITAN V32 Fantasma Risk Index
        ├── Precursor Scanner (15 types)
        └── Muro de los 5 Eventos
```

**Hierarchy**: #2 agents → report to #1 → Padre cross-validates across families.
**Schumann is the heartbeat**: Everything correlates against Schumann resonance (Beta-1).
If Schumann is perturbed alongside any other signal = precursor detected.

**Families**:
- `space_weather`: Alfa-1, Alfa-2
- `schumann_cymatics`: Beta-1, Beta-2
- `financial_sentiment`: Delta
- ` Correlation Alpha's Telemetry, Schumann Resonance, Delta and Beta's Patterns':Omega

**Consensus requires**: >= 2 families active + >= 2 alerts + schumann_correlation > 0.3

## Key formulas

- **Fantasma**: `(abs(bz)^2) + (viento*0.02) + (sch_wpc*1.5)` + pressure/Kp/LOD modifiers
- **Risk levels**: LOW (<5), MODERATE (5-15), HIGH (15-30), CRITICAL (>=30)
- **Asymmetric loss**: Miss penalty = 10x, False alarm = 1x
- **Beta-1 (honesto)**: FFT PLANO del Kp (`kp_spectral_features`) + Schumann
  MEDIDO de Tomsk (excitación >15% suma confianza; >30% con espectro calmo →
  WATCH). El viejo "filtro armónico"/coherencia era numerología y se eliminó.
- **Molchan**: ganancia = hit_rate ÷ tasa base (modelo nulo alertar-siempre,
  `core/precursor/baseline.py`). Ganancia ≤ 1 = sin habilidad real.
- **Pisos**: el sistema MIDE desde M3.3 (piso real del backcast); ALERTA solo
  desde M4.5 (solo el Padre avisa). `MIN_MAGNITUD_FIRMA=4.5`.
- **Vara de asertividad**: SOLO la vista `viva_real` (fase='viva', append-only);
  verdad POR FILA — ventana propia de 72h + nodos de la propia predicción.


## Dashboard (React Vite + FastAPI 8787)

- Dev: Vite 6.4.3, proxy `/api`→8787. Build: 67 módulos, 333KB/102KB gzip → `dist/`.
- API: `infrastructure/dashboard/api.py` + 13 compat aliases sin `/api`
  (`/health`, `/kpis`, `/telemetry/*`, `/consenso/*`, `/analysis/*`, `/agents/*`,
  `/system/*`). CORS para 5173/5174/4173.
- **Diseño y contratos de dato: `infrastructure/dashboard/README.md`.** Léelo
  antes de tocar un tab: tiene el sistema de color (saturado = riesgo, y nada
  más), las superficies por pestaña y los pozos conocidos.

### Reglas de dato del tablero (v3, 2026-09-28)

Cuatro trampas verificadas contra la DB de producción. Las cuatro son la misma
familia: un default benigno haciendo pasar «no hay dato» por un número.

1. **`tbl_locf_cache.updated_at` es REAL (epoch), no TEXT.** Un `strptime`
   directo lanza `TypeError`; con un `except: pass` alrededor se tragaba **5 de
   6 fuentes** y el strip de salud mostraba dos chips como si fueran todas.
   Usar el helper `_edad_horas`, que acepta epoch y texto.
2. **Frescura ≠ validez.** Tomsk reescribe el mismo valor cada hora (25 filas,
   1 valor distinto): por antigüedad parece `LIVE`. El estado `CONGELADO`
   existe para eso. Al añadir una fuente con serie, comprobar variación, no
   sólo `MAX(timestamp)`.
3. **`viva_real` NO filtra `en_vivo`.** La vista es sólo `fase='viva'`, así que
   arrastra los 603 veredictos duplicados del 27-sep. Toda métrica de
   asertividad necesita además `COALESCE(en_vivo,1)=1`.
4. **`aciertos_total` de `/api/bots` es suma POR BOT** (138.068: cada ventana
   contada una vez por cada bot que opinó). No es comparable con los conteos de
   `viva_real` (21.400/1.651/313). Para proporciones usar `veredictos_sistema`.

5. **Un número puede cambiar de SIGNIFICADO sin cambiar de nombre.** El
   2026-10-08 `tbl_lag_anticipacion` pasó de promediar todas las firmas con lag
   a promediar solo las específicas (`SISMO_M4`: 8,8 d con n=1.402 → 8,4 d con
   n=448) y las **cuatro** superficies que lo pintan siguieron igual. Al tocar
   el significado de un agregado, busca sus consumidores: `grep` del nombre de
   la tabla en `infrastructure/dashboard/`, `deploy/` y `pipeline/`.
6. **El universo de un porcentaje es el que CONSUME el número.** El reparto del
   nulo del lag salía 13 % dividiendo entre todas las filas con un valor de lag
   y 32 % dividiendo entre las exigibles --- y el aviso solo empareja
   exigibles (`match_estado_actual` itera `consolidadas()`). Las 1.442 firmas
   con lag rancio fuera de ese universo van nombradas aparte, no en el
   denominador.

La **asertividad nunca se muestra sola**: cuenta como acierto cada silencio en
calma y excluye los falsos positivos del denominador. Va siempre junto a
`ganancia_real` (Molchan). Medido el 2026-10-08 sobre `viva_real`: **ganancia
1,17× con asertividad 35,3 % contra 97,1 % de un bot que nunca alarma** --- el
sistema alarmó en 203 de 306 ventanas, así que su asertividad quedó POR DEBAJO
del silencio. Enseñar una sin la otra miente en los dos sentidos. El tablero
debe hacer esa contradicción imposible de ignorar.

### Superficies nuevas del tablero (2026-10-08)

- **`/api/modelos` + panel «Compuerta de habilidad» en MODELOS.** Los ocho ONNX
  con su AUC y su ganancia sobre el modelo nulo POR NODO. Tres estados, y
  `medido: false` se pinta distinto de aprobado y de negado (regla de diseño 3).
  Estado real tras el primer reentrenamiento con compuerta: **aprueban ninguno,
  niega los siete**; el caso de `beta1` es el que hay que entender --- AUC
  0,800 negado porque la tasa base del nodo sola da 0,899, así que el modelo
  dice QUÉ nodo y no CUÁNDO.
- **El nulo del lag en PADRE+JUEZ y PREDICCIONES.** Cuatro KPI (anticipan /
  solo persisten / sin nulo medido / medidas sin lag) puestos ANTES de la tabla
  de horas, porque deciden si esas horas significan algo.

- Troubleshooting: `ERR_CONNECTION_REFUSED` en 5173 = host 127.0.0.1 en WSL; fix
  host 0.0.0.0. DB desconectada falso = health sin wrapper `db.connected`; fix
  `health_alias`. Launcher `UnboundLocalError FormattedMessage` = import mal
  scope; fix `_FM2`. **Radix Tabs ignora `.click()` sintético** (escucha pointer
  events): para automatizar hay que despachar `Input.dispatchMouseEvent` por
  CDP, o parecerá que todas las pestañas muestran el mismo contenido.

## Running tests

```bash
# From the workspace root (/home/user/workspaces):
python -m pytest sentinel_omega/tests/ -q

# Single test file:
python -m pytest sentinel_omega/tests/test_precursor.py -v
```

**Important**: Always run from `/home/user/workspaces/`, not from inside `sentinel_omega/`.

## Launcher / Shutdown / Reboot

```bash
# Launch orchestrator (continuous cycle mode)
python sentinel_omega/launcher.py

# Launch with dashboard + dry run (no Telegram)
python sentinel_omega/launcher.py --dashboard --dry-run

# Single cycle and exit
python sentinel_omega/launcher.py --once

# Historical backcast (one-time, 1994-2025)
python sentinel_omega/launcher.py --backcast

# Entrenamiento completo (sesgo PRE → Fase 1 + 1b → Fase 2 → lags →
# correlaciones → cimática histórica → sesgo POST)
python sentinel_omega/launcher.py --entrenar

# Disciplina de trasfondo (menores M3.3-4.49) y barrido diario
python sentinel_omega/launcher.py --disciplina
python sentinel_omega/launcher.py --barrido
# NOTA: los flags de tarea corren la tarea y SALEN (no entran al ciclo)

# Pasada del Juez (real vs predicción, ritmo auto-impuesto 4h)
python deploy/verificacion_juez.py

# Reportes periódicos con gráficas + despacho de correo
python deploy/reporte_periodico.py --comparativo   # (o --semanal / --mensual)
python deploy/enviar_correos.py

# Graceful shutdown (SIGTERM)
python sentinel_omega/shutdown.py

# Force shutdown (SIGKILL after 30s timeout)
python sentinel_omega/shutdown.py --force

# Reboot (stop + relaunch)
python sentinel_omega/reboot.py
python sentinel_omega/reboot.py --dashboard --dry-run
```

PID file: `data/sentinel_omega.pid`
Log file: `data/sentinel_omega.log`

## Rebuild Completo

Ejecuta reconstrucción de punta a punta: limpia memoria aprendida, migra DB v6, entrena Fase 1+1b+Fase 2, disciplina, VACUUM y genera reportes.

```bash
# Background run (recomendado)
nohup python deploy/rebuild_completo.py > estado/rebuild.log 2>&1 &

# Ver progreso en vivo
tail -f estado/rebuild.log
```

El script:
1. Para launcher (graceful SIGTERM)
2. Vacía: TBL_FIRMAS, pesos, correlaciones, orden, sesgo, lags, cimática (conserva backcast + Juez viva)
3. Migración DB v6 + índices + vistas
4. ANALYZE + PRAGMA optimize
5. Entrenamiento: Fase 1 (sísmico) + Fase 1b (volcánico+solar+financiero) + Fase 2 (disciplina) + lags + correlaciones
6. Disciplina de trasfondo + barrido diario (todos los cruces)
7. VACUUM + ANALYZE final
8. Reportes: generar_reporte.py + reporte_ejecutivo.py

Reporte final: `estado/REPORTE_REBUILD.md` (pesos, sesgo pre/post, firmas, rutas, tamaño DB).

## Running the dashboard

```bash
streamlit run sentinel_omega/infrastructure/dashboard/app.py
```

## Project structure

```
sentinel_omega/
├── orchestrator.py              # Master orchestrator — single runner cycle
├── config/sentinel_config.py    # Central config (secrets via os.environ)
├── core/
│   ├── shared/
│   │   ├── agent_base.py        # BaseAgent, PadreAgent, SignalType, ConsensusResult
│   │   ├── data_pipeline.py     # Pipeline base class
│   │   └── geometria_uvg.py     # Static UVG-125 Becker-Hagens matrix in RAM
│   ├── precursor/
│   │   ├── risk_calculator.py   # TITAN V32 fantasma formula
│   │   ├── scanner.py           # 15-type precursor scanner
│   │   ├── muro_cinco_eventos.py # 5-wall cross-correlation engine
│   │   ├── precursor_types.py   # Type registry + detection functions
│   │   └── assertivity.py       # V46 prediction tracking
│   ├── firmas/                  # Signature engine: per-bot pattern memory
│   │   └── signature_engine.py  # Extract/promote/match firmas (nueva→consolidada)
│   ├── juez/                    # Cold auditor, SEPARATE from Padre
│   │   └── juez.py              # ACIERTO/FALLO/FALSO_POSITIVO, recidivism severity
│   └── snt_engine/              # SNT math framework (satellization, friction, ASI, N-Body)
├── layers/
│   └── geodynamic/              # All 6 agents: alfa1, alfa2, beta1, beta2, delta,Omega, padre
├── infrastructure/
│   ├── api/                     # NOAA, USGS, Schumann, ESA, OWM, Crypto, Bolsa, Telegram
│   ├── pipeline/                # GeodynamicPipeline + runners + backcast + entrenamiento + mantenimiento + reportes
│   ├── database/                # SQLite schema, repository, 125-node seed
│   └── dashboard/               # Streamlit + Plotly dashboard (9 tabs)
├── data/                        # SQLite databases
└── tests/                       # 1.294 tests (medido 2026-10-08; 5 fallan)
```

### Pipeline scripts (operational map)

- Core runtime:
  - `launcher.py` → `_build_live_features(runner, conn)` — **el vector que el
    modelo recibe en vivo**. Regla que gobierna este archivo: cada rasgo se
    calcula de la MISMA fuente y con la MISMA ventana que lo calcula la firma
    (`signature_engine.extraer_features_ventana`), o el modelo responde a una
    magnitud que no es la que aprendió. Tres casos ya medidos y arreglados:
    los conteos sísmicos (globales y topados a 500 → del nodo, 336 h/72 h),
    `proton_max` (nunca llegaba) y el Kp. El del Kp es el ejemplo a recordar:
    `planetary_k_index_1m.json` es de **1 minuto** y trae ~6 h, así que
    `kp[-24:]` eran **24 minutos** con el nombre `kp_max_72h`, y los tres rasgos
    de Kp salían de 6 h donde el entrenamiento usa 336 h y 72 h. Ahora salen de
    `tbl_clima_espacial_raw`. Sin fuente el rasgo se OMITE: `vector_para` pone
    0,0, y ese 0,0 es «no lo sé» --- nunca se rellena.
  - `core/onnx_mixin.py` — `inferencia_de` **se niega a usar un modelo cuya
    entrada no coincida con `BOT_DIMS[bot]`** y manda la rama de reglas. Sin eso
    `pad_vector` recorta o rellena y la excepción de `onnxruntime` queda como un
    `None` indistinguible de «no hay modelo». Contrato:
    `tests/test_onnx_dims.py`.
  - `infrastructure/pipeline/data_pipeline.py` — ingesta multi-fuente + LOCF.
    Expone `proton_flux` (último) y `proton_flux_max` (máximo de ventana): el
    flujo de protones NO viaja como columna del `omni_dataframe`, así que sin
    esto la posición `proton_max` del vector de alfa1 llegaba siempre vacía.
  - `infrastructure/pipeline/layer_runners.py` — ciclo fetch→ingest→analyze→consensus.
    `_aplicar_modelos` es **el único sitio donde un modelo opina**: sustituye
    señal, confianza **y `reasoning`** (antes dejaba el texto de la regla junto
    al veredicto del modelo, y el registro se contradecía). Con `None` del
    modelo manda la regla y su texto queda intacto.
  - `infrastructure/pipeline/juez_cycle_register.py` — registro de predicciones por ciclo.
    Persiste `onnx` / `onnx_senal` / `onnx_conf` / `regla_senal` / `regla_conf`
    desde `sig.data`, así que **quién decidió —modelo o regla— es consultable**:

        WHERE json_extract(detalles_json,'$.onnx_senal')
           != json_extract(detalles_json,'$.regla_senal')

    Copia SOLO esas cinco claves, no `sig.data` entero, para que el
    `detalles_json` no crezca con lo que cada agente meta en su `data`. Las
    filas anteriores al 2026-09-27 no las tienen.
- One-time / batch:
  - `infrastructure/pipeline/backcast.py` — carga histórica one-time.
  - `infrastructure/pipeline/entrenamiento.py` + `entrenar_paralelo.py` — aprendizaje por fases.
    `BOT_FEATURES` decide qué rasgos llevan las firmas de cada bot. **Un rasgo que
    está en `features_onnx.FEATURE_ORDER[bot]` y no en `BOT_FEATURES[bot]` es una
    FUGA DE ETIQUETA POR PROCEDENCIA**, no un detalle: vale 0 en toda la mitad
    etiquetada como alarma (las firmas nacen de eventos) y un valor real en la
    mitad neutral (los ciclos vivos del Juez), así que el modelo aprende de qué
    TABLA vino la fila. Medido el 2026-09-27: 17 rasgos en 4 bots, con
    `P(alarma | rasgo=0)` entre 96,7 % y 100 % contra 1,2-1,5 % cuando el rasgo
    venía. Cerrado esa noche; lo fija `tests/test_fuga_de_procedencia.py`.
    Dos condiciones para declarar un rasgo, y las dos hacen falta:
    **(1)** que exista en `signature_engine.FEATURE_KEYS` --- si no, el filtro
    `if k in FEATURE_KEYS` lo descarta **en silencio** y el arreglo es falso; y
    **(2)** cobertura medida sobre las ventanas REALES de ese bot, no sobre el
    agregado (`padre` tiene el 73 % de las firmas y se traga cualquier promedio).
    `calcular_lags_anticipacion` aprende **cuánto avisa cada firma, en horas**:
    reprueba sus eventos con la ventana desplazada atrás y se queda con el
    desplazamiento más temprano en que aún emparejaba. Escribe
    `TBL_FIRMAS.lag_promedio_h`/`lag_n` (por firma) y `tbl_lag_anticipacion`
    (por clase). Los nueve bots y resolución de 1 h desde el 2026-09-27.
    **Tres cosas que cambiaron el 2026-10-08 y hay que saber antes de tocarlo**
    (corre en ~240 s, no en 21 s; se puede repoblar sin rebuild):
    * **El presupuesto se cuenta en FIRMAS, no en sondeos de evento.** Se
      contaba por evento y cada firma gasta hasta 3 (`LIMIT 3`), así que
      `LAG_MUESTRA_POR_CLASE = 150` eran **50 firmas** por (bot, clase) y el
      resto se saltaba con un `continue` sin log. La huella en los datos era
      del revés de un muestreo: cubos pequeños completos (`SISMO_M4_obs` 20/20)
      y grandes vacíos (`beta1 SISMO_M4` 417 exigibles → **9** con lag).
      Cobertura arreglada: **159/982 → 978/982**.
    * **La rejilla mira por debajo de 24 h.** Paraba ahí, y el emparejamiento
      no cae al acercarse al evento, SUBE: 33 % a 336 h, 58 % a 24 h, 80 % a
      1 h. Todo lo que anticipaba menos de un día salía como `None`.
    * **El lag tiene su MODELO NULO** (`lag_calma_h`/`lag_calma_n`): la misma
      firma sondeada en ventanas de calma **del mismo nodo**. Solo **315 de
      978 (32 %)** no emparejan en calma --- ahí el lag es tiempo de aviso; las
      663 restantes miden cuánto DURA el patrón. El promedio por clase cuenta
      solo las específicas. El nodo es la clave: con un nodo al azar daba 69 %,
      porque medía «otro nodo» y no «no antes del evento». `lag_calma_n` tiene
      TRES valores (`0`, `>0`, `NULL`) y un `(x or 0) > 0` mete el `NULL` en el
      saco de «específico» --- regla 7 en la línea que dice cuánto tiempo hay.
      Consulta compartida: `signature_engine.resumen_nulo_lag(conn)`, usada por
      `/api/lag` y los tres reportes para que no vuelvan a desincronizarse.
  - `infrastructure/pipeline/mantenimiento.py` — barrido diario/correlaciones/sesgo/poda.
- Reporting:
  - `infrastructure/pipeline/reporte_sentinel.py` — reportes general/padre/omega.
  - `infrastructure/pipeline/reporte_engine.py` — envoltura DRY + versionado estado/historial.
  - `infrastructure/pipeline/scheduler_reportes.py` — scheduler 2h/6h (normalmente deshabilitado para evitar duplicidad con `sentinel-omega.service`).
- Recovery / data fixes (on demand):
  - `infrastructure/pipeline/sismos_refetch_recent.py` — refetch incremental USGS.
  - `infrastructure/pipeline/topologia_cascada.py` — ETL/recalculo topológico.
  - `infrastructure/pipeline/clima_gapfill_2026.py` — fill puntual 2026 de clima espacial.
  - `infrastructure/pipeline/data_pipeline_locf_patch.py` — parche LOCF persistente.

> El repositorio raíz tiene un `AGENTS.md` (estándar neutral para cualquier
> agente de IA). Este `CLAUDE.md` es la guía específica de Claude Code y tiene
> prioridad para archivos dentro de `sentinel_omega/`.

## Security rules

- **NEVER hardcode API keys or tokens** — use `os.environ.get("KEY_NAME", "")`
- Keys will be rotated as used
- All secrets in `config/sentinel_config.py` use environment variables

## Environment variables

```
TELEGRAM_BOT_TOKEN    — Canal ÚNICO de alertas. Bot @SismoBio_Bot (verificado
                        contra getMe el 2026-09-27), COMPARTIDO con
                        ~/consensus-expert-agent: rotarlo desde aquí rompe el
                        otro proyecto. @IngZainos_bot es el del watchdog, otro.
TELEGRAM_CHAT_ID      — Chat destino
OPENWEATHERMAP_KEY    — Atmospheric data
BITSO_API_KEY         — Bitso exchange
BITSO_API_SECRET      — Bitso exchange
COINGECKO_API_KEY     — Market data
ALPHA_VANTAGE_KEY     — Stock market data
```

## Rutinas 24/7 (Roy Vigilante — GitHub Actions, hora MX = UTC-6)

- **Cada 2 h** — ciclo del Padre: status, registro de predicción viva
  (con SUS nodos) y snapshot cimático.
- **Cada 4 h** — el Juez verifica real vs predicción contra USGS (verdad
  por fila; ritmo auto-impuesto en `pipeline/verificacion.py`).
- **Cada 6 h** — reporte ejecutivo.
- **12am y 12pm MX** — comparativo contra el día anterior (con gráfica).
- **Domingo 12:15pm MX** — reporte semanal (gráficas de fantasma/alertas/breaches).
- **Fin de mes 12:30pm MX** — reporte mensual.
- **Cada corrida** — despacho del digest (`deploy/enviar_correos.py`, que pese al
  nombre despacha por **Telegram**).

## Cimática (el canal es Telegram)

- `tbl_cimatica_patrones` — snapshot del sistema por ciclo: patrón NUEVO →
  telemetría completa guardada; patrón existente → frecuencia+1 (contar,
  no anotar). Ámbito `general` o `nodo`; `event_class` cuando se conoce.
  Todo alta/incremento dispara la revisión del Padre; patrón nuevo con
  Padre activo o frecuencia consistente (≥3) con evento asociado → alerta
  por Telegram. Módulo: `core/firmas/cimatica.py`.
- **El correo ya no existe.** `infrastructure/api/correo.py` se borró el
  2026-09-15 y las variables SMTP están comentadas. `tbl_correo_salida` sigue en
  la base pero **cero código la referencia**: vestigio conservado a propósito
  (decisión del operador, 2026-09-27, «por si acaso»). No la rellenes ni la leas.
  Si lees una versión de este archivo que dice «el canal es correo» o «Telegram en
  pausa», está desactualizada --- corregido el 2026-09-27 **contra el código**,
  que es la autoridad, no contra la fecha del documento.

## Database (SQLite)

Operational tables in `data/SENTINEL_OMEGA_PRO.db`:
- `TBL_PRECURSORES_COSMICOS` — Bz, viento, protones, Kp, LOD, Schumann, fase lunar, fantasma
- `TBL_NODOS_TOPOLOGIA` — 125 nodes (50 real + 50 ghost + 25 geobattery)
- `TBL_HISTORICO_SISMICO` — USGS seismic catalog
- `TBL_DETECCIONES` — Precursor detection log
- `TBL_CICLOS` — Orchestrator cycle history
- `TBL_MURO_EVENTOS` — Muro breach history

Learning/audit tables:
- `TBL_FIRMAS` — per-bot signature memory. Estado: nueva → observada → recurrente → consolidada (by recurrence). Only consolidadas are enforceable knowledge.
- `TBL_JUEZ_AUDITORIA` — Juez discipline ledger: ACIERTO / FALLO / FALSO_POSITIVO, asymmetric severity (miss of known firma = 20 base, miss = 10, false alarm = 1), recidivism-scaled. Columna `fase` ESTRICTA; fase viva append-only.
- `viva_real` (vista) — vara canónica de asertividad: solo fase='viva'.
- `TBL_PESOS_BOTS` — pesos de credibilidad [0.3, 1.5]; Padre paga doble.
- `tbl_firmas_menores` — disciplina de trasfondo (M3.3-4.49, temporal 90d).
- `tbl_correlaciones_padre` / `tbl_correlaciones_omega` — conteo patrón→evento (+1).
- `tbl_orden_precursores` / `tbl_orden_veredictos` — ¿el orden importa o es indiferente?
- `tbl_sesgo_aprendizaje` — realidad (causal) vs fantasía (in-sample) por bot.
- `tbl_cimatica_patrones` — snapshot de telemetría por ciclo: nuevo=telemetría completa, repetido=frecuencia+1; retro-etiquetado por eventos reales, poda del ruido a 30 días.
- `tbl_correo_salida` — outbox de alertas/reportes por email (fail-soft).
- `tbl_salud_sistema` / `tbl_resumen_diario` — bitácora por corte y barrido diario.

Backcast tables (1H resolution, 1994-2025):
- `tbl_clima_espacial_raw` — NASA OMNI2 (Bz, solar wind, Kp, proton flux)
- `tbl_astronomia_cinematica` — LOD, lunar phase, lunar distance, syzygy
- `tbl_historico_sismico_raw` — USGS seismic mapped to UVG-125 nodes
- `tbl_psique_financiera` — BTC price, volatility (2014+)
- `tbl_enjambre_telemetria` — Schumann resonance per node
- `tbl_nodo_estado_dinamico` — Node charge/tension (capped at 1.0)

Triggers: `trg_nodo_saturacion` + `trg_procesar_saturacion` cap saturation at 1.0

## Muro de los 5 Eventos

Five walls of cross-correlation. Breach when >= 3 walls active:

1. **GEOFISICO**: Seismic Cluster, Volcanico, Fantasma
2. **ATMOSFERICO**: Blue Jet, Sprite Rojo, Niebla Tule
3. **OCEANICO**: Tsunami, Huracan
4. **SOLAR/GEOMAGNETICO**: Tormenta Solar, Perturbacion, Schumann, Silent Trigger, GRB
5. **FINANCIERO/SOCIAL**: Correlacion Financiera

## Orchestrator cycle order

1. GeodynamicPipeline fetches data for all agents (alfa1, beta1, beta2, delta, alfa2)
2. Precursor risk computed (TITAN V32 fantasma)
3. Hurricane data fetched (non-blocking)
4. Scanner evaluates 15 precursor types
5. Muro evaluates 5-wall correlation
6. All agents ingest + analyze → signals
7. Padre evaluates consensus (hierarchical + Schumann correlation)
8. Alerts dispatched via Telegram

## Dashboard tabs

1. Precursor Risk — Fantasma gauge + waterfall + risk distribution
2. Muro 5 Eventos — Wall status cards + radar + activation timeline
3. Scanner — Detection table + type frequency + confidence stats
4. Topologia — World map 125 nodes + saturation ranking
5. Sismico — Seismic map + depth vs magnitude + region charts
6. Schumann — Frequency trend + activity + Hz vs WPC scatter
7. Layer Signals — Agent consensus per layer
8. SNT Analysis — Satellization exponent + power law fits
9. Ciclos — Timeline + alert/breach rate gauges

## Branch

Rama viva: **`local/recuperacion-datos-2026-09`** (verificado contra `git branch --show-current`
el 2026-10-08; sin push). `claude/sentinel-omega-architecture-j3c2kn` fue la rama de
los PR de Claude y este archivo la citaba como si siguiera siendo la de trabajo.
Nunca push a `main`.

## Telegram (consenso Padre, 2026-09-03)

Canal Telegram ya no dispara cada ciclo. El Padre (`consenso_vigilante.py`):

1. **Reporte horario siempre** (`TG_DIGEST_MINUTES=60`) — Fantasma+nivel, muro n/5, telemetría, top precursores, loop, botón Mini App (`TELEGRAM_WEBAPP_URL` HTTPS público a `/mini`). No se omite la hora en calma. No es un pile de "precursores revisar".
   **La cadencia se cumple entre procesos** desde el 2026-10-07: la marca del
   último envío vive en `data/estado_digesto.json`, no en memoria. Hasta
   entonces el despacho real (`enviar_correos.py`, un `Type=oneshot` cada 15
   min) mandaba **4 digestos por hora** con el `60` declarado, porque la marca
   nacía en `0.0` en cada proceso nuevo y `force=True` saltaba el temporizador.
   Dos cosas que NO hay que hacer al tocar esto: poner la compuerta de minuto
   en `rutinas_locales.sh` (sería una segunda fuente de verdad) y dejar que un
   test escriba la marca de producción — lo impide el fixture de sesión de
   `tests/conftest.py`, y un test que lo hiciera dejaría al operador una hora
   sin reporte. Contrato: `tests/test_cadencia_digesto.py` y
   `tests/test_aislamiento_estado_vivo.py`.
2. **Page inmediato solo si no hay registro** (`is_unprecedented`): patrón cimática NUEVO, firma `TBL_FIRMAS` nueva, tipo de muro no visto, `SYSTEM_DEAD`. Firmas recurrentes y watches de precursores van al digest. Rojo/naranja rutinario NO pagina.
3. Correo (`tbl_correo_salida`) no cambia. `SENTINEL_DRY_RUN=1` no envía. Mini App exige HTTPS; este repo no crea túnel.
