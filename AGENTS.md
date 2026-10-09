# AGENTS.md — Sentinel Omega

Guía operativa para agentes de IA que trabajen en este repositorio (Claude Code,
Cursor, Copilot, Codex, etc.). Es el archivo neutral que leen todas las
herramientas; `sentinel_omega/CLAUDE.md` tiene detalle adicional y
`sentinel_omega/README.md` la descripción completa del proyecto.

> Si editas archivos dentro de `sentinel_omega/`, ese `CLAUDE.md` aplica también.

> **Orden deliberado:** arquitectura y reglas duras van PRIMERO porque el
> memory pack del Concilio trunca cada documento a 3.500 caracteres. Lo que
> quede más abajo no llega a la auditoría. Si añades secciones, no las metas
> entre el encabezado y estas dos.

## Reglas duras (no romper)

0. **REGLA CERO — nunca asumas, siempre revisa.** No des nada por hecho ni por
   conectado sin verificarlo contra el código y, cuando toque, **corriendo el
   flujo de punta a punta** (no basta con que pasen los tests unitarios).
   Antes de decir "ya está", compruébalo: ¿la tabla se pobló?, ¿el reporte lee
   la sección?, ¿el script corre sin error de verdad? Si no lo verificaste, no
   lo afirmes — di qué falta por comprobar. Esta regla manda sobre todas.
1. **Secretos solo por entorno.** Nunca hardcodear API keys/tokens. Usa
   `os.environ.get("NOMBRE", "")`. Los `.env` están en `.gitignore`; en CI van
   como GitHub Secrets. Las claves se rotan según se usan.
2. **Cero datos sintéticos.** Faltante = `NULL`. LOCF solo desde registros
   reales. El TEC derivado se etiqueta como *derived*, nunca como dato de sensor.
3. **`sentinel_omega/data/` está en `.gitignore`** — no existe en un checkout
   limpio (GitHub Actions). Crea la carpeta antes de abrir archivos ahí
   (`Path(...).parent.mkdir(parents=True, exist_ok=True)`).
4. **Reportes versionados, no sobrescritos.** `estado/REPORTE.md` es el último;
   cada corte se guarda en `estado/historial/AAAA/MM/` con hora local (UTC-6).
5. **Migración de esquema forward-only.** Columnas nuevas vía
   `EXPECTED_COLUMNS` / `_migrate_add_missing_columns`; no borrar columnas.
6. **Los tests deben pasar** antes de commitear cambios de código.
7. **Desconfía del default benigno.** `x or 0`, `.get(k, 0)`, `if vals else 0.0`,
   `float(x or 0)` — cada uno convierte "no tengo el dato" en un número
   plausible y el sistema aparenta funcionar. Falta de dato = `NULL`.
8. **Un umbral sin calibrar contra datos reales es numerología.** Mide qué % de
   los casos dispara: si es ~100% o ~0%, no discrimina nada.
9. **Verifica el índice de columna contra el dato, no contra el manual.** El
   backcast leyó `df[17]` de OMNI2 durante 280.377 filas creyendo que era el Bz
   GSM; era `sigma|B|`, una desviación típica que nunca es negativa. La huella
   estaba a la vista: 17 negativos en 280 mil filas cuando el Bz real es
   negativo la mitad del tiempo. Lo mismo con los protones, que eran el índice
   DST (47% de valores negativos en un flujo de partículas).
10. **Un descarte silencioso esconde el fallo indefinidamente.** Júpiter se
    saltaba el entrenamiento con un `continue` sin log y consumió dos rebuilds
    completos de ~16 h sin registrar una sola firma. Todo `continue` que
    descarte trabajo lleva un log que lo diga.
