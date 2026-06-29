"""api/frontend_views.py – Serves the single-page dashboard template"""
from django.views.generic import TemplateView


class DashboardView(TemplateView):
    """Render the main investment research dashboard."""
    template_name = "dashboard.html"


class MarketDashboardView(TemplateView):
    """Render the Simply Wall St-inspired stock market dashboard."""
    template_name = "market_dashboard.html"
