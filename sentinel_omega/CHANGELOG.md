## 2026-10-21 (madrugada) — Auditoría de despliegue + fix: convergencia del muro de lags

Detalle y verificación en `estado/BITACORA_2026-10-21.md`.

### Fixed — `muro_lags` invisible en plantillas y MiniApp (Real 10)
`plantillas_concilio.py` seleccionaba `dias_restantes` de
`tbl_muro_lags_estado` — columna que **no existe**: es valor calculado en
lectura (contrato de `/api/muro_lags`). El `sqlite3.OperationalError` caía
en un `except` silencioso y la línea «🕐 Convergencia: faltan ~N–M d» jamás
salió, ni en P2H ni en `miniapp_estado.json`, pese a fila activa en la
tabla. Fix: cálculo en lectura espejo del API. Verificado punta a punta
contra DB real y en producción tras reinicio: `[4, 6]` días
(2026-10-25 → 2026-10-27, SISMO_M4/M5).

### Fixed — `test_fetch_goes_xray` (Real 12: el instrumento, no el código)
El mock seteaba `resp.json()` pero el fetch lee `resp.text` (parse
defensivo del 10-20). `_mock_response` ahora expone `resp.text` como JSON
serializado, como una respuesta real. Suite: **1.339 pasan, 0 fallos**
(fuera de los 2 rojos deliberados de alfa1, que no corrían en la pasada).

### Verified — despliegue del 10-20 completo y vivo
Timestamps arranque-vs-edición de los 5 servicios tocados: cero archivos
editados después del arranque. Cascada de plantillas disparada de forma
natural: **primera P24H** a medianoche junto con P6H/P12H. Logs sin
errores («Ciclo persistido OK» ×226).

---

## 2026-10-20 (noche) — Reestructuración del dashboard: señales con countdown, cimática como figura

### Added — `/api/estado-vivo` + panel «Señales vivas · lag restándose»
El leading que faltaba en el Monitor: cada firma emparejada como tarjeta
con **sitio completo** (nombre → nodo → coords, formato `core/nodos`),
evento, parecido/repeticiones y el **countdown restándose en vivo**
(cliente ticka cada segundo desde `lag_restante_h` + ts del snapshot;
ancla en la primera detección continua — no re-proyecta). Colores por
urgencia: >72 h calma · 24–72 atención · <24 aviso · vencida neutra —
siempre dentro de la regla «saturado = riesgo». «Sin lag medido» se ve
distinto (ausente ≠ cero, al pixel). El endpoint sirve el JSON del
launcher (≤5 min, `edad_s` explícito) — una llamada que consolida lo que
antes pedían varios polls.

### Added — `CimaticaFigura.tsx`: la clave cimática hecha FIGURA
Hasta hoy la cimática se mostraba como hash crudo (un muro de texto
ilegible). Ahora la clave se dibuja como **figura geométrica
determinista** (FNV-1a → PRNG → 16 nodos perturbados sobre anillos,
espejo vertical como las placas de Chladni, curvas suavizadas): la misma
clave SIEMPRE dibuja la misma figura — reconocible de reojo, que es el
punto de la cimática (libro/skill de ~/conocimiento). Color de la rampa
neutra: la figura es dato, no estado de riesgo.

### Changed — Cimática ahora (PrincipalTab)
La figura al lado de la clave (rotulada «la semilla de la figura») +
patrones y biblioteca en la misma superficie.

### Verificación
Build verde (76 módulos); navegador real (Playwright): 5 señales con
sitio/countdown renderizadas, figura SVG presente, endpoint con 98 s de
frescura y 5 señales. Suite: baseline.

---

## 2026-10-20 (tarde) — Interfaces del operador: countdowns, plantillas cascada y MiniApp

Detalle y verificación en `estado/BITACORA_2026-10-20.md` §9.

### Added — `core/nodos.py`: el formato canónico de sitio y el countdown
`sitio_nodo()`: «Indonesia Java (Nodo 25 · -7.5, 110.0)» — nombre primero,
una sola fuente de verdad (alertas, digesto, plantillas, MiniApp).
`lag_restante_h()`: el countdown POR SEÑAL con ancla derivada del
historial continuo del padre (sin estado en memoria; sobrevive reinicios;
no re-proyecta desde ahora). Cableado en `format_precursor_alert` y en
las líneas de precursores del digesto (lag RESTANDO en render).

### Added — Plantillas cascada para el Concilio (messaging/plantillas_concilio.py)
P2H cada 3 h (estado), P6H cada 6 h (comportamiento: junta las P2H previas,
tendencias, señales que entran/salen/persisten), P12H (comparativo medio
día), P24H (medianoche). Cadena por JSON en `estado/plantillas/`, MD
legible, marca de cadencia `data/estado_plantillas.json` (patrón del
digesto), dispatch por la cola de Telegram. **Disparo natural verificado
a las 12:00:00 local: ['p2h','p6h','p12h'] con formato completo.**

### Added — `estado/miniapp_estado.json`: el snapshot que sirve la MiniApp
El launcher lo refresca cada ciclo (≤5 min) con TODO lo que la MiniApp
muestra — estado, señales con countdown, auditoría con ganancia
(calculada con el código de ESTE repo; el Concilio solo lo sirve). Sin
duplicación de algoritmos entre repos: el JSON es el contrato.

### Changed — MiniApp rediseñada (sirve el Concilio, calcula Sentinel)
Hero leading, señales con countdown TICKANDO cada segundo, sparkline con
umbrales 12/29, cimática, sismos, auditoría con la trinidad honesta
(asertividad + muda + ganancia JUNTAS), chat Rápida/Tarea con el
chatbot del sistema (ruta por intención + árbitro 4b — saga completa en
el CHANGELOG del Concilio v3.0.7). Verificada en navegador real.

### Fixed — hook de plantillas: `name 'conn' is not defined`
Reventó EN CADA CICLO desde las 10:12 (scope: `conn` vive en
`_auditar_ciclo`; en el loop principal es `repo._conn`) — la cascada y el
refresh de la MiniApp quedaban muertos con el warning no-bloqueante
tragándolo. Otra vez la regla 10: el silencio "no bloqueante" escondió
un hook entero muerto.

