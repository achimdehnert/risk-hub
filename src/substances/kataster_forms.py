# src/substances/kataster_forms.py
"""Django Forms für das Gefahrstoffkataster (UC-004)."""

from django import forms
from django.db.models import Q

from .models import Party, Product, SubstanceUsage

# Shared Tailwind CSS classes
_INPUT = "block w-full rounded-md border-gray-300 shadow-sm focus:ring-orange-500 focus:border-orange-500 text-sm"
_SELECT = _INPUT
_TEXTAREA = _INPUT
_CHECKBOX = "rounded border-gray-300 text-orange-600 focus:ring-orange-500"


class ProductForm(forms.ModelForm):
    """Form für Handelsprodukt-Erstellung/-Bearbeitung."""

    class Meta:
        model = Product
        fields = [
            "trade_name",
            "manufacturer",
            "supplier",
            "material_number",
            "status",
            "description",
        ]
        widgets = {
            "trade_name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Produktname / Handelsname"}),
            "manufacturer": forms.Select(attrs={"class": _SELECT}),
            "supplier": forms.Select(attrs={"class": _SELECT}),
            "material_number": forms.TextInput(attrs={"class": _INPUT, "placeholder": "z.B. MAT-12345"}),
            "status": forms.Select(attrs={"class": _SELECT}),
            "description": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 3, "placeholder": "Beschreibung / Verwendungszweck"}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id
        if tenant_id:
            self.fields["manufacturer"].queryset = Party.objects.filter(
                Q(tenant_id=tenant_id), party_type="manufacturer"
            )
            self.fields["supplier"].queryset = Party.objects.filter(
                Q(tenant_id=tenant_id), party_type="supplier"
            )
        self.fields["manufacturer"].required = False
        self.fields["supplier"].required = False


class SubstanceUsageForm(forms.ModelForm):
    """Form für Gefahrstoff-Verwendung."""

    class Meta:
        model = SubstanceUsage
        fields = [
            "product",
            "site",
            "department",
            "usage_description",
            "storage_location",
            "storage_class",
            "aggregate_state",
            "max_storage_qty",
            "max_storage_unit",
            "annual_consumption",
            "annual_consumption_unit",
            "substitution_status",
            "substitution_notes",
            "status",
            "last_reviewed",
            "notes",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": _SELECT}),
            "site": forms.Select(attrs={"class": _SELECT}),
            "department": forms.Select(attrs={"class": _SELECT}),
            "usage_description": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2, "placeholder": "Wofür wird das Produkt verwendet?"}),
            "storage_location": forms.TextInput(attrs={"class": _INPUT, "placeholder": "z.B. Gefahrstofflager Halle 3"}),
            "storage_class": forms.Select(attrs={"class": _SELECT}),
            "aggregate_state": forms.Select(attrs={"class": _SELECT}),
            "max_storage_qty": forms.NumberInput(attrs={"class": _INPUT, "placeholder": "0.000", "step": "0.001"}),
            "max_storage_unit": forms.Select(attrs={"class": _SELECT}),
            "annual_consumption": forms.NumberInput(attrs={"class": _INPUT, "placeholder": "0.000", "step": "0.001"}),
            "annual_consumption_unit": forms.Select(attrs={"class": _SELECT}),
            "substitution_status": forms.Select(attrs={"class": _SELECT}),
            "substitution_notes": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2}),
            "status": forms.Select(attrs={"class": _SELECT}),
            "last_reviewed": forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
            "notes": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2}),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id
        if tenant_id:
            self.fields["product"].queryset = Product.objects.filter(tenant_id=tenant_id).order_by("trade_name")
            from tenancy.models import Department, Site

            self.fields["site"].queryset = Site.objects.filter(tenant_id=tenant_id, is_active=True).order_by("name")
            self.fields["department"].queryset = Department.objects.filter(tenant_id=tenant_id).order_by("name")
        self.fields["department"].required = False


class KatasterImportForm(forms.Form):
    """Form für Kataster-Excel-Import."""

    import_file = forms.FileField(
        label="Excel-Datei",
        help_text="Gefahrstoffkataster als .xlsx oder .xls",
        widget=forms.FileInput(attrs={"class": _INPUT, "accept": ".xlsx,.xls"}),
    )

    target_site = forms.IntegerField(
        widget=forms.Select(attrs={"class": _SELECT}),
        label="Ziel-Standort",
    )

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            from tenancy.models import Site

            sites = Site.objects.filter(tenant_id=tenant_id, is_active=True).order_by("name")
            self.fields["target_site"].widget = forms.Select(
                attrs={"class": _SELECT},
                choices=[("", "--- Standort wählen ---")] + [(s.pk, s.name) for s in sites],
            )
