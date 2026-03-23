# ============================================================
#  components/charts.py
#  All Plotly chart builders — one function per chart
#  Each function takes a DataFrame and returns a go.Figure
# ============================================================

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from config import COLORS as C, PLOT_LAYOUT, FILLS


def _base(fig: go.Figure, height: int = 300, title: str = "") -> go.Figure:
    """Applies standard dark theme to any figure."""
    fig.update_layout(**PLOT_LAYOUT, height=height, title=title)
    return fig


# ── Hourly Heatmap ────────────────────────────────────────────
def chart_hourly_heatmap(hourly_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=hourly_df["hour"], y=hourly_df["total"],
        name="Total Txns", marker_color=C["blue"], opacity=0.25,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=hourly_df["hour"], y=hourly_df["flagged"],
        name="Flagged", mode="lines+markers",
        line=dict(color=C["red"], width=3),
        marker=dict(size=7, color=C["red"]),
        fill="tozeroy", fillcolor=FILLS["red"],
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=hourly_df["hour"], y=hourly_df["fraud_rate_pct"],
        name="Fraud Rate %", mode="lines",
        line=dict(color=C["orange"], width=2, dash="dot"),
    ), secondary_y=True)

    fig.update_layout(**PLOT_LAYOUT, height=300,
        title="24-Hour Fraud Heatmap — Flagged Transactions by Hour")
    fig.update_yaxes(title_text="Count",      color=C["text"],   secondary_y=False, gridcolor=C["border"])
    fig.update_yaxes(title_text="Fraud Rate %", color=C["orange"], secondary_y=True,  gridcolor=C["border"])
    return fig


# ── Daily Trend ───────────────────────────────────────────────
def chart_daily_trend(daily_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df["date"], y=daily_df["flagged"],
        name="Fraud per Day", fill="tozeroy", fillcolor=FILLS["red"],
        line=dict(color=C["red"], width=2.5),
    ))
    fig.add_trace(go.Scatter(
        x=daily_df["date"], y=daily_df["total"] / 100,
        name="Total Txns (÷100)", line=dict(color=C["blue"], width=1.5, dash="dot"),
    ))
    return _base(fig, 250, "Daily Fraud Trend")


# ── Amount Distribution ───────────────────────────────────────
def chart_amount_distribution(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for status, color in [("Approved", C["blue"]), ("Flagged", C["red"])]:
        subset = df[df["status"] == status]["amount"]
        fig.add_trace(go.Histogram(
            x=subset, name=status, marker_color=color,
            opacity=0.75, nbinsx=60,
        ))
    fig.update_layout(**PLOT_LAYOUT, height=280,
        title="Amount Distribution: Approved vs Flagged",
        barmode="overlay",
        xaxis_title="Amount (USD)", yaxis_title="Count")
    return fig


# ── Merchant Treemap ──────────────────────────────────────────
def chart_merchant_treemap(merchant_df: pd.DataFrame) -> go.Figure:
    fraud_only = merchant_df[merchant_df["flagged"] > 0]
    if fraud_only.empty:
        fraud_only = merchant_df  # fallback

    fig = px.treemap(
        fraud_only,
        path=["merchant_category"],
        values="flagged",
        color="fraud_rate_pct",
        color_continuous_scale=[C["green"], C["orange"], C["red"]],
        title="Merchant Fraud Treemap — size = cases, color = rate %",
    )
    fig.update_layout(**PLOT_LAYOUT, height=320,
        coloraxis_colorbar=dict(
            title="Fraud %",
            tickfont=dict(color=C["text"]),
            title_font=dict(color=C["text"]),
        ))
    fig.update_traces(textfont=dict(size=14))
    return fig


# ── Merchant Fraud Rate Bar ───────────────────────────────────
def chart_merchant_bar(merchant_df: pd.DataFrame) -> go.Figure:
    colors = [
        C["red"] if r >= 3 else C["orange"] if r >= 1 else C["green"]
        for r in merchant_df["fraud_rate_pct"]
    ]
    fig = go.Figure(go.Bar(
        y=merchant_df["merchant_category"],
        x=merchant_df["fraud_rate_pct"],
        orientation="h",
        marker_color=colors,
        text=[f"{r:.2f}%" for r in merchant_df["fraud_rate_pct"]],
        textposition="outside",
        textfont=dict(color=C["text"]),
    ))
    fig.update_layout(**PLOT_LAYOUT, height=280,
        title="Fraud Rate % by Merchant Category",
        xaxis_title="Fraud Rate (%)", yaxis_title="")
    return fig


# ── Fraud Donut ───────────────────────────────────────────────
def chart_fraud_donut(merchant_df: pd.DataFrame) -> go.Figure:
    fraud_only = merchant_df[merchant_df["flagged"] > 0]
    total_fraud = int(fraud_only["flagged"].sum())
    fig = go.Figure(go.Pie(
        labels=fraud_only["merchant_category"],
        values=fraud_only["flagged"],
        hole=0.58,
        marker=dict(
            colors=[C["red"], C["orange"]],
            line=dict(color=C["panel"], width=3),
        ),
    ))
    fig.update_layout(**PLOT_LAYOUT, height=300,
        title="Share of Fraud by Merchant",
        annotations=[dict(
            text=f"<b>{total_fraud}</b><br>Fraud Cases",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=C["text"]),
        )])
    return fig