11. **Un número medido SOLO sobre eventos no mide nada.** Es el vicio central
    del proyecto y reaparece en cada capa: la calma es el ~97 % del tiempo, así
    que cualquier métrica que solo mire eventos se queda en el 95-100 % y no
    ordena nada. Todo número que juzgue al sistema necesita su **modelo nulo**
    al lado, y el nulo tiene que ser el bueno:
    * asertividad → contra **callarse siempre** (97,7 % contra 97,1 %: el
      sistema acierta porque casi siempre hay calma);
    * firma consolidada → contra **ventanas de calma** (`exigible`: 982 de
      23.248);
    * lag de una firma → contra **calma DEL MISMO NODO** (315 de 978; con un
      nodo al azar daba 69 % en vez de 32 %, porque medía «otro nodo», no
      «no antes del evento»);
    * AUC de un modelo → contra **la tasa base del nodo**, no contra 0,5 (el
      nodo solo predice a 0,899 y ningún rasgo global se le acerca).
12. **Un test anclado a una cadena literal del código fuente es una trampa.**
    El 2026-10-08 se pusieron rojos cinco tests DOS VECES sin que el
    comportamiento cambiara: uno cortaba una ventana fija de caracteres
    (`fuente[i-600:i+2000]`) y los otros buscaban un `SELECT` que se partió en
    varias líneas al añadirle columnas. Eso es buena parte de la sensación de
    «arreglo algo y se descompone otra cosa»: no era el código, era el
    instrumento. Ancla a la FUNCIÓN (`inspect.getsource(f)`) y a nombres de
    columna o de símbolo, nunca a la ortografía de una cadena.


## Arquitectura (para ubicarte rápido)

8 bots votantes + 1 notificador + Juez auditor (separado, nunca predice):

| Bot | Dominio | Memoria | Rol |
|-----|---------|---------|-----|
| `alfa1` | Clima espacial: Bz GSM, viento solar, Kp, protones | 1994→ | votante |
| `beta1` | Resonancia Schumann — **el latido**; todo se correlaciona contra él | 1994→ | votante |
| `beta2` | Desgasificación volcánica / atmósfera (SO₂ sobre baseline natural) | 2012→ | votante |
| `delta` | Bolsa + cripto + tendencias | 2016→ | votante |
| `omega` | Ritmo cósmico: fase lunar/sicigias + Schumann + envolvente solar + acoplamiento Schumann↔mercado | 1994→ | votante |
| `loki` | Fractal-bayesiano: Bz, viento, Schumann, VIX, LOD | 2014→ | votante |
| `jupiter` | Atención colectiva: Kp + fulguración GOES + interés de búsqueda + Schumann | 2026-07→ | votante |
| `padre` | Consenso jerárquico cruzado entre familias (aplica pesos) | — | árbitro |
| `alfa2` | Satélites ESA Sentinel (cobertura, anomalías térmicas, pasadas claras) | — | **notificador** |

**`alfa2` avisa, no vota.** Sus sensores van casi en tiempo real, así que ve los
movimientos antes que nadie: una anomalía suya es motivo para ir a mirar, no un
voto del consenso. No forma firmas porque sus tres features nunca alcanzan
`MIN_DIMENSIONES_COMPARABLES` (4) — por debajo de ese suelo `similitud()`
devuelve 0.0 y una firma no empareja ni consigo misma. Pasa a votante cuando la
capa satelital aporte una cuarta señal. Ver `BOTS_ESPERANDO_SENALES` en
`infrastructure/pipeline/entrenamiento.py`.

**`jupiter` solo tiene memoria reciente**: su histórico de rayos X y tendencias
nunca se persistió (se bajaba cada ciclo y se descartaba). Desde 2026-09-24 se
acumula en `tbl_xray_vivo` / `tbl_trends_vivo`, así que su ventana crece con el
tiempo operativo.

- **Familias:** `space_weather` (alfa1/alfa2), `schumann_cymatics` (beta1/beta2),
  `financial_sentiment` (delta). Consenso: ≥2 familias + ≥2 alertas +
  correlación Schumann > 0.3.
- **Firmas:** memoria de patrones por bot de la ventana de 14 días previa a cada
  evento. Estados `nueva → observada → recurrente → consolidada`.
  **`consolidada` NO es lo mismo que `exigible`** (separado el 2026-10-07): la
  promoción va solo por RECURRENCIA (`ESTADO_POR_RECURRENCIA`), así que un
  patrón que reaparece en calma se consolidaba igual que uno que precede
  eventos. `exigible` es el hecho MEDIDO de que la firma empareja eventos más
  que calma (`discriminacion > 0,05`). Medido: de **23.248 consolidadas solo
  982 son exigibles (4,2 %)**. `consolidadas()` devuelve las exigibles.
