# Changelog — Sentinel Omega

## [Unreleased] - 2026-10-13 — JSONB: propuesto, medido, rechazado

Del full-upgrade (SQLite 3.53) salió la hipótesis de acelerar las
auditorías del Juez con JSONB. Medida contra la DB real (1,03 M filas /
124,5 MB de `detalles_json`): `json_extract` GANA en todos los patrones
(1,21–1,25× más rápido, incluso contra el jsonb materializado una vez por
fila). **Integración rechazada por medición**; `deploy/bench_jsonb.py`
queda como instrumento para no re-persuadirla. La migración de venvs a
python 3.14 sigue pendiente de ventana de rebuild (nunca en caliente).

## [Unreleased] - 2026-10-12 (madrugada del 13) — Auditoría del tablero: las superficies invisibles montadas por fin

**La trampa del 25-sep, cazada de nuevo:** `App.tsx` montaba 7 pestañas
mientras 6 archivos de tabs vivían sin montar. Lo grave medido: los **4 KPI
del nulo del lag** (10-08) se escribieron en `PadreJuezTab`… que nadie
montaba — superficie invisible. Y `ConsensoTab`/`SistemaTab` referenciaban
`api.system`, un namespace que **nunca existió** (compilaban porque tsc no
llega a archivos fuera del grafo de importación).

- **LokiTab reescrita y MONTADA**: identidad nueva (Resonancia del Ciclo
  Mayor), KPIs medidos (resonancia con días, P(tormenta hoy) con base al
  lado, última tormenta, rotación de Carrington como constante declarada),
  Schumann como **actividad** (Hz SIN MEDIR), y el **reasoning vivo** de la
  última predicción del Juez. `/api/unificado` sirve el bloque `loki`
  completo: resonancia calculada con la MISMA función del runner
  (`estado_resonancia` extraída a módulo para que la regla viva una sola
  vez), posteriores medidos y último veredicto con su explicación.
- **PadreJuezTab montada** — los 4 KPI del nulo del lag y los veredictos
  del Juez fase viva por fin visibles.
- **Borradas** `ConsensoTab`/`SistemaTab` (muertas + rotas). FamiliasTab y
  OmegaTab quedan sin montar, documentadas en el README del dashboard.
- **Telegram**: rama solar en `describe_values` (grieta Bz mín / Kp máx /
  viento máx) — no existía porque `TORMENTA_SOLAR` no había disparado ni
  una vez en toda la historia; hoy dispara y sus valores son los extremos.
- Auditoría de pipeline: los consumidores de `values_json` son genéricos
  (safe con las claves nuevas); `juez_cycle_register` copia sólo sus 5
  claves — la resonancia no engorda `detalles_json`.
- Build verde (tsc + 366 KB), Vite sirviendo ambas pestañas nuevas en 200,
  API devuelta verificada con curl (resonancia medida: última tormenta
  hace 3 d, inactiva — correcto). Suite: 1.348 · 2 rojos deliberados.

## [Unreleased] - 2026-10-12 (noche) — Loki rediseñado: la teoría del operador, medida y viva

**«TEORÍA DEL CAMPO UNIFICADO FRACTAL» (operador, 2026-09-16), operacionalizada
con `deploy/medir_loki_teoria.py` contra 11.688 días (1994-2025).** El
pipeline SVD→FFT→φ de una fila (muerto por ~112 órdenes de magnitud, medido
el 10-09) salió; entra la señal que los datos aprueban: **la resonancia de
la rotación solar** — el sistema menor (tormentas) resonando con el ciclo
mayor (Carrington, 27,275 d), tal como pide la teoría.

| Paso de la teoría | Medido | Veredicto |
|---|---|---|
| Fourier (resonancia con el ciclo mayor) | picos vs nulo de ruido rojo: 27,3 d en viento (×1,19) y Bz (×1,53); armónicos 13,5/9,1 d | **VIVE** |
| Bayes (la recurrencia como regla) | P(tormenta) 0,94 % → **3,19 %** con antecedente hace 26–29 d (ganancia 3,4×; control sin antecedente 0,88 %; dispara 3,2 % de los días) | **VIVE** |
| Colapso (resonancia ∧ grieta) | P=23 %, n=13 días en 32 años — frágil, reportado con su n; la conjunción no supera a la grieta sola (34 %) | el aporte de loki es el eje del TIEMPO, no la conjunción |
| Gauss-Jordan (matriz limpia) | rango 4,00 exacto en calma y tormenta: las 7 columnas son colineales SIEMPRE | **LIMPIEZA** (preprocesado), no señal — y con ello muere el SVD de una fila |

- **WATCH de resonancia** (conf 0,55): tormenta Kp≥5 hace 26–29 d → el
  posterior medido va EN el reasoning («P(tormenta hoy) 3,19 % contra base
  0,94 % — ganancia 3,4× medida 1994-2025»).
- **Confirmación** (conf 0,70): grieta viva (Bz≤−5) dentro de la ventana →
  «COLAPSO RECURRENTE… Loki CONFIRMA, no alerta solo» — su rol de consenso
  del 10-10 intacto, y la fragilidad (n=13) declarada en el propio texto.
- `bayesian_posterior` del signal sigue existiendo para el tablero — ahora
  con la probabilidad REAL condicional, no un φ-alignment.
- El runner mide el antecedente contra `tbl_clima_espacial_raw` (read-only,
  reloj UTC alineado con la tabla — off-by-one cazado por el test).
- La Espiral Dorada de la teoría sobrevive como el CICLO EN EL TIEMPO
  (27,275 d), no como la norma de un vector contra 1,618.
- **Predicción concreta**: la tormenta del 10-oct activa la ventana de
  resonancia ~**5–8 de noviembre** — si su fuente fue un agujero coronal
  recurrente, loki pre-avisará.

Tests: 6 nuevos (resonancia activa/colapso/inactiva/ausente/grieta sin
resonancia + el runner contra DB temporal); mutación (ramas en `if False`)
mata exactamente a los tres que vigilan la decisión. Suite: **1.348 · 2
rojos deliberados de alfa1 · 7 saltos**. Launcher reiniciado: primer ciclo
vivo `resonancia=medida, inactiva → neutral`, cero errores.

## [Unreleased] - 2026-10-12 — La tormenta que el sistema no vio: la cadena solar recalibrada a extremos

**La tormenta Kp=7 del 10-oct (Bz_min −28,9 nT durante 2 h, viento 841 km/s)
pasó sin UNA detección solar, sin UN GRIETA y con el consenso en `neutral`.**
Corrección al propio CHANGELOG: la entrada del 10-11 decía
«`_scan_tormenta_solar` ✓ · GRIETA en alertas ✓» — las rutas existían, pero
medidas contra producción **disparaban 0 veces en 1.770 h vivas** y 0 en toda
la historia de `TBL_DETECCIONES`. `TORMENTA_SOLAR` nunca había disparado.

### La causa: toda la cadena solar leía la MEDIA de 24 h

`layer_runners._compute_precursor_risk` reducía el feed 1-min a
`bz = mean(omni_df.bz_gsm)`, y ese escalar era el que llegaba al scanner
(`bz ≤ −10 ∧ kp ≥ 5`) y a la alerta GRIETA (`bz ≤ −5`). Una grieta de 2 h a
−12/−28,9 se diluye a ~−3 en la media diaria: la compuerta vieja sólo se
cruzaba en las tormentas del siglo (**187 h en 30 años**, 2003-11/1998-11).
Regla 8 en estado puro.

### El arreglo: quien decide "AHORA" lee el EXTREMO

- `components` gana claves (forward-only, sin tocar DB): `bz_min`, `bz_max`,
  `bz_inst`, `viento_max`, `viento_inst`, `kp_max`. `bz_nT`/`wind_kms` siguen
  siendo la MEDIA — el fantasma conserva su comparabilidad con sus 3.261
  ciclos y con el backcast.
