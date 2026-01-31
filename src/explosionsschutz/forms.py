# src/explosionsschutz/forms.py
"""
Django Forms für Explosionsschutz-Modul
"""

from django import forms

from .models import (
    Area,
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    EquipmentType,
)


class AreaForm(forms.ModelForm):
    """Form für Betriebsbereiche"""

    class Meta:
        model = Area
        fields = ["code", "name", "description"]
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "z.B. PROD-01",
            }),
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "z.B. Produktionshalle 1",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "rows": 3,
                "placeholder": "Beschreibung des Bereichs...",
            }),
        }


class ExplosionConceptForm(forms.ModelForm):
    """Form für Explosionsschutzkonzepte"""

    class Meta:
        model = ExplosionConcept
        fields = ["area", "title", "substance_name"]
        widgets = {
            "area": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
            }),
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "Titel des Konzepts",
            }),
            "substance_name": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "z.B. Ethanol, Lösungsmittel",
            }),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["area"].queryset = Area.objects.filter(
                tenant_id=tenant_id
            )


class ZoneDefinitionForm(forms.ModelForm):
    """Form für Zonendefinitionen"""

    class Meta:
        model = ZoneDefinition
        fields = ["zone_type", "name", "description", "geometry_wkt"]
        widgets = {
            "zone_type": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
            }),
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "z.B. Zone 1 - Abfüllbereich",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "rows": 3,
            }),
            "geometry_wkt": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg font-mono",
                "rows": 2,
                "placeholder": "POLYGON((...)) - optional",
            }),
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
            "location_description",
        ]
        widgets = {
            "area": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
            }),
            "zone": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
            }),
            "equipment_type": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
            }),
            "serial_number": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "Seriennummer",
            }),
            "asset_number": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "Anlagennummer (optional)",
            }),
            "installation_date": forms.DateInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "type": "date",
            }),
            "location_description": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                "placeholder": "z.B. Raum 101, neben Abfüllanlage",
            }),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["area"].queryset = Area.objects.filter(
                tenant_id=tenant_id
            )
            self.fields["zone"].queryset = ZoneDefinition.objects.filter(
                tenant_id=tenant_id
            )
            self.fields["zone"].required = False
            self.fields["equipment_type"].queryset = EquipmentType.objects.filter(
                tenant_id__isnull=True
            ) | EquipmentType.objects.filter(tenant_id=tenant_id)