### OCR completado
Estadística Práctica (726 KB), Battaner (336 KB) y Rosen (879 págs,
2.9 MB) ya son grep-able — `~/conocimiento/INDICE.md` sin ⚠ pendientes.

---

## 2026-10-20 — «Aplicaremos todo»: el plan de la biblioteca ejecutado

Detalle y verificación en `estado/BITACORA_2026-10-20.md`.

### Added — `infrastructure/database/ruta_db.py`: el puerto de la DB
Una sola fuente de verdad para la ruta canónica (`SENTINEL_DB` → prod →
árbol, nunca workspaces-dev implícito) + `abrir_readonly()`. Migrados
dashboard api, `consenso_vigilante` y `orchestrator`, que cargaban tres
defaults hardcodeados gemelos — la familia del bug del MockConfig.

### Added — `core/plausibilidad.py`: invariante de rango físico en ingesta
Rangos de IMPOSIBILIDAD (no de rareza): OWM presión/temp/humedad/gases
(incl. AQI 1–5 — el 0 imposible ya no pasa), GOES flux, Kp 0–9, Bz ±200,
y como invariante en `compute_fantasma` (Bz=999 de API corrupta ya no
hace fantasma=998001). 8 tests; wiring OWM+GOES+fantasma. Empezó en
infrastructure y se MUDÓ a core (core no importa de infra — skill
Cosmic Python). **Regla 9 en vivo contra el propio validador**: su piso
de flux 1e-9 anuló 4+ lecturas REALES de sol quieto (9,99e-10) en el
primer ciclo → piso corregido a 1e-11, bloques re-llenados solos por el
fetch 7d + INSERT OR IGNORE (791 filas, 0 NULL, 0 falsos positivos).

### Changed — `layer_runners`: frontera única de persistencia (UoW adaptado)
`_persistir_operativa()`: UNA línea estructurada por ciclo (ok/parcial/
total-fail), fail-soft conservado pero silencio imposible; fetch GOES
adelantado al arranque para que alfa2 no dependa de la persistencia.
Motivación: el NameError del 10-19 vivió 2 días en uno de los cuatro
silencios que esto reemplaza. Verificado en producción: `Ciclo persistido
OK: {'sismos','clima','goes_trends'}`.

### Added — `deploy/medir_similitud_geometria.py`: geometría del umbral 0,80
Con la métrica DEL engine sobre 131.468 pares intra-nodo reales: **el
0,80 cae en el P97** (solo 3,1 % de las firmas de un mismo nodo se
reconocen entre sí), dimensionalidad efectiva ~26 de 55, y el espacio
**NO es euclidiano** (Schoenberg 18,7 % energía negativa). Mapa MDS:
`estado/graficas/firma_espacio.png`. El umbral NO se tocó — la mesa para
calibrarlo por nodo queda servida con números.

### Added — `docs/JUEZ_INCENTIVOS_NASH.md`: diagnosis de incentivos
Con pérdida 10:1, alertar es dominante para p>1/11: la ganancia 0,88× es
el equilibrio que las reglas crean. Cuatro opciones de mechanism design
(A–D), recomendación D→B. Ninguna aplicada — requiere GO.

### Changed — Frontend (UX Reader + KPI Guide, quirúrgico)
Encuadre leading/lagging explícito en PrincipalTab (la ganancia habla
del PASADO, la franja del AHORA) y columna Origen en lenguaje de usuario
(Ciclo/Muro/Fantasma/Fulguración). Build verde; sistema de diseño intacto.

### Pendiente operador
OCR de los 2 escaneados: `sudo apt install -y tesseract-ocr
tesseract-ocr-spa` + `pip install pytesseract pdf2image`.

---

## 2026-10-19 (noche) — Defaults benignos fuera de la cadena OWM + forecast integrado

### Fixed — regla 7/8 en CADA eslabón atmosférico (8 archivos)
`fetch_weather` publicaba 1013 hPa/20 °C/cielo despejado si OWM omitía un
campo; `fetch_air_quality` reportaba gases ausentes como 0.0 «medidos» y
un AQI 0 (imposible: la escala OWM es 1–5); el gradiente con <2 lecturas
devolvía media 1013.0; `layer_runners` alimentaba el **término de presión
del Fantasma** con ese default y `launcher` lo persistía como medido; el
scanner evaluaba niebla/blue-jet/sprite con humedad 50 %/cielo despejado
inventados; beta2 sumaba estrés con «presiones» que no existían. Fix:
campo ausente = `None` en toda la cadena, modificadores saltados con None,
persistencia NULL, reporte «sin dato». El valor del fantasma NO cambia
(1013/0 no activaban los modificadores; None los salta) — lo que cambia
es que ya no se persiste calma falsa.

### Added — lo que OWM ya entregaba y se tiraba
- Campos nuevos por lectura (cero llamadas extra): `wind_gust_ms`,
  `rain_1h`/`snow_1h`, `grnd_level_hpa` (presión a nivel de estación),
  `data_ts`.
- `fetch_forecast()`: endpoint `/data/2.5/forecast` (5 días/3 h, incluido
  en la misma key, nunca usado) → resumen por nodo (presión mín 24/48 h,
  caída pronosticada, lluvia, ráfaga máx), TTL 3 h, integrado al ingest
  de beta2 (`Forecast present: True`). **Sin regla de alerta aún**
  (regla 9: primero observar la distribución, luego calibrar). One Call
  3.0 (alertas de agencias, candidato a reemplazar el NHC 404) requiere
  suscripción del operador — anotado.

### Verificación
Suite: solo los 2 rojos deliberados del baseline (`test_fantasma` 13/13,
`test_precursor` 164/164). Smoke HTTP real: forecast tlaxcala (mín
1016 hPa/48 h, 40 pasos), `gust`/`grnd_level` vivos, `rain_1h=None`
honesto; gradiente sin presiones → `mean_pressure: None` + warning.

---

## 2026-10-19 (tarde) — Concilio a user-units y atención solar con fallback libre

