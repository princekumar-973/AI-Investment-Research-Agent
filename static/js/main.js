/**
 * main.js – InvestIQ Dashboard Logic
 * ====================================
 * Handles:
 *  1. Ticker autocomplete search via /api/ticker-search/
 *  2. Main analysis trigger via /api/analyze/
 *  3. Populating all dashboard sections from the JSON response
 *  4. Chart.js chart rendering (Revenue, Score, Competitor)
 *
 * No external libraries except Chart.js (loaded via CDN in <head>).
 * All DOM manipulation is done via vanilla JavaScript.
 */

"use strict";

/* ── Chart references (so we can destroy before re-render) ──────────────── */
let revenueChart     = null;
let scoreChart       = null;
let competitorChart  = null;
let modalChart       = null;

/* ── Autocomplete state ─────────────────────────────────────────────────── */
let autocompleteTimeout = null;

/* ══════════════════════════════════════════════════════════════════════════
   Helper utilities
══════════════════════════════════════════════════════════════════════════ */

/**
 * Format a large number to a human-readable string.
 * e.g. 1_500_000_000 → "$1.50B"
 */
function formatNumber(value) {
  if (value == null || value === 0) return "N/A";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9)  return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6)  return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  return `${sign}$${abs.toLocaleString()}`;
}

/** Safely access a nested property, returning fallback if missing/null. */
function safe(obj, key, fallback = "N/A") {
  const val = obj?.[key];
  return (val !== undefined && val !== null && val !== "") ? val : fallback;
}

/** Show or hide the global error banner. */
function showError(message) {
  const banner = document.getElementById("errorBanner");
  document.getElementById("errorText").textContent = message;
  banner.classList.remove("hidden");
}
function hideError() {
  document.getElementById("errorBanner").classList.add("hidden");
}

/** Toggle search button between loading and default states. */
function setLoading(loading) {
  const btn     = document.getElementById("searchBtn");
  const text    = document.getElementById("searchBtnText");
  const icon    = document.getElementById("searchBtnIcon");
  const spinner = document.getElementById("searchBtnSpinner");
  btn.disabled = loading;
  text.textContent = loading ? "Analyzing…" : "Analyze";
  icon.classList.toggle("hidden", loading);
  spinner.classList.toggle("hidden", !loading);
}

/* ══════════════════════════════════════════════════════════════════════════
   Autocomplete / Ticker Search
══════════════════════════════════════════════════════════════════════════ */

const companyInput = document.getElementById("companyInput");
const dropdown     = document.getElementById("autocomplete-dropdown");

companyInput.addEventListener("input", () => {
  clearTimeout(autocompleteTimeout);
  const q = companyInput.value.trim();
  if (q.length < 2) { dropdown.classList.add("hidden"); return; }
  // Debounce – wait 400ms after user stops typing
  autocompleteTimeout = setTimeout(() => fetchAutoComplete(q), 400);
});

companyInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { dropdown.classList.add("hidden"); runAnalysis(); }
});

// Close dropdown when clicking outside
document.addEventListener("click", (e) => {
  if (!dropdown.contains(e.target) && e.target !== companyInput) {
    dropdown.classList.add("hidden");
  }
});

