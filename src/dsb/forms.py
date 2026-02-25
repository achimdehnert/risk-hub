"""DSB Module Forms (ADR-038 Phase 1)."""

from django import forms

from dsb.models import (
    DataProcessingAgreement,
    Mandate,
    OrganizationalMeasure,
    ProcessingActivity,
    TechnicalMeasure,
)

_TW_INPUT = (
    "block w-full rounded-md border-gray-300 shadow-sm "
    "focus:border-blue-500 focus:ring-blue-500 sm:text-sm "
    "px-3 py-2 border"
)
_TW_SELECT = _TW_INPUT
_TW_TEXTAREA = _TW_INPUT + " h-24"
_TW_CHECKBOX = "rounded border-gray-300 text-blue-600 focus:ring-blue-500"


def _apply_mandate_autoselect(form, tenant_id):
    """Filter mandate queryset and auto-select if only one exists."""
    if not tenant_id:
        return
    qs = Mandate.objects.filter(tenant_id=tenant_id, status="active")
    form.fields["mandate"].queryset = qs
    if qs.count() == 1 and not form.initial.get("mandate") and not form.data.get("mandate"):
        form.fields["mandate"].initial = qs.first().pk
        form.fields["mandate"].required = True


class MandateForm(forms.ModelForm):
    """Form f\u00fcr Mandate (betreutes Unternehmen)."""

    class Meta:
        model = Mandate
        fields = [
            "name",
            "industry",
            "employee_count",
            "dsb_appointed_date",
            "contract_end_date",
            "supervisory_authority",
            "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": _TW_INPUT}),
            "industry": forms.Select(attrs={"class": _TW_SELECT}),
            "employee_count": forms.NumberInput(
                attrs={"class": _TW_INPUT},
            ),
            "dsb_appointed_date": forms.DateInput(
                attrs={"class": _TW_INPUT, "type": "date"},
            ),
            "contract_end_date": forms.DateInput(
                attrs={"class": _TW_INPUT, "type": "date"},
            ),
            "supervisory_authority": forms.TextInput(
                attrs={"class": _TW_INPUT},
            ),
            "status": forms.Select(attrs={"class": _TW_SELECT}),
        }


class ProcessingActivityForm(forms.ModelForm):
    """Form f\u00fcr VVT-Eintr\u00e4ge (Art. 30)."""

    class Meta:
        model = ProcessingActivity
        fields = [
            "mandate",
            "number",
            "name",
            "description",
            "legal_basis",
            "purposes",
            "data_categories",
            "data_subjects",
            "recipients",
            "risk_level",
            "dsfa_required",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": _TW_SELECT}),
            "number": forms.NumberInput(attrs={"class": _TW_INPUT}),
            "name": forms.TextInput(attrs={"class": _TW_INPUT}),
            "description": forms.Textarea(
                attrs={"class": _TW_TEXTAREA},
            ),
            "legal_basis": forms.Select(
                attrs={"class": _TW_SELECT},
            ),
            "purposes": forms.CheckboxSelectMultiple(),
            "data_categories": forms.CheckboxSelectMultiple(),
            "data_subjects": forms.CheckboxSelectMultiple(),
            "recipients": forms.CheckboxSelectMultiple(),
            "risk_level": forms.Select(
                attrs={"class": _TW_SELECT},
            ),
            "dsfa_required": forms.CheckboxInput(
                attrs={"class": _TW_CHECKBOX},
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_mandate_autoselect(self, tenant_id)


class TechnicalMeasureForm(forms.ModelForm):
    """Form f\u00fcr technische Ma\u00dfnahmen (Art. 32)."""

    class Meta:
        model = TechnicalMeasure
        fields = [
            "mandate",
            "category",
            "title",
            "description",
            "status",
            "review_date",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": _TW_SELECT}),
            "category": forms.Select(attrs={"class": _TW_SELECT}),
            "title": forms.TextInput(attrs={"class": _TW_INPUT}),
            "description": forms.Textarea(
                attrs={"class": _TW_TEXTAREA},
            ),
            "status": forms.Select(attrs={"class": _TW_SELECT}),
            "review_date": forms.DateInput(
                attrs={"class": _TW_INPUT, "type": "date"},
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_mandate_autoselect(self, tenant_id)


class OrganizationalMeasureForm(forms.ModelForm):
    """Form f\u00fcr organisatorische Ma\u00dfnahmen (Art. 32)."""

    class Meta:
        model = OrganizationalMeasure
        fields = [
            "mandate",
            "category",
            "title",
            "description",
            "status",
            "review_date",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": _TW_SELECT}),
            "category": forms.Select(attrs={"class": _TW_SELECT}),
            "title": forms.TextInput(attrs={"class": _TW_INPUT}),
            "description": forms.Textarea(
                attrs={"class": _TW_TEXTAREA},
            ),
            "status": forms.Select(attrs={"class": _TW_SELECT}),
            "review_date": forms.DateInput(
                attrs={"class": _TW_INPUT, "type": "date"},
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_mandate_autoselect(self, tenant_id)


class DataProcessingAgreementForm(forms.ModelForm):
    """Form f\u00fcr AVV (Art. 28)."""

    class Meta:
        model = DataProcessingAgreement
        fields = [
            "mandate",
            "partner_name",
            "partner_role",
            "subject_matter",
            "status",
            "effective_date",
            "expiry_date",
            "subprocessors_allowed",
            "notes",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": _TW_SELECT}),
            "partner_name": forms.TextInput(
                attrs={"class": _TW_INPUT},
            ),
            "partner_role": forms.Select(
                attrs={"class": _TW_SELECT},
            ),
            "subject_matter": forms.Textarea(
                attrs={"class": _TW_TEXTAREA},
            ),
            "status": forms.Select(attrs={"class": _TW_SELECT}),
            "effective_date": forms.DateInput(
                attrs={"class": _TW_INPUT, "type": "date"},
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": _TW_INPUT, "type": "date"},
            ),
            "subprocessors_allowed": forms.CheckboxInput(
                attrs={"class": _TW_CHECKBOX},
            ),
            "notes": forms.Textarea(
                attrs={"class": _TW_TEXTAREA},
            ),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_mandate_autoselect(self, tenant_id)


class CsvImportForm(forms.Form):
    """Upload-Form f\u00fcr VVT / TOM / AVV CSV-Dateien."""

    CSV_TYPE_CHOICES = [
        ("auto", "Automatisch erkennen"),
        ("vvt", "VVT (Verarbeitungst\u00e4tigkeiten)"),
        ("tom", "TOM (Technische & Org. Ma\u00dfnahmen)"),
    ]

    csv_file = forms.FileField(
        label="CSV-Datei",
        help_text=(
            "Semikolon-getrennte CSV (.csv), "
            "generell oder mandantenspezifisch"
        ),
        widget=forms.ClearableFileInput(
            attrs={"class": _TW_INPUT, "accept": ".csv"},
        ),
    )
    csv_type = forms.ChoiceField(
        label="Datentyp",
        choices=CSV_TYPE_CHOICES,
        initial="auto",
        widget=forms.Select(attrs={"class": _TW_SELECT}),
    )
    mandate = forms.ModelChoiceField(
        label="Mandat",
        queryset=Mandate.objects.none(),
        widget=forms.Select(attrs={"class": _TW_SELECT}),
        help_text="Zuordnung zum betreuten Unternehmen",
    )

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not tenant_id:
            return
        qs = Mandate.objects.filter(tenant_id=tenant_id).order_by("name")
        self.fields["mandate"].queryset = qs
        if qs.count() == 1 and not self.data.get("mandate"):
            self.fields["mandate"].initial = qs.first().pk
