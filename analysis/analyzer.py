"""
analysis/analyzer.py
====================
Rule-based analytical engines for the Investment Research Application.

All analysis is produced through deterministic if/elif/else logic applied
to numeric financial metrics.  No ML, no AI, no LLM.

Classes
-------
SWOTAnalyzer      – generates Strengths, Weaknesses, Opportunities, Threats
RiskAnalyzer      – assesses financial, market, and operational risks
FinancialAnalyzer – produces a financial health narrative
GrowthAnalyzer    – evaluates historical and forward growth trajectory
CompetitorAnalyzer – ranks the company vs its peers
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# SWOT Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class SWOTAnalyzer:
    """
    Generates a SWOT analysis from financial metrics and news sentiment.

    Each quadrant returns a list of plain-English finding strings so the
    frontend can render them as bullet points.
    """

    def __init__(self, financials: dict, news: list, profile: dict):
        self.f = financials         # financial metrics dict
        self.news = news            # list of news article dicts
        self.p = profile            # company profile dict

    # ── private helpers ────────────────────────────────────────────────────────

    def _positive_news_ratio(self) -> float:
        """Fraction of news articles with positive sentiment."""
        if not self.news:
            return 0.0
        pos = sum(1 for n in self.news if n.get("sentiment") == "positive")
        return pos / len(self.news)

    # ── public quadrant generators ─────────────────────────────────────────────

    def get_strengths(self) -> list[str]:
        """Return a list of identified strengths."""
        strengths = []
        f = self.f

        if f.get("profit_margin", 0) > 15:
            strengths.append(
                f"Strong profitability: Profit margin of {f['profit_margin']:.1f}% "
                "significantly exceeds the 15% benchmark, indicating efficient cost management."
            )
        if f.get("revenue_growth", 0) > 10:
            strengths.append(
                f"Robust revenue growth of {f['revenue_growth']:.1f}% YoY signals "
                "growing market demand and successful commercial execution."
            )
        if f.get("operating_cash_flow", 0) > 0:
            strengths.append(
                "Positive operating cash flow demonstrates the business generates "
                "real cash from its core operations without relying on external financing."
            )
        if f.get("return_on_equity", 0) > 15:
            strengths.append(
                f"High return on equity ({f['return_on_equity']:.1f}%) indicates "
                "management is efficiently deploying shareholder capital."
            )
        if f.get("total_cash", 0) > f.get("total_debt", 1):
            strengths.append(
                "Net cash position: The company holds more cash than total debt, "
                "providing a strong liquidity buffer and strategic flexibility."
            )
        if f.get("market_cap", 0) > 1e11:  # > $100B
            strengths.append(
                "Large-cap status (market cap > $100B) reflects institutional trust "
                "and provides access to favourable financing terms."
            )
        if self._positive_news_ratio() >= 0.5:
            strengths.append(
                "Positive media sentiment: The majority of recent news coverage is "
                "favourable, which typically supports investor confidence."
            )
        if not strengths:
            strengths.append("No significant financial strengths identified based on available data.")
        return strengths

    def get_weaknesses(self) -> list[str]:
        """Return a list of identified weaknesses."""
        weaknesses = []
        f = self.f

        if f.get("profit_margin", 0) < 5:
            weaknesses.append(
                f"Thin profit margin of {f['profit_margin']:.1f}% leaves little room "
                "for error and makes the company vulnerable to cost increases."
            )
        if f.get("debt_to_equity", 0) > 2:
            weaknesses.append(
                f"High debt-to-equity ratio of {f['debt_to_equity']:.1f}x suggests "
                "the company relies heavily on borrowed capital, increasing financial risk."
            )
        if f.get("free_cash_flow", 0) < 0:
            weaknesses.append(
                "Negative free cash flow means the company is consuming more cash than "
                "it generates after capital expenditures, limiting reinvestment capacity."
            )
        if f.get("revenue_growth", 0) < 0:
            weaknesses.append(
                f"Revenue decline of {abs(f['revenue_growth']):.1f}% YoY is a red flag, "
                "suggesting market share loss or weakening demand."
            )
        if f.get("pe_ratio", 0) > 60:
            weaknesses.append(
                f"Elevated P/E ratio of {f['pe_ratio']:.1f}x implies the stock price "
                "is priced for perfection; any earnings miss could trigger a sharp re-rating."
            )
        if f.get("return_on_assets", 0) < 5:
            weaknesses.append(
                f"Low return on assets ({f['return_on_assets']:.1f}%) signals the "
                "company's asset base may be underutilised."
            )
        if not weaknesses:
            weaknesses.append("No significant financial weaknesses identified based on available data.")
        return weaknesses

    def get_opportunities(self) -> list[str]:
        """Return a list of potential opportunities."""
        opportunities = []
        f = self.f
        sector = self.p.get("sector", "")

        if f.get("revenue_growth", 0) > 5:
            opportunities.append(
                "Accelerating revenue trajectory creates a platform for market share "
                "expansion through additional product lines or geographic expansion."
            )
        if f.get("total_cash", 0) > 5e9:   # > $5B cash
            opportunities.append(
                f"Large cash reserves (${f['total_cash'] / 1e9:.1f}B) provide "
                "firepower for strategic acquisitions or share buybacks."
            )
        if sector in ("Technology", "Communication Services"):
            opportunities.append(
                "Operates in a high-growth sector with continued tailwinds from "
                "digital transformation, cloud adoption, and AI integration."
            )
        if f.get("dividend_yield", 0) == 0:
            opportunities.append(
                "No current dividend suggests management is reinvesting profits for "
                "growth rather than returning cash, indicating expansion focus."
            )
        if f.get("earnings_growth", 0) > 15:
            opportunities.append(
                f"Strong earnings growth of {f['earnings_growth']:.1f}% signals "
                "potential for further re-rating as earnings compound."
            )
        if not opportunities:
            opportunities.append(
                "General market expansion and potential sector-level tailwinds remain "
                "as baseline opportunities given stable financials."
            )
        return opportunities

    def get_threats(self) -> list[str]:
        """Return a list of identified threats."""
        threats = []
        f = self.f
        neg_ratio = 1 - self._positive_news_ratio()

        if neg_ratio >= 0.4:
            threats.append(
                "Elevated negative news sentiment may reflect underlying operational, "
                "regulatory, or reputational headwinds that require monitoring."
            )
        if f.get("total_debt", 0) > f.get("revenue", 1) * 0.5:
            threats.append(
                "Debt load exceeds 50% of annual revenue, creating potential refinancing "
                "risk if interest rates rise or cash flows deteriorate."
            )
        if f.get("pe_ratio", 0) > 40:
            threats.append(
                "High valuation multiples leave the stock exposed to significant drawdown "
                "in a broader market correction or risk-off environment."
            )
        threats.append(
            "Macroeconomic risks including inflation, rising interest rates, and "
            "potential recession could dampen consumer/enterprise spending."
        )
        threats.append(
            "Intensifying competition from both established incumbents and disruptive "
            "start-ups could pressure market share and pricing power."
        )
        return threats

    def generate(self) -> dict:
        """Return the full SWOT dict."""
        return {
            "strengths":     self.get_strengths(),
            "weaknesses":    self.get_weaknesses(),
            "opportunities": self.get_opportunities(),
            "threats":       self.get_threats(),
        }


# ══════════════════════════════════════════════════════════════════════════════
# Risk Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class RiskAnalyzer:
    """
    Produces a structured risk assessment across multiple risk dimensions.

    Each risk is represented as a dict:
      {"category": str, "level": "High"|"Medium"|"Low", "description": str}
    """

    def __init__(self, financials: dict, news: list, profile: dict):
        self.f = financials
        self.news = news
        self.p = profile

    def _negative_news_ratio(self) -> float:
        if not self.news:
            return 0.0
        neg = sum(1 for n in self.news if n.get("sentiment") == "negative")
        return neg / len(self.news)

    def generate(self) -> list[dict]:
        """Return an ordered list of risk assessment dicts."""
        risks = []
        f = self.f

        # ── Debt / Leverage Risk ───────────────────────────────────────────────
        leverage = f.get("debt_to_equity", 0)
        if leverage > 3:
            level = "High"
            desc = (f"Debt-to-equity of {leverage:.1f}x is dangerously high. "
                    "Servicing this debt becomes difficult during revenue downturns.")
        elif leverage > 1.5:
            level = "Medium"
            desc = (f"Debt-to-equity of {leverage:.1f}x is elevated but manageable "
                    "if operating cash flows remain stable.")
        else:
            level = "Low"
            desc = (f"Debt-to-equity of {leverage:.1f}x indicates a conservatively "
                    "financed balance sheet with limited leverage risk.")
        risks.append({"category": "Leverage Risk", "level": level, "description": desc})

        # ── Liquidity Risk ────────────────────────────────────────────────────
        cash = f.get("total_cash", 0)
        debt = f.get("total_debt", 0)
        if cash < debt * 0.2:
            level = "High"
            desc = "Cash reserves are less than 20% of total debt, indicating a tight liquidity position."
        elif cash < debt * 0.6:
            level = "Medium"
            desc = "Moderate liquidity: cash covers a reasonable portion of short-term obligations."
        else:
            level = "Low"
            desc = "Strong liquidity: ample cash relative to debt obligations reduces short-term risk."
        risks.append({"category": "Liquidity Risk", "level": level, "description": desc})

        # ── Profitability Risk ────────────────────────────────────────────────
        margin = f.get("profit_margin", 0)
        if margin < 0:
            level = "High"
            desc = "Negative profit margin means the company is losing money on every dollar of revenue."
        elif margin < 5:
            level = "Medium"
            desc = f"Thin profit margin of {margin:.1f}% offers little buffer against cost shocks."
        else:
            level = "Low"
            desc = f"Healthy profit margin of {margin:.1f}% provides resilience against cost inflation."
        risks.append({"category": "Profitability Risk", "level": level, "description": desc})

        # ── Valuation Risk ────────────────────────────────────────────────────
        pe = f.get("pe_ratio", 0)
        if pe > 60:
            level = "High"
            desc = (f"P/E ratio of {pe:.1f}x prices in extraordinary growth expectations. "
                    "Any disappointment could trigger a severe de-rating.")
        elif pe > 30:
            level = "Medium"
            desc = (f"P/E ratio of {pe:.1f}x reflects a growth premium. "
                    "Monitoring earnings delivery is critical.")
        elif pe > 0:
            level = "Low"
            desc = f"Reasonable P/E of {pe:.1f}x suggests the stock is fairly to attractively valued."
        else:
            level = "Medium"
            desc = "P/E ratio not available or negative – further qualitative due diligence required."
        risks.append({"category": "Valuation Risk", "level": level, "description": desc})

        # ── Market / Sentiment Risk ────────────────────────────────────────────
        neg_ratio = self._negative_news_ratio()
        if neg_ratio > 0.5:
            level = "High"
            desc = ("More than half of recent news articles are negative. "
                    "Adverse sentiment can trigger selling pressure regardless of fundamentals.")
        elif neg_ratio > 0.25:
            level = "Medium"
            desc = "Some negative media coverage warrants attention but is not alarming at current levels."
        else:
            level = "Low"
            desc = "News sentiment is predominantly neutral or positive, posing limited near-term sentiment risk."
        risks.append({"category": "Sentiment Risk", "level": level, "description": desc})

        # ── Cash Flow Risk ────────────────────────────────────────────────────
        fcf = f.get("free_cash_flow", 0)
        if fcf < 0:
            level = "High"
            desc = ("Negative free cash flow means the company is burning cash. "
                    "Continued burn may necessitate debt issuance or equity dilution.")
        elif fcf < f.get("revenue", 1) * 0.05:
            level = "Medium"
            desc = "Free cash flow generation is modest relative to revenues."
        else:
            level = "Low"
            desc = "Strong free cash flow generation provides financial flexibility and buyback/dividend capacity."
        risks.append({"category": "Cash Flow Risk", "level": level, "description": desc})

        return risks


# ══════════════════════════════════════════════════════════════════════════════
# Financial Health Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class FinancialHealthAnalyzer:
    """Produces a short-paragraph financial health narrative."""

    def __init__(self, financials: dict, profile: dict):
        self.f = financials
        self.p = profile

    def generate(self) -> dict:
        """
        Return a dict with an overall health label and explanatory bullets.
        Labels: "Excellent" | "Good" | "Fair" | "Poor"
        """
        f = self.f
        score = 0  # internal health sub-score (0-6)

        if f.get("profit_margin", 0) > 10:  score += 1
        if f.get("revenue_growth", 0) > 5:  score += 1
        if f.get("free_cash_flow", 0) > 0:  score += 1
        if f.get("debt_to_equity", 99) < 2: score += 1
        if f.get("return_on_equity", 0) > 10: score += 1
        if f.get("total_cash", 0) > f.get("total_debt", 1): score += 1

        if score >= 5:
            label = "Excellent"
            summary = ("The company demonstrates outstanding financial health across "
                       "profitability, growth, leverage, and cash-generation dimensions.")
        elif score >= 4:
            label = "Good"
            summary = ("The company's financials are solid with minor areas for improvement. "
                       "Overall, it is in a healthy position to sustain operations and grow.")
        elif score >= 2:
            label = "Fair"
            summary = ("Mixed financial signals. While some metrics are encouraging, "
                       "key areas (leverage or profitability) require close monitoring.")
        else:
            label = "Poor"
            summary = ("The company faces significant financial headwinds. Multiple metrics "
                       "are below acceptable thresholds, suggesting elevated investment risk.")

        bullets = [
            f"Profit Margin: {f.get('profit_margin', 0):.1f}%",
            f"Revenue Growth (YoY): {f.get('revenue_growth', 0):.1f}%",
            f"Earnings Growth (YoY): {f.get('earnings_growth', 0):.1f}%",
            f"Return on Equity: {f.get('return_on_equity', 0):.1f}%",
            f"Return on Assets: {f.get('return_on_assets', 0):.1f}%",
            f"Debt-to-Equity: {f.get('debt_to_equity', 0):.1f}x",
            (f"Free Cash Flow: ${f.get('free_cash_flow', 0) / 1e9:.2f}B"
             if abs(f.get("free_cash_flow", 0)) > 1e6 else "Free Cash Flow: N/A"),
        ]

        return {"label": label, "summary": summary, "bullets": bullets}


# ══════════════════════════════════════════════════════════════════════════════
# Growth Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class GrowthAnalyzer:
    """Evaluates the company's growth trajectory from historical revenue data."""

    def __init__(self, financials: dict):
        self.f = financials

    def generate(self) -> dict:
        """
        Return growth narrative and chart-ready data.
        """
        f = self.f
        rev_growth = f.get("revenue_growth", 0)
        earn_growth = f.get("earnings_growth", 0)
        rev_history = f.get("revenue_history", [])

        # Compute CAGR if we have ≥ 2 data points
        cagr = None
        if len(rev_history) >= 2:
            start = rev_history[0]["revenue"]
            end   = rev_history[-1]["revenue"]
            years = rev_history[-1]["year"] - rev_history[0]["year"]
            if start > 0 and years > 0:
                cagr = ((end / start) ** (1 / years) - 1) * 100

        # Growth narrative label
        if rev_growth > 20:
            growth_label = "Hyper-Growth"
            narrative = (f"Revenue is growing at {rev_growth:.1f}% YoY – well into "
                         "hyper-growth territory. This growth rate, if sustained, "
                         "would double revenue in under 4 years.")
        elif rev_growth > 10:
            growth_label = "Strong Growth"
            narrative = (f"Revenue growth of {rev_growth:.1f}% YoY is strong and "
                         "outpaces most mature-market benchmarks (~5-7%).")
        elif rev_growth > 0:
            growth_label = "Moderate Growth"
            narrative = (f"Revenue is growing at {rev_growth:.1f}% YoY. Growth is "
                         "positive but moderate; watch for acceleration catalysts.")
        else:
            growth_label = "Revenue Decline"
            narrative = (f"Revenue contracted {abs(rev_growth):.1f}% YoY. This warrants "
                         "investigation into the root cause – market saturation, "
                         "competition, or macro headwinds.")

        return {
            "label":          growth_label,
            "revenue_growth": rev_growth,
            "earnings_growth": earn_growth,
            "cagr":           round(cagr, 2) if cagr is not None else None,
            "narrative":      narrative,
            "revenue_history": rev_history,   # for Chart.js
        }


