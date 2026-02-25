"""
risk-hub URL Configuration
==========================
"""

from django.contrib import admin
from django.urls import include, path

from apps.core.views import health_check

urlpatterns = [
    # Health Check (für Load Balancer)
    path("health/", health_check, name="health_check"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # API (Django Ninja)
    path("api/", include("config.api")),
    
    # Domain URLs
    path("risk/", include("apps.risk.urls")),
    path("actions/", include("apps.actions.urls")),
    path("documents/", include("apps.documents.urls")),
    path("reports/", include("apps.reporting.urls")),
    
    # Root redirect
    path("", lambda r: __import__("django.shortcuts", fromlist=["redirect"]).redirect("risk:assessment_list")),
]
