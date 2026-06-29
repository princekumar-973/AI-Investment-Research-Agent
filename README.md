# InvestIQ – Professional Investment Research Application

> A rule-based, AI-free investment analysis platform built with Django and Python.

---

## Overview

InvestIQ is a full-stack web application that lets you research any publicly listed company by entering its name or ticker symbol. It fetches real financial data, runs deterministic rule-based analysis, and outputs a clear **INVEST / HOLD / PASS** recommendation with detailed reasoning — no AI, no LLM, no black boxes.

---

## Features

| Feature | Details |
|---|---|
| 🔍 Smart Search | Autocomplete ticker resolution via Yahoo Finance API |
| 📊 Company Profile | Name, CEO, HQ, sector, industry, description, exchange |
| 💰 Financial Metrics | Revenue, Net Income, Market Cap, EPS, P/E, Profit Margin, Debt, Cash Flow |
| 📈 Revenue History Chart | Multi-year bar chart using real income statement data |
| 🏅 Investment Score | Rule-based score out of 10 with per-rule explanations |
| 🟢 INVEST / 🟡 HOLD / 🔴 PASS | Clear decision with a one-sentence summary |
| 🔀 SWOT Analysis | Strengths, Weaknesses, Opportunities, Threats |
| ⚠️ Risk Analysis | 6 risk dimensions: Leverage, Liquidity, Profitability, Valuation, Sentiment, Cash Flow |
| 💪 Financial Health | Excellent / Good / Fair / Poor label with explanation |
| 🚀 Growth Analysis | YoY Revenue/Earnings growth + CAGR calculation |
| 🏆 Competitor Analysis | Peer comparison with market-cap ranking |
| 📰 Latest News | Headlines with rule-based positive/neutral/negative sentiment |
| 📊 Chart.js Visualizations | 3 interactive charts: Revenue, Score Breakdown, Market Cap Comparison |
| 🔑 Env-variable API Keys | All secrets in `.env`, never in source code |
| ⚡ REST API | Full DRF API at `/api/analyze/` and `/api/ticker-search/` |

---

## Screenshots

