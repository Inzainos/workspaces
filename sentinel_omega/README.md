# Sentinel Omega v2.5

**Plataforma de deteccion de precursores de eventos naturales**

Sentinel Omega monitorea en tiempo real datos geofisicos, atmosfericos, solares, oceanicos y financieros para detectar precursores de terremotos, erupciones volcanicas, tormentas solares, tsunamis y otros eventos naturales de alto impacto.

> Sucesor de la familia de bots TITAN V32/V46/V53.
> Autor: Elan Zainos Corona — Fractal Core Research

---

## Objetivo del Proyecto

El sistema busca resolver un problema fundamental: **detectar senales precursoras de eventos naturales con suficiente anticipacion para permitir alertas tempranas**. A diferencia de los sistemas de alerta sismica convencionales que solo reaccionan despues del evento, Sentinel Omega monitorea correlaciones multi-dominio (geofisico, atmosferico, solar, oceanico y financiero) para identificar patrones que historicamente preceden a eventos de gran magnitud.

La plataforma integra datos de 10+ fuentes publicas en tiempo real y aplica un framework de consenso jerarquico donde agentes especializados votan con perdida asimetrica: el costo de no detectar un evento (miss) se penaliza 10x mas que una falsa alarma.

---

## Hallazgos e Innovacion

### 1. Formula Fantasma (TITAN V32)

El indice Fantasma es una funcion compuesta que correlaciona variables solares, geomagneticas y atmosfericas para producir un score de riesgo precursor:

```
fantasma = (abs(Bz)^2) + (viento x 0.02) + (Schumann_WPC x 1.5)

Modificadores post-core:
  + Presion atmosferica (< 1008 hPa -> hasta +3.0)
  x Kp storm (>= 5 -> hasta x1.5)
  + LOD anomaly (> 0.5 ms -> hasta +2.0)
```

**Hallazgo**: La componente cuadratica del Bz (campo magnetico interplanetario norte-sur) es el predictor mas fuerte. Valores de Bz < -10 nT generan contribuciones Bz^2 > 100 puntos, disparando directamente el umbral CRITICAL. Esto se alinea con la observacion empirica de que perturbaciones geomagneticas severas (Bz fuertemente negativo) preceden actividad sismica inusual en ventanas de 48-96 horas.

| Nivel    | Rango   | Interpretacion                                   |
|----------|---------|--------------------------------------------------|
| LOW      | < 5     | Actividad de fondo normal                        |
| MODERATE | 5 - 15  | Senales elevadas, monitoreo activo               |
| HIGH     | 15 - 30 | Precursores multiples, alerta preventiva         |
| CRITICAL | >= 30   | Correlacion multi-dominio, alerta inmediata      |

### 2. Filtro Fourier-Schumann (Innovacion Beta-1)

El agente Beta-1 aplica un filtro armonico al espectro FFT de datos geomagneticos (serie temporal de Kp):

- **Armonicos de Schumann**: 7.83, 14.3, 20.8, 27.3, 33.8 Hz
- Los datos geofisicos se muestrean en intervalos de horas, no Hz directamente. El filtro identifica que bins de frecuencia son **sub-armonicos** de las resonancias de Schumann
- Bins no-resonantes se atenuan al 10%, preservando solo la energia resonante
- La frecuencia de Schumann en vivo (no hardcoded a 7.83 Hz) escala proporcionalmente los armonicos

**Hallazgo**: La **coherencia de Schumann** — ratio de energia en bins resonantes vs energia total — proporciona un indicador de acoplamiento Tierra-ionosfera. Coherencia > 0.3 combinada con excitacion activa produce la senal WATCH, un estado intermedio entre NEUTRAL y ALERT que indica "precursor potencial, monitorear de cerca". Este descubrimiento emergio de la correlacion entre excitaciones anomalas en la resonancia Schumann de Tomsk (Rusia) y actividad sismica significativa 48-72 horas despues.

### 3. Muro de los 5 Eventos (Correlacion Cruzada Multi-Dominio)

La innovacion central es que ningun precursor individual es confiable — es la **correlacion simultanea** de multiples dominios lo que indica riesgo real:

| Muro | Dominio             | Precursores                                    |
|------|---------------------|------------------------------------------------|
| 1    | GEOFISICO           | Enjambre Sismico, Volcanico, Fantasma          |
| 2    | ATMOSFERICO         | Blue Jet, Sprite Rojo, Niebla Tule             |
| 3    | OCEANICO            | Tsunami, Huracan                               |
| 4    | SOLAR/GEOMAGNETICO  | Tormenta, Perturbacion, Schumann, Silent, GRB  |
| 5    | FINANCIERO/SOCIAL   | Correlacion Financiera                         |