- `_scan_tormenta_solar`: `bz_min(24 h) ≤ −10 ∧ kp_max(6 h) ≥ 5` — tasa
  medida sobre 287.178 h: **1,99 %** (5.701 h); en el periodo vivo habría
  disparado **57 de 1.770 h** (toda la tormenta del 10-oct incluida).
- `_scan_perturbacion_geomagnetica`: mismos extremos (`bz_min ≤ −5 ∧
  kp_max ≥ 3`, callando si cumple la de tormenta). Tasa: 15,4 % — al borde
  de lo hablador; vigilar en producción y apretar a `kp_max ≥ 4` si ruido.
- GRIETA/TORMENTA inmediatos (Centinela): leen el Bz/viento
  **instantáneo** (última lectura 1-min) con respaldo a la media.
- Sin dato en la serie → `None`, no dispara: ausencia no es cero (regla 7).

Verificado: replay de la tormenta real (desde `tbl_clima_espacial_raw`) a
través del `scan()` nuevo — pico 17:00 UTC → `TORMENTA_SOLAR 0,85` con
`bz_min −28,89 / kp_max 7,0`; calma → nada. Mutación: vuelta a medias →
el test de la tormenta cae. Suite: 1.337 pasan · 2 rojos deliberados de
alfa1. Con esto el muro SOLAR se enciende en tormentas: la base del
«modo tormenta activa» (Kp≥5 → reportes más frecuentes).

### Modo TORMENTA ACTIVA: el digesto acelera con Kp≥5 (mismo día, GO)

Con tormenta geomagnética (Kp≥5, definición G1 de NOAA) el digesto pasa de
cada 60 min a **cada 15 min** — la cadencia del oneshot de rutinas, tormenta
en tiempo casi real. La señal es `MAX(kp_max)` de las últimas **3 h** de
`tbl_clima_espacial_raw` (read-only), el mismo umbral medido del scanner.
Medido: la tormenta del 10-oct habría mantenido el modo activo **12 h**
(15:00 → 02:00) — ~48 digestos en vez de 12.

- `TG_DIGEST_MINUTES_TORMENTA` (default 15) y `TG_TORMENTA_KP_MIN`
  (default 5.0) por entorno. La marca compartida del digesto sigue siendo
  la única fuente de verdad; sólo cambia cada cuánto se considera vencida.
- Banner «🌀 MODO TORMENTA ACTIVA» con el Kp medido al tope del digesto, y
  `· TORMENTA` en el subject.
- **Por qué 3 h a piso de hora** (regla 0, cazado en vivo): el bloque de la
  hora H no aparece hasta que H cierra (~1-1,5 h de retraso medido) y una
  ventana de 2 h con segundos excluía la fila límite — la primera versión
  devolvía `None` con la tabla llena. Sin dato → sin modo tormenta (regla 7).
- La suite se aísla de la DB de producción (`conftest` apunta `SENTINEL_DB`
  a un temporal): una corrida DURANTE una tormenta real no puede cambiar la
  cadencia de los tests.

## [Unreleased] - 2026-10-11 — El pivote, la auto-reparación y la miniapp del pipeline

**El proyecto se convierte en lo que ya era.** El operador dio el GO:
«B y C en paralelo, A como experimento dirigido». El pivote de
«predecir sismos vía Schumann» a **plataforma multi-dominio de detección
de anomalías naturales**.

### La Opción B: la plataforma que ya existe (medida contra 30 años)

| Dominio | Señal | En la DB | Firmas | Scanner |
|---|---|---|---|---|
| Espacio | Tormentas Kp≥5 | **8.439** horas | 429 Kp6 | `_scan_tormenta_solar` ✓ |
| Espacio | Grietas Bz≤−10 | **1.738** horas | — | GRIETA en alertas ✓ |
| Espacio | Kp≥8 extremas | **258** horas | — | ✓ |
| Volcánico | Erupciones VEI≥3 | — | **756** | SO2 + air_quality ✓ |
| Sísmico | Enjambres activos | **2 ahora** | 20.130+ | `_scan_seismic_cluster` ✓ |

**Hubo una tormenta Kp=9 AYER** y el sistema la vio.

### La Opción C: el 46 % de exigibles, descompuesto

Los 11.271 exigibles del padre son **100 % Omori** (`sismo_*_win`):
cero sin rasgo sísmico. Es un mapa de peligrosidad, no detección de
precursores. Sin el padre: **2.399 exigibles reales** (beta1 2.394 +
mínimos). El reparto concuerda con la compuerta ONNX (medición
independiente).

### La Opción A: plantilla del experimento dirigido

`docs/EXPERIMENTO_DIRIGIDO.md` — las cuatro reglas (declarar antes de
medir, nulo al lado, once semillas, control más barato primero), cinco
candidatos con física más plausible que Schumann (radón, resistividad,
migración de enjambres, Vp/Vs, infrasonido), y el paso a paso.

### Auto-reparación: tres capas vivas

| Capa | Qué hace | Cómo |
|---|---|---|
| 1. Detección | Tests, journal, servicios, DB | Timer cada 4 h |
| 2. Fix determinístico | WAL→checkpoint, launcher→restart, timer→reanclar | Instantáneo |
| 3. Fix vía Concilio | codegemma escribe, verificador ejecuta | Esqueleto, GO pendiente |

Más el **vigilante de rebuild** (cada 15 min): detecta que terminó,
verifica log, sube servicios, reancla timers, corre verificación —
TODO sin intervención.

### Rebuild con el código nuevo (post-pivote)

40.726 firmas, 23.266 consolidadas, 13.972 exigibles, **cero rasgos de
Schumann fabricados** (verificado), 348.588 patrones cimáticos,
3h 20min, log verificado sin fallos.

### Mensajes y saneador, verificados punta a punta

El saneador de HTML para Telegram: `<b>`, `<i>`, `<code>`, `<pre>` pasan
tal cual; `<br>` se convierte a salto de línea; `<` y `&` sueltos se
escapan (el caso `(<50)` que mató 16 digestos). Plantilla huérfana
corregida. Dos interpolaciones sin `html.escape()` en el bot del
Concilio arregladas.

### Miniapp rediseñada: pipeline de Sentinel como protagonista

`/api/mini/sentinel` — nuevo endpoint que lee la DB de producción.
6 cards: estado del ciclo, telemetría, muro visual, sismicidad (M4.5+ +
enjambres), clima espacial (tormentas), memoria del sistema. El Concilio
relegado a card secundaria. Verificado contra producción.

### El residuo de Eskdalemuir, muerto a ±7 días

El efecto aparente de `sr3_hz` (+0,64 con ±180 días) se desplomó al
estrechar el empareje estacional: ±30 días +0,27 → **±7 días +0,057 ±
0,078 (cero)**. El 100 % era calendario (tormentas globales moviendo
SR3 en 0,3-0,6 Hz entre meses, filtrado por el hueco may-oct del
dataset). La explicación de Omori que propuse para el residuo quedó
DESCARTADA por medición — la lección: el siguiente control más BARATO
antes que la explicación elaborada. Costo: seis corridas de un minuto.

### Git limpiado para push

2,6 GB de blobs muertos en la historia (915 MB DB, 733 MB ×2 WAL, 255
MB log) removidos con filter-branch por rango. Chat-id personal
redactado (repo público). Cero secretos en el rango. CLAUDE.md y
CHANGELOG actualizados con lo medido. 218 commits limpios.

## [Unreleased] - 2026-10-10/11 - Eskdalemuir: la réplica medida — y la hipótesis central cerrada en DOS estaciones

