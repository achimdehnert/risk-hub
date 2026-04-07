"""
Django Forms für das Explosionsschutz-Modul.
Keine business logic in Forms – nur Eingabevalidierung.
"""
from __future__ import annotations

from django import forms

from .models import (
    ExplosionConcept,
    Inspection,
    ProtectionMeasure,
    SubstituteCheckStatus,
    ZoneDefinition,
)


class AreaForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        label="Kürzel",
        widget=forms.TextInput(attrs={"placeholder": "z.B. E2-50.01"}),
    )
    name = forms.CharField(max_length=200, label="Bezeichnung")
    description = forms.CharField(
        required=False,
        label="Beschreibung",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    location_description = forms.CharField(
        required=False,
        max_length=500,
        label="Gebäude / Raum / Adresse",
        widget=forms.TextInput(),
    )


class ConceptBasicForm(forms.Form):
    """Wizard Schritt 1: Grunddaten."""

    area_id = forms.UUIDField(
        label="Betriebsbereich",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    title = forms.CharField(
        max_length=300,
        label="Dokumententitel",
        widget=forms.TextInput(
            attrs={"placeholder": "z.B. Explosionsschutzdokument Senkrechtofen Nr. 5"}
        ),
    )
    document_number = forms.CharField(
        required=False,
        max_length=100,
        label="Dokumentennummer",
        widget=forms.TextInput(attrs={"placeholder": "interne Nummer (optional)"}),
    )
    atmosphere_type = forms.ChoiceField(
        label="Atmosphären-Typ",
        choices=ExplosionConcept.AtmosphereType.choices,
        widget=forms.RadioSelect,
        initial="gas",
    )
    substance_id = forms.UUIDField(
        required=False,
        label="Maßgeblicher Stoff",
        help_text="Stoff aus Gefahrstoffkataster (optional – kann später ergänzt werden)",
        widget=forms.HiddenInput(),
    )
    process_description = forms.CharField(
        required=False,
        label="Anlagen- / Verfahrensbeschreibung",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": (
                    "Beschreiben Sie die Anlage und das Verfahren: "
                    "Art der Anlage, eingesetzte Stoffe, Betriebsweise, …"
                ),
            }
        ),
    )

    def __init__(self, *args, areas=None, **kwargs):
        super().__init__(*args, **kwargs)
        if areas is not None:
            self.fields["area_id"].widget = forms.Select(
                choices=[("", "— Bereich wählen —")]
                + [(str(a.id), str(a)) for a in areas],
                attrs={"class": "form-select"},
            )


class ConceptReleaseForm(forms.Form):
    """Wizard Schritt 2: Substitutionsprüfung + Freisetzungsquellen."""

    substitute_check_status = forms.ChoiceField(
        label="Substitutionsprüfung (GefStoffV §6(2))",
        choices=[(s.value, s.value.replace("_", " ").title()) for s in SubstituteCheckStatus],
        widget=forms.RadioSelect,
        initial=SubstituteCheckStatus.NOT_CHECKED,
    )
    substitute_check_notes = forms.CharField(
        required=False,
        label="Begründung (wenn Substitution nicht möglich)",
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "z.B. 'Verfahrenstechnisch nicht möglich – Wasserstoff ist Prozessgas.'",
            }
        ),
    )
    release_source_type = forms.ChoiceField(
        label="Art des Freisetzungsmediums",
        choices=[
            ("gas", "Gas"),
            ("vapor", "Dampf / Nebel"),
            ("dust", "Staub"),
            ("mist", "Aerosol"),
        ],
        widget=forms.RadioSelect,
    )
    release_grade = forms.ChoiceField(
        label="Freisetzungsgrad (TRGS 721 Abschnitt 4)",
        choices=[
            ("continuous", "Ständig / kontinuierlich (Zone 0/20)"),
            ("primary", "Gelegentlich im Normalbetrieb (Zone 1/21)"),
            ("secondary", "Selten und kurzzeitig bei Störungen (Zone 2/22)"),
        ],
        widget=forms.RadioSelect,
    )
    release_description = forms.CharField(
        required=False,
        label="Beschreibung der Freisetzungsquellen und -raten",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": (
                    "Beschreiben Sie Art, Ort und Rate der Freisetzung. "
                    "z.B. 'Offene Behälter beim Umfüllen, nur bei geringfügigen Leckagen …'"
                ),
            }
        ),
    )


