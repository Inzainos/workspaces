# Sentinel Omega v2.5

**Plataforma de detección de precursores de eventos naturales**

Sentinel Omega monitorea en tiempo real datos geofísicos, atmosféricos, solares, oceánicos y financieros para detectar precursores de terremotos, erupciones volcánicas, tormentas solares, tsunamis y otros eventos naturales de alto impacto.

> Sucesor de la familia de bots TITAN V32/V46/V53.
> Autor: Elán Zainos Corona — Fractal Core Research

---

## Objetivo del Proyecto

El sistema busca resolver un problema fundamental: **detectar señales precursoras de eventos naturales con suficiente anticipación para permitir alertas tempranas**. A diferencia de los sistemas de alerta sísmica convencionales que solo reaccionan después del evento, Sentinel Omega monitorea correlaciones multi-dominio (geofísico, atmosférico, solar, oceánico y financiero) para identificar patrones que históricamente preceden a eventos de gran magnitud.

La plataforma integra datos de 10+ fuentes públicas en tiempo real y aplica un framework de consenso jerárquico donde agentes especializados votan con pérdida asimétrica: el costo de no detectar un evento (miss) se penaliza 10x más que una falsa alarma.

---

## Hallazgos e Innovación

### 1. Fórmula Fantasma (TITAN V32)

El índice Fantasma es una función compuesta que correlaciona variables solares, geomagnéticas y atmosféricas para producir un score de riesgo precursor:

```
fantasma = (abs(Bz)^2) + (viento x 0.02) + (Schumann_WPC x 1.5)

Modificadores post-core:
  + Presión atmosférica (< 1008 hPa -> hasta +3.0)
  x Kp storm (>= 5 -> hasta x1.5)
  + LOD anomaly (> 0.5 ms -> hasta +2.0)
```

**Hallazgo**: La componente cuadrática del Bz (campo magnético interplanetario norte-sur) es el predictor más fuerte. Valores de Bz < -10 nT generan contribuciones Bz^2 > 100 puntos, disparando directamente el umbral CRITICAL. Esto se alinea con la observación empírica de que perturbaciones geomagnéticas severas (Bz fuertemente negativo) preceden actividad sísmica inusual en ventanas de 48-96 horas.

| Nivel    | Rango   | Interpretación                                   |
|----------|---------|--------------------------------------------------|
| LOW      | < 5     | Actividad de fondo normal                        |
| MODERATE | 5 - 15  | Señales elevadas, monitoreo activo               |
| HIGH     | 15 - 30 | Precursores múltiples, alerta preventiva         |
| CRITICAL | >= 30   | Correlación multi-dominio, alerta inmediata      |

### 2. Filtro Fourier-Schumann (Innovación Beta-1)

El agente Beta-1 aplica un filtro armónico al espectro FFT de datos geomagnéticos (serie temporal de Kp):

- **Armónicos de Schumann**: 7.83, 14.3, 20.8, 27.3, 33.8 Hz
- Los datos geofísicos se muestrean en intervalos de horas, no Hz directamente. El filtro identifica qué bins de frecuencia son **sub-armónicos** de las resonancias de Schumann
- Bins no-resonantes se atenúan al 10%, preservando solo la energía resonante
- La frecuencia de Schumann en vivo (no hardcoded a 7.83 Hz) escala proporcionalmente los armónicos

**Hallazgo**: La **coherencia de Schumann** — ratio de energía en bins resonantes vs energía total — proporciona un indicador de acoplamiento Tierra-ionosfera. Coherencia > 0.3 combinada con excitación activa produce la señal WATCH, un estado intermedio entre NEUTRAL y ALERT que indica "precursor potencial, monitorear de cerca". Este descubrimiento emergió de la correlación entre excitaciones anómalas en la resonancia Schumann de Tomsk (Rusia) y actividad sísmica significativa 48-72 horas después.

### 3. Muro de los 5 Eventos (Correlación Cruzada Multi-Dominio)

La innovación central es que ningún precursor individual es confiable — es la **correlación simultánea** de múltiples dominios lo que indica riesgo real:

