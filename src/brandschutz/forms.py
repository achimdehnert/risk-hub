"""Brandschutz forms — concept create/edit, section create."""

from django import forms

from tenancy.models import Site

from .models import FireProtectionConcept, FireSection

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


class FireSectionForm(forms.ModelForm):
    """Form für Brandabschnitte."""

    class Meta:
        model = FireSection
        fields = [
            "name",
            "floor",
            "area_sqm",
            "construction_class",
            "max_occupancy",
            "fire_load_mj_m2",
            "has_sprinkler",
            "has_smoke_detector",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": _CSS,
                    "placeholder": "z.B. Brandabschnitt A1",
                }
            ),
            "floor": forms.TextInput(
                attrs={
                    "class": _CSS,
                    "placeholder": "z.B. EG, 1.OG, UG",
                }
            ),
            "area_sqm": forms.NumberInput(
                attrs={
                    "class": _CSS,
                    "placeholder": "Fläche in m²",
                    "step": "0.1",
                }
            ),
            "construction_class": forms.Select(attrs={"class": _CSS}),
            "max_occupancy": forms.NumberInput(
                attrs={
                    "class": _CSS,
                    "placeholder": "Max. Personen",
                }
            ),
            "fire_load_mj_m2": forms.NumberInput(
                attrs={
                    "class": _CSS,
                    "placeholder": "MJ/m²",
                    "step": "0.1",
                }
            ),
            "has_sprinkler": forms.CheckboxInput(attrs={"class": "rounded border-gray-300"}),
            "has_smoke_detector": forms.CheckboxInput(attrs={"class": "rounded border-gray-300"}),
            "notes": forms.Textarea(
                attrs={
                    "class": _CSS,
                    "rows": 2,
                    "placeholder": "Anmerkungen...",
                }
            ),
        }
