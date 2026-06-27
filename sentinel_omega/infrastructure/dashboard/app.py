"""
Sentinel Omega v2.0 — Command Dashboard
Real-time multi-layer monitoring based on Shadow Node Theory.
Launch: streamlit run sentinel_omega/infrastructure/dashboard/app.py
"""

import time
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

# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sentinel Omega",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

SIGNAL_COLORS = {
    "BULLISH": "#00c853",
    "BEARISH": "#ff1744",
    "NEUTRAL": "#ffc107",
    "ALERT": "#d500f9",
    "NO_SIGNAL": "#757575",
}

REGIME_COLORS = {
    DominanceRegime.CONVERGENCE: "#00c853",
    DominanceRegime.EQUILIBRIUM: "#ffc107",
    DominanceRegime.SATELLIZATION: "#ff9100",
    DominanceRegime.ROCHE_RADIUS: "#ff1744",
    DominanceRegime.LEAPFROG: "#2979ff",
}

# ── Session State Init ───────────────────────────────────────────────

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


# ── Sidebar ──────────────────────────────────────────────────────────

def render_sidebar():
    cfg = st.session_state.config
    st.sidebar.title("⚡ Sentinel Omega")
    st.sidebar.caption(f"v{cfg.version}")
    st.sidebar.caption(f"{cfg.author}")
    st.sidebar.divider()

    st.sidebar.subheader("Active Layers")
    active = {k: v for k, v in cfg.layers.items() if v.enabled}
    for name, layer_cfg in active.items():
        emoji = {"geodynamic": "🌍", "crypto": "₿", "bolsa": "📈"}.get(name, "⚡")
        st.sidebar.markdown(f"{emoji} **{name.upper()}** — {layer_cfg.refresh_interval_s}s refresh")

    st.sidebar.divider()
    st.sidebar.subheader("SNT Parameters")
    st.sidebar.markdown(f"**Roche threshold**: b ≥ {cfg.snt.roche_threshold}")
    st.sidebar.markdown(f"**Equilibrium band**: ±{cfg.snt.equilibrium_band}")
    st.sidebar.markdown(f"**Friction ρ**: {cfg.snt.friction_spearman_rho}")
    st.sidebar.markdown(f"**Min data points**: {cfg.snt.min_data_points}")

    st.sidebar.divider()
    st.sidebar.subheader("Location")
    st.sidebar.markdown(f"📍 {cfg.coordinates.get('location', 'Unknown')}")
    st.sidebar.markdown(f"Lat: {cfg.coordinates.get('lat')}, Lon: {cfg.coordinates.get('lon')}")

    return list(active.keys())


# ── Demo Data Generators ─────────────────────────────────────────────

def generate_demo_satellization():
    rng = np.random.default_rng(int(time.time()) % 1000)
    t = np.arange(1, 101, dtype=float)
    scenarios = {
        "BTC/ETH Dominance": (2.0, 0.35 + rng.normal(0, 0.05)),
        "BTC/SOL Dominance": (1.5, 0.65 + rng.normal(0, 0.08)),
        "SPY/QQQ Ratio": (1.1, -0.15 + rng.normal(0, 0.03)),
        "Tlaxcala/CDMX GDP": (0.03, -0.47 + rng.normal(0, 0.02)),
        "Kp Intensity": (3.0, 0.02 + rng.normal(0, 0.01)),
    }
    results = {}
    snt = st.session_state.snt
    for name, (a_true, b_true) in scenarios.items():
        noise = rng.normal(0, 0.02 * a_true, len(t))
        ratio = a_true * np.power(t, b_true) + np.abs(noise)
        ratio = np.maximum(ratio, 1e-6)
        try:
            result = snt.fit(t, ratio)
            results[name] = {"result": result, "t": t, "ratio": ratio}
        except ValueError:
            pass
    return results