Lo que siguió a la medición de Granada: tres pasadas más del retiro del Hz
(porque estaba a medias y la primera mató la serie de actividad), la
auditoría de TODO el pipeline por el cambio, el consenso arreglado, y el
GO del operador para la réplica en estación independiente. Que resultó
estar descargable, abierta y cruda — y que CONFIRMÓ el nulo, con el
confound rastreado hasta el mecanismo.

### El retiro del Hz, terminado de verdad (tres pasadas)

- **Pasada 1**: el fetcher medía actividad real y la tiraba como
  «placeholder» (`is_baseline_placeholder` trataba `hz=None` como el
  fallback viejo); el LOCF arrastraba el 7,92 fabricado como «último valor
  real» para siempre; `launcher.schumann_mean` y las puertas de frescura
  tenían `float(None)` latentes. La ACTIVIDAD es la señal en toda la
  cadena; el hz viaja NULL.
- **Pasada 2**: el digesto llevaba SIN telemetría de precursores por una
  query con columna muerta (`ts`); el Kp salía con 15 decimales; el
  `delta_enrichd` reventaba por ciclo en `float(AVG(NULL))`; el
  `DEFAULT 7.83` del DDL era una máquina de fabricación en potencia;
  la historia fabricada NULL-eada con respaldos (740 precursores + 883
  enjambre + 25 vivo).
- **Pasada 3 (auditoría del pipeline completo, con el reentreno ONNX como
  fecha límite)**: el volcado al enjambre TIRABA la actividad (columna
  añadida forward-only + backfill de 117 filas desde precursores, donde la
  actividad siempre fue real); `.get(..., 0.0)` (regla 7) en el scanner; las
  dos rutas muertas del scanner declaradas en el código. Verificados
  seguros: rasgos del Juez, ONNX (el reentreno realinea ambos lados),
  consenso, omega, loki, jupiter.

### El consenso: la «correlación Schumann» era «beta1 activo» disfrazado

Medido: **0 ALERTs en 4.566 ciclos de producción**. La compuerta nunca leyó
un dato de Schumann; exigía beta1 específicamente (ruta viva al 0,02 %).
Opción B del operador: **corroboración por FAMILIA** — beta1 O beta2
(~7 % vía niebla/estrés, medido) dan la segunda voz; Loki pasa a solo
subir confianza (sus ramas de decisión están muertas por construcción,
posterior ~1e-112); el veto huérfano y las dos ramas muertas retirados.
Sin la familia activa, dos alertas de dos familias siguen en WATCH (test
que lo ancla).

### Regla 8 sobre los abiertos: delta, beta1 y loki medidos

- **Delta**: sus dos «bonos de topología» disparaban en 2.674/2.674 ciclos
  — uno estructural (b=−4,85 contra umbral −0,2) y uno comparando DÓLARES
  contra 0,7. Retirados; `combined = fear_score` medido y verificado en
  vivo (0,000 en calma).
- **beta1** (`deploy/medir_reglas_beta1.py`): única ruta viva = espectro Kp
  (0,02 % de 95.652 ventanas); las tres rutas de Schumann muertas con la
  escala real de actividad.
- **loki**: todas sus rutas no neutrales muertas por construcción (SVD de
  una fila → FFT plana → dim fractal clavada en 2,0; la norma del vector
  contra φ=1,618 da posterior ~1e-112). Documentado, no tocado —
  rediseñarlo es decisión del operador.
- `sos70-descarga.timer` resucitado: la cirugía systemd del 8-oct lo dejó
  disabled sin registro (archivaba Tomsk desde el 27-sep; se detuvo ese
  día). Documentado en AGENTS.

### Eskdalemuir: abierto, crudo y con el método del propio BGS

- **Acceso ABIERTO**: el item 192216 del NGDC es unrestricted, licencia
  Open Government Licence («Contains data supplied by UKRI»). El blurb de
  copyright NERC en data.gov.uk era el texto genérico. 2025.zip:
  21,3 GB, descarga reanudable, montada como servicio que sobrevive
  reinicios (~29 h reales).
- **La documentación legacy estaba DENTRO del zip**: lector oficial de
  BGS, las DOS tablas de calibración de las bobinas GFZ MFS-05 (calibradas
  en Niemegk 2024) y el docx de Ciaran Beggan. El `.ssc` es ASCII de
  espacios a 128 Hz; el espectro sale calibrado en nT/√Hz. El «conteo de
  píxeles» sobre los PNG quedó descartado: con el crudo, el lorentziano
  es estrictamente más información.
- **La física salió el primer día**: SR1 ≈ 7,9-8,0 Hz, SR2 ≈ 14,1, SR3 ≈
  20,0-20,6, con variación intradía de ~0,6 Hz — la misma escala que
  Granada. Lector endurecido con alineación por `%hh` REAL (los huecos del
  digitizador no corren los bloques; el digitizador escribe «NAN» literal
  y el parser C de pandas revienta ahí — corregido). 220 días, 52.490
  intervalos, procesado incremental mientras bajaba.

### La réplica: el efecto que sobrevivió once semillas… y era el calendario

El barrido pareció dar OTRA cosa: sr3_hz a +0,53 (24 h) y +0,78 (72 h),
**estable a once semillas** (+0,64 ± 0,11 — a diferencia del +0,19 de
Granada, que murió al primer barrido). El playbook mandó desconfiar, y la
descomposición escalón a escalón del empareje estacional lo cerró:

| empareje | sr3_hz (24 h) |
|---|---|
| ±180 días | +0,64 ± 0,11 |
| ±30 días | +0,27 ± 0,08 |
| **±7 días** | **+0,057 ± 0,078 — nada** |

**El 100 % era fuga estacional**: la base mensual de SR3 oscila 1,35 Hz
(feb 21,30 vs dic 19,95) y el hueco may-oct del dataset la filtraba. La
explicación de Omori que se propuso para el residuo quedó DESCARTADA por
medición — la lección (dicha en la bitácora): el siguiente control más
BARATO antes que la explicación elaborada. **El nulo queda confirmado en
DOS estaciones independientes** (España 2013-2017, Escocia 2025), dos
instrumentos, el mismo medidor y protocolo.

### La historia de git, limpiada para poder empujar

Los 217 commits sin push llevaban dentro blobs de **915 MB (copia de la
DB), 733 MB ×2 (WAL) y 255 MB (log)** — GitHub los habría rechazado. La
primera herramienta (git-filter-repo) reescribió toda la historia al
quitar la firma GPG del commit raíz (perdió el merge-base); corregido con
filter-branch por RANGO: ancestros intactos, 217 commits, cero blobs
>10 MB, árbol final idéntico, sin secretos en el diff (escaneado por
patrones de token).

## [Unreleased] - 2026-10-09 - El latido medido por fin: la hipótesis central, en negativo

El eje del proyecto nunca había sido medido: `schumann_hz` era una recta sobre
un conteo de píxeles (retirada el 2026-10-09). Hoy se bajó el **procesado
completo de Sierra Nevada (UGR)** — 4 años, 96 `.npz`, 405.276 intervalos de
10 min, ajuste lorentziano calibrado — y con él se contestó la pregunta que
el sistema fue diseñado para hacer.

**No hay señal precursora.** 26.458 sismos M4.5+, ventanas de evento contra
calma **emparejada por época**, nivel y forma, escalas de 24 h a 336 h:

- **NIVEL**: el único asomo (`sr3_hz` a 24 h, +0,191 en la primera lectura)
  no sobrevive el barrido de once semillas: media **+0,063 ± 0,073**, y ningún
  canal llega a 1 σ de su propio ruido de muestreo. El +0,191 era el sorteo
  optimista, 3× la media.
- **FORMA**: la curva z-normalizada no se parece más entre eventos que contra
  calma en ninguna escala (ev-ev menos ev-calma entre −0,0007 y −0,0028; lift
  0,96-1,01×).

