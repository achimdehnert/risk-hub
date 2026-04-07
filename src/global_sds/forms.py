# src/global_sds/forms.py
"""Forms für Global SDS Library Frontend (ADR-012)."""

from django import forms

from global_sds.models import GlobalSdsRevision

_TW = "w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 text-sm"


class RevisionEditForm(forms.ModelForm):
    """Bearbeitung einer SDS-Revision (Metadaten + regulatorisch)."""

    class Meta:
        model = GlobalSdsRevision
        fields = [
            "product_name",
            "manufacturer_name",
            "revision_date",
            "version_number",
            "signal_word",
            "wgk",
            "storage_class_trgs510",
            "flash_point_c",
            "ignition_temperature_c",
            "lower_explosion_limit",
            "upper_explosion_limit",
            "status",
        ]
        widgets = {
            "product_name": forms.TextInput(
                attrs={"class": _TW},
            ),
            "manufacturer_name": forms.TextInput(
                attrs={"class": _TW},
            ),
            "revision_date": forms.DateInput(
                attrs={"class": _TW, "type": "date"},
            ),
            "version_number": forms.TextInput(
                attrs={"class": _TW},
            ),
            "signal_word": forms.Select(
                choices=[
                    ("", "—"),
                    ("danger", "Gefahr / Danger"),
                    ("warning", "Achtung / Warning"),
                    ("none", "Kein Signalwort"),
                ],
                attrs={"class": _TW},
            ),
            "wgk": forms.NumberInput(
                attrs={"class": _TW, "min": 1, "max": 3},
            ),
            "storage_class_trgs510": forms.TextInput(
                attrs={"class": _TW},
            ),
            "flash_point_c": forms.NumberInput(
                attrs={"class": _TW, "step": "0.1"},
            ),
            "ignition_temperature_c": forms.NumberInput(
                attrs={"class": _TW, "step": "0.1"},
            ),
            "lower_explosion_limit": forms.NumberInput(
                attrs={"class": _TW, "step": "0.001"},
            ),
            "upper_explosion_limit": forms.NumberInput(
                attrs={"class": _TW, "step": "0.001"},
            ),
            "status": forms.Select(attrs={"class": _TW}),
        }
        labels = {
            "product_name": "Produktname",
            "manufacturer_name": "Hersteller",
            "revision_date": "Revisionsdatum",
            "version_number": "Version",
            "signal_word": "Signalwort",
            "wgk": "WGK (1-3)",
            "storage_class_trgs510": "Lagerklasse (TRGS 510)",
            "flash_point_c": "Flammpunkt (°C)",
            "ignition_temperature_c": "Zündtemperatur (°C)",
            "lower_explosion_limit": "UEG (Vol.%)",
            "upper_explosion_limit": "OEG (Vol.%)",
            "status": "Status",
        }


class GlobalSdsUploadForm(forms.Form):
    """SDS-PDF Upload in die globale Pipeline."""

    pdf_file = forms.FileField(
        label="SDS-Datei (PDF)",
        help_text="Sicherheitsdatenblatt als PDF-Datei",
        widget=forms.FileInput(
            attrs={"class": "form-input", "accept": ".pdf"},
        ),
    )


class DeferUpdateForm(forms.Form):
    """Zurückstellung mit Pflichtbegründung (GefStoffV §7)."""

    reason = forms.CharField(
        label="Begründung",
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea w-full rounded-lg border-gray-300",
                "rows": 3,
                "placeholder": (
                    "Begründung für die Zurückstellung (Pflichtfeld gemäß GefStoffV §7)..."
                ),
            }
        ),
        help_text="Pflichtfeld — wird für Audit-Trail gespeichert.",
    )
    deferred_until = forms.DateField(
        label="Zurückgestellt bis",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-input",
                "type": "date",
            }
        ),
        help_text="Optional: Datum bis wann zurückgestellt.",
    )
