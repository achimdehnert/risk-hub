"""PDF extraction and template structure utilities.

Extracted from projects/views.py for service-layer compliance.
Used by: projects.services, projects.views (template upload/import).
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


# ─── Low-level helpers ───────────────────────────────────────


def extract_pdf_text(pdf_file) -> str:
    """Extract text from PDF file."""
    try:
        import pdfplumber

        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        parts = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pdfplumber failed: %s", exc)

    try:
        import PyPDF2

        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        reader = PyPDF2.PdfReader(pdf_file)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PyPDF2 failed: %s", exc)

    return ""


def _clean_toc(title: str) -> str:
    """Remove TOC dots and page numbers."""
    title = re.sub(r"\s*[.·…]{2,}\s*\d*\s*$", "", title)
    title = re.sub(r"\s+\d{1,4}\s*$", "", title)
    return title.strip()


def _split_cols(line: str) -> list[str]:
    """Split a line by tab or multi-space."""
    if "\t" in line:
        parts = [c.strip() for c in line.split("\t")]
    else:
        parts = [c.strip() for c in re.split(r"\s{2,}", line)]
    return [p for p in parts if p]


def _is_valid_heading(num: str, title: str, line: str) -> bool:
    """Filter false positives: table rows, PLZ, measurements."""
    top = int(num.split(".")[0])
    if top > 30:
        return False
    if sum(1 for c in title if c.isalpha()) < 2:
        return False
    if len(_split_cols(line)) >= 3:
        return False
    return not re.match(r"^(m[²³]?/[hs]|kg|cm|mm|l/|bar|°C|kW)\b", title, re.IGNORECASE)


# ─── Table detection ─────────────────────────────────────────


def _detect_table(content: str) -> list[str] | None:
    """Detect table columns in section content.

    Strategies:
    1. Tab-separated or multi-space lines (classic)
    2. Pipe-separated (|col1|col2|)
    3. Known German table headers (Nr., Zone, etc.)
    4. Header-like first line followed by data rows
    """
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return None

    # Strategy 1: tab / multi-space structured lines
    structured = [ln for ln in lines if "\t" in ln or ln.count("  ") >= 2]
    if len(structured) >= 2:
        cols = _split_cols(structured[0])
        if 2 <= len(cols) <= 10:
            return cols

    # Strategy 2: pipe-separated table
    pipe_lines = [ln for ln in lines if ln.count("|") >= 2]
    if len(pipe_lines) >= 2:
        cols = [c.strip() for c in pipe_lines[0].split("|") if c.strip()]
        if 2 <= len(cols) <= 10:
            return cols

    # Strategy 3: known German table header patterns
    header_pat = re.compile(
        r"(Nr\.?|Nummer|Zone|Bereich|Anlagenteil|"
        r"Bemerkung|Schutzma[sß]nahm|Ma[sß]nahm|"
        r"Beschreibung|Bezeichnung|Menge|Einheit|"
        r"Ergebnis|Bewertung|Kategorie|Status|"
        r"Gefährdung|Risiko|Häufigkeit|Typ)",
        re.IGNORECASE,
    )
    for _i, line in enumerate(lines[:10]):
        stripped = line.strip()
        matches = header_pat.findall(stripped)
        if len(matches) >= 2:
            cols = _split_cols(stripped)
            if len(cols) < 2:
                # Try splitting by known separators
                cols = [c.strip() for c in re.split(r"\s{2,}|\t", stripped) if c.strip()]
            if 2 <= len(cols) <= 10:
                return cols
            # Fallback: use the matched keywords as cols
            if 2 <= len(matches) <= 10:
                return matches

    # Strategy 4: short first line (potential header)
    # followed by lines with similar structure
    first = lines[0].strip()
    if len(first) < 120:
        first_cols = _split_cols(first)
        if 2 <= len(first_cols) <= 10:
            # Check if following lines have similar col count
            similar = 0
            for ln in lines[1 : min(6, len(lines))]:
                lcols = _split_cols(ln.strip())
                if lcols and abs(len(lcols) - len(first_cols)) <= 1:
                    similar += 1
            if similar >= 1:
                return first_cols

    return None


# ─── TOC detection ───────────────────────────────────────────


def _detect_toc_entries(text: str) -> list[tuple[str, str]] | None:
    """Detect TOC (Inhaltsverzeichnis) and return entries."""
    toc_match = re.search(
        r"^(Inhaltsverzeichnis|Inhalt|Table of Contents)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not toc_match:
        return None

    lines = text[toc_match.end() :].split("\n")
    toc_lines = []
    non_toc = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            non_toc += 1
            if non_toc >= 3:
                break
            continue
        is_toc = bool(
            re.search(r"[.·…]{2,}", stripped)
            or re.match(r"^[A-Z]\.\s+\S", stripped)
            or re.match(r"^\d+(?:\.\d+)*\.?\s+\S", stripped)
        )
        if is_toc:
            toc_lines.append(stripped)
            non_toc = 0
        else:
            non_toc += 1
            if non_toc >= 3:
                break

    if len(toc_lines) < 2:
        return None

    toc_text = "\n".join(toc_lines)
    entries = []
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
        re.MULTILINE,
    )
    letter_pat = re.compile(
        r"^([A-Z])\.\s+(.+)$",
        re.MULTILINE,
    )
    for m in num_pat.finditer(toc_text):
        num = m.group(1).rstrip(".")
        title = _clean_toc(m.group(2).strip())
        if title:
            entries.append((num, title, m.start()))
    for m in letter_pat.finditer(toc_text):
        title = _clean_toc(m.group(2).strip())
        if title:
            entries.append((m.group(1), title, m.start()))
    entries.sort(key=lambda x: x[2])
    if len(entries) < 2:
        return None
    return [(eid, et) for eid, et, _ in entries]


# ─── Content → Fields ────────────────────────────────────────


def _content_to_fields(content: str) -> list[dict]:
    """Split section content into typed fields.

    Detects tables and separates text before/after them.
    Returns a list of field dicts for template structure.
    """
    if not content.strip():
        return [
            {
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
            }
        ]

    table_cols = _detect_table(content)

    if not table_cols:
        return [
            {
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": content[:3000],
            }
        ]

    # Table detected — split text before table from table
    fields = []
    lines = content.split("\n")

    # Find where table starts (first structured line)
    table_start_idx = 0
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        cols = _split_cols(stripped)
        if len(cols) >= len(table_cols) - 1:
            # Check if this looks like the header
            match_count = sum(1 for c in cols if any(tc.lower() in c.lower() for tc in table_cols))
            if match_count >= 1:
                table_start_idx = i
                break

    # Text before table
    text_before = "\n".join(
        lines[:table_start_idx],
    ).strip()
    if text_before:
        fields.append(
            {
                "key": "beschreibung",
                "label": "Beschreibung",
                "type": "textarea",
                "required": False,
                "default": text_before[:2000],
            }
        )

    # Table field
    fields.append(
        {
            "key": "tabelle",
            "label": "Tabelle",
            "type": "table",
            "required": False,
            "columns": table_cols,
        }
    )

    # Text after table (if any significant text)
    text_after = "\n".join(
        lines[table_start_idx + len(table_cols) + 5 :],
    ).strip()
    if len(text_after) > 50:
        fields.append(
            {
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": text_after[:2000],
            }
        )

    # If only table, add empty inhalt for notes
    if not text_before and len(text_after) <= 50:
        fields.append(
            {
                "key": "inhalt",
                "label": "Anmerkungen",
                "type": "textarea",
                "required": False,
            }
        )

    return fields


# ─── TOC-first structure extraction ─────────────────────────


def _extract_toc_first(
    text: str,
    toc_entries: list[tuple[str, str]],
) -> list[dict]:
    """Use TOC as structure, map body content to each entry."""
    toc_end = len(text) // 5
    body_pos = []
    for eid, etitle in toc_entries:
        prefix = re.escape(etitle[:20])
        if eid.isalpha():
            pat = re.compile(
                rf"^{re.escape(eid)}\.\s+{prefix}",
                re.MULTILINE,
            )
        else:
            pat = re.compile(
                rf"^{re.escape(eid)}\.?\s+{prefix}",
                re.MULTILINE,
            )
        m = pat.search(text, toc_end)
        if m:
            lend = text.find("\n", m.start())
            if lend == -1:
                lend = len(text)
            body_pos.append((m.start(), lend, eid, etitle))

    if not body_pos:
        return []

    body_pos.sort(key=lambda x: x[0])
    pos_map = {}
    for start, end, eid, etitle in body_pos:
        if eid not in pos_map:
            pos_map[eid] = (start, end, etitle)

    sections = []
    for eid, etitle in toc_entries:
        key = f"section_{eid.lower()}" if eid.isalpha() else f"section_{eid.replace('.', '_')}"
        label = f"{eid}. {etitle}"

        if eid not in pos_map:
            sections.append(
                {
                    "key": key,
                    "label": label,
                    "fields": [
                        {
                            "key": "inhalt",
                            "label": "Inhalt",
                            "type": "textarea",
                            "required": False,
                        }
                    ],
                }
            )
            continue

        hstart, hend, _ = pos_map[eid]
        next_start = len(text)
        for ostart, _, _, _ in body_pos:
            if ostart > hstart:
                next_start = ostart
                break
        content = text[hend:next_start].strip()

        fields = _content_to_fields(content)
        sections.append(
            {
                "key": key,
                "label": label,
                "fields": fields,
            }
        )
    return sections


# ─── Main structure extraction ───────────────────────────────


def text_to_structure(text: str) -> dict:
    """Convert extracted PDF text to template structure.

    Strategy 1: TOC-first (Inhaltsverzeichnis detection).
    Strategy 2: Heading detection with filters.
    Fallback: Single section with full text.
    """
    # Try concept_templates package first
    try:
        from concept_templates.pdf_structure_extractor import (
            extract_structure_from_text as _pkg_extract,
        )

        ct = _pkg_extract(text)
        sections = []
        for s in ct.sections:
            fields = []
            for f in s.fields:
                fd = {
                    "key": f.name,
                    "label": f.label,
                    "type": str(f.field_type.value),
                    "required": f.required,
                }
                if f.default:
                    fd["default"] = f.default
                if f.columns:
                    fd["columns"] = f.columns
                fields.append(fd)
            sections.append(
                {
                    "key": s.name,
                    "label": s.title,
                    "fields": fields,
                }
            )
        return {"sections": sections}
    except ImportError:
        pass

    # Strategy 1: TOC-first
    toc = _detect_toc_entries(text)
    if toc:
        sections = _extract_toc_first(text, toc)
        if sections:
            return {"sections": sections}

    # Strategy 2: Heading detection with filters
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
        re.MULTILINE,
    )
    candidates = []
    for m in num_pat.finditer(text):
        num = m.group(1).rstrip(".")
        title = _clean_toc(m.group(2).strip())
        if not title:
            continue
        try:
            if not _is_valid_heading(num, title, m.group(0)):
                continue
        except (ValueError, IndexError):
            continue
        candidates.append((m, num, title))

    sections = []
    for i, (m, num, title) in enumerate(candidates):
        key = f"section_{num.replace('.', '_')}"
        start = m.end()
        end = candidates[i + 1][0].start() if i + 1 < len(candidates) else len(text)
        content = text[start:end].strip()[:3000]
        fields = _content_to_fields(content)

        sections.append(
            {
                "key": key,
                "label": f"{num}. {title}",
                "fields": fields,
            }
        )

    if sections:
        return {"sections": sections}

    # Fallback
    return {
        "sections": [
            {
                "key": "section_1",
                "label": "1. Dokumentinhalt",
                "fields": [
                    {
                        "key": "inhalt",
                        "label": "Inhalt",
                        "type": "textarea",
                        "required": False,
                        "default": text[:5000],
                    }
                ],
            }
        ]
    }


def import_text_into_template(
    text: str,
    structure: dict,
) -> dict:
    """Import text from PDF into template field values.

    Splits text by section labels and assigns to fields.
    """
    values = {}
    sections = structure.get("sections", [])

    for i, section in enumerate(sections):
        skey = section["key"]
        fields = section.get("fields", [])

        content = ""
        label = section.get("label", "")
        num_match = re.match(r"(\d+(?:\.\d+)*)", label)
        if num_match:
            num = num_match.group(1)
            pat = re.compile(
                rf"^{re.escape(num)}\.?\s+",
                re.MULTILINE,
            )
            match = pat.search(text)
            if match:
                start = match.end()
                next_section = sections[i + 1] if i + 1 < len(sections) else None
                if next_section:
                    next_label = next_section.get("label", "")
                    next_num = re.match(
                        r"(\d+(?:\.\d+)*)",
                        next_label,
                    )
                    if next_num:
                        next_pat = re.compile(
                            rf"^{re.escape(next_num.group(1))}\.?\s+",
                            re.MULTILINE,
                        )
                        next_m = next_pat.search(text, start)
                        end = next_m.start() if next_m else len(text)
                    else:
                        end = len(text)
                else:
                    end = len(text)
                content = text[start:end].strip()

        values[skey] = {}
        for field in fields:
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            if ftype == "table":
                values[skey][fkey] = []
            else:
                values[skey][fkey] = content[:5000]

    return values
