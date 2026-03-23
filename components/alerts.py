# ============================================================
#  components/alerts.py
#  Live transaction ticker and real-time fraud alert feed
# ============================================================

import streamlit as st
import pandas as pd
from config import COLORS as C


def render_live_ticker(ticker_df: pd.DataFrame):
    """
    Shows a scrolling table of the most recent transactions.
    Fraud rows are highlighted in red.
    """
    if ticker_df.empty:
        st.info("No transactions to display.")
        return

    # Build HTML table row by row for custom coloring
    rows_html = ""
    for _, row in ticker_df.iterrows():
        is_fraud  = row.get("status", "") == "Flagged"
        row_bg    = "rgba(230,57,70,0.10)" if is_fraud else "transparent"
        status_html = (
            f'<span style="color:{C["red"]};font-weight:700;">🚨 FLAGGED</span>'
            if is_fraud
            else f'<span style="color:{C["green"]};">✓ Approved</span>'
        )
        ts_str = str(row.get("timestamp", ""))[:19]  # trim microseconds
        rows_html += f"""
        <tr style="background:{row_bg};border-bottom:1px solid {C['border']};">
            <td style="padding:7px 10px;font-size:12px;font-family:Space Mono,monospace;color:{C['dimmed']};">{row.get('transaction_id','—')}</td>
            <td style="padding:7px 10px;font-size:12px;font-family:Space Mono,monospace;">{row.get('user_id','—')}</td>
            <td style="padding:7px 10px;font-size:12px;">{ts_str}</td>
            <td style="padding:7px 10px;font-size:12px;font-family:Space Mono,monospace;color:{'#e63946' if is_fraud else C['text']};font-weight:{'700' if is_fraud else '400'};">${row.get('amount',0):,.2f}</td>
            <td style="padding:7px 10px;font-size:12px;">{row.get('merchant_category','—')}</td>
            <td style="padding:7px 10px;font-size:12px;">{row.get('city','—')}</td>
            <td style="padding:7px 10px;font-size:12px;">{status_html}</td>
        </tr>
        """

    header_style = f"padding:8px 10px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:{C['dimmed']};border-bottom:2px solid {C['border']};"
    table_html = f"""
    <div style="overflow-x:auto;max-height:320px;overflow-y:auto;">
    <table style="width:100%;border-collapse:collapse;font-family:Syne,sans-serif;">
        <thead style="position:sticky;top:0;background:{C['panel']};z-index:1;">
            <tr>
                <th style="{header_style}">Txn ID</th>
                <th style="{header_style}">User</th>
                <th style="{header_style}">Timestamp</th>
                <th style="{header_style}">Amount</th>
                <th style="{header_style}">Merchant</th>
                <th style="{header_style}">City</th>
                <th style="{header_style}">Status</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def render_schema_report(report: dict):
    """Shows what column mappings were applied to the uploaded file."""
    with st.expander("🔧 Schema Mapping Report — click to see column normalization"):
        mappings = report.get("column_mappings", {})
        warnings = report.get("warnings", [])
        rows_before = report.get("rows_before", 0)
        rows_after  = report.get("rows_after", 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Rows Loaded",   f"{rows_before:,}")
        c2.metric("Rows After Clean", f"{rows_after:,}")
        c3.metric("Dropped Rows", f"{rows_before - rows_after:,}",
                  delta_color="inverse" if rows_before != rows_after else "normal")

        if mappings:
            st.markdown("**Column name normalizations applied:**")
            for orig, standard in mappings.items():
                if orig != standard:
                    st.markdown(f"- `{orig}` → `{standard}`")
                else:
                    st.markdown(f"- `{orig}` ✓ already standard")

        if warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.success("✅ No issues found — all columns mapped successfully.")