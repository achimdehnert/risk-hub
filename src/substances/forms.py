# src/substances/forms.py
"""Django Forms für Substances Module."""

from django import forms
from django.db.models import Q

from .models import Party, Substance, SdsRevision


class SubstanceForm(forms.ModelForm):
    """Form für Gefahrstoff-Erstellung/-Bearbeitung."""

    cas_number = forms.CharField(
        max_length=20,
        required=False,
        label="CAS-Nummer",
        help_text="z.B. 67-64-1",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "000-00-0"
        })
    )

    class Meta:
        model = Substance
        fields = [
            "name", "trade_name", "description",
            "status", "storage_class", "is_cmr",
            "manufacturer", "supplier",
            "flash_point_c", "ignition_temperature_c",
            "lower_explosion_limit", "upper_explosion_limit",
            "temperature_class", "explosion_group", "vapor_density",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Stoffname"
            }),
            "trade_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Handelsname (optional)"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "Beschreibung / Verwendungszweck"
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
            "storage_class": forms.Select(attrs={"class": "form-select"}),
            "is_cmr": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "manufacturer": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "flash_point_c": forms.NumberInput(attrs={
                "class": "form-input",
                "placeholder": "°C"
            }),
            "ignition_temperature_c": forms.NumberInput(attrs={
                "class": "form-input",
                "placeholder": "°C"
            }),
            "lower_explosion_limit": forms.NumberInput(attrs={
                "class": "form-input",
                "placeholder": "Vol.%",
                "step": "0.1"
            }),
            "upper_explosion_limit": forms.NumberInput(attrs={
                "class": "form-input",
                "placeholder": "Vol.%",
                "step": "0.1"
            }),
            "temperature_class": forms.Select(
                choices=[("", "---")] + [
                    ("T1", "T1 (≤450°C)"),
                    ("T2", "T2 (≤300°C)"),
                    ("T3", "T3 (≤200°C)"),
                    ("T4", "T4 (≤135°C)"),
                    ("T5", "T5 (≤100°C)"),
                    ("T6", "T6 (≤85°C)"),
                ],
                attrs={"class": "form-select"}
            ),
            "explosion_group": forms.Select(
                choices=[("", "---")] + [
                    ("IIA", "IIA"),
                    ("IIB", "IIB"),
                    ("IIC", "IIC"),
                ],
                attrs={"class": "form-select"}
            ),
            "vapor_density": forms.NumberInput(attrs={
                "class": "form-input",
                "placeholder": "Luft = 1",
                "step": "0.01"
            }),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id

        # Filtere Parteien nach Tenant
        if tenant_id:
            self.fields["manufacturer"].queryset = Party.objects.filter(
                Q(tenant_id=tenant_id),
                party_type="manufacturer"
            )
            self.fields["supplier"].queryset = Party.objects.filter(
                Q(tenant_id=tenant_id),
                party_type="supplier"
            )


class SdsUploadForm(forms.Form):
    """Form für SDS-PDF Upload."""

    pdf_file = forms.FileField(
        label="SDS-Datei (PDF)",
        help_text="Sicherheitsdatenblatt als PDF-Datei",
        widget=forms.FileInput(attrs={
            "class": "form-input",
            "accept": ".pdf"
        })
    )

    revision_date = forms.DateField(
        label="Revisionsdatum",
        help_text="Datum des Sicherheitsdatenblatts",
        widget=forms.DateInput(attrs={
            "class": "form-input",
            "type": "date"
        })
    )


class PartyForm(forms.ModelForm):
    """Form für Hersteller/Lieferanten."""

    class Meta:
        model = Party
        fields = ["name", "party_type", "email", "phone", "address", "website"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Firmenname"
            }),
            "party_type": forms.Select(attrs={"class": "form-select"}),
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "email@example.com"
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "+49 ..."
            }),
            "address": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 3
            }),
            "website": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "https://..."
            }),
        }
