# src/explosionsschutz/forms.py
"""
Django Forms für Explosionsschutz-Modul
"""

from django import forms

from .models import (
    Area,
    Equipment,
    EquipmentType,
    ExplosionConcept,
    ZoneDefinition,
)


class AreaForm(forms.ModelForm):
    """Form für Betriebsbereiche"""

    class Meta:
        model = Area
        fields = ["code", "name", "description"]
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "z.B. PROD-01",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "z.B. Produktionshalle 1",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "rows": 3,
                    "placeholder": "Beschreibung des Bereichs...",
                }
            ),
        }


class ExplosionConceptForm(forms.ModelForm):
    """Form für Explosionsschutzkonzepte"""

    class Meta:
        model = ExplosionConcept
        fields = ["area", "title", "substance_name"]
        widgets = {
            "area": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "Titel des Konzepts",
                }
            ),
            "substance_name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "z.B. Ethanol, Lösungsmittel",
                }
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["area"].queryset = Area.objects.filter(tenant_id=tenant_id)


class ZoneDefinitionForm(forms.ModelForm):
    """Form für Zonendefinitionen"""

    class Meta:
        model = ZoneDefinition
        fields = ["zone_type", "name", "description", "justification"]
        widgets = {
            "zone_type": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "z.B. Zone 1 - Abfüllbereich",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "rows": 3,
                }
            ),
            "justification": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "rows": 2,
                    "placeholder": "Begründung für Zoneneinteilung",
                }
            ),
        }


class EquipmentForm(forms.ModelForm):
    """Form für Betriebsmittel"""

    class Meta:
        model = Equipment
        fields = [
            "area",
            "zone",
            "equipment_type",
            "serial_number",
            "asset_number",
            "installation_date",
            "location_detail",
        ]
        widgets = {
            "area": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                }
            ),
            "zone": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                }
            ),
            "equipment_type": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                }
            ),
            "serial_number": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "Seriennummer",
                }
            ),
            "asset_number": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "Anlagennummer (optional)",
                }
            ),
            "installation_date": forms.DateInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "type": "date",
                }
            ),
            "location_detail": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                    "placeholder": "z.B. Raum 101, neben Abfüllanlage",
                }
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["area"].queryset = Area.objects.filter(tenant_id=tenant_id)
            self.fields["zone"].queryset = ZoneDefinition.objects.filter(tenant_id=tenant_id)
            self.fields["zone"].required = False
            self.fields["equipment_type"].queryset = EquipmentType.objects.filter(
                tenant_id__isnull=True
            ) | EquipmentType.objects.filter(tenant_id=tenant_id)


_INPUT_CSS = "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-300"


class ZoneCalculationForm(forms.Form):
    """Formular für TRGS 721 Zonenberechnung via riskfw"""

    RELEASE_CHOICES = [
        ("jet", "Strahlausbreitung (Jet)"),
        ("pool", "Lachenausbreitung (Pool)"),
        ("diffuse", "Diffuse Freisetzung"),
    ]

    zone_id = forms.UUIDField(widget=forms.HiddenInput())
    release_rate_kg_s = forms.FloatField(
        label="Freisetzungsrate (kg/s)",
        min_value=0.0001,
        widget=forms.NumberInput(
            attrs={
                "class": _INPUT_CSS,
                "step": "0.0001",
                "placeholder": "z.B. 0.01",
            }
        ),
    )
    ventilation_rate_m3_s = forms.FloatField(
        label="Lüftungsrate (m³/s)",
        min_value=0.001,
        widget=forms.NumberInput(
            attrs={
                "class": _INPUT_CSS,
                "step": "0.001",
                "placeholder": "z.B. 0.5",
            }
        ),
    )
    release_type = forms.ChoiceField(
        label="Freisetzungsart",
        choices=RELEASE_CHOICES,
        widget=forms.Select(attrs={"class": _INPUT_CSS}),
    )
    notes = forms.CharField(
        label="Bemerkungen",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": _INPUT_CSS,
                "rows": 2,
                "placeholder": "Optionale Hinweise zur Berechnung...",
            }
        ),
    )


class ConceptDxfImportForm(forms.Form):
    """Formular für DXF-Import von Ex-Zonen via nl2cad-brandschutz"""

    dxf_file = forms.FileField(
        label="DXF-Datei",
        widget=forms.ClearableFileInput(
            attrs={
                "class": _INPUT_CSS,
                "accept": ".dxf",
            }
        ),
        help_text="Max. 50 MB. Ex-Zonen-Layer werden automatisch erkannt.",
    )
