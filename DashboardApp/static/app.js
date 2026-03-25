const el = (id) => document.getElementById(id);

const state = {
  activeTab: "overview",
  autoRefreshTimer: null,
  currentMode: "batch",
};

function setModeUI(mode) {
  state.currentMode = mode;
  const liveDot = el("liveDot");
  const modeText = el("modeText");
  const modeToggle = el("modeToggle");

  const isStream = mode === "stream";
  liveDot.classList.toggle("live", isStream);
  modeText.textContent = isStream ? "Live Stream Mode" : "Batch Mode";
  modeToggle.checked = isStream;
}

function formatNumber(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  const num = Number(n);
  if (Number.isInteger(num)) return num.toLocaleString();
  return num.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

function setKpis(kpis) {
  el("kpi-total").textContent = formatNumber(kpis.total);
  el("kpi-flagged").textContent = formatNumber(kpis.flagged);
  el("kpi-fraud-rate").textContent = `${formatNumber(kpis.fraud_rate_pct)}%`;
  el("kpi-avg-fraud-amt").textContent = `$${formatNumber(kpis.avg_fraud_amt).replace(/\.0+$/, "")}`;
  el("kpi-velocity-suspects").textContent = formatNumber(kpis.velocity_suspects);
  el("kpi-impossible-travel").textContent = formatNumber(kpis.impossible_travel_cases);
}

function renderSimpleTable(container, columns, rows, rowStyleFn) {
  if (!container) return;
  if (!rows || rows.length === 0) {
    container.innerHTML = `<div style="color: var(--dimmed); padding: 10px;">No rows.</div>`;
    return;
  }

  const thead = `<thead><tr>${columns.map((c) => `<th>${c}</th>`).join("")}</tr></thead>`;
  const tbody = rows
    .map((r) => {
      const style = rowStyleFn ? rowStyleFn(r) : "";
      return `<tr style="${style}">
        ${columns.map((c) => `<td>${r[c] ?? ""}</td>`).join("")}
      </tr>`;
    })
    .join("");

  container.innerHTML = `<table>${thead}<tbody>${tbody}</tbody></table>`;
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, { ...options, credentials: "same-origin" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

async function fetchFigure(url, divId) {
  const data = await fetchJSON(url);
  const fig = JSON.parse(data.figure);
  await Plotly.react(divId, fig.data, fig.layout, fig.config || {});
}

function setActiveTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${tab}`);
  });
  loadActiveTab().catch(console.error);
}

async function loadKPIs() {
  const data = await fetchJSON("/api/kpis");
  setModeUI(data.mode);
  setKpis(data.kpis);
}

async function loadLiveTicker() {
  const data = await fetchJSON("/api/live-ticker?n=25");
  renderLiveTable(data.live_ticker || []);
}

function renderLiveTable(rows) {
  const container = el("table-live-ticker");
  const columns = ["transaction_id", "timestamp", "amount", "merchant_category", "city", "status", "user_id"];
  const normalized = rows.map((r) => ({
    transaction_id: r.transaction_id ?? "",
    timestamp: r.timestamp ?? "",
    amount: r.amount ?? "",
    merchant_category: r.merchant_category ?? "",
    city: r.city ?? "",
    status: r.status ?? "",
    user_id: r.user_id ?? "",
  }));

  renderSimpleTable(
    container,
    columns,
    normalized,
    (r) => (r.status === "Flagged" ? "background: rgba(230,57,70,0.10);" : "")
  );
}

async function loadOverviewCharts() {
  await Promise.all([
    fetchFigure("/api/overview/hourly-heatmap", "chart-hourly-heatmap"),
    fetchFigure("/api/overview/daily-trend", "chart-daily-trend"),
    fetchFigure("/api/overview/amount-distribution", "chart-amount-distribution"),
  ]);
}

async function loadMerchantCharts() {
  await Promise.all([
    fetchFigure("/api/merchant-risk/treemap", "chart-merchant-treemap"),
    fetchFigure("/api/merchant-risk/fraud-donut", "chart-merchant-fraud-donut"),
    fetchFigure("/api/merchant-risk/merchant-bar", "chart-merchant-bar"),
  ]);
}

async function loadGeoCharts() {
  await Promise.all([
    fetchFigure("/api/geo-anomaly/geo-map", "chart-geo-map"),
    (async () => {
      const data = await fetchJSON("/api/geo-anomaly/travel-routes");
      const fig = JSON.parse(data.figure);
      await Plotly.react("chart-travel-routes", fig.data, fig.layout, fig.config || {});
      renderSimpleTable(
        el("table-travel-routes"),
        ["route", "cases", "flagged_cases", "avg_gap_hrs", "risk_level"],
        data.rows || []
      );
    })(),
  ]);
}

async function loadVelocityCharts() {
  await fetchFigure("/api/velocity-spikes/velocity-histogram", "chart-velocity-histogram");
}

async function loadUsers() {
  const data = await fetchJSON("/api/user-profiles/watchlist");

  const watchlistRows = data.rows || [];
  const columns = [
    "user_id",
    "risk_score",
    "risk_label",
    "flagged_txns",
    "max_velocity",
    "impossible_travel",
    "cities_used",
    "max_amount",
    "reasons",
  ];

  // Dropdown options
  const userSelect = el("userSelect");
  userSelect.innerHTML = "";
  watchlistRows.slice(0, 50).forEach((r) => {
    const opt = document.createElement("option");
    opt.value = r.user_id;
    opt.textContent = `${r.user_id} (Score: ${r.risk_score}/100)`;
    userSelect.appendChild(opt);
  });

  renderSimpleTable(el("table-watchlist"), columns, watchlistRows.map((r) => {
    const obj = {};
    columns.forEach((c) => obj[c] = r[c] ?? "");
    return obj;
  }));
}

async function loadUserTxns() {
  const userId = el("userSelect").value;
  if (!userId) return;
  const data = await fetchJSON(`/api/user/${encodeURIComponent(userId)}/txns`);
  const container = el("table-user-txns");
  const columns = ["transaction_id", "timestamp", "amount", "merchant_category", "city", "status"];
  const normalized = (data.rows || []).map((r) => ({
    transaction_id: r.transaction_id ?? "",
    timestamp: r.timestamp ?? "",
    amount: r.amount ?? "",
    merchant_category: r.merchant_category ?? "",
    city: r.city ?? "",
    status: r.status ?? "",
  }));
  renderSimpleTable(
    container,
    columns,
    normalized,
    (r) => (r.status === "Flagged" ? "background: rgba(230,57,70,0.10);" : "")
  );
}

async function loadActiveTab() {
  const tab = state.activeTab;
  if (tab === "overview") return loadOverviewCharts();
  if (tab === "merchant") return loadMerchantCharts();
  if (tab === "geo") return loadGeoCharts();
  if (tab === "velocity") return loadVelocityCharts();
  if (tab === "users") return loadUsers();
  if (tab === "live") return loadLiveTicker();
}

async function stepStream() {
  const data = await fetchJSON("/api/live/advance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n_new: 3, n_latest: 25 }),
  });
  setModeUI(data.mode);
  setKpis(data.kpis);
  renderLiveTable(data.live_ticker || []);
  await loadActiveTab().catch(() => {});
}

function setAutoRefresh(enabled) {
  const autoToggle = el("autoToggle");
  autoToggle.checked = enabled;

  if (state.autoRefreshTimer) {
    clearInterval(state.autoRefreshTimer);
    state.autoRefreshTimer = null;
  }
  if (!enabled) return;

  // Only useful in stream mode, but keep it on anyway and it will just "refresh".
  state.autoRefreshTimer = setInterval(() => {
    stepStream().catch(console.error);
  }, 5000);
}

async function init() {
  const modeData = await fetchJSON("/api/mode");
  setModeUI(modeData.mode);

  el("modeToggle").addEventListener("change", async (e) => {
    const mode = e.target.checked ? "stream" : "batch";
    await fetchJSON("/api/mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    await loadKPIs();
    await loadActiveTab();
  });

  el("autoToggle").addEventListener("change", (e) => {
    setAutoRefresh(e.target.checked);
  });

  el("refreshBtn").addEventListener("click", async () => {
    if (state.currentMode === "stream") {
      await stepStream();
    } else {
      await loadKPIs();
      await loadActiveTab();
    }
  });

  el("loadBtn").addEventListener("click", async () => {
    const fileInput = el("csvFile");
    const file = fileInput.files[0];
    const mode = el("modeToggle").checked ? "stream" : "batch";
    if (!file) {
      alert("Please select a CSV file first.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);
    const data = await fetchJSON("/api/upload", {
      method: "POST",
      body: form,
    });
    setModeUI(data.mode);
    setKpis(data.kpis);
    renderLiveTable(data.live_ticker || []);
    await loadActiveTab();
  });

  el("loadUserTxnsBtn").addEventListener("click", () => loadUserTxns().catch(console.error));

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });

  // Initial render
  await loadKPIs();
  await loadOverviewCharts();
  await loadLiveTicker();
}

init().catch(console.error);

