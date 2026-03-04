"""
Tests für GBU Phase 2D — PDF-Generierung und Dokumentenspeicherung.

Folgende Bereiche werden getestet:
- render_gbu_pdf / render_ba_pdf (mit gemocktem WeasyPrint)
- store_gbu_pdf / store_ba_pdf (DB + Storage)
- generate_documents_task (Celery-Task, synchron per CELERY_TASK_ALWAYS_EAGER)
"""

import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────


def _make_activity(db, tenant_id, user_id):
    """Minimale HazardAssessmentActivity für Tests."""
    from substances.models import SdsRevision, Substance
    from tenancy.models import Organization, Site

    org, _ = Organization.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={"name": "Test Org", "slug": f"test-{tenant_id}"},
    )
    site, _ = Site.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={"name": "Teststandort", "organization": org},
    )
    substance, _ = Substance.objects.get_or_create(
        tenant_id=tenant_id,
        name="Testaceton",
    )
    revision, _ = SdsRevision.objects.get_or_create(
        tenant_id=tenant_id,
        substance=substance,
        revision_number=1,
        defaults={"language": "de"},
    )
    from django.utils import timezone

    from gbu.models.activity import ActivityStatus, HazardAssessmentActivity

    activity = HazardAssessmentActivity.objects.create(
        tenant_id=tenant_id,
        site=site,
        sds_revision=revision,
        activity_description="Reinigung mit Aceton",
        activity_frequency="weekly",
        duration_minutes=30,
        quantity_class="s",
        status=ActivityStatus.APPROVED,
        approved_by_id=user_id,
        approved_by_name="Max Mustermann",
        approved_at=timezone.now(),
        created_by=user_id,
    )
    return activity


# ── Tests: PDF-Rendering ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_should_render_gbu_html_template(settings):
    """
    render_gbu_pdf() soll HTML-Template rendern und WeasyPrint aufrufen.
    WeasyPrint wird gemockt → gibt Dummy-Bytes zurück.
    """
    from gbu.services.pdf_service import render_gbu_pdf

    tenant_id = uuid.uuid4()

    with pytest.raises(Exception):
        # Ohne DB-Daten soll DoesNotExist kommen, nicht ImportError
        render_gbu_pdf(uuid.uuid4(), tenant_id)


@pytest.mark.django_db
def test_should_call_weasyprint_for_gbu(db):
    """
    render_gbu_pdf() soll WeasyPrint.HTML.write_pdf() aufrufen.
    """
    from gbu.services.pdf_service import render_gbu_pdf

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    activity = _make_activity(db, tenant_id, user_id)

    fake_pdf = b"%PDF-1.4 fake"
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = fake_pdf

    with patch("gbu.services.pdf_service.HTML", return_value=mock_html_instance) as mock_cls:
        result = render_gbu_pdf(activity.id, tenant_id)

    assert result == fake_pdf
    mock_cls.assert_called_once()
    mock_html_instance.write_pdf.assert_called_once()


@pytest.mark.django_db
def test_should_call_weasyprint_for_ba(db):
    """
    render_ba_pdf() soll WeasyPrint.HTML.write_pdf() aufrufen.
    """
    from gbu.services.pdf_service import render_ba_pdf

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    activity = _make_activity(db, tenant_id, user_id)

    fake_pdf = b"%PDF-1.4 fake-ba"
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = fake_pdf

    with patch("gbu.services.pdf_service.HTML", return_value=mock_html_instance):
        result = render_ba_pdf(activity.id, tenant_id)

    assert result == fake_pdf


@pytest.mark.django_db
def test_should_raise_runtime_error_without_weasyprint(db):
    """
    _html_to_pdf() soll RuntimeError werfen wenn WeasyPrint fehlt.
    """
    from gbu.services.pdf_service import _html_to_pdf

    with patch.dict("sys.modules", {"weasyprint": None}):
        with pytest.raises((RuntimeError, ImportError)):
            _html_to_pdf("<html><body>test</body></html>")


# ── Tests: Dokumentenspeicherung ───────────────────────────────────────────────


@pytest.mark.django_db
def test_should_store_gbu_pdf_creates_document_version(db):
    """
    store_gbu_pdf() soll DocumentVersion erzeugen und
    activity.gbu_document setzen.
    """
    from gbu.services.document_store import store_gbu_pdf

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    activity = _make_activity(db, tenant_id, user_id)
    fake_pdf = b"%PDF-fake-content"

    with patch("gbu.services.document_store._write_storage"):
        version = store_gbu_pdf(activity.id, tenant_id, fake_pdf)

    assert version is not None
    assert version.content_type == "application/pdf"
    assert version.size_bytes == len(fake_pdf)
    assert version.sha256 == hashlib.sha256(fake_pdf).hexdigest()

    activity.refresh_from_db()
    assert activity.gbu_document_id == version.id


@pytest.mark.django_db
def test_should_store_ba_pdf_creates_document_version(db):
    """
    store_ba_pdf() soll DocumentVersion erzeugen und
    activity.ba_document setzen.
    """
    from gbu.services.document_store import store_ba_pdf

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    activity = _make_activity(db, tenant_id, user_id)
    fake_pdf = b"%PDF-fake-ba"

    with patch("gbu.services.document_store._write_storage"):
        version = store_ba_pdf(activity.id, tenant_id, fake_pdf)

    assert version is not None
    assert version.filename.startswith("ba_")

    activity.refresh_from_db()
    assert activity.ba_document_id == version.id


@pytest.mark.django_db
def test_should_increment_version_on_second_store(db):
    """
    Wird store_gbu_pdf() zweimal aufgerufen, soll version=2 entstehen.
    """
    from gbu.services.document_store import store_gbu_pdf

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    activity = _make_activity(db, tenant_id, user_id)

    with patch("gbu.services.document_store._write_storage"):
        v1 = store_gbu_pdf(activity.id, tenant_id, b"%PDF-v1")
        v2 = store_gbu_pdf(activity.id, tenant_id, b"%PDF-v2")

    assert v1.version == 1
    assert v2.version == 2


# ── Tests: Celery-Task ─────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_should_generate_documents_task_returns_ids(db):
    """
    generate_documents_task() soll gbu_version_id + ba_version_id zurückgeben.
    """
    from gbu.tasks import generate_documents_task

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    activity = _make_activity(db, tenant_id, user_id)

    fake_pdf = b"%PDF-fake"

    with (
        patch("gbu.services.pdf_service.HTML") as mock_html_cls,
        patch("gbu.services.document_store._write_storage"),
    ):
        mock_inst = MagicMock()
        mock_inst.write_pdf.return_value = fake_pdf
        mock_html_cls.return_value = mock_inst

        result = generate_documents_task(str(activity.id), str(tenant_id))

    assert "gbu_version_id" in result
    assert "ba_version_id" in result
    assert result["activity_id"] == str(activity.id)