Lo que los días previos decían («no hay señal precursora») era correcto; lo que
faltaba era haberlo medido con el sensor principal, y ahora está medido. No se
integra al backcast un canal medido en nulo — lo contrario del vicio que esta
bitácora persigue. Detalle y reproducibles:
`estado/BITACORA_2026-10-09.md` · `deploy/medir_schumann_precursor.py` ·
`deploy/bajar_schumann_ugr.sh` · `docs/SCHUMANN_FUENTES.md`.

De adquisición: el «HTTP 403» del repositorio UGR era **bloqueo de bots** (con
`User-Agent` propio entra); y la primera descarga se truncó al 30 % saliendo
con `curl` exit 0 y HTTP 200 — el servidor cerró la conexión y el código de
salida no lo delató. El reanudador verifica el **tamaño**, no el exit code.

### El rebuild de la mañana murió a medias — 9 h con cero memoria exigible

El rebuild de las 07:20 se cortó a las 07:40 (80.000/191.482 eventos, la sesión
que lo lanzó murió y se lo llevó puesto) y dejó `TBL_FIRMAS` a medias con
**cero exigibles**: el Padre sin memoria que exigir, y el sistema mandando
digestos «normal» durante 9 h. Dos trampas medidas: `parar_launcher` mata el
PID pero systemd (`Restart=always`) lo resucita en 10 s — el rebuild corrió
17 min con el launcher escribiendo encima — y el `verificar_post_rebuild.py`
escrito a las 07:23 nunca se corrió. Receta corregida y aplicada: launcher y
watchdog bajados **a nivel systemd**, rebuild como **unit transitoria**
(`systemd-run --user`) que sobrevive a la sesión. Verificación sobre
poblaciones completas con `deploy/verificar_post_rebuild.py`.

## [Unreleased] - 2026-10-09 - El notificador: rescatado, y un rebuild que NO se hizo

Abierto por una pregunta del operador que el criterio no aguantaba: **«estás
matando al notificador»**. El padre es quien ve y quien avisa, y tenía 29.148
firmas ---el 72 % de la memoria del sistema--- con **cero exigibles**.

### El criterio de `exigible` era absoluto y lo excluía por aritmética

| bot | pe | pc | pe/pc | exigibles (viejo) |
|---|---|---|---|---|
| `padre` | 0,0040 | 0,0015 | **2,67×** | **0** |
| `beta1` | 0,0391 | 0,0138 | 2,83× | 816 |
| `alfa1` | 0,1610 | 0,1477 | **1,09×** | **131** |

Con `pe - pc >= 0,05` y un `pe` de 0,0040, la diferencia máxima POSIBLE del
padre era 0,0040: **no podía pasar el umbral ni siendo perfecto**. Y al revés
premiaba a alfa1 por disparar mucho, no por distinguir.

Ahora decide el **lift** suavizado `>= 2,0` más un suelo de 20 aciertos, con la
muestra de 300 a 1.200 ventanas. Padre **0 → 895**, beta2 0 → 15, beta1 816 →
1.812; alfa1, omega y loki a 0. Y la compuerta de habilidad ---medición
independiente--- les había dado AUC 0,490/0,493/0,494 contra 0,800 de beta1:
**las dos mediciones concuerdan ahora; antes se contradecían.**

El padre ya tiene asertividad histórica: `causal 0,449`, `falsa_alarma 0,273`,
**ganancia 0,176**.

`tbl_sesgo_aprendizaje.consolidadas_sin_exigir` separa «no tiene memoria» de
«tiene memoria y ninguna discrimina» ---el peor estado, y además deja al bot
inmune al castigo---. Va en la misma pasada a propósito: dejar caer a tres bots
sin esto habría trasladado el descarte silencioso.

### Y el rebuild de los rasgos del padre NO se hizo, con el GO dado

El operador autorizó rediseñar su conjunto de rasgos **aunque tocara rebuild**,
pidiendo documentar antes de empezar. Documentar es lo que lo salvó.

Con 21 dimensiones el lift del padre sería 5,26× contra 1,77×. Pero al diseñar
el conjunto por medición, los cuatro rasgos que lo encabezan son `sismo_*_win`
---la sismicidad PREVIA del propio nodo, **30-75×** más en una ventana de
evento--- y **quitando esa familia el lift cae a 1,04-1,09×** en todos los
tamaños. O sea que el 5,26× venía entero del historial sísmico del nodo.

No es fuga de etiqueta (la ventana es `timestamp_blk < ts_evento`, estricta):
es **agrupamiento de Omori**, lo mismo que la compuerta rechaza con
`origen == "agrupamiento_omori"`. Darle una lista habría cocido un mapa de
peligrosidad con cara de precursor en la memoria del que avisa, y es la tercera
vez que la misma señal se disfraza en este proyecto. Reproducible:
`deploy/disenar_rasgos_padre.py` y `deploy/sin_omori.py`.

## [Unreleased] - 2026-10-08 - El modelo nulo, en todas las capas

Sin push. Branch `local/recuperacion-datos-2026-09`, 14 commits.

El día entero gira sobre una sola idea: **un número medido solo sobre eventos no
mide nada**, porque la calma es el ~97 % del tiempo. Apareció en cuatro capas
distintas y en las cuatro el arreglo fue el mismo —poner el modelo nulo al
lado—, así que quedó como **regla dura 11** en `AGENTS.md`.

| Capa | El número viejo | Su nulo | Resultado medido |
|---|---|---|---|
| Juez | asertividad 35,3 % | callarse siempre: **97,1 %** | ganancia 1,17× |
| Firmas | 23.248 consolidadas | ventanas de calma | **982 exigibles** (4,2 %) |
| Lag | 978 firmas «anticipan» | calma **del mismo nodo** | **315** (32 %) |
| ONNX | AUC contra 0,5 | tasa base **por nodo** (0,899) | **0 de 7 aprueban** |

### La compuerta de habilidad de los ONNX: niega a los siete

Primera corrida con la compuerta activa. No se escribió un solo `.onnx` —los de
octubre siguen en disco intactos, que es lo que promete— y el reparto dice todo:

```
alfa1  AUC 0,490   ganancia -0,409      beta1  AUC 0,800   ganancia -0,099
beta2  AUC 0,502   ganancia -0,398      delta  AUC 0,551   ganancia -0,350
omega  AUC 0,493   ganancia -0,406      loki   AUC 0,494   ganancia -0,405
alfa2  38 muestras (<50)                jupiter  53 muestras (<60)
```

El caso de `beta1` es el que hay que entender: **AUC 0,800 negado** porque la
tasa base del propio nodo da 0,899. En palabras del motivo, *«el modelo dice QUÉ
nodo, no CUÁNDO — eso es un mapa de peligrosidad, no detección de
precursores»*. Y confirma por otra vía el diagnóstico que lleva escrito
`test_fantasma_alfa1_kp_cero` sobre el `.onnx` del 4-oct.

### El lag: el tiempo no se perdía al calcularse, se perdía sin calcularse

El operador preguntó dónde se pierde el tiempo de anticipación. La huella estaba
en los datos y era del revés de lo que haría un muestreo: cubos pequeños
completos y grandes vacíos.

```
beta1 SISMO_M4       417 exigibles ->  9 con lag    <- topado
beta1 SISMO_M4_obs    20 exigibles -> 20 con lag    <- cabe entero
```

Dos defectos en el mismo bucle: el tope se contaba en **sondeos de evento** y
cada firma gasta hasta 3, así que «150» eran **50 firmas** por (bot, clase) y el
resto se saltaba con un `continue` **sin log**; y la rejilla **paraba en 24 h**
cuando el emparejamiento no cae al acercarse al evento, sube (33 % a 336 h,
58 % a 24 h, 80 % a 1 h). Cobertura: **159/982 → 978/982**.

