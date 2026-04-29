from django.urls import path
from . import views

app_name = "intake"

urlpatterns = [
    path("new/", views.intake_new, name="new"),
    path("upload/", views.intake_upload, name="upload"),
    path("<int:pk>/route/", views.intake_route, name="route"),
]
