"""Training query helpers (ADR-041)."""

from __future__ import annotations


def get_training_topics(tenant_id):
    """Return active TrainingTopics for a tenant."""
    from training.models import TrainingTopic

    return TrainingTopic.objects.filter(tenant_id=tenant_id, is_active=True)


def get_all_training_topics(tenant_id):
    """Return all TrainingTopics for a tenant (incl. inactive)."""
    from training.models import TrainingTopic

    return TrainingTopic.objects.filter(tenant_id=tenant_id)


def get_training_sessions(tenant_id):
    """Return TrainingSessions for a tenant."""
    from training.models import TrainingSession

    return TrainingSession.objects.filter(tenant_id=tenant_id)


def get_topics_with_sessions(tenant_id):
    """Return active topics prefetched with sessions for the dashboard."""
    return get_training_topics(tenant_id).prefetch_related("sessions")


def get_sessions_with_topics(tenant_id):
    """Return sessions with topic related data."""
    from training.models import TrainingSession

    return TrainingSession.objects.filter(tenant_id=tenant_id).select_related("topic")


def get_member_users(tenant_id):
    """Return Users who are members of the tenant org."""
    from identity.models import User
    from tenancy.models import Membership

    member_user_ids = (
        Membership.objects.filter(organization__tenant_id=tenant_id)
        .values_list("user_id", flat=True)
    )
    return User.objects.filter(pk__in=member_user_ids).order_by("username")


def get_users_by_ids(user_ids):
    """Return User queryset for a list of PKs."""
    from identity.models import User

    return User.objects.filter(pk__in=user_ids)
