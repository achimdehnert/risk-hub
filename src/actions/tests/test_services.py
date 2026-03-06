"""Tests für actions/services.py — list_actions, get_action, create_action."""

import uuid
from datetime import date
from unittest.mock import patch

import pytest

from actions.models import ActionItem
from actions.services import CreateActionCmd, create_action, get_action, list_actions

TENANT_ID = uuid.uuid4()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def mock_context():
    """Patch common.context.get_context to return a fixed tenant."""
    from unittest.mock import MagicMock
    ctx = MagicMock()
    ctx.tenant_id = TENANT_ID
    ctx.user = None
    with patch("actions.services.get_context", return_value=ctx):
        with patch("actions.services.require_permission"):
            yield ctx


@pytest.fixture
def fixture_action(db, mock_context):
    return ActionItem.objects.create(
        tenant_id=TENANT_ID,
        title="Test Maßnahme",
        status="open",
        priority=2,
    )


@pytest.mark.django_db
class TestListActions:
    def test_returns_list(self, mock_context, fixture_action):
        result = list_actions()
        assert isinstance(result, list)
        assert any(a.id == fixture_action.id for a in result)

    def test_no_tenant_raises(self):
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.tenant_id = None
        with patch("actions.services.get_context", return_value=ctx):
            with patch("actions.services.require_permission"):
                with pytest.raises(ValueError, match="Tenant required"):
                    list_actions()

    def test_limit_offset(self, mock_context, fixture_action):
        result = list_actions(limit=10, offset=0)
        assert len(result) <= 10


@pytest.mark.django_db
class TestGetAction:
    def test_returns_action(self, mock_context, fixture_action):
        result = get_action(fixture_action.id)
        assert result.id == fixture_action.id
        assert result.title == "Test Maßnahme"

    def test_wrong_tenant_raises(self, mock_context):
        other_id = uuid.uuid4()
        with pytest.raises(ActionItem.DoesNotExist):
            get_action(other_id)

    def test_no_tenant_raises(self):
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.tenant_id = None
        with patch("actions.services.get_context", return_value=ctx):
            with patch("actions.services.require_permission"):
                with pytest.raises(ValueError, match="Tenant required"):
                    get_action(uuid.uuid4())


@pytest.mark.django_db
class TestCreateAction:
    def test_creates_action(self, mock_context):
        cmd = CreateActionCmd(
            title="Neue Maßnahme",
            description="Beschreibung",
            status="open",
            priority=1,
            due_date=date.today(),
        )
        action = create_action(cmd)
        assert action.pk is not None
        assert action.title == "Neue Maßnahme"
        assert action.tenant_id == TENANT_ID

    def test_title_stripped(self, mock_context):
        cmd = CreateActionCmd(title="  Leerzeichen  ")
        action = create_action(cmd)
        assert action.title == "Leerzeichen"

    def test_no_tenant_raises(self):
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.tenant_id = None
        with patch("actions.services.get_context", return_value=ctx):
            with patch("actions.services.require_permission"):
                with pytest.raises(ValueError, match="Tenant required"):
                    create_action(CreateActionCmd(title="x"))
