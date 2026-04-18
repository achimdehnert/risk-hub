# src/actions/forms.py
"""Django Forms für Maßnahmen-Tracking (UC-Q06)."""

from django import forms

from .models import ActionItem


class ActionItemForm(forms.ModelForm):
    """Form für Maßnahmen."""

    class Meta:
        model = ActionItem
        fields = ["title", "description", "status", "priority", "due_date"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "z.B. Absauganlage in Halle 2 installieren"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 3, "placeholder": "Beschreibung der Maßnahme…"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(
                attrs={"class": "form-input", "type": "date"},
                format="%Y-%m-%d",
            ),
        }