### Changed — `consensus-telegram`/`consensus-web`: user units únicas, system units viejas enmascaradas
Existían como **system units** (`/etc/systemd/system/`, enabled,
`Restart=always`) — el `sudo systemctl` del AGENTS.md era de su época.
Creadas las equivalentes **user units** (`~/.config/systemd/user/`,
Linger=yes; sin EnvironmentFile, se auto-cargan el .env con
`load_dotenv`). Tras el reinicio de WSL de esa tarde las system units
despertaron y duplicaron todo: dos pollers de `getUpdates` (**409
Conflict** medidos, 60 en 45 min) y la web del sistema tomando el
puerto 8002 (la user unit en crash-loop EADDRINUSE). El operador aplicó
stop + mask manual (mv del archivo + `ln -s /dev/null` — `systemctl
mask` solo se niega si el archivo de unit existe y no se pasó `--force`).
Verificado: dos procesos vivos == MainPIDs de las user units, 0
conflictos post-mask, cola drenada por el bot único. Home `AGENTS.md`
corregido a `systemctl --user` con la historia.

### Added — `atencion_wiki.py`: atención solar vía Wikipedia pageviews
`fetch_solar_storm_trends` (pytrends) devuelve HTTP 400 de forma
**intermitente** — medido: días seguidos en 400 y recuperación espontánea
(este ciclo trajo 93 puntos). Nueva
`infrastructure/api/atencion_wiki.py`: pageviews diarios (agent=user) de
Solar_flare/Geomagnetic_storm/Solar_wind en en.wikipedia, MISMO contrato
[date, solar_interest] (max entre artículos), keyless. Cableada como
**fallback** en `fetch_jupiter_data`: Trends primero, Wikipedia cuando
Google throttlea. **X API descartada**: su capa gratuita solo permite
publicar; el endpoint de búsqueda/conteo —lo único que mide atención—
cuesta ~$200/mes.

### Changed — `tbl_trends_vivo.fuente`: la escala ya no se mezcla en silencio
Trends es 0–100; Wikipedia pageviews son cientos–miles. Añadida columna
`fuente` (migración forward-only: ALTER TABLE + UPDATE de las 119 filas
históricas a `'trends'`), escrita por `_persist_xray_trends` desde
`trends_fuente` del pipeline. El consumidor del dashboard
(`/api/telemetry` trends) ahora muestra las últimas 5 filas con su fuente
y la nota explica que las escalas NO son comparables. Impacto del cambio
de escala en `trends_mean` de delta documentado en la bitácora: ONNX sin
efecto (compuerta los deshabilitó) y la dimensión ya era degenerada en
firmas (la tabla llevaba días congelada con varianza cero).

---

## 2026-10-19 — Revisión punta a punta: tres bugs bajo el "todo funciona"

Pedido del operador: revisar el pipeline de punta a punta, empezando por
logs. Los logs cantaron primero. Detalle completo en
`estado/BITACORA_2026-10-19.md`.

### Fixed — `layer_runners._persist_xray_trends`: NameError congelaba GOES 47 h
La guarda interna decía `jupiter_data` tras renombrar el parámetro a
`atencion_data`. El `except` "non-blocking" del llamador lo tragó dos días:
`tbl_xray_vivo` congelada en 10-18 00:00 (alfa2 en memoria sí veía el xray
fresco; lo muerto era la persistencia). El fetch de 7 días de NOAA rellenó
el gap solo: 730 → 777 filas en el primer ciclo post-fix.

### Fixed — `orchestrator._get_xray_max` leía config inexistente
`SentinelOmegaConfig` no expone `database_path`/`db_path`; el getattr
silencioso devolvía None y **FULGURACION_M jamás despachó** — con una
fulguración M-class real activa (1,68e-05 W/m²) sin pagina. Refactor a
`_leer_go_alfa2()`: una conexión read-only para (xray_max, goes_flare,
alfa2_thermal), ruta por el patrón de `ConsensoVigilante`
(`SENTINEL_DB` + default canónico). Los bloques goes_flare/alfa2_thermal
de `_analyze_results` tenían el mismo vicio (`load_config().database_path`
tragado por except) — reescritos contra el lector único. Verificado contra
la config REAL (la primera verificación fue contra MockConfig — regla 0
violada).

### Fixed — etiqueta del digesto mentía sobre la ventana
La línea de fulguración decía "· 6 h" cuando `_flare_reciente` lee 24 h.
Corregida. El digesto ahora renderiza: `fulguración GOES clase M (máx
1.7e-05 W/m² · 24 h)`.

### Cadena verificada contra un flare M-class REAL
fetch NOAA → persist → alfa2 watch (Juez) → `_leer_go_alfa2` →
`format_fulguracion_alert` → AlertService → vigilante immediate (no buffer)
→ cola compartida (stats `last_alert` 17:58:55) → bot del Concilio →
Telegram. Anti-spam: cooldown 30 min por tipo (`IMMEDIATE_COOLDOWN_S`).

### Nota operativa
`consensus-telegram`/`consensus-web` corren como procesos directos (PID
444/445), no como systemd units — `systemctl status consensus-telegram`
da un falso "caído". Google Trends responde 400 (externo, preexistente):
`tbl_trends_vivo` al día 17-oct por eso, y `trends_mean` de delta lee la
última lectura real.

---

## 2026-10-18 — Enriquecimiento total: reportes, alertas, Telegram y dashboard

**Objetivo**: Retirar jupiter (2026-10-18), enriquecer con GOES X-ray (Alfa-2 solar) y Alfa-2 térmico (Sentinel-1/2) en reportes, alertas, Telegram y dashboard.

### Changed — Retiro de jupiter (medido, no especulado)
- `deploy/generar_reporte.py`: `BOTS_RETIRADOS = {"jupiter"}` + filtro en todas las secciones
- `deploy/aciertos_reporte.py`: `AND bot_name NOT IN ('jupiter')` en SQL total y por-bot
- `deploy/reporte_ejecutivo.py`: `BOTS_ORDEN` actualizado (8 bots vivos, sin jupiter)
- `tests/test_reporte_agentes.py`: test actualizado a `test_live_only_agents_appear_without_firmas`
- `sentinel_omega/infrastructure/dashboard/api.py`: 4 referencias en comentarios/notas → "jupiter retirado"
- **Resultado**: `grep -c jupiter estado/REPORTE.md` → 0; narrativa "8 bots especializados" presente