**Breach**: Cuando >= 3 muros estan activos simultaneamente, el sistema declara un "breach" — indicando que multiples dominios independientes estan correlacionados, lo cual historicamente precede eventos significativos.

**Hallazgo**: La inclusion del muro FINANCIERO/SOCIAL es innovadora. Se observan correlaciones entre caidas abruptas en mercados financieros (VIX spike, crypto fear index alto, bolsa bearish) y eventos naturales dentro de ventanas de 72 horas. La hipotesis es que mercados sensibles capturan informacion agregada (comportamiento de aseguradoras, contratos de reaseguro, posiciones de commodities agricolas) que anticipa disrupciones.

### 4. Silent Trigger (Calma Precursora)

**Hallazgo contra-intuitivo**: Periodos de calma geomagnetica extrema (todos los valores de Kp < 2.0 sostenidos por 24+ horas) son precursores tan significativos como las tormentas. El "Silent Trigger" detecta esta calma anomala. La ausencia de perturbacion es, en si misma, una senal.

### 5. Topologia de 125 Nodos con Saturacion

El sistema modela la Tierra con 125 nodos de monitoreo basados en la grilla UVG Becker-Hagens:

| Tipo        | Cantidad | Descripcion                                    |
|-------------|----------|------------------------------------------------|
| Real        | 50       | Zonas sismicas reales (Mexico + Ring of Fire)  |
| Ghost       | 50       | Nodos fantasma inferidos de gaps sismicos      |
| Geobattery  | 25       | Zonas de acumulacion electroquimica            |

**Hallazgo**: Los nodos "ghost" — posiciones inferidas donde no hay monitoreo pero la topologia sugiere acumulacion de estres — han mostrado ser zonas de riesgo subestimado por redes sismicas convencionales. Los nodos "geobattery" modelan zonas donde corrientes teluricas y diferencias de potencial electroquimico en el subsuelo pueden actuar como acumuladores de energia. La saturacion de un nodo (capped a 1.0 por trigger SQL) indica zona de maximo estres acumulado.

La matriz estatica UVG-125 se carga en RAM al importar (`geometria_uvg.py`) y proporciona lookup O(N) de nodo mas cercano para mapear sismos a nodos.

### 6. Perdida Asimetrica en Consenso Jerarquico

El Padre usa perdida asimetrica en el consenso:

```
Costo de miss   = 10 x peso_base
Costo de falsa  =  1 x peso_base
```

**Innovacion**: El sistema prefiere sobre-alertar a sub-alertar. Un 10% de falsas alarmas es aceptable si el sistema captura el 95% de eventos reales. Esto invierte la logica de la mayoria de sistemas de alerta que optimizan para minimizar falsas alarmas.

### 7. Validacion de Asertividad (V46 Lineage)

El tracker de asertividad compara predicciones contra eventos reales del catalogo USGS usando distancia euclidiana dentro de un radio de 5 grados:

- **Hit rate**: Predicciones confirmadas por eventos M>=4.5
- **Miss rate**: Eventos que no fueron predichos
- **False alarm rate**: Predicciones sin evento correspondiente

---

## Arquitectura — 6 Agentes, Sistema Unico

```
Orchestrator -> GeodynamicLayerRunner -> 6 Agents -> Padre Consensus
|
+-- Alfa-1 (Geodynamic: Bz, solar wind, seismic) — 30yr training
|       ^ validates
+-- Alfa-2 (Satellite: ESA Sentinel) — 16yr training
|
+-- Beta-1 (Schumann/cymatics/energy released) — 30yr training  <- HEARTBEAT
|       ^ validates
+-- Beta-2 (Air chemistry/atmospheric) — 16yr training
|
+-- Delta  (Crypto + Bolsa + humor de la tierra) — 10yr training
|
+-- Padre  (Hierarchical cross-family validator)
        +-- TITAN V32 Fantasma Risk Index
        +-- Precursor Scanner (15 types)
        +-- Muro de los 5 Eventos
```

**Jerarquia**: Agentes #2 -> reportan a #1 -> Padre valida entre familias.
**Schumann es el heartbeat**: Todo se correlaciona contra la resonancia Schumann (Beta-1).
Si Schumann esta perturbado junto con cualquier otra senal = precursor detectado.