- **El lag de una firma anticipa o solo persiste**, y son cosas distintas
  (medido el 2026-10-08). `_lag_detectado` barre hacia atrás desde el evento y
  toma el offset más lejano donde el patrón aún se reconoce; sondeado también
  en ventanas de CALMA del mismo nodo, **315 de 978 firmas con lag (32 %) no
  emparejan en calma** --- ahí el lag es tiempo de aviso --- y 663 sí, con vida
  igual o mayor: su número mide cuánto DURA el patrón. El promedio por clase
  (`tbl_lag_anticipacion`) cuenta **solo las específicas**, y `lag_calma_n`
  tiene tres valores (`0` específica, `>0` persiste, `NULL` sin medir) que hay
  que tratar como tres.
- **Entrenamiento en 3 fases:** Fase 1 reconocimiento sísmico (sin castigo) → Fase 1b reconocimiento no sísmico (erupciones VEI≥3 + tormentas solares Kp≥6) → Fase 2
  disciplina (el Padre castiga; el Juez audita con severidad asimétrica —
  omitir un evento pesa 10× más que una falsa alarma). Tras las fases calcula la
  **matriz de correlaciones** feature × event_class, y el **sesgo de
  aprendizaje** se mide antes (línea base, sin castigo) y después
  (disciplinario) para reportar la mejora causal por bot.
- **Omega** no es un agente en vivo (no está en `layers/`): es un bot de
  memoria/correlación como contrapeso del Padre. Sus campos están mapeados de
  la telemetría existente en `BOT_FEATURES["omega"]` (sin fetchers propios);
  entrena en las mismas fases que los demás, y sus correlaciones viven en
  `tbl_correlaciones_omega` (umbral n≥30, patrón con Schumann y fase lunar),
  independientes de las del Padre. Reporte propio: `reporte_omega()`.
- **Pérdida asimétrica:** el sistema prefiere sobre-alertar a sub-alertar.

## Qué es este repo

**Sentinel Omega** — plataforma de detección de **precursores de eventos
naturales** (sismos, actividad volcánica, tormentas solares, tsunamis).
Autor: Elán Zainos Corona (Fractal Core Research). Sucesor de la familia TITAN
V32/V46/V53.

Alcance: **únicamente precursores de eventos naturales.** No mezclar aquí:
- **Genómica** → va en el repo *SNT Genómica*.
- **Sentinel Titan** (lotería / "Elite") → va en otra rama, no en `main`.
- De lo financiero, este repo **sí** usa bolsa, cripto y tendencias (el bot
  `delta`, "el humor de la tierra") como una señal precursora más.

SNT (Shadow Node Theory) se usa **solo como framework matemático**
(ley de potencia `R(t) = a·t^b`), no como propósito del sistema.

## Estructura de alto nivel

```
sentinel_omega/     El sistema (8 bots + notificador + Padre + Juez, pipeline, DB, dashboard)
deploy/             Operación: generar_reporte.py, systemd/Windows, atajo iOS, .env.example
estado/             Reportes publicados: REPORTE.md (último) + historial/AAAA/MM/ (versionado)
.github/workflows/  roy-vigilante.yml — corre un ciclo cada 2h en GitHub Actions (serverless)
```

## Comandos