async function fetchAutoComplete(query) {
  try {
    const res  = await fetch(`/api/ticker-search/?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    renderDropdown(data.results || []);
  } catch { dropdown.classList.add("hidden"); }
}

function renderDropdown(results) {
  dropdown.innerHTML = "";
  if (!results.length) { dropdown.classList.add("hidden"); return; }
  results.forEach(r => {
    const item = document.createElement("div");
    item.className = "autocomplete-item";
    item.innerHTML = `
      <div>
        <span class="autocomplete-ticker">${r.ticker}</span>
        <span class="autocomplete-name"> – ${r.name}</span>
      </div>
      <span class="autocomplete-name">${r.exchange}</span>`;
    item.addEventListener("click", () => {
      companyInput.value = r.ticker;
      dropdown.classList.add("hidden");
      runAnalysis();
    });
    dropdown.appendChild(item);
  });
  dropdown.classList.remove("hidden");
}

/* ══════════════════════════════════════════════════════════════════════════
   Quick Search from ticker chips
══════════════════════════════════════════════════════════════════════════ */
function quickSearch(ticker) {
  companyInput.value = ticker;
  runAnalysis();
}

/* ══════════════════════════════════════════════════════════════════════════
   Main Analysis Flow
══════════════════════════════════════════════════════════════════════════ */

async function runAnalysis() {
  const input = companyInput.value.trim().toUpperCase();
  if (!input) { showError("Please enter a company name or ticker symbol."); return; }

  hideError();
  setLoading(true);
  document.getElementById("results").classList.add("hidden");

  try {
    const res  = await fetch(`/api/analyze/?ticker=${encodeURIComponent(input)}`);
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "An unexpected error occurred. Please try again.");
      return;
    }

    renderDashboard(data);
    document.getElementById("results").classList.remove("hidden");
    // Smooth scroll to results
    document.getElementById("results").scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    showError("Network error: Could not reach the server. Please check your connection.");
    console.error(err);
  } finally {
    setLoading(false);
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   Dashboard Renderers
══════════════════════════════════════════════════════════════════════════ */

function renderDashboard(data) {
  const { profile, financials, news, analysis, scoring } = data;
  renderProfile(profile);
  renderMetrics(financials);
  renderScoring(scoring);
  renderSWOT(analysis.swot);
  renderRisks(analysis.risks);
  renderHealth(analysis.health);
  renderGrowth(analysis.growth);
  renderCompetitors(analysis.competitors, profile, financials);
  renderNews(news);
  renderCharts(financials, scoring, analysis.competitors);
}

/* ── Company Profile ──────────────────────────────────────────────────── */
function renderProfile(p) {
  const name = safe(p, "name", p.ticker || "Unknown");
  const initials = name.split(" ").slice(0,2).map(w => w[0]).join("").toUpperCase();

  document.getElementById("companyInitials").textContent   = initials;
  document.getElementById("companyName").textContent       = name;
  document.getElementById("companyTicker").textContent     = p.ticker + " · " + safe(p, "exchange");
  document.getElementById("companySector").textContent     = safe(p, "sector");
  document.getElementById("companyIndustry").textContent   = safe(p, "industry");
  document.getElementById("companyCEO").textContent        = safe(p, "ceo");
  document.getElementById("companyHQ").textContent         = [safe(p,"city",""), safe(p,"country","")].filter(Boolean).join(", ") || "N/A";
  document.getElementById("companyExchange").textContent   = safe(p, "exchange");
  document.getElementById("companyEmployees").textContent  = p.employees ? Number(p.employees).toLocaleString() : "N/A";
  document.getElementById("companyDescription").textContent = safe(p, "description", "No description available.");
}

/* ── Financial Metrics Grid ───────────────────────────────────────────── */
function renderMetrics(f) {
  const fmt = f.formatted || {};
  const metrics = [
    { label: "Revenue",           value: fmt.revenue           || formatNumber(f.revenue),          sub: "Annual" },
    { label: "Net Income",        value: fmt.net_income        || formatNumber(f.net_income),        sub: "Annual" },
    { label: "Market Cap",        value: fmt.market_cap        || formatNumber(f.market_cap),        sub: "Current" },
    { label: "EPS",               value: f.eps ? `$${f.eps.toFixed(2)}` : "N/A",                    sub: "Trailing 12m" },
    { label: "P/E Ratio",         value: f.pe_ratio ? f.pe_ratio.toFixed(1) + "x" : "N/A",         sub: "Trailing" },
    { label: "Profit Margin",     value: f.profit_margin != null ? f.profit_margin.toFixed(1) + "%" : "N/A", sub: "Net" },
    { label: "Revenue Growth",    value: f.revenue_growth != null ? f.revenue_growth.toFixed(1) + "%" : "N/A", sub: "YoY" },
    { label: "Total Debt",        value: fmt.total_debt        || formatNumber(f.total_debt),        sub: "" },
    { label: "Total Cash",        value: fmt.total_cash        || formatNumber(f.total_cash),        sub: "" },
    { label: "Free Cash Flow",    value: fmt.free_cash_flow    || formatNumber(f.free_cash_flow),    sub: "Annual" },
    { label: "Return on Equity",  value: f.return_on_equity != null ? f.return_on_equity.toFixed(1) + "%" : "N/A", sub: "" },
    { label: "Debt / Equity",     value: f.debt_to_equity != null ? f.debt_to_equity.toFixed(2) + "x" : "N/A", sub: "" },
  ];
  const grid = document.getElementById("metricsGrid");
  grid.innerHTML = metrics.map(m => `
    <div class="metric-card">
      <div class="metric-label">${m.label}</div>
      <div class="metric-value">${m.value}</div>
      ${m.sub ? `<div class="metric-sub">${m.sub}</div>` : ""}
    </div>`).join("");
}

/* ── Investment Scoring ───────────────────────────────────────────────── */
function renderScoring(s) {
  const circle = document.getElementById("scoreCircle");
  const badge  = document.getElementById("recommendationBadge");
  const scoreN = document.getElementById("scoreNumber");

  // Animate the score number counting up
  let current = 0;
  const interval = setInterval(() => {
    current = Math.min(current + 1, s.score);
    scoreN.textContent = current;
    if (current >= s.score) clearInterval(interval);
  }, 80);

  // Apply colour class based on recommendation
  circle.className = "score-circle " + s.decision_color;
  badge.textContent = s.recommendation;
  badge.className   = "recommendation-badge badge-" + s.recommendation;
  document.getElementById("scoreSummary").textContent = s.summary;

  // Rules breakdown
  const container = document.getElementById("rulesBreakdown");
  container.innerHTML = s.rules.map(r => `
    <div class="rule-row">
      <div>
        <div class="rule-name">${r.rule}</div>
        <div class="rule-criterion">Criterion: ${r.criterion} · Actual: <strong>${r.actual_value}</strong></div>
        <div class="rule-explanation">${r.explanation}</div>
      </div>
      <div class="rule-points">
        <div class="rule-pts-val" style="color:${r.points===2?"var(--green)":r.points===1?"var(--amber)":"var(--red)"}">${r.points}</div>
        <div class="rule-pts-max">/ ${r.max_points} pts</div>
        <span class="rule-verdict verdict-${r.verdict}">${r.verdict}</span>
      </div>
    </div>`).join("");
}

/* ── SWOT ─────────────────────────────────────────────────────────────── */
function renderSWOT(swot) {
  const renderList = (id, items) => {
    document.getElementById(id).innerHTML = items.map(i => `<li>${i}</li>`).join("");
  };
  renderList("swotStrengths",     swot.strengths);
  renderList("swotWeaknesses",    swot.weaknesses);
  renderList("swotOpportunities", swot.opportunities);
  renderList("swotThreats",       swot.threats);
}

/* ── Risks ────────────────────────────────────────────────────────────── */
function renderRisks(risks) {
  document.getElementById("riskList").innerHTML = risks.map(r => `
    <div class="risk-row">
      <div class="risk-level-badge risk-${r.level}">${r.level}</div>
      <div>
        <div class="risk-category">${r.category}</div>
        <div class="risk-description">${r.description}</div>
      </div>
    </div>`).join("");
}

/* ── Financial Health ─────────────────────────────────────────────────── */
function renderHealth(h) {
  document.getElementById("healthBadge").textContent = h.label;
  document.getElementById("healthBadge").className   = "health-badge health-" + h.label;
  document.getElementById("healthSummary").textContent = h.summary;
  document.getElementById("healthBullets").innerHTML  = h.bullets.map(b => `<li>${b}</li>`).join("");
}

/* ── Growth ───────────────────────────────────────────────────────────── */
function renderGrowth(g) {
  document.getElementById("growthBadge").textContent      = g.label;
  document.getElementById("growthNarrative").textContent  = g.narrative;
  document.getElementById("growthRevenue").textContent    = g.revenue_growth != null ? g.revenue_growth.toFixed(1) + "%" : "N/A";
  document.getElementById("growthEarnings").textContent   = g.earnings_growth != null ? g.earnings_growth.toFixed(1) + "%" : "N/A";
  document.getElementById("growthCAGR").textContent       = g.cagr != null ? g.cagr.toFixed(1) + "%" : "N/A";
}

/* ── Competitor Analysis ──────────────────────────────────────────────── */
function renderCompetitors(ca, profile, financials) {
  document.getElementById("competitorPosition").textContent  = ca.market_position || "Unknown";
  document.getElementById("competitorCommentary").textContent = ca.commentary || "";

  const tbody   = document.getElementById("competitorTableBody");
  const subject = ca.subject || {};
  const peers   = ca.peers   || [];

  // Insert subject row + peer rows
  const allRows = [{ ...subject, isSubject: true }, ...peers];
  tbody.innerHTML = allRows.map(r => `
    <tr class="${r.isSubject ? "subject-row" : ""}">
      <td>${r.name || "N/A"}</td>
      <td>${r.ticker || "N/A"}</td>
      <td>${formatNumber(r.market_cap)}</td>
      <td>${r.pe_ratio ? r.pe_ratio.toFixed(1) + "x" : "N/A"}</td>
    </tr>`).join("");
}

/* ── News ─────────────────────────────────────────────────────────────── */
function renderNews(articles) {
  const grid = document.getElementById("newsGrid");
  if (!articles || !articles.length) {
    grid.innerHTML = `<p style="color:var(--text-muted);font-size:0.88rem;">No recent news available.</p>`;
    return;
  }
  grid.innerHTML = articles.map(a => `
    <div class="news-card">
      <div class="news-header">
        <div class="news-sentiment-dot dot-${a.sentiment}"></div>
        <div class="news-title">
          <a href="${a.url}" target="_blank" rel="noopener">${a.title || "Untitled"}</a>
        </div>
      </div>
      <div class="news-footer">
        <span class="news-source">${a.source || "Unknown"}</span>
        <span class="news-sentiment-label sentiment-${a.sentiment}">${a.sentiment}</span>
      </div>
    </div>`).join("");
}

/* ══════════════════════════════════════════════════════════════════════════
   Chart.js Renderers
══════════════════════════════════════════════════════════════════════════ */

const CHART_DEFAULTS = {
  color:      "#94a3b8",
  gridColor:  "rgba(255,255,255,0.05)",
  fontFamily: "'Inter', sans-serif",
};

function destroyChart(ref) { if (ref) ref.destroy(); }

/**
 * Open Chart Modal
 */
function openChartModal(sourceChart, titleText) {
  const modal = document.getElementById("chartModal");
  document.getElementById("chartModalTitle").textContent = titleText;
  
  if (modalChart) { modalChart.destroy(); }
  const ctx = document.getElementById("modalCanvas").getContext("2d");
  
  // Clone the raw config data to avoid circular references
  // Rather than deep cloning, we just make a shallow copy and override specific options
  const newOptions = Object.assign({}, sourceChart.config.options);
  newOptions.maintainAspectRatio = false;
  
  // Increase font sizes safely if they exist
  if (newOptions.plugins?.legend?.labels) {
    newOptions.plugins.legend.labels = { ...newOptions.plugins.legend.labels, font: { family: CHART_DEFAULTS.fontFamily, size: 14 } };
  }
  if (newOptions.scales) {
    newOptions.scales = { ...newOptions.scales };
    for (let axis in newOptions.scales) {
      if (newOptions.scales[axis].ticks) {
        newOptions.scales[axis].ticks = { ...newOptions.scales[axis].ticks, font: { size: 13, family: CHART_DEFAULTS.fontFamily } };
      }
    }
  }

  modalChart = new Chart(ctx, {
    type: sourceChart.config.type,
    data: sourceChart.config.data, // Reuse data
    options: newOptions
  });
  
  modal.classList.remove("hidden");
}

document.getElementById("modalCloseBtn")?.addEventListener("click", () => {
  document.getElementById("chartModal").classList.add("hidden");
});

/**
 * Chart 1: Revenue History – Beautiful Smooth Area Chart
 */
function renderRevenueChart(financials) {
  destroyChart(revenueChart);
  const ctx = document.getElementById("revenueChart").getContext("2d");
  const history = financials.revenue_history || [];
  if (!history.length) { ctx.canvas.parentElement.innerHTML += '<p style="color:var(--text-muted);font-size:0.82rem;margin-top:1rem;">No historical revenue data available.</p>'; return; }

  const labels = history.map(h => h.year);
  const values = history.map(h => h.revenue / 1e9); // display in $B

  // Create a stunning vertical gradient for the line fill (Simply Wall St style)
  let gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, 'rgba(99, 102, 241, 0.45)');
  gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

  revenueChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Revenue ($B)",
        data:  values,
        fill: true,
        backgroundColor: gradient,
        borderColor:     "#8b5cf6",
        borderWidth:     3,
        pointBackgroundColor: "#0f1224",
        pointBorderColor: "#8b5cf6",
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 7,
        tension: 0.4 // Makes the line smooth/curved
      }]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: CHART_DEFAULTS.color, font: { family: CHART_DEFAULTS.fontFamily } } },
        tooltip: {
          backgroundColor: 'rgba(10, 11, 20, 0.9)',
          titleFont: { size: 14, family: CHART_DEFAULTS.fontFamily },
          bodyFont: { size: 14, family: CHART_DEFAULTS.fontFamily },
          borderColor: 'rgba(99,102,241,0.3)',
          borderWidth: 1,
          padding: 10,
          callbacks: { label: ctx => `$${ctx.parsed.y.toFixed(2)}B` }
        }
      },
      scales: {
        x: { ticks: { color: CHART_DEFAULTS.color }, grid: { display: false } },
        y: {
          ticks: { color: CHART_DEFAULTS.color, callback: v => `$${v.toFixed(0)}B` },
          grid:  { color: CHART_DEFAULTS.gridColor, borderDash: [5, 5] },
          beginAtZero: true
        }
      }
    }
  });

  ctx.canvas.parentElement.onclick = () => openChartModal(revenueChart, "Revenue History ($B)");
}

/**
 * Chart 2: Score breakdown polar/doughnut – one segment per rule.
 */
function renderScoreChart(scoring) {
  destroyChart(scoreChart);
  const ctx = document.getElementById("scoreChart").getContext("2d");
  const rules = scoring.rules || [];

  const labels = rules.map(r => r.rule);
  const values = rules.map(r => r.points);
  const colors = values.map(v => v === 2 ? "rgba(16,185,129,0.8)" : v === 1 ? "rgba(245,158,11,0.8)" : "rgba(239,68,68,0.8)");

  scoreChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [{
        label: "Score",
        data:            values,
        backgroundColor: "rgba(99,102,241,0.25)",
        borderColor:     "rgb(99,102,241)",
        pointBackgroundColor: "rgb(99,102,241)",
        borderWidth:     2,
      }]
    },
    options: {
      responsive: true,
      scales: {
        r: {
          angleLines: { color: "rgba(255,255,255,0.1)" },
          grid: { color: "rgba(255,255,255,0.05)", circular: true },
          pointLabels: { color: CHART_DEFAULTS.color, font: { family: CHART_DEFAULTS.fontFamily, size: 11, weight: 'bold' } },
          ticks: { display: false, max: 2, min: 0, stepSize: 1 }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(10, 11, 20, 0.9)',
          borderColor: 'rgba(99,102,241,0.3)',
          borderWidth: 1,
          callbacks: { label: ctx => `${ctx.label}: ${ctx.raw} pts` }
        }
      }
    }
  });

  ctx.canvas.parentElement.onclick = () => openChartModal(scoreChart, "Financial Snowflake");
}

/**
 * Chart 3: Market cap comparison – horizontal bar chart.
 */
function renderCompetitorChart(ca, profile, financials) {
  destroyChart(competitorChart);
  const ctx = document.getElementById("competitorChart").getContext("2d");

  const subject = { name: profile.name || profile.ticker, market_cap: financials.market_cap };
  const peers   = (ca.peers || []).slice(0, 4);
  const all     = [subject, ...peers];

  const labels = all.map(c => c.name || c.ticker || "");
  const values = all.map(c => (c.market_cap || 0) / 1e9);
  const bgColors = all.map((_, i) =>
    i === 0 ? "rgba(99,102,241,0.85)" : "rgba(148,163,184,0.4)"
  );

  competitorChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Market Cap ($B)",
        data:  values,
        backgroundColor: bgColors,
        borderRadius:    6,
      }]
    },
    options: {
      indexAxis: "y",  // horizontal bars
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(10, 11, 20, 0.9)',
          borderColor: 'rgba(99,102,241,0.3)',
          borderWidth: 1,
          callbacks: { label: ctx => `$${ctx.parsed.x.toFixed(2)}B` } 
        }
      },
      scales: {
        x: {
          ticks: { color: CHART_DEFAULTS.color, callback: v => `$${v}B` },
          grid:  { color: CHART_DEFAULTS.gridColor, borderDash: [5, 5] },
          beginAtZero: true
        },
        y: { 
          ticks: { color: CHART_DEFAULTS.color, font: { weight: 'bold' } }, 
          grid: { display: false } 
        }
      }
    }
  });

  ctx.canvas.parentElement.onclick = () => openChartModal(competitorChart, "Market Cap vs Peers");
}

function renderCharts(financials, scoring, competitorAnalysis) {
  renderRevenueChart(financials);
  renderScoreChart(scoring);
  renderCompetitorChart(competitorAnalysis, {}, financials);
}