**Familias**:
- `space_weather`: Alfa-1, Alfa-2
- `schumann_cymatics`: Beta-1, Beta-2
- `financial_sentiment`: Delta

**Consenso requiere**: >= 2 familias activas + >= 2 alertas + schumann_correlation > 0.3

### Ciclo del Orquestador

1. **GeodynamicPipeline** obtiene datos para todos los agentes (alfa1, beta1, beta2, delta, alfa2)
2. **Fantasma V32** calcula riesgo precursor de las senales crudas
3. **Hurricane data** se obtiene (non-blocking)
4. **Scanner** evalua 15 tipos de precursor contra datos del ciclo
5. **Muro de los 5 Eventos** evalua correlacion de 5 dominios
6. Todos los agentes ingestan + analizan -> senales
7. **Padre** evalua consenso (jerarquico + correlacion Schumann)
8. Alertas despachadas via Telegram + registro en SQLite

### Senales del Sistema

| Senal     | Significado                           | Uso                     |
|-----------|---------------------------------------|-------------------------|
| BULLISH   | Tendencia alcista (mercados)          | Delta (financial)       |
| BEARISH   | Tendencia bajista (mercados)          | Delta (financial)       |
| NEUTRAL   | Sin tendencia clara                   | Todos los agentes       |
| WATCH     | Excitacion coherente, monitorear      | Beta-1 (Schumann)       |
| ALERT     | Precursor confirmado, alertar         | Geodynamic              |
| NO_SIGNAL | Sin datos o sin analisis              | Todos los agentes       |

---

## 15 Tipos de Precursor

| #  | Tipo                     | Muro               | Ventana | Variables Clave                       |
|----|--------------------------|---------------------|---------|---------------------------------------|
| 1  | Resonancia Schumann      | Solar/Geomagnetico  | 72h     | schumann_hz, activity_pct             |
| 2  | Silent Trigger (Calma)   | Solar/Geomagnetico  | 48h     | kp_values (todos < 2.0 por 24h)      |
| 3  | Enjambre Sismico         | Geofisico           | 48h     | event_count, max_mag, cluster_radius  |
| 4  | Blue Jet                 | Atmosferico         | 72h     | humidity, temp, pressure, weather_id  |
| 5  | Sprite Rojo              | Atmosferico         | 72h     | humidity, pressure, weather_id (211)  |
| 6  | Niebla Tule              | Atmosferico         | 72h     | humidity, temp, visibility, wind      |
| 7  | Tormenta Solar           | Solar/Geomagnetico  | 96h     | xray_flux (>= 1e-5 W/m2 = M-class)  |
| 8  | Perturbacion Geomag.     | Solar/Geomagnetico  | 96h     | kp_mean (>= 5.0 = storm level)       |
| 9  | Huracan                  | Oceanico            | 120h    | distance_km, category                 |
| 10 | Tsunami                  | Oceanico            | 24h     | magnitude, depth (>= 7.0, < 70km)    |
| 11 | Inferencia ML            | —                   | 48h     | onnx_model_output                     |
| 12 | Gamma-Ray Burst          | Solar/Geomagnetico  | 168h    | xray_flux (>= 1e-4 W/m2)            |
| 13 | Precursor Volcanico      | Geofisico           | 72h     | so2_index, seismic_coupling           |
| 14 | Indice Fantasma          | Geofisico           | 72h     | fantasma composite score              |
| 15 | Correlacion Financiera   | Financiero/Social   | 72h     | fear_greed, vix, btc_change           |

---

## Framework Matematico (SNT)

Sentinel Omega utiliza la **Shadow Node Theory** exclusivamente como framework matematico — no como proposito del sistema. El modelo de ley de potencia describe relaciones de dominancia/subordinacion en sistemas complejos:

```
R(t) = a * t^b
```

| Regimen              | Exponente b | Interpretacion                             |
|----------------------|-------------|--------------------------------------------|
| Extreme              | > 2.0       | Satelizacion sin friccion                  |
| Roche Radius         | > 1.0       | Satelizacion rapida (punto de no retorno)  |
| Active               | > 0.3       | Satelizacion activa                        |
| Gradual              | > 0.05      | Satelizacion gradual                       |
| Equilibrium          | > -0.1      | Estado estable                             |
| Convergence/Leapfrog | <= -0.1     | Desacoplamiento / convergencia             |

Se aplica a:
- Ratios de dominancia financiera (BTC/ETH, SPY/QQQ)
- Intensidad geomagnetica (Kp trends)
- Gradientes de nodos topologicos