_(Run the server and use the dashboard at http://localhost:8000)_

---

## Installation

### Prerequisites

- Python 3.10+
- pip

### Steps

```bash
# 1. Clone / download the project
cd investment_agent

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
# Edit .env and add any optional API keys (see below)

# 5. Run database migrations
python manage.py migrate

# 6. Start the development server
python manage.py runserver

# 7. Open the dashboard
# http://localhost:8000
```

---

## Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key (any long random string) |
| `DEBUG` | No | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | No | Comma-separated hosts, e.g. `localhost,127.0.0.1` |
| `NEWS_API_KEY` | No | Free key from [newsapi.org](https://newsapi.org). Falls back to yfinance news if blank. |
| `ALPHA_VANTAGE_API_KEY` | No | From [alphavantage.co](https://www.alphavantage.co). For future supplementary data use. |

---

## Folder Structure

```
investment_agent/
│
├── manage.py                   # Django management entry point
├── wsgi.py                     # WSGI entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
├── .env.example                # Template for .env
│
├── backend/                    # Django project config package
│   ├── __init__.py
│   ├── settings.py             # All settings loaded from .env
│   └── urls.py                 # Root URL router
│
├── api/                        # REST API + frontend views app
│   ├── __init__.py
│   ├── views.py                # DRF API views (AnalyzeCompany, TickerSearch)
│   ├── urls.py                 # /api/ URL routes
│   ├── frontend_views.py       # Dashboard TemplateView
│   └── frontend_urls.py        # / URL route
│
├── services/                   # External data retrieval
│   ├── __init__.py
│   └── data_fetcher.py         # DataFetcherService (yfinance + NewsAPI)
│
├── analysis/                   # All rule-based analysis engines
│   ├── __init__.py
│   ├── analyzer.py             # SWOT, Risk, Health, Growth, Competitor analyzers
│   └── scoring_engine.py       # Investment scoring (5 rules × 2 pts = 10)
│
├── utils/                      # Shared utilities
│   └── __init__.py             # format_currency, safe_pct, clamp helpers
│
├── templates/
│   └── dashboard.html          # Main SPA-style dashboard
│
└── static/
    ├── css/styles.css          # Premium dark-theme stylesheet
    └── js/main.js              # Dashboard JS: API calls, Chart.js, DOM rendering
```

---

## Architecture

```
Browser
  │
  ├── GET /                    → DashboardView → dashboard.html (template)
  └── GET /api/analyze/?ticker=TSLA
        │
        └── AnalyzeCompanyView
              │
              ├── DataFetcherService (services/data_fetcher.py)
              │     ├── yfinance → profile, financials, news, revenue history
              │     └── NewsAPI  → headlines (optional)
              │
              ├── SWOTAnalyzer         (analysis/analyzer.py)
              ├── RiskAnalyzer          (analysis/analyzer.py)
              ├── FinancialHealthAnalyzer (analysis/analyzer.py)
              ├── GrowthAnalyzer        (analysis/analyzer.py)
              ├── CompetitorAnalyzer    (analysis/analyzer.py)
              └── ScoringEngine         (analysis/scoring_engine.py)
                    │
                    └── JSON Response → JavaScript renders charts + DOM
```

---

## APIs Used

| API | Usage | Free Tier |
|---|---|---|
| **Yahoo Finance** (via `yfinance`) | All financial data: profile, financials, news | Unlimited (unofficial) |
| **Yahoo Finance Search API** | Ticker autocomplete resolution | Unlimited (unofficial) |
| **NewsAPI** | Fresh news headlines (optional) | 100 req/day |

---

## Investment Decision Rules

The scoring engine evaluates 5 rules, each worth a maximum of 2 points:

| # | Rule | Threshold | Points |
|---|---|---|---|
| 1 | Revenue Growth YoY | > 10% = 2pts, 5–10% = 1pt, < 5% = 0pt | 0–2 |
| 2 | Profit Margin | > 15% = 2pts, 5–15% = 1pt, < 5% = 0pt | 0–2 |
| 3 | Low Debt | D/E < 1.0x = 2pts, 1–2x = 1pt, > 2x = 0pt | 0–2 |
| 4 | Positive News | ≥ 50% positive = 2pts, 25–49% = 1pt, < 25% = 0pt | 0–2 |
| 5 | Strong Cash Flow | FCF > 0 = 2pts, OCF > 0 = 1pt, both ≤ 0 = 0pt | 0–2 |

**Total: 10 points**

| Score | Decision |
|---|---|
| ≥ 8 | 🟢 **INVEST** |
| 5–7 | 🟡 **HOLD** |
|  < 5 | 🔴 **PASS** |

---

## Example Output (TSLA – hypothetical)

```json
{
  "scoring": {
    "score": 6,
    "max_score": 10,
    "recommendation": "HOLD",
    "decision_color": "amber",
    "summary": "A score of 6/10 indicates solid but not outstanding fundamentals.",
    "rules": [
      { "rule": "Revenue Growth", "points": 2,  "verdict": "PASS",    "actual_value": "18.8%" },
      { "rule": "Profit Margin",  "points": 1,  "verdict": "PARTIAL", "actual_value": "9.2%"  },
      { "rule": "Low Debt",       "points": 2,  "verdict": "PASS",    "actual_value": "0.8x"  },
      { "rule": "Positive News",  "points": 1,  "verdict": "PARTIAL", "actual_value": "38% positive" },
      { "rule": "Strong Cash Flow","points": 0, "verdict": "FAIL",    "actual_value": "-$1.50B FCF" }
    ]
  }
}
```

---

## Trade-offs

| Decision | Rationale |
|---|---|
| `yfinance` over paid APIs | Free, no registration required, rich data; unofficial so may occasionally be rate-limited |
| Rule-based scoring over ML | Completely transparent, auditable, and explainable – suitable for a research tool |
| SQLite database | Sufficient for a stateless research tool; upgrade to PostgreSQL for production |
| No user authentication | Research tool focus; easily added via Django's built-in auth |
| Partial credit (+1) rules | Avoids binary cliff-edges in scoring, produces more nuanced results |

---

## Future Improvements

- [ ] **PDF Report Export** – Download a full analysis as a branded PDF
- [ ] **Comparison Mode** – Analyse two tickers side by side
- [ ] **Portfolio Tracker** – Save multiple analyses and track score changes over time
- [ ] **Sector Benchmarking** – Compare metrics against sector median
- [ ] **Alerts** – Email/webhook notification when a tracked company's score changes
- [ ] **Historical Score Chart** – Track score over time as financials update
- [ ] **PostgreSQL + Redis** – Production-grade data persistence and caching
- [ ] **Docker** – Containerise for one-command deployment
- [ ] **Indian Stock Support** – NSE/BSE integration for Reliance, Infosys, etc.

---

## Deployment

### Development (local)
```bash
python manage.py runserver
```

### Production Checklist
1. Set `DEBUG=False` in `.env`
2. Set a strong `SECRET_KEY`
3. Set `ALLOWED_HOSTS` to your domain
4. Run `python manage.py collectstatic`
5. Use Gunicorn + Nginx or a PaaS like Railway/Render

```bash
pip install gunicorn
gunicorn wsgi:application --bind 0.0.0.0:8000
```

---

## License

MIT – free to use, modify, and distribute.