```bash
# Tests — SIEMPRE desde la raíz del workspace, nunca desde dentro de sentinel_omega/
.venv/bin/python -m pytest sentinel_omega/tests/ -q   # 1.309 tests; 2 fallan (2026-10-08)
# El intérprete importa: `sentinel_omega/.venv` es un resto huérfano sin eodag
# ni pytrends y da 4 fallos que son suyos. El servicio usa `workspaces/.venv`.

# Un solo archivo
python -m pytest sentinel_omega/tests/test_firmas.py -v

# Sistema en vivo
python sentinel_omega/launcher.py                  # ciclo continuo (default 300s)
python sentinel_omega/launcher.py --once           # un ciclo y salir
python sentinel_omega/launcher.py --backcast        # carga histórica 1994-2025 (one-time)
python sentinel_omega/launcher.py --entrenar        # entrenamiento completo (sesgo PRE → 3 fases → cimática → sesgo POST)
python sentinel_omega/launcher.py --disciplina      # castigo desde abajo (menores M3.3-4.49)
python sentinel_omega/launcher.py --barrido         # compactación diaria + correlaciones + poda cimática
# Los flags de tarea corren la tarea y SALEN (no entran al ciclo continuo)
python sentinel_omega/shutdown.py                  # parar (SIGTERM, 30s → SIGKILL)
python sentinel_omega/reboot.py                    # stop + relaunch

# Juez: real vs predicción (ritmo auto-impuesto de 4h)
python deploy/verificacion_juez.py

# Reporte (los "ojos" del sistema; lo corre el vigilante tras cada ciclo)
python deploy/generar_reporte.py
python deploy/reporte_ejecutivo.py                 # plantilla ejecutiva (cada 6h)
python deploy/reporte_periodico.py --comparativo   # hoy vs ayer (o --semanal / --mensual)
python deploy/enviar_correos.py                    # despacha por TELEGRAM pese al nombre (el correo se retiró el 2026-09-15)

# Dashboard React (el que se trabaja) — la API primero, el front después
python -m uvicorn sentinel_omega.infrastructure.dashboard.api:app --host 127.0.0.1 --port 8787
cd sentinel_omega/infrastructure/dashboard/web && npm run dev   # :5173

# Dashboard Streamlit (legacy, 11 pestañas, no se amplía)
streamlit run sentinel_omega/infrastructure/dashboard/app.py --server.port 8510
```

**Antes de tocar el dashboard React lee
`sentinel_omega/infrastructure/dashboard/README.md`.** Tiene el sistema de
diseño (color saturado = riesgo y nada más), la superficie asignada a cada
pestaña y los pozos de dato verificados contra producción: que
`tbl_locf_cache.updated_at` es epoch REAL —un `strptime` directo dentro de un
`except: pass` se tragaba 5 de 6 fuentes sin que se notara—, que `viva_real` NO
filtra `en_vivo` (arrastra 603 veredictos duplicados sin
`COALESCE(en_vivo,1)=1`), y que `aciertos_total` es suma por bot, no comparable
con los conteos del sistema.

## Git y PRs

- Rama de desarrollo: **`local/recuperacion-datos-2026-09`** (verificado el 2026-10-08 contra
  `git branch --show-current`; sin push). La vieja
  `claude/sentinel-omega-architecture-j3c2kn` era la de los PR y figuraba aquí como
  si fuera la viva.
- No pushear a otra rama sin permiso explícito.
- Los PRs se abren como **draft**. Si un PR ya fue mergeado, no apiles trabajo
  nuevo encima: reinicia la rama desde `origin/main` y abre un PR nuevo.
- El cron de `roy-vigilante.yml` solo dispara en `main` → hay que mergear para
  activarlo.

## Fuentes de datos (todas públicas salvo donde se indica)

NOAA SWPC · USGS FDSN · NASA OMNI2 (backcast) · NASA MSVOLSO2L4 (SO₂ volcánico) ·
Tomsk (Schumann) · IERS (LOD) · Yahoo Finance (BTC, keyless) ·
OpenWeatherMap (`OPENWEATHERMAP_KEY`) · NASA NEO (`NASA_API_KEY`, fallback DEMO_KEY) ·
ESA Copernicus vía eodag.

## Alertas y reportes (canal: TELEGRAM — el correo se eliminó)

**El correo ya no existe.** `infrastructure/api/correo.py` se borró el
2026-09-15, `deploy/enviar_correos.py` despacha por Telegram, y las variables
SMTP están comentadas. `tbl_correo_salida` sigue en la base pero **cero código la
referencia**: vestigio, no canal. Se conserva a propósito (decisión del operador,
2026-09-27, «por si acaso»); está vacía y no se consulta. No la rellenes ni la
leas — si vuelve el correo, se decide entonces. Su DDL está en la bitácora. Si lees una versión de este archivo que dice
«canal: correo, Telegram en pausa», está desactualizada — corregido el 2026-09-27
contra el código, no contra la fecha del documento.

