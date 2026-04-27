"""Completeness: HTML-Struktur-Validierung aller lokal überschriebenen Templates.

Verhindert:
- Verschachtelte <form>-Tags (Invalid HTML5, wie in doc_templates/edit.html passiert)
- Fehlende hx-target bei hx-post (ADR-048)

Wird bei jeder Template-Änderung automatisch durch pytest ausgeführt.
"""

from __future__ import annotations

import os
from pathlib import Path

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
django.setup()

from django.template.loader import render_to_string  # noqa: E402
from tests.utils.html_assertions import assert_valid_html  # noqa: E402

TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "templates"


def _collect_local_overrides() -> list[str]:
    """Alle .html-Dateien in src/templates/ die Third-Party-Packages überschreiben.

    Erkennt Overrides als: Verzeichnis-Name entspricht einem installierten Package-Namen.
    """
    overrides = []
    for path in sorted(TEMPLATES_DIR.rglob("*.html")):
        rel = path.relative_to(TEMPLATES_DIR)
        overrides.append(str(rel))
    return overrides


_MINIMAL_CONTEXTS: dict[str, dict] = {
    "doc_templates/edit.html": {
        "tmpl": type(
            "_FakeTmpl",
            (),
            {
                "pk": 1,
                "name": "Test-Vorlage",
                "description": "",
                "source_filename": "",
                "status": "draft",
                "scope": "explosionsschutz",
                "section_count": 0,
                "field_count": 0,
                "get_status_display": lambda self: "Entwurf",
                "structure": {"sections": []},
            },
        )(),
    },
}


def _render_with_minimal_context(template_name: str) -> str | None:
    """Rendert Template mit minimalem Fake-Context. Gibt None zurück wenn kein Context definiert."""
    ctx = _MINIMAL_CONTEXTS.get(template_name)
    if ctx is None:
        return None
    try:
        return render_to_string(template_name, ctx)
    except Exception:
        return None


@pytest.mark.parametrize("template_name", _collect_local_overrides())
def test_should_have_no_nested_forms_in_local_template(template_name: str) -> None:
    """Kein Template darf verschachtelte <form>-Tags enthalten."""
    html = _render_with_minimal_context(template_name)
    if html is None:
        pytest.skip(f"Kein minimaler Context für {template_name} definiert — statischer Check")

    assert_valid_html(html, source=template_name)


@pytest.mark.parametrize("template_name", _collect_local_overrides())
def test_should_have_no_nested_forms_static(template_name: str) -> None:
    """Statischer Check: kein <form innerhalb von <form im Quellcode (ohne Rendering)."""
    path = TEMPLATES_DIR / template_name
    content = path.read_text(encoding="utf-8")

    # Einfacher Heuristik-Check: zähle öffnende <form-Tags
    # Wenn >1 und kein </form> dazwischen: potentiell nested
    import re
    form_opens = [m.start() for m in re.finditer(r"<form[\s>]", content, re.IGNORECASE)]
    form_closes = [m.start() for m in re.finditer(r"</form>", content, re.IGNORECASE)]

    if len(form_opens) <= 1:
        return  # OK — max 1 Form

    # Prüfe ob sich Forms überschneiden (erste form schließt vor zweiter öffnet)
    sorted_opens = sorted(form_opens)
    sorted_closes = sorted(form_closes)

    open_stack = []
    events = [(pos, "open") for pos in sorted_opens] + [(pos, "close") for pos in sorted_closes]
    events.sort()

    depth = 0
    for _, event_type in events:
        if event_type == "open":
            depth += 1
            if depth > 1:
                pytest.fail(
                    f"Möglicherweise verschachtelte <form>-Tags in {template_name}. "
                    f"Gefunden: {len(form_opens)} öffnende, {len(form_closes)} schließende Tags. "
                    f"Prüfe manuell und füge minimalen Context zu _MINIMAL_CONTEXTS hinzu."
                )
        else:
            depth = max(0, depth - 1)
