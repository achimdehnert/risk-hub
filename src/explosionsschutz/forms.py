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
    Inspection,
    ProtectionMeasure,
    VerificationDocument,
    ZoneDefinition,
)


class AreaForm(forms.ModelForm):
    """Form für Betriebsbereiche"""

    class Meta:
        model = Area
        fields = ["code", "name", "description"]
        labels = {
            "code": "Bereichscode",
            "name": "Bereichsname",
            "description": "Beschreibung",
        }
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

    doc_template_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = ExplosionConcept
        fields = ["project", "area", "title", "substance_name"]
        labels = {
            "project": "Projekt (optional)",
            "area": "Bereich",
            "title": "Titel",
            "substance_name": "Gefahrstoff",
        }
        widgets = {
            "project": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg",
                }
            ),
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
        from projects.models import Project

        self.fields["project"].required = False
        if tenant_id:
            self.fields["area"].queryset = Area.objects.filter(tenant_id=tenant_id)
            self.fields["project"].queryset = Project.objects.filter(
                tenant_id=tenant_id
            ).order_by("name")
        else:
            self.fields["project"].queryset = Project.objects.none()


class ZoneDefinitionForm(forms.ModelForm):
    """Form für Zonendefinitionen"""

    class Meta:
        model = ZoneDefinition
        fields = ["zone_type", "name", "description", "justification"]
        labels = {
            "zone_type": "Zonentyp",
            "name": "Bezeichnung",
            "description": "Beschreibung",
            "justification": "Begründung",
        }
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
        labels = {
            "area": "Bereich",
            "zone": "Zone",
            "equipment_type": "Gerätetyp",
            "serial_number": "Seriennummer",
            "asset_number": "Anlagennummer",
            "installation_date": "Inbetriebnahme",
            "location_detail": "Standort",
        }
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


class ProtectionMeasureForm(forms.ModelForm):
    """Form für Schutzmaßnahmen (HTMX inline add)"""

    class Meta:
        model = ProtectionMeasure
        fields = ["category", "title", "description", "due_date"]
        labels = {
            "category": "Kategorie",
            "title": "Titel",
            "description": "Beschreibung",
            "due_date": "Fälligkeitsdatum",
        }
        widgets = {
            "category": forms.Select(attrs={"class": _INPUT_CSS}),
            "title": forms.TextInput(
                attrs={"class": _INPUT_CSS, "placeholder": "Titel der Maßnahme"}
            ),
            "description": forms.Textarea(
                attrs={"class": _INPUT_CSS, "rows": 2, "placeholder": "Beschreibung..."}
            ),
            "due_date": forms.DateInput(attrs={"class": _INPUT_CSS, "type": "date"}),
        }


class InspectionForm(forms.ModelForm):
    """Form für Prüfungserfassung"""

    class Meta:
        model = Inspection
        fields = [
            "inspection_type",
            "inspection_date",
            "inspector_name",
            "inspector_organization",
            "result",
            "findings",
            "recommendations",
            "certificate_number",
        ]
        widgets = {
            "inspection_type": forms.Select(attrs={"class": _INPUT_CSS}),
            "inspection_date": forms.DateInput(attrs={"class": _INPUT_CSS, "type": "date"}),
            "inspector_name": forms.TextInput(
                attrs={"class": _INPUT_CSS, "placeholder": "Name des Prüfers"}
            ),
            "inspector_organization": forms.TextInput(
                attrs={"class": _INPUT_CSS, "placeholder": "z.B. ZÜS, TÜV"}
            ),
            "result": forms.Select(attrs={"class": _INPUT_CSS}),
            "findings": forms.Textarea(
                attrs={"class": _INPUT_CSS, "rows": 3, "placeholder": "Feststellungen..."}
            ),
            "recommendations": forms.Textarea(
                attrs={"class": _INPUT_CSS, "rows": 2, "placeholder": "Empfehlungen..."}
            ),
            "certificate_number": forms.TextInput(
                attrs={"class": _INPUT_CSS, "placeholder": "Bescheinigungsnummer"}
            ),
        }


class ZoneProposalForm(forms.Form):
    """Form für regelbasierte Zonenvorschlag (TRGS 721 Engine)"""

    RELEASE_GRADE_CHOICES = [
        ("continuous", "Ständig (continuous)"),
        ("primary", "Gelegentlich im Normalbetrieb (primary)"),
        ("secondary", "Selten / nur bei Störung (secondary)"),
    ]

    VENTILATION_CHOICES = [
        ("none", "Keine Lüftung"),
        ("natural", "Natürliche Lüftung"),
        ("technical_dilution", "Technische Lüftung (Verdünnung)"),
        ("local_exhaust", "Objektabsaugung"),
        ("inertization", "Inertisierung"),
    ]

    ATMOSPHERE_CHOICES = [
        ("gas", "Gas/Dampf"),
        ("dust", "Staub"),
    ]

    release_grade = forms.ChoiceField(
        label="Freisetzungsgrad",
        choices=RELEASE_GRADE_CHOICES,
        widget=forms.Select(attrs={"class": _INPUT_CSS}),
    )
    ventilation_type = forms.ChoiceField(
        label="Lüftungsart",
        choices=VENTILATION_CHOICES,
        widget=forms.Select(attrs={"class": _INPUT_CSS}),
    )
    atmosphere_type = forms.ChoiceField(
        label="Atmosphärentyp",
        choices=ATMOSPHERE_CHOICES,
        widget=forms.Select(attrs={"class": _INPUT_CSS}),
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


class VerificationDocumentForm(forms.ModelForm):
    """Form für Nachweisdokumente (HTMX inline add)"""

    class Meta:
        model = VerificationDocument
        fields = ["title", "document_type", "file", "issued_by"]
        labels = {
            "title": "Titel",
            "document_type": "Dokumenttyp",
            "file": "Datei",
            "issued_by": "Ausgestellt von",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT_CSS, "placeholder": "Dokumenttitel"}),
            "document_type": forms.Select(attrs={"class": _INPUT_CSS}),
            "file": forms.ClearableFileInput(
                attrs={"class": _INPUT_CSS, "accept": ".pdf,.jpg,.png,.docx"}
            ),
            "issued_by": forms.TextInput(attrs={"class": _INPUT_CSS, "placeholder": "Aussteller"}),
        }
