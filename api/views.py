"""
api/views.py
============
Django REST Framework views for the Investment Research API.

Endpoints
---------
GET /api/analyze/?ticker=TSLA
    - Resolves ticker, fetches all data, runs all analyses, returns JSON.

GET /api/ticker-search/?q=Tesla
    - Attempts a best-effort ticker resolution from a free-text company name.

Error Handling
--------------
All errors are returned as structured JSON with an "error" key and an
appropriate HTTP status code. The frontend reads this key to display
user-friendly error messages.
"""

import logging
import requests

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# ── Internal modules ──────────────────────────────────────────────────────────
from services.data_fetcher import DataFetcherService
from analysis.analyzer import (
    SWOTAnalyzer,
    RiskAnalyzer,
    FinancialHealthAnalyzer,
    GrowthAnalyzer,
    CompetitorAnalyzer,
)
from analysis.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ══════════════════════════════════════════════════════════════════════════════

def _format_number(value: float | None) -> str:
    """
    Human-readable formatting for large financial numbers.
    e.g. 1_500_000_000 → "$1.50B", 950_000_000 → "$950.00M"
    """
    if value is None or value == 0:
        return "N/A"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1e12:
        return f"{sign}${abs_val / 1e12:.2f}T"
    if abs_val >= 1e9:
        return f"{sign}${abs_val / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"{sign}${abs_val / 1e6:.2f}M"
    return f"{sign}${abs_val:,.0f}"


# ══════════════════════════════════════════════════════════════════════════════
# /api/analyze/
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeCompanyView(APIView):
    """
    Main analysis endpoint.

    Query params
    ------------
    ticker : str  — required, Yahoo Finance ticker symbol (e.g. TSLA)

    Returns
    -------
    200 OK with full analysis JSON on success.
    400 Bad Request if ticker is missing or unresolvable.
    503 Service Unavailable if upstream data fetch fails completely.
    """

    def get(self, request):
        ticker = request.query_params.get("ticker", "").strip().upper()
        if not ticker:
            return Response(
                {"error": "The 'ticker' query parameter is required. Example: /api/analyze/?ticker=TSLA"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # ── Step 1: Fetch all raw data ─────────────────────────────────
            fetcher     = DataFetcherService(ticker)
            profile     = fetcher.get_company_profile()   # may raise ValueError
            financials  = fetcher.get_financial_metrics()
            news        = fetcher.get_news()
            competitors = fetcher.get_competitors()

            # ── Step 2: Run all analyses ───────────────────────────────────
            swot          = SWOTAnalyzer(financials, news, profile).generate()
            risks         = RiskAnalyzer(financials, news, profile).generate()
            health        = FinancialHealthAnalyzer(financials, profile).generate()
            growth        = GrowthAnalyzer(financials).generate()
            competitor_a  = CompetitorAnalyzer(profile, financials, competitors).generate()
            scoring       = ScoringEngine(financials, news).calculate()

            # ── Step 3: Add human-readable formatted values for the UI ─────
            formatted = {
                "revenue":            _format_number(financials.get("revenue")),
                "net_income":         _format_number(financials.get("net_income")),
                "market_cap":         _format_number(financials.get("market_cap")),
                "total_debt":         _format_number(financials.get("total_debt")),
                "total_cash":         _format_number(financials.get("total_cash")),
                "operating_cash_flow":_format_number(financials.get("operating_cash_flow")),
                "free_cash_flow":     _format_number(financials.get("free_cash_flow")),
                "ebitda":             _format_number(financials.get("ebitda")),
            }

            # ── Step 4: Compose the response payload ───────────────────────
            payload = {
                "profile":      profile,
                "financials":   {**financials, "formatted": formatted},
                "news":         news,
                "competitors":  competitors,
                "analysis": {
                    "swot":        swot,
                    "risks":       risks,
                    "health":      health,
                    "growth":      growth,
                    "competitors": competitor_a,
                },
                "scoring": scoring,
            }

            logger.info("Analysis complete for ticker=%s score=%d recommendation=%s",
                        ticker, scoring["score"], scoring["recommendation"])
            return Response(payload, status=status.HTTP_200_OK)

        except ValueError as exc:
            # Ticker not found or data is completely absent
            logger.warning("Invalid ticker '%s': %s", ticker, exc)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching data for ticker '%s'", ticker)
            return Response(
                {"error": "The data request timed out. Please try again in a moment."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except requests.exceptions.ConnectionError:
            logger.error("Network error fetching data for ticker '%s'", ticker)
            return Response(
                {"error": "Network error: unable to reach financial data provider. Check your connection."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            # Catch-all: log the full traceback but return a clean user message
            logger.exception("Unexpected error analysing ticker='%s'", ticker)
            return Response(
                {"error": f"An unexpected error occurred: {str(exc)}. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ══════════════════════════════════════════════════════════════════════════════
# /api/ticker-search/
# ══════════════════════════════════════════════════════════════════════════════

class TickerSearchView(APIView):
    """
    Resolve a company name to a ticker symbol using Yahoo Finance search API.

    Query params
    ------------
    q : str — free-text company name (e.g. "Tesla", "Infosys", "Reliance")

    Returns
    -------
    200 OK with a list of candidate tickers regardless of whether any are found.
    """

    YF_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"results": []}, status=status.HTTP_200_OK)

        try:
            headers = {"User-Agent": "InvestmentResearchApp/1.0"}
            params = {"q": query, "quotesCount": 8, "newsCount": 0, "enableFuzzyQuery": True}
            resp = requests.get(
                self.YF_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            quotes = data.get("quotes", [])

            results = [
                {
                    "ticker":   q.get("symbol", ""),
                    "name":     q.get("longname") or q.get("shortname", ""),
                    "exchange": q.get("exchange", ""),
                    "type":     q.get("quoteType", ""),
                }
                for q in quotes
                if q.get("quoteType") in ("EQUITY", "ETF")
            ]
            return Response({"results": results[:6]}, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.warning("Ticker search failed for query='%s': %s", query, exc)
            return Response(
                {"results": [], "warning": "Search unavailable; enter the ticker directly."},
                status=status.HTTP_200_OK,
            )
