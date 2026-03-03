from django.urls import path

from gbu import views

app_name = "gbu"

urlpatterns = [
    path("", views.activity_list, name="activity-list"),
    path("compliance/", views.compliance_dashboard, name="compliance-dashboard"),
    path("new/", views.wizard_step1, name="wizard-step1"),
    path("new/step2/", views.wizard_step2, name="wizard-step2"),
    path("new/step3/", views.wizard_step3, name="wizard-step3"),
    path("new/step4/", views.wizard_step4, name="wizard-step4"),
    path("new/step5/", views.wizard_step5, name="wizard-step5"),
    path("<uuid:pk>/", views.activity_detail, name="activity-detail"),
    path("<uuid:pk>/pdf/gbu/", views.download_gbu_pdf, name="pdf-gbu"),
    path("<uuid:pk>/pdf/ba/", views.download_ba_pdf, name="pdf-ba"),
    path("partials/hazards/", views.partial_hazard_list, name="partial-hazards"),
    path("partials/measures/", views.partial_measure_list, name="partial-measures"),
    path(
        "partials/risk-badge/",
        views.partial_risk_badge,
        name="partial-risk-badge",
    ),
]