| Muro | Dominio             | Precursores                                    |
|------|---------------------|------------------------------------------------|
| 1    | GEOFÍSICO           | Enjambre Sísmico, Volcánico, Fantasma          |
| 2    | ATMOSFÉRICO         | Blue Jet, Sprite Rojo, Niebla Tule             |
| 3    | OCEÁNICO            | Tsunami, Huracán                               |
| 4    | SOLAR/GEOMAGNÉTICO  | Tormenta, Perturbación, Schumann, Silent, GRB  |
| 5    | FINANCIERO/SOCIAL   | Correlación Financiera                         |

**Breach**: Cuando >= 3 muros están activos simultáneamente, el sistema declara un "breach" — indicando que múltiples dominios independientes están correlacionados, lo cual históricamente precede eventos significativos.

**Hallazgo**: La inclusión del muro FINANCIERO/SOCIAL es innovadora. Se observan correlaciones entre caídas abruptas en mercados financieros (VIX spike, crypto fear index alto, bolsa bearish) y eventos naturales dentro de ventanas de 72 horas. La hipótesis es que mercados sensibles capturan información agregada (comportamiento de aseguradoras, contratos de reaseguro, posiciones de commodities agrícolas) que anticipa disrupciones.

### 4. Silent Trigger (Calma Precursora)

**Hallazgo contra-intuitivo**: Períodos de calma geomagnética extrema (todos los valores de Kp < 2.0 sostenidos por 24+ horas) son precursores tan significativos como las tormentas. El "Silent Trigger" detecta esta calma anómala. La ausencia de perturbación es, en sí misma, una señal.

### 5. Topología de 125 Nodos con Saturación

El sistema modela la Tierra completa con una malla de 125 nodos de monitoreo basada en la geometría UVG Becker-Hagens:

| Tipo        | Cantidad | Descripción                                    |
|-------------|----------|------------------------------------------------|
| Real        | 50       | Zonas sísmicas reales (Ring of Fire global)    |
| Ghost       | 50       | Nodos fantasma inferidos de gaps sísmicos      |
| Geobattery  | 25       | Zonas de acumulación electroquímica            |

**Hallazgo**: Los nodos "ghost" — posiciones inferidas donde no hay monitoreo pero la topología sugiere acumulación de estrés — han mostrado ser zonas de riesgo subestimado por redes sísmicas convencionales. Los nodos "geobattery" modelan zonas donde corrientes telúricas y diferencias de potencial electroquímico en el subsuelo pueden actuar como acumuladores de energía. La saturación de un nodo (capped a 1.0 por trigger SQL) indica zona de máximo estrés acumulado.

La matriz estática UVG-125 se carga en RAM al importar (`geometria_uvg.py`) y permite mapear cada sismo global al nodo más cercano. Tlaxcala (19.31, -98.24) es el nodo de observación (id=0); los otros 125 cubren el planeta.

### 6. Pérdida Asimétrica en Consenso Jerárquico

El Padre usa pérdida asimétrica en el consenso:

```
Costo de miss   = 10 x peso_base
Costo de falsa  =  1 x peso_base
```

**Innovación**: El sistema prefiere sobre-alertar a sub-alertar. Un 10% de falsas alarmas es aceptable si el sistema captura el 95% de eventos reales. Esto invierte la lógica de la mayoría de sistemas de alerta que optimizan para minimizar falsas alarmas.

### 7. Validación de Asertividad (V46 Lineage)

El tracker de asertividad compara predicciones contra eventos reales del catálogo USGS usando distancia euclidiana dentro de un radio de 5 grados:

- **Hit rate**: Predicciones confirmadas por eventos M>=4.5
- **Miss rate**: Eventos que no fueron predichos
- **False alarm rate**: Predicciones sin evento correspondiente

---

## Arquitectura — 6 Agentes, Sistema Único

```
Orchestrator -> GeodynamicLayerRunner -> 6 Agentes -> Consenso del Padre
|
+-- Alfa-1 (Geodinámico: Bz, viento solar, sísmico) — 30 años entrenamiento
|       ^ valida
+-- Alfa-2 (Satélite: ESA Sentinel) — 14 años
|
+-- Beta-1 (Schumann / cimática / energía liberada) — 30 años  <- LATIDO
|       ^ valida
+-- Beta-2 (Química atmosférica) — 14 años
|
+-- Delta  (Financiero: crypto + bolsa + humor de la tierra) — 10 años
|
+-- Padre  (Validador jerárquico cruzado entre familias)
        +-- Índice de Riesgo Fantasma TITAN V32
        +-- Scanner de Precursores (15 tipos)
        +-- Muro de los 5 Eventos
```

