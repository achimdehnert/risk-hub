# src/global_sds/forms.py
"""Forms für Global SDS Library Frontend (ADR-012)."""

from django import forms


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
        widget=forms.Textarea(attrs={
            "class": "form-textarea w-full rounded-lg border-gray-300",
            "rows": 3,
            "placeholder": (
                "Begründung für die Zurückstellung "
                "(Pflichtfeld gemäß GefStoffV §7)..."
            ),
        }),
        help_text="Pflichtfeld — wird für Audit-Trail gespeichert.",
    )
    deferred_until = forms.DateField(
        label="Zurückgestellt bis",
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-input",
            "type": "date",
        }),
        help_text="Optional: Datum bis wann zurückgestellt.",
    )
