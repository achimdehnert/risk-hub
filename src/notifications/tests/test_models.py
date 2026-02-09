"""Tests for notification models."""

import uuid

import pytest

from notifications.models import Notification, NotificationPreference


TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest.mark.django_db
class TestNotification:
    """Test Notification model."""

    def test_should_create_notification(self):
        n = Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.INSPECTION_DUE,
            severity=Notification.Severity.WARNING,
            title="Prüfung fällig",
            message="Equipment XYZ",
        )
        assert n.pk is not None
        assert n.is_read is False
        assert n.severity == "warning"

    def test_should_default_to_info_severity(self):
        n = Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.SYSTEM,
            title="Test",
        )
        assert n.severity == Notification.Severity.INFO

    def test_should_mark_read(self):
        n = Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.SYSTEM,
            title="Test",
        )
        assert n.is_read is False
        n.mark_read()
        n.refresh_from_db()
        assert n.is_read is True
        assert n.read_at is not None

    def test_should_not_update_already_read(self):
        n = Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.SYSTEM,
            title="Test",
        )
        n.mark_read()
        first_read_at = n.read_at
        n.mark_read()
        assert n.read_at == first_read_at

    def test_should_order_by_newest_first(self):
        _n1 = Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.SYSTEM,
            title="First",
        )
        n2 = Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.SYSTEM,
            title="Second",
        )
        qs = Notification.objects.filter(tenant_id=TENANT_ID)
        assert list(qs)[0].pk == n2.pk

    def test_should_filter_by_tenant(self):
        other_tenant = uuid.uuid4()
        Notification.objects.create(
            tenant_id=TENANT_ID,
            category=Notification.Category.SYSTEM,
            title="Mine",
        )
        Notification.objects.create(
            tenant_id=other_tenant,
            category=Notification.Category.SYSTEM,
            title="Other",
        )
        qs = Notification.objects.filter(tenant_id=TENANT_ID)
        assert qs.count() == 1


@pytest.mark.django_db
class TestNotificationPreference:
    """Test NotificationPreference model."""

    def test_should_create_preference(self):
        pref = NotificationPreference.objects.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            category=Notification.Category.INSPECTION_DUE,
            channel=NotificationPreference.Channel.EMAIL,
            reminder_days=[30, 7, 1],
        )
        assert pref.pk is not None
        assert pref.channel == "email"
        assert pref.reminder_days == [30, 7, 1]

    def test_should_enforce_unique_per_user_category(self):
        NotificationPreference.objects.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            category=Notification.Category.SYSTEM,
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            NotificationPreference.objects.create(
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                category=Notification.Category.SYSTEM,
            )