**Jerarquía**: Los agentes #2 reportan al #1 -> el Padre valida entre familias.
**Schumann es el latido**: Todo se correlaciona contra la resonancia Schumann (Beta-1).
Si Schumann está perturbado junto con cualquier otra señal = precursor detectado.

**Familias**:
- `space_weather`: Alfa-1, Alfa-2
- `schumann_cymatics`: Beta-1, Beta-2
- `financial_sentiment`: Delta

**El consenso requiere**: >= 2 familias activas + >= 2 alertas + correlación_schumann > 0.3

### Ciclo del Orquestador

1. **GeodynamicPipeline** obtiene datos para todos los agentes (alfa1, beta1, beta2, delta, alfa2)
2. **Fantasma V32** calcula el riesgo precursor de las señales crudas
3. **Datos de huracán** se obtienen (non-blocking)
4. **Scanner** evalúa los 15 tipos de precursor contra los datos del ciclo
5. **Muro de los 5 Eventos** evalúa la correlación de 5 dominios
6. Todos los agentes ingestan + analizan -> señales
7. **Padre** evalúa el consenso (jerárquico + correlación Schumann)
8. Las alertas se despachan vía Telegram + registro en SQLite

### Señales del Sistema

| Señal     | Significado                           | Uso                     |
|-----------|---------------------------------------|-------------------------|
| BULLISH   | Tendencia alcista (mercados)          | Delta (financiero)      |
| BEARISH   | Tendencia bajista (mercados)          | Delta (financiero)      |
| NEUTRAL   | Sin tendencia clara                   | Todos los agentes       |
| WATCH     | Excitación coherente, monitorear      | Beta-1 (Schumann)       |
| ALERT     | Precursor confirmado, alertar         | Geodinámico             |
| NO_SIGNAL | Sin datos o sin análisis              | Todos los agentes       |

---

## 15 Tipos de Precursor

| #  | Tipo                     | Muro               | Ventana | Variables Clave                       |
|----|--------------------------|---------------------|---------|---------------------------------------|
| 1  | Resonancia Schumann      | Solar/Geomagnético  | 72h     | schumann_hz, activity_pct             |
| 2  | Silent Trigger (Calma)   | Solar/Geomagnético  | 48h     | kp_values (todos < 2.0 por 24h)      |
| 3  | Enjambre Sísmico         | Geofísico           | 48h     | event_count, max_mag, cluster_radius  |
| 4  | Blue Jet                 | Atmosférico         | 72h     | humidity, temp, pressure, weather_id  |
| 5  | Sprite Rojo              | Atmosférico         | 72h     | humidity, pressure, weather_id (211)  |
| 6  | Niebla Tule              | Atmosférico         | 72h     | humidity, temp, visibility, wind      |
| 7  | Tormenta Solar           | Solar/Geomagnético  | 96h     | xray_flux (>= 1e-5 W/m2 = M-class)   |
| 8  | Perturbación Geomag.     | Solar/Geomagnético  | 96h     | kp_mean (>= 5.0 = storm level)       |
| 9  | Huracán                  | Oceánico            | 120h    | distance_km, category                 |
| 10 | Tsunami                  | Oceánico            | 24h     | magnitude, depth (>= 7.0, < 70km)    |
| 11 | Inferencia ML            | —                   | 48h     | onnx_model_output                     |
| 12 | Gamma-Ray Burst          | Solar/Geomagnético  | 168h    | xray_flux (>= 1e-4 W/m2)            |
| 13 | Precursor Volcánico      | Geofísico           | 72h     | so2_index, seismic_coupling           |
| 14 | Índice Fantasma          | Geofísico           | 72h     | fantasma composite score              |
| 15 | Correlación Financiera   | Financiero/Social   | 72h     | fear_greed, vix, btc_change           |

