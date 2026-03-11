"""Tests for module catalogue (ADR-137 Phase 3)."""

import uuid

import pytest
from django.test import override_settings

from django_module_shop.catalogue import (
    enrich_catalogue,
    get_catalogue,
    get_module_entry,
)


class TestGetCatalogue:
    def test_should_return_configured_catalogue(self):
        cat = get_catalogue()
        assert "risk" in cat
        assert cat["risk"]["name"] == "Risikobewertung"

    def test_should_return_empty_when_not_configured(self):
        with override_settings(MODULE_SHOP_CATALOGUE={}):
            assert get_catalogue() == {}


class TestGetModuleEntry:
    def test_should_return_entry(self):
        entry = get_module_entry("risk")
        assert entry is not None
        assert entry["standalone_bookable"] is True

    def test_should_return_none_for_unknown(self):
        assert get_module_entry("nonexistent") is None


@pytest.mark.django_db
class TestEnrichCatalogue:
    def test_should_return_all_modules(self):
        tid = uuid.uuid4()
        result = enrich_catalogue(tid, "starter")
        codes = [m["code"] for m in result]
        assert "risk" in codes
        assert "locked" in codes

    def test_should_mark_bookable_as_available(self):
        tid = uuid.uuid4()
        result = enrich_catalogue(tid, "starter")
        risk = next(m for m in result if m["code"] == "risk")
        assert risk["status"] == "available"
        assert risk["is_bookable"] is True

    def test_should_mark_non_bookable_as_locked(self):
        tid = uuid.uuid4()
        result = enrich_catalogue(tid, "starter")
        locked = next(m for m in result if m["code"] == "locked")
        assert locked["status"] == "locked"
        assert locked["is_bookable"] is False

    def test_should_mark_included_in_plan(self):
        tid = uuid.uuid4()
        result = enrich_catalogue(tid, "professional")
        risk = next(m for m in result if m["code"] == "risk")
        # risk is in professional plan but no subscription
        assert risk["included_in_plan"] is True

    def test_should_sort_active_first(self):
        tid = uuid.uuid4()
        result = enrich_catalogue(tid, "starter")
        statuses = [m["status"] for m in result]
        order = {
            "active": 0,
            "included": 1,
            "available": 2,
            "locked": 3,
        }
        values = [order[s] for s in statuses]
        assert values == sorted(values)