Después vino el nulo, y cambió la lectura: solo **315 de 978 (32 %)** no
emparejan en ventanas de calma **del mismo nodo**. El nodo es la clave —con un
nodo al azar daba 69 %, porque medía «otro nodo» y no «no antes del evento»— y
encaja con la compuerta: la firma codifica sobre todo QUÉ nodo, no CUÁNDO.

### Los avisos: el ✅ era «el archivo existe»

El digesto horario cerraba con `✅ ALFA1 (791KB)` y la única comprobación era
`os.path.exists`. Los ocho `.onnx` en disco no habían pasado nunca por la
compuerta. Ahora enseña la habilidad **medida** en tres estados —aprobado,
negado con su motivo, y **sin medir**— y lleva la vara del Juez, que era la
última superficie donde no aparecía ninguna de las dos cifras.

### Todo con `--user`

Las dos unidades de sistema que quedaban se migraron (abajo el detalle). En
`/etc` solo quedan launcher y watchdog **enmascarados a propósito**.

### Reportes y tablero

Las cuatro superficies que pintan el lag por clase se actualizaron, porque
`tbl_lag_anticipacion` **cambió de significado** sin cambiar de nombre
(`SISMO_M4` 8,8 d n=1.402 → 8,4 d n=448) y ninguna lo decía. Quedó como regla
de dato 5 del tablero. Panel nuevo «Compuerta de habilidad» en MODELOS y los
cuatro KPI del nulo en PADRE+JUEZ.

### Dos lecciones de proceso

**Cinco tests se pusieron rojos DOS VECES sin que el comportamiento cambiara**,
por estar anclados a cadenas literales del código fuente —una ventana fija
`fuente[i-600:i+2000]` y un `SELECT` que se partió en líneas al añadirle
columnas—. Es buena parte de la sensación de «arreglo algo y se descompone otra
cosa»: no era el código, era el instrumento. Regla dura 12.

**Y un `(x or 0) > 0` que escribí yo** metía el `NULL` de «no se midió el nulo»
en el saco de «específico», justo en la línea que le dice al operador cuánto
tiempo tiene. La regla 7 muerde también al que la escribió.

### (Noche) El digesto no llegaba: 16 avisos rechazados por un `(<50)`

El log del Concilio —que es quien despacha la cola— llevaba desde las **13:49**
repitiendo `Can't parse entities: unsupported start tag "50)"` y, tras cinco
reintentos, `aviso descartado`. **16 mensajes del Sentinel perdidos** hasta las
18:25, digesto horario incluido. La causa se escribió hoy mismo: el entrenador
pone `NO se reentrena: 38 muestras reales (<50) y sin prior` en
`models_meta.json` y `get_model_status` lo interpolaba en HTML sin escapar, así
que Telegram leía `<50)` como etiqueta y devolvía 400 sobre el mensaje
**completo**. No llegaba mal formateado: no llegaba.

Y había un test con ese texto exacto (`test_aviso_habilidad_modelos`, línea 138)
que pasaba, porque comprobaba que el motivo apareciera y nunca que la salida se
pudiera parsear. Regla 12 en la superficie que más se lee.

- **`sanear_html_telegram()`** en `infrastructure/api/telegram.py`, el único
  punto de salida del repo: deja intactas las etiquetas que el Bot API admite,
  traduce `<br>` a salto de línea —`br` **no** está entre ellas— y escapa
  cualquier otro `<` o `&` suelto. Lo que entra sano sale idéntico.
- **`_esc()` en el origen**: `motivo`, `source` y el texto de la excepción en
  `consenso_vigilante`. La puerta es la red, no la excusa.
- **Barrido de hermanas**: `cimatica_consistente` usaba `<br>` ×4, que habría
  muerto igual, y `event_class`/`clave`/`ambito`/`bot_name` entraban sin escapar
  en cuatro plantillas. `_strip_tags` deshace las entidades, porque `plain`
  significa «sin marcado».
- **El recorte iba después del saneo** y podía partir un `<b` por la mitad:
  ahora recorta primero y sanea al final. Y cubría solo la rama legada, cuando
  por la cola va todo: un mensaje de más de 4.096 lo rechaza Telegram con el
  mismo final que el `(<50)`.
- 14 tests nuevos (`test_html_telegram_parseable.py`) con un validador que
  aplica la regla del parser, no la ortografía. 4 mutaciones, 4 pruebas caídas.

Verificado de punta a punta: el digesto muerto de las 18:25, pasado por el
saneador y enviado por `send_alert`, lo registró el bot como `Alert sent` a las
**18:40:21**. El despacho es un `Type=oneshot`, así que el arreglo quedó vivo sin
reiniciar nada.

### (Noche) El FRP no es la contraseña, es el reloj --- y dos venv que me engañaron

`The token is not yet valid (iat)` llevaba dando por caída la anomalía térmica
con el rótulo «fallo de autenticación». Medido entero: el texto sale de **PyJWT**
(`jwt/api_jwt.py:481`), o sea validación **local** dentro de eodag; el `iat` del
vale nace **+4,9 s en nuestro futuro** y este reloj va ~5 s por detrás de
Copernicus y de Cloudflare (contra su cabecera `Date`); y el servidor **sí**
acepta ese vale --- una petición directa con `Bearer` llega hasta devolver 416
por la cabecera `Range`. PyJWT compara `iat` con el reloj local sin margen, así
que con 5 s de atraso todo vale recién emitido nace en el futuro. **El arreglo
de fondo era sincronizar el reloj, y **no con `hwclock -s`** (esto es WSL2: no hay
RTC propio, la hora la pone el host y es el atrasado; además `hwclock` no existe en
esta instalación). **RESUELTO a las 20:34**: el servicio de hora de Windows estaba
`Stopped`/`Manual` --- de ahí que `w32tm /resync` devolviera `0x80070426` ---, se
arrancó y se dejó en `Automatic`, y WSL recogió la hora del host solo. Desfase
**−6/−7 s → 0/−1 s**, y el FRP pasó a leer **11 productos de 3 zonas sin un solo
rechazo** (20:34:22), contra 6 productos y 5 rechazos en el ciclo anterior.
Detalle en la bitácora §10.1.

Aquí se quitó el daño colateral: eodag lo envuelve en `AuthenticationError`,
`_es_fatal` lo daba por fatal y eso **cortaba las descargas del ciclo entero**
por un producto. Ya no. Verificado en vivo tras el reinicio: `se cortan las
descargas` desapareció del journal. **Sin reintento**: probado con 3 s y 10 s, no
recupera, y pedir vales seguidos hizo que Copernicus devolviera **403** en el
endpoint de tokens. 10 tests, 1 mutación.

**Y una corrección a mí mismo, que es la parte instructiva.** Corrí la suite con
`sentinel_omega/.venv` creyendo que era el entorno del proyecto, y «encontré»
cuatro fallos más. Hay **dos venv** y el servicio usa `workspaces/.venv` (lo dice
su `ExecStart`): el otro es un resto huérfano que nadie referencia y al que le
faltan eodag y pytrends. Con el bueno fallan **2**, las de `alfa1`, rojas a
propósito --- la cifra que la bitácora decía desde el principio. Lo que afirmé y
retiro: que `pytrends` y `h5py` no estuvieran instalados (lo están), y sobre todo
que **«la fuga de la marea sigue roja después del rebuild»** --- es falso, esos
dos tests pasan con el venv bueno. Queda en pie que `h5py` estaba **sin
declarar** en `requirements.txt` aunque el código vivo lo importa, y ahí queda
escrita la trampa de los dos venv. Regla 12 un piso más abajo: ancla el
instrumento antes de anclar el test.