---

## Framework Matemático (SNT)

Sentinel Omega utiliza la **Shadow Node Theory** exclusivamente como framework matemático — no como propósito del sistema. El modelo de ley de potencia describe relaciones de dominancia/subordinación en sistemas complejos:

```
R(t) = a * t^b
```

| Régimen              | Exponente b | Interpretación                             |
|----------------------|-------------|--------------------------------------------|
| Extreme              | > 2.0       | Satelización sin fricción                  |
| Roche Radius         | > 1.0       | Satelización rápida (punto de no retorno)  |
| Active               | > 0.3       | Satelización activa                        |
| Gradual              | > 0.05      | Satelización gradual                       |
| Equilibrium          | > -0.1      | Estado estable                             |
| Convergence/Leapfrog | <= -0.1     | Desacoplamiento / convergencia             |

Se aplica a:
- Ratios de dominancia financiera (BTC/ETH, SPY/QQQ)
- Intensidad geomagnética (tendencias de Kp)
- Gradientes de nodos topológicos

---

## Base de Datos (SQLite)

### Tablas Operacionales

6 tablas en `SENTINEL_OMEGA_PRO.db` con modo WAL y foreign keys (schema v6):

| Tabla                    | Registros   | Propósito                                              |
|--------------------------|-------------|--------------------------------------------------------|
| TBL_PRECURSORES_COSMICOS | Por ciclo   | Snapshot: Bz, viento, protones, Kp, LOD, Schumann, fantasma, fase lunar |
| TBL_NODOS_TOPOLOGIA      | 125 fijos   | Nodos N-Body con conductividad, energía, saturación    |
| TBL_HISTORICO_SISMICO    | Acumulativo | Catálogo USGS con deduplicación por event_id           |
| TBL_DETECCIONES          | Por ciclo   | Log de precursores detectados con tipo, confianza, JSON |
| TBL_CICLOS               | Por ciclo   | Historial de ciclos: señal, consenso, riesgo, muro     |
| TBL_MURO_EVENTOS         | Por breach  | Breaches del Muro con correlación y muros activos      |

### Tablas de Aprendizaje y Auditoría

| Tabla                      | Propósito                                                        |
|----------------------------|-------------------------------------------------------------------|
| TBL_FIRMAS                 | Memoria de patrones por bot. Estado: nueva → observada → recurrente → consolidada (por recurrencia). Solo las consolidadas son conocimiento exigible. |
| TBL_JUEZ_AUDITORIA         | Ledger disciplinario del Juez: ACIERTO / FALLO / FALSO_POSITIVO con severidad asimétrica (omitir firma conocida = 20 base, omisión = 10, falsa alarma = 1) escalada por reincidencia. |
| tbl_eventos_no_sismicos    | Catálogo derivado de erupciones volcánicas (VEI≥3) y tormentas solares (Kp≥6 onset). Alimenta la Fase 1b de entrenamiento multi-evento. |
| tbl_patrones_correlacion   | Matriz feature × event_class calculada tras el entrenamiento. Para cada par guarda media, media global y ratio; ratio > 1 significa que la variable está elevada en los 14 días previos a ese tipo de evento. |

**Entrenamiento en tres fases** (`--entrenar`):
- **Fase 1** — Reconocimiento sísmico (sin castigo): extrae la ventana de 14 días previa a cada evento M5+ del backcast y la registra como firma por bot.
- **Fase 1b** — Reconocimiento no sísmico: igual proceso sobre erupciones volcánicas (VEI≥3) y tormentas solares (Kp≥6) derivadas de las tablas de backcast. Los bots aprenden qué precede a estos eventos además de los sísmicos.
- **Fase 2** — Disciplina: re-presenta las firmas consolidadas; el Juez castiga si el sistema ya no las reconoce.
- Al finalizar, calcula la **matriz de correlaciones** (feature × event_class) y la almacena en `tbl_patrones_correlacion` para el reporte de mapa de calor.

En operación, cada ciclo compara el estado vivo contra las firmas consolidadas ("el estado actual se parece 87% al que precedió el M7 del nodo 45").

### Tablas de Backcast Histórico (resolución 1H, 1994-2025)