---

## Base de Datos (SQLite)

### Tablas Operacionales

6 tablas en `SENTINEL_OMEGA_PRO.db` con modo WAL y foreign keys:

| Tabla                    | Registros   | Proposito                                              |
|--------------------------|-------------|--------------------------------------------------------|
| TBL_PRECURSORES_COSMICOS | Por ciclo   | Snapshot: Bz, viento, protones, Kp, LOD, Schumann, fantasma, fase lunar |
| TBL_NODOS_TOPOLOGIA      | 125 fijos   | Nodos N-Body con conductividad, energia, saturacion    |
| TBL_HISTORICO_SISMICO    | Acumulativo | Catalogo USGS con deduplicacion por event_id           |
| TBL_DETECCIONES          | Por ciclo   | Log de precursores detectados con tipo, confianza, JSON |
| TBL_CICLOS               | Por ciclo   | Historial de ciclos: senal, consenso, riesgo, muro     |
| TBL_MURO_EVENTOS         | Por breach  | Breaches del Muro con correlacion y muros activos      |

### Tablas de Backcast Historico (1H resolution, 1994-2025)

| Tabla                      | Clave Primaria          | Proposito                                    |
|----------------------------|-------------------------|----------------------------------------------|
| tbl_clima_espacial_raw     | timestamp_blk           | NASA OMNI2: Bz, viento solar, Kp, protones  |
| tbl_astronomia_cinematica  | timestamp_blk           | LOD, fase lunar, distancia lunar, sicigia    |
| tbl_historico_sismico_raw  | (timestamp_blk, id_nodo)| Sismos USGS mapeados a nodos UVG-125        |
| tbl_psique_financiera      | timestamp_blk           | BTC precio, volatilidad (2014+)              |
| tbl_enjambre_telemetria    | (timestamp_blk, id_nodo)| Schumann resonancia por nodo                 |
| tbl_nodo_estado_dinamico   | (timestamp_blk, id_nodo)| Carga/tension por nodo (cap 1.0 via trigger) |

**Protocolo backcast**: ZERO datos sinteticos. Missing = NULL. LOCF solo desde registros reales.

**Triggers**: `trg_nodo_saturacion` (TBL_NODOS_TOPOLOGIA) y `trg_procesar_saturacion` (tbl_nodo_estado_dinamico) — cap automatico de saturacion/carga a 1.0.

---

## Dashboard (Streamlit + Plotly)

9 pestanas interactivas con datos en tiempo real:

| Tab | Nombre          | Visualizaciones                                                          |
|-----|-----------------|--------------------------------------------------------------------------|
| 1   | Precursor Risk  | Gauge fantasma, historial, waterfall de componentes, donut de riesgo     |
| 2   | Muro 5 Eventos  | 5 tarjetas de estado, radar de correlacion, timeline de activacion       |
| 3   | Scanner         | Tabla de detecciones, barras por tipo, histograma de confianza, stats    |
| 4   | Topologia       | Mapa mundial 125 nodos, ranking saturacion, conductividad vs energia    |
| 5   | Sismico         | Mapa sismico, histograma magnitudes, profundidad vs magnitud, regiones  |
| 6   | Schumann        | Tendencia Hz, actividad WPC, distribucion, Hz vs actividad scatter      |
| 7   | Layer Signals   | Consenso por capa, senales de agentes individuales                       |
| 8   | SNT Analysis    | Exponente de satelizacion, fits de ley de potencia                       |
| 9   | Ciclos          | Timeline fantasma + precursores, tasa de alertas, breach rate gauges    |

---

## Fuentes de Datos (APIs)

| Fuente           | Datos                                     | Auth      | Uso                  |
|------------------|-------------------------------------------|-----------|----------------------|
| NOAA SWPC        | Bz, viento solar, Kp, GOES X-ray, protones | Publico   | Alfa-1, Scanner      |
| USGS FDSN        | Catalogo sismico mundial                   | Publico   | Scanner, Asertividad |
| Tomsk SRF        | Resonancia Schumann (7.83 Hz)              | Publico   | Beta-1, Scanner      |
| IERS             | Length-of-Day (LOD)                        | Publico   | Fantasma             |
| ESA Copernicus   | Sentinel-1 SAR, Sentinel-2 multispectral   | Publico   | Alfa-2, Beta-2       |
| OpenWeatherMap   | Presion, temp, humedad, weather_id          | API Key   | Beta-2, Scanner      |
| NOAA NHC         | Ciclones tropicales activos                 | Publico   | Scanner (huracanes)  |
| CoinGecko        | Dominancia BTC, market caps                 | Publico   | Delta                |
| Binance          | OHLCV crypto                               | Publico   | Delta                |
| Yahoo Finance    | OHLCV acciones, VIX, ETFs                  | Publico   | Delta                |