### Added — GOES X-ray (Alfa-2 solar) en reportes
- `deploy/generar_reporte.py`: sección "🌤️ GOES X-ray — Fulguración solar" (clase C/M/X, flux máx, ventana 24h)
- `deploy/reporte_ejecutivo.py`: misma sección + contexto NOAA
- `deploy/reporte_periodico.py`: `--comparativo`, `--semanal`, `--mensual` incluyen GOES + Alfa-2

### Added — Alfa-2 térmico (Sentinel-1/2) en reportes
- `deploy/generar_reporte.py`: tabla de zonas con anomalías térmicas (precedente de zona)
- `deploy/reporte_ejecutivo.py`: misma tabla con cobertura y pases limpios/totales
- `deploy/reporte_periodico.py`: todas las variantes incluyen Alfa-2 térmico

### Changed — Formato nodos en todos los reportes y dashboard
- **Antes**: `Tonga-Kermadec (Nodo 26)` con coords `(lat, lon)`
- **Ahora**: `Tonga-Kermadec (Nodo 26)` — nombre principal + número de nodo como referencia
- Archivos: `generar_reporte.py`, `reporte_ejecutivo.py`, `reporte_periodico.py`, `api.py` (cimática JOIN), `SenalesTab.tsx`

### Added — Alertas & Telegram enriquecidos
- `telegram.py`: `format_fulguracion_alert()` → impacto (ALTO/MODERADO/BAJO) + detalles (flux_mean, duración, región NOAA)
- `format_centinela_threat()`: params `goes_flare`, `alfa2_thermal` → cada alerta incluye contexto solar/térmico
- `dispatch_cycle_alerts()`: params `goes_flare`, `alfa2_thermal`
- `orchestrator.py`: `_get_xray_max()` + lee GOES/Alfa-2 en ciclo → pasa a dispatcher
- `consenso_vigilante.py`: `_flare_reciente()` + `FULGURACION_X/M` en `_ALWAYS_IMMEDIATE_TYPES` → page inmediato

### Added — Dashboard API endpoints enriquecidos
- `/api/telemetry`: GOES `flux_class` + Copernicus `zones_with_anomalies[]` (con zona, anomalías, cobertura, pases)
- `/api/alertas`: `flare_alerts[]` (M/X class 24h)
- `/api/health/apis`: **goes** (flare_class_24h, flux_max_24h) + **copernicus** (zones_with_anomalies, max_anomalies, status WATCH/ALERT/NEUTRAL)
- `/api/cimatica`: JOIN `TBL_NODOS_TOPOLOGIA` → `nodo_nombre` en items
- `/api/telemetry/history`: NUEVO endpoint serie 48h con GOES flux + Alfa-2 zones

### Added — Dashboard Front enriquecido
- **PrincipalTab**: GOES flare en telemetría + columna "Clase" en Alertas (emoji + ALERT/WATCH/INFO)
- **TelemetriaTab**: 6 KPIs (incluye GOES + Alfa-2) + gráficas históricas GOES/Alfa-2 + tabla con flux_class
- **SeñalesTab**: `nodo_nombre` en patrones cimáticos (ej: `Tonga-Kermadec (Nodo 26)`)
- **Build**: ✅ TypeScript + Vite (75 módulos, 369KB)

### Verificación
| Check | Resultado |
|-------|-----------|
| `grep -c jupiter estado/REPORTE.md` | **0** (limpio) |
| Tests | **1,307 pass / 2 known-fail** (mismo baseline) |
| 5 Reportes | ✅ Generan + Telegram |
| Dashboard Build | ✅ TypeScript + Vite |
| Servicios | ✅ 5/5 `active running` |
| API Health | GOES STALE + Copernicus NEUTRAL_LIVE + Beta1 LIVE |

---

## 2026-10-17 — Vigía de Sentinel Omega (sidecar Elixir)

Instalado `sidecar/vigia_sentinel/` — dead man's switch que detecta si el
ciclo del launcher se paró y avisa por Telegram (bot compartido
`@SismoBio_Bot`).

- Lee `data/sentinel_omega.log` (líneas `Starting cycle #N`) cada 5 min; la
  DB (`sentinel.db`) no deja huella de ciclo (`insert_ciclo` cae en un
  try/rescue silencioso), así que el log es el latido real.
- Alerta si el último ciclo supera 15 min (3 ciclos perdidos; umbral medido:
  cadencia 300 s), re-alerta cada 2 h y avisa la recuperación.
- Detección de pausa del sistema: si el propio vigía estuvo congelado
  (WSL2/Windows), no alerta.
- Runtime aparte (BEAM): si el ecosistema Python falla, el aviso lo emite
  otro mundo. Cero dependencias Hex.
- El token nunca vive en el estado del GenServer (se lee de entorno vía
  systemd `EnvironmentFile`; los crash dumps no lo exponen).
- `mix test` no arranca el watcher (`:ignore`): evitaría envíos reales de
  Telegram durante pruebas.
- Verificado: 13/13 tests; envío real de Telegram (HTTP 200); simulación de
  caída en dry-run contra copia del log (alerta correcta, sin envío real);
  `vigia-sentinel.service` (systemd --user, enabled).
- Es un sidecar: no toca el launcher, ni la DB, ni el unit de Sentinel.
- Operación: `sidecar/README.md`.

---

## 2026-09-28 (madrugada) — Pendientes cerrados: el tapón por una bandera, el bot mal nombrado y 959 filas de relleno

Los créditos de la pandilla se agotaron (vuelven en siete días) y el operador pidió
no dejar nada abierto. De su orden de seis pasos, 1-3 quedaron verificados en la
bitácora §22.4; esto es el resto.

### Changed — `infrastructure/pipeline/layer_runners.py`: el tapón sale, la bandera entra

`RASGOS_CON_FUGA` queda **vacío**, con el mecanismo conservado. Su condición de
retirada («hasta que `P(alarma|rasgo=0)` colapse») se cumplió y está medida.

Y al medir beta2 --- que no se había medido --- salió otro defecto, **de otra
familia**:

    beta2 con marea real (lo que da el ciclo)   NO_SIGNAL 0,3500
    beta2 sin marea                            WATCH     0,7126