| Tabla                      | Clave Primaria          | Propósito                                    |
|----------------------------|-------------------------|----------------------------------------------|
| tbl_clima_espacial_raw     | timestamp_blk           | NASA OMNI2: Bz, viento solar, Kp, protones  |
| tbl_astronomia_cinematica  | timestamp_blk           | LOD, fase lunar, distancia lunar, sicigia    |
| tbl_historico_sismico_raw  | (timestamp_blk, id_nodo)| Sismos USGS mapeados a nodos UVG-125        |
| tbl_psique_financiera      | timestamp_blk           | BTC precio, volatilidad (2014+)              |
| tbl_enjambre_telemetria    | (timestamp_blk, id_nodo)| Resonancia Schumann por nodo                 |
| tbl_nodo_estado_dinamico   | (timestamp_blk, id_nodo)| Carga/tensión por nodo (cap 1.0 vía trigger) |

### Tablas de Live-Only (acumuladas desde ciclos en vivo)

| Tabla                   | Clave Primaria            | Propósito                                         |
|-------------------------|---------------------------|---------------------------------------------------|
| tbl_cobertura_satelital | id (autoincrement)        | Cobertura satelital ESA Sentinel-2 por zona/ciclo |
| tbl_delta_cross         | id (autoincrement)        | Resultados de correlación cruzada geofísico-financiera por ciclo |

**Protocolo de backcast**: CERO datos sintéticos. Faltante = NULL. LOCF solo desde registros reales.

**Triggers**: `trg_nodo_saturacion` y `trg_procesar_saturacion` — cap automático de saturación/carga a 1.0.

---

## Dashboard (Streamlit + Plotly)

9 pestañas interactivas con datos en tiempo real:

| Tab | Nombre          | Visualizaciones                                                          |
|-----|-----------------|--------------------------------------------------------------------------|
| 1   | Precursor Risk  | Gauge fantasma, historial, waterfall de componentes, donut de riesgo     |
| 2   | Muro 5 Eventos  | 5 tarjetas de estado, radar de correlación, timeline de activación       |
| 3   | Scanner         | Tabla de detecciones, barras por tipo, histograma de confianza, stats    |
| 4   | Topología       | Mapa mundial 125 nodos, ranking saturación, conductividad vs energía    |
| 5   | Sísmico         | Mapa sísmico, histograma magnitudes, profundidad vs magnitud, regiones  |
| 6   | Schumann        | Tendencia Hz, actividad WPC, distribución, Hz vs actividad scatter      |
| 7   | Layer Signals   | Consenso por capa, señales de agentes individuales                       |
| 8   | SNT Analysis    | Exponente de satelización, fits de ley de potencia                       |
| 9   | Ciclos          | Timeline fantasma + precursores, tasa de alertas, breach rate gauges    |

---

## Fuentes de Datos (APIs)

| Fuente           | Datos                                     | Auth      | Uso                  |
|------------------|-------------------------------------------|-----------|----------------------|
| NOAA SWPC        | Bz, viento solar, Kp, GOES X-ray, protones | Público   | Alfa-1, Scanner      |
| USGS FDSN        | Catálogo sísmico mundial                   | Público   | Scanner, Asertividad |
| NASA OMNI2       | Bz, viento solar, Kp históricos (backcast) | Público   | Backcast             |
| Tomsk SRF        | Resonancia Schumann (7.83 Hz)              | Público   | Beta-1, Scanner      |
| IERS             | Length-of-Day (LOD)                        | Público   | Fantasma             |
| ESA Copernicus   | Sentinel-1 SAR, Sentinel-2 multispectral   | Público   | Alfa-2, Beta-2       |
| OpenWeatherMap   | Presión, temp, humedad, weather_id          | API Key   | Beta-2, Scanner      |
| NOAA NHC         | Ciclones tropicales activos                 | Público   | Scanner (huracanes)  |
| CoinGecko        | Dominancia BTC, market caps                 | Público   | Delta                |
| Yahoo Finance    | OHLCV acciones, VIX, ETFs                  | Público   | Delta                |

---

## Estructura del Proyecto

