"""
GBU-Wizard Forms (Phase 2C).

Schritt 1: Stoff-Auswahl (SdsRevision + Site)
Schritt 2: Tätigkeitsdaten (Beschreibung, Frequenz, Dauer, Menge)
Schritt 3: Exposition / Substitution (automatisch + manuell bestätigt)
Schritt 4: Maßnahmen bestätigen
Schritt 5: Freigabe
"""

import datetime

from django import forms

from gbu.models.activity import ActivityFrequency


class WizardStep1Form(forms.Form):
    """Schritt 1 — Stoff (SdsRevision) und Standort auswählen."""

    sds_revision_id = forms.UUIDField(
        label="SDB-Revision",
        widget=forms.HiddenInput(),
        required=True,
    )
    site_id = forms.UUIDField(
        label="Standort",
        widget=forms.HiddenInput(),
        required=True,
    )


class WizardStep2Form(forms.Form):
    """Schritt 2 — Tätigkeitsdaten erfassen."""

    activity_description = forms.CharField(
        label="Tätigkeitsbeschreibung",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "w-full border border-gray-300 rounded-lg p-3 text-sm",
                "placeholder": "Was wird gemacht? Mit welchem Stoff? In welchem Bereich?",
            }
        ),
        max_length=2000,
    )
    activity_frequency = forms.ChoiceField(
        label="Expositionsfrequenz",
        choices=[(f.value, f.name.title()) for f in ActivityFrequency],
        widget=forms.RadioSelect(attrs={"class": "mr-2"}),
    )
    duration_minutes = forms.IntegerField(
        label="Expositionsdauer (Minuten/Vorgang)",
        min_value=1,
        max_value=480,
        widget=forms.NumberInput(
            attrs={
                "class": "w-32 border border-gray-300 rounded-lg p-2 text-sm",
            }
        ),
    )
    quantity_class = forms.ChoiceField(
        label="Mengenkategorie (EMKG)",
        choices=[
            ("xs", "XS — weniger als 1 L / kg"),
            ("s", "S — 1 bis 10 L / kg"),
            ("m", "M — 10 bis 100 L / kg"),
            ("l", "L — mehr als 100 L / kg"),
        ],
        widget=forms.RadioSelect(attrs={"class": "mr-2"}),
    )
    substitution_checked = forms.BooleanField(
        label="Substitutionsprüfung nach §7 GefStoffV durchgeführt",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "mr-2"}),
    )
    substitution_notes = forms.CharField(
        label="Ergebnis der Substitutionsprüfung",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": "w-full border border-gray-300 rounded-lg p-2 text-sm",
                "placeholder": "Warum ist Substitution nicht möglich oder wurde durchgeführt?",
            }
        ),
        max_length=1000,
    )


class WizardStep3Form(forms.Form):
    """Schritt 3 — Gefährdungskategorien bestätigen."""

    confirmed = forms.BooleanField(
        label="Ich bestätige, dass die abgeleiteten Gefährdungskategorien korrekt sind.",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "mr-2"}),
        error_messages={"required": "Bitte bestätigen Sie die Gefährdungsbeurteilung."},
    )


class WizardStep4Form(forms.Form):
    """Schritt 4 — Maßnahmen bestätigen."""

    confirmed_measure_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    def get_confirmed_ids(self) -> list[str]:
        raw = self.cleaned_data.get("confirmed_measure_ids", "")
        if not raw:
            return []
        return [m.strip() for m in raw.split(",") if m.strip()]


class WizardStep5Form(forms.Form):
    """Schritt 5 — Freigabe."""

    next_review_date = forms.DateField(
        label="Nächstes Überprüfungsdatum (GefStoffV §6)",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "border border-gray-300 rounded-lg p-2 text-sm",
            }
        ),
    )
    approved_by_name = forms.CharField(
        label="Freigegeben durch (Vollname)",
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "w-full border border-gray-300 rounded-lg p-2 text-sm",
                "placeholder": "Max Mustermann",
            }
        ),
    )
    confirm_release = forms.BooleanField(
        label="Ich gebe diese GBU-Tätigkeit rechtsverbindlich frei (GefStoffV §6).",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "mr-2"}),
        error_messages={"required": "Bitte bestätigen Sie die Freigabe."},
    )

    def clean_next_review_date(self) -> datetime.date:
        value = self.cleaned_data["next_review_date"]
        if value <= datetime.date.today():
            raise forms.ValidationError("Das Überprüfungsdatum muss in der Zukunft liegen.")
        return value