No es fuga de procedencia: tras el rebuild la marea está en el 100 % de las DOS
mitades, así que el modelo **nunca vio un cero** y extrapola. Es una región de
entrada nunca medida. Callarlo siempre era perder su voto sin ganar nada.

`RASGOS_REQUERIDOS` --- rasgos cuyo CERO no puede ser una medición. Si uno falta,
ausente, no finito o cero, al modelo **no se le pregunta** y `onnx_callado` guarda
`falta:<rasgo>`, distinto del `fuga:<rasgo>` de Agente-C. Lleva
`beta2: ["marea_total"]` de canario: las ocho se calculan juntas por efemérides, solo
pueden faltar si `ephem` no está, y cero es imposible por física.

Es la «bandera de rasgo presente» que llevaba días propuesta, **en la puerta de la
inferencia** y no dentro del vector: `vector_para` pone 0,0 en lo que falta y para un
modelo 0,0 es un valor medido (regla dura 7), así que una bandera dentro del vector
solo movería el problema de columna.

### Fixed — dos fugas de token en el log, no una

La pandilla tenía apuntado `consenso_vigilante.py:895`. Barriendo todo el camino de
Telegram apareció `alert_service.py:362` con el mismo patrón: `logger.error(f"...:
{e}")` sobre una excepción de `requests`, que trae la URL, y la URL de la API lleva
el token DENTRO. Las dos usan ya `sin_token()`. Las de `charts.py` no entran --- son
fallos de matplotlib, ahí no hay URL. `test_token_no_se_filtra.py` cubre los cinco
sitios.

### Fixed — el bot es `@SismoBio_Bot`, y estaba mal en tres documentos

Lo escribí como `@IngZainos_bot` en `AGENTS.md`, `sentinel_omega/CLAUDE.md` y el
`AGENTS.md` del home. `@IngZainos_bot` es el bot **propio del watchdog**; lo dice el
`AGENTS.md` del home en su sección, «no el del Concilio (@SismoBio_Bot)».

Verificado contra la fuente autorizada sin exponer el token: `getMe` → `ok: True`,
`username: SismoBio_Bot`, id 8460857489. Es la Regla 0 aplicada a un documento: lo
escribí apoyado en otro documento en vez de preguntarle al sistema.

### Changed — el relleno de Schumann, marcado `en_vivo=0`

- `tbl_schumann_vivo`: 2 filas (rowid 534, 541), las únicas con `en_vivo=1`, 8.26 Hz
  / 21.46 % y `atraso_horas=0.0` --- fingiendo frescura. Respaldo
  `tbl_schumann_vivo_pre_marcado_20260928`.
- `TBL_PRECURSORES_COSMICOS`: **957 filas** (797 con 8.26/21.46 y 160 con
  25.0/21.46, que es el mismo conteo de píxeles en la escala vieja:
  `7,83 + 21,46 × 0,8 = 24,99`). Respaldo `tbl_prec_pre_marcado_schumann_20260928`.

El criterio no fue el valor sino la **fórmula** (`hz == 7,83 + act × escala`), y se
midió que **0 filas con `act=21,46` quedan fuera de él**: no se barrió ninguna
lectura real. El rango se cerró solo, la última es la id 12357 --- la corrección de
Schumann entró en el reinicio y desde entonces se escribe NULL.

### Removed — `launcher_fixed.py` (904 líneas)

Nada de producción lo importaba: su único lector era una prueba que existía para
mantenerlo honesto. Retirados los dos. Tener dos launchers EN EL CÓDIGO es el mismo
riesgo que tener dos corriendo, y eso costó el día entero. Las auditorías de
`docs/audits/` lo siguen mencionando y ahí se quedan: son registros de lo que había.

### Fixed — systemd

- `sentinel-omega-scheduler.service` estaba **`enabled` a nivel de usuario**: un
  segundo launcher armado, el mismo que el CHANGELOG del 2026-09-13 documenta como
  deshabilitado a propósito. `systemctl --user disable`.
- Corrección a lo reportado: los enlaces de `multi-user.target.wants` **no estaban
  rotos**, los cinco resolvían. El problema era el objetivo --- un gestor de USUARIO
  no alcanza `multi-user.target` ---, así que las unidades vivían de enlaces hechos a
  mano. `deploy/install.sh --no-start` lo corrigió sin tirar nada.

### Descubierto al verificar

`onnx: False` significa «el modelo no opinó» y mezcla **tres** casos: no hay modelo,
se abstuvo (`predict_signal` devuelve None cuando el nombre es `NO_SIGNAL`), o lo
callamos. La clave `onnx_callado` distingue el tercero; los dos primeros siguen
indistinguibles en la auditoría. Anotado, no arreglado.

### Pendiente con FECHA

**Antes del 4 de octubre, 03:07**: instalar con sudo `sentinel-omega-mantenimiento` y
`-onnx-retrain` desde `~/.cache/sentinel-omega/system-units/` (las dejó ahí
`install.sh`). La versión viva de `onnx-retrain` intenta reiniciar la unidad de
sistema **enmascarada** y falla sin avisar, así que el reentreno semanal no
ocurriría. El timer de mantenimiento sigue parado: sin él no hay barrido diario.

---

## 2026-09-27 (noche) — La fuga de procedencia, cerrada en el código; y el Kp que medía 24 minutos

Reparto acordado con la pandilla del Capitán en `CANAL_CLAUDE.md`: a Agente-C
`layer_runners.py`, `omega` y `loki`; a Claude `entrenamiento.py` y `launcher.py`;
a Agente-T la revisión. Esto es la parte de Claude, y se salió del reparto en dos
archivos por una razón que se explica abajo.

### Changed — `infrastructure/pipeline/entrenamiento.py`: los 17 rasgos

Un rasgo que está en `features_onnx.FEATURE_ORDER[bot]` y no en `BOT_FEATURES[bot]`
vale **0 en toda la mitad etiquetada como alarma** --- las firmas nacen de eventos
--- y un valor real en la mitad neutral --- los ciclos vivos del Juez. El modelo no
aprende el rasgo: aprende de qué TABLA vino la fila. Los 17 quedan declarados, cada
uno con la cobertura MEDIDA sobre las ventanas reales de su bot:

