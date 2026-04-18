# src/training/forms.py
"""Django Forms für Unterweisungen (UC-009)."""

from django import forms
from django.db.models import Q

from tenancy.models import Department, Site

from .models import TrainingAttendance, TrainingSession, TrainingTopic


class TrainingTopicForm(forms.ModelForm):
    """Form für Unterweisungsthemen."""

    class Meta:
        model = TrainingTopic
        fields = ["title", "description", "interval", "site", "department"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "z.B. Umgang mit brennbaren Flüssigkeiten"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 3, "placeholder": "Inhalt der Unterweisung…"}
            ),
            "interval": forms.Select(attrs={"class": "form-select"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["site"].queryset = Site.objects.filter(tenant_id=tenant_id, is_active=True)
            self.fields["department"].queryset = Department.objects.filter(tenant_id=tenant_id)
        self.fields["site"].required = False
        self.fields["department"].required = False


class TrainingSessionForm(forms.ModelForm):
    """Form für Unterweisungs-Veranstaltungen."""

    class Meta:
        model = TrainingSession
        fields = ["topic", "session_date", "status", "notes"]
        widgets = {
            "topic": forms.Select(attrs={"class": "form-select"}),
            "session_date": forms.DateInput(
                attrs={"class": "form-input", "type": "date"},
                format="%Y-%m-%d",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 3, "placeholder": "Anmerkungen…"}
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["topic"].queryset = TrainingTopic.objects.filter(
                tenant_id=tenant_id, is_active=True
            )
