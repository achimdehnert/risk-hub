"""DSB Datenpannen-Workflow — E-Mail-Versand und Status-Transitionen (Art. 33 DSGVO)."""

from __future__ import annotations

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from dsb.models.breach import Breach, BreachStatus


def _breach_context(breach: Breach, extra: dict | None = None) -> dict:
    """Gemeinsamer Template-Kontext für alle Breach-E-Mails."""
    from datetime import timedelta
    deadline = breach.discovered_at + timedelta(hours=72)
    ctx = {
        "breach_ref": str(breach.id)[:8].upper(),
        "reported_by_name": breach.reported_by_name or "Verantwortliche/r",
        "reported_by_email": breach.reported_by_email,
        "mandate_name": breach.mandate.name,
        "title": breach.title or "Datenpanne",
        "severity": breach.get_severity_display(),
        "discovered_at": breach.discovered_at.strftime("%d.%m.%Y %H:%M"),
        "deadline_72h": deadline.strftime("%d.%m.%Y %H:%M"),
        "authority_name": breach.authority_name or "zuständige Aufsichtsbehörde",
        "authority_reference": breach.authority_reference,
        "dsb_name": "Datenschutzbeauftragter/in",
        "dsb_email": "datenschutz@schutztat.de",
        "dsb_notified_at": breach.dsb_notified_at.strftime("%d.%m.%Y %H:%M") if breach.dsb_notified_at else "—",
        "authority_notified_at": breach.authority_notified_at.strftime("%d.%m.%Y %H:%M") if breach.authority_notified_at else "—",
        "resolved_at": breach.resolved_at.strftime("%d.%m.%Y %H:%M") if breach.resolved_at else "—",
        "closed_at": breach.closed_at.strftime("%d.%m.%Y %H:%M") if breach.closed_at else "—",
        "dsb_notes": breach.dsb_notes,
        "authority_notes": breach.authority_notes,
        "remediation_notes": breach.remediation_notes,
        "resolution_notes": breach.resolution_notes,
    }
    if extra:
        ctx.update(extra)
    return ctx


def _send_email(to: str, subject: str, template: str, ctx: dict) -> None:
    html = render_to_string(f"dsb/emails/{template}.html", ctx)
    text = f"{subject}\n\nBitte lesen Sie diese E-Mail in einem HTML-fähigen E-Mail-Client."
    msg = EmailMultiAlternatives(subject=subject, body=text, to=[to])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


STEP_EMAIL_MAP = {
    BreachStatus.REPORTED: (
        "⚠ Datenpanne gemeldet — Ref. {ref}",
        "breach_01_reported",
        "reported_by_email",
    ),
    BreachStatus.DSB_NOTIFIED: (
        "DSB übernimmt Datenpanne — Ref. {ref}",
        "breach_02_dsb_notified",
        "reported_by_email",
    ),
    BreachStatus.AUTHORITY_NOTIFIED: (
        "✓ Aufsichtsbehörde benachrichtigt — Ref. {ref}",
        "breach_03_authority_notified",
        "reported_by_email",
    ),
    BreachStatus.RESOLVED: (
        "✓ Datenpanne behoben — Abschlussmeldung folgt — Ref. {ref}",
        "breach_04_resolved",
        "reported_by_email",
    ),
    BreachStatus.CLOSED: (
        "✓ Datenpannen-Verfahren abgeschlossen — Ref. {ref}",
        "breach_05_closed",
        "reported_by_email",
    ),
}

STEP_TIMESTAMPS = {
    BreachStatus.DSB_NOTIFIED: "dsb_notified_at",
    BreachStatus.AUTHORITY_NOTIFIED: "authority_notified_at",
    BreachStatus.REMEDIATION: "remediation_started_at",
    BreachStatus.RESOLVED: "resolved_at",
    BreachStatus.AUTHORITY_CLOSED: "authority_closed_at",
    BreachStatus.CLOSED: "closed_at",
}


def advance_breach_workflow(
    breach: Breach,
    new_status: str,
    notes: str = "",
    authority_name: str = "",
    authority_reference: str = "",
    send_mail: bool = True,
) -> None:
    """Advance breach to new_status, set timestamp, optionally send e-mail."""
    breach.workflow_status = new_status

    ts_field = STEP_TIMESTAMPS.get(new_status)
    if ts_field:
        setattr(breach, ts_field, timezone.now())

    if notes:
        if new_status == BreachStatus.DSB_NOTIFIED:
            breach.dsb_notes = notes
        elif new_status == BreachStatus.AUTHORITY_NOTIFIED:
            breach.authority_notes = notes
        elif new_status == BreachStatus.REMEDIATION:
            breach.remediation_notes = notes
        elif new_status in (BreachStatus.RESOLVED, BreachStatus.AUTHORITY_CLOSED):
            breach.resolution_notes = notes

    if authority_name:
        breach.authority_name = authority_name
    if authority_reference:
        breach.authority_reference = authority_reference

    # Sync reported_to_authority_at for legacy is_overdue check
    if new_status == BreachStatus.AUTHORITY_NOTIFIED:
        breach.reported_to_authority_at = timezone.now()

    breach.save()

    if send_mail and new_status in STEP_EMAIL_MAP:
        subject_tpl, template, email_field = STEP_EMAIL_MAP[new_status]
        ref = str(breach.id)[:8].upper()
        to = getattr(breach, email_field, "")
        if to:
            ctx = _breach_context(breach)
            try:
                _send_email(to, subject_tpl.format(ref=ref), template, ctx)
            except Exception:
                pass


def send_initial_breach_confirmation(breach: Breach) -> None:
    """Send step-1 confirmation immediately after creation."""
    if not breach.reported_by_email:
        return
    subject_tpl, template, _ = STEP_EMAIL_MAP[BreachStatus.REPORTED]
    ref = str(breach.id)[:8].upper()
    ctx = _breach_context(breach)
    try:
        _send_email(breach.reported_by_email, subject_tpl.format(ref=ref), template, ctx)
    except Exception:
        pass
