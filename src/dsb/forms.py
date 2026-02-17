"""DSB Module Forms (ADR-038)."""

from django import forms

from dsb.models import (
    DataProcessingAgreement,
    Mandate,
    OrganizationalMeasure,
    ProcessingActivity,
    TechnicalMeasure,
)


class MandateForm(forms.ModelForm):
    """Form for creating/editing a Mandate."""

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
            "name": forms.TextInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "industry": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "employee_count": forms.NumberInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "dsb_appointed_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-md border-gray-300"}),
            "contract_end_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-md border-gray-300"}),
            "supervisory_authority": forms.TextInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "status": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
        }


class ProcessingActivityForm(forms.ModelForm):
    """Form for creating/editing a ProcessingActivity (VVT)."""

    class Meta:
        model = ProcessingActivity
        fields = [
            "mandate",
            "number",
            "name",
            "description",
            "legal_basis",
            "risk_level",
            "dsfa_required",
            "purposes",
            "data_categories",
            "data_subjects",
            "recipients",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "number": forms.NumberInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "name": forms.TextInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-md border-gray-300"}),
            "legal_basis": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "risk_level": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "dsfa_required": forms.CheckboxInput(attrs={"class": "rounded border-gray-300"}),
            "purposes": forms.CheckboxSelectMultiple(),
            "data_categories": forms.CheckboxSelectMultiple(),
            "data_subjects": forms.CheckboxSelectMultiple(),
            "recipients": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["mandate"].queryset = Mandate.objects.filter(
                tenant_id=tenant_id, status="active",
            )


class TechnicalMeasureForm(forms.ModelForm):
    """Form for creating/editing a TechnicalMeasure."""

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
            "mandate": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "category": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "title": forms.TextInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-md border-gray-300"}),
            "status": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "review_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-md border-gray-300"}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["mandate"].queryset = Mandate.objects.filter(
                tenant_id=tenant_id, status="active",
            )


class OrganizationalMeasureForm(forms.ModelForm):
    """Form for creating/editing an OrganizationalMeasure."""

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
            "mandate": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "category": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "title": forms.TextInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-md border-gray-300"}),
            "status": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "review_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-md border-gray-300"}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["mandate"].queryset = Mandate.objects.filter(
                tenant_id=tenant_id, status="active",
            )


class DataProcessingAgreementForm(forms.ModelForm):
    """Form for creating/editing a DataProcessingAgreement (AVV)."""

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
            "subprocessors_notes",
            "notes",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "partner_name": forms.TextInput(attrs={"class": "w-full rounded-md border-gray-300"}),
            "partner_role": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "subject_matter": forms.Textarea(attrs={"rows": 3, "class": "w-full rounded-md border-gray-300"}),
            "status": forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
            "effective_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-md border-gray-300"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-md border-gray-300"}),
            "subprocessors_allowed": forms.CheckboxInput(attrs={"class": "rounded border-gray-300"}),
            "subprocessors_notes": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-md border-gray-300"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-md border-gray-300"}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields["mandate"].queryset = Mandate.objects.filter(
                tenant_id=tenant_id, status="active",
            )
