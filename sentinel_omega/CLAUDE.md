# Sentinel Omega

Precursor detection platform for natural events.
Author: Elan Zainos Corona (Fractal Core Research)

## What this project does

Sentinel Omega detects **precursors of natural events** (earthquakes, volcanic activity, solar storms, tsunamis, etc.) using real-time geophysical data from NOAA, USGS, ESA, and other sources. It uses Shadow Node Theory (SNT) **only as the mathematical framework** (power law R(t) = a·t^b), not as the system's core purpose.

The system is the successor to the TITAN V32/V46/V53 bot family.

## Architecture

```
Orchestrator
├── Crypto Layer    → Alfa/Beta/Delta/Padre → Consensus
├── Bolsa Layer     → Alfa/Beta/Delta/Padre → Consensus
└── Geodynamic Layer
    ├── Alfa-1 (NOAA OMNI Bz/Solar Wind)
    ├── Alfa-2 (ESA Sentinel-2 Satellite)
    ├── Beta-1 (Kp FFT + Schumann Harmonic Filter)
    ├── Beta-2 (Sentinel-1 SAR InSAR)
    ├── Delta  (N-Body Topology + Atmospheric)
    └── Padre  (Asymmetric Loss Consensus)
        ├── TITAN V32 Fantasma Risk Index
        ├── Precursor Scanner (15 types)
        └── Muro de los 5 Eventos
```

## Key formulas

- **Fantasma**: `(abs(bz)^2) + (viento*0.02) + (sch_wpc*1.5)` + pressure/Kp/LOD modifiers
- **Risk levels**: LOW (<5), MODERATE (5-15), HIGH (15-30), CRITICAL (>=30)
- **Asymmetric loss**: Miss penalty = 10x, False alarm = 1x
- **Schumann coherence**: Ratio of resonant-bin energy to total energy. > 0.3 with excitation = WATCH signal

## Running tests

```bash
# From the workspace root (/home/user/workspaces):
python -m pytest sentinel_omega/tests/ -q

# Single test file:
python -m pytest sentinel_omega/tests/test_precursor.py -v
```

**Important**: Always run from `/home/user/workspaces/`, not from inside `sentinel_omega/`.

## Running the dashboard

```bash
streamlit run sentinel_omega/infrastructure/dashboard/app.py
```

## Project structure

```
sentinel_omega/
├── orchestrator.py              # Master orchestrator — runs cycles
├── config/sentinel_config.py    # Central config (secrets via os.environ)
├── core/
│   ├── shared/
│   │   ├── agent_base.py        # BaseAgent, PadreAgent, SignalType, ConsensusResult
│   │   └── data_pipeline.py     # Pipeline base class
│   ├── precursor/
│   │   ├── risk_calculator.py   # TITAN V32 fantasma formula
│   │   ├── scanner.py           # 15-type precursor scanner
│   │   ├── muro_cinco_eventos.py # 5-wall cross-correlation engine
│   │   ├── precursor_types.py   # Type registry + detection functions
│   │   └── assertivity.py       # V46 prediction tracking
│   └── snt_engine/              # SNT math framework (satellization, friction, ASI, N-Body)
├── layers/
│   ├── geodynamic/              # Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Padre
│   ├── crypto/                  # Alfa, Beta, Delta, Padre
│   └── bolsa/                   # Alfa, Beta, Delta, Padre
├── infrastructure/
│   ├── api/                     # NOAA, USGS, Schumann, ESA, OWM, Crypto, Bolsa, Telegram
│   ├── pipeline/                # Data pipelines + layer runners
│   ├── database/                # SQLite schema, repository, 125-node seed
│   └── dashboard/               # Streamlit + Plotly dashboard (9 tabs)
├── data/                        # SQLite databases
└── tests/                       # 312 tests (7 test files)
```

## Security rules

- **NEVER hardcode API keys or tokens** — use `os.environ.get("KEY_NAME", "")`
- Keys will be rotated as used
- All secrets in `config/sentinel_config.py` use environment variables

## Environment variables

```
TELEGRAM_BOT_TOKEN    — Telegram alert dispatch
TELEGRAM_CHAT_ID      — Target chat for alerts
OPENWEATHERMAP_KEY    — Atmospheric data
BITSO_API_KEY         — Bitso exchange
BITSO_API_SECRET      — Bitso exchange
COINGECKO_API_KEY     — Market data
ALPHA_VANTAGE_KEY     — Stock market data
```

## Database (SQLite)

Tables in `data/SENTINEL_OMEGA_PRO.db`:
- `TBL_PRECURSORES_COSMICOS` — Bz, viento, protones, Kp, LOD, Schumann, fase lunar, fantasma
- `TBL_NODOS_TOPOLOGIA` — 125 nodes (50 real + 50 ghost + 25 geobattery)
- `TBL_HISTORICO_SISMICO` — USGS seismic catalog
- `TBL_DETECCIONES` — Precursor detection log
- `TBL_CICLOS` — Orchestrator cycle history
- `TBL_MURO_EVENTOS` — Muro breach history
- Trigger: `trg_nodo_saturacion` caps saturacion at 1.0

## Muro de los 5 Eventos

Five walls of cross-correlation. Breach when >= 3 walls active:

1. **GEOFISICO**: Seismic Cluster, Volcanico, Fantasma
2. **ATMOSFERICO**: Blue Jet, Sprite Rojo, Niebla Tule
3. **OCEANICO**: Tsunami, Huracan
4. **SOLAR/GEOMAGNETICO**: Tormenta Solar, Perturbacion, Schumann, Silent Trigger, GRB
5. **FINANCIERO/SOCIAL**: Correlacion Financiera

## Orchestrator cycle order

1. Crypto + Bolsa layers run first
2. Financial data extracted (fear_greed, VIX, BTC change)
3. Geodynamic layer runs with financial cross-correlation
4. Scanner evaluates 15 precursor types
5. Muro evaluates 5-wall correlation
6. Alerts dispatched via Telegram

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

All development on: `claude/sentinel-omega-architecture-j3c2kn`