| bot | rasgos añadidos | cobertura |
|---|---|---|
| alfa1 | `kp_mean`, `kp_max` | 100 % |
| omega | `bz_mean`, `kp_mean`, `viento_avg` | 100 % |
| loki | `kp_mean`, `fase_lunar`, `bz_min`, `btc_volatilidad` | 100 % (858/858) |
| beta2 | las 8 de marea | 100 % (efemérides) |

**Las firmas guardadas NO cambian por esto.** Hasta que un rebuild las regenere y
se reentrenen los 8 ONNX, el vector sigue leyendo 0 en la mitad de alarma. La
verificación de que la fuga murió es que `P(alarma | rasgo=0)` colapse del 98-100 %
a la tasa base.

### Changed — `core/firmas/signature_engine.py`: sin esto, el arreglo era falso

Las 8 de marea **no existían en `FEATURE_KEYS`**. Declararlas solo en
`BOT_FEATURES`, como decía el reparto, habría puesto el contador de fugas en cero
con la firma igual de vacía: el filtro `{k: v for k, v in features.items() if k in
FEATURE_KEYS}` las descarta **en silencio** (regla dura 10 aplicada a la
corrección, no al defecto).

- `FEATURE_KEYS` pasa de 36 a 44 claves. Retrocompatible: `features_json` es un
  diccionario y `_vector` lo relee contra la lista vigente, así que una firma
  vieja simplemente trae NaN en las nuevas y `similitud` las excluye.
- `_marea_de_ventana(ts)` --- memorizada por instante --- llama a
  `marea_ventana(ts, horas=24)`, **la misma función que usa el lado vivo** en
  `models/rasgos_juez._marea`. Las dos mitades hablan de lo mismo, que era el
  punto. Coste medido: 0,651 ms por ventana sin caché, y un evento se extrae una
  vez por cada nodo, así que la caché lo absorbe (5 nodos del mismo instante:
  5,9 ms en total, SQL incluido).
- Verificado de punta a punta contra la base: las 8 claves salen para ventanas de
  1997, 2014 y 2026. Se calculan por efemérides, así que no dependen de ninguna
  fuente viva --- son la única cobertura del 100 % del sistema.

**Efecto colateral medido, que necesita decisión del operador:** `padre` lleva el
vector completo (`BOT_FEATURES["padre"] = None`), así que sus firmas también van a
llevar la marea. Sobre 4.000 pares reales de `padre`/`SISMO_M5`:

| | media | p95 | cruzan 0,85 |
|---|---:|---:|---:|
| sin marea | 0,6545 | 0,8297 | 2,85 % |
| con marea | 0,6768 | 0,8144 | **1,38 %** |

82 pares dejan de emparejar y 23 empiezan: padre se vuelve **más selectivo**, y eso
significa menos fusiones → más firmas distintas → menos recurrencia → menos
consolidadas, que son las que el Juez puede exigir. No parece malo (la marea es un
forzamiento candidato real y aporta variación donde el clima espacial coincide),
pero cambia la población de firmas exigibles y no era parte del encargo.

### Changed — `launcher.py`: el Kp salía de una ventana de 6 horas

Hallazgo de Agente-C, verificado contra la fuente en vivo: el endpoint es
`planetary_k_index_1m.json`, y midiéndolo da **358 filas, paso de 1,0 min, span de
5,95 h**. El código hacía `kp[-24:]` con un comentario que afirmaba «la serie viene
en tramos de 3 h: las últimas 24 muestras son 72 h». Son **24 minutos**; 72 h
necesitarían 4.320 muestras que ese feed no tiene ni puede tener.

Y no era solo `kp_max_72h`: los **tres** rasgos de Kp salían de esa ventana de 6 h
donde el entrenamiento usa 336 h y 72 h sobre `tbl_clima_espacial_raw`. Medido esa
noche:

| rasgo | entrenamiento (336/72 h) | ciclo vivo (feed de 6 h) |
|---|---:|---:|
| `kp_mean` | 1,96 | ≈ 0,30 |
| `kp_max` | 4,00 | 1,00 |
| `kp_max_72h` | 4,00 | **0,000** |

La distribución con la que se entrenó tiene p5 = 0,896 y mediana 1,742: el ciclo
entregaba el Kp **por debajo de su percentil 5 de forma permanente**. Arreglar solo
`kp_max_72h` habría bajado un número dejando el desajuste. Los tres salen ahora de
la misma tabla y las mismas ventanas que la firma; sin tabla el rasgo se omite y
`vector_para` pone 0,0 --- no se inventa.

**Con los modelos de hoy y todo lo demás fijo**, la ventana correcta desatura a los
tres bots que llevaban 10 de cada 10 ciclos en WATCH:

| bot | antes (Kp del feed) | ahora (Kp de la ventana) |
|---|---|---|
| alfa1 | `WATCH` 0,6771 | `NO_SIGNAL` 0,2150 |
| omega | `WATCH` 0,6149 | `NO_SIGNAL` 0,2630 |
| loki | `WATCH` **0,8200** | `NO_SIGNAL` 0,3500 |

loki pasaba de 0,82, o sea **por encima del veto bayesiano de 0,8** del tercer
acto: un fantasma satisfaciendo el acto final del consenso.

**Esto no cierra la fuga**, y conviene no contarlo como tal: el modelo sigue
respondiendo WATCH a un Kp casi nulo. Lo que cambió es que el ciclo ya no le sirve
uno. Un Kp real bajo en una quincena tranquila lo dispararía otra vez. Basta un
**reinicio** para que aplique --- no requiere rebuild.

### Added — `core/onnx_mixin.py`: un modelo de otro tamaño no se usa

Condición de Agente-T. `inferencia_de` compara la entrada declarada del `.onnx` con
`BOT_DIMS[bot]` y, si no coinciden, **descarta el modelo con `logger.error`** y deja
mandar a la regla. Sin esto el desajuste era invisible por los dos lados:
`pad_vector` recorta o rellena con ceros, y la excepción de `onnxruntime` la atrapa
`predict_signal` devolviendo `None`, indistinguible de «este bot no tiene modelo».

