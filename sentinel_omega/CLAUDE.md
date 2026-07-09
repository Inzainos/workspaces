# Sentinel Omega

Precursor detection platform for natural events.
Author: Elan Zainos Corona (Fractal Core Research)

## What this project does

Sentinel Omega detects **precursors of natural events** (earthquakes, volcanic activity, solar storms, tsunamis, etc.) using real-time geophysical data from NOAA, USGS, ESA, and other sources. It uses Shadow Node Theory (SNT) **only as the mathematical framework** (power law R(t) = a·t^b), not as the system's core purpose.

The system is the successor to the TITAN V32/V46/V53 bot family.

## Architecture — 6 Agents, Single System

```
Orchestrator → GeodynamicLayerRunner → 6 Agents → Padre Consensus
│
├── Alfa-1 (Geodynamic: Bz, solar wind, seismic) — 30yr training
│       ↑ validates
├── Alfa-2 (Satellite: ESA Sentinel) — 14yr training
│
├── Beta-1 (Schumann/cymatics/energy released) — 30yr training  ← HEARTBEAT
│       ↑ validates
├── Beta-2 (Air chemistry/atmospheric) — 14yr training
│
├── Delta  (Crypto + Bolsa + humor de la tierra) — 10yr training
│
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

**Consensus requires**: >= 2 families active + >= 2 alerts + schumann_correlation > 0.3

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

# Signature training over the backcast (Fase 1 reconocimiento + Fase 2 disciplina)
python sentinel_omega/launcher.py --entrenar

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
│   └── geodynamic/              # All 6 agents: alfa1, alfa2, beta1, beta2, delta, padre
├── infrastructure/
│   ├── api/                     # NOAA, USGS, Schumann, ESA, OWM, Crypto, Bolsa, Telegram
│   ├── pipeline/                # GeodynamicPipeline + GeodynamicLayerRunner + backcast
│   ├── database/                # SQLite schema, repository, 125-node seed
│   └── dashboard/               # Streamlit + Plotly dashboard (9 tabs)
├── data/                        # SQLite databases
└── tests/                       # 335 tests
```

> El repositorio raíz tiene un `AGENTS.md` (estándar neutral para cualquier
> agente de IA). Este `CLAUDE.md` es la guía específica de Claude Code y tiene
> prioridad para archivos dentro de `sentinel_omega/`.

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

Operational tables in `data/SENTINEL_OMEGA_PRO.db`:
- `TBL_PRECURSORES_COSMICOS` — Bz, viento, protones, Kp, LOD, Schumann, fase lunar, fantasma
- `TBL_NODOS_TOPOLOGIA` — 125 nodes (50 real + 50 ghost + 25 geobattery)
- `TBL_HISTORICO_SISMICO` — USGS seismic catalog
- `TBL_DETECCIONES` — Precursor detection log
- `TBL_CICLOS` — Orchestrator cycle history
- `TBL_MURO_EVENTOS` — Muro breach history

Learning/audit tables:
- `TBL_FIRMAS` — per-bot signature memory. Estado: nueva → observada → recurrente → consolidada (by recurrence). Only consolidadas are enforceable knowledge.
- `TBL_JUEZ_AUDITORIA` — Juez discipline ledger: ACIERTO / FALLO / FALSO_POSITIVO, asymmetric severity (miss of known firma = 20 base, miss = 10, false alarm = 1), recidivism-scaled.

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

All development on: `claude/sentinel-omega-architecture-j3c2kn`
