"""
URL Reference Audit — ensures every {% url 'namespace:name' %} in templates
has a matching registered URL pattern. Prevents NoReverseMatch 500s.

Runs as part of CI (pytest). Catches the root cause:
templates referencing URLs that exist in API namespace but not HTML namespace.
"""

import re
from pathlib import Path

from django.test import TestCase
from django.urls import NoReverseMatch, reverse


class TestTemplateUrlReferences(TestCase):
    """Every {% url %} tag in templates must resolve without error."""

    def test_all_template_url_references_exist(self):
        """Scan all templates for {% url %} tags and verify each one resolves."""
        src_dir = Path(__file__).resolve().parent.parent
        templates_dir = src_dir / "templates"

        if not templates_dir.exists():
            self.skipTest("templates/ directory not found")

        url_pattern = re.compile(r"""{%\s*url\s+['"]([a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_-]+)['"]""")

        missing = []
        checked = 0

        for html_file in templates_dir.rglob("*.html"):
            content = html_file.read_text(errors="ignore")
            for match in url_pattern.finditer(content):
                url_name = match.group(1)
                checked += 1
                try:
                    # Try without args first — we only care if the name exists
                    reverse(url_name)
                except NoReverseMatch as e:
                    err_msg = str(e)
                    # Distinguish "not found" from "args missing"
                    if "is not a valid view function or pattern name" in err_msg:
                        rel_path = html_file.relative_to(templates_dir)
                        line_no = content[: match.start()].count("\n") + 1
                        missing.append(f"  {rel_path}:{line_no} → {url_name}")

        self.assertGreater(checked, 0, "No URL references found in templates")
        self.assertEqual(
            missing,
            [],
            f"\n{len(missing)} broken URL reference(s) in templates:\n"
            + "\n".join(missing)
            + "\n\nFix: register the URL name in the correct html_urls.py "
            + "(not just in the API urls.py)",
        )