```
sentinel_omega/
├── launcher.py                          # Launcher — arranca el orquestador en ciclo continuo
├── shutdown.py                          # Shutdown — detiene gracefully vía SIGTERM/SIGKILL
├── reboot.py                            # Reboot — stop + relaunch
├── orchestrator.py                      # Orquestador maestro — ejecuta ciclos
├── config/
│   └── sentinel_config.py               # Configuración central (secrets vía os.environ)
│
├── core/
│   ├── shared/
│   │   ├── agent_base.py                # BaseAgent, PadreAgent, SignalType, ConsensusResult
│   │   ├── data_pipeline.py             # Pipeline base para ingesta de datos
│   │   └── geometria_uvg.py             # Matriz UVG-125 Becker-Hagens estática en RAM
│   ├── precursor/
│   │   ├── risk_calculator.py           # Fórmula Fantasma TITAN V32
│   │   ├── scanner.py                   # Scanner de 15 tipos de precursor
│   │   ├── muro_cinco_eventos.py        # Motor de correlación cruzada 5 muros
│   │   ├── precursor_types.py           # Registro de tipos + funciones de detección
│   │   └── assertivity.py              # Tracking de asertividad V46
│   ├── firmas/
│   │   └── signature_engine.py          # Memoria de patrones por bot (nueva→consolidada)
│   ├── juez/
│   │   └── juez.py                      # Auditor frío separado del Padre (ACIERTO/FALLO/FP)
│   └── snt_engine/
│       ├── satellization.py             # R(t) = a*t^b — fits y regímenes
│       ├── friction.py                  # Calculador de fricción institucional
│       ├── asi.py                       # Índice de Soberanía Atómica
│       ├── nbody.py                     # Procesador N-Body multi-entidad
│       └── corpus.py                    # Corpus de observaciones empíricas (satelización)
│
├── layers/
│   └── geodynamic/                      # Los 6 agentes del sistema único
│       ├── alfa1/agent.py               # NOAA OMNI: Bz, viento solar
│       ├── alfa2/agent.py               # ESA Sentinel-2 multispectral
│       ├── beta1/agent.py               # Kp FFT + filtro Schumann
│       ├── beta2/agent.py               # Sentinel-1 SAR InSAR / química atmosférica
│       ├── delta/agent.py               # Correlación financiera + atmosférico
│       └── padre/agent.py               # Consenso asimétrico + Fantasma + Scanner + Muro
│
├── infrastructure/
│   ├── api/                             # 10 conectores de API
│   │   ├── noaa.py                      # NOAA SWPC (Bz, Kp, protones)
│   │   ├── usgs.py                      # USGS FDSN (catálogo sísmico)
│   │   ├── schumann.py                  # Tomsk SRF (resonancia Schumann)
│   │   ├── esa_sentinel.py              # ESA Copernicus (Sentinel-1/2)
│   │   ├── openweathermap.py            # OpenWeatherMap (atmosférico)
│   │   ├── noaa_hazards.py              # NOAA NHC (ciclones tropicales)
│   │   ├── geophysical.py               # IERS LOD
│   │   ├── crypto.py                    # CoinGecko + Binance + Bitso (Delta)
│   │   ├── bolsa.py                     # Yahoo Finance + Alpha Vantage (Delta)
│   │   └── telegram.py                  # Telegram Bot API
│   ├── pipeline/
│   │   ├── data_pipeline.py             # Pipeline maestro con LOCF
│   │   ├── layer_runners.py             # GeodynamicLayerRunner (6 agentes)
│   │   ├── backcast.py                  # Carga histórica one-time (1994-2025, 1H)
│   │   └── legacy_loader.py             # Cargador de datos TITAN legacy
│   ├── database/
│   │   ├── schema.py                    # Schema SQLite + WAL + triggers + backcast + migración
│   │   ├── repository.py                # CRUD + 12 queries analíticas
│   │   └── seed_nodos.py                # 125 nodos semilla (malla global)
│   ├── dashboard/
│   │   └── app.py                       # Dashboard Streamlit (9 tabs)
│   └── telegram/
│       └── bot.py                       # Bot Telegram para alertas
│
├── tests/                               # 301 tests
│   ├── test_snt_engine.py               # Tests SNT (satellization, friction, ASI, N-Body)
│   ├── test_agents.py                   # Tests de agentes (6 agentes)
│   ├── test_precursor.py                # Tests precursor (fantasma, scanner, muro, assertivity)
│   ├── test_schumann_filter.py          # Tests Schumann filter + DB schema
│   ├── test_api_connectors.py           # Tests de conectores API
│   ├── test_pipeline.py                 # Tests de pipeline + layer runners
│   └── test_infrastructure.py           # Tests de infraestructura (config, DB, telegram)
│
└── data/                                # Bases de datos SQLite
    └── SENTINEL_OMEGA_PRO.db            # DB principal (6 tablas operacionales + 6 backcast)
```

