"""Risk assessment forms (UC-008)."""

from django import forms

from risk.models import Assessment, Hazard, ProtectiveMeasure, SubstitutionCheck


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ["title", "description", "category"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-orange-500 focus:border-orange-500",
                    "placeholder": "Titel der Gefährdungsbeurteilung",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-orange-500 focus:border-orange-500",
                    "rows": 3,
                    "placeholder": "Beschreibung...",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-orange-500 focus:border-orange-500",
                }
            ),
        }


class HazardForm(forms.ModelForm):
    class Meta:
        model = Hazard
        fields = [
            "title",
            "description",
            "severity",
            "probability",
            "mitigation",
            "mitigation_status",
            "due_date",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-orange-500 focus:border-orange-500",
                    "placeholder": "Gefährdung...",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-orange-500 focus:border-orange-500",
                    "rows": 3,
                }
            ),
            "severity": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                }
            ),
            "probability": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                }
            ),
            "mitigation": forms.Textarea(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "rows": 2,
                    "placeholder": "Beschreibung der Gegenmaßnahme...",
                }
            ),
            "mitigation_status": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "type": "date",
                }
            ),
        }


class ProtectiveMeasureForm(forms.ModelForm):
    class Meta:
        model = ProtectiveMeasure
        fields = [
            "measure_type",
            "description",
            "specification",
            "norm_reference",
            "due_date",
            "status",
        ]
        widgets = {
            "measure_type": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "rows": 3,
                    "placeholder": "Beschreibung der Schutzmaßnahme...",
                }
            ),
            "specification": forms.Textarea(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "rows": 2,
                    "placeholder": "PSA-Details, Produktspezifikation...",
                }
            ),
            "norm_reference": forms.TextInput(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "placeholder": "z.B. EN 374, TRGS 510",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "type": "date",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                }
            ),
        }


class SubstitutionCheckForm(forms.ModelForm):
    class Meta:
        model = SubstitutionCheck
        fields = ["result", "justification", "implementation_deadline"]
        widgets = {
            "result": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                }
            ),
            "justification": forms.Textarea(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "rows": 4,
                    "placeholder": "Begründung der Substitutionsprüfung...",
                }
            ),
            "implementation_deadline": forms.DateInput(
                attrs={
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                    "type": "date",
                }
            ),
        }
