# src/explosionsschutz/urls.py
"""
URL-Routing für Explosionsschutz-Modul

Verwendet Django REST Framework für API-Endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "explosionsschutz"

router = DefaultRouter()
router.register(r"areas", views.AreaViewSet, basename="area")
router.register(r"concepts", views.ExplosionConceptViewSet, basename="concept")
router.register(r"zones", views.ZoneDefinitionViewSet, basename="zone")
router.register(r"measures", views.ProtectionMeasureViewSet, basename="measure")
router.register(r"equipment", views.EquipmentViewSet, basename="equipment")
router.register(r"inspections", views.InspectionViewSet, basename="inspection")
router.register(r"documents", views.VerificationDocumentViewSet, basename="document")

# Stammdaten (Read-Only für normale User)
router.register(
    r"master/standards",
    views.ReferenceStandardViewSet,
    basename="standard"
)
router.register(
    r"master/catalog",
    views.MeasureCatalogViewSet,
    basename="catalog"
)
router.register(
    r"master/equipment-types",
    views.EquipmentTypeViewSet,
    basename="equipment-type"
)
router.register(
    r"master/safety-functions",
    views.SafetyFunctionViewSet,
    basename="safety-function"
)

urlpatterns = [
    path("", include(router.urls)),
    
    # Custom Actions
    path(
        "concepts/<uuid:pk>/validate/",
        views.ExplosionConceptViewSet.as_view({"post": "validate"}),
        name="concept-validate"
    ),
    path(
        "concepts/<uuid:pk>/archive/",
        views.ExplosionConceptViewSet.as_view({"post": "archive"}),
        name="concept-archive"
    ),
    path(
        "concepts/<uuid:pk>/export-pdf/",
        views.ExplosionConceptViewSet.as_view({"get": "export_pdf"}),
        name="concept-export-pdf"
    ),
    
    # Dashboard & Reports
    path(
        "dashboard/",
        views.DashboardView.as_view(),
        name="dashboard"
    ),
    path(
        "reports/inspections-due/",
        views.InspectionsDueReportView.as_view(),
        name="inspections-due"
    ),
    path(
        "reports/zone-summary/",
        views.ZoneSummaryReportView.as_view(),
        name="zone-summary"
    ),
]