**El recuento de tests de esta entrada era correcto** (2 rojos); lo que estaba mal
era mi medición. **La invocación decide**, y las cifras intermedias de esta
entrada (6 y 15) eran de un árbol a medio arreglar. Vuelto a medir al cierre
del día, con el árbol limpio en `a7f6c1b`:

```
cd /home/deamon/workspaces && .venv/bin/python -m pytest sentinel_omega/tests/ -q
  -> 1.309 recolectados, 2 rojos          <- LA BUENA (el venv del servicio)

cd sentinel_omega && PYTHONPATH=. ../.venv/bin/python -m pytest tests/ -q
  -> 11 rojos                             <- nueve fantasmas de rutas relativas
```

El `AGENTS.md` del home prescribía la segunda y daba por roto lo que no lo
estaba. Corregido ahí, en `workspaces/AGENTS.md` y en `CLAUDE.md`. La lección
dura es la del instrumento (regla 12) y no el número: **si un test cae con
`ModuleNotFoundError`, mira el intérprete antes que el código.**

---

## [Unreleased] - 2026-10-08 - Todo con `--user`: se retiran las últimas unidades de sistema

Sin push. Branch `local/recuperacion-datos-2026-09`.

Quedaban **dos** unidades de sistema vivas en `/etc/systemd/system`, y no por
necesidad técnica: ninguna de las dos pide privilegios. Medido:

| Unidad en `/etc` | Estado | Por qué estaba ahí |
|---|---|---|
| `sentinel-omega-dashboard.service` | `enabled`, **corriendo** (PID 541) | Streamlit en el 8510, un puerto alto. Antigüedad, nada más. |
| `sentinel-omega-onnx-retrain.timer` | `enabled`, esperando (dom. 03:00) | `install.sh` **imprimía** la línea `sudo install … /etc/systemd/system/`. |

Esa línea de `install.sh` era el único sitio donde el root se reintroducía solo
tras cada instalación. El `onnx-retrain` cargaba además tres líneas de andamio
que solo existían por ser unit de sistema --- `User=`, `XDG_RUNTIME_DIR` y
`DBUS_SESSION_BUS_ADDRESS`, para que su `ExecStartPost` encontrara el bus del
gestor de usuario. Como unit de usuario las tres sobran, y **`User=` es
inválido** en el gestor de usuario.

### La copia de usuario del dashboard estaba rancia y no podía arrancar

Había ya un `sentinel-omega-dashboard.service` a nivel usuario, y dos defectos:

1. `WantedBy=multi-user.target`. **Un gestor de usuario nunca alcanza los
   objetivos de sistema**, así que el enlace caía en
   `~/.config/systemd/user/multi-user.target.wants/` y la unidad figuraba como
   `enabled` sin poder arrancar jamás en boot. El propio
   `sentinel-omega-rutinas.timer` lo advierte en un comentario; esta copia era
   la que no se había corregido. El directorio ya no existe.
2. Apuntaba al puerto **8501**, que hoy ocupa un **contenedor Docker** ajeno a
   Sentinel. Arrancarla habría chocado. Ahora es el 8510 del repo, que es el
   que documenta `CLAUDE.md` y el que de verdad corre.

### La discrepancia del `0.0.0.0`, resuelta

Al medir salió que el archivo de `/etc` decía `--server.address 0.0.0.0` pero
el proceso vivo escuchaba en `127.0.0.1`. No era un archivo rancio: había un
**drop-in de endurecimiento deliberado**,
`/etc/systemd/system/sentinel-omega-dashboard.service.d/localhost.conf`
(14-sep), que anulaba el `ExecStart` entero —

> `# Harden: bind Streamlit to loopback only (was 0.0.0.0)`
> `# Remote access: SSH tunnel or existing cloudflared — not open LAN bind`

— así que el `127.0.0.1` que conserva la unit de usuario no es una elección
nueva: es esa decisión, ya tomada, y el repo la tenía bien desde entonces. El
directorio `.d` queda huérfano (su unidad vive ahora en el nivel de usuario) y
es redundante, porque el `127.0.0.1` va escrito en la unit.

### Tres restos que salieron al retirar las dos primeras

`rutinas.timer`, `rutinas.service` y `scheduler.service` siguen en `/etc`.
Están `disabled`, así que hoy no duplican nada, **pero el preset de
`rutinas.timer` es `enabled`**: un `systemctl preset-all` lo encendería y
volverían las rutinas corriendo dos veces —root y usuario—, que es el bicho de
los cuatro digestos por hora del 7-oct entrando por otra puerta. Un archivo
inerte con el preset a favor no es un archivo inofensivo. El guardia de
`install.sh` ya los nombra.

### Y el guardia, para que no vuelva

`install.sh` ya tenía el patrón: así se migró `mantenimiento` el 30-sep. Ahora
instala y habilita `onnx-retrain` y el Streamlit como unidades de usuario, y
avisa de cualquier gemela que siga en `/etc` preguntando por el **archivo**
--- no por `is-enabled`, que para estos nombres ya responde por la unidad de
usuario. También se corrigió `WantedBy` en `barrido`, `disciplina` y
`scheduler`, que habrían repetido el mismo enlace muerto.

Las nueve unidades se suben y bajan con `systemctl --user`. Las de sistema que
quedan en `/etc` son las dos **enmascaradas a propósito** (launcher y watchdog,
para que no haya un segundo Sentinel como root).

## [Unreleased] - 2026-10-07 - La causa de los falsos positivos, la cadencia del digesto, y una revisión de las pruebas

Sin push. Branch `local/recuperacion-datos-2026-09`, 6 commits.
Bitácora completa con las mediciones y la forma de reproducirlas:
**`estado/BITACORA_2026-10-07.md`**.

Resumen de lo que cambió de criterio, porque es lo que más importa de este día:
el fantasma de `alfa1` **no** había vuelto (la asimetría es 1,016×, no >2×), el
§20.2 de la bitácora del 26-sep que se citó como vigente es **historia**, y los
159 falsos positivos tienen **una sola causa común** a los nueve bots --- el
objetivo del entrenamiento, no los umbrales.

### El timer de rutinas está ENCENDIDO (corrección de documentación)

Las notas del 4-oct dicen «timer de rutinas apagado». Era cierto entonces: se
apagó mientras se trabajaba y **se volvió a levantar al terminar los cambios**
(operador, 7-oct). Lo que seguía desactualizado era el documento, no el
servicio. `systemctl --user list-timers` lo da `active`, disparando cada 15 min.

### Despachaba 4 digestos por hora con `TG_DIGEST_MINUTES=60` declarado

Medido en el journal del 7-oct: **54 digestos en un día, 4 por hora exactas**.
La cadena necesita sus cuatro eslabones:

1. `sentinel-omega-rutinas.timer` corre cada 15 min (`OnUnitActiveSec=15min`).
2. `deploy/rutinas_locales.sh` pone compuerta de minuto a todos sus bloques
   **menos al último**, que es `enviar_correos.py`.
3. Ese llamaba `flush_digest(force=True)`, y `force` salta el temporizador ---
   lo dice su propio docstring: «force ignores the timer».
4. Y debajo, el eslabón que hacía inútil arreglar solo el 3: `last_digest_ts`
   nacía en `0.0` y **no se guardaba en ninguna parte**. El servicio es
   `Type=oneshot`, o sea un proceso nuevo cada corrida, así que la compuerta de
   `maybe_flush` no podía cerrarse nunca.

`launcher.py` no sufría el bicho: es un proceso largo con un único
`get_vigilante()`, y ahí la marca en memoria sí funcionaba. Por eso el defecto
solo se veía en el teléfono del operador, nunca en el código.

Tercera aparición de la misma familia, tras el `days` de `fetch_kp_index` y el
`confidence_threshold` de los ocho ONNX. La variante de aquí es más fina: el
mando **sí** se leía, pero el estado contra el que se comparaba moría con el
proceso, que para el caso es lo mismo.

