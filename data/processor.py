# ============================================================
#  data/processor.py
#  All fraud detection analytics — velocity, geo, merchant stats
#  Pure functions: take a DataFrame, return a DataFrame/dict
#  No Streamlit or Plotly imports here — just logic
# ============================================================

import pandas as pd
import numpy as np
from datetime import timedelta


# ── 1. Summary KPIs ──────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    """Returns top-level KPI numbers for the dashboard header."""
    total      = len(df)
    flagged    = int(df["is_flagged"].sum())
    approved   = total - flagged
    fraud_rate = round(flagged / total * 100, 3) if total else 0

    flagged_df  = df[df["status"] == "Flagged"]
    approved_df = df[df["status"] == "Approved"]

    avg_fraud_amt   = round(flagged_df["amount"].mean(), 2)  if len(flagged_df)  else 0
    avg_normal_amt  = round(approved_df["amount"].mean(), 2) if len(approved_df) else 0
    amount_multiple = round(avg_fraud_amt / avg_normal_amt, 1) if avg_normal_amt else 0

    return {
        "total":           total,
        "flagged":         flagged,
        "approved":        approved,
        "fraud_rate_pct":  fraud_rate,
        "avg_fraud_amt":   avg_fraud_amt,
        "avg_normal_amt":  avg_normal_amt,
        "amount_multiple": amount_multiple,
    }