def generate_demo_nbody():
    return {
        "Geodynamic Nodes": {
            "Pacific_Ring": 400.0, "Atlantic_Ridge": 120.0,
            "Himalayas": 80.0, "Andes": 60.0, "Alps": 30.0,
            "Tlaxcala_Zone": 15.0, "Iceland": 10.0,
        },
        "Crypto Market Cap ($B)": {
            "Bitcoin": 1200.0, "Ethereum": 350.0, "BNB": 80.0,
            "Solana": 65.0, "XRP": 40.0, "Cardano": 15.0,
            "Avalanche": 10.0, "Polkadot": 8.0,
        },
        "Sector ETFs ($B)": {
            "Technology": 500.0, "Healthcare": 200.0, "Financials": 180.0,
            "Consumer": 120.0, "Energy": 90.0, "Industrials": 75.0,
            "Materials": 40.0, "Utilities": 30.0,
        },
    }


def generate_demo_signals():
    rng = np.random.default_rng(int(time.time()) % 1000)
    layers = {
        "geodynamic": {
            "agents": {
                "Alfa-1 (Bz/OMNI)": {"signal": "NEUTRAL", "confidence": 0.3, "bz_mean": round(rng.normal(-2, 3), 1)},
                "Beta-1 (Kp/FFT)": {"signal": "NEUTRAL", "confidence": 0.3, "dominant_period_h": round(rng.uniform(6, 48), 1)},
                "Delta (Topology)": {"signal": "NEUTRAL", "confidence": 0.3, "power_law_b": round(rng.normal(-0.5, 0.2), 3)},
            },
            "padre": {"consensus": False, "signal": "NO_SIGNAL", "confidence": 0.0, "miss_penalty": 10, "false_alarm_penalty": 1},
        },
        "crypto": {
            "agents": {
                "Alfa-Crypto (SNT)": {"signal": rng.choice(["BULLISH", "BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.8), 2), "avg_b": round(rng.normal(0.1, 0.3), 3)},
                "Beta-Crypto (On-Chain)": {"signal": rng.choice(["BULLISH", "BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.8), 2), "whale_ratio": round(rng.uniform(0.05, 0.5), 2)},
                "Delta-Crypto (Sentiment)": {"signal": rng.choice(["BULLISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.7), 2), "fear_greed": int(rng.integers(15, 85))},
            },
            "padre": {"consensus": False, "signal": "NEUTRAL", "confidence": 0.2, "miss_penalty": 3, "false_alarm_penalty": 5},
        },
        "bolsa": {
            "agents": {
                "Alfa-Bolsa (Technical)": {"signal": rng.choice(["BULLISH", "BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.75), 2), "rsi": round(rng.uniform(30, 70), 1)},
                "Beta-Bolsa (Macro)": {"signal": rng.choice(["BEARISH", "NEUTRAL"]), "confidence": round(rng.uniform(0.3, 0.7), 2), "yield_spread": round(rng.normal(0.5, 1.0), 2)},
                "Delta-Bolsa (Regime)": {"signal": "NEUTRAL", "confidence": 0.3, "vix": round(rng.uniform(12, 35), 1)},
            },
            "padre": {"consensus": False, "signal": "NEUTRAL", "confidence": 0.2, "miss_penalty": 2, "false_alarm_penalty": 5},
        },
    }
    return layers


# ── Visualization Components ─────────────────────────────────────────

def render_system_header():
    col1, col2, col3, col4 = st.columns(4)
    cfg = st.session_state.config
    active = sum(1 for v in cfg.layers.values() if v.enabled)
    col1.metric("Active Layers", f"{active}/4")
    col2.metric("Architecture", "Shadow Node Theory")
    col3.metric("Model", "R(t) = a·t^b")
    col4.metric("Hardware", "RTX 3050 CUDA")


def render_layer_signals(signals: dict):
    st.subheader("Layer Consensus Status")

    cols = st.columns(len(signals))
    emojis = {"geodynamic": "🌍", "crypto": "₿", "bolsa": "📈"}

    for i, (layer_name, layer_data) in enumerate(signals.items()):
        with cols[i]:
            padre = layer_data["padre"]
            signal = padre["signal"]
            color = SIGNAL_COLORS.get(signal, "#757575")

            st.markdown(
                f"### {emojis.get(layer_name, '⚡')} {layer_name.upper()}"
            )

            st.markdown(
                f"<div style='padding:12px;border-radius:8px;border-left:4px solid {color};background:rgba(0,0,0,0.05)'>"
                f"<b>Padre:</b> <span style='color:{color}'>{signal}</span><br>"
                f"<b>Confidence:</b> {padre['confidence']:.0%}<br>"
                f"<b>Consensus:</b> {'Yes' if padre['consensus'] else 'No'}<br>"
                f"<b>Miss penalty:</b> {padre['miss_penalty']}× | <b>False alarm:</b> {padre['false_alarm_penalty']}×"
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


def render_satellization_analysis(results: dict):
    st.subheader("SNT Satellization Analysis — R(t) = a·t^b")

    cols = st.columns(2)

    names = list(results.keys())
    b_values = [results[n]["result"].b for n in names]
    r2_values = [results[n]["result"].r_squared for n in names]
    regimes = [results[n]["result"].regime for n in names]
    colors = [REGIME_COLORS.get(r, "#757575") for r in regimes]

    with cols[0]:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=names, y=b_values,
            marker_color=colors,
            text=[f"b={b:.3f}" for b in b_values],
            textposition="outside",
        ))
        fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Roche Radius")
        fig.add_hline(y=0.05, line_dash="dot", line_color="gray")
        fig.add_hline(y=-0.05, line_dash="dot", line_color="gray")
        fig.add_hrect(y0=-0.05, y1=0.05, fillcolor="yellow", opacity=0.1,
                      annotation_text="Equilibrium Band")
        fig.update_layout(
            title="Satellization Exponent (b) by Domain",
            yaxis_title="b value",
            height=400,
            template="plotly_dark",
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
            fit_line = a * np.power(data["t"], b)
            fig.add_trace(go.Scatter(
                x=data["t"], y=fit_line,
                mode="lines", name=f"{name} fit",
                line=dict(color=color, dash="dash"),
                showlegend=False,
            ))
        fig.update_layout(
            title="Power Law Fits",
            xaxis_title="t",
            yaxis_title="R(t)",
            height=400,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    regime_df = pd.DataFrame({
        "Domain": names,
        "b": [f"{b:.4f}" for b in b_values],
        "R²": [f"{r:.4f}" for r in r2_values],
        "Regime": [r.value for r in regimes],
        "Observations": [results[n]["result"].n_observations for n in names],
    })
    st.dataframe(regime_df, use_container_width=True, hide_index=True)


def render_nbody_analysis(nbody_data: dict):
    st.subheader("N-Body Matrix — Multi-Entity Power Law")

    nbody = st.session_state.nbody
    tabs = st.tabs(list(nbody_data.keys()))

    for tab, (system_name, entities) in zip(tabs, nbody_data.items()):
        with tab:
            hub_name = max(entities, key=entities.get)
            result = nbody.analyze(entities, hub_name)

            col1, col2 = st.columns(2)

            with col1:
                sorted_nodes = sorted(result.nodes, key=lambda n: -n.value)
                ranks = list(range(1, len(sorted_nodes) + 1))
                values = [n.value for n in sorted_nodes]
                node_names = [n.name for n in sorted_nodes]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=node_names, y=values,
                    marker_color=px.colors.sequential.Viridis_r[:len(node_names)],
                    text=[f"{v:.0f}" for v in values],
                    textposition="outside",
                ))

                fit_values = [result.power_law_a * r ** result.power_law_b for r in ranks]
                fig.add_trace(go.Scatter(
                    x=node_names, y=fit_values,
                    mode="lines+markers", name=f"Power law fit (b={result.power_law_b:.3f})",
                    line=dict(color="red", dash="dash"),
                ))

                fig.update_layout(
                    title=f"{system_name} — Rank Distribution",
                    yaxis_title="Value",
                    height=400,
                    template="plotly_dark",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                level_names = {0: "Macro Hub", 1: "Secondary Attractor", 2: "Bypass Logistic",
                               3: "Shadow Node", 4: "Exogenous"}
                level_colors = {0: "#d500f9", 1: "#2979ff", 2: "#ffc107", 3: "#ff9100", 4: "#757575"}

                node_df = pd.DataFrame([
                    {
                        "Entity": n.name,
                        "Value": f"{n.value:.1f}",
                        "Classification": level_names.get(n.level, "Unknown"),
                        "Extraction Vector": f"{n.extraction_vector:.3f}",
                    }
                    for n in sorted_nodes
                ])
                st.dataframe(node_df, use_container_width=True, hide_index=True)

                st.metric("Power Law b", f"{result.power_law_b:.4f}")
                st.metric("R²", f"{result.r_squared:.4f}")
                st.metric("Composite Gradient", f"{result.composite_gradient:.1f}")


def render_friction_map():
    st.subheader("Institutional Friction Map — ρ = -0.68")

    calc = st.session_state.friction_calc

    domains = [
        ("Epidemic", 0.0, 0.0, 0.0),
        ("Gravity", 0.02, 0.01, 0.01),
        ("Digital Platform", 0.15, 0.1, 0.2),
        ("Crypto", 0.2, 0.15, 0.25),
        ("Stock Market", 0.5, 0.55, 0.6),
        ("Subnational", 0.55, 0.6, 0.5),
        ("Sovereign", 0.75, 0.8, 0.7),
        ("Predator-Prey", 0.8, 0.75, 0.85),
        ("Geodynamic", 0.95, 0.95, 0.9),
    ]

    profiles = []
    for name, rd, sb, ti in domains:
        p = calc.calculate(rd, sb, ti, name.lower().replace(" ", "_").replace("-", "_"))
        expected_b = calc.expected_b(p)
        profiles.append({
            "domain": name,
            "score": p.score,
            "level": p.level.name,
            "expected_b": expected_b,
        })

    df = pd.DataFrame(profiles)

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["score"], y=df["expected_b"],
            mode="markers+text",
            text=df["domain"],
            textposition="top center",
            marker=dict(
                size=15,
                color=df["score"],
                colorscale="RdYlGn_r",
                showscale=True,
                colorbar=dict(title="Friction"),
            ),
        ))
        fig.update_layout(
            title="Friction vs Expected Satellization (b)",
            xaxis_title="Institutional Friction Score",
            yaxis_title="Expected b",
            height=450,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure(go.Bar(
            x=df["domain"], y=df["expected_b"],
            marker_color=[
                "#00c853" if b > 0.5 else "#ffc107" if b > 0.2 else "#ff1744"
                for b in df["expected_b"]
            ],
            text=[f"b={b:.2f}" for b in df["expected_b"]],
            textposition="outside",
        ))
        fig.update_layout(
            title="Expected b by Domain",
            yaxis_title="Expected b (Satellization Exponent)",
            height=450,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_asi_explorer():
    st.subheader("Atomic Sovereignty Index (ASI)")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("**Interactive ASI Calculator**")
        behaviors = st.text_input(
            "Behavioral sequence (comma-separated)",
            value="trade,hold,trade,sell,buy,hold,analyze",
        )
        seq = [b.strip() for b in behaviors.split(",") if b.strip()]
        autonomous = st.slider("Autonomous actions", 0, 100, 70)
        total = st.slider("Total actions", 1, 100, 100)
        friction = st.slider("Friction index", 0.01, 2.0, 0.5, step=0.01)

        asi = st.session_state.asi_calc
        result = asi.calculate(seq, autonomous, total, friction)

        classification = asi.sovereignty_classification(result.asi_score)
        class_colors = {"sovereign": "#00c853", "semi_autonomous": "#2979ff",
                        "dependent": "#ffc107", "captured": "#ff1744"}

        st.metric("ASI Score", f"{result.asi_score:.3f}")
        st.markdown(
            f"**Classification:** <span style='color:{class_colors.get(classification, '#fff')}'>"
            f"{classification.upper()}</span>",
            unsafe_allow_html=True,
        )
        st.metric("Shannon Entropy (δH)", f"{result.delta_h:.3f}")
        st.metric("Autonomy (α)", f"{result.alpha:.2%}")
        wall_status = "ABOVE" if result.above_threshold else "BELOW"
        st.metric(f"Event Wall ({asi.EVENT_WALL})", f"{result.event_count} events — {wall_status}")

    with col2:
        friction_range = np.linspace(0.01, 2.0, 50)
        autonomy_range = [0.2, 0.5, 0.7, 0.9, 1.0]

        fig = go.Figure()
        for alpha in autonomy_range:
            asi_scores = [result.delta_h * alpha / f for f in friction_range]
            fig.add_trace(go.Scatter(
                x=friction_range, y=asi_scores,
                mode="lines", name=f"α={alpha:.0%}",
            ))

        fig.add_hline(y=3.0, line_dash="dash", line_color="green", annotation_text="Sovereign")
        fig.add_hline(y=1.5, line_dash="dot", line_color="blue", annotation_text="Semi-autonomous")
        fig.add_hline(y=0.5, line_dash="dot", line_color="orange", annotation_text="Dependent")

        fig.update_layout(
            title=f"ASI = δH × α / F (δH={result.delta_h:.2f})",
            xaxis_title="Friction (F)",
            yaxis_title="ASI Score",
            height=450,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_cross_layer():
    st.subheader("Cross-Layer Correlation Matrix")

    rng = np.random.default_rng(42)
    metrics = ["Bz (nT)", "Kp Index", "BTC Dom", "ETH/BTC b", "VIX", "S&P RSI",
               "Yield Spread", "Fear&Greed", "Whale Ratio"]
    corr = rng.uniform(-1, 1, (len(metrics), len(metrics)))
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1.0)
    corr[0, 3] = corr[3, 0] = -0.42
    corr[0, 4] = corr[4, 0] = 0.38
    corr[1, 4] = corr[4, 1] = 0.55
    corr[2, 7] = corr[7, 2] = -0.61

    fig = go.Figure(go.Heatmap(
        z=corr, x=metrics, y=metrics,
        colorscale="RdBu_r", zmid=0,
        text=[[f"{v:.2f}" for v in row] for row in corr],
        texttemplate="%{text}",
        textfont={"size": 10},
    ))
    fig.update_layout(
        title="Cross-Layer Metric Correlations (SNT-derived)",
        height=500,
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Main App ─────────────────────────────────────────────────────────

def main():
    active_layers = render_sidebar()

    st.title("⚡ Sentinel Omega — Command Dashboard")
    st.caption("Multi-domain prediction platform · Shadow Node Theory · R(t) = a·t^b")

    render_system_header()
    st.divider()

    tab_signals, tab_snt, tab_nbody, tab_friction, tab_asi, tab_cross = st.tabs([
        "📡 Layer Signals",
        "📐 SNT Analysis",
        "🔗 N-Body Matrix",
        "🏛️ Friction Map",
        "🧬 ASI Explorer",
        "🔀 Cross-Layer",
    ])

    with tab_signals:
        signals = generate_demo_signals()
        render_layer_signals(signals)

    with tab_snt:
        snt_results = generate_demo_satellization()
        render_satellization_analysis(snt_results)

    with tab_nbody:
        nbody_data = generate_demo_nbody()
        render_nbody_analysis(nbody_data)

    with tab_friction:
        render_friction_map()

    with tab_asi:
        render_asi_explorer()

    with tab_cross:
        render_cross_layer()


if __name__ == "__main__":
    main()
