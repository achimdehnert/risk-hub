"""DSB Löschungsworkflow Forms."""

from django import forms

from dsb.models import Mandate
from dsb.models.deletion_request import DeletionRequest

_TW_INPUT = (
    "block w-full rounded-md border-gray-300 shadow-sm "
    "focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
)
_TW_SELECT = _TW_INPUT
_TW_TEXTAREA = _TW_INPUT + " h-24"


class DeletionRequestForm(forms.ModelForm):
    """Formular für neuen Löschantrag (Art. 17 DSGVO)."""

    class Meta:
        model = DeletionRequest
        fields = [
            "mandate",
            "subject_name",
            "subject_email",
            "subject_reference",
            "request_date",
            "request_description",
            "data_categories",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": _TW_SELECT}),
            "subject_name": forms.TextInput(attrs={"class": _TW_INPUT, "placeholder": "Max Mustermann"}),
            "subject_email": forms.EmailInput(attrs={"class": _TW_INPUT, "placeholder": "max@beispiel.de"}),
            "subject_reference": forms.TextInput(attrs={"class": _TW_INPUT, "placeholder": "Kundennr. / Referenz (optional)"}),
            "request_date": forms.DateInput(attrs={"class": _TW_INPUT, "type": "date"}),
            "request_description": forms.Textarea(attrs={
                "class": _TW_TEXTAREA,
                "placeholder": "Welche Daten sollen gelöscht werden? Wo wurden diese gespeichert?",
            }),
            "data_categories": forms.TextInput(attrs={
                "class": _TW_INPUT,
                "placeholder": "z.B. Stammdaten, Kontaktdaten, Kaufhistorie",
            }),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            qs = Mandate.objects.filter(tenant_id=tenant_id, status="active")
            self.fields["mandate"].queryset = qs
            if qs.count() == 1 and not self.data.get("mandate"):
                self.fields["mandate"].initial = qs.first().pk
