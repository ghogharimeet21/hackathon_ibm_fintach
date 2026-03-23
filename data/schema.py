# ============================================================
#  data/schema.py
#  Column mapper — normalizes ANY dataset to standard schema
#  This is the "translation layer" between raw data and the app
# ============================================================

import pandas as pd
from config import COLUMN_ALIASES, STATUS_ALIASES, STANDARD_COLUMNS


class SchemaError(Exception):
    """Raised when required columns can't be mapped."""
    pass


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Takes a raw DataFrame with ANY column names and returns:
    - df with standardized column names
    - mapping_report: dict showing what was renamed (for user feedback)

    Example:
        "Time_Stamp" → "timestamp"
        "Amount_USD" → "amount"
        "Location_City" → "city"
    """
    df = df.copy()
    raw_cols = list(df.columns)
    mapping_report = {}   # { original_name: standard_name }
    missing = []

    for standard_name, aliases in COLUMN_ALIASES.items():
        matched = None
        # Check each raw column against the alias list (case-insensitive)
        for raw_col in raw_cols:
            if raw_col in aliases or raw_col.strip().lower() in [a.lower() for a in aliases]:
                matched = raw_col
                break

        if matched:
            if matched != standard_name:
                df.rename(columns={matched: standard_name}, inplace=True)
                mapping_report[matched] = standard_name
            else:
                mapping_report[matched] = standard_name  # already correct
        else:
            missing.append(standard_name)

    # Soft fail: warn about missing but don't crash if non-critical
    critical = {"timestamp", "amount", "status"}
    critical_missing = [c for c in missing if c in critical]
    if critical_missing:
        raise SchemaError(
            f"Could not find required columns: {critical_missing}\n"
            f"Dataset has: {raw_cols}\n"
            f"Please check config.py → COLUMN_ALIASES and add your column names."
        )

    return df, mapping_report


def normalize_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes status column values to standard "Flagged" / "Approved".
    Handles variations like: fraud/legitimate, 1/0, blocked/success, etc.
    """
    df = df.copy()
    if "status" not in df.columns:
        return df

    # Build reverse lookup: "fraud" → "Flagged", "approved" → "Approved"
    reverse_map = {}
    for standard_val, variants in STATUS_ALIASES.items():
        for v in variants:
            reverse_map[v.lower()] = standard_val

    def map_status(val):
        if pd.isna(val):
            return "Unknown"
        return reverse_map.get(str(val).strip().lower(), str(val))

    df["status"] = df["status"].apply(map_status)
    return df


def parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Robustly parses timestamp column — handles many formats:
    '2023-12-31 03:00:00', '31/12/2023', '2023-12-31T03:00:00Z', etc.
    """
    df = df.copy()
    if "timestamp" not in df.columns:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Drop rows where timestamp couldn't be parsed
    invalid = df["timestamp"].isna().sum()
    if invalid > 0:
        df = df.dropna(subset=["timestamp"])

    return df, invalid


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds columns the app needs: hour, date, day_of_week, is_flagged.
    These are always derived from the standard schema.
    """
    df = df.copy()
    df["hour"]        = df["timestamp"].dt.hour
    df["date"]        = df["timestamp"].dt.date
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["is_flagged"]  = (df["status"] == "Flagged").astype(int)
    df["amount"]      = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    return df


def validate_and_normalize(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Master function — runs the full normalization pipeline.
    Call this on any raw DataFrame before passing it to the app.

    Returns:
        (clean_df, report) where report has mapping info + warnings
    """
    report = {
        "column_mappings": {},
        "invalid_timestamps": 0,
        "rows_before": len(df),
        "rows_after": 0,
        "warnings": [],
    }

    # Step 1 — normalize column names
    df, col_map = normalize_columns(df)
    report["column_mappings"] = col_map

    # Step 2 — normalize status values
    df = normalize_status(df)

    # Step 3 — parse timestamps
    df, invalid_ts = parse_timestamps(df)
    report["invalid_timestamps"] = invalid_ts
    if invalid_ts > 0:
        report["warnings"].append(f"{invalid_ts} rows dropped — unparseable timestamps")

    # Step 4 — add derived columns
    df = add_derived_columns(df)

    report["rows_after"] = len(df)
    return df, report