# src/substances/kataster_urls.py
"""URL-Konfiguration für das Gefahrstoffkataster (UC-004)."""

from django.urls import path

from . import kataster_views as views

app_name = "kataster"

urlpatterns = [
    # Dashboard
    path("", views.KatasterDashboardView.as_view(), name="dashboard"),
    # Produkte
    path("produkte/", views.ProductListView.as_view(), name="product-list"),
    path("produkte/neu/", views.ProductCreateView.as_view(), name="product-create"),
    path("produkte/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("produkte/<int:pk>/edit/", views.ProductEditView.as_view(), name="product-edit"),
    # Verwendungen
    path("verwendungen/", views.UsageListView.as_view(), name="usage-list"),
    path("verwendungen/neu/", views.UsageCreateView.as_view(), name="usage-create"),
    path("verwendungen/<int:pk>/", views.UsageDetailView.as_view(), name="usage-detail"),
    path("verwendungen/<int:pk>/edit/", views.UsageEditView.as_view(), name="usage-edit"),
    # Import
    path("import/", views.KatasterImportView.as_view(), name="import"),
    path("import/batches/", views.ImportBatchListView.as_view(), name="import-list"),
]
