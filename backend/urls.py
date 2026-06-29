"""
Root URL configuration for investment_agent.
All API routes live under /api/ and the dashboard serves at /.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # REST API endpoints
    path('api/', include('api.urls')),
    # Frontend dashboard (template-based view)
    path('', include('api.frontend_urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
