# 🛡️ LogicLoop — FinTech Transaction Anomaly & Fraud Visualizer

> **National Hackathon 2026 · Track D5 · Team 44 — Logic Loop**

An interactive, real-time fraud detection dashboard built with **Streamlit + Plotly + Pandas** that detects suspicious financial transactions, surfaces high-risk users, and provides actionable insights for fraud prevention — all through a sleek dark-themed visualization interface.

---

## 📋 Table of Contents

- [Problem Statement (D5)](#-problem-statement-d5)
- [How This Project Solves D5](#-how-this-project-solves-d5)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Overall Architecture & Flow](#-overall-architecture--flow)
- [Fraud Detection Algorithms](#-fraud-detection-algorithms)
- [How to Run](#-how-to-run)
- [Using the Dashboard](#-using-the-dashboard)
- [Dataset Format](#-dataset-format)
- [Configuration](#-configuration)

---

## 🎯 Problem Statement (D5)

In today's digital financial ecosystem, fraud detection is one of the most critical challenges. With rapidly growing volumes of online transactions, identifying fraudulent activities is hard due to:

- **Difficulty in detecting real-time fraudulent transactions** — fraud happens in seconds, but traditional batch analysis is too slow
- **Lack of visibility into high-risk users and locations** — no single view surfaces who or where to investigate
- **No clear way to detect unusual transaction behavior** — velocity spikes and burst patterns go unnoticed
- **Inefficient monitoring of fraud patterns over time** — peak fraud hours and recurring patterns remain hidden
- **Data interpretation complexity** — raw transaction logs are unreadable for decision-makers

The dataset represents financial transaction logs with user activity, timestamps, amounts, risk scores, and geographic locations.

---

## ✅ How This Project Solves D5

| D5 Problem | LogicLoop Solution | Impact |
|---|---|---|
| No real-time monitoring | Live Stream Mode with auto-refresh every 5s | Immediate detection of suspicious activity |
| Fraud patterns not visible | Time-series heatmaps, hourly & daily trend charts | Identifies peak fraud hours and spikes |
| Difficult to detect risky users | Composite Risk Score (0–100) across 5 fraud signals | Instantly highlights users to freeze/investigate |
| No geographical insights | City-wise fraud map and impossible travel detection | Identifies fraud hubs and geo anomalies |
| Raw data hard to understand | Interactive KPI cards, charts, and watchlist tables | Easy decision-making for non-technical stakeholders |
| Stolen card testing via rapid small txns | Velocity detection — flags users with 5+ txns/hour | Auto-block candidates identified immediately |

---

## ✨ Key Features

### 📊 Tab 1 — Overview & KPIs
- Total transactions, fraud count, fraud rate %
- Average fraudulent vs. normal transaction amounts
- Hourly heatmap showing when fraud spikes occur
- Daily trend line — total vs. flagged transactions

### 🏪 Tab 2 — Merchant Analysis
- Treemap of fraud by merchant category
- Bar chart of fraud rate per merchant type
- Risk classification: CRITICAL / HIGH / CLEAN
- Fraud amount distribution histogram

### 🗺️ Tab 3 — Geographic Intelligence
- City-level fraud map (choropleth/bubble)
- **Impossible Travel Detection** — flags users appearing in 2 different cities within 1 hour (physically impossible)
- Travel route visualization with risk levels

### ⚡ Tab 4 — Transaction Velocity
- Sliding-window velocity analysis (1-hour windows)
- Users with 5+ transactions in 60 minutes are flagged
- Velocity histogram with risk scores
- Flagged user table with burst details

### 👤 Tab 5 — User Risk Profiles (Watchlist)
- Composite risk score (0–100) combining 5 signals: fraud flags, velocity, geo anomalies, crypto merchant usage, high transaction amounts
- CRITICAL / HIGH / MEDIUM risk labels
- Top 5 "freeze these accounts now" panel
- Full watchlist table (up to 100 users)
- Drill-down: investigate any individual user's full transaction timeline

### 📡 Tab 6 — Live Transaction Feed
- Most recent 25 transactions in real time
- Fraud rows highlighted in red
- Rule accuracy metrics — Precision, Recall, F1 Score
- Threshold sweep simulator: find the optimal fraud-blocking threshold

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Dashboard Framework | [Streamlit](https://streamlit.io/) |
| Charts & Visualizations | [Plotly](https://plotly.com/python/) |
| Data Processing | [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/) |
| Styling | Custom CSS (Space Mono + Syne fonts, dark theme) |
| Live Streaming (simulated) | In-memory stream source with push simulation |
| Production Ready | Kafka integration stub in `data/loader.py` |

---

## 📁 Project Structure

```
hackathon_ibm_fintach/
│
├── D5_44_IBM.pdf                    # Problem statement & insight report
│
└── DashboardApp/
    ├── app.py                       # Main Streamlit app — entry point
    ├── config.py                    # Colors, thresholds, column aliases
    ├── requirements.txt             # Python dependencies
    ├── FinTech_Fraud_Logs.csv       # Sample dataset (14MB)
    │
    ├── data/
    │   ├── loader.py                # CSV / stream data source builder
    │   ├── processor.py             # All fraud detection algorithms
    │   └── schema.py                # Column normalisation & validation
    │
    └── components/
        ├── kpis.py                  # KPI metric cards, alert boxes
        ├── charts.py                # All Plotly chart builders
        └── alerts.py                # Live ticker feed renderer
```

---

## 🔄 Overall Architecture & Flow

```
User uploads CSV  ──►  schema.py           (normalise column names & status labels)
       │                   │
       ▼                   ▼
  loader.py  ──────►  BatchSource / StreamSource
  (build_source)             │
                             ▼
                       processor.py        (pure analytical functions)
                       ┌─────────────────────────────────────┐
                       │ compute_kpis()          → KPI numbers│
                       │ compute_hourly()        → heatmap    │
                       │ compute_daily()         → trend line │
                       │ compute_merchant_stats()→ treemap    │
                       │ compute_city_stats()    → geo map    │
                       │ compute_velocity()      → burst detect│
                       │ compute_impossible_travel()→ geo fraud│
                       │ compute_user_profiles() → watchlist  │
                       │ compute_false_positive_stats()       │
                       └─────────────────────────────────────┘
                             │
                             ▼
                       components/          (rendering layer)
                       kpis.py + charts.py + alerts.py
                             │
                             ▼
                       app.py               (Streamlit tabs → final UI)
```

**Two operating modes:**
- **Batch Mode** — loads the full CSV once; great for historical analysis
- **Live Stream Mode** — simulates real-time transactions arriving every few seconds (swap `push_new_transactions()` in `loader.py` for a real Kafka consumer in production)

---

## 🔍 Fraud Detection Algorithms

### 1. Transaction Velocity Detection
Identifies users who execute ≥ 5 transactions within any rolling 1-hour window — a classic signal that a stolen card is being tested with small rapid purchases.

```
For each user → slide a 1-hour window across their sorted transactions
If window count ≥ 5 → flag user, compute risk score = min(100, txns×10 + 40 if fraud present)
```

### 2. Impossible Travel Detection
Flags users whose account appears in two different cities within 1 hour — physically impossible and a strong account takeover signal.

```
For each user → compare consecutive transactions
If city_1 ≠ city_2 AND time_gap ≤ 1 hour → record impossible travel event
```

### 3. Composite User Risk Score (0–100)
Five weighted signals combined per user:

| Signal | Max Points |
|---|---|
| Fraud-flagged transactions (×15 each) | 40 |
| Transaction velocity burst | 20 |
| Impossible travel events (×8 each) | 15 |
| Crypto Exchange usage | 10 |
| High single transaction amount | 15 |

**Risk Labels:** 🔴 CRITICAL (70+) · 🟠 HIGH (40–69) · 🟡 MEDIUM (15–39) · 🟢 LOW (<15)

### 4. False Positive / Rule Accuracy Analysis
Measures how precisely the `amount > $500 at Crypto/Electronics` rule catches real fraud without blocking legitimate customers. Outputs Precision, Recall, and F1 Score with a threshold-sweep chart.

---

## 🚀 How to Run

### Prerequisites
- Python 3.10 or higher
- pip

### 1. Clone the repository
```bash
git clone https://github.com/ghogharimeet21/hackathon_ibm_fintach.git
cd hackathon_ibm_fintach/DashboardApp
```

### 2. Install dependencies
```bash
pip install streamlit plotly pandas numpy
```

> For the full dependency set (includes optional libraries):
> ```bash
> pip install -r requirements.txt
> ```

### 3. Run the dashboard
```bash
streamlit run app.py
```

The app will open automatically at **http://localhost:8501**

### 4. Load the sample data
The included `FinTech_Fraud_Logs.csv` loads automatically on startup. You can also upload your own CSV using the sidebar.

---

## 🖥️ Using the Dashboard

| Sidebar Control | What it does |
|---|---|
| **Upload CSV** | Load your own transaction dataset |
| **▶ Load Data** | Reload data after uploading a new CSV |
| **🔴 Live Stream Mode** | Toggles simulated real-time transaction feed |
| **🔄 Auto-Refresh** | Refreshes the dashboard every 5 seconds automatically |
| **🔁 Refresh Now** | Manual single refresh; pushes 5 new simulated transactions in stream mode |

Navigate across the **6 tabs** in the main panel for different views of the fraud landscape.

---

## 📂 Dataset Format

The app accepts any CSV with these columns (many naming variations are auto-detected):

| Standard Name | Accepted Aliases |
|---|---|
| `transaction_id` | `txn_id`, `TransactionID`, `order_id`, ... |
| `user_id` | `UserID`, `customer_id`, `account_id`, ... |
| `timestamp` | `Timestamp`, `created_at`, `event_time`, ... |
| `amount` | `Amount`, `txn_amount`, `value`, `price`, ... |
| `merchant_category` | `Merchant`, `category`, `mcc`, ... |
| `city` | `location`, `region`, `geo`, ... |
| `status` | `flag`, `outcome`, `result`, ... (Flagged / Approved) |

**Status values** are also auto-normalised: `fraud`, `FRAUD`, `suspicious`, `blocked`, `1` → `Flagged`; `legitimate`, `normal`, `ok`, `0` → `Approved`.

---

## ⚙️ Configuration

Edit `config.py` to adjust detection thresholds or add new column name aliases for your dataset:

```python
# Detection thresholds
DEFAULTS = {
    "velocity_threshold":  5,    # txns in 1 hour = suspicious
    "amount_threshold":    500,  # USD — high value alert
    "travel_window_hrs":   1,    # hours — impossible travel window
    "auto_refresh_secs":   5,    # seconds between auto-refresh
}
```

No other files need to change when adapting to a new dataset — `config.py` is the single source of truth for all aliases and thresholds.

---

## 👥 Team

**Team 44 — Logic Loop**  
National Hackathon 2026 · IBM FinTech Track · Problem D5

---

*Built with Streamlit · Plotly · Pandas*