# ── 2. Hourly Breakdown ───────────────────────────────────────
def compute_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates transactions by hour with fraud counts and rates."""
    hourly = (
        df.groupby("hour")
        .agg(total=("transaction_id", "count"), flagged=("is_flagged", "sum"))
        .reset_index()
    )
    hourly["fraud_rate_pct"] = (hourly["flagged"] / hourly["total"] * 100).round(3)
    # Fill missing hours with 0
    all_hours = pd.DataFrame({"hour": range(24)})
    hourly = all_hours.merge(hourly, on="hour", how="left").fillna(0)
    return hourly


# ── 3. Daily Trend ────────────────────────────────────────────
def compute_daily(df: pd.DataFrame) -> pd.DataFrame:
    daily = (
        df.groupby("date")
        .agg(total=("transaction_id", "count"), flagged=("is_flagged", "sum"))
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    return daily.sort_values("date")


# ── 4. Merchant Risk Stats ────────────────────────────────────
def compute_merchant_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = (
        df.groupby("merchant_category")
        .agg(
            total      =("transaction_id", "count"),
            flagged    =("is_flagged",      "sum"),
            avg_amount =("amount",          "mean"),
        )
        .reset_index()
    )
    stats["fraud_rate_pct"] = (stats["flagged"] / stats["total"] * 100).round(2)
    stats["avg_amount"]     = stats["avg_amount"].round(2)
    stats["risk_level"] = stats["fraud_rate_pct"].apply(
        lambda x: "CRITICAL" if x >= 3 else ("HIGH" if x >= 1 else "CLEAN")
    )
    return stats.sort_values("fraud_rate_pct", ascending=False)


# ── 5. City Risk Stats ────────────────────────────────────────
def compute_city_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = (
        df.groupby("city")
        .agg(total=("transaction_id","count"), flagged=("is_flagged","sum"))
        .reset_index()
    )
    stats["fraud_rate_pct"] = (stats["flagged"] / stats["total"] * 100).round(3)
    return stats.sort_values("flagged", ascending=False)


# ── 6. Transaction Velocity Detection ────────────────────────
def compute_velocity(df: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
    """
    Finds users with >= threshold transactions in any 1-hour window.
    Returns a ranked DataFrame of suspicious users.

    This is O(n log n) — sorts per user then uses a sliding window.
    """
    results = []
    for uid, grp in df.sort_values("timestamp").groupby("user_id"):
        txns = grp.sort_values("timestamp").reset_index(drop=True)
        ts_list  = txns["timestamp"].tolist()
        amt_list = txns["amount"].tolist()
        sta_list = txns["status"].tolist()

        for i, ts_start in enumerate(ts_list):
            ts_end = ts_start + timedelta(hours=1)
            window = [
                (t, a, s)
                for t, a, s in zip(ts_list, amt_list, sta_list)
                if ts_start <= t <= ts_end
            ]
            if len(window) >= threshold:
                results.append({
                    "user_id":       uid,
                    "txns_in_1hr":   len(window),
                    "window_start":  ts_start,
                    "total_amount":  round(sum(w[1] for w in window), 2),
                    "has_fraud":     any(w[2] == "Flagged" for w in window),
                    "risk_score":    min(100, len(window) * 10 + (40 if any(w[2] == "Flagged" for w in window) else 0)),
                })
                break  # one entry per user

    if not results:
        return pd.DataFrame(columns=["user_id","txns_in_1hr","window_start","total_amount","has_fraud","risk_score"])

    return (
        pd.DataFrame(results)
        .sort_values("risk_score", ascending=False)
        .reset_index(drop=True)
    )


# ── 7. Impossible Travel Detection ───────────────────────────
def compute_impossible_travel(df: pd.DataFrame, window_hrs: float = 1.0) -> pd.DataFrame:
    """
    Detects same user_id appearing in 2 different cities within window_hrs.
    These are physically impossible trips — strong fraud signal.
    """
    rows = []
    for uid, grp in df.sort_values("timestamp").groupby("user_id"):
        txns = grp.sort_values("timestamp").reset_index(drop=True)
        for i in range(len(txns) - 1):
            t1, t2 = txns.iloc[i], txns.iloc[i + 1]
            diff_hrs = (t2["timestamp"] - t1["timestamp"]).total_seconds() / 3600
            if diff_hrs <= window_hrs and t1["city"] != t2["city"]:
                rows.append({
                    "user_id":       uid,
                    "city_1":        t1["city"],
                    "city_2":        t2["city"],
                    "time_gap_hrs":  round(diff_hrs, 2),
                    "amount_1":      t1["amount"],
                    "amount_2":      t2["amount"],
                    "timestamp_1":   t1["timestamp"],
                    "timestamp_2":   t2["timestamp"],
                    "either_flagged":t1["status"] == "Flagged" or t2["status"] == "Flagged",
                    "route":         f"{t1['city']} → {t2['city']}",
                })

    if not rows:
        return pd.DataFrame()

    df_out = pd.DataFrame(rows)
    # Summarize by route pair
    route_summary = (
        df_out.groupby("route")
        .agg(
            cases          =("user_id",       "count"),
            flagged_cases  =("either_flagged", "sum"),
            avg_gap_hrs    =("time_gap_hrs",  "mean"),
        )
        .reset_index()
        .sort_values("cases", ascending=False)
    )
    route_summary["risk_level"] = route_summary["cases"].apply(
        lambda x: "CRITICAL" if x >= 300 else ("HIGH" if x >= 200 else "MEDIUM")
    )
    return route_summary


# ── 8. False Positive Analysis ────────────────────────────────
def compute_false_positive_stats(df: pd.DataFrame, amount_threshold: float = 500) -> dict:
    """
    Analyses rule accuracy — how many legit transactions got flagged.
    Simulates precision/recall for different amount thresholds.
    """
    flagged_df  = df[df["status"] == "Flagged"]
    approved_df = df[df["status"] == "Approved"]

    # True positives: flagged transactions above threshold in risky merchants
    high_risk_merchants = ["Crypto Exchange", "Electronics"]
    true_positives = len(flagged_df[
        (flagged_df["amount"] >= amount_threshold) &
        (flagged_df["merchant_category"].isin(high_risk_merchants))
    ])

    # False positives estimate: approved txns that would have been caught by rule
    false_positives = len(approved_df[
        (approved_df["amount"] >= amount_threshold) &
        (approved_df["merchant_category"].isin(high_risk_merchants))
    ])

    total_fraud  = len(flagged_df)
    precision    = round(true_positives / (true_positives + false_positives) * 100, 1) if (true_positives + false_positives) > 0 else 0
    recall       = round(true_positives / total_fraud * 100, 1) if total_fraud > 0 else 0
    f1           = round(2 * (precision/100 * recall/100) / ((precision/100) + (recall/100)) * 100, 1) if (precision + recall) > 0 else 0

    # Threshold sweep for the simulator chart
    thresholds = [100, 250, 500, 750, 1000, 1500, 2000]
    sweep = []
    for t in thresholds:
        tp = len(flagged_df[flagged_df["amount"] >= t])
        fp = len(approved_df[
            (approved_df["amount"] >= t) &
            (approved_df["merchant_category"].isin(high_risk_merchants))
        ])
        catch_rate = round(tp / total_fraud * 100, 1) if total_fraud else 0
        prec       = round(tp / (tp + fp) * 100, 1)   if (tp + fp) > 0 else 0
        sweep.append({"threshold": t, "catch_rate_pct": catch_rate,
                      "false_positives": fp, "precision_pct": prec})

    return {
        "true_positives":  true_positives,
        "false_positives": false_positives,
        "total_fraud":     total_fraud,
        "precision_pct":   precision,
        "recall_pct":      recall,
        "f1_score":        f1,
        "threshold_sweep": pd.DataFrame(sweep),
    }


# ── 9. Live Ticker (latest N transactions) ───────────────────
def get_live_ticker(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Returns the N most recent transactions for the live feed panel."""
    cols = ["transaction_id", "user_id", "timestamp", "amount",
            "merchant_category", "city", "status"]
    available = [c for c in cols if c in df.columns]
    return (
        df[available]
        .sort_values("timestamp", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )