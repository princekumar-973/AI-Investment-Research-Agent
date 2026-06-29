"""
analysis/scoring_engine.py
===========================
Rule-Based Investment Scoring Engine
=====================================

This module implements the exact scoring rules specified by the product owner.
Each criterion contributes a maximum of 2 points, yielding a maximum score of 10.

Scoring Rules
-------------
1. Revenue Growth > 10% YoY                    → +2 pts
2. Profit Margin  > 15%                        → +2 pts
3. Low Debt (Debt-to-Equity < 1.0)             → +2 pts
4. Positive News Sentiment (≥ 50% positive)    → +2 pts
5. Strong Cash Flow (Free Cash Flow > 0)       → +2 pts

Total Maximum Score = 10

Investment Decision
-------------------
Score ≥ 8  →  INVEST (green) – Strong financial fundamentals
Score 5–7  →  HOLD   (amber) – Some strengths; await clearer signals
Score < 5  →  PASS   (red)   – Significant risks or weak fundamentals
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Calculates a composite investment score (0–10) using 5 deterministic rules.

    Parameters
    ----------
    financials : dict
        Output of DataFetcherService.get_financial_metrics()
    news : list
        Output of DataFetcherService.get_news()
    """

    # ── Decision thresholds ───────────────────────────────────────────────────
    INVEST_THRESHOLD = 8
    HOLD_THRESHOLD   = 5

    # ── Rule thresholds ────────────────────────────────────────────────────────
    REVENUE_GROWTH_MIN  = 10.0   # percent
    PROFIT_MARGIN_MIN   = 15.0   # percent
    DEBT_TO_EQUITY_MAX  = 1.0    # ratio
    POSITIVE_NEWS_MIN   = 0.50   # fraction
    FREE_CASH_FLOW_MIN  = 0      # absolute USD

    def __init__(self, financials: dict, news: list):
        self.f    = financials
        self.news = news

    # ── Private helper ─────────────────────────────────────────────────────────

    def _positive_news_ratio(self) -> float:
        """Return the fraction of articles with positive sentiment."""
        if not self.news:
            return 0.0
        pos = sum(1 for n in self.news if n.get("sentiment") == "positive")
        return pos / len(self.news)

    # ── Individual rule evaluators ─────────────────────────────────────────────

    def _rule_revenue_growth(self) -> dict:
        """
        Rule 1: Revenue Growth > 10% = +2 points
        Partial credit (+1) awarded for growth between 5%–10%.
        """
        growth = self.f.get("revenue_growth", 0)
        if growth > self.REVENUE_GROWTH_MIN:
            points = 2
            verdict = "PASS"
            explanation = (
                f"Revenue grew {growth:.1f}% YoY, comfortably above the 10% threshold. "
                "This indicates strong commercial momentum and market demand."
            )
        elif growth >= 5:
            points = 1
            verdict = "PARTIAL"
            explanation = (
                f"Revenue grew {growth:.1f}% YoY – positive but below the 10% benchmark. "
                "Growth is healthy at the sector pace but not yet exceptional."
            )
        else:
            points = 0
            verdict = "FAIL"
            explanation = (
                f"Revenue growth of {growth:.1f}% fails to meet the 10% minimum threshold. "
                "This signals slowing demand or competitive pressure."
            )
        return {
            "rule":        "Revenue Growth",
            "criterion":   "> 10% YoY",
            "actual_value": f"{growth:.1f}%",
            "points":      points,
            "max_points":  2,
            "verdict":     verdict,
            "explanation": explanation,
        }

    def _rule_profit_margin(self) -> dict:
        """
        Rule 2: Profit Margin > 15% = +2 points
        Partial credit (+1) for margins between 5%–15%.
        """
        margin = self.f.get("profit_margin", 0)
        if margin > self.PROFIT_MARGIN_MIN:
            points = 2
            verdict = "PASS"
            explanation = (
                f"Profit margin of {margin:.1f}% exceeds the 15% benchmark, "
                "demonstrating excellent operational efficiency and pricing power."
            )
        elif margin >= 5:
            points = 1
            verdict = "PARTIAL"
            explanation = (
                f"Profit margin of {margin:.1f}% is acceptable but below the 15% ideal. "
                "The company is profitable but cost structure should be monitored."
            )
        else:
            points = 0
            verdict = "FAIL"
            explanation = (
                f"Profit margin of {margin:.1f}% is very thin or negative. "
                "The company struggles to convert revenue into bottom-line profit."
            )
        return {
            "rule":        "Profit Margin",
            "criterion":   "> 15%",
            "actual_value": f"{margin:.1f}%",
            "points":      points,
            "max_points":  2,
            "verdict":     verdict,
            "explanation": explanation,
        }

    def _rule_low_debt(self) -> dict:
        """
        Rule 3: Low Debt (Debt-to-Equity < 1.0) = +2 points
        Partial credit (+1) for D/E between 1.0–2.0.
        """
        de_ratio = self.f.get("debt_to_equity", 0)
        if de_ratio <= self.DEBT_TO_EQUITY_MAX:
            points = 2
            verdict = "PASS"
            explanation = (
                f"Debt-to-equity of {de_ratio:.1f}x is low, indicating a conservatively "
                "financed company that is not overly reliant on borrowed capital."
            )
        elif de_ratio <= 2.0:
            points = 1
            verdict = "PARTIAL"
            explanation = (
                f"Debt-to-equity of {de_ratio:.1f}x is elevated but manageable. "
                "Monitor debt service capacity if interest rates rise."
            )
        else:
            points = 0
            verdict = "FAIL"
            explanation = (
                f"Debt-to-equity of {de_ratio:.1f}x is high. The company carries "
                "significant financial leverage which amplifies downside risk."
            )
        return {
            "rule":        "Low Debt",
            "criterion":   "Debt-to-Equity < 1.0",
            "actual_value": f"{de_ratio:.1f}x",
            "points":      points,
            "max_points":  2,
            "verdict":     verdict,
            "explanation": explanation,
        }

    def _rule_positive_news(self) -> dict:
        """
        Rule 4: Positive News Sentiment ≥ 50% = +2 points
        Partial credit (+1) for 25%–49% positive.
        """
        pos_ratio = self._positive_news_ratio()
        pos_pct   = pos_ratio * 100
        if pos_ratio >= self.POSITIVE_NEWS_MIN:
            points = 2
            verdict = "PASS"
            explanation = (
                f"{pos_pct:.0f}% of recent news articles are positive, reflecting "
                "favourable market perception and strong public/investor sentiment."
            )
        elif pos_ratio >= 0.25:
            points = 1
            verdict = "PARTIAL"
            explanation = (
                f"{pos_pct:.0f}% of recent news is positive. Sentiment is mixed. "
                "Watch for developments that could shift the narrative either way."
            )
        else:
            points = 0
            verdict = "FAIL"
            explanation = (
                f"Only {pos_pct:.0f}% of recent news is positive. Predominantly negative "
                "sentiment may weigh on investor confidence and stock performance."
            )
        return {
            "rule":        "Positive News",
            "criterion":   "≥ 50% positive sentiment",
            "actual_value": f"{pos_pct:.0f}% positive",
            "points":      points,
            "max_points":  2,
            "verdict":     verdict,
            "explanation": explanation,
        }

    def _rule_cash_flow(self) -> dict:
        """
        Rule 5: Strong Cash Flow (Free Cash Flow > 0) = +2 points
        Partial credit (+1) for positive Operating Cash Flow with negative FCF.
        """
        fcf = self.f.get("free_cash_flow", 0)
        ocf = self.f.get("operating_cash_flow", 0)
        fcf_b = fcf / 1e9 if abs(fcf) > 1e6 else fcf     # display in $B

        if fcf > self.FREE_CASH_FLOW_MIN:
            points = 2
            verdict = "PASS"
            explanation = (
                f"Free cash flow of ${fcf_b:.2f}B is positive, demonstrating the "
                "company generates real cash surplus after capital expenditures."
            )
        elif ocf > 0:
            points = 1
            verdict = "PARTIAL"
            explanation = (
                "Operating cash flow is positive but free cash flow is negative, "
                "suggesting high capital expenditure investment phase. "
                "Monitor capex trends to see if FCF turns positive."
            )
        else:
            points = 0
            verdict = "FAIL"
            explanation = (
                "Both free and operating cash flows are negative. The company is "
                "burning cash and may need to raise capital to sustain operations."
            )
        return {
            "rule":        "Strong Cash Flow",
            "criterion":   "Free Cash Flow > 0",
            "actual_value": f"${fcf_b:.2f}B FCF",
            "points":      points,
            "max_points":  2,
            "verdict":     verdict,
            "explanation": explanation,
        }

    # ── Master scorer ──────────────────────────────────────────────────────────

    def calculate(self) -> dict:
        """
        Run all five rules and return a comprehensive scoring result.

        Returns
        -------
        dict with keys:
          score         – int total (0–10)
          max_score     – int (always 10)
          recommendation – "INVEST" | "HOLD" | "PASS"
          decision_color – "green" | "amber" | "red"
          summary        – one-sentence overall reasoning
          rules          – list of per-rule breakdown dicts
        """
        rules_results = [
            self._rule_revenue_growth(),
            self._rule_profit_margin(),
            self._rule_low_debt(),
            self._rule_positive_news(),
            self._rule_cash_flow(),
        ]

        total_score = sum(r["points"] for r in rules_results)

        # ── Decision logic ────────────────────────────────────────────────────
        if total_score >= self.INVEST_THRESHOLD:
            recommendation = "INVEST"
            decision_color = "green"
            summary = (
                f"With a score of {total_score}/10, the company meets or exceeds all major "
                "investment criteria. The fundamentals support initiating or adding to a position."
            )
        elif total_score >= self.HOLD_THRESHOLD:
            recommendation = "HOLD"
            decision_color = "amber"
            summary = (
                f"A score of {total_score}/10 indicates solid but not outstanding fundamentals. "
                "Existing holders should hold; new investors may wait for a better entry."
            )
        else:
            recommendation = "PASS"
            decision_color = "red"
            summary = (
                f"A score of {total_score}/10 reveals multiple financial weaknesses. "
                "The risk/reward profile is unfavourable at this time."
            )

        logger.info(
            "Scoring complete for ticker: score=%d recommendation=%s",
            total_score, recommendation
        )

        return {
            "score":           total_score,
            "max_score":       10,
            "recommendation":  recommendation,
            "decision_color":  decision_color,
            "summary":         summary,
            "rules":           rules_results,
        }
