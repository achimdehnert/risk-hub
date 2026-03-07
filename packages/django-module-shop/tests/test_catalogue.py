"""Tests for django_module_shop.catalogue."""

from django_module_shop.catalogue import (
    ModuleDefinition,
    get_catalogue,
    get_module,
    get_modules_by_category,
)


def test_get_catalogue_returns_all_modules():
    cat = get_catalogue()
    assert set(cat.keys()) == {"risk", "dsb", "ex"}


def test_module_definition_fields():
    cat = get_catalogue()
    risk = cat["risk"]
    assert risk.code == "risk"
    assert risk.name == "Risikobewertung"
    assert risk.price_month == 29.0
    assert risk.price_year == 290.0
    assert risk.category == "safety"
    assert risk.dependencies == []


def test_get_module_known():
    mod = get_module("dsb")
    assert mod is not None
    assert mod.code == "dsb"


def test_get_module_unknown():
    assert get_module("nonexistent") is None


def test_is_free_false():
    mod = get_module("risk")
    assert not mod.is_free


def test_is_free_true():
    free_mod = ModuleDefinition(code="core", name="Core", price_month=0.0, price_year=0.0)
    assert free_mod.is_free


def test_yearly_discount_pct():
    # 29 * 12 = 348, year = 290 → discount ≈ 17%
    mod = get_module("risk")
    assert mod.yearly_discount_pct == 17


def test_yearly_discount_zero_if_free():
    mod = ModuleDefinition(code="x", name="X", price_month=0.0, price_year=0.0)
    assert mod.yearly_discount_pct == 0


def test_get_modules_by_category_groups_correctly():
    by_cat = get_modules_by_category()
    assert "safety" in by_cat
    assert "legal" in by_cat
    safety_codes = {m.code for m in by_cat["safety"]}
    assert "risk" in safety_codes
    assert "ex" in safety_codes
    legal_codes = {m.code for m in by_cat["legal"]}
    assert "dsb" in legal_codes
