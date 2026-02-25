"""DSB Datenpannen-Workflow Forms (Art. 33 DSGVO)."""

from django import forms

from dsb.models import Mandate
from dsb.models.breach import Breach
from dsb.models.choices import SeverityLevel

_TW_INPUT = (
    "block w-full rounded-md border-gray-300 shadow-sm "
    "focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
)
_TW_SELECT = _TW_INPUT
_TW_TEXTAREA = _TW_INPUT + " h-24"


class BreachCreateForm(forms.ModelForm):
    """Erfassungsmaske für neue Datenpanne (Art. 33 DSGVO)."""

    class Meta:
        model = Breach
        fields = [
            "mandate",
            "title",
            "reported_by_name",
            "reported_by_email",
            "discovered_at",
            "severity",
            "affected_count",
            "root_cause",
            "measures_taken",
            "authority_name",
        ]
        widgets = {
            "mandate": forms.Select(attrs={"class": _TW_SELECT}),
            "title": forms.TextInput(attrs={
                "class": _TW_INPUT,
                "placeholder": "Kurzbeschreibung der Datenpanne",
            }),
            "reported_by_name": forms.TextInput(attrs={
                "class": _TW_INPUT,
                "placeholder": "Name des Meldenden (Firma / Ansprechpartner)",
            }),
            "reported_by_email": forms.EmailInput(attrs={
                "class": _TW_INPUT,
                "placeholder": "E-Mail für Benachrichtigungen",
            }),
            "discovered_at": forms.DateTimeInput(attrs={
                "class": _TW_INPUT,
                "type": "datetime-local",
            }),
            "severity": forms.Select(attrs={"class": _TW_SELECT}),
            "affected_count": forms.NumberInput(attrs={
                "class": _TW_INPUT,
                "placeholder": "Ungefähre Anzahl betroffener Personen",
            }),
            "root_cause": forms.Textarea(attrs={
                "class": _TW_TEXTAREA,
                "placeholder": "Ursache der Datenpanne (soweit bekannt)",
            }),
            "measures_taken": forms.Textarea(attrs={
                "class": _TW_TEXTAREA,
                "placeholder": "Bereits ergriffene Sofortmaßnahmen",
            }),
            "authority_name": forms.TextInput(attrs={
                "class": _TW_INPUT,
                "placeholder": "z.B. LfDI Baden-Württemberg",
            }),
        }

    def __init__(self, *args, tenant_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            qs = Mandate.objects.filter(tenant_id=tenant_id, status="active")
            self.fields["mandate"].queryset = qs
            if qs.count() == 1 and not self.data.get("mandate"):
                self.fields["mandate"].initial = qs.first().pk
        self.fields["authority_name"].required = False
        self.fields["affected_count"].required = False
        self.fields["root_cause"].required = False
        self.fields["measures_taken"].required = False
        self.fields["reported_by_name"].required = False
        self.fields["reported_by_email"].required = False
