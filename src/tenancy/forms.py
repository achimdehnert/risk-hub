"""Tenancy forms — Organization + Membership management."""

from django import forms
from django.utils.text import slugify

from django_tenancy.module_models import ModuleMembership, ModuleSubscription
from identity.models import User
from tenancy.models import Membership, Organization

_TW_INPUT = (
    "block w-full rounded-md border-gray-300 shadow-sm "
    "focus:border-blue-500 focus:ring-blue-500 sm:text-sm "
    "px-3 py-2 border"
)
_TW_SELECT = _TW_INPUT
_TW_TEXTAREA = _TW_INPUT + " h-24"


class OrganizationForm(forms.ModelForm):
    """Form für Mandanten (Organisationen)."""

    class Meta:
        model = Organization
        fields = [
            "name",
            "slug",
            "status",
            "plan_code",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": _TW_INPUT}),
            "slug": forms.TextInput(
                attrs={"class": _TW_INPUT, "pattern": "[a-z0-9-]+"},
            ),
            "status": forms.Select(attrs={"class": _TW_SELECT}),
            "plan_code": forms.TextInput(attrs={"class": _TW_INPUT}),
        }
        help_texts = {
            "slug": "Subdomain-Prefix, z.B. 'marold' → marold.schutztat.de",
        }

    def clean_slug(self) -> str:
        slug = self.cleaned_data["slug"].lower().strip()
        slug = slugify(slug)
        if not slug:
            raise forms.ValidationError("Slug darf nicht leer sein.")
        qs = Organization.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                f"Slug '{slug}' ist bereits vergeben.",
            )
        return slug


class InviteUserForm(forms.Form):
    """Form zum Einladen eines Users in eine Organisation."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": _TW_INPUT, "placeholder": "Benutzername"},
        ),
        label="Benutzername",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": _TW_INPUT, "placeholder": "E-Mail"},
        ),
        label="E-Mail",
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": _TW_INPUT}),
        label="Vorname",
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": _TW_INPUT}),
        label="Nachname",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": _TW_INPUT, "placeholder": "Passwort"},
        ),
        label="Passwort",
        min_length=8,
    )
    role = forms.ChoiceField(
        choices=Membership.Role.choices,
        initial=Membership.Role.MEMBER,
        widget=forms.Select(attrs={"class": _TW_SELECT}),
        label="Rolle",
    )

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "Benutzername existiert bereits.",
            )
        return username

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "E-Mail-Adresse wird bereits verwendet.",
            )
        return email


class MembershipRoleForm(forms.Form):
    """Form zum Ändern der Rolle eines Mitglieds."""

    role = forms.ChoiceField(
        choices=Membership.Role.choices,
        widget=forms.Select(attrs={"class": _TW_SELECT}),
        label="Rolle",
    )


class ModuleSubscriptionForm(forms.ModelForm):
    """Form zum Bearbeiten einer Modul-Subscription."""

    class Meta:
        model = ModuleSubscription
        fields = ["status", "plan_code", "trial_ends_at", "activated_at", "expires_at"]
        widgets = {
            "status": forms.Select(attrs={"class": _TW_SELECT}),
            "plan_code": forms.TextInput(attrs={"class": _TW_INPUT}),
            "trial_ends_at": forms.DateTimeInput(
                attrs={"class": _TW_INPUT, "type": "datetime-local"}, format="%Y-%m-%dT%H:%M",
            ),
            "activated_at": forms.DateTimeInput(
                attrs={"class": _TW_INPUT, "type": "datetime-local"}, format="%Y-%m-%dT%H:%M",
            ),
            "expires_at": forms.DateTimeInput(
                attrs={"class": _TW_INPUT, "type": "datetime-local"}, format="%Y-%m-%dT%H:%M",
            ),
        }
        labels = {
            "status": "Status",
            "plan_code": "Plan",
            "trial_ends_at": "Trial-Ende",
            "activated_at": "Aktiviert am",
            "expires_at": "Läuft ab am",
        }


class ModuleMembershipGrantForm(forms.Form):
    """Form zum Zuweisen eines Benutzers zu einem Modul."""

    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": _TW_SELECT}),
        label="Benutzer",
    )
    role = forms.ChoiceField(
        choices=ModuleMembership.Role.choices,
        initial=ModuleMembership.Role.MEMBER,
        widget=forms.Select(attrs={"class": _TW_SELECT}),
        label="Modul-Rolle",
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={"class": _TW_INPUT, "type": "datetime-local"}, format="%Y-%m-%dT%H:%M",
        ),
        label="Ablaufdatum (optional)",
    )

    def __init__(self, *args, org=None, module=None, **kwargs):
        super().__init__(*args, **kwargs)
        if org is not None:
            already_granted = ModuleMembership.objects.filter(
                tenant_id=org.tenant_id, module=module,
            ).values_list("user_id", flat=True)
            self.fields["user"].queryset = User.objects.filter(
                tenant_id=org.tenant_id,
            ).exclude(pk__in=already_granted).order_by("username")


class ModuleMembershipRoleForm(forms.Form):
    """Form zum Ändern der Modul-Rolle eines Benutzers."""

    role = forms.ChoiceField(
        choices=ModuleMembership.Role.choices,
        widget=forms.Select(attrs={"class": _TW_SELECT}),
        label="Modul-Rolle",
    )