### Arreglo

- `consenso_vigilante.py`: la marca se persiste en `data/estado_digesto.json`
  (escritura atómica), se lee en el `__init__`, y solo avanza **si el digesto
  salió de verdad** --- si Telegram falla, la corrida de los 15 min siguientes
  reintenta en vez de callarse una hora. Guardas medidas: marca en el futuro
  (reloj que salta) y marca ilegible mandan digesto y lo **dicen** en el log.
  No va en la base: esta clase la abre `mode=ro` en todas sus rutas y
  producción tiene un escritor vivo 24/7.
- `deploy/enviar_correos.py`: `force=False`. Quien decide la cadencia es
  `maybe_flush` contra la marca, no el llamador. `rutinas_locales.sh` **no se
  tocó**: una sola fuente de verdad, y es `TG_DIGEST_MINUTES`.
- `deploy/enviar_correos.py`: el heartbeat imprimía `ok` cuando se quedaba en
  el buffer --- y en un `oneshot` el buffer muere con el proceso, así que NO
  llegaba a Telegram. `dispatch` cuenta «buffered» como éxito
  (`alert_service.py:359`). Ahora dice cuál de las dos cosas pasó.

### El arreglo casi se convierte en un silencio nuevo

Al persistir la marca, **la suite empezó a escribir la de producción**. Medido:
se movió el archivo a un lado, se corrió la suite y reapareció con el sello de
la corrida. Ningún mensaje real salió (el transporte estaba sustituido), pero
el estado sí se tocaba: una corrida de tests podía dejar al operador una hora
sin reporte. El guardarraíl de `dry_run` no basta y no puede bastar --- un test
tiene derecho a usar `dry_run=False` con el transporte sustituido.

Cerrado con `sentinel_omega/tests/conftest.py` (primer conftest del proyecto):
fixture de sesión que apunta `TG_DIGEST_STATE` a un temporal. Se descartó que
el código de producción mirara `PYTEST_CURRENT_TEST`: no debe cambiar de
comportamiento según quién lo corre. Quien se aísla es el instrumento.

### Verificado de punta a punta (regla 0)

En el despachador real, en procesos separados, sin mandar nada:

```
marca de hace  5 min → «digesto aún no toca: faltan 55 min de los 60 declarados»
marca de hace 61 min → «DIGESTO_HORARIO enviado»
```

Suite: 1.181 pasan, 8 se saltan, 3 fallan --- los tres de antes
(`test_producto_en_cache_no_se_vuelve_a_bajar` y los dos de
`test_fantasma_alfa1_kp_cero`), ninguno nuevo. 23 pruebas nuevas.

### Pendiente anotado, no tocado

`send_alert` devuelve `True` por la rama de `alert_queue` sin comprobar
credenciales: «enviado» significa **encolado** en la cola del Concilio
(`~/consensus-expert-agent/alert_queue.py`), que drena su `telegram_bot.py`. Si
ese bot está caído, Sentinel sigue creyendo que mandó. Es del proyecto
compartido, no de aquí.

### La causa de los 159 falsos positivos: el objetivo del entrenamiento

Bitácora: `estado/BITACORA_2026-10-07.md` §2. No está en los umbrales ni en el
consenso, sino en `models/train_onnx_from_db.py`: `y_conf` sale de
`EVENT_CLASS_LABEL[clase] + ESTADO_BOOST[estado]`, o sea **no es función de
`X`**. Con el 94 % de las firmas en M4/M5 el objetivo vive en 0,60-0,75 y el
bosque devuelve la media. Seis de ocho bots salen con el 96-100 % de sus
muestras etiquetadas como alarma.

**B1 (negativos reales) es viable y no da habilidad.** Hay material --- el
72,8 % de los pares (hora, nodo real) al azar son calma y el 100 % da vector
extraíble --- pero con corte **temporal** 70/30 y objetivo real:

| objetivo | alfa1 | beta1 | beta2 | delta | loki | omega |
|---|---:|---:|---:|---:|---:|---:|
| por nodo, M≥4.5 en 190 h | 0,467 | 0,470\* | 0,515 | 0,504 | 0,465 | 0,470 |
| global, M≥6.0 en 24 h | 0,511 | 0,482 | 0,498 | 0,512 | 0,513 | 0,510 |

\* sin sus `sismo_*`. Con ellos, 0,814 --- y **un solo rasgo**,
`sismo_count_win`, da los mismos 0,814: es agrupamiento de Omori, no un
precursor, y comparte catálogo y nodo con el objetivo. `alfa2` y `jupiter` no
tienen cobertura antes de ago-2026, así que B1 no les aplica; `delta` solo desde
2014.

Tasas base medidas, para no volver a usar una vara degenerada: M≥4.5/72 h
global = **100,0 %** (inservible), M≥6.0/24 h = 30,6 %, M≥6.5/72 h = 28,8 %,
M≥7.0/168 h = 23,0 %.

### `alfa1`: el fantasma NO volvió --- corrección de diagnóstico

Se estuvo a punto de apagar su modelo por un motivo inexistente. El fantasma es
**asimetría**, no «alarmar» (bitácora del 26-sep §22.2): antes 2,3×, después
1,06×, y medido hoy con el modelo del 4-oct **1,016×** con los huecos de
densidad de ese ciclo y **1,002×** con densidad real. La fuga de procedencia
sigue cerrada en los nueve bots y `test_la_asimetria_del_fantasma_desaparecio`
está en verde.

Lo que sí pasa es nivel: 19 `WATCH` de 28 ciclos vivos, su regla `neutral`
28/28, y el Juez da **18 falsos positivos contra 1 acierto**. El tramo de más
confianza (0,70-0,75) es **8 de 8 falsos**, así que ningún corte sobre la
confianza ayuda --- queda retirada la propuesta de subir el umbral (regla dura
8: un umbral que deja pasar ~0 % no discrimina). Y no es solo de `alfa1`: en la
misma ventana `alfa2` 27 FP, `beta1` 24, `delta` 26, `loki` 26, `omega` 27,
`padre` 26, todos con 1 acierto.

**Corrección a la bitácora del 26-sep §20.2**, que se citó como vigente y es
historia: `_aplicar_modelos` **ya no** sustituye sin condición. Verificado
contra el código: `gana_el_modelo = float(conf) >= regla_conf`, puesto el 27-sep
por decisión del operador. Para `alfa1` da igual, porque su regla emite
**0,3000 constante** y el modelo gana 29/29 por definición.

### Revisión de las pruebas que gobiernan los modelos

Cinco defectos (bitácora §4). Los dos que más costaron: el mensaje de
`test_fantasma_alfa1_kp_cero` mandaba a buscar una fuga inexistente, y
`test_al_bot_callado_no_se_le_pregunta` **se saltaba** desde que
`RASGOS_CON_FUGA` quedó vacío, dejando a oscuras la rama de silenciado ---
nadie vigilaba que el tapón desapareciera. Más una **tautología** propia
(`test_el_corte_cae_en_el_hueco...` comparaba literales del mismo archivo) y
`_rasgo_requerido_ausente` sin ninguna prueba, estando viva para `beta2`. Y
`test_producto_en_cache_no_se_vuelve_a_bajar` llevaba once días en rojo por
**fecha de caducidad**: `copytree` conserva la mtime y `_podar_cache(7)` se
llevaba la caché que la prueba acababa de montar.

### Higiene de git

