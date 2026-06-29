"""api/urls.py – REST API URL routing"""
from django.urls import path
from .views import AnalyzeCompanyView, TickerSearchView

urlpatterns = [
    # GET /api/analyze/?ticker=TSLA
    path('analyze/', AnalyzeCompanyView.as_view(), name='api-analyze'),
    # GET /api/ticker-search/?q=Tesla
    path('ticker-search/', TickerSearchView.as_view(), name='api-ticker-search'),
]
