# ============================================================
#  data/loader.py
#  Data Source Layer — abstracts WHERE data comes from
#
#  Today:   CSV file upload  (BatchSource)
#  Future:  Kafka / WebSocket / REST API  (StreamSource)
#
#  The app always calls get_data() — it never knows or cares
#  whether data came from a file or a live stream.
# ============================================================

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from data.schema import validate_and_normalize


# ── Abstract Base: defines the contract for ALL data sources ──
class DataSource(ABC):
    """
    Every data source (CSV, Kafka, API, WebSocket) must implement
    this interface. The dashboard only talks to DataSource — never
    directly to files or streams.
    """

    @abstractmethod
    def get_data(self) -> tuple[pd.DataFrame, dict]:
        """Return (normalized_df, schema_report)"""
        pass

    @abstractmethod
    def get_latest(self, n: int = 20) -> pd.DataFrame:
        """Return the N most recent transactions (for live ticker)"""
        pass

    @property
    @abstractmethod
    def source_label(self) -> str:
        """Human-readable label shown in the UI"""
        pass


# ── Source 1: CSV / File Upload (used today) ─────────────────
class BatchSource(DataSource):
    """
    Loads from a local CSV file or a Streamlit UploadedFile object.
    Used for hackathon demo and offline analysis.
    """

    def __init__(self, filepath_or_buffer):
        self._raw = pd.read_csv(filepath_or_buffer)
        self._df  = None
        self._report = {}

    def get_data(self) -> tuple[pd.DataFrame, dict]:
        if self._df is None:
            self._df, self._report = validate_and_normalize(self._raw)
        return self._df, self._report

    def get_latest(self, n: int = 20) -> pd.DataFrame:
        df, _ = self.get_data()
        return df.sort_values("timestamp", ascending=False).head(n)

    @property
    def source_label(self) -> str:
        return "📂 CSV / Batch File"


# ── Source 2: Simulated Live Stream (demo real-time mode) ─────
class SimulatedStreamSource(DataSource):
    """
    Generates synthetic transactions in real-time to simulate
    a live data stream.  Plug in Kafka/WebSocket here later —
    just replace _generate_transaction() with a real consumer.

    HOW TO UPGRADE TO REAL KAFKA LATER:
        1. pip install confluent-kafka
        2. Replace _generate_transaction() with:
               consumer = Consumer({...})
               msg = consumer.poll(1.0)
               return json.loads(msg.value())
        3. Nothing else in the app changes.
    """

    CITIES     = ["New York", "London", "Dubai", "Mumbai", "Toronto", "Sydney"]
    MERCHANTS  = ["Groceries", "Dining", "Retail", "Electronics", "Travel", "Crypto Exchange"]
    FRAUD_MERCHANTS = {"Crypto Exchange": 0.35, "Electronics": 0.12}

    def __init__(self, seed_df: pd.DataFrame | None = None):
        """
        If seed_df is provided (from an uploaded CSV), the stream
        replays + augments it. Otherwise generates from scratch.
        """
        self._seed_df = seed_df
        self._buffer: list[dict] = []
        self._last_user_city: dict = {}  # tracks last city per user for geo anomalies

        # Pre-seed with historical data if available
        if seed_df is not None:
            clean, _ = validate_and_normalize(seed_df)
            self._buffer = clean.to_dict("records")

    def _generate_transaction(self) -> dict:
        """Generates one synthetic transaction with realistic fraud patterns."""
        user_id   = f"USR-{random.randint(0, 14999):05d}"
        merchant  = random.choice(self.MERCHANTS)
        city      = random.choice(self.CITIES)
        ts        = datetime.now()

        # Fraud probability based on merchant
        fraud_prob = self.FRAUD_MERCHANTS.get(merchant, 0.001)

        # Inject impossible travel occasionally
        last_city = self._last_user_city.get(user_id)
        if last_city and last_city != city and random.random() < 0.05:
            fraud_prob = max(fraud_prob, 0.6)  # suspicious if city changed fast

        self._last_user_city[user_id] = city

        # Fraudulent transactions have higher amounts
        is_fraud = random.random() < fraud_prob
        amount   = round(random.uniform(800, 3000), 2) if is_fraud \
                   else round(random.uniform(5, 200), 2)

        return {
            "transaction_id":    f"TXN-{random.randint(1000000,9999999)}",
            "user_id":           user_id,
            "timestamp":         ts,
            "amount":            amount,
            "merchant_category": merchant,
            "city":              city,
            "status":            "Flagged" if is_fraud else "Approved",
            # Derived columns (add directly so no re-normalization needed)
            "hour":              ts.hour,
            "date":              ts.date(),
            "day_of_week":       ts.strftime("%A"),
            "is_flagged":        int(is_fraud),
        }

    def push_new_transactions(self, n: int = 3):
        """
        Call this on each auto-refresh tick to add new live transactions.
        In a real system, this would be replaced by a Kafka consumer poll.
        """
        for _ in range(n):
            self._buffer.append(self._generate_transaction())

    def get_data(self) -> tuple[pd.DataFrame, dict]:
        if not self._buffer:
            self.push_new_transactions(50)  # warm up
        df = pd.DataFrame(self._buffer)
        report = {
            "column_mappings":    {"source": "live stream — no mapping needed"},
            "invalid_timestamps": 0,
            "rows_before":        len(df),
            "rows_after":         len(df),
            "warnings":           [],
        }
        return df, report

    def get_latest(self, n: int = 20) -> pd.DataFrame:
        df, _ = self.get_data()
        return df.sort_values("timestamp", ascending=False).head(n)

    @property
    def source_label(self) -> str:
        return "🔴 Live Simulated Stream"


# ── FUTURE STUB: Real Kafka Stream ────────────────────────────
# Uncomment and fill in when you have a real stream.
#
# class KafkaStreamSource(DataSource):
#     def __init__(self, bootstrap_servers: str, topic: str):
#         from confluent_kafka import Consumer
#         self._consumer = Consumer({
#             "bootstrap.servers": bootstrap_servers,
#             "group.id": "fraudguard",
#             "auto.offset.reset": "latest",
#         })
#         self._consumer.subscribe([topic])
#         self._buffer = []
#
#     def push_new_transactions(self, n=10):
#         for _ in range(n):
#             msg = self._consumer.poll(0.5)
#             if msg and not msg.error():
#                 import json
#                 self._buffer.append(json.loads(msg.value()))
#
#     def get_data(self):
#         df = pd.DataFrame(self._buffer)
#         df, report = validate_and_normalize(df)
#         return df, report
#
#     def get_latest(self, n=20):
#         df, _ = self.get_data()
#         return df.sort_values("timestamp", ascending=False).head(n)
#
#     @property
#     def source_label(self): return "⚡ Kafka Live Stream"


def build_source(uploaded_file=None, mode: str = "batch") -> DataSource:
    """
    Factory function — the app calls this once.
    Returns the right DataSource based on mode.

    Args:
        uploaded_file: Streamlit UploadedFile or filepath string
        mode: "batch" | "stream"
    """
    if mode == "stream":
        seed_df = pd.read_csv(uploaded_file) if uploaded_file else None
        return SimulatedStreamSource(seed_df=seed_df)
    else:
        if uploaded_file is None:
            # fallback to local file
            return BatchSource("FinTech_Fraud_Logs.csv")
        return BatchSource(uploaded_file)