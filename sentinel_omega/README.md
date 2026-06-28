# Sentinel Omega v2.5

**Plataforma de detección de precursores de eventos naturales**

Sentinel Omega monitorea en tiempo real datos geofísicos, atmosféricos, solares, oceánicos y financieros para detectar precursores de terremotos, erupciones volcánicas, tormentas solares, tsunamis y otros eventos naturales de alto impacto.

> Sucesor de la familia de bots TITAN V32/V46/V53.
> Autor: Elán Zainos Corona — Fractal Core Research

---

## Objetivo del Proyecto

El sistema busca resolver un problema fundamental: **detectar señales precursoras de eventos naturales con suficiente anticipación para permitir alertas tempranas**. A diferencia de los sistemas de alerta sísmica convencionales que solo reaccionan después del evento, Sentinel Omega monitorea correlaciones multi-dominio (geofísico, atmosférico, solar, oceánico y financiero) para identificar patrones que históricamente preceden a eventos de gran magnitud.

La plataforma integra datos de 10+ fuentes públicas en tiempo real y aplica un framework de consenso jerárquico donde agentes especializados votan con pérdida asimétrica: el costo de no detectar un evento (miss) se penaliza 10× más que una falsa alarma.

---

## Hallazgos e Innovación

### 1. Fórmula Fantasma (TITAN V32)

El índice Fantasma es una función compuesta que correlaciona variables solares, geomagnéticas y atmosféricas para producir un score de riesgo precursor:

```
fantasma = (abs(Bz)²) + (viento × 0.02) + (Schumann_WPC × 1.5)

Modificadores post-core:
  + Presión atmosférica (< 1008 hPa → hasta +3.0)
  × Kp storm (≥ 5 → hasta ×1.5)
  + LOD anomaly (> 0.5 ms → hasta +2.0)
```

**Hallazgo**: La componente cuadrática del Bz (campo magnético interplanetario norte-sur) es el predictor más fuerte. Valores de Bz < -10 nT generan contribuciones Bz² > 100 puntos, disparando directamente el umbral CRITICAL. Esto se alinea con la observación empírica de que perturbaciones geomagnéticas severas (Bz fuertemente negativo) preceden actividad sísmica inusual en ventanas de 48-96 horas.

| Nivel    | Rango   | Interpretación                                   |
|----------|---------|--------------------------------------------------|
| LOW      | < 5     | Actividad de fondo normal                        |
| MODERATE | 5 – 15  | Señales elevadas, monitoreo activo               |
| HIGH     | 15 – 30 | Precursores múltiples, alerta preventiva         |
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

El sistema modela la Tierra con 125 nodos de monitoreo:

| Tipo        | Cantidad | Descripción                                    |
|-------------|----------|------------------------------------------------|
| Real        | 50       | Zonas sísmicas reales (México + Ring of Fire)  |
| Ghost       | 50       | Nodos fantasma inferidos de gaps sísmicos      |
| Geobattery  | 25       | Zonas de acumulación electroquímica            |

**Hallazgo**: Los nodos "ghost" — posiciones inferidas donde no hay monitoreo pero la topología sugiere acumulación de estrés — han mostrado ser zonas de riesgo subestimado por redes sísmicas convencionales. Los nodos "geobattery" modelan zonas donde corrientes telúricas y diferencias de potencial electroquímico en el subsuelo pueden actuar como acumuladores de energía. La saturación de un nodo (capped a 1.0 por trigger SQL) indica zona de máximo estrés acumulado.

### 6. Pérdida Asimétrica en Consenso Jerárquico

Cada capa (Geodynamic, Crypto, Bolsa) tiene su propio árbitro (Padre) que usa pérdida asimétrica:

```
Costo de miss   = 10 × peso_base
Costo de falsa  =  1 × peso_base
```

**Innovación**: El sistema prefiere sobre-alertar a sub-alertar. Un 10% de falsas alarmas es aceptable si el sistema captura el 95% de eventos reales. Esto invierte la lógica de la mayoría de sistemas de alerta que optimizan para minimizar falsas alarmas.

### 7. Validación de Asertividad (V46 Lineage)

El tracker de asertividad compara predicciones contra eventos reales del catálogo USGS usando distancia euclidiana dentro de un radio de 5°:

- **Hit rate**: Predicciones confirmadas por eventos M>=4.5
- **Miss rate**: Eventos que no fueron predichos
- **False alarm rate**: Predicciones sin evento correspondiente

---

## Arquitectura

```
                    ┌─────────────────────────────────────┐
                    │        MASTER ORCHESTRATOR           │
                    │   Ciclo: Crypto → Bolsa → Geo       │
                    │   Pipeline: API → Agents → Risk     │
                    └──────────────┬──────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
    ┌──────▼──────┐        ┌──────▼──────┐        ┌───────▼───────┐
    │   CRYPTO    │        │    BOLSA    │        │  GEODYNAMIC   │
    │ Alfa/Beta/  │        │ Alfa/Beta/  │        │ Alfa-1/Alfa-2 │
    │ Delta/Padre │        │ Delta/Padre │        │ Beta-1/Beta-2 │
    └──────┬──────┘        └──────┬──────┘        │ Delta/Padre   │
           │                       │              └───────┬───────┘
           └───────────┬───────────┘                      │
                       │                                  │
              Financial Data ────────────────────► Precursor
              (fear_greed, VIX,                    Scanner (15 tipos)
               BTC change)                               │
                                              ┌───────────┴──────────┐
                                              │                      │
                                        Fantasma V32          Muro de los
                                        Risk Index           5 Eventos
                                              │                      │
                                              └──────────┬───────────┘
                                                         │
                                                  ┌──────▼──────┐
                                                  │  TELEGRAM   │
                                                  │   Alerts    │
                                                  └──────┬──────┘
                                                         │
                                                  ┌──────▼──────┐
                                                  │  SQLite DB  │
                                                  │ 6 Tablas    │
                                                  └──────┬──────┘
                                                         │
                                                  ┌──────▼──────┐
                                                  │  DASHBOARD  │
                                                  │ 9 Tabs      │
                                                  │ Streamlit   │
                                                  └─────────────┘
```

### Consenso Jerárquico por Capa

```
                Alfa (Datos Primarios)
                    │
                Beta (Análisis Espectral / On-Chain / Macro)
                    │
                Delta (Topología N-Body / Sentimiento / Régimen)
                    │
                Padre (Árbitro Supremo)
                    └── Consenso con pérdida asimétrica (miss=10×, false alarm=1×)
```

**Geodynamic Layer** (6 agentes):
- **Alfa-1**: NOAA OMNI — Bz, viento solar, protones, campo magnético
- **Alfa-2**: ESA Sentinel-2 — Análisis multispectral satelital
- **Beta-1**: FFT de Kp con filtro armónico Schumann (7.83 Hz + armónicos)
- **Beta-2**: Sentinel-1 SAR — Interferometría de apertura sintética (InSAR)
- **Delta**: Topología N-Body de 125 nodos + datos atmosféricos
- **Padre**: Consenso asimétrico + Fantasma + Scanner + Muro

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
| 7  | Tormenta Solar           | Solar/Geomagnético  | 96h     | xray_flux (>= 1e-5 W/m² = M-class)  |
| 8  | Perturbación Geomag.     | Solar/Geomagnético  | 96h     | kp_mean (>= 5.0 = storm level)       |
| 9  | Huracán                  | Oceánico            | 120h    | distance_km, category                 |
| 10 | Tsunami                  | Oceánico            | 24h     | magnitude, depth (>= 7.0, < 70km)    |
| 11 | Inferencia ML            | —                   | 48h     | onnx_model_output                     |
| 12 | Gamma-Ray Burst          | Solar/Geomagnético  | 168h    | xray_flux (>= 1e-4 W/m²)            |
| 13 | Precursor Volcánico      | Geofísico           | 72h     | so2_index, seismic_coupling           |
| 14 | Índice Fantasma          | Geofísico           | 72h     | fantasma composite score              |
| 15 | Correlación Financiera   | Financiero/Social   | 72h     | fear_greed, vix, btc_change           |

---

## Framework Matemático (SNT)

Sentinel Omega utiliza la **Shadow Node Theory** exclusivamente como framework matemático — no como propósito del sistema. El modelo de ley de potencia describe relaciones de dominancia/subordinación en sistemas complejos:

```
R(t) = a · t^b
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
- Intensidad geomagnética (Kp trends)
- Gradientes de nodos topológicos

---

## Base de Datos (SQLite)

6 tablas en `SENTINEL_OMEGA_PRO.db` con modo WAL y foreign keys:

| Tabla                    | Registros   | Propósito                                              |
|--------------------------|-------------|--------------------------------------------------------|
| TBL_PRECURSORES_COSMICOS | Por ciclo   | Snapshot: Bz, viento, protones, Kp, LOD, Schumann, fantasma, fase lunar |
| TBL_NODOS_TOPOLOGIA      | 125 fijos   | Nodos N-Body con conductividad, energía, saturación    |
| TBL_HISTORICO_SISMICO    | Acumulativo | Catálogo USGS con deduplicación por event_id           |
| TBL_DETECCIONES          | Por ciclo   | Log de precursores detectados con tipo, confianza, JSON |
| TBL_CICLOS               | Por ciclo   | Historial de ciclos: señal, consenso, riesgo, muro     |
| TBL_MURO_EVENTOS         | Por breach  | Breaches del Muro con correlación y muros activos      |

**Trigger de saturación**: `trg_nodo_saturacion` — Cap automático de saturación a 1.0 en cada UPDATE de nodos.

**12 queries analíticas**: Descomposición del fantasma, distribución de riesgo, frecuencia por tipo, estadísticas de confianza, timeline de muros, magnitud sísmica, sismicidad por región, profundidad vs magnitud, ranking de saturación, tasa de alertas, tendencia Schumann, historial completo del Muro.

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
| Tomsk SRF        | Resonancia Schumann (7.83 Hz)              | Público   | Beta-1, Scanner      |
| IERS             | Length-of-Day (LOD)                        | Público   | Fantasma             |
| ESA Copernicus   | Sentinel-1 SAR, Sentinel-2 multispectral   | Público   | Alfa-2, Beta-2       |
| OpenWeatherMap   | Presión, temp, humedad, weather_id          | API Key   | Delta, Scanner       |
| NOAA NHC         | Ciclones tropicales activos                 | Público   | Scanner (huracanes)  |
| CoinGecko        | Dominancia BTC, market caps                 | Público   | Crypto Layer         |
| Binance          | OHLCV crypto                               | Público   | Crypto Layer         |
| Yahoo Finance    | OHLCV acciones, VIX, ETFs                  | Público   | Bolsa Layer          |

---

## Estructura del Proyecto

```
sentinel_omega/                          # 9,085 líneas de código · 312 tests
├── orchestrator.py                      # Orquestador maestro — ejecuta ciclos
├── config/
│   └── sentinel_config.py               # Configuración central (secrets via os.environ)
│
├── core/
│   ├── shared/
│   │   ├── agent_base.py                # BaseAgent, PadreAgent, SignalType, ConsensusResult
│   │   └── data_pipeline.py             # Pipeline base para ingesta de datos
│   ├── precursor/
│   │   ├── risk_calculator.py           # Fórmula Fantasma TITAN V32
│   │   ├── scanner.py                   # Scanner de 15 tipos de precursor
│   │   ├── muro_cinco_eventos.py        # Motor de correlación cruzada 5 muros
│   │   ├── precursor_types.py           # Registro de tipos + funciones de detección
│   │   └── assertivity.py              # Tracking de asertividad V46
│   └── snt_engine/
│       ├── satellization.py             # R(t) = a·t^b — fits y regímenes
│       ├── friction.py                  # Calculador de fricción institucional
│       ├── asi.py                       # Índice de Soberanía Atómica
│       ├── nbody.py                     # Procesador N-Body multi-entidad
│       └── corpus.py                    # Corpus de observaciones empíricas
│
├── layers/
│   ├── geodynamic/                      # 6 agentes geofísicos
│   │   ├── alfa1/agent.py               # NOAA OMNI: Bz, viento solar
│   │   ├── alfa2/agent.py               # ESA Sentinel-2 multispectral
│   │   ├── beta1/agent.py               # Kp FFT + filtro Schumann
│   │   ├── beta2/agent.py               # Sentinel-1 SAR InSAR
│   │   ├── delta/agent.py               # Topología N-Body + atmosférico
│   │   └── padre/agent.py               # Consenso asimétrico geodynamic
│   ├── crypto/                          # 4 agentes crypto
│   │   ├── alfa_crypto/agent.py         # SNT satellization
│   │   ├── beta_crypto/agent.py         # On-chain analysis
│   │   ├── delta_crypto/agent.py        # Sentiment
│   │   └── padre_crypto/agent.py        # Consenso crypto
│   └── bolsa/                           # 4 agentes bursátiles
│       ├── alfa_bolsa/agent.py          # Technical analysis
│       ├── beta_bolsa/agent.py          # Macro analysis
│       ├── delta_bolsa/agent.py         # Régimen de mercado
│       └── padre_bolsa/agent.py         # Consenso bolsa
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
│   │   ├── crypto.py                    # CoinGecko + Binance + Bitso
│   │   ├── bolsa.py                     # Yahoo Finance + Alpha Vantage
│   │   └── telegram.py                  # Telegram Bot API
│   ├── pipeline/
│   │   ├── data_pipeline.py             # Pipeline maestro de datos
│   │   ├── layer_runners.py             # Runners por capa
│   │   └── legacy_loader.py             # Cargador de datos TITAN legacy
│   ├── database/
│   │   ├── schema.py                    # Schema SQLite + WAL + triggers
│   │   ├── repository.py                # CRUD + 12 queries analíticas
│   │   └── seed_nodos.py                # 125 nodos semilla (México + Ring of Fire)
│   ├── dashboard/
│   │   └── app.py                       # Dashboard Streamlit (9 tabs, 1433 líneas)
│   └── telegram/
│       └── bot.py                       # Bot Telegram para alertas
│
├── tests/                               # 312 tests
│   ├── test_snt_engine.py               # Tests SNT (satellization, friction, ASI, N-Body)
│   ├── test_agents.py                   # Tests de agentes (14 agentes)
│   ├── test_precursor.py                # Tests precursor (fantasma, scanner, muro, assertivity)
│   ├── test_schumann_filter.py          # Tests Schumann filter + DB schema (46 tests)
│   ├── test_api_connectors.py           # Tests de conectores API
│   ├── test_pipeline.py                 # Tests de pipeline + layer runners
│   └── test_infrastructure.py           # Tests de infraestructura (config, DB, telegram)
│
└── data/                                # Bases de datos SQLite
    └── SENTINEL_OMEGA_PRO.db            # DB principal (6 tablas)