class ZoneForm(forms.Form):
    """Formular für eine einzelne Zonendefinition."""

    name = forms.CharField(
        max_length=200,
        label="Zonenbezeichnung",
        widget=forms.TextInput(
            attrs={"placeholder": "z.B. Umgebung Wasserstoffeinlass, 5 m Radius"}
        ),
    )
    zone_type = forms.ChoiceField(
        label="Zonentyp",
        choices=[("", "— aus Vorschlag übernehmen —")]
        + list(ZoneDefinition.ZoneType.choices),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location_in_area = forms.CharField(
        required=False,
        max_length=300,
        label="Lage im Bereich",
        widget=forms.TextInput(attrs={"placeholder": "z.B. 'Ofenraum E2-50.01, Raumbereich'"}),
    )
    extent_shape = forms.ChoiceField(
        label="Geometrie",
        choices=ZoneDefinition.ExtentShape.choices,
        initial="custom",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    extent_radius_m = forms.DecimalField(
        required=False, label="Radius [m]", min_value=0
    )
    extent_height_m = forms.DecimalField(
        required=False, label="Höhe [m]", min_value=0
    )
    extent_description = forms.CharField(
        required=False,
        label="Ausdehnung (Freitext)",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    ventilation_type = forms.ChoiceField(
        label="Lüftungsart",
        choices=[
            ("natural", "Natürliche Lüftung"),
            ("technical_dilution", "Technische Lüftung (Verdünnung)"),
            ("local_exhaust", "Objektabsaugung"),
            ("inertization", "Inertisierung"),
            ("none", "Keine Lüftung"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "hx-get": "",         # wird per template gesetzt
                "hx-trigger": "change",
                "hx-target": "#zone-proposal",
                "hx-include": "[name=release_grade]",
            }
        ),
    )
    ventilation_notes = forms.CharField(
        required=False,
        label="Lüftungsdetails / Nachweis",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    justification = forms.CharField(
        required=False,
        label="Begründung der Zoneneinteilung",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Wird aus dem Zonenvorschlag vorausgefüllt – kann überschrieben werden.",
            }
        ),
    )
    trgs_reference_id = forms.UUIDField(
        required=False,
        label="Normativer Nachweis (TRGS)",
        widget=forms.HiddenInput(),
    )


class MeasureForm(forms.Form):
    """Formular für eine Schutzmaßnahme."""

    category = forms.ChoiceField(
        label="Kategorie",
        choices=[
            ("primary", "Primär (Vermeidung ex. Atmosphäre)"),
            ("secondary", "Sekundär (Zündquellenvermeidung)"),
            ("constructive", "Konstruktiv (Schadensminimierung)"),
            ("organisational", "Organisatorisch"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    title = forms.CharField(
        max_length=300,
        label="Maßnahme",
        widget=forms.TextInput(attrs={"placeholder": "z.B. Erstinertisierung N₂-Spülung"}),
    )
    description = forms.CharField(
        label="Beschreibung",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": (
                    "Technische Details, Parameter, Grenzwerte … "
                    "z.B. 'N₂-Spülung der Quarzglasglocke, 10 min, MFC-überwacht, "
                    "Durchfluss ≥ X l/min'"
                ),
            }
        ),
    )
    justification = forms.CharField(
        required=False,
        label="Begründung / Nachweis",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    status = forms.ChoiceField(
        label="Status",
        choices=ProtectionMeasure.Status.choices,
        initial="done",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    catalog_reference_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(),
    )


class EquipmentForm(forms.Form):
    """Formular für ein Betriebsmittel."""

    name = forms.CharField(max_length=300, label="Bezeichnung")
    inventory_number = forms.CharField(
        required=False, max_length=100, label="Inventarnummer"
    )
    serial_number = forms.CharField(
        required=False, max_length=100, label="Seriennummer"
    )
    manufacturer = forms.CharField(
        required=False, max_length=200, label="Hersteller"
    )
    atex_marking_override = forms.CharField(
        required=False,
        max_length=100,
        label="ATEX-Kennzeichnung (manuell)",
        help_text="Nur ausfüllen wenn abweichend vom Gerätetyp-Katalog",
    )
    equipment_type_id = forms.UUIDField(
        required=False,
        label="Gerätetyp",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    inspection_interval_months = forms.IntegerField(
        required=False,
        label="Prüfintervall [Monate]",
        min_value=1,
        max_value=120,
    )
    first_inspection_date = forms.DateField(
        required=False,
        label="Datum der Erstprüfung",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


class InspectionForm(forms.Form):
    """Formular für eine Prüfaufzeichnung."""

    inspection_type = forms.ChoiceField(
        label="Prüfart",
        choices=Inspection.InspectionType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    scheduled_date = forms.DateField(
        label="Fälligkeitsdatum",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    performed_date = forms.DateField(
        required=False,
        label="Durchführungsdatum",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    external_inspector = forms.CharField(
        required=False,
        max_length=200,
        label="Externe Prüforganisation",
        widget=forms.TextInput(attrs={"placeholder": "z.B. TÜV Süd GmbH"}),
    )
    result = forms.ChoiceField(
        required=False,
        label="Ergebnis",
        choices=[("", "—")] + list(Inspection.Result.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    findings = forms.CharField(
        required=False,
        label="Mängel / Feststellungen",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    corrective_actions = forms.CharField(
        required=False,
        label="Abstellmaßnahmen",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    next_inspection_date = forms.DateField(
        required=False,
        label="Nächste Prüfung",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


# Formset-Alias für Zündquellenbewertung
IgnitionAssessmentFormSet = None  # Wird dynamisch in view erzeugt
