# Sentinel Omega — Agents Registry (v2.5.4)

This document defines the roles, logic, and hierarchy of the agents within the Sentinel Omega system.

## 1. Hierarchy of Consensus (The Path to Alert)
The system follows a tiered validation process. A signal must climb this ladder to trigger a final alert:

**SNT Families** $\rightarrow$ **Padre** $\rightarrow$ **Juez** (auditor)

1. **SNT Families (Alfa, Beta, Delta)**: The first line of detection. Consists of specialized bots looking for patterns in space weather, cymatics, and financial sentiment.
2. **Padre (The Arbiter)**: Hierarchical cross-family validator. Consensus requires ≥2 families active + ≥2 alerts + corroboration from the schumann_cymatics family (>0.3). Junior→Senior demotion (WATCH @50%) applies if unconfirmed.
3. **Omega**: The global correlator. Validates if the SNT signals align with the "Cosmic Rhythm" (lunar phase, Schumann activity, solar envelopes). Lifts the confidence ceiling when it corroborates.
4. **Loki**: Solar-rotation resonance (see below) — lifts confidence only when its 26–29 day window confirms. No longer a "final probability arbiter": the Bayesian collapse it used to be was measured dead (~1e-112) and redesigned 2026-10-12.

---

## 2. Agent Definitions

### 🟦 SNT Families (The Detectors)
- **Alfa-1 (Space Weather)**: Monitors Bz, solar wind, and seismic clusters.
- **Alfa-2 (Satellite)**: ESA Sentinel thermal **by zone precedent** (a zone's
  current temp above its OWN historical max = sin precedente; ≥1 zone → WATCH,
  ≥3 simultaneous → ALERT) + **GOES X-ray flares** (M-class → WATCH, X-class →
  ALERT; took over from jupiter on 2026-10-18). Live-accumulating, no backcast.
- **Beta-1 (The Artist)**: Generates the **Cymatic Figure**. Captures the current vibration of the system as a vector.
- **Beta-2 (The Analyst)**: Interprets the Figure. Compares it against the historical library to find magnitude-specific replicas. Atmospheric inputs: OWM pressure/chemistry with honest NULLs + the 5-day/3h **forecast** (ingested for observation since 2026-10-19; no alert rule until its live distribution is measured).
- **Delta (Financial Sentiment)**: Monitors VIX, Fear & Greed, Crypto Topology, and **public attention** (`trends_mean`: Google Trends with Wikipedia-pageviews fallback when Google 400s — source marked in `tbl_trends_vivo.fuente`). **Techo WATCH: NUNCA emite ALERT** — el estrés financiero es CONTEXTO para el Padre, no predicción (`delta/agent.py`: la vía ALERT está capada a propósito; corregido contra el código el 2026-10-20, este párrafo decía "Active Vote: emits ALERT").

### 🟪 Omega (The Correlator)
- **Role**: Validates the SNT consensus against global cosmic cycles.
- **Logic**: If $\ge 2$ families agree and the schumann_cymatics family corroborates ($> 0.3$), Omega elevates the signal. (Renamed 2026-10-10: the gate was mislabeled "Schumann correlation" but read no Schumann data and demanded beta1 specifically — 0 ALERTs in 4,566 cycles.)

### 🟥 Loki (Solar Rotation Resonance)
- **Role**: The old Bayesian collapse (Gauss-Jordan → Fourier → φ) is DEAD —
  measured ~1e-112, decorative (bitácoras 2026-10-11/12). Redesigned
  2026-10-12 to its live route: the **solar rotation resonance** — a storm
  Kp≥5 makes a recurrent storm 26–29 days later (one Carrington cycle);
  gain 3.4× measured over 32 years. Loki only lifts confidence when the
  resonance window confirms.

### ⚖️ The Judge (The Auditor)
- **Role**: Cold auditor of truth.
- **Rule**: Compares predictions against the USGS catalog.
- **Penalty**: Applies asymmetric loss. If the **Father** fails to corroborate a signal that later becomes a hit, the Father and the informing bot receive a severe weight penalty.

---

## 3. Operational Script Contract (Pipeline)

Para operación y auditoría script-by-script, este registro de agentes se complementa con:
- `README.md` → sección **"Scripts auxiliares del pipeline (auditados)"**.
- `CLAUDE.md` → sección **"Pipeline scripts (operational map)"**.
- `CHANGELOG.md` → decisiones operativas vigentes (por ejemplo, scheduler deshabilitado para evitar duplicidad).

Regla: cambios en comportamiento de pipeline deben reflejarse en esas secciones en el mismo PR para mantener contrato código↔documentación.