```

---

## Funcionalidad Detallada

### Ciclo del Orquestador

1. **Crypto Layer** ejecuta primero → Alfa analiza satelización SNT, Beta analiza on-chain, Delta evalúa sentimiento → Padre genera consenso
2. **Bolsa Layer** ejecuta → Alfa analiza técnico, Beta analiza macro, Delta clasifica régimen → Padre genera consenso
3. **Datos financieros extraídos**: `fear_greed`, `VIX`, `BTC change` se pasan como correlación cruzada
4. **Geodynamic Layer** ejecuta con correlación financiera:
   - Alfa-1 ingiere datos NOAA OMNI (Bz, viento solar, protones)
   - Alfa-2 procesa imágenes Sentinel-2 (NDVI, clasificación espectral)
   - Beta-1 computa FFT de serie Kp + aplica filtro armónico Schumann
   - Beta-2 analiza SAR InSAR (deformación terrestre)
   - Delta evalúa topología N-Body de 125 nodos + datos atmosféricos
   - Padre genera consenso con pérdida asimétrica
5. **Fantasma V32** se calcula de las señales agregadas
6. **Scanner** evalúa los 15 tipos de precursor contra datos del ciclo
7. **Muro de los 5 Eventos** evalúa correlación de 5 dominios
8. Si hay alertas: despacho via Telegram + registro en SQLite

### Señales del Sistema

| Señal     | Significado                           | Uso                     |
|-----------|---------------------------------------|-------------------------|
| BULLISH   | Tendencia alcista (mercados)          | Crypto, Bolsa           |
| BEARISH   | Tendencia bajista (mercados)          | Crypto, Bolsa           |
| NEUTRAL   | Sin tendencia clara                   | Todas las capas         |
| WATCH     | Excitación coherente, monitorear      | Geodynamic (Schumann)   |
| ALERT     | Precursor confirmado, alertar         | Geodynamic              |
| NO_SIGNAL | Sin datos o sin análisis              | Todas las capas         |

---

## Instalación

```bash
# Clonar e instalar con todas las dependencias
pip install -e ".[all]"

# Solo módulo geodynamic
pip install -e ".[geodynamic]"

# Solo crypto
pip install -e ".[crypto]"
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
# Tests (312 tests, ejecutar desde /home/user/workspaces/)
python -m pytest sentinel_omega/tests/ -q

# Dashboard (9 tabs interactivas)
streamlit run sentinel_omega/infrastructure/dashboard/app.py

# Ciclo completo del orquestador (requiere APIs activas)
python -c "
from sentinel_omega.config.sentinel_config import SentinelOmegaConfig
from sentinel_omega.orchestrator import SentinelOrchestrator
orch = SentinelOrchestrator.create_with_live_pipelines(SentinelOmegaConfig())
results = orch.run_cycle()
print(orch.get_status())
"
```

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

> **Seguridad**: Todas las claves se cargan exclusivamente via `os.environ.get()`. Nunca se hardcodean tokens en el código. Las claves se rotan según se van usando.

---

## Linaje

| Versión  | Sistema          | Aportación                                           |
|----------|------------------|------------------------------------------------------|
| V32      | TITAN V32        | Fórmula Fantasma, Schumann WPC, 2 muros (Geo+Solar) |
| V46      | TITAN V46        | Asertividad, validación contra USGS, hits/misses     |
| V53      | TITAN V53        | Patrones WPC, Lorenz-X/Lyapunov, multi-horizonte     |
| v2.5     | Sentinel Omega   | 15 precursores, 5 muros, 125 nodos, 14 agentes, dashboard, filtro Schumann |

---

## Licencia

Proprietary — Fractal Core Research

**Autor**: Elán Zainos Corona
**Contacto**: elan.zainos.corona@gmail.com