# ── Geographic Bubble Map ─────────────────────────────────────
CITY_COORDS = {
    "New York": (40.71, -74.01),
    "London":   (51.51, -0.13),
    "Dubai":    (25.20, 55.27),
    "Mumbai":   (19.08, 72.88),
    "Toronto":  (43.65, -79.38),
    "Sydney":   (-33.87, 151.21),
}

def chart_geo_map(city_df: pd.DataFrame) -> go.Figure:
    city_df = city_df.copy()
    city_df["lat"] = city_df["city"].map(lambda c: CITY_COORDS.get(c, (0, 0))[0])
    city_df["lon"] = city_df["city"].map(lambda c: CITY_COORDS.get(c, (0, 0))[1])
    city_df = city_df[city_df["lat"] != 0]  # drop unmapped cities

    fig = px.scatter_geo(
        city_df,
        lat="lat", lon="lon",
        size="flagged",
        color="fraud_rate_pct",
        hover_name="city",
        hover_data={"flagged": True, "total": True,
                    "fraud_rate_pct": ":.3f", "lat": False, "lon": False},
        color_continuous_scale=[C["green"], C["orange"], C["red"]],
        size_max=55,
        projection="natural earth",
        title="Geographic Fraud Distribution",
    )
    fig.update_layout(
        paper_bgcolor=C["panel"], plot_bgcolor=C["bg"],
        font=dict(family="Syne", color=C["text"]),
        geo=dict(
            bgcolor=C["bg"],
            showland=True,    landcolor=C["border"],
            showocean=True,   oceancolor=C["bg"],
            showframe=False,  showcountries=True, countrycolor="#2a3550",
        ),
        height=400, margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(
            title="Fraud Rate %",
            tickfont=dict(color=C["text"]),
            title_font=dict(color=C["text"]),
        ),
    )
    return fig


# ── Impossible Travel Route Bar ───────────────────────────────
def chart_travel_routes(route_df: pd.DataFrame) -> go.Figure:
    if route_df.empty:
        fig = go.Figure()
        return _base(fig, 200, "No impossible travel detected")

    colors = [
        C["red"] if r == "CRITICAL" else C["orange"] if r == "HIGH" else C["blue"]
        for r in route_df["risk_level"]
    ]
    fig = go.Figure(go.Bar(
        x=route_df["cases"],
        y=route_df["route"],
        orientation="h",
        marker_color=colors,
        text=route_df["cases"],
        textposition="outside",
        textfont=dict(color=C["text"]),
    ))
    return _base(fig, 300, "Impossible Travel Cases by City Pair")


# ── Velocity Histogram ────────────────────────────────────────
def chart_velocity_histogram(vel_df: pd.DataFrame, threshold: int = 5) -> go.Figure:
    if vel_df.empty:
        fig = go.Figure()
        return _base(fig, 240, "No velocity data")

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=vel_df["txns_in_1hr"],
        marker_color=C["orange"], opacity=0.85, nbinsx=10,
        name="Users",
    ))
    fig.add_vline(
        x=threshold, line_color=C["red"], line_dash="dash",
        annotation_text=f"Alert Threshold: {threshold} txns/hr",
        annotation_font_color=C["red"],
    )
    fig.update_layout(**PLOT_LAYOUT, height=240,
        title="Distribution of Peak Hourly Transaction Counts",
        xaxis_title="Txns per Hour", yaxis_title="Number of Users")
    return fig


# ── Precision Gauge ───────────────────────────────────────────
def chart_precision_gauge(precision: float, recall: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=precision,
        title={"text": "Rule Precision Score", "font": {"color": C["text"], "family": "Syne"}},
        delta={"reference": 85, "increasing": {"color": C["green"]}},
        gauge={
            "axis":  {"range": [0, 100], "tickcolor": C["text"]},
            "bar":   {"color": C["green"]},
            "steps": [
                {"range": [0,  60], "color": "rgba(230,57,70,0.2)"},
                {"range": [60, 80], "color": "rgba(255,140,66,0.2)"},
                {"range": [80,100], "color": "rgba(6,214,160,0.2)"},
            ],
            "threshold": {"line": {"color": C["green"], "width": 3},
                          "thickness": 0.75, "value": 90},
            "bgcolor":     C["panel"],
            "bordercolor": C["border"],
        },
        number={"suffix": "%", "font": {"color": C["text"], "family": "Space Mono"}},
    ))
    fig.update_layout(
        paper_bgcolor=C["panel"],
        font=dict(color=C["text"]),
        height=280, margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


# ── Threshold Sweep Line Chart ────────────────────────────────
def chart_threshold_sweep(sweep_df: pd.DataFrame, current_threshold: float) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=sweep_df["threshold"], y=sweep_df["catch_rate_pct"],
        name="Fraud Catch Rate %", line=dict(color=C["green"], width=2.5),
        marker=dict(size=8),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=sweep_df["threshold"], y=sweep_df["false_positives"],
        name="False Positives", line=dict(color=C["red"], width=2.5, dash="dot"),
        marker=dict(size=8),
    ), secondary_y=True)
    fig.add_vline(
        x=current_threshold, line_color=C["orange"], line_dash="dash",
        annotation_text=f"Current: ${current_threshold}",
        annotation_font_color=C["orange"],
    )
    fig.update_layout(**PLOT_LAYOUT, height=300,
        title="Fraud Catch Rate vs False Positives by Amount Threshold")
    fig.update_yaxes(title_text="Catch Rate %",     color=C["green"],  secondary_y=False, gridcolor=C["border"])
    fig.update_yaxes(title_text="False Positives",  color=C["red"],    secondary_y=True,  gridcolor=C["border"])
    return fig