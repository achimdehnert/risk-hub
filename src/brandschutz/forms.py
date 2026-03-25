"""Brandschutz forms — concept create/edit."""

from django import forms

from tenancy.models import Site

from .models import FireProtectionConcept

_CSS = "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-300"


class FireProtectionConceptForm(forms.ModelForm):
    """Form für Brandschutzkonzepte — Create + Edit."""

    class Meta:
        model = FireProtectionConcept
        fields = [
            "site",
            "title",
            "concept_type",
            "status",
            "description",
            "valid_from",
            "valid_until",
        ]
        widgets = {
            "site": forms.Select(attrs={"class": _CSS}),
            "title": forms.TextInput(
                attrs={"class": _CSS, "placeholder": "z.B. Brandschutzkonzept Hauptgebäude"}
            ),
            "concept_type": forms.Select(attrs={"class": _CSS}),
            "status": forms.Select(attrs={"class": _CSS}),
            "description": forms.Textarea(
                attrs={"class": _CSS, "rows": 3, "placeholder": "Beschreibung..."}
            ),
            "valid_from": forms.DateInput(attrs={"class": _CSS, "type": "date"}),
            "valid_until": forms.DateInput(attrs={"class": _CSS, "type": "date"}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["site"].queryset = Site.objects.filter(tenant_id=tenant_id)
