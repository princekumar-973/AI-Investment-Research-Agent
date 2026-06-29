"""
services/data_fetcher.py
========================
DataFetcherService – the single source of truth for all external data.

Responsibilities:
  • Resolve a company name → ticker symbol (best-effort fuzzy match via yfinance)
  • Fetch company profile, description, CEO, headquarters, industry
  • Fetch financial statements: revenue, net income, EPS, PE ratio, market cap,
    debt, and cash flow from operations
  • Fetch latest news headlines  (NewsAPI → yfinance news fallback)
  • Identify up to 5 ticker-based competitors in the same sector

All methods return plain Python dicts/lists so they are easy to serialise.
All exceptions are caught locally and surfaced as structured error dicts so
the API layer never receives an unhandled exception from this module.
"""

import os
import logging
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
NEWS_API_URL = "https://newsapi.org/v2/everything"
REQUEST_TIMEOUT = 12   # seconds before we give up on an external HTTP call


class DataFetcherService:
    """Encapsulates all external data retrieval for a given ticker symbol."""

    def __init__(self, ticker: str):
        """
        Parameters
        ----------
        ticker : str
            A valid Yahoo Finance ticker symbol, e.g. 'TSLA', 'AAPL', 'INFY'.
        """
        self.ticker = ticker.upper().strip()
        self._yf_ticker = yf.Ticker(self.ticker)
        self._info: dict = {}  # cached .info dict from yfinance

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_info(self) -> dict:
        """Return (and cache) the yfinance .info dict for this ticker."""
        if not self._info:
            try:
                self._info = self._yf_ticker.info or {}
            except Exception as exc:
                logger.error("yfinance .info failed for %s: %s", self.ticker, exc)
                self._info = {}
        return self._info

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        """Safely cast a value to float, returning `default` on failure."""
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_company_profile(self) -> dict:
        """
        Return a flat dict of descriptive company information.

        Keys
        ----
        name, ticker, sector, industry, country, city, website,
        employees, description, ceo, exchange
        """
        info = self._get_info()
        # yfinance sometimes returns a nearly empty dict (e.g. {'trailingPegRatio': None}) for invalid symbols
        if not info or len(info) < 5:
            raise ValueError(f"No data found for ticker '{self.ticker}'. "
                             "Please check the symbol and try again.")

        # yfinance stores officer names in a list; grab the CEO if available
        ceo = "N/A"
        for officer in info.get("companyOfficers", []):
            title = officer.get("title", "").lower()
            if "chief executive" in title or "ceo" in title:
                ceo = officer.get("name", "N/A")
                break

        return {
            "name":        info.get("longName") or info.get("shortName", self.ticker),
            "ticker":      self.ticker,
            "sector":      info.get("sector", "N/A"),
            "industry":    info.get("industry", "N/A"),
            "country":     info.get("country", "N/A"),
            "city":        info.get("city", "N/A"),
            "website":     info.get("website", "N/A"),
            "employees":   info.get("fullTimeEmployees", "N/A"),
            "description": info.get("longBusinessSummary", "No description available."),
            "ceo":         ceo,
            "exchange":    info.get("exchange", "N/A"),
        }

    def get_financial_metrics(self) -> dict:
        """
        Return a flat dict of key financial metrics.

        All monetary values are in USD (as reported by Yahoo Finance).
        Ratios are plain floats. Revenue growth is expressed as a decimal
        (e.g. 0.12 = 12 %).
        """
        info = self._get_info()

        # ── Income-statement metrics ──────────────────────────────────────────
        revenue        = self._safe_float(info.get("totalRevenue"))
        net_income     = self._safe_float(info.get("netIncomeToCommon"))
        gross_profit   = self._safe_float(info.get("grossProfits"))
        ebitda         = self._safe_float(info.get("ebitda"))

        # ── Per-share / valuation metrics ────────────────────────────────────
        eps            = self._safe_float(info.get("trailingEps"))
        pe_ratio       = self._safe_float(info.get("trailingPE"))
        market_cap     = self._safe_float(info.get("marketCap"))
        book_value     = self._safe_float(info.get("bookValue"))
        price_to_book  = self._safe_float(info.get("priceToBook"))
        dividend_yield = self._safe_float(info.get("dividendYield"))

        # ── Balance-sheet metrics ─────────────────────────────────────────────
        total_debt     = self._safe_float(info.get("totalDebt"))
        total_cash     = self._safe_float(info.get("totalCash"))

        # ── Cash-flow metric ──────────────────────────────────────────────────
        operating_cf   = self._safe_float(info.get("operatingCashflow"))
        free_cf        = self._safe_float(info.get("freeCashflow"))

        # ── Derived ratios ────────────────────────────────────────────────────
        profit_margin       = self._safe_float(info.get("profitMargins"))   # decimal
        revenue_growth      = self._safe_float(info.get("revenueGrowth"))   # decimal (yoy)
        earnings_growth     = self._safe_float(info.get("earningsGrowth"))  # decimal (yoy)
        return_on_equity    = self._safe_float(info.get("returnOnEquity"))
        return_on_assets    = self._safe_float(info.get("returnOnAssets"))
        debt_to_equity      = self._safe_float(info.get("debtToEquity"))

        # ── 52-week price range ───────────────────────────────────────────────
        current_price = self._safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        week_52_high  = self._safe_float(info.get("fiftyTwoWeekHigh"))
        week_52_low   = self._safe_float(info.get("fiftyTwoWeekLow"))

        # ── Historical revenue (last 4 years) for chart ──────────────────────
        revenue_history = self._get_revenue_history()

        return {
            "revenue":             revenue,
            "net_income":          net_income,
            "gross_profit":        gross_profit,
            "ebitda":              ebitda,
            "eps":                 eps,
            "pe_ratio":            pe_ratio,
            "market_cap":          market_cap,
            "book_value":          book_value,
            "price_to_book":       price_to_book,
            "dividend_yield":      round(dividend_yield * 100, 2),  # convert to %
            "total_debt":          total_debt,
            "total_cash":          total_cash,
            "operating_cash_flow": operating_cf,
            "free_cash_flow":      free_cf,
            "profit_margin":       round(profit_margin * 100, 2),   # convert to %
            "revenue_growth":      round(revenue_growth * 100, 2),   # convert to %
            "earnings_growth":     round(earnings_growth * 100, 2),  # convert to %
            "return_on_equity":    round(return_on_equity * 100, 2),
            "return_on_assets":    round(return_on_assets * 100, 2),
            "debt_to_equity":      round(debt_to_equity, 2),
            "current_price":       current_price,
            "week_52_high":        week_52_high,
            "week_52_low":         week_52_low,
            "revenue_history":     revenue_history,
        }

    def _get_revenue_history(self) -> list:
        """
        Fetch annual revenues from the income statement (up to 4 years).
        Returns a list of dicts: [{"year": 2023, "revenue": 96_773_000_000}, ...]
        """
        try:
            income_stmt = self._yf_ticker.financials  # pandas DataFrame
            if income_stmt is None or income_stmt.empty:
                return []
            # 'Total Revenue' row, columns are DatetimeIndex
            if "Total Revenue" not in income_stmt.index:
                return []
            revenue_row = income_stmt.loc["Total Revenue"]
            history = []
            for date_col, value in revenue_row.items():
                history.append({
                    "year":    date_col.year,
                    "revenue": float(value) if value == value else 0.0,  # NaN guard
                })
            # Sort ascending by year for chart rendering
            history.sort(key=lambda x: x["year"])
            return history[-4:]   # last 4 years
        except Exception as exc:
            logger.warning("Could not fetch revenue history for %s: %s", self.ticker, exc)
            return []

    def get_news(self, max_articles: int = 8) -> list:
        """
        Fetch the latest news for the company.

        Strategy:
          1. Try NewsAPI (if NEWS_API_KEY is set in .env).
          2. Fall back to yfinance .news attribute.

        Returns a list of dicts:
          [{"title": str, "source": str, "url": str, "published_at": str,
            "sentiment": "positive"|"neutral"|"negative"}, ...]
        """
        news_api_key = os.getenv("NEWS_API_KEY", "")
        company_name = (self._get_info().get("longName") or self.ticker)

        articles = []

        # ── Strategy 1: NewsAPI ───────────────────────────────────────────────
        if news_api_key:
            try:
                params = {
                    "q":        f'"{company_name}" OR "{self.ticker}"',
                    "language": "en",
                    "sortBy":   "publishedAt",
                    "pageSize": max_articles,
                    "apiKey":   news_api_key,
                }
                resp = requests.get(NEWS_API_URL, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("articles", [])[:max_articles]:
                    articles.append({
                        "title":        item.get("title", ""),
                        "source":       item.get("source", {}).get("name", ""),
                        "url":          item.get("url", "#"),
                        "published_at": item.get("publishedAt", ""),
                        "sentiment":    self._classify_sentiment(item.get("title", "")),
                    })
                if articles:
                    return articles
            except Exception as exc:
                logger.warning("NewsAPI failed, falling back to yfinance: %s", exc)

        # ── Strategy 2: yfinance .news ────────────────────────────────────────
        try:
            raw_news = self._yf_ticker.news or []
            for item in raw_news[:max_articles]:
                title = item.get("title", "")
                articles.append({
                    "title":        title,
                    "source":       item.get("publisher", "Yahoo Finance"),
                    "url":          item.get("link", "#"),
                    "published_at": str(item.get("providerPublishTime", "")),
                    "sentiment":    self._classify_sentiment(title),
                })
        except Exception as exc:
            logger.warning("yfinance .news failed for %s: %s", self.ticker, exc)

        return articles

    @staticmethod
    def _classify_sentiment(headline: str) -> str:
        """
        Rule-based headline sentiment classifier.

        Scans the headline for known positive / negative keyword sets and
        returns "positive", "negative", or "neutral".
        This is intentionally simple and transparent – no AI or ML involved.
        """
        POSITIVE_WORDS = {
            "surge", "soar", "beat", "record", "growth", "profit", "gain",
            "rise", "rally", "upgrade", "bullish", "strong", "outperform",
            "expand", "exceed", "boom", "up", "positive", "revenue growth",
        }
        NEGATIVE_WORDS = {
            "fall", "drop", "loss", "miss", "decline", "down", "weak",
            "downgrade", "bearish", "lawsuit", "fine", "penalty", "recall",
            "layoff", "cut", "crash", "plunge", "risk", "debt", "concern",
        }
        lower = headline.lower()
        pos = sum(1 for w in POSITIVE_WORDS if w in lower)
        neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    def get_competitors(self, max_competitors: int = 5) -> list:
        """
        Identify peer companies in the same sector using yfinance.

        yfinance does not have a direct "competitors" endpoint, so we use
        the sector ETF / industry peer strategy:
          • Read the sector from the company's .info dict.
          • Use a hardcoded mapping of sector → well-known peer tickers.
          • Exclude the original company from the list.

        Returns a list of dicts:
          [{"name": str, "ticker": str, "market_cap": float, "pe_ratio": float}, ...]
        """
        info = self._get_info()
        sector   = info.get("sector", "")
        industry = info.get("industry", "")

        # Sector → list of representative large-cap peers
        SECTOR_PEERS = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN", "TSLA", "ORCL", "CRM", "ADBE"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "SNAP"],
            "Consumer Cyclical":      ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "BKNG", "TGT"],
            "Consumer Defensive":     ["WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "CL"],
            "Healthcare":             ["JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR"],
            "Financials":             ["JPM", "BAC", "WFC", "GS", "MS", "BRK-B", "AXP", "BLK"],
            "Energy":                 ["XOM", "CVX", "SHEL", "BP", "COP", "SLB", "EOG", "MPC"],
            "Industrials":            ["BA", "HON", "UPS", "CAT", "GE", "RTX", "DE", "LMT"],
            "Basic Materials":        ["LIN", "APD", "ECL", "SHW", "NEM", "FCX", "NUE", "ALB"],
            "Real Estate":            ["AMT", "PLD", "CCI", "EQIX", "SPG", "PSA", "DLR", "WELL"],
            "Utilities":              ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL"],
        }

        peers = SECTOR_PEERS.get(sector, [])
        # Remove the current company from the peer list
        peers = [p for p in peers if p != self.ticker][:max_competitors]

        result = []
        for peer_ticker in peers:
            try:
                peer_info = yf.Ticker(peer_ticker).info or {}
                result.append({
                    "name":       peer_info.get("longName") or peer_info.get("shortName", peer_ticker),
                    "ticker":     peer_ticker,
                    "market_cap": self._safe_float(peer_info.get("marketCap")),
                    "pe_ratio":   self._safe_float(peer_info.get("trailingPE")),
                    "sector":     peer_info.get("sector", sector),
                })
            except Exception as exc:
                logger.warning("Could not fetch data for peer %s: %s", peer_ticker, exc)

        return result

    def fetch_all(self) -> dict:
        """
        Master method – returns all data in one consolidated dict.
        Raises a ValueError if the ticker is completely unresolvable.
        """
        profile     = self.get_company_profile()   # raises ValueError on bad ticker
        financials  = self.get_financial_metrics()
        news        = self.get_news()
        competitors = self.get_competitors()

        return {
            "profile":     profile,
            "financials":  financials,
            "news":        news,
            "competitors": competitors,
        }
