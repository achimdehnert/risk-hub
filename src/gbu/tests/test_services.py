"""Unit-Tests für GBU-Services (Phase 2A)."""
import datetime
import uuid

import pytest

from gbu.services.gbu_engine import (
    ApproveActivityCmd,
    CreateActivityCmd,
    derive_hazard_categories,
)


def test_should_create_activity_cmd_be_frozen():
    cmd = CreateActivityCmd(
        site_id=uuid.uuid4(),
        sds_revision_id=uuid.uuid4(),
        activity_description="Test",
        activity_frequency="daily",
        duration_minutes=60,
        quantity_class="s",
    )
    with pytest.raises(Exception):
        cmd.duration_minutes = 999  # frozen=True → FrozenInstanceError


def test_should_approve_activity_cmd_use_date_type():
    """M3: next_review_date muss datetime.date sein, kein str."""
    cmd = ApproveActivityCmd(
        activity_id=uuid.uuid4(),
        next_review_date=datetime.date(2027, 3, 1),
    )
    assert isinstance(cmd.next_review_date, datetime.date)


@pytest.mark.django_db
def test_should_derive_hazard_categories_return_empty_for_no_h_codes(mocker):
    """Wenn SdsRevision keine H-Sätze hat, leere Liste zurückgeben."""
    rev_id = uuid.uuid4()

    mock_revision = mocker.MagicMock()
    mock_revision.hazard_statements.values_list.return_value = []

    mocker.patch(
        "gbu.services.gbu_engine.SdsRevision.objects.prefetch_related"
    ).return_value.get.return_value = mock_revision

    result = derive_hazard_categories(rev_id)
    assert result == []