T ya tenía escrito el contrato en `tests/test_onnx_dims.py` con `xfail(strict=True)`
esperando el chequeo; se quitó la marca, como indica su propio docstring. Medido
antes de tocar nada: los ocho `.onnx` en disco coinciden con `BOT_DIMS` (10, 8, 16,
16, 16, 12, 8, 8), así que hoy no cambia nada --- existe para el reinicio en que sí
cambie.

### Descubierto al verificar

- **`tbl_psique_financiera` está parada desde el 2026-01-01** (4.125 filas). Se
  suma a `tbl_desgasificacion_raw` (31-jul) y `tbl_astronomia_cinematica`
  (31-dic-2025). Importa para el rebuild: `btc_volatilidad` cubre el 100 % de las
  858 ventanas reales de loki porque sus firmas terminan el 2026-01-08, pero los
  eventos de 2026-01 a hoy son el **5,9 %** del material sísmico posterior a 2014 y
  en esas ventanas no hay BTC. Tras el rebuild quedará una fuga residual de ese
  tamaño en loki: de 100 % a ~6 %, no a cero.
- **Una medición mía de la tarde estaba mal.** Reporté `btc_volatilidad` con 96,2 %
  de cobertura; lo había sacado del `features_json` de `padre`, que está
  **fusionado** entre eventos y por tanto puede traer claves de un evento distinto
  al de su `primera_vista`. Rehecho ejecutando la extracción sobre cada ventana de
  loki: 100 %. El error no cambia la decisión, pero el método sí importaba.
- **`TBL_HISTORICO_SISMICO.timestamp` es epoch Unix**, no texto. Una consulta mía
  comparándolo contra `'2014-09-01'` devolvió 0 filas y estuve a punto de leerlo
  como «no hay eventos». Regla 9, esta vez del lado de quien pregunta.
- **beta2 estaba en el mínimo exacto.** Tenía 4 rasgos, justo
  `MIN_DIMENSIONES_COMPARABLES`, y los cuatro de una fuente muerta desde julio.
  Ahora tiene 12, ocho de ellos incapaces de faltar.

### Verificación

Fugas: **17 → 0**, contadas como `FEATURE_ORDER[bot] - BOT_FEATURES[bot]` en los
nueve bots, y con una prueba nueva (`test_lo_declarado_existe_de_verdad`) que exige
además que todo nombre declarado exista en `FEATURE_KEYS` --- el modo de fallo que
habría convertido esto en un arreglo de mentira. Antes eso solo se comprobaba para
omega.

---

## 2026-09-27 (cierre) — El modelo gana siempre, aunque confíe menos

Primer hallazgo del registro arreglado. Sobre cinco horas de operación real, la
consulta que era imposible hasta hoy:

| bot | el modelo dijo | la regla decía | veces |
|---|---|---|---:|
| **beta1** | `WATCH` | `neutral` | **22** |
| **beta2** | `NEUTRAL` | `watch` | **8** |

beta1 convirtió en alarma 22 veredictos que su regla daba por calmos --- coherente
con que el tope de 500 lo tenía silenciado y ahora habla.

**El caso de beta2 es el que importa.** `layer_runners._aplicar_modelos` asigna
`sig.signal_type` y `sig.confidence` **sin condición**: el modelo gana siempre que
hable, aunque su confianza sea MENOR que la de la regla. La condición que parece
guardar eso --- `if tipo != sig.signal_type or conf > sig.confidence` --- solo
decide si se escribe una línea de log, no si se sustituye.

Un modelo con 0,35 de confianza apaga una alarma de regla con 0,60. En un sistema
de pérdida asimétrica, donde omitir pesa 10× y `AGENTS.md` dice que «el sistema
prefiere sobre-alertar a sub-alertar», ocho alarmas bajadas en cinco horas van
contra el principio declarado.

**No se toca**: es una decisión de diseño del operador, no un bug evidente. Lo que
cambió es que ahora se puede ver, y por eso llevaba quién sabe cuánto ocurriendo.

### Verificado en producción

`reasoning` con atribución, sobre una fila real:

    beta1  neutral 0.548
      reasoning: modelo ONNX: NEUTRAL (55%) [regla: neutral (30%) — Normal
                 spectral distribution; Schumann sin dato]
      onnx=True  onnx_senal=NEUTRAL  regla_senal=neutral

`tbl_firma_racha_viva`: 23 firmas con racha abierta en el primer ciclo tras el
reinicio (14517), cinco con lag propio sirviendo de ancla.

Nota de proceso: los campos `onnx_*` entraron a las 08:49 locales, no en el
reinicio de las 13:42 --- hubo un reinicio intermedio (probablemente el watchdog)
que no se registró, así que llevaban cinco horas funcionando mientras se decía que
esperaban reinicio.

---

## 2026-09-27 (tarde) — El tiempo de vida de una firma, en horas y para los nueve bots

Pedido del operador: *«si una firma es idéntica a una que vimos en el pasado
podremos intuir que tiene cierto tiempo de vida, y por eso hay que meterlos en
el entrenamiento»*. Estaba implementado a medias; lo que faltaba era medible.

### Changed — `infrastructure/pipeline/entrenamiento.py`

- **Los nueve bots, no solo `padre`.** Había un filtro fijo
  `if f["bot_name"] == "padre"` en `calcular_lags_anticipacion`, y por eso solo
  **182 de 19.578 firmas** tenían `lag_promedio_h` --- las 182 de padre. Ninguna
  firma de alfa1, beta1 ni el resto podía decir cuánto anticipa.
- **Resolución de 1 h en vez de 48–96 h.** La rejilla
  `[336, 240, 168, 120, 72, 24]` mide en DÍAS: medido, de 37 valores distintos
  los seis puntos exactos concentraban las firmas. Y como el barrido va de lejos
  a cerca y para en el primer emparejamiento, **redondeaba hacia abajo** --- una
  firma que empieza a emparejar a las 100 h se registraba como 72.

  El nuevo `_lag_detectado` es de dos etapas: la rejilla gruesa **acota** (mismo
  resultado que antes) y una **bisección refina dentro del tramo**. No se
  bisecta todo el rango a propósito: eso asumiría que la similitud es monótona
  en el tiempo y **eso no está medido** --- una firma puede emparejar a 100 h, no
  a 80 y otra vez a 60. Acotar confina la suposición a un tramo de 96 h, y si el
  refinamiento falla se devuelve el punto grueso: nunca peor que antes.
  ~13 sondeos contra los <=6 de antes, en vez de los 336 de un barrido horario.
