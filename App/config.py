# ============================================================
#  config.py
#  Central configuration — column aliases, thresholds, colors
#  Edit THIS file to adapt the app to any new dataset
# ============================================================

# ── Standard internal column names the app always uses ───────
# No matter what the uploaded CSV calls them, they get mapped
# to these names by schema.py before anything else runs.
STANDARD_COLUMNS = {
    "transaction_id",
    "user_id",
    "timestamp",
    "amount",
    "merchant_category",
    "city",
    "status",
}

# ── Column Aliases ────────────────────────────────────────────
# Add any new variation you encounter to the relevant list.
# The mapper checks each list and renames to the dict key.
COLUMN_ALIASES = {
    "transaction_id": [
        "transaction_id", "Transaction_ID", "txn_id", "TXN_ID",
        "trans_id", "TransactionID", "id", "transaction_number",
        "txnid", "Txn_ID", "order_id",
    ],
    "user_id": [
        "user_id", "User_ID", "UserID", "uid", "UID",
        "customer_id", "CustomerID", "account_id", "AccountID",
        "client_id", "user", "userId",
    ],
    "timestamp": [
        "timestamp", "Timestamp", "TIMESTAMP", "time_stamp",
        "Time_Stamp", "txn_time", "TxnTime", "created_at",
        "CreatedAt", "date_time", "DateTime", "transaction_time",
        "TransactionTime", "event_time", "datetime", "date",
    ],
    "amount": [
        "amount", "Amount", "AMOUNT", "amount_usd", "Amount_USD",
        "txn_amount", "TxnAmount", "transaction_amount",
        "TransactionAmount", "value", "Value", "price", "Price",
        "total", "Total", "amt",
    ],
    "merchant_category": [
        "merchant_category", "Merchant_Category", "MerchantCategory",
        "merchant_type", "MerchantType", "category", "Category",
        "merchant", "Merchant", "mcc", "MCC", "merchant_code",
        "business_type", "BusinessType",
    ],
    "city": [
        "city", "City", "CITY", "location_city", "Location_City",
        "location", "Location", "geo", "Geo", "region", "Region",
        "country", "Country", "place", "Place", "geography",
    ],
    "status": [
        "status", "Status", "STATUS", "txn_status", "TxnStatus",
        "transaction_status", "TransactionStatus", "state", "State",
        "result", "Result", "outcome", "flag", "Flag",
    ],
}

# ── Status Value Aliases ──────────────────────────────────────
# Maps any variation of fraud/approved labels to standard values
STATUS_ALIASES = {
    "Flagged": [
        "flagged", "Flagged", "FLAGGED", "fraud", "Fraud", "FRAUD",
        "suspicious", "Suspicious", "blocked", "Blocked", "declined",
        "Declined", "rejected", "Rejected", "alert", "Alert", "1",
    ],
    "Approved": [
        "approved", "Approved", "APPROVED", "legitimate", "Legitimate",
        "normal", "Normal", "ok", "OK", "success", "Success",
        "passed", "Passed", "valid", "Valid", "0",
    ],
}

# ── Detection Thresholds (defaults — user can override in sidebar) ──
DEFAULTS = {
    "velocity_threshold":   5,      # txns in 1 hour = suspicious
    "amount_threshold":     500,    # USD — high value alert
    "travel_window_hrs":    1,      # hours — impossible travel window
    "auto_refresh_secs":    5,      # seconds between auto-refresh
}

# ── Chart Colors ──────────────────────────────────────────────
COLORS = {
    "red":    "#e63946",
    "orange": "#ff8c42",
    "green":  "#06d6a0",
    "blue":   "#4cc9f0",
    "purple": "#9b59b6",
    "grey":   "#4a5568",
    "bg":     "#080b12",
    "panel":  "#0d1220",
    "border": "#1a2440",
    "text":   "#c8d6e5",
    "dimmed": "#64748b",
}

# Plotly-safe rgba equivalents for transparent fills
FILLS = {
    "red":    "rgba(230,57,70,0.13)",
    "orange": "rgba(255,140,66,0.13)",
    "green":  "rgba(6,214,160,0.13)",
    "blue":   "rgba(76,201,240,0.13)",
}

# ── Plotly Base Layout ────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="#0d1220",
    plot_bgcolor="#080b12",
    font=dict(family="Syne, sans-serif", color="#c8d6e5"),
    xaxis=dict(gridcolor="#1a2440", zerolinecolor="#1a2440"),
    yaxis=dict(gridcolor="#1a2440", zerolinecolor="#1a2440"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="#0d1220", bordercolor="#1a2440", borderwidth=1),
)