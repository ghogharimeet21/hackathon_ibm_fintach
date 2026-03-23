# ============================================================
#  app.py — LogicLoop · FinTech Anomaly Visualizer
#  National Hackathon 2026 · Problem D5
#  Run: streamlit run app.py
# ============================================================

import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import COLORS as C, PLOT_LAYOUT
from data.loader import build_source
from data.processor import (
    compute_kpis, compute_hourly, compute_daily,
    compute_merchant_stats, compute_city_stats,
    compute_velocity, compute_impossible_travel,
    compute_false_positive_stats, get_live_ticker,
    compute_user_profiles,
)
from components.kpis   import render_kpi_row, alert_box, section_header
from components.charts import (
    chart_hourly_heatmap, chart_daily_trend, chart_amount_distribution,
    chart_merchant_treemap, chart_merchant_bar, chart_fraud_donut,
    chart_geo_map, chart_travel_routes,
    chart_velocity_histogram, chart_precision_gauge, chart_threshold_sweep,
)
from components.alerts import render_live_ticker

# ── Fixed detection settings (no sliders needed) ─────────────
VELOCITY_THRESHOLD = 5    # flag users with 5+ txns in 1 hour
AMOUNT_THRESHOLD   = 500  # flag transactions above $500
TRAVEL_WINDOW_HRS  = 1    # flag same user in 2 cities within 1 hour

# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="LogicLoop | Fraud Visualizer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

    html, body, [class*="css"]       { font-family: 'Syne', sans-serif; }
    .stApp                           { background-color: #080b12; }
    .stTabs [data-baseweb="tab"]     { font-family: 'Syne', sans-serif; font-weight: 600; }
    [data-testid="metric-container"] { background:#0d1220; border:1px solid #1a2440; border-radius:10px; padding:16px; }
    [data-testid="stMetricValue"]    { font-family:'Space Mono',monospace !important; font-size:1.8rem !important; }
    [data-testid="stSidebar"]        { background:#0d1220; border-right:1px solid #1a2440; }
    h1, h2, h3                       { font-family:'Syne',sans-serif !important; }

    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
    .live-dot {
        display:inline-block; width:9px; height:9px; border-radius:50%;
        background:#06d6a0; animation:pulse 1.4s infinite; margin-right:6px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════
if "source"       not in st.session_state: st.session_state.source       = None
if "mode"         not in st.session_state: st.session_state.mode         = "batch"
if "auto_refresh" not in st.session_state: st.session_state.auto_refresh = False
if "tick_count"   not in st.session_state: st.session_state.tick_count   = 0


# ══════════════════════════════════════════════════════════════
#  SIDEBAR — kept intentionally simple
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🛡️ LogicLoop")
    st.caption("FinTech Anomaly Visualizer · D5")
    st.divider()

    st.markdown("### 📂 Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if st.button("▶ Load Data", use_container_width=True):
        with st.spinner("Loading..."):
            st.session_state.source = build_source(
                uploaded_file=uploaded,
                mode=st.session_state.mode,
            )
        st.success("Loaded!")

    st.divider()

    st.markdown("### 📡 Mode")
    live_on = st.toggle(
        "🔴 Live Stream Mode",
        value=(st.session_state.mode == "stream"),
        help="Simulates real-time transactions. In production, connect Kafka in data/loader.py",
    )
    st.session_state.mode = "stream" if live_on else "batch"
    if live_on:
        st.caption("Simulating live transactions arriving every few seconds.")

    st.divider()

    st.markdown("### ⏱️ Auto-Refresh")
    auto_on = st.toggle("🔄 Auto-Refresh", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_on
    if auto_on:
        st.markdown(
            f'<div style="font-size:12px;color:{C["green"]};">'
            f'<span class="live-dot"></span>Refreshing every 5s</div>',
            unsafe_allow_html=True,
        )
    if st.button("🔁 Refresh Now", use_container_width=True):
        if st.session_state.source and st.session_state.mode == "stream":
            st.session_state.source.push_new_transactions(n=5)
        st.rerun()

    st.divider()
    st.caption("National Hackathon 2026 · Track D5\nStreamlit + Plotly + Pandas")


# ══════════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════════
if st.session_state.source is None:
    try:
        st.session_state.source = build_source(mode="batch")
    except FileNotFoundError:
        st.warning("👈 Upload your CSV using the sidebar to get started.")
        st.stop()

source = st.session_state.source

if st.session_state.mode == "stream":
    source.push_new_transactions(n=3)

try:
    df, schema_report = source.get_data()
except Exception as e:
    st.error(f"Could not read data: {e}")
    st.stop()


# ══════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════
is_live    = st.session_state.mode == "stream"
mode_badge = (
    f'<span class="live-dot"></span><span style="color:{C["green"]};font-weight:700;">LIVE STREAM</span>'
    if is_live else f'<span style="color:{C["dimmed"]};">📂 BATCH MODE</span>'
)

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            background:{C['panel']}; border:1px solid {C['border']};
            border-radius:12px; padding:20px 28px; margin-bottom:20px;">
    <div>
        <h1 style="margin:0; font-size:24px; color:#fff;">
            🛡️ Logic<span style="color:{C['red']};">Loop</span>
            <span style="font-size:13px; font-weight:400; color:{C['dimmed']}; margin-left:10px;">
                FinTech Transaction Anomaly &amp; Fraud Visualizer
            </span>
        </h1>
        <p style="margin:4px 0 0; font-size:11px; color:{C['dimmed']}; font-family:Space Mono,monospace;">
            {len(df):,} transactions loaded · National Hackathon 2026 · D5
        </p>
    </div>
    <div style="font-size:13px;">{mode_badge}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PRE-COMPUTE once, shared across all tabs
# ══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def get_all_stats(_df):
    vel_df   = compute_velocity(_df, threshold=VELOCITY_THRESHOLD)
    route_df = compute_impossible_travel(_df, window_hrs=TRAVEL_WINDOW_HRS)
    return vel_df, route_df

with st.spinner("Running anomaly detection..."):
    vel_df, route_df = get_all_stats(df)


# ── KPI row always visible ────────────────────────────────────
kpis = compute_kpis(df)
kpis["velocity_suspects"]       = len(vel_df)
kpis["velocity_threshold"]      = VELOCITY_THRESHOLD
kpis["impossible_travel_cases"] = int(route_df["cases"].sum()) if not route_df.empty else 0
render_kpi_row(kpis)
st.divider()


# ══════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "🏪 Merchant Risk",
    "✈️ Geo Anomaly",
    "⚡ Velocity Spikes",
    "👤 User Profiles",
    "📡 Live Feed",
])


# ── TAB 1: OVERVIEW ──────────────────────────────────────────
with tab1:
    section_header(
        "🕐 When does fraud happen? — 24-Hour Heatmap",
        "Red line = fraud cases per hour. Peaks are coordinated attack windows.",
    )
    hourly_df = compute_hourly(df)
    st.plotly_chart(chart_hourly_heatmap(hourly_df), use_container_width=True)

    top3  = hourly_df.nlargest(3, "flagged")[["hour", "flagged", "fraud_rate_pct"]]
    icons = ["🔴 Peak", "🟠 2nd", "🟡 3rd"]
    cols  = st.columns(3)
    for i, (_, row) in enumerate(top3.iterrows()):
        cols[i].markdown(f"""
        <div style="background:rgba(230,57,70,0.07); border-left:4px solid {C['red']};
                    border-radius:8px; padding:12px 16px;">
            <div style="font-size:12px; color:{C['dimmed']};">{icons[i]} attack hour</div>
            <div style="font-size:28px; font-weight:800; font-family:Space Mono,monospace;
                        color:{C['red']};">{int(row['hour']):02d}:00</div>
            <div style="font-size:13px; color:{C['text']};">
                <strong>{int(row['flagged'])}</strong> fraud cases
            </div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        section_header("📅 Daily Fraud Trend", "Is fraud getting worse over time?")
        st.plotly_chart(chart_daily_trend(compute_daily(df)), use_container_width=True)
    with c2:
        section_header("💵 How much do fraudsters spend?", "Fraud transactions are far larger than normal ones.")
        st.plotly_chart(chart_amount_distribution(df), use_container_width=True)

    alert_box(
        f"💡 Legitimate transactions average <strong>${kpis['avg_normal_amt']:.0f}</strong>. "
        f"Fraudulent ones average <strong>${kpis['avg_fraud_amt']:,.0f}</strong> — "
        f"that's <strong>{kpis['amount_multiple']}× higher</strong>. "
        "Any transaction above $500 at Crypto or Electronics should be auto-flagged.",
        level="danger",
    )


# ── TAB 2: MERCHANT RISK ─────────────────────────────────────
with tab2:
    merchant_df = compute_merchant_stats(df)
    section_header(
        "🏪 Which merchant types are being targeted?",
        "100% of fraud in this dataset is concentrated in just 2 categories.",
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_merchant_treemap(merchant_df), use_container_width=True)
    with c2:
        st.plotly_chart(chart_fraud_donut(merchant_df), use_container_width=True)

    st.plotly_chart(chart_merchant_bar(merchant_df), use_container_width=True)

    display = merchant_df[["merchant_category", "total", "flagged", "fraud_rate_pct", "risk_level"]].copy()
    display.columns = ["Merchant", "Total Txns", "Fraud Cases", "Fraud Rate %", "Risk Level"]
    def _cr(val):
        if val == "CRITICAL": return "color:#e63946; font-weight:700"
        if val == "HIGH":     return "color:#ff8c42; font-weight:700"
        if val == "CLEAN":    return "color:#06d6a0; font-weight:700"
        return ""
    st.dataframe(
        display.style.applymap(_cr, subset=["Risk Level"]).format({"Fraud Rate %": "{:.2f}%"}),
        use_container_width=True, hide_index=True,
    )
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        alert_box("🔴 <strong>Crypto Exchange — 4.4% fraud rate</strong><br>→ Require 2FA · Auto-hold above $500", level="danger")
    with c2:
        alert_box("🟠 <strong>Electronics — 1.0% fraud rate</strong><br>→ Max 2 txns/hr per user · Flag above $800", level="warning")
    alert_box("🟢 <strong>Groceries / Dining / Retail / Travel — 0% fraud</strong> · No action needed.", level="success")


# ── TAB 3: GEO ANOMALY ───────────────────────────────────────
with tab3:
    section_header(
        "✈️ Impossible Travel — Same card, two cities, within 1 hour",
        "If a card is used in Mumbai at 10 PM and New York at 10:45 PM — "
        "that's physically impossible. The card is cloned.",
    )
    city_df = compute_city_stats(df)
    st.plotly_chart(chart_geo_map(city_df), use_container_width=True)

    st.divider()
    total_travel = int(route_df["cases"].sum()) if not route_df.empty else 0
    section_header("🗺️ Most common impossible routes", f"{total_travel:,} impossible travel cases detected.")

    if not route_df.empty:
        st.plotly_chart(chart_travel_routes(route_df), use_container_width=True)
        st.dataframe(route_df, use_container_width=True, hide_index=True)
        alert_box(
            "⚠ These users' cards were used in cities no flight can connect in under 1 hour. "
            "This is the clearest sign of <strong>card cloning</strong> — a physical copy "
            "of the card is being used simultaneously in another country.",
            level="danger",
        )
    else:
        alert_box("✅ No impossible travel detected.", level="success")


# ── TAB 4: VELOCITY SPIKES ───────────────────────────────────
with tab4:
    section_header(
        "⚡ Velocity Spikes — Too many transactions in too little time",
        f"Normal users make 1-2 transactions per hour. "
        f"Anyone making {VELOCITY_THRESHOLD}+ in one hour is likely a fraud bot.",
    )
    v1, v2, v3 = st.columns(3)
    v1.metric("⚡ Suspicious Users",  len(vel_df))
    v2.metric("🚨 With Fraud Flags",  int(vel_df["has_fraud"].sum()) if not vel_df.empty else 0, delta_color="inverse")
    v3.metric("💰 Highest Burst",     f"${vel_df['total_amount'].max():,.0f}" if not vel_df.empty else "$0", delta="spent in 1 hour")

    if not vel_df.empty:
        st.plotly_chart(chart_velocity_histogram(vel_df, VELOCITY_THRESHOLD), use_container_width=True)
        st.divider()
        section_header("🚨 Flagged Users")
        dv = vel_df.head(20).copy()
        dv["has_fraud"]    = dv["has_fraud"].map({True: "🚨 YES", False: "⚠ No"})
        dv["total_amount"] = dv["total_amount"].apply(lambda x: f"${x:,.2f}")
        dv["risk_score"]   = dv["risk_score"].apply(lambda x: f"{x}/100")
        dv.columns = ["User ID", "Txns in 1hr", "Window Start", "Total Spent", "Has Fraud", "Risk Score"]
        st.dataframe(
            dv.style.applymap(lambda v: "color:#e63946; font-weight:bold" if "YES" in str(v) else "", subset=["Has Fraud"]),
            use_container_width=True, hide_index=True,
        )
        alert_box(
            "🤖 Fraudsters test stolen cards by making many small transactions quickly. "
            f"Any user with <strong>{VELOCITY_THRESHOLD}+ transactions in 60 minutes</strong> "
            "should be auto-blocked until verified.",
            level="info",
        )
    else:
        alert_box(f"✅ No users with {VELOCITY_THRESHOLD}+ transactions in 1 hour.", level="success")


# ── TAB 5: USER PROFILES ─────────────────────────────────────
with tab5:
    section_header(
        "👤 User Risk Profiles — Who should be investigated?",
        "Each user is scored 0-100 across all 5 fraud signals combined.",
    )
    with st.spinner("Building user risk profiles..."):
        profiles_df = compute_user_profiles(df, velocity_threshold=VELOCITY_THRESHOLD, travel_window_hrs=TRAVEL_WINDOW_HRS)

    if profiles_df.empty:
        alert_box("✅ No suspicious users found.", level="success")
    else:
        critical = len(profiles_df[profiles_df["risk_label"].str.contains("CRITICAL")])
        high     = len(profiles_df[profiles_df["risk_label"].str.contains("HIGH")])
        medium   = len(profiles_df[profiles_df["risk_label"].str.contains("MEDIUM")])
        u1,u2,u3,u4 = st.columns(4)
        u1.metric("👥 Total Suspicious", len(profiles_df))
        u2.metric("🔴 CRITICAL", critical, delta_color="inverse")
        u3.metric("🟠 HIGH",     high,     delta_color="inverse")
        u4.metric("🟡 MEDIUM",   medium)

        st.divider()
        section_header("🚨 Top 5 — Freeze These Accounts Now")
        for _, user in profiles_df.head(5).iterrows():
            score = user["risk_score"]
            color = "#e63946" if score >= 70 else "#ff8c42" if score >= 40 else "#ffd166"
            tags  = "".join([
                f'<span style="background:{color}22; border:1px solid {color}55; color:{color}; '
                f'border-radius:20px; padding:3px 10px; font-size:11px; font-weight:600; margin-right:6px;">{r}</span>'
                for r in user["reasons"].split(" | ") if r != "—"
            ])
            st.markdown(f"""
            <div style="background:#0d1220; border:1px solid {color}44; border-left:5px solid {color};
                        border-radius:10px; padding:16px 20px; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-family:Space Mono,monospace; font-size:16px; font-weight:700; color:#c8d6e5;">{user['user_id']}</span>
                    <span style="font-family:Space Mono,monospace; font-size:22px; font-weight:800; color:{color};">{score}/100</span>
                </div>
                <div style="font-size:12px; color:{C['dimmed']}; margin-bottom:10px;">
                    {user['total_txns']} transactions · ${user['total_spent']:,.0f} total · {user['cities_used']} cities
                </div>
                <div style="background:#1a2440; border-radius:4px; height:5px; margin-bottom:10px;">
                    <div style="width:{score}%; background:{color}; border-radius:4px; height:100%;"></div>
                </div>
                <div>{tags}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()
        section_header("📋 Full Watchlist", f"{len(profiles_df)} suspicious users")
        disp = profiles_df.head(100)[["user_id","risk_score","risk_label","flagged_txns","max_velocity","impossible_travel","cities_used","max_amount","reasons"]].copy()
        disp.columns = ["User ID","Score","Risk Level","Fraud Flags","Peak Velocity","Geo Anomalies","Cities","Max Txn ($)","Why Flagged"]
        disp["Max Txn ($)"] = disp["Max Txn ($)"].apply(lambda x: f"${x:,.0f}")
        def _cl(val):
            if "CRITICAL" in str(val): return "color:#e63946; font-weight:bold"
            if "HIGH"     in str(val): return "color:#ff8c42; font-weight:bold"
            if "MEDIUM"   in str(val): return "color:#ffd166"
            return ""
        st.dataframe(disp.style.applymap(_cl, subset=["Risk Level"]), use_container_width=True, hide_index=True, height=400)

        st.divider()
        section_header("🔎 Drill Down — Investigate a specific user")
        selected = st.selectbox(
            "Select user",
            options=profiles_df.head(50)["user_id"].tolist(),
            format_func=lambda u: f"{u}  ·  Risk Score: {profiles_df[profiles_df['user_id']==u]['risk_score'].values[0]}/100",
        )
        if selected:
            user_txns  = df[df["user_id"] == selected].sort_values("timestamp")
            flagged_u  = user_txns[user_txns["status"] == "Flagged"]
            approved_u = user_txns[user_txns["status"] == "Approved"]
            d1,d2,d3 = st.columns(3)
            d1.metric("Total Transactions", len(user_txns))
            d2.metric("Flagged", len(flagged_u), delta_color="inverse")
            d3.metric("Total Spent", f"${user_txns['amount'].sum():,.0f}")

            fig_user = go.Figure()
            fig_user.add_trace(go.Scatter(x=approved_u["timestamp"], y=approved_u["amount"], mode="markers", name="Approved", marker=dict(color=C["blue"], size=9)))
            fig_user.add_trace(go.Scatter(x=flagged_u["timestamp"],  y=flagged_u["amount"],  mode="markers", name="Flagged 🚨", marker=dict(color=C["red"], size=14, symbol="x")))
            fig_user.update_layout(**PLOT_LAYOUT, height=260, title=f"Transaction Timeline — {selected}", xaxis_title="Date", yaxis_title="Amount ($)")
            st.plotly_chart(fig_user, use_container_width=True)
            render_live_ticker(user_txns)


# ── TAB 6: LIVE FEED ─────────────────────────────────────────
with tab6:
    section_header(
        "📡 Live Transaction Feed",
        "Most recent 25 transactions. Fraud rows highlighted in red."
        + (" Auto-refreshing." if st.session_state.auto_refresh else " Enable Auto-Refresh in the sidebar."),
    )
    render_live_ticker(get_live_ticker(df, n=25))

    st.divider()
    section_header("🎯 Rule Accuracy — Are we blocking real customers?")
    fp = compute_false_positive_stats(df, amount_threshold=AMOUNT_THRESHOLD)
    f1,f2,f3,f4 = st.columns(4)
    f1.metric("✅ Fraud Correctly Caught",    f"{fp['true_positives']:,}")
    f2.metric("❌ Legit Txns Wrongly Blocked", f"{fp['false_positives']:,}", delta_color="normal")
    f3.metric("🎯 Precision",                 f"{fp['precision_pct']}%")
    f4.metric("📈 F1 Score",                  f"{fp['f1_score']}%")
    st.plotly_chart(chart_precision_gauge(fp["precision_pct"], fp["recall_pct"]), use_container_width=True)
    alert_box(
        "💡 Rule: Flag any transaction above <strong>$500</strong> at a "
        "<strong>Crypto Exchange</strong> or <strong>Electronics</strong> store. "
        "Catches 92% of fraud with near-zero false positives.",
        level="success",
    )


# ══════════════════════════════════════════════════════════════
#  AUTO-REFRESH
# ══════════════════════════════════════════════════════════════
if st.session_state.auto_refresh:
    if st.session_state.mode == "stream" and st.session_state.source:
        st.session_state.source.push_new_transactions(n=3)
    time.sleep(5)
    st.session_state.tick_count += 1
    st.rerun()


# ── Footer ────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="display:flex; justify-content:space-between;
            font-size:11px; color:{C['dimmed']}; font-family:Space Mono,monospace;">
    <span>National Hackathon 2026 · Track D5 · LogicLoop</span>
    <span>Streamlit + Plotly + Pandas</span>
    <span>{"🔴 Live" if is_live else "📂 Batch"} · Tick #{st.session_state.tick_count}</span>
</div>
""", unsafe_allow_html=True)