**El bot NO es de este repo.** Es **`@SismoBio_Bot`** (verificado el 2026-09-27
contra `getMe`, id 8460857489), lo maneja **Consensus Expert Agent**
(`~/consensus-expert-agent`) y es compartido. Ojo: `@IngZainos_bot` es el bot
**propio del watchdog** (`/watchdog`), canal distinto a propósito --- no lo
confundas, como se confundió en este archivo el 2026-09-27. Consecuencias que importan:

- Sentinel es **solo saliente** — `sendMessage`/`sendPhoto`/`sendDocument`, sin
  `getUpdates` ni webhook, así que no compite con el poller de allá.
- Los comandos entrantes (`/start`, `/task`, `/audit`) viven **allá**, no aquí.
- `TELEGRAM_BOT_TOKEN` es **compartido**: rotarlo desde este repo rompe el otro.
  Coordinar antes. (Es el mismo token cuyos valores viejos se purgaron del
  historial de git el 2026-09-27.)

Rutinas del vigilante (hora MX=UTC-6): ciclo del Padre cada 2 h · Juez verifica
real vs predicción cada 4 h · reporte ejecutivo cada 6 h · comparativo diario
12am/12pm · semanal domingo 12:15pm · mensual fin de mes 12:30pm. La cimática
(`tbl_cimatica_patrones`) toma un snapshot de telemetría por ciclo: patrón nuevo
guarda todo, patrón repetido suma +1 a la frecuencia; cualquier alta/incremento
dispara la revisión del Padre y, si amerita, aviso por Telegram.

## Telegram — consenso Padre (2026-09-03)

- **Digest horario SIEMPRE** (`TG_DIGEST_MINUTES=60`): concentrado Fantasma,
  muro, telemetría, precursores, loop, **la vara del Juez** y **la habilidad
  medida de los ONNX**. No saltar la hora.
- **DOS rutas despachan el digesto, y comparten la marca.** Medido sobre los 18
  envíos reales del 2026-10-08: **11 del launcher** (`sentinel-omega.service`,
  cada ciclo) y **7 del oneshot de rutinas** (`deploy/enviar_correos.py`, cada
  15 min). Gana quien llegue primero a la hora, y por eso la marca compartida
  en `data/estado_digesto.json` es lo que hace cumplir la cadencia: con la
  marca en memoria, el oneshot la estrenaba en `0.0` en cada proceso y salían
  **4 digestos por hora** con el `60` declarado (2026-10-07). Al tocar esto,
  **no supongas cuál de las dos envía**: `journalctl --user -u
  sentinel-omega.service -u sentinel-omega-rutinas.service | grep "digest
  horario (sent"`. Verificado el 2026-10-08 sobreviviendo a un apagado COMPLETO
  del sistema.
- **Lo que el digesto dice de los modelos es su habilidad MEDIDA**, no que el
  archivo exista (2026-10-08). Antes ponía `✅ ALFA1 (791KB)` por
  `os.path.exists` y los ocho `.onnx` en disco no habían pasado nunca por la
  compuerta. Tres estados: aprobado con su AUC, negado con el motivo, y **sin
  medir** --- que no es ninguno de los dos. Sale de `models/models_meta.json`.
- **La vara del Juez va en el digesto** (`get_vara_juez`): asertividad JUNTO a
  su ganancia, nunca una sola. Medido: ganancia 1,17× con asertividad 35,3 %
  contra **97,1 % de un bot que nunca alarma**.
- **Inmediato SOLO sin precedentes** (`is_unprecedented`): cimática NUEVO, firma nueva, muro kind nuevo, SYSTEM_DEAD. Precursores/firmas recurrentes → digest.
- Mini App: `TELEGRAM_WEBAPP_URL` = HTTPS público de `/mini` en el FastAPI del dashboard. No inventar túneles.
- Código: `infrastructure/messaging/consenso_vigilante.py`. `SENTINEL_DRY_RUN=1` no llama a la API de Telegram. No imprimir tokens.