`sentinel_omega/data/` **no** está ignorada como carpeta, aunque la regla 3 de
`AGENTS.md` lo diga: solo `*.db`, `*.pid`, `cache/` y `backups/`. Se ignoran
`estado_digesto.json` (estado por máquina que crea el arreglo de la cadencia;
commitearlo silenciaría el digesto una hora en un checkout nuevo),
`schumann_sos70/`, `reporte_padre_*.txt` y `*.bak_*`. Y `egg-info` sale del
índice: `*.egg-info/` estaba en `.gitignore` desde el 27-sep pero los archivos
seguían rastreados de antes de la regla --- existía y nunca se había aplicado.

Entran al repo tres notas que llevaban días fuera, escaneadas por secretos:
`CANAL_CLAUDE.md`, `PROPUESTA_LEGACY_2026-09-27.md` y
`estado/MURO_FINANCIERO_2026-10-04.md` (al que el `CHANGELOG` ya hacía
referencia estando sin rastrear).

### El muro, medido

`FINANCIERO` **0 de 7.830 registros**; los **5 muros nunca simultáneos** (4
ocurre el 0,3 %); breach del 29 % histórico al **3,8 %** esta semana, efecto
medible de apagar los seis ONNX. De 712 detecciones, 490 son `SEISMIC_CLUSTER`
(246) y `SILENT_TRIGGER` (244). Trampa que volvió a morder:
`TBL_MURO_EVENTOS.timestamp` y `TBL_JUEZ_AUDITORIA.timestamp` son **epoch
REAL**, así que un `datetime('now','-7 days')` devuelve cero filas sin error.

### Ramas y worktrees: nada pendiente fuera de la rama viva

`/home/deamon/workspaces-dev` **no es un worktree**: es otro repositorio parado
en `2d7e246` (**2026-08-22**), que **es ancestro** de la rama viva --- 245
commits por detrás. Sus ~86 entradas «sin commitear» son un árbol de septiembre:
`layer_runners.py` con 282 líneas y **sin `_aplicar_modelos`**, `onnx_config.py`
sin una mención de `jupiter`. Commitearlo habría sido una regresión de 245
commits disfrazada de recuperación. `local/recuperacion-datos-2026-10` es una
copia paralela que va detrás, y el cambio suelto del worktree de julio ya está
superado. El registro de worktree de `dev` está roto (`git worktree prune`).

## [Unreleased] - 2026-10-04/05 - Cortes, rebuild, muro vivo, CSV USGS

Sin push. Nota: `estado/CORTES_2026-10-04.md`. Branch `local/recuperacion-datos-2026-09`.

### Data / base

- USGS geojson (`usgs_catalogo`): upsert M≥4.5 → `tbl_eventos_sismicos_fuente` con `depth_km`, segmento, tipos, tsunami/alert/mmi/cdi/felt/sig. 215 769 filas; 1994–2025 con profundidad.
- Rebuild desde cero 4-oct (PID 597333) cerrado a las 17:55 CST: ~40 361 firmas, cimática ~189 933.

### Cortes y firma

- Observación desde M2.5; predicción/castigo desde M4.5; alerta sísmica M6/M7. Trasfondo USGS menor sigue en 3.3.
- Ventana previa en la firma (sin el sismo predicho). Claves ausentes no se inventan.

### Detector / reporte

- Tsunami/profundidad en precursor (scanner + pipeline).
- Blanco de reportes nuevos: M≥6 en 24 h. Contadores = ventana guardada. Nadie llama `es_blanco_del_reporte`.

### Muro por magnitud

- `entrenar_umbral_por_magnitud` + `calcular_umbral_muro` → `tbl_muro_umbral_magnitud`.
- Tabla (cálculo 4-oct 20:50): M4=2 (278), M5=1 (143), M6/M7 vacíos (13/3).
- Vivo: relee SISMO_M6 cada ciclo en solo lectura; vacío → corte **3**. PID launcher 2815744 desde 5-oct 08:17. Watchdog intacto. Timer de rutinas apagado.

### CSV backcast / topología

- Conserva `depth`/`type`/… del CSV FDSN. Topología mapea a `depth_km`/`event_type` dentro de `if not dry_run`.
- CSV no trae alert/mmi/…; eso sigue en geojson. Sin `--refetch` en este hilo.

### Tests

- `test_cortes_firma`, `test_muro_por_magnitud`, `test_tsunami_profundidad`, `test_reporte_blanco`, `test_csv_usgs_columnas`, `test_usgs_catalogo`.

### Explicitamente fuera

- ONNX, dashboard/mapas, SSN loader, push a remoto.


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


### Mapas — el globo mentía y los hex violaban el sistema (2026-09-28, tarde)

Sin commit, sin push. Rediseño de Map2D/Globe3D (`components/maps/`), verificado
en navegador real (Chromium headless + CDP, eventos de puntero): 0 errores de
consola, fichas de hover funcionando, aro de focus desde el ranking, Principal
sin regresión.

- **El globo prometía lo que no dibujaba.** El caption decía «el tamaño y color
  de cada nodo reflejan su saturación» y `Globe3D` ignoraba `sat`/`medido` por
  completo: puntos fijos por tipo. Ahora el radio crece con la saturación, el
  aro va en la rampa de riesgo y un nodo sin lectura se dibuja hueco y neutro.
- **Hex sueltos fuera del sistema de diseño.** `#5e6ad2` (indigo decorativo)
  para nodos y `#ff1744` para TODOS los sismos violaban «el color saturado
  significa riesgo y nada más». Ahora: tipo = categoría en `--color-serie-*`,
  carga = rampa calma→atención→aviso, sismo = magnitud (M≥5 aviso, M≥6
  crítico) con opacidad por recencia (0.95 recién, 0.35 a los 60 días).
- **Datos que la API daba y el mapa tiraba:** `depth_km` y `timestamp` de cada
  sismo viajan a la ficha de hover («M4.9 · 71 km de profundidad · 2 km SW of
  Sakai, Japan · hace 2 h»); cada nodo muestra región y fecha de lectura. Meta
  honesta: «últimos 60 de 1.975 sismos M≥4.5» en vez de insinuar que lo
  visible es todo el catálogo.
- **`Number(nd.lat)` con `null` es `0`, no `NaN`:** un nodo sin coordenadas
  pasaría el filtro `Number.isFinite` y caería en (0,0). Guard explícito
  `nd.lat == null ? NaN : Number(nd.lat)` (hoy 0 nodos lo sufren, pero el pozo
  estaba abierto).
- Mundo compartido (`maps/shared.tsx`): costas reconocibles + islas (Japón, GB,
  Madagascar, NZ, Indonesia, Filipinas…) en vez de 6 manchas de 15 vértices;
  leyenda única para ambos mapas con cada codificación explicada.
- Globo: canvas nítido (devicePixelRatio + ResizeObserver), auto-rotación en
  reposo que se pausa al arrastrar o hacer hover y respeta
  `prefers-reduced-motion`; tooltip con hit-test al pasar el cursor.
- Mapas 2D: graticule con etiquetas de latitud, ficha bajo el mapa al hacer
  hover (altura fija, sin salto de layout); hover en el ranking «Nodos con más
  tensión» marca el nodo con aro punteado en 2D y 3D.
- Retrocompatible: Principal/Loki no pasan `sat`/`medido` y siguen viendo
  puntos por tipo como antes.

### Verified (mapas)

- `npx tsc -b` limpio · `npm run build` 344 KB / 107 KB gzip.
- Chromium headless + CDP con `Input.dispatchMouseEvent` (Radix Tabs exige
  eventos reales): Mapas renderiza 284 círculos SVG (125 nodos + 37 aros de
  carga + 120 de sismos + Tlaxcala) y canvas del globo; leyendas y fichas
  presentes; meta «últimos 60 de 1.975»; **0 errores de consola**; Principal
  sin regresión (207 círculos). El aro de focus se probó tras
  `scrollIntoView` — el primer intento falló porque el ranking quedaba bajo el
  pliegue del viewport: era el harness, no el código.

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