---

## Estructura del Proyecto

```
sentinel_omega/
+-- launcher.py                          # Launcher — arranca el orquestador en ciclo continuo
+-- shutdown.py                          # Shutdown — detiene gracefully via SIGTERM/SIGKILL
+-- reboot.py                            # Reboot — stop + relaunch
+-- orchestrator.py                      # Orquestador maestro — ejecuta ciclos
+-- config/
|   +-- sentinel_config.py               # Configuracion central (secrets via os.environ)
|
+-- core/
|   +-- shared/
|   |   +-- agent_base.py                # BaseAgent, PadreAgent, SignalType, ConsensusResult
|   |   +-- data_pipeline.py             # Pipeline base para ingesta de datos
|   |   +-- geometria_uvg.py             # Matriz UVG-125 Becker-Hagens estatica en RAM
|   +-- precursor/
|   |   +-- risk_calculator.py           # Formula Fantasma TITAN V32
|   |   +-- scanner.py                   # Scanner de 15 tipos de precursor
|   |   +-- muro_cinco_eventos.py        # Motor de correlacion cruzada 5 muros
|   |   +-- precursor_types.py           # Registro de tipos + funciones de deteccion
|   |   +-- assertivity.py              # Tracking de asertividad V46
|   +-- snt_engine/
|       +-- satellization.py             # R(t) = a*t^b — fits y regimenes
|       +-- friction.py                  # Calculador de friccion institucional
|       +-- asi.py                       # Indice de Soberania Atomica
|       +-- nbody.py                     # Procesador N-Body multi-entidad
|       +-- corpus.py                    # Corpus de observaciones empiricas
|
+-- layers/
|   +-- geodynamic/                      # 6 agentes del sistema unico
|       +-- alfa1/agent.py               # NOAA OMNI: Bz, viento solar
|       +-- alfa2/agent.py               # ESA Sentinel-2 multispectral
|       +-- beta1/agent.py               # Kp FFT + filtro Schumann
|       +-- beta2/agent.py               # Sentinel-1 SAR InSAR
|       +-- delta/agent.py               # Financial cross-correlation + atmosferico
|       +-- padre/agent.py               # Consenso asimetrico + Fantasma + Scanner + Muro
|
+-- infrastructure/
|   +-- api/                             # 10 conectores de API
|   |   +-- noaa.py                      # NOAA SWPC (Bz, Kp, protones)
|   |   +-- usgs.py                      # USGS FDSN (catalogo sismico)
|   |   +-- schumann.py                  # Tomsk SRF (resonancia Schumann)
|   |   +-- esa_sentinel.py              # ESA Copernicus (Sentinel-1/2)
|   |   +-- openweathermap.py            # OpenWeatherMap (atmosferico)
|   |   +-- noaa_hazards.py              # NOAA NHC (ciclones tropicales)
|   |   +-- geophysical.py               # IERS LOD
|   |   +-- crypto.py                    # CoinGecko + Binance + Bitso
|   |   +-- bolsa.py                     # Yahoo Finance + Alpha Vantage
|   |   +-- telegram.py                  # Telegram Bot API
|   +-- pipeline/
|   |   +-- data_pipeline.py             # Pipeline maestro con LOCF
|   |   +-- layer_runners.py             # GeodynamicLayerRunner (6 agentes)
|   |   +-- backcast.py                  # Carga historica one-time (1994-2025, 1H)
|   |   +-- legacy_loader.py             # Cargador de datos TITAN legacy
|   +-- database/
|   |   +-- schema.py                    # Schema SQLite + WAL + triggers + backcast tables
|   |   +-- repository.py                # CRUD + 12 queries analiticas
|   |   +-- seed_nodos.py                # 125 nodos semilla (Mexico + Ring of Fire)
|   +-- dashboard/
|   |   +-- app.py                       # Dashboard Streamlit (9 tabs)
|   +-- telegram/
|       +-- bot.py                       # Bot Telegram para alertas
|
+-- tests/                               # 301 tests
|   +-- test_snt_engine.py               # Tests SNT (satellization, friction, ASI, N-Body)
|   +-- test_agents.py                   # Tests de agentes (6 agentes)
|   +-- test_precursor.py                # Tests precursor (fantasma, scanner, muro, assertivity)
|   +-- test_schumann_filter.py          # Tests Schumann filter + DB schema
|   +-- test_api_connectors.py           # Tests de conectores API
|   +-- test_pipeline.py                 # Tests de pipeline + layer runners
|   +-- test_infrastructure.py           # Tests de infraestructura (config, DB, telegram)
|
+-- data/                                # Bases de datos SQLite
    +-- SENTINEL_OMEGA_PRO.db            # DB principal (6 tablas operacionales + 6 backcast)
```

