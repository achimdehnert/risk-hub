"""Tests for identity models (User, ApiKey)."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_should_create_user_via_manager():
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="securepass123",
    )
    assert user.pk is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.check_password("securepass123")


@pytest.mark.django_db
def test_should_store_tenant_id_on_user():
    import uuid

    tenant_id = uuid.uuid4()
    user = User.objects.create_user(
        username="tenant_user",
        password="pass",
        tenant_id=tenant_id,
    )
    assert user.tenant_id == tenant_id


@pytest.mark.django_db
def test_should_allow_null_tenant_id_on_user():
    user = User.objects.create_user(username="notenant", password="pass")
    assert user.tenant_id is None


@pytest.mark.django_db
def test_should_create_superuser_via_manager():
    user = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )
    assert user.is_superuser is True
    assert user.is_staff is True
