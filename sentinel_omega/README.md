# Sentinel Omega v2.5

**Plataforma de detección de precursores de eventos naturales.**

Sentinel Omega monitorea en tiempo real datos geofísicos, atmosféricos, solares, oceánicos y financieros para detectar precursores de terremotos, erupciones volcánicas, tormentas solares, tsunamis y otros eventos naturales.

> Sucesor de la familia de bots TITAN V32/V46/V53.
> Autor: Elán Zainos Corona — Fractal Core Research

---

## Arquitectura

```
                    ┌─────────────────────────────┐
                    │      ORCHESTRATOR            │
                    │  Ciclo: Crypto → Bolsa → Geo │
                    └──────────┬──────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │   CRYPTO    │    │    BOLSA    │    │ GEODYNAMIC  │
    │ Alfa/Beta/  │    │ Alfa/Beta/  │    │ Alfa-1/Alfa-2│
    │ Delta/Padre │    │ Delta/Padre │    │ Beta-1/Beta-2│
    └──────┬──────┘    └──────┬──────┘    │ Delta/Padre │
           │                   │          └──────┬──────┘
           └───────────┬───────┘                 │
                       │                         │
              Financial Data ──────────────► Precursor
                                              Scanner
                                                │
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
                                        └─────────────┘
```

## Fórmula Fantasma (TITAN V32)

```
fantasma = (abs(Bz)²) + (viento × 0.02) + (Schumann_WPC × 1.5)

Modificadores:
  + Presión atmosférica (< 1008 hPa → hasta +3.0)
  × Kp storm (≥ 5 → hasta ×1.5)
  + LOD anomaly (> 0.5 ms → hasta +2.0)
```

| Nivel      | Rango     |
|-----------|-----------|
| LOW       | < 5       |
| MODERATE  | 5 – 15    |
| HIGH      | 15 – 30   |
| CRITICAL  | ≥ 30      |

## 15 Tipos de Precursor

| #  | Tipo                     | Muro              | Ventana |
|----|-------------------------|--------------------|---------|
| 1  | Resonancia Schumann     | Solar/Geomagnético | 72h     |
| 2  | Silent Trigger (Calma)  | Solar/Geomagnético | 48h     |
| 3  | Enjambre Sísmico        | Geofísico          | 48h     |
| 4  | Blue Jet                | Atmosférico        | 72h     |
| 5  | Sprite Rojo             | Atmosférico        | 72h     |
| 6  | Niebla Tule             | Atmosférico        | 72h     |
| 7  | Tormenta Solar          | Solar/Geomagnético | 96h     |
| 8  | Perturbación Geomag.    | Solar/Geomagnético | 96h     |
| 9  | Huracán                 | Oceánico           | 120h    |
| 10 | Tsunami                 | Oceánico           | 24h     |
| 11 | Inferencia ML           | —                  | 48h     |
| 12 | Gamma-Ray Burst         | Solar/Geomagnético | 168h    |
| 13 | Precursor Volcánico     | Geofísico          | 72h     |
| 14 | Índice Fantasma         | Geofísico          | 72h     |
| 15 | Correlación Financiera  | Financiero/Social  | 72h     |

## Muro de los 5 Eventos

Breach cuando ≥ 3 muros están activos simultáneamente:

| Muro | Dominio              | Precursores                                    |
|------|---------------------|------------------------------------------------|
| 1    | GEOFÍSICO           | Enjambre Sísmico, Volcánico, Fantasma          |
| 2    | ATMOSFÉRICO         | Blue Jet, Sprite Rojo, Niebla Tule             |
| 3    | OCEÁNICO            | Tsunami, Huracán                                |
| 4    | SOLAR/GEOMAGNÉTICO  | Tormenta, Perturbación, Schumann, Silent, GRB  |
| 5    | FINANCIERO/SOCIAL   | Correlación Financiera                          |

## Filtro Fourier-Schumann

Beta-1 aplica un filtro armónico de Schumann al espectro FFT:
- Armónicos: 7.83, 14.3, 20.8, 27.3, 33.8 Hz
- Bins sub-armónicos se retienen, el resto se atenúa al 10%
- Coherencia armónica modula la confianza de la señal
- Frecuencia de Schumann en vivo (no hardcoded) escala los armónicos

## Base de Datos (SQLite)

6 tablas en `SENTINEL_OMEGA_PRO.db`:

- **TBL_PRECURSORES_COSMICOS** — Snapshot cósmico por ciclo (Bz, viento, protones, Kp, LOD, Schumann, fase lunar, fantasma)
- **TBL_NODOS_TOPOLOGIA** — 125 nodos N-Body (50 real, 50 ghost, 25 geobattery) con trigger de saturación
- **TBL_HISTORICO_SISMICO** — Catálogo USGS con deduplicación
- **TBL_DETECCIONES** — Log de precursores detectados
- **TBL_CICLOS** — Historial de ciclos del orquestador
- **TBL_MURO_EVENTOS** — Historial de breaches del Muro

## Topología: 125 Nodos

| Tipo        | Cantidad | Descripción                              |
|-------------|----------|------------------------------------------|
| Real        | 50       | Zonas sísmicas reales (México + Ring of Fire) |
| Ghost       | 50       | Nodos fantasma inferidos de gaps sísmicos |
| Geobattery  | 25       | Zonas de acumulación electroquímica       |

## Consenso Jerárquico

Cada capa tiene agentes subordinados y un Padre (Árbitro Supremo):

- **Alfa**: Datos primarios (OMNI/SNT/Technical)
- **Beta**: Análisis espectral/on-chain/macro
- **Delta**: Topología N-Body/sentimiento/régimen
- **Padre**: Consenso con pérdida asimétrica (miss=10×, false alarm=1×)

## API Sources

| Fuente          | Datos                                    | Auth      |
|----------------|------------------------------------------|-----------|
| NOAA SWPC      | Bz, solar wind, Kp, GOES X-ray           | Público   |
| USGS FDSN      | Catálogo sísmico mundial                  | Público   |
| Tomsk SRF      | Resonancia Schumann                       | Público   |
| IERS           | Length-of-Day (LOD)                       | Público   |
| ESA Copernicus | Sentinel-1 SAR, Sentinel-2 multispectral | Público   |
| OpenWeatherMap | Presión, temperatura, humedad, weather_id | API Key   |
| NOAA NHC       | Ciclones tropicales activos               | Público   |
| CoinGecko      | Dominancia BTC, market caps               | Público   |
| Binance        | OHLCV crypto                              | Público   |
| Yahoo Finance  | OHLCV acciones, VIX, ETFs                 | Público   |

## Instalación

```bash
pip install -e ".[all]"
```

## Ejecución

```bash
# Tests (312 tests)
python -m pytest sentinel_omega/tests/ -q

# Dashboard
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
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export OPENWEATHERMAP_KEY="..."
export COINGECKO_API_KEY="..."
export ALPHA_VANTAGE_KEY="..."
export BITSO_API_KEY="..."
export BITSO_API_SECRET="..."
```

## Licencia

Proprietary — Fractal Core Research