# ══════════════════════════════════════════════════════════════════════════════
# Competitor Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class CompetitorAnalyzer:
    """
    Ranks the subject company vs its sector peers on Market Cap and P/E.
    """

    def __init__(self, company_profile: dict, company_financials: dict, competitors: list):
        self.p = company_profile
        self.f = company_financials
        self.competitors = competitors

    def generate(self) -> dict:
        """
        Return a structured comparison with qualitative commentary.
        """
        subject = {
            "name":       self.p.get("name", self.p.get("ticker")),
            "ticker":     self.p.get("ticker"),
            "market_cap": self.f.get("market_cap", 0),
            "pe_ratio":   self.f.get("pe_ratio", 0),
        }
        all_peers = self.competitors
        if not all_peers:
            return {
                "subject":     subject,
                "peers":       [],
                "commentary":  "No peer data available for comparison.",
                "market_position": "Unknown",
            }

        # Market-cap rank
        all_caps = [subject["market_cap"]] + [p["market_cap"] for p in all_peers]
        all_caps_sorted = sorted(all_caps, reverse=True)
        rank = all_caps_sorted.index(subject["market_cap"]) + 1
        total = len(all_caps_sorted)

        if rank == 1:
            position = "Market Leader"
            commentary = (f"{subject['name']} is the largest company by market cap "
                          f"among its peer group ({rank}/{total}).")
        elif rank <= total // 2:
            position = "Upper Tier"
            commentary = (f"{subject['name']} ranks {rank} of {total} by market cap, "
                          "placing it in the upper half of its peer group.")
        else:
            position = "Lower Tier"
            commentary = (f"{subject['name']} ranks {rank} of {total} by market cap. "
                          "There is potential to climb the rankings through sustained growth.")

        return {
            "subject":          subject,
            "peers":            all_peers,
            "market_position":  position,
            "rank":             rank,
            "total_peers":      total,
            "commentary":       commentary,
        }
