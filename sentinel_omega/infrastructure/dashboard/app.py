"""
Sentinel Omega — Command Dashboard
Precursor detection platform for natural events.
Launch: streamlit run sentinel_omega/infrastructure/dashboard/app.py
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from sentinel_omega.config.sentinel_config import SentinelOmegaConfig
from sentinel_omega.core.snt_engine.satellization import SatellizationEngine, DominanceRegime
from sentinel_omega.core.snt_engine.friction import InstitutionalFrictionCalculator, FrictionLevel
from sentinel_omega.core.snt_engine.asi import AtomicSovereigntyIndex
from sentinel_omega.core.snt_engine.nbody import NBodyMatrix
from sentinel_omega.core.shared.agent_base import SignalType
from sentinel_omega.core.precursor.risk_calculator import (
    PrecursorRisk,
    classify_risk,
    RISK_THRESHOLDS,
)
from sentinel_omega.core.precursor.precursor_types import (
    PrecursorType,
    PRECURSOR_DISPLAY_NAMES,
)
from sentinel_omega.core.precursor.muro_cinco_eventos import (
    WALL_GEOFISICO,
    WALL_ATMOSFERICO,
    WALL_OCEANICO,
    WALL_SOLAR,
    WALL_FINANCIERO,
    WALL_MEMBERS,
)
from sentinel_omega.infrastructure.database.schema import get_connection
from sentinel_omega.infrastructure.database.repository import SentinelRepository
from sentinel_omega.infrastructure.database.seed_nodos import SEED_NODOS

# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sentinel Omega",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

SIGNAL_COLORS = {
    "BULLISH": "#00c853",
    "bullish": "#00c853",
    "BEARISH": "#ff1744",
    "bearish": "#ff1744",
    "NEUTRAL": "#ffc107",
    "neutral": "#ffc107",
    "WATCH": "#ff9100",
    "watch": "#ff9100",
    "ALERT": "#d500f9",
    "alert": "#d500f9",
    "NO_SIGNAL": "#757575",
    "no_signal": "#757575",
}

RISK_COLORS = {
    "LOW": "#00c853",
    "MODERATE": "#ffc107",
    "HIGH": "#ff9100",
    "CRITICAL": "#ff1744",
}

WALL_ICONS = {
    WALL_GEOFISICO: "🌋",
    WALL_ATMOSFERICO: "🌩️",
    WALL_OCEANICO: "🌊",
    WALL_SOLAR: "☀️",
    WALL_FINANCIERO: "📊",
}

REGIME_COLORS = {
    DominanceRegime.CONVERGENCE: "#00c853",
    DominanceRegime.EQUILIBRIUM: "#ffc107",
    DominanceRegime.SATELLIZATION_GRADUAL: "#ffab40",
    DominanceRegime.SATELLIZATION_ACTIVE: "#ff9100",
    DominanceRegime.ROCHE_RADIUS: "#ff1744",
    DominanceRegime.EXTREME: "#d50000",
    DominanceRegime.LEAPFROG: "#2979ff",
}

# ── Session State ────────────────────────────────────────────────────

if "config" not in st.session_state:
    st.session_state.config = SentinelOmegaConfig()
if "snt" not in st.session_state:
    st.session_state.snt = SatellizationEngine()
if "friction_calc" not in st.session_state:
    st.session_state.friction_calc = InstitutionalFrictionCalculator()
if "asi_calc" not in st.session_state:
    st.session_state.asi_calc = AtomicSovereigntyIndex()
if "nbody" not in st.session_state:
    st.session_state.nbody = NBodyMatrix()
if "repo" not in st.session_state:
    st.session_state.repo = SentinelRepository()


def get_repo() -> SentinelRepository:
    return st.session_state.repo


# ── Sidebar ──────────────────────────────────────────────────────────

def render_sidebar():
    cfg = st.session_state.config
    st.sidebar.title("⚡ Sentinel Omega")
    st.sidebar.caption(f"v{cfg.version} — Precursor Detection Platform")
    st.sidebar.caption(f"{cfg.author}")
    st.sidebar.divider()

    st.sidebar.subheader("Active Layers")
    active = {k: v for k, v in cfg.layers.items() if v.enabled}
    for name, layer_cfg in active.items():
        emoji = {"geodynamic": "🌍", "crypto": "₿", "bolsa": "📈"}.get(name, "⚡")
        st.sidebar.markdown(f"{emoji} **{name.upper()}** — {layer_cfg.refresh_interval_s}s")

    st.sidebar.divider()
    st.sidebar.subheader("Location")
    st.sidebar.markdown(f"📍 {cfg.coordinates.get('location', 'Unknown')}")
    st.sidebar.markdown(f"Lat: {cfg.coordinates.get('lat')}, Lon: {cfg.coordinates.get('lon')}")

    st.sidebar.divider()
    st.sidebar.subheader("SNT Parameters")
    st.sidebar.markdown(f"**Roche**: b ≥ {cfg.snt.roche_threshold}")
    st.sidebar.markdown(f"**Equilibrium**: ±{cfg.snt.equilibrium_band}")

    return list(active.keys())


# ══════════════════════════════════════════════════════════════════════
# TAB 1: Precursor Risk (Fantasma)
# ══════════════════════════════════════════════════════════════════════

def render_precursor_risk():
    st.subheader("Índice Fantasma — TITAN V32 Precursor Risk")

    repo = get_repo()
    records = repo.get_precursores_cosmicos(limit=50)

    if not records:
        st.info("No hay datos de precursores cósmicos registrados. Ejecuta un ciclo del orquestador para alimentar la DB.")
        _render_fantasma_demo()
        return

    latest = records[0]
    fantasma = latest["fantasma"]
    risk_level = latest["nivel_riesgo"]
    risk_color = RISK_COLORS.get(risk_level, "#757575")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fantasma Index", f"{fantasma:.2f}")
    col2.metric("Risk Level", risk_level)
    col3.metric("Schumann", f"{latest['schumann_hz']:.2f} Hz")
    col4.metric("Kp", f"{latest['kp']:.1f}")

    c1, c2 = st.columns([2, 1])

    with c1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=fantasma,
            title={"text": "Fantasma Risk Index"},
            gauge={
                "axis": {"range": [0, 50], "tickwidth": 1},
                "bar": {"color": risk_color},
                "steps": [
                    {"range": [0, 5], "color": "#e8f5e9"},
                    {"range": [5, 15], "color": "#fff9c4"},
                    {"range": [15, 30], "color": "#ffe0b2"},
                    {"range": [30, 50], "color": "#ffcdd2"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 30,
                },
            },
        ))
        fig.update_layout(height=300, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**Componentes:**")
        st.markdown(f"- **Bz²**: {latest['bz_nT']:.1f} nT")
        st.markdown(f"- **Viento**: {latest['viento_km_s']:.0f} km/s")
        st.markdown(f"- **Schumann**: {latest['schumann_hz']:.2f} Hz ({latest['schumann_activity']:.0f}%)")
        st.markdown(f"- **Presión**: {latest['presion_hpa']:.0f} hPa")
        st.markdown(f"- **LOD**: {latest['lod_ms']:.2f} ms")
        st.markdown(f"- **Fase Lunar**: {latest['fase_lunar']:.2f}")
        st.markdown(f"- **Protones**: {latest['protones']:.1f}")

    if len(records) > 1:
        st.markdown("---")
        st.markdown("**Historial Fantasma (últimos 50 ciclos)**")
        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["time"], y=df["fantasma"],
            mode="lines+markers", name="Fantasma",
            line=dict(color="#d500f9"),
        ))
        fig.add_hline(y=5, line_dash="dot", line_color="#ffc107", annotation_text="MODERATE")
        fig.add_hline(y=15, line_dash="dot", line_color="#ff9100", annotation_text="HIGH")
        fig.add_hline(y=30, line_dash="dash", line_color="#ff1744", annotation_text="CRITICAL")
        fig.update_layout(
            yaxis_title="Fantasma Index",
            height=300, template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_fantasma_demo():
    st.markdown("**Demo: Composición del Fantasma**")
    rng = np.random.default_rng(int(time.time()) % 1000)
    bz = rng.normal(-3, 5)
    viento = max(0, rng.normal(400, 100))
    sch_wpc = max(0, rng.normal(0.5, 0.3))
    pressure = rng.normal(1010, 8)
    kp = max(0, rng.normal(3, 2))
    lod = rng.normal(0.2, 0.3)

    bz_c = abs(bz) ** 2
    wind_c = viento * 0.02
    sch_c = sch_wpc * 1.5
    fantasma = bz_c + wind_c + sch_c

    pressure_mod = 0.0
    if pressure < 1008:
        pressure_mod = min(3.0, (1008 - pressure) / 5.0)
        fantasma += pressure_mod

    kp_mod = 1.0
    if kp >= 5:
        kp_mod = 1.0 + (kp - 5.0) * 0.1
        fantasma *= kp_mod

    risk = classify_risk(fantasma)
    risk_color = RISK_COLORS.get(risk, "#757575")

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fantasma,
            title={"text": "Fantasma (Demo)"},
            gauge={
                "axis": {"range": [0, 50]},
                "bar": {"color": risk_color},
                "steps": [
                    {"range": [0, 5], "color": "#e8f5e9"},
                    {"range": [5, 15], "color": "#fff9c4"},
                    {"range": [15, 30], "color": "#ffe0b2"},
                    {"range": [30, 50], "color": "#ffcdd2"},
                ],
            },
        ))
        fig.update_layout(height=300, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric("Risk Level", risk)
        st.markdown(f"Bz² = `{bz_c:.2f}` (Bz={bz:.1f} nT)")
        st.markdown(f"Wind = `{wind_c:.2f}` ({viento:.0f} km/s)")
        st.markdown(f"Schumann = `{sch_c:.2f}` (WPC={sch_wpc:.2f})")
        st.markdown(f"Pressure mod = `+{pressure_mod:.2f}` ({pressure:.0f} hPa)")
        st.markdown(f"Kp mod = `×{kp_mod:.2f}` (Kp={kp:.1f})")


# ══════════════════════════════════════════════════════════════════════
# TAB 2: Muro de los 5 Eventos
# ══════════════════════════════════════════════════════════════════════

def render_muro():
    st.subheader("Muro de los 5 Eventos — Cross-Correlation Engine")

    repo = get_repo()
    breaches = repo.get_muro_breaches(limit=20)
    cycles = repo.get_ciclos(limit=1)

    wall_names = [WALL_GEOFISICO, WALL_ATMOSFERICO, WALL_OCEANICO, WALL_SOLAR, WALL_FINANCIERO]
    wall_fields = ["wall_geofisico", "wall_atmosferico", "wall_oceanico", "wall_solar", "wall_financiero"]

    if cycles:
        latest = cycles[0]
        walls_active = latest["muro_walls_active"]
        is_breach = latest["muro_breach"]
    else:
        walls_active = 0
        is_breach = False

    c1, c2, c3 = st.columns(3)
    c1.metric("Walls Active", f"{walls_active}/5")
    c2.metric("Breach", "YES" if is_breach else "NO")
    c3.metric("Historical Breaches", len(breaches))

    st.markdown("---")
    cols = st.columns(5)

    for i, (wall_name, wall_field) in enumerate(zip(wall_names, wall_fields)):
        with cols[i]:
            icon = WALL_ICONS.get(wall_name, "⬜")
            members = WALL_MEMBERS.get(wall_name, set())
            member_names = [PRECURSOR_DISPLAY_NAMES.get(m, m.value) for m in members]

            if breaches and wall_field in breaches[0]:
                active = bool(breaches[0].get(wall_field, 0))
            elif cycles and wall_field in cycles[0]:
                active = bool(cycles[0].get(wall_field, 0))
            else:
                active = False

            color = "#00c853" if active else "#616161"
            border = f"3px solid {color}"

            st.markdown(
                f"<div style='padding:16px;border-radius:12px;border:{border};"
                f"text-align:center;background:rgba(0,0,0,0.03)'>"
                f"<h2 style='margin:0'>{icon}</h2>"
                f"<b style='color:{color}'>{wall_name}</b><br>"
                f"<small>{'ACTIVO' if active else 'INACTIVO'}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )
            for mn in member_names:
                st.caption(f"• {mn}")

    if breaches:
        st.markdown("---")
        st.markdown("**Historial de Breaches**")
        df = pd.DataFrame(breaches)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        display_cols = ["time", "walls_active", "correlation_score", "risk_label"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available].head(20), use_container_width=True, hide_index=True)
    else:
        st.info("No se han registrado breaches del Muro. El Muro se activa cuando ≥3 muros están activos simultáneamente.")

    st.markdown("---")
    st.markdown("**Esquema de Correlación**")
    fig = go.Figure()
    categories = [w.split("/")[0] for w in wall_names]
    categories.append(categories[0])

    demo_values = [0.6, 0.3, 0.1, 0.8, 0.4]
    demo_values.append(demo_values[0])

    fig.add_trace(go.Scatterpolar(
        r=demo_values,
        theta=categories,
        fill="toself",
        name="Correlation Score",
        fillcolor="rgba(213,0,249,0.2)",
        line=dict(color="#d500f9"),
    ))
    fig.add_trace(go.Scatterpolar(
        r=[0.6] * 6,
        theta=categories,
        name="Breach Threshold",
        line=dict(color="#ff1744", dash="dash"),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        height=400, template="plotly_dark",
        title="Radar de Correlación Multi-Dominio",
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 3: Precursor Scanner
# ══════════════════════════════════════════════════════════════════════

def render_scanner():
    st.subheader("Precursor Scanner — Detecciones Activas")

    repo = get_repo()
    detections = repo.get_detecciones(limit=100)

    if not detections:
        st.info("No hay detecciones registradas. Ejecuta un ciclo del orquestador para escanear precursores.")
        _render_precursor_types_reference()
        return

    col1, col2, col3 = st.columns(3)
    high_conf = [d for d in detections if d["confidence"] >= 0.7]
    col1.metric("Total Detecciones", len(detections))
    col2.metric("Alta Confianza (≥70%)", len(high_conf))
    unique_types = set(d["tipo"] for d in detections)
    col3.metric("Tipos Activos", len(unique_types))

    st.markdown("---")

    df = pd.DataFrame(detections)
    df["time"] = pd.to_datetime(df["timestamp"], unit="s")
    df["confidence_pct"] = (df["confidence"] * 100).round(1)

    display_df = df[["time", "tipo", "display_name", "station", "confidence_pct"]].copy()
    display_df.columns = ["Timestamp", "Tipo", "Nombre", "Estación", "Confianza (%)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        type_counts = df["tipo"].value_counts()
        fig = go.Figure(go.Bar(
            x=type_counts.index,
            y=type_counts.values,
            marker_color="#d500f9",
        ))
        fig.update_layout(
            title="Detecciones por Tipo",
            yaxis_title="Count",
            height=350, template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure(go.Histogram(
            x=df["confidence"],
            nbinsx=20,
            marker_color="#2979ff",
        ))
        fig.update_layout(
            title="Distribución de Confianza",
            xaxis_title="Confidence",
            yaxis_title="Count",
            height=350, template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_precursor_types_reference():
    st.markdown("**Referencia: 15 Tipos de Precursor**")
    data = []
    for pt in PrecursorType:
        dn = PRECURSOR_DISPLAY_NAMES.get(pt, pt.value)
        wall = "—"
        for wname, members in WALL_MEMBERS.items():
            if pt in members:
                wall = wname
                break
        data.append({"Tipo": pt.value, "Nombre": dn, "Muro": wall})
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 4: Topología 125 Nodos
# ══════════════════════════════════════════════════════════════════════

def render_topology():
    st.subheader("Topología N-Body — 125 Nodos")

    repo = get_repo()
    nodes = repo.get_nodos()

    if not nodes:
        st.info("Nodos no cargados en la DB. Usando datos seed.")
        nodes = SEED_NODOS

    c1, c2, c3 = st.columns(3)
    real = [n for n in nodes if n.get("tipo") == "real"]
    ghost = [n for n in nodes if n.get("tipo") == "ghost"]
    geobat = [n for n in nodes if n.get("tipo") == "geobattery"]
    c1.metric("Real Nodes", len(real))
    c2.metric("Ghost Nodes", len(ghost))
    c3.metric("Geobattery Nodes", len(geobat))

    tipo_colors = {"real": "#00c853", "ghost": "#ff9100", "geobattery": "#2979ff"}
    tipo_sizes = {"real": 10, "ghost": 7, "geobattery": 12}

    fig = go.Figure()

    for tipo in ["real", "ghost", "geobattery"]:
        subset = [n for n in nodes if n.get("tipo") == tipo]
        if not subset:
            continue
        lats = [n["lat"] for n in subset]
        lons = [n["lon"] for n in subset]
        names = [n.get("nombre", f"Node {n.get('node_id', '?')}") for n in subset]
        cond = [n.get("conductividad", n.get("conductividad_telurica", 0)) for n in subset]

        hover = [
            f"{name}<br>Lat: {lat:.2f}, Lon: {lon:.2f}<br>"
            f"Conductividad: {c:.2f}<br>Region: {n.get('region', '—')}"
            for name, lat, lon, c, n in zip(names, lats, lons, cond, subset)
        ]

        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons,
            text=hover,
            hoverinfo="text",
            name=tipo.capitalize(),
            marker=dict(
                size=tipo_sizes[tipo],
                color=tipo_colors[tipo],
                opacity=0.8,
                line=dict(width=1, color="white"),
            ),
        ))

    fig.update_geos(
        showland=True, landcolor="#1a1a2e",
        showocean=True, oceancolor="#0d1b2a",
        showcountries=True, countrycolor="#444",
        showcoastlines=True, coastlinecolor="#555",
        projection_type="natural earth",
        center=dict(lat=19, lon=-99),
    )
    fig.update_layout(
        title="Mapa de Nodos — Ring of Fire + Mexico Focus",
        height=550,
        template="plotly_dark",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("**Detalle de Nodos por Región**")
    region_filter = st.selectbox(
        "Filtrar por región",
        ["All"] + sorted(set(n.get("region", "—") for n in nodes)),
    )
    filtered = nodes if region_filter == "All" else [
        n for n in nodes if n.get("region", "—") == region_filter
    ]

    table_data = []
    for n in filtered:
        table_data.append({
            "ID": n.get("node_id", "—"),
            "Nombre": n.get("nombre", "—"),
            "Tipo": n.get("tipo", "—"),
            "Lat": n.get("lat", 0),
            "Lon": n.get("lon", 0),
            "Conductividad": n.get("conductividad", n.get("conductividad_telurica", 0)),
            "Energía": n.get("energia", n.get("energia_acumulada", 0)),
            "Saturación": n.get("saturacion", 0),
            "Región": n.get("region", "—"),
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 5: Histórico Sísmico
# ══════════════════════════════════════════════════════════════════════

def render_sismico():
    st.subheader("Histórico Sísmico — Catálogo USGS")

    repo = get_repo()
    total = repo.count_sismos()

    if total == 0:
        st.info("No hay datos sísmicos en la DB. Se poblarán cuando el pipeline USGS se ejecute.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Eventos", f"{total:,}")
    col2.metric("M5.0+", f"{repo.count_sismos(min_magnitude=5.0):,}")
    col3.metric("M7.0+", f"{repo.count_sismos(min_magnitude=7.0):,}")

    min_mag = st.slider("Magnitud mínima", 0.0, 9.0, 4.0, 0.5)
    sismos = repo.get_sismos(min_magnitude=min_mag, limit=500)

    if sismos:
        df = pd.DataFrame(sismos)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")

        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Scattergeo(
                lat=df["lat"], lon=df["lon"],
                text=[
                    f"M{row['magnitude']:.1f} — {row['region']}<br>{row.get('source', 'USGS')}"
                    for _, row in df.iterrows()
                ],
                hoverinfo="text",
                marker=dict(
                    size=df["magnitude"] * 2,
                    color=df["magnitude"],
                    colorscale="Hot",
                    showscale=True,
                    colorbar=dict(title="Mag"),
                ),
            ))
            fig.update_geos(
                showland=True, landcolor="#1a1a2e",
                showocean=True, oceancolor="#0d1b2a",
                projection_type="natural earth",
            )
            fig.update_layout(
                title=f"Eventos ≥ M{min_mag:.1f} (últimos {len(df)})",
                height=450, template="plotly_dark",
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = go.Figure(go.Histogram(
                x=df["magnitude"],
                nbinsx=30,
                marker_color="#ff9100",
            ))
            fig.update_layout(
                title="Distribución de Magnitudes",
                xaxis_title="Magnitud",
                yaxis_title="Frecuencia",
                height=450, template="plotly_dark",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df[["time", "magnitude", "depth_km", "region", "lat", "lon", "source"]].head(50),
            use_container_width=True, hide_index=True,
        )


# ══════════════════════════════════════════════════════════════════════
# TAB 6: Layer Signals (existing, cleaned up)
# ══════════════════════════════════════════════════════════════════════

def generate_demo_signals():
    rng = np.random.default_rng(int(time.time()) % 1000)
    layers = {
        "geodynamic": {
            "agents": {
                "Alfa-1 (Bz/OMNI)": {"signal": "NEUTRAL", "confidence": 0.3, "bz_mean": round(rng.normal(-2, 3), 1)},
                "Beta-1 (Kp/FFT+Schumann)": {"signal": "NEUTRAL", "confidence": 0.3, "dominant_period_h": round(rng.uniform(6, 48), 1), "schumann_coherence": round(rng.uniform(0, 0.5), 2)},
                "Delta (Topology)": {"signal": "NEUTRAL", "confidence": 0.3, "power_law_b": round(rng.normal(-0.5, 0.2), 3)},
            },
            "padre": {"consensus": False, "signal": "NO_SIGNAL", "confidence": 0.0},
        },
        "crypto": {
            "agents": {
                "Alfa-Crypto (SNT)": {"signal": rng.choice(["BULLISH", "BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.8), 2)},
                "Beta-Crypto (On-Chain)": {"signal": rng.choice(["BULLISH", "BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.8), 2)},
                "Delta-Crypto (Sentiment)": {"signal": rng.choice(["BULLISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.7), 2)},
            },
            "padre": {"consensus": False, "signal": "NEUTRAL", "confidence": 0.2},
        },
        "bolsa": {
            "agents": {
                "Alfa-Bolsa (Technical)": {"signal": rng.choice(["BULLISH", "BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.75), 2)},
                "Beta-Bolsa (Macro)": {"signal": rng.choice(["BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.7), 2)},
                "Delta-Bolsa (Regime)": {"signal": "NEUTRAL", "confidence": 0.3, "vix": round(rng.uniform(12, 35), 1)},
            },
            "padre": {"consensus": False, "signal": "NEUTRAL", "confidence": 0.2},
        },
    }
    return layers


def render_layer_signals(signals: dict):
    st.subheader("Layer Consensus Status")
    cols = st.columns(len(signals))
    emojis = {"geodynamic": "🌍", "crypto": "₿", "bolsa": "📈"}

    for i, (layer_name, layer_data) in enumerate(signals.items()):
        with cols[i]:
            padre = layer_data["padre"]
            signal = padre["signal"]
            color = SIGNAL_COLORS.get(signal, "#757575")

            st.markdown(f"### {emojis.get(layer_name, '⚡')} {layer_name.upper()}")
            st.markdown(
                f"<div style='padding:12px;border-radius:8px;border-left:4px solid {color};"
                f"background:rgba(0,0,0,0.05)'>"
                f"<b>Padre:</b> <span style='color:{color}'>{signal}</span><br>"
                f"<b>Confidence:</b> {padre['confidence']:.0%}<br>"
                f"<b>Consensus:</b> {'Yes' if padre['consensus'] else 'No'}"
                f"</div>",
                unsafe_allow_html=True,
            )

            st.markdown("**Agent Signals:**")
            for agent_name, agent_data in layer_data["agents"].items():
                sig = agent_data["signal"]
                conf = agent_data["confidence"]
                sig_color = SIGNAL_COLORS.get(sig, "#757575")
                extras = {k: v for k, v in agent_data.items() if k not in ("signal", "confidence")}
                extra_str = " · ".join(f"{k}={v}" for k, v in extras.items())
                st.markdown(
                    f"<span style='color:{sig_color}'>●</span> **{agent_name}** — "
                    f"{sig} ({conf:.0%}) {extra_str}",
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════
# TAB 7: SNT Analysis (existing)
# ══════════════════════════════════════════════════════════════════════

def generate_demo_satellization():
    rng = np.random.default_rng(int(time.time()) % 1000)
    t = np.arange(1, 101, dtype=float)
    scenarios = {
        "BTC/ETH Dominance": (2.0, 0.35 + rng.normal(0, 0.05)),
        "BTC/SOL Dominance": (1.5, 0.65 + rng.normal(0, 0.08)),
        "SPY/QQQ Ratio": (1.1, -0.15 + rng.normal(0, 0.03)),
        "Kp Intensity": (3.0, 0.02 + rng.normal(0, 0.01)),
    }
    results = {}
    snt = st.session_state.snt
    for name, (a_true, b_true) in scenarios.items():
        noise = rng.normal(0, 0.02 * a_true, len(t))
        ratio = a_true * np.power(t, b_true) + np.abs(noise)
        ratio = np.maximum(ratio, 1e-6)
        try:
            result = snt.fit_ratio(t, ratio)
            results[name] = {"result": result, "t": t, "ratio": ratio}
        except ValueError:
            pass
    return results


def render_satellization_analysis(results: dict):
    st.subheader("SNT Satellization — R(t) = a·t^b")
    if not results:
        st.warning("No satellization results to display.")
        return

    names = list(results.keys())
    b_values = [results[n]["result"].b for n in names]
    regimes = [results[n]["result"].regime for n in names]
    colors = [REGIME_COLORS.get(r, "#757575") for r in regimes]

    cols = st.columns(2)
    with cols[0]:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=names, y=b_values,
            marker_color=colors,
            text=[f"b={b:.3f}" for b in b_values],
            textposition="outside",
        ))
        fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Roche Radius")
        fig.add_hline(y=0.3, line_dash="dot", line_color="orange", annotation_text="Active")
        fig.add_hrect(y0=-0.1, y1=0.05, fillcolor="yellow", opacity=0.1, annotation_text="Equilibrium")
        fig.update_layout(
            title="Satellization Exponent (b)", yaxis_title="b",
            height=400, template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    with cols[1]:
        fig = go.Figure()
        for name, data in results.items():
            regime = data["result"].regime
            color = REGIME_COLORS.get(regime, "#757575")
            fig.add_trace(go.Scatter(
                x=data["t"], y=data["ratio"],
                mode="lines", name=f"{name} (b={data['result'].b:.3f})",
                line=dict(color=color),
            ))
            a, b = data["result"].a, data["result"].b
            fig.add_trace(go.Scatter(
                x=data["t"], y=a * np.power(data["t"], b),
                mode="lines", name=f"{name} fit",
                line=dict(color=color, dash="dash"), showlegend=False,
            ))
        fig.update_layout(
            title="Power Law Fits", xaxis_title="t", yaxis_title="R(t)",
            height=400, template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    r2_values = [results[n]["result"].r_squared for n in names]
    regime_df = pd.DataFrame({
        "Domain": names,
        "b": [f"{b:.4f}" for b in b_values],
        "R²": [f"{r:.4f}" for r in r2_values],
        "Regime": [r.value for r in regimes],
    })
    st.dataframe(regime_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 8: Cycle History
# ══════════════════════════════════════════════════════════════════════

def render_cycle_history():
    st.subheader("Historial de Ciclos del Orquestador")

    repo = get_repo()
    cycles = repo.get_ciclos(limit=50)

    if not cycles:
        st.info("No hay ciclos registrados. El orquestador los registrará al ejecutarse.")
        return

    df = pd.DataFrame(cycles)
    df["time"] = pd.to_datetime(df["timestamp"], unit="s")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Ciclos", len(cycles))
    alerts = [c for c in cycles if c["geo_signal"] == "alert"]
    col2.metric("Geo Alerts", len(alerts))
    total_precursors = sum(c["precursors_count"] for c in cycles)
    col3.metric("Total Precursors", total_precursors)
    total_breaches = sum(1 for c in cycles if c["muro_breach"])
    col4.metric("Muro Breaches", total_breaches)

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=["Fantasma Index por Ciclo", "Precursores + Muro Walls"],
        shared_xaxes=True,
    )
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["fantasma"],
        mode="lines+markers", name="Fantasma",
        line=dict(color="#d500f9"),
    ), row=1, col=1)
    fig.add_hline(y=15, line_dash="dot", line_color="#ff9100", row=1, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#ff1744", row=1, col=1)

    fig.add_trace(go.Bar(
        x=df["time"], y=df["precursors_count"],
        name="Precursors", marker_color="#2979ff",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["muro_walls_active"],
        mode="lines+markers", name="Muro Walls",
        line=dict(color="#ff9100"),
    ), row=2, col=1)

    fig.update_layout(height=500, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    display_cols = [
        "time", "geo_signal", "geo_confidence", "fantasma",
        "nivel_riesgo", "precursors_count", "muro_walls_active", "muro_breach",
    ]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available].head(50), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# Main App
# ══════════════════════════════════════════════════════════════════════

def main():
    active_layers = render_sidebar()

    st.title("⚡ Sentinel Omega — Command Dashboard")
    st.caption("Precursor Detection Platform · TITAN V32 Lineage · R(t) = a·t^b")

    col1, col2, col3, col4, col5 = st.columns(5)
    cfg = st.session_state.config
    active = sum(1 for v in cfg.layers.values() if v.enabled)
    col1.metric("Active Layers", f"{active}/3")
    col2.metric("Precursor Types", "15")
    col3.metric("Topology Nodes", "125")
    col4.metric("Muro Walls", "5")
    col5.metric("Architecture", "SNT + TITAN")

    st.divider()

    tabs = st.tabs([
        "🔴 Precursor Risk",
        "🧱 Muro 5 Eventos",
        "🔍 Scanner",
        "🗺️ Topología",
        "📊 Sísmico",
        "📡 Layer Signals",
        "📐 SNT Analysis",
        "📋 Ciclos",
    ])

    with tabs[0]:
        render_precursor_risk()

    with tabs[1]:
        render_muro()

    with tabs[2]:
        render_scanner()

    with tabs[3]:
        render_topology()

    with tabs[4]:
        render_sismico()

    with tabs[5]:
        signals = generate_demo_signals()
        render_layer_signals(signals)

    with tabs[6]:
        snt_results = generate_demo_satellization()
        render_satellization_analysis(snt_results)

    with tabs[7]:
        render_cycle_history()


if __name__ == "__main__":
    main()