---

## Instalación

```bash
pip install -e ".[all]"
```

### Dependencias Principales

```
numpy>=1.24          # Computación numérica, FFT
scipy>=1.10          # Estadística, Pearson, Mann-Whitney
pandas>=2.0          # DataFrames para análisis
requests>=2.28       # HTTP para APIs
onnxruntime>=1.14    # Inferencia ML (precursor tipo 11)
streamlit>=1.28      # Dashboard interactivo
plotly>=5.15         # Visualizaciones
```

## Ejecución

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

# Carga histórica (one-time, 1994-2025)
python sentinel_omega/launcher.py --backcast

# Entrenamiento de firmas sobre el backcast (Fase 1 sísmica + Fase 1b no sísmica + Fase 2 disciplina)
python sentinel_omega/launcher.py --entrenar

# Detener gracefully (SIGTERM -> espera 30s)
python sentinel_omega/shutdown.py

# Detener forzado (SIGKILL si no responde)
python sentinel_omega/shutdown.py --force

# Reiniciar (stop + relaunch)
python sentinel_omega/reboot.py
python sentinel_omega/reboot.py --dashboard --dry-run
```

| Archivo                     | Propósito                              |
|-----------------------------|----------------------------------------|
| `data/sentinel_omega.pid`   | PID del proceso activo                 |
| `data/sentinel_omega.log`   | Log persistente del orquestador        |

El launcher:
- Verifica que no haya otra instancia corriendo (vía PID file)
- Inicializa la base de datos, aplica migraciones y siembra los 125 nodos si está vacía
- Ejecuta ciclos en loop con el intervalo configurado (default 300s)
- Maneja SIGTERM/SIGINT para shutdown graceful
- Persiste cada ciclo en SQLite (precursores cósmicos + ciclos + detecciones + muro)
- Opcionalmente lanza el dashboard de Streamlit como proceso hijo
- El flag `--backcast` ejecuta la carga histórica antes de iniciar ciclos

## Variables de Entorno

```bash
export TELEGRAM_BOT_TOKEN="..."        # Dispatch de alertas Telegram
export TELEGRAM_CHAT_ID="..."          # Chat destino para alertas
export OPENWEATHERMAP_KEY="..."        # Datos atmosféricos (presión, humedad)
export COINGECKO_API_KEY="..."         # Datos de mercado crypto
export ALPHA_VANTAGE_KEY="..."         # Datos bursátiles
export BITSO_API_KEY="..."             # Exchange Bitso
export BITSO_API_SECRET="..."          # Exchange Bitso
```

> **Seguridad**: Todas las claves se cargan exclusivamente vía `os.environ.get()`. Nunca se hardcodean tokens en el código. Las claves se rotan según se van usando.

---

## Linaje

| Versión  | Sistema          | Aportación                                           |
|----------|------------------|------------------------------------------------------|
| V32      | TITAN V32        | Fórmula Fantasma, Schumann WPC, 2 muros (Geo+Solar) |
| V46      | TITAN V46        | Asertividad, validación contra USGS, hits/misses     |
| V53      | TITAN V53        | Patrones WPC, Lorenz-X/Lyapunov, multi-horizonte     |
| v2.5     | Sentinel Omega   | 15 precursores, 5 muros, 125 nodos, 6 agentes, dashboard, filtro Schumann, backcast 1H |

---

## Licencia

Proprietary — Fractal Core Research

**Autor**: Elán Zainos Corona
**Contacto**: elan.zainos.corona@gmail.com
