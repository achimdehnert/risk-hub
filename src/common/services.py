"""Shared service helpers for risk-hub (ADR-041).

Generic CRUD helpers that enforce tenant isolation and audit fields.
All apps should use these instead of calling .save()/.delete() in views.
"""

import logging
from uuid import UUID

from django.db import models
from django.forms import ModelForm

logger = logging.getLogger(__name__)


def save_form(
    form: ModelForm,
    tenant_id: UUID,
    user_id: int | None = None,
    *,
    is_create: bool = True,
) -> models.Model:
    """Save a ModelForm with tenant + audit fields (ADR-041).

    Args:
        form: A valid ModelForm (must pass is_valid() before calling).
        tenant_id: Tenant UUID.
        user_id: Request user pk.
        is_create: True for create, False for update.

    Returns:
        The saved model instance.
    """
    obj = form.save(commit=False)
    if is_create:
        obj.tenant_id = tenant_id
        if user_id and hasattr(obj, "created_by_id"):
            obj.created_by_id = user_id
    else:
        if user_id and hasattr(obj, "updated_by_id"):
            obj.updated_by_id = user_id
    obj.save()
    form.save_m2m()
    return obj


def delete_object(obj: models.Model) -> None:
    """Delete a model instance (ADR-041 — centralised delete)."""
    obj.delete()
