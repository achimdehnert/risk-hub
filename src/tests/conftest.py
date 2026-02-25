# src/tests/conftest.py — ADR-058 §Confirmation
import uuid
import pytest

# Shared platform fixtures (platform-context[testing])
from platform_context.testing.fixtures import (  # noqa: F401
    admin_client,
    htmx_client,
)

# Repo-specific fixtures (risk-hub uses UserFactory + tenant_id)
@pytest.fixture
def tenant_id():
    """A fixed tenant UUID for multi-tenant tests."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def user(db):
    """Standard authenticated user."""
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Admin user with superuser rights."""
    from tests.factories import UserFactory
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def auth_client(client, user):
    """Pre-authenticated Django test client."""
    client.force_login(user)
    return client
