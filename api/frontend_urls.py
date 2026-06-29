"""api/frontend_urls.py – URL routing for the template-rendered dashboard"""
from django.urls import path
from .frontend_views import DashboardView, MarketDashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('market/', MarketDashboardView.as_view(), name='market_dashboard'),
]
