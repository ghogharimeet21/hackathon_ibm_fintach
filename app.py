# ============================================================
#  app.py — LogicLoop Main Entry Point
#  National Hackathon 2026 · Problem D5
#
#  Run:   streamlit run app.py
#
#  Architecture:
#    app.py           ← you are here (UI only, no business logic)
#    config.py        ← all settings, column aliases, thresholds
#    data/schema.py   ← column normalization for any CSV format
#    data/loader.py   ← data source abstraction (batch + stream)
#    data/processor.py← fraud detection analytics
#    components/      ← reusable UI widgets
# ============================================================

import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import DEFAULTS, COLORS as C, PLOT_LAYOUT
from data.loader import build_source
from data.processor import (
    compute_kpis, compute_hourly, compute_daily,
    compute_merchant_stats, compute_city_stats,
    compute_velocity, compute_impossible_travel,
    compute_false_positive_stats, get_live_ticker,
    compute_user_profiles,
)
from components.kpis    import render_kpi_row, alert_box, section_header
from components.charts  import (
    chart_hourly_heatmap, chart_daily_trend, chart_amount_distribution,
    chart_merchant_treemap, chart_merchant_bar, chart_fraud_donut,
    chart_geo_map, chart_travel_routes,
    chart_velocity_histogram, chart_precision_gauge, chart_threshold_sweep,
)
from components.alerts  import render_live_ticker, render_schema_report


# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Logic Loop | FinTech Anomaly Visualizer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

    html, body, [class*="css"]  { font-family: 'Syne', sans-serif; }
    .stApp                      { background-color: #080b12; }
    .stTabs [data-baseweb="tab"]{ font-family: 'Syne', sans-serif; font-weight: 600; }
    [data-testid="metric-container"] {
        background: #0d1220;
        border: 1px solid #1a2440;
        border-radius: 10px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Space Mono', monospace !important;
        font-size: 1.8rem !important;
    }
    [data-testid="stSidebar"]   { background: #0d1220; border-right: 1px solid #1a2440; }
    h1, h2, h3                  { font-family: 'Syne', sans-serif !important; }

    /* live pulse dot */
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
    .live-dot {
        display:inline-block; width:9px; height:9px;
        border-radius:50%; background:#06d6a0;
        animation: pulse 1.4s infinite; margin-right:6px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SESSION STATE  (persists across Streamlit reruns)
# ══════════════════════════════════════════════════════════════
if "source"       not in st.session_state: st.session_state.source       = None
if "mode"         not in st.session_state: st.session_state.mode         = "batch"
if "auto_refresh" not in st.session_state: st.session_state.auto_refresh = False
if "tick_count"   not in st.session_state: st.session_state.tick_count   = 0


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🛡️ LogicLoop")
    st.caption("FinTech Anomaly Visualizer · D5")
    st.divider()

    # ── Data Source ──────────────────────────────────────────
    st.markdown("### 📡 Data Source")
    mode = st.radio(
        "Mode",
        ["📂 Batch (CSV Upload)", "🔴 Live Stream (Simulated)"],
        index=0,
        help="Live Stream simulates a real-time Kafka/WebSocket feed. "
             "Swap data/loader.py → KafkaStreamSource to connect a real stream.",
    )
    st.session_state.mode = "stream" if "Live" in mode else "batch"

    uploaded = st.file_uploader(
        "Upload CSV (any column format)",
        type=["csv"],
        help="Column names are auto-detected. Add variations in config.py → COLUMN_ALIASES.",
    )

    if st.button("▶ Load / Reload Data", use_container_width=True):
        with st.spinner("Loading data..."):
            st.session_state.source = build_source(
                uploaded_file=uploaded,
                mode=st.session_state.mode,
            )
        st.success("Data loaded!")

    # ── Real-time Controls ────────────────────────────────────
    st.divider()
    st.markdown("### ⏱️ Real-Time Controls")

    auto_on = st.toggle(
        "🔄 Auto-Refresh",
        value=st.session_state.auto_refresh,
        help="Refreshes the dashboard every N seconds (simulates live feed)",
    )
    st.session_state.auto_refresh = auto_on

    refresh_secs = st.slider(
        "Refresh interval (seconds)", 2, 30,
        DEFAULTS["auto_refresh_secs"],
        disabled=not auto_on,
    )

    if st.button("🔁 Manual Refresh Now", use_container_width=True):
        if st.session_state.source and st.session_state.mode == "stream":
            st.session_state.source.push_new_transactions(n=5)
        st.rerun()

    if st.session_state.auto_refresh:
        st.markdown(
            f'<div style="font-size:12px;color:{C["green"]};">'
            f'<span class="live-dot"></span>Auto-refreshing every {refresh_secs}s</div>',
            unsafe_allow_html=True,
        )

    # ── Detection Thresholds ──────────────────────────────────
    st.divider()
    st.markdown("### ⚙️ Detection Thresholds")
    velocity_threshold = st.slider("Velocity alert (txns/hr)", 3, 15, DEFAULTS["velocity_threshold"])
    amount_threshold   = st.slider("High-value alert ($)",     100, 3000, DEFAULTS["amount_threshold"])
    travel_window      = st.slider("Impossible travel (hrs)",  1, 6,  int(DEFAULTS["travel_window_hrs"]))

    # ── Filters ───────────────────────────────────────────────
    st.divider()
    st.markdown("### 🔎 Filters")
    city_filter     = st.multiselect("Cities",    ["New York","London","Dubai","Mumbai","Toronto","Sydney"],
                                      default=["New York","London","Dubai","Mumbai","Toronto","Sydney"])
    merchant_filter = st.multiselect("Merchants", ["Groceries","Dining","Retail","Electronics","Travel","Crypto Exchange"],
                                      default=["Groceries","Dining","Retail","Electronics","Travel","Crypto Exchange"])
    status_filter   = st.radio("Status", ["All","Flagged Only","Approved Only"])

    st.divider()
    st.caption("National Hackathon 2026 · Track D5\nBuilt with Streamlit + Plotly + Pandas")


# ══════════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════════

# Auto-load on first run (uses local CSV if present)
if st.session_state.source is None:
    try:
        st.session_state.source = build_source(mode="batch")
    except FileNotFoundError:
        st.warning("👈 Upload your CSV using the sidebar to get started.")
        st.stop()

source = st.session_state.source

# Push new transactions if in live mode
if st.session_state.mode == "stream":
    source.push_new_transactions(n=3)

# Get data
try:
    df_full, schema_report = source.get_data()
except Exception as e:
    st.error(f"❌ Schema Error: {e}")
    st.info("Check **config.py → COLUMN_ALIASES** and add your column name variations.")
    st.stop()

# Apply sidebar filters
df = df_full.copy()
if city_filter     and "city"              in df.columns: df = df[df["city"].isin(city_filter)]
if merchant_filter and "merchant_category" in df.columns: df = df[df["merchant_category"].isin(merchant_filter)]
if status_filter == "Flagged Only":  df = df[df["status"] == "Flagged"]
elif status_filter == "Approved Only": df = df[df["status"] == "Approved"]


# ══════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════
is_live = st.session_state.mode == "stream"
source_badge = (
    f'<span class="live-dot"></span><span style="color:{C["green"]};font-weight:700;">LIVE STREAM</span>'
    if is_live else
    f'<span style="color:{C["dimmed"]};">📂 BATCH MODE</span>'
)

st.markdown(f"""
<div style="
    display:flex; justify-content:space-between; align-items:center;
    background:{C['panel']}; border:1px solid {C['border']};
    border-radius:12px; padding:20px 28px; margin-bottom:20px;
">
    <div>
        <h1 style="margin:0;font-size:24px;color:#fff;">
            🛡️ Fraud<span style="color:{C['red']};">Guard</span>
            <span style="font-size:13px;font-weight:400;color:{C['dimmed']};margin-left:10px;">
                FinTech Transaction Anomaly &amp; Fraud Visualizer
            </span>
        </h1>
        <p style="margin:4px 0 0;font-size:11px;color:{C['dimmed']};font-family:Space Mono,monospace;">
            {source.source_label} · {len(df):,} transactions loaded · Hackathon 2026 D5
        </p>
    </div>
    <div style="text-align:right;font-size:13px;">{source_badge}</div>
</div>
""", unsafe_allow_html=True)

render_schema_report(schema_report)


# ══════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "🏪 Merchant Risk",
    "✈️ Geo & Velocity",
    "👤 User Profiles",
    "🔍 False Positive Tracker",
    "📡 Live Feed",
])


# ╔═════════════════════════════════════════════╗
# ║  TAB 1 — OVERVIEW                          ║
# ╚═════════════════════════════════════════════╝
with tab1:
    kpis = compute_kpis(df)

    # Compute velocity + travel counts for KPI row
    with st.spinner("Computing anomaly counts..."):
        _vel_df   = compute_velocity(df, threshold=velocity_threshold)
        _route_df = compute_impossible_travel(df, window_hrs=travel_window)

    kpis["velocity_suspects"]       = len(_vel_df)
    kpis["velocity_threshold"]      = velocity_threshold
    kpis["impossible_travel_cases"] = int(_route_df["cases"].sum()) if not _route_df.empty else 0

    render_kpi_row(kpis)

    st.divider()

    section_header(
        "🕐 24-Hour Fraud Heatmap",
        "Hourly breakdown of flagged vs approved transactions. "
        "Peaks reveal coordinated attack windows.",
    )
    hourly_df = compute_hourly(df)
    st.plotly_chart(chart_hourly_heatmap(hourly_df), use_container_width=True)

    # Peak hour callouts
    top3 = hourly_df.nlargest(3, "flagged")[["hour","flagged","fraud_rate_pct"]]
    labels = ["🔴 Peak Attack Hour", "🟠 2nd Risk Hour", "🟡 3rd Risk Hour"]
    cols = st.columns(3)
    for i, (_, row) in enumerate(top3.iterrows()):
        cols[i].markdown(f"""
        <div style="background:rgba(230,57,70,0.08);border:1px solid rgba(230,57,70,0.3);
                    border-left:4px solid {C['red']};border-radius:8px;padding:10px 14px;">
            <strong>{labels[i]}</strong><br>
            ⏰ <code>{int(row['hour']):02d}:00</code> — 
            <strong>{int(row['flagged'])}</strong> cases &nbsp;|&nbsp;
            Rate: <strong>{row['fraud_rate_pct']}%</strong>
        </div>""", unsafe_allow_html=True)

    st.divider()

    c1, c2 = st.columns([1.3, 1])
    with c1:
        section_header("📅 Daily Fraud Trend", "Is fraud increasing over time?")
        st.plotly_chart(chart_daily_trend(compute_daily(df)), use_container_width=True)
    with c2:
        section_header("💵 Amount Distribution", "Fraud transactions are 19× larger on average.")
        st.plotly_chart(chart_amount_distribution(df), use_container_width=True)

    if kpis["amount_multiple"] > 5:
        alert_box(
            f"💡 <strong>Key Signal:</strong> Flagged transactions average "
            f"<strong>${kpis['avg_fraud_amt']:,.0f}</strong> — that's "
            f"<strong>{kpis['amount_multiple']}× higher</strong> than normal "
            f"(${kpis['avg_normal_amt']:.0f}). Amount threshold is your strongest single rule.",
            level="danger",
        )


# ╔═════════════════════════════════════════════╗
# ║  TAB 2 — MERCHANT RISK                     ║
# ╚═════════════════════════════════════════════╝
with tab2:
    merchant_df = compute_merchant_stats(df)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        section_header("🗂️ Merchant Fraud Treemap",
                        "Size = total fraud cases. Color = fraud rate %.")
        st.plotly_chart(chart_merchant_treemap(merchant_df), use_container_width=True)
    with c2:
        section_header("🍩 Fraud Share by Merchant")
        st.plotly_chart(chart_fraud_donut(merchant_df), use_container_width=True)

    st.divider()
    section_header("📊 Fraud Rate by Merchant Category",
                   "Red = CRITICAL (≥3%), Orange = HIGH (≥1%), Green = CLEAN")
    st.plotly_chart(chart_merchant_bar(merchant_df), use_container_width=True)

    st.divider()
    section_header("📋 Merchant Risk Scorecard")

    display = merchant_df[["merchant_category","total","flagged","fraud_rate_pct","avg_amount","risk_level"]].copy()
    display.columns = ["Merchant","Total Txns","Flagged","Fraud Rate %","Avg Amount ($)","Risk Level"]

    def color_risk(val):
        if val == "CRITICAL": return "color:#e63946; font-weight:700"
        if val == "HIGH":     return "color:#ff8c42; font-weight:700"
        if val == "CLEAN":    return "color:#06d6a0; font-weight:700"
        return ""

    st.dataframe(
        display.style
            .applymap(color_risk, subset=["Risk Level"])
            .format({"Fraud Rate %": "{:.2f}%", "Avg Amount ($)": "${:,.2f}"}),
        use_container_width=True, hide_index=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        alert_box(
            "🔴 <strong>Crypto Exchange (4.4% fraud rate)</strong><br>"
            "→ Mandatory 2FA on ALL transactions<br>"
            "→ Auto-hold amounts above $500 for manual review<br>"
            "→ Block first-time international purchases",
            level="danger",
        )
    with c2:
        alert_box(
            "🟠 <strong>Electronics (1.0% fraud rate)</strong><br>"
            "→ Max 2 transactions per hour per user<br>"
            "→ Flag amounts > $800 for review<br>"
            "→ Cross-check with geo-location data",
            level="warning",
        )
    alert_box(
        "🟢 <strong>Groceries / Dining / Retail / Travel — 0% fraud detected</strong><br>"
        "No additional friction needed. Standard approval rules apply.",
        level="success",
    )


# ╔═════════════════════════════════════════════╗
# ║  TAB 3 — GEO & VELOCITY                    ║
# ╚═════════════════════════════════════════════╝
with tab3:
    geo_tab, vel_tab = st.tabs(["✈️ Geographic Anomaly", "⚡ Velocity Spikes"])

    with geo_tab:
        section_header(
            "🗺️ Impossible Travel Detection",
            f"Same user in 2 cities within {travel_window} hour(s) — physically impossible.",
        )

        city_df = compute_city_stats(df)
        st.plotly_chart(chart_geo_map(city_df), use_container_width=True)

        st.divider()
        section_header("🔴 Top Impossible Travel Route Pairs")

        with st.spinner("Scanning for impossible travel..."):
            route_df = compute_impossible_travel(df, window_hrs=travel_window)

        if not route_df.empty:
            st.plotly_chart(chart_travel_routes(route_df), use_container_width=True)
            total_cases = int(route_df["cases"].sum())
            st.dataframe(route_df, use_container_width=True, hide_index=True)
            alert_box(
                f"⚠ <strong>{total_cases:,} impossible travel cases detected</strong>. "
                "These indicate card cloning or stolen credential sharing across accounts. "
                "The New York ↔ London route (min 7hr flight) is the most common pair — "
                "strongly suggesting automated credential stuffing attacks.",
                level="danger",
            )
        else:
            alert_box("✅ No impossible travel cases detected with current filters.", level="success")

    with vel_tab:
        section_header(
            "⚡ Transaction Velocity Spike Detection",
            f"Users making ≥ {velocity_threshold} transactions in a 1-hour window.",
        )

        with st.spinner("Computing velocity patterns..."):
            vel_df = compute_velocity(df, threshold=velocity_threshold)

        v1, v2, v3 = st.columns(3)
        v1.metric("⚡ Velocity Suspects",   len(vel_df))
        v2.metric("🚨 With Fraud Flag",     int(vel_df["has_fraud"].sum()) if not vel_df.empty else 0, delta_color="inverse")
        v3.metric("💰 Max Window Amount",   f"${vel_df['total_amount'].max():,.2f}" if not vel_df.empty else "$0")

        if not vel_df.empty:
            st.plotly_chart(chart_velocity_histogram(vel_df, velocity_threshold), use_container_width=True)

            st.markdown("#### 🚨 Suspect Users — Prioritized Action List")
            display_vel = vel_df.head(20).copy()
            display_vel["has_fraud"]    = display_vel["has_fraud"].map({True: "🚨 YES", False: "⚠ NO"})
            display_vel["total_amount"] = display_vel["total_amount"].apply(lambda x: f"${x:,.2f}")
            display_vel["risk_score"]   = display_vel["risk_score"].apply(lambda x: f"{x}/100")
            display_vel.columns = ["User ID","Txns/hr","Window Start","Total Amount","Has Fraud","Risk Score"]

            st.dataframe(
                display_vel.style.applymap(
                    lambda v: "color:#e63946; font-weight:bold" if "YES" in str(v) else "",
                    subset=["Has Fraud"],
                ),
                use_container_width=True, hide_index=True,
            )
        else:
            alert_box("✅ No velocity spikes detected with current settings.", level="success")

        alert_box(
            "🤖 <strong>Detection Logic:</strong> A velocity spike is flagged when the same "
            f"User_ID makes <strong>≥{velocity_threshold} transactions in any 60-minute window</strong>. "
            "This pattern matches automated bots testing stolen card credentials with micro-charges "
            "before one large fraudulent purchase.",
            level="info",
        )


# ╔═════════════════════════════════════════════╗
# ║  TAB 4 — FALSE POSITIVE TRACKER            ║
# ╚═════════════════════════════════════════════╝
with tab5:
    section_header(
        "🔍 False Positive Tracker",
        "How many legitimate transactions did our rules incorrectly block?",
    )

    fp_stats = compute_false_positive_stats(df, amount_threshold=amount_threshold)

    fp1, fp2, fp3, fp4 = st.columns(4)
    fp1.metric("✅ True Fraud Flags",    f"{fp_stats['true_positives']:,}")
    fp2.metric("❌ False Positives",      f"{fp_stats['false_positives']:,}", delta_color="normal")
    fp3.metric("🎯 Rule Precision",       f"{fp_stats['precision_pct']}%")
    fp4.metric("📈 F1 Score",             f"{fp_stats['f1_score']}%")

    st.divider()
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.plotly_chart(
            chart_precision_gauge(fp_stats["precision_pct"], fp_stats["recall_pct"]),
            use_container_width=True,
        )
    with c2:
        section_header("📊 Rule Performance Breakdown")
        perf = {
            "Metric": [
                "Total Transactions",
                "True Fraud Flags",
                "False Positives (Wrongly Blocked)",
                "Rule Precision",
                "Estimated Recall",
                "F1 Score",
            ],
            "Value": [
                f"{len(df):,}",
                f"{fp_stats['true_positives']:,}",
                f"{fp_stats['false_positives']:,}",
                f"{fp_stats['precision_pct']}%",
                f"{fp_stats['recall_pct']}%",
                f"{fp_stats['f1_score']}%",
            ],
        }
        st.dataframe(pd.DataFrame(perf), use_container_width=True, hide_index=True)

    st.divider()
    section_header(
        "⚙️ Rule Threshold Simulator",
        "Drag the 'High-value alert ($)' slider in the sidebar to simulate different thresholds.",
    )
    st.plotly_chart(
        chart_threshold_sweep(fp_stats["threshold_sweep"], amount_threshold),
        use_container_width=True,
    )
    st.dataframe(fp_stats["threshold_sweep"], use_container_width=True, hide_index=True)

    alert_box(
        f"💡 <strong>Optimal Rule:</strong> Set amount threshold at <strong>$500</strong> for "
        "Crypto Exchange and Electronics categories. This catches ~92% of fraud while keeping "
        "false positives near zero — no unnecessary friction for genuine customers.",
        level="success",
    )


# ╔═════════════════════════════════════════════╗
# ║  TAB 4 — USER RISK PROFILES                ║
# ╚═════════════════════════════════════════════╝
with tab4:
    section_header(
        "👤 User Risk Profiles — Suspicious Account Watchlist",
        "Every user scored across 5 signals: fraud flags, velocity bursts, "
        "impossible travel, high amounts, risky merchants.",
    )

    with st.spinner("Building user risk profiles... (this takes ~10s for 200k rows)"):
        profiles_df = compute_user_profiles(
            df,
            velocity_threshold=velocity_threshold,
            travel_window_hrs=travel_window,
        )

    if profiles_df.empty:
        alert_box("✅ No suspicious users detected with current filter settings.", level="success")
    else:
        # ── Summary KPIs ─────────────────────────────────
        critical = len(profiles_df[profiles_df["risk_label"].str.contains("CRITICAL")])
        high     = len(profiles_df[profiles_df["risk_label"].str.contains("HIGH")])
        medium   = len(profiles_df[profiles_df["risk_label"].str.contains("MEDIUM")])

        u1, u2, u3, u4 = st.columns(4)
        u1.metric("👥 Flagged Users",      len(profiles_df),  delta="suspicious activity")
        u2.metric("🔴 CRITICAL",           critical,          delta_color="inverse")
        u3.metric("🟠 HIGH Risk",          high,              delta_color="inverse")
        u4.metric("🟡 MEDIUM Risk",        medium)

        st.divider()

        # ── Top 5 User Cards ─────────────────────────────
        section_header("🚨 Top 5 Highest-Risk Accounts", "Immediate action required")

        for _, user in profiles_df.head(5).iterrows():
            score    = user["risk_score"]
            bar_color = (
                "#e63946" if score >= 70 else
                "#ff8c42" if score >= 40 else
                "#ffd166"
            )
            filled = int(score)
            empty  = 100 - filled

            st.markdown(f"""
            <div style="background:#0d1220; border:1px solid {'#e6394655' if score>=70 else '#ff8c4255' if score>=40 else '#1a2440'};
                        border-left:5px solid {bar_color}; border-radius:10px;
                        padding:16px 20px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div>
                        <span style="font-family:Space Mono,monospace; font-size:16px;
                                     font-weight:700; color:#c8d6e5;">{user['user_id']}</span>
                        <span style="margin-left:12px; font-size:12px; color:#64748b;">
                            {user['total_txns']} transactions · ${user['total_spent']:,.0f} total · 
                            {user['cities_used']} cities
                        </span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:13px; font-weight:700; color:{bar_color};">
                            {user['risk_label']}
                        </span>
                        <span style="font-family:Space Mono,monospace; font-size:22px;
                                     font-weight:700; color:{bar_color}; margin-left:12px;">
                            {score}/100
                        </span>
                    </div>
                </div>
                <!-- Risk bar -->
                <div style="background:#1a2440; border-radius:4px; height:6px; margin-bottom:10px;">
                    <div style="width:{filled}%; background:{bar_color};
                                border-radius:4px; height:100%; transition:width 0.5s;"></div>
                </div>
                <!-- Signal tags -->
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    {''.join([
                        f'<span style="background:{bar_color}22; border:1px solid {bar_color}55; '
                        f'color:{bar_color}; border-radius:20px; padding:3px 10px; '
                        f'font-size:11px; font-weight:600;">{r}</span>'
                        for r in user['reasons'].split(' | ') if r != '—'
                    ])}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ── Full Watchlist Table ──────────────────────────
        section_header(
            "📋 Full Suspicious User Watchlist",
            f"Showing top 100 of {len(profiles_df)} flagged users",
        )

        display_profiles = profiles_df.head(100)[[
            "user_id", "risk_score", "risk_label", "flagged_txns",
            "max_velocity", "impossible_travel", "cities_used",
            "max_amount", "avg_amount", "has_crypto", "reasons"
        ]].copy()

        display_profiles.columns = [
            "User ID", "Risk Score", "Risk Level", "Fraud Flags",
            "Max Velocity", "Impossible Travel", "Cities",
            "Max Amount ($)", "Avg Amount ($)", "Crypto?", "Why Flagged"
        ]
        display_profiles["Max Amount ($)"] = display_profiles["Max Amount ($)"].apply(lambda x: f"${x:,.0f}")
        display_profiles["Avg Amount ($)"] = display_profiles["Avg Amount ($)"].apply(lambda x: f"${x:,.0f}")
        display_profiles["Crypto?"]        = display_profiles["Crypto?"].map({True: "⚠ Yes", False: "No"})

        def color_risk_cell(val):
            if "CRITICAL" in str(val): return "color:#e63946; font-weight:bold"
            if "HIGH"     in str(val): return "color:#ff8c42; font-weight:bold"
            if "MEDIUM"   in str(val): return "color:#ffd166; font-weight:bold"
            return ""

        st.dataframe(
            display_profiles.style
                .applymap(color_risk_cell, subset=["Risk Level"])
                .applymap(lambda v: "color:#e63946" if "Yes" in str(v) else "", subset=["Crypto?"])
                .format({"Risk Score": "{}/100"}),
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        # ── Drill-down: pick a user ───────────────────────
        st.divider()
        section_header("🔎 User Transaction Drill-Down", "Pick any user to see their full transaction history")

        selected_user = st.selectbox(
            "Select User ID",
            options=profiles_df.head(50)["user_id"].tolist(),
            format_func=lambda u: f"{u}  (Risk: {profiles_df[profiles_df['user_id']==u]['risk_score'].values[0]}/100)",
        )

        if selected_user:
            user_txns = df[df["user_id"] == selected_user].sort_values("timestamp")
            st.markdown(f"**{len(user_txns)} transactions for `{selected_user}`**")

            from components.alerts import render_live_ticker
            render_live_ticker(user_txns.rename(columns={
                "user_id":"user_id","timestamp":"timestamp","amount":"amount",
                "merchant_category":"merchant_category","city":"city","status":"status",
                "transaction_id":"transaction_id",
            }))

            # Mini amount timeline for this user
            fig_user = go.Figure()
            flagged_u   = user_txns[user_txns["status"] == "Flagged"]
            approved_u  = user_txns[user_txns["status"] == "Approved"]

            fig_user.add_trace(go.Scatter(
                x=approved_u["timestamp"], y=approved_u["amount"],
                mode="markers", name="Approved",
                marker=dict(color=C["blue"], size=9),
            ))
            fig_user.add_trace(go.Scatter(
                x=flagged_u["timestamp"], y=flagged_u["amount"],
                mode="markers", name="Flagged",
                marker=dict(color=C["red"], size=14, symbol="x"),
            ))
            fig_user.update_layout(
                **PLOT_LAYOUT, height=240,
                title=f"Transaction Timeline — {selected_user}",
                xaxis_title="Time", yaxis_title="Amount ($)",
            )
            st.plotly_chart(fig_user, use_container_width=True)


# ╔═════════════════════════════════════════════╗
# ║  TAB 5 — FALSE POSITIVE TRACKER            ║
# ╚═════════════════════════════════════════════╝
with tab5:
    section_header(
        "🔍 False Positive Tracker",
        "How many legitimate transactions did our rules incorrectly block?",
    )

    fp_stats = compute_false_positive_stats(df, amount_threshold=amount_threshold)

    fp1, fp2, fp3, fp4 = st.columns(4)
    fp1.metric("✅ True Fraud Flags",    f"{fp_stats['true_positives']:,}")
    fp2.metric("❌ False Positives",      f"{fp_stats['false_positives']:,}", delta_color="normal")
    fp3.metric("🎯 Rule Precision",       f"{fp_stats['precision_pct']}%")
    fp4.metric("📈 F1 Score",             f"{fp_stats['f1_score']}%")

    st.divider()
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.plotly_chart(
            chart_precision_gauge(fp_stats["precision_pct"], fp_stats["recall_pct"]),
            use_container_width=True,
        )
    with c2:
        section_header("📊 Rule Performance Breakdown")
        perf = {
            "Metric": [
                "Total Transactions",
                "True Fraud Flags",
                "False Positives (Wrongly Blocked)",
                "Rule Precision",
                "Estimated Recall",
                "F1 Score",
            ],
            "Value": [
                f"{len(df):,}",
                f"{fp_stats['true_positives']:,}",
                f"{fp_stats['false_positives']:,}",
                f"{fp_stats['precision_pct']}%",
                f"{fp_stats['recall_pct']}%",
                f"{fp_stats['f1_score']}%",
            ],
        }
        st.dataframe(pd.DataFrame(perf), use_container_width=True, hide_index=True)

    st.divider()
    section_header(
        "⚙️ Rule Threshold Simulator",
        "Drag the 'High-value alert ($)' slider in the sidebar to simulate different thresholds.",
    )
    st.plotly_chart(
        chart_threshold_sweep(fp_stats["threshold_sweep"], amount_threshold),
        use_container_width=True,
    )
    st.dataframe(fp_stats["threshold_sweep"], use_container_width=True, hide_index=True)

    alert_box(
        f"💡 <strong>Optimal Rule:</strong> Set amount threshold at <strong>$500</strong> for "
        "Crypto Exchange and Electronics categories. This catches ~92% of fraud while keeping "
        "false positives near zero — no unnecessary friction for genuine customers.",
        level="success",
    )


# ╔═════════════════════════════════════════════╗
# ║  TAB 6 — LIVE FEED                         ║
# ╚═════════════════════════════════════════════╝
with tab6:
    section_header(
        "📡 Live Transaction Feed",
        "Most recent transactions — fraud rows highlighted in red. "
        + ("Auto-refreshing." if st.session_state.auto_refresh else "Enable Auto-Refresh in sidebar."),
    )

    ticker = get_live_ticker(df, n=25)
    render_live_ticker(ticker)

    st.divider()
    st.markdown("#### 💡 How to connect a real data stream")
    st.code("""
# In data/loader.py — replace SimulatedStreamSource with KafkaStreamSource:

from confluent_kafka import Consumer
import json

class KafkaStreamSource(DataSource):
    def __init__(self, bootstrap_servers, topic):
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": "LogicLoop",
        })
        self._consumer.subscribe([topic])
        self._buffer = []

    def push_new_transactions(self, n=10):
        for _ in range(n):
            msg = self._consumer.poll(0.5)
            if msg and not msg.error():
                self._buffer.append(json.loads(msg.value()))

# Then in app.py change one line:
source = build_source(mode="kafka",
                      bootstrap_servers="localhost:9092",
                      topic="transactions")
    """, language="python")


# ══════════════════════════════════════════════════════════════
#  AUTO-REFRESH LOOP (at the bottom — triggers st.rerun)
# ══════════════════════════════════════════════════════════════
if st.session_state.auto_refresh:
    if st.session_state.mode == "stream" and st.session_state.source:
        st.session_state.source.push_new_transactions(n=3)
    time.sleep(refresh_secs)
    st.session_state.tick_count += 1
    st.rerun()


# ── Footer ────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="display:flex;justify-content:space-between;
            font-size:11px;color:{C['dimmed']};font-family:Space Mono,monospace;">
    <span>National Hackathon 2026 · Track D5 · LogicLoop v2.0</span>
    <span>Streamlit + Plotly + Pandas · Multi-file architecture</span>
    <span>Tick #{st.session_state.tick_count}</span>
</div>
""", unsafe_allow_html=True)