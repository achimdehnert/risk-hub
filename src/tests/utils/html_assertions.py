"""HTML structural assertions — immer anwenden nach Template-Änderungen.

Usage in tests:
    from tests.utils.html_assertions import assert_valid_html

    response = client.get("/some-url/")
    assert_valid_html(response.content, source="/some-url/")

Usage in render checks:
    from django.template.loader import render_to_string
    from tests.utils.html_assertions import assert_valid_html

    html = render_to_string("my/template.html", context)
    assert_valid_html(html, source="my/template.html")
"""

from __future__ import annotations

from bs4 import BeautifulSoup


def assert_valid_html(html: str | bytes, *, source: str = "") -> None:
    """Prüft häufige HTML-Strukturfehler. Wirft AssertionError bei Verstößen.

    Checks:
    - Keine verschachtelten <form>-Tags (Invalid HTML5)
    - Jedes <form id="..."> ist eindeutig
    - Jedes hx-post / hx-get hat auch hx-target
    """
    soup = BeautifulSoup(html, "html.parser")
    label = f" [{source}]" if source else ""

    _check_no_nested_forms(soup, label)
    _check_unique_form_ids(soup, label)
    _check_htmx_has_target(soup, label)


def _check_no_nested_forms(soup: BeautifulSoup, label: str) -> None:
    for outer in soup.find_all("form"):
        inner = outer.find("form")
        if inner:
            raise AssertionError(
                f"Verschachtelte <form>-Tags{label}: "
                f"<form id={outer.get('id')!r}> enthält <form id={inner.get('id')!r}>. "
                f"Lösung: innere Form nach außen verschieben + HTML5 form='-Attribut nutzen."
            )


def _check_unique_form_ids(soup: BeautifulSoup, label: str) -> None:
    seen: set[str] = set()
    for form in soup.find_all("form"):
        fid = form.get("id")
        if fid:
            if fid in seen:
                raise AssertionError(
                    f"Doppelte form id={fid!r}{label}. Jede id muss eindeutig sein."
                )
            seen.add(fid)


def _check_htmx_has_target(soup: BeautifulSoup, label: str) -> None:
    for el in soup.find_all(attrs={"hx-post": True}):
        if not el.get("hx-target") and not el.get("hx-boost"):
            tag = el.name
            hint = el.get("hx-post", "")[:60]
            raise AssertionError(
                f"<{tag} hx-post='{hint}'> fehlt hx-target{label}. "
                f"ADR-048: hx-post/hx-get immer mit hx-target."
            )
