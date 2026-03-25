# ============================================================
#  components/kpis.py
#  KPI metric cards and alert box helpers
# ============================================================

import streamlit as st
from config import COLORS as C


def render_kpi_row(kpis: dict):
    """Renders the 6 top-level KPI metric cards."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("💳 Total Transactions", f"{kpis['total']:,}")
    c2.metric("🚨 Flagged Alerts",     f"{kpis['flagged']:,}",
              delta="requires review", delta_color="inverse")
    c3.metric("📊 Fraud Rate",         f"{kpis['fraud_rate_pct']}%",
              delta="Industry avg: 1.2%", delta_color="normal")
    c4.metric("💰 Avg Fraud Amount",   f"${kpis['avg_fraud_amt']:,.0f}",
              delta=f"{kpis['amount_multiple']}× above normal", delta_color="inverse")
    c5.metric("⚡ Velocity Suspects",
              f"{kpis.get('velocity_suspects', 0):,}",
              delta=f"≥{kpis.get('velocity_threshold', 5)} txns/hr", delta_color="inverse")
    c6.metric("✈️ Impossible Travel",
              f"{kpis.get('impossible_travel_cases', 0):,}",
              delta="multi-city < 1hr", delta_color="inverse")


def alert_box(text: str, level: str = "danger"):
    """
    Renders a styled alert box.
    level: "danger" | "warning" | "success" | "info"
    """
    styles = {
        "danger":  (C["red"],    "rgba(230,57,70,0.08)"),
        "warning": (C["orange"], "rgba(255,140,66,0.08)"),
        "success": (C["green"],  "rgba(6,214,160,0.08)"),
        "info":    (C["blue"],   "rgba(76,201,240,0.08)"),
    }
    border_color, bg = styles.get(level, styles["info"])
    st.markdown(f"""
    <div style="
        background:{bg};
        border:1px solid {border_color}55;
        border-left:4px solid {border_color};
        border-radius:8px;
        padding:12px 16px;
        margin:8px 0;
        font-size:14px;
        color:{C['text']};
        line-height:1.6;
    ">{text}</div>
    """, unsafe_allow_html=True)


def section_header(title: str, subtitle: str = ""):
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <div style="font-size:17px;font-weight:800;color:{C['text']};">{title}</div>
        {"" if not subtitle else f'<div style="font-size:12px;color:{C["dimmed"]};margin-top:3px;">{subtitle}</div>'}
    </div>
    """, unsafe_allow_html=True)