"""DSB Löschungsworkflow — E-Mail-Versand und Status-Transitionen."""

from __future__ import annotations

from datetime import date, timedelta

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from dsb.models.deletion_request import DeletionRequest, DeletionRequestStatus


def _dsb_context(req: DeletionRequest, extra: dict | None = None) -> dict:
    """Gemeinsamer Template-Kontext für alle Löschungs-E-Mails."""
    from dateutil.relativedelta import relativedelta
    deadline = req.request_date + relativedelta(months=1)
    ctx = {
        "request_id": str(req.id)[:8].upper(),
        "subject_name": req.subject_name,
        "subject_email": req.subject_email,
        "subject_reference": req.subject_reference or "—",
        "mandate_name": req.mandate.name,
        "request_date": req.request_date.strftime("%d.%m.%Y"),
        "deadline_date": deadline.strftime("%d.%m.%Y"),
        "data_categories": req.data_categories or req.request_description[:100],
        "request_description": req.request_description,
        "dsb_name": "Datenschutzbeauftragter/in",
        "dsb_email": "datenschutz@schutztat.de",
        "auth_deadline": (date.today() + timedelta(days=14)).strftime("%d.%m.%Y"),
        "auth_received_date": req.auth_received_at.strftime("%d.%m.%Y") if req.auth_received_at else "—",
        "ordered_date": req.deletion_ordered_at.strftime("%d.%m.%Y") if req.deletion_ordered_at else "—",
        "confirmed_date": req.deletion_confirmed_at.strftime("%d.%m.%Y") if req.deletion_confirmed_at else "—",
        "closed_date": req.closed_at.strftime("%d.%m.%Y") if req.closed_at else date.today().strftime("%d.%m.%Y"),
        "deletion_notes": req.deletion_notes,
    }
    if extra:
        ctx.update(extra)
    return ctx


def _send_email(to: str, subject: str, template: str, ctx: dict) -> None:
    """Render HTML template and send as e-mail."""
    html = render_to_string(f"dsb/emails/{template}.html", ctx)
    text = f"{subject}\n\nBitte lesen Sie diese E-Mail in einem HTML-fähigen E-Mail-Client."
    msg = EmailMultiAlternatives(subject=subject, body=text, to=[to])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


STEP_EMAIL_MAP = {
    DeletionRequestStatus.PENDING: (
        "Eingang Ihres Löschantrags — Ref. {ref}",
        "deletion_01_request_received",
    ),
    DeletionRequestStatus.AUTH_SENT: (
        "Identitätsverifizierung erforderlich — Ref. {ref}",
        "deletion_02_auth_request",
    ),
    DeletionRequestStatus.AUTH_RECEIVED: (
        "Identität bestätigt — Löschung wird beauftragt — Ref. {ref}",
        "deletion_03_auth_received",
    ),
    DeletionRequestStatus.DELETION_ORDERED: (
        "Löschung wurde beauftragt — Ref. {ref}",
        "deletion_04_deletion_ordered",
    ),
    DeletionRequestStatus.DELETION_CONFIRMED: (
        "Löschung bestätigt — Ref. {ref}",
        "deletion_05_deletion_confirmed",
    ),
    DeletionRequestStatus.NOTIFIED: (
        "Abschlussbestätigung Ihres Löschantrags — Ref. {ref}",
        "deletion_06_notified",
    ),
}

STEP_TIMESTAMPS = {
    DeletionRequestStatus.AUTH_SENT: "auth_sent_at",
    DeletionRequestStatus.AUTH_RECEIVED: "auth_received_at",
    DeletionRequestStatus.DELETION_ORDERED: "deletion_ordered_at",
    DeletionRequestStatus.DELETION_CONFIRMED: "deletion_confirmed_at",
    DeletionRequestStatus.NOTIFIED: "notified_at",
    DeletionRequestStatus.CLOSED: "closed_at",
}


def advance_workflow(req: DeletionRequest, new_status: str, notes: str = "", send_mail: bool = True) -> None:
    """Advance deletion request to new_status, set timestamp, send e-mail."""
    req.status = new_status

    ts_field = STEP_TIMESTAMPS.get(new_status)
    if ts_field:
        setattr(req, ts_field, timezone.now())

    if new_status == DeletionRequestStatus.CLOSED:
        req.closed_at = timezone.now()

    if notes:
        if new_status in (DeletionRequestStatus.AUTH_SENT, DeletionRequestStatus.AUTH_RECEIVED):
            req.auth_notes = notes
        elif new_status in (DeletionRequestStatus.DELETION_ORDERED, DeletionRequestStatus.DELETION_CONFIRMED):
            req.deletion_notes = notes
        elif new_status == DeletionRequestStatus.REJECTED:
            req.rejection_reason = notes

    req.save()

    if send_mail and new_status in STEP_EMAIL_MAP:
        subject_tpl, template = STEP_EMAIL_MAP[new_status]
        ref = str(req.id)[:8].upper()
        ctx = _dsb_context(req)
        try:
            _send_email(req.subject_email, subject_tpl.format(ref=ref), template, ctx)
        except Exception:
            pass  # Mail-Fehler nicht den Workflow blockieren lassen


def send_initial_confirmation(req: DeletionRequest) -> None:
    """Send step-1 confirmation immediately after creation."""
    subject_tpl, template = STEP_EMAIL_MAP[DeletionRequestStatus.PENDING]
    ref = str(req.id)[:8].upper()
    ctx = _dsb_context(req)
    try:
        _send_email(req.subject_email, subject_tpl.format(ref=ref), template, ctx)
    except Exception:
        pass
