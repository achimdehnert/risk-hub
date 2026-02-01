# src/substances/urls.py
"""URL-Konfiguration für Substances Module."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "substances-api"

# DRF Router
router = DefaultRouter()
router.register(r"parties", views.PartyViewSet, basename="party")
router.register(r"substances", views.SubstanceViewSet, basename="substance")
router.register(r"sds", views.SdsRevisionViewSet, basename="sds")
router.register(r"inventory", views.SiteInventoryViewSet, basename="inventory")

# Referenzdaten (Read-Only)
router.register(
    r"ref/h-statements",
    views.HazardStatementRefViewSet,
    basename="h-statement"
)
router.register(
    r"ref/p-statements",
    views.PrecautionaryStatementRefViewSet,
    basename="p-statement"
)
router.register(
    r"ref/pictograms",
    views.PictogramRefViewSet,
    basename="pictogram"
)

urlpatterns = [
    # API Endpoints
    path("", include(router.urls)),
    
    # Custom Endpoints
    path(
        "substances/<uuid:pk>/sds/upload/",
        views.SdsUploadView.as_view(),
        name="sds-upload"
    ),
    path(
        "sds/<uuid:pk>/approve/",
        views.SdsApproveView.as_view(),
        name="sds-approve"
    ),
    path(
        "exports/hazard-register/",
        views.HazardRegisterExportView.as_view(),
        name="hazard-register-export"
    ),
]