---

## Instalacion

```bash
pip install -e ".[all]"
```

### Dependencias Principales

```
numpy>=1.24          # Computacion numerica, FFT
scipy>=1.10          # Estadistica, Pearson, Mann-Whitney
pandas>=2.0          # DataFrames para analisis
requests>=2.28       # HTTP para APIs
onnxruntime>=1.14    # Inferencia ML (precursor tipo 11)
streamlit>=1.28      # Dashboard interactivo
plotly>=5.15         # Visualizaciones
```

## Ejecucion

```bash
# Tests (301 tests, ejecutar desde /home/user/workspaces/)
python -m pytest sentinel_omega/tests/ -q

# Dashboard (9 tabs interactivas)
streamlit run sentinel_omega/infrastructure/dashboard/app.py
```

### Launcher / Shutdown / Reboot

```bash
# Iniciar el orquestador en ciclo continuo
python sentinel_omega/launcher.py

# Iniciar con dashboard + sin alertas Telegram (dry run)
python sentinel_omega/launcher.py --dashboard --dry-run

# Un solo ciclo y salir
python sentinel_omega/launcher.py --once

# Carga historica (one-time, 1994-2025)
python sentinel_omega/launcher.py --backcast

# Detener gracefully (SIGTERM -> espera 30s)
python sentinel_omega/shutdown.py

# Detener forzado (SIGKILL si no responde)
python sentinel_omega/shutdown.py --force

# Reiniciar (stop + relaunch)
python sentinel_omega/reboot.py
python sentinel_omega/reboot.py --dashboard --dry-run
```

| Archivo                     | Proposito                              |
|-----------------------------|----------------------------------------|
| `data/sentinel_omega.pid`   | PID del proceso activo                 |
| `data/sentinel_omega.log`   | Log persistente del orquestador        |

El launcher:
- Verifica que no haya otra instancia corriendo (via PID file)
- Inicializa la base de datos y siembra los 125 nodos si esta vacia
- Ejecuta ciclos en loop con el intervalo configurado (default 300s)
- Maneja SIGTERM/SIGINT para shutdown graceful
- Persiste cada ciclo en SQLite (precursores cosmicos + ciclos)
- Opcionalmente lanza el dashboard de Streamlit como proceso hijo
- Flag `--backcast` ejecuta carga historica antes de iniciar ciclos

## Variables de Entorno

```bash
export TELEGRAM_BOT_TOKEN="..."        # Dispatch de alertas Telegram
export TELEGRAM_CHAT_ID="..."          # Chat destino para alertas
export OPENWEATHERMAP_KEY="..."        # Datos atmosfericos (presion, humedad)
export COINGECKO_API_KEY="..."         # Datos de mercado crypto
export ALPHA_VANTAGE_KEY="..."         # Datos bursatiles
export BITSO_API_KEY="..."             # Exchange Bitso
export BITSO_API_SECRET="..."          # Exchange Bitso
```

> **Seguridad**: Todas las claves se cargan exclusivamente via `os.environ.get()`. Nunca se hardcodean tokens en el codigo. Las claves se rotan segun se van usando.

---

## Linaje

| Version  | Sistema          | Aportacion                                           |
|----------|------------------|------------------------------------------------------|
| V32      | TITAN V32        | Formula Fantasma, Schumann WPC, 2 muros (Geo+Solar) |
| V46      | TITAN V46        | Asertividad, validacion contra USGS, hits/misses     |
| V53      | TITAN V53        | Patrones WPC, Lorenz-X/Lyapunov, multi-horizonte     |
| v2.5     | Sentinel Omega   | 15 precursores, 5 muros, 125 nodos, 6 agentes, dashboard, filtro Schumann, backcast 1H |

---

## Licencia

Proprietary — Fractal Core Research

**Autor**: Elan Zainos Corona
**Contacto**: elan.zainos.corona@gmail.com