- **El tope de muestra es por BOT Y CLASE.** Era por clase; padre tiene el 73 %
  de las firmas, así que sin este cambio quitar el filtro no habría servido de
  nada. Y un log por bot, porque antes el reparto era «padre: todo, el resto:
  nada» y no había forma de notarlo (regla dura 10).

**Medido sobre copia de la base y repoblado en producción:**

| | antes | ahora |
|---|---:|---:|
| firmas con lag | 182 | **1.058** |
| bots cubiertos | 1 | **8** (todos los que forman firmas) |
| valores distintos | 37 | **569** |
| clases medidas | 8 | **11** |
| en punto exacto de rejilla | 100 % | **16,4 %** |
| coste | — | **20,6 s** (0,4 % del entrenamiento) |

Aparecieron `TORMENTA_Kp6/Kp7/Kp9`, que no existían en `tbl_lag_anticipacion`
porque solo se medía a padre y las tormentas son firmas de otros bots. Kp7
anticipa ~12,7 días; Kp9 ~11,1.

Los promedios por clase NO son comparables uno a uno con los de antes: cambió la
población (ocho bots en vez de uno) además de la resolución.

### Added — el ancla de la cuenta regresiva (`tbl_firma_racha_viva`)

`format_lag_line` sabía restar el transcurrido al lag aprendido, pero se anclaba
en `tbl_cimatica_patrones.primera_vez`, y **el rebuild pone esa columna al 100 %
en la fecha del rebuild** (279.453 de 279.453 filas). La cuenta regresiva se
reiniciaba entera en cada reconstrucción: un número plausible que no medía nada.
`TBL_FIRMAS.primera_vista` tampoco sirve --- guarda fechas reales (1994–2026)
pero es la primera vez HISTÓRICA, y restarle el transcurrido da «restan 0 h».

Tabla nueva (forward-only), llenada por `launcher._registrar_racha_viva` en cada
ciclo: `firma_id`, `inicio_ts`, `ultimo_ts`, `ciclos`. Si la firma se vio hace
menos de `RACHA_TOLERANCIA_MIN` (20 min, dos ciclos de holgura) la racha
**continúa** y su origen no se mueve; si hubo un hueco mayor, empieza una nueva.
Es dato VIVO: no se reconstruye del histórico y el rebuild no lo toca.

`alert_enrichment.ancla_de_racha_viva` lo prefiere al patrón cimático, y se lleva
**el lag de ESA firma**, no el promedio de su clase. Sin racha, cae al
comportamiento anterior.

De punta a punta, firma real de beta1 (lag propio 202,7 h) con 40 h de racha:

    ⏱ Lag típico: ~203 h (restan ~163 h) · cuenta regresiva: ~163 h restantes
      · freq: 2 → vigilar hasta 04/10 10:00 UTC

### Changed — `launcher.py`: la ventana, en horas

El launcher ya priorizaba correctamente el lag DE LA FIRMA sobre el promedio de
clase, pero lo imprimía dividido por 24. Con la rejilla vieja eso no perdía nada;
con resolución de 1 h sí --- 202,7 h impresas como «8 días». Se añade
`ventana_tipica_h` y se **conserva** `ventana_tipica_dias`, que leen `muro_lags`,
`generar_reporte` y el reporte ejecutivo. Campo añadido, ninguno quitado.

### Descubierto al verificar

`analizar_factores_lag` ya existía y ahora tiene material. Lo que diferencia una
firma de aviso CORTO de una de aviso largo:

| rasgo | rápidas | lentas |
|---|---:|---:|
| `so2_kt_win` (SO₂ volcánico) | **91,66** | 4,60 |
| `so2_kt_90d` | 268,25 | 105,91 |
| `sismo_count_72h` | 4,14 | 1,59 |
| `es_sicigia` | 0,25 | 0,11 |

**La desgasificación volcánica activa y la sismicidad reciente predicen un aviso
corto**; su ausencia, uno largo. Es «qué firmas caen en qué banda de horas», y ya
es consultable.

### Verificación

23 pruebas nuevas (15 de lag + 8 de racha). Suite completa: `PYTEST_EXIT=0`,
cero `FAILED`. El lag ya está repoblado en producción; la racha necesita
**reinicio** para empezar a registrarse --- **no requiere rebuild**, por ser dato
vivo.

---

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

### Conectado (a orden del operador, «conecta el campo»)

- **`infrastructure/pipeline/juez_cycle_register.py`** — el `detalles` ahora
  persiste `onnx`, `onnx_senal`, `onnx_conf`, `regla_senal` y `regla_conf` desde
  `sig.data`. Era lo que el docstring de `_aplicar_modelos` prometía desde el
  principio: «para que el Juez pueda comparar después quién acertaba». Con esto
  la comparación es SQL en vez de prosa:

      SELECT bot_name, resultado, COUNT(*) FROM TBL_JUEZ_AUDITORIA
      WHERE json_extract(detalles_json,'$.onnx_senal') IS NOT NULL
        AND json_extract(detalles_json,'$.onnx_senal')
         != json_extract(detalles_json,'$.regla_senal')
      GROUP BY 1,2;

  Se copian SOLO esas cinco claves, no `sig.data` entero: si cada agente vuelca
  lo que quiera en su `data`, el `detalles_json` de todas las filas crece sin
  control. `onnx: False` también se guarda --- distingue «decidió la regla» de
  «no hubo modelo». Retrocompatible: las filas de antes no las tienen. 6 pruebas.

### Pendiente (propuesto, no hecho)

1. Rematerializar `tbl_juez_rasgos_reconstruidos` — raíz del 8,26; la purga es el
   cinturón.
2. Codificar la ausencia aparte del valor (bandera «kp presente»). El fantasma
   sigue DENTRO del modelo —sin Kp responde WATCH 0,726— pero ya no tiene ruta.
   Mientras el vector no pueda decir «no lo sé», cada 0,0 es un fantasma esperando.
3. alfa2 con rasgos de ESA: `tbl_frp_detecciones` lleva **una fila** (S3B del
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
