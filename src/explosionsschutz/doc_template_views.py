# src/explosionsschutz/doc_template_views.py
"""
Standalone Dokument-Template Views für Explosionsschutz.

UC1: PDF hochladen → Template erstellen → editieren → akzeptieren
UC2: Template auswählen → Inhalte erstellen
UC3: Template + Dokument hochladen → Inhalte einlesen → editieren

Nutzt concept_templates Package für:
- PDF-Strukturerkennung (TOC-Bereinigung, Content-Analyse)
- Tabellen-Erkennung und Feldtyp-Zuweisung
"""

import contextlib
import json
import logging
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import ExDocInstance, ExDocTemplate

logger = logging.getLogger(__name__)

TPL_DIR = "explosionsschutz/doc_templates"

# concept_templates Package (optional — graceful fallback)
try:
    from concept_templates.pdf_structure_extractor import (
        extract_structure_from_text as _pkg_extract,
    )

    _HAS_PKG = True
except ImportError:
    _HAS_PKG = False


def _tenant_id(request: HttpRequest) -> str:
    return str(getattr(request, "tenant_id", ""))


def _extract_pdf_text(pdf_file) -> str:
    """PDF-Text extrahieren (pdfplumber oder PyPDF2)."""
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


def _template_to_dict(ct) -> dict:
    """ConceptTemplate → JSON-kompatibles dict für DB."""
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
            if f.default_rows:
                fd["default_rows"] = f.default_rows
            fields.append(fd)
        sections.append(
            {
                "key": s.name,
                "label": s.title,
                "fields": fields,
            }
        )
    return {"sections": sections}


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
    if re.match(
        r"^(m[²³]?/[hs]|kg|cm|mm|l/|bar|°C|kW)\b",
        title,
        re.IGNORECASE,
    ):
        return False
    return not re.match(r"^\d{5}\b", num + title)


def _detect_table(content: str) -> list[str] | None:
    """Detect table columns in section content."""
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return None
    structured = [ln for ln in lines if "\t" in ln or ln.count("  ") >= 2]
    if len(structured) >= 2:
        cols = _split_cols(structured[0])
        if 2 <= len(cols) <= 10:
            return cols
    return None


def _detect_toc_entries(text: str) -> list[tuple[str, str]] | None:
    """Detect TOC (Inhaltsverzeichnis) and return entries in order."""
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


def _extract_toc_first(
    text: str,
    toc_entries: list[tuple[str, str]],
) -> list[dict]:
    """Use TOC as structure, map body content to each entry."""
    # Find body headings
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

        fields = []
        table_cols = _detect_table(content)
        if table_cols:
            fields.append(
                {
                    "key": "tabelle",
                    "label": "Tabelle",
                    "type": "table",
                    "required": False,
                    "columns": table_cols,
                }
            )
        fields.append(
            {
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": content[:3000],
            }
        )
        sections.append(
            {
                "key": key,
                "label": label,
                "fields": fields,
            }
        )
    return sections


def _extract_no_toc(text: str) -> list[dict]:
    """Fallback extraction without TOC: heading detection + filters."""
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
        re.MULTILINE,
    )
    letter_pat = re.compile(
        r"^([A-Z])\.\s+(.+)$",
        re.MULTILINE,
    )
    num_cands = []
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
        num_cands.append((m, num, title))

    filtered = []
    max_top = 0
    for m, num, title in num_cands:
        parts = num.split(".")
        top = int(parts[0])
        if len(parts) == 1 and top < max_top:
            continue
        if len(parts) == 1:
            max_top = max(max_top, top)
        filtered.append((m, num, title))

    letter_cands = []
    for m in letter_pat.finditer(text):
        title = _clean_toc(m.group(2).strip())
        if title:
            letter_cands.append((m, m.group(1), title))

    all_valid = sorted(
        filtered + letter_cands,
        key=lambda x: x[0].start(),
    )
    sections = []
    for i, (m, num, title) in enumerate(all_valid):
        key = f"section_{num.lower()}" if num.isalpha() else f"section_{num.replace('.', '_')}"
        start = m.end()
        end = all_valid[i + 1][0].start() if i + 1 < len(all_valid) else len(text)
        content = text[start:end].strip()
        fields = []
        table_cols = _detect_table(content)
        if table_cols:
            fields.append(
                {
                    "key": "tabelle",
                    "label": "Tabelle",
                    "type": "table",
                    "required": False,
                    "columns": table_cols,
                }
            )
        fields.append(
            {
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": content[:3000],
            }
        )
        sections.append(
            {
                "key": key,
                "label": f"{num}. {title}",
                "fields": fields,
            }
        )
    return sections


def _text_to_structure(text: str) -> dict:
    """Extrahierten Text in Template-Struktur umwandeln.

    Delegiert an concept_templates Package falls verfügbar.
    Fallback: TOC-first → heading detection with filters.
    """
    if _HAS_PKG:
        ct = _pkg_extract(text)
        return _template_to_dict(ct)

    # Strategy 1: TOC-first
    toc = _detect_toc_entries(text)
    if toc:
        sections = _extract_toc_first(text, toc)
        if sections:
            return {"sections": sections}

    # Strategy 2: No TOC — heading detection
    sections = _extract_no_toc(text)
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


def _import_text_into_template(
    text: str,
    structure: dict,
) -> dict:
    """Importiert Text aus Dokument in Template-Werte.

    Versucht den Text anhand der Section-Labels aufzuteilen.
    Unterstützt Freitext- und Tabellen-Felder.
    """
    values = {}
    sections = structure.get("sections", [])

    for i, section in enumerate(sections):
        skey = section["key"]
        label = section.get("label", "")
        fields = section.get("fields", [])

        # Suche nach dem Section-Label im Text
        content = ""
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
                    next_label = next_section.get(
                        "label",
                        "",
                    )
                    next_num = re.match(
                        r"(\d+(?:\.\d+)*)",
                        next_label,
                    )
                    if next_num:
                        next_pat = re.compile(
                            rf"^{re.escape(next_num.group(1))}\.?\s+",
                            re.MULTILINE,
                        )
                        next_m = next_pat.search(
                            text,
                            start,
                        )
                        end = next_m.start() if next_m else len(text)
                    else:
                        end = len(text)
                else:
                    end = len(text)
                content = text[start:end].strip()

        # Felder befüllen
        values[skey] = {}
        for field in fields:
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            if ftype == "table":
                # Tabelle aus Content nicht importiert
                values[skey][fkey] = []
            else:
                values[skey][fkey] = content[:5000]

    return values


# ─── Template List ───────────────────────────────────────────


@login_required
def template_list(request: HttpRequest) -> HttpResponse:
    """Alle Dokumentvorlagen anzeigen."""
    tid = _tenant_id(request)
    templates = ExDocTemplate.objects.filter(
        tenant_id=tid,
    ).order_by("-updated_at")
    instances = (
        ExDocInstance.objects.filter(
            tenant_id=tid,
        )
        .select_related("template")
        .order_by("-updated_at")[:20]
    )

    return render(
        request,
        f"{TPL_DIR}/list.html",
        {
            "templates": templates,
            "instances": instances,
        },
    )


# ─── Template Create (manual) ───────────────────────────────


@login_required
def template_create(request: HttpRequest) -> HttpResponse:
    """Neue leere Dokumentvorlage erstellen."""
    if request.method == "GET":
        return render(request, f"{TPL_DIR}/create.html")

    tid = _tenant_id(request)
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name ist Pflichtfeld.")
        return render(request, f"{TPL_DIR}/create.html")

    desc = request.POST.get("description", "").strip()
    structure = {
        "sections": [
            {
                "key": "section_1",
                "label": "1. Allgemeines",
                "fields": [
                    {
                        "key": "inhalt",
                        "label": "Inhalt",
                        "type": "textarea",
                        "required": False,
                    },
                ],
            },
        ],
    }

    tmpl = ExDocTemplate.objects.create(
        tenant_id=tid,
        name=name,
        description=desc,
        structure_json=json.dumps(
            structure,
            ensure_ascii=False,
        ),
    )
    messages.success(request, f"Vorlage '{name}' erstellt.")
    return redirect(
        "explosionsschutz:ex-doc-template-edit",
        pk=tmpl.pk,
    )


# ─── Template Create from Upload (UC1) ──────────────────────


@login_required
def template_upload(request: HttpRequest) -> HttpResponse:
    """PDF hochladen → Text extrahieren → Template erstellen."""
    if request.method == "GET":
        return render(request, f"{TPL_DIR}/upload.html")

    tid = _tenant_id(request)
    pdf_file = request.FILES.get("pdf_file")
    if not pdf_file:
        messages.error(request, "Keine Datei ausgewählt.")
        return render(request, f"{TPL_DIR}/upload.html")

    name = request.POST.get("name", "").strip()
    if not name:
        name = pdf_file.name.replace(".pdf", "").replace(
            "_",
            " ",
        )

    text = _extract_pdf_text(pdf_file)
    if not text:
        messages.warning(
            request,
            "Kein Text aus PDF extrahiert. Leere Vorlage erstellt.",
        )

    structure = (
        _text_to_structure(text)
        if text
        else {
            "sections": [],
        }
    )

    tmpl = ExDocTemplate.objects.create(
        tenant_id=tid,
        name=name,
        description=request.POST.get("description", ""),
        structure_json=json.dumps(
            structure,
            ensure_ascii=False,
        ),
        source_filename=pdf_file.name,
        source_text=text[:50000],
    )
    messages.success(
        request,
        f"Vorlage '{name}' aus PDF erstellt ({tmpl.section_count} Abschnitte).",
    )
    return redirect(
        "explosionsschutz:ex-doc-template-edit",
        pk=tmpl.pk,
    )


# ─── Template Edit (UC1 continued) ──────────────────────────


@login_required
def template_edit(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Template-Struktur bearbeiten."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate,
        pk=pk,
        tenant_id=tid,
    )

    if request.method == "GET":
        try:
            structure = json.loads(tmpl.structure_json)
        except (json.JSONDecodeError, TypeError):
            structure = {"sections": []}

        from explosionsschutz.ex_doc_constants import (
            ai_source_choices_for_js,
            field_type_choices_for_js,
        )

        return render(
            request,
            f"{TPL_DIR}/edit.html",
            {
                "tmpl": tmpl,
                "structure": structure,
                "structure_json": json.dumps(
                    structure,
                    ensure_ascii=False,
                    indent=2,
                ),
                "field_types_json": json.dumps(
                    field_type_choices_for_js(),
                    ensure_ascii=False,
                ),
                "ai_source_types_json": json.dumps(
                    ai_source_choices_for_js(),
                    ensure_ascii=False,
                ),
            },
        )

    # POST: Struktur speichern
    raw_json = request.POST.get("structure_json", "")
    try:
        structure = json.loads(raw_json)
        if "sections" not in structure:
            raise ValueError("Missing 'sections' key")
    except (json.JSONDecodeError, ValueError) as exc:
        messages.error(
            request,
            f"Ungültiges JSON: {exc}",
        )
        return render(
            request,
            f"{TPL_DIR}/edit.html",
            {
                "tmpl": tmpl,
                "structure": {"sections": []},
                "structure_json": raw_json,
            },
        )

    tmpl.structure_json = json.dumps(
        structure,
        ensure_ascii=False,
    )
    tmpl.name = request.POST.get("name", tmpl.name)
    tmpl.description = request.POST.get(
        "description",
        tmpl.description,
    )
    new_status = request.POST.get("status", tmpl.status)
    if new_status in dict(ExDocTemplate.Status.choices):
        tmpl.status = new_status
    tmpl.save()

    messages.success(request, "Vorlage gespeichert.")
    return redirect("explosionsschutz:ex-doc-templates")


# ─── Template Delete ─────────────────────────────────────────


@login_required
@require_POST
def template_delete(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Dokumentvorlage löschen."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate,
        pk=pk,
        tenant_id=tid,
    )
    name = tmpl.name
    try:
        tmpl.delete()
    except models.ProtectedError:
        count = tmpl.instances.count()
        messages.error(
            request,
            f"Vorlage '{name}' kann nicht gelöscht werden — "
            f"es gibt noch {count} Dokument(e) die darauf basieren. "
            f"Bitte zuerst die Dokumente löschen.",
        )
        return redirect("explosionsschutz:ex-doc-templates")
    messages.success(request, f"Vorlage '{name}' gelöscht.")
    return redirect("explosionsschutz:ex-doc-templates")


# ─── Instance Create (UC2 + UC3) ────────────────────────────


@login_required
def instance_create(
    request: HttpRequest,
    template_pk: int,
) -> HttpResponse:
    """Neues Dokument aus Template erstellen (leer oder Import)."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate,
        pk=template_pk,
        tenant_id=tid,
    )

    if request.method == "GET":
        return render(
            request,
            f"{TPL_DIR}/instance_create.html",
            {
                "tmpl": tmpl,
            },
        )

    name = request.POST.get("name", "").strip()
    if not name:
        name = f"{tmpl.name} — Neu"

    try:
        structure = json.loads(tmpl.structure_json)
    except (json.JSONDecodeError, TypeError):
        structure = {"sections": []}

    # UC3: Dokument hochladen → Inhalte einlesen
    pdf_file = request.FILES.get("pdf_file")
    values = {}
    source_filename = ""

    if pdf_file:
        text = _extract_pdf_text(pdf_file)
        if text:
            values = _import_text_into_template(
                text,
                structure,
            )
            source_filename = pdf_file.name
            messages.info(
                request,
                f"Inhalte aus '{pdf_file.name}' importiert.",
            )
        else:
            messages.warning(
                request,
                "Kein Text aus PDF extrahiert.",
            )

    instance = ExDocInstance.objects.create(
        tenant_id=tid,
        template=tmpl,
        name=name,
        values_json=json.dumps(
            values,
            ensure_ascii=False,
        ),
        source_filename=source_filename,
    )
    return redirect(
        "explosionsschutz:ex-doc-instance-edit",
        pk=instance.pk,
    )


# ─── Instance Create for Concept ─────────────────────────────


@login_required
def instance_create_for_concept(
    request: HttpRequest,
    template_pk: int,
    concept_pk: str,
) -> HttpResponse:
    """Neues Dokument aus Template für ein Konzept erstellen."""
    from .models import ExplosionConcept

    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate,
        pk=template_pk,
        tenant_id=tid,
    )
    concept = get_object_or_404(
        ExplosionConcept,
        pk=concept_pk,
        tenant_id=tid,
    )

    name = f"{concept.title} — {tmpl.name}"
    instance = ExDocInstance.objects.create(
        tenant_id=tid,
        template=tmpl,
        concept=concept,
        name=name,
        values_json="{}",
    )
    messages.success(
        request,
        f"Dokument '{name}' erstellt.",
    )
    return redirect(
        "explosionsschutz:ex-doc-instance-edit",
        pk=instance.pk,
    )


# ─── Instance Edit ───────────────────────────────────────────


@login_required
def instance_edit(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Dokument-Inhalte bearbeiten."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        ExDocInstance.objects.select_related("template"),
        pk=pk,
        tenant_id=tid,
    )

    try:
        structure = json.loads(
            instance.template.structure_json,
        )
    except (json.JSONDecodeError, TypeError):
        structure = {"sections": []}

    if request.method == "GET":
        try:
            values = json.loads(instance.values_json)
        except (json.JSONDecodeError, TypeError):
            values = {}

        # AI source label mapping (shared constants)
        from explosionsschutz.ex_doc_constants import ai_source_short_labels

        _ai_src_labels = ai_source_short_labels()

        # Merge values into structure for easy rendering
        for section in structure.get("sections", []):
            skey = section["key"]
            svals = values.get(skey, {})
            for field in section.get("fields", []):
                fkey = field["key"]
                ftype = field.get("type", "textarea")
                val = svals.get(fkey, "")
                if ftype == "table":
                    field["table_rows"] = (
                        val
                        if isinstance(
                            val,
                            list,
                        )
                        else field.get("default_rows", [])
                    )
                    # Ensure min 3 empty rows
                    cols = field.get("columns", [])
                    while len(field["table_rows"]) < 3:
                        field["table_rows"].append(
                            [""] * len(cols),
                        )
                else:
                    field["field_value"] = val or field.get(
                        "default",
                        "",
                    )

                # AI config for template rendering
                ai_src = field.get("ai_sources", [])
                if ai_src:
                    field["ai_sources_csv"] = ",".join(
                        ai_src,
                    )
                    field["ai_sources_labels"] = ", ".join(_ai_src_labels.get(s, s) for s in ai_src)

        return render(
            request,
            f"{TPL_DIR}/instance_edit.html",
            {
                "instance": instance,
                "structure": structure,
            },
        )

    # POST: Werte speichern
    values = {}
    for section in structure.get("sections", []):
        skey = section["key"]
        values[skey] = {}
        for field in section.get("fields", []):
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            form_key = f"{skey}__{fkey}"

            if ftype == "table":
                columns = field.get("columns", [])
                rows = []
                row_idx = 0
                while True:
                    row_key = f"{form_key}__row_{row_idx}"
                    first_col = request.POST.get(
                        f"{row_key}__col_0",
                        None,
                    )
                    if first_col is None:
                        break
                    row = []
                    for ci in range(len(columns)):
                        cell = request.POST.get(
                            f"{row_key}__col_{ci}",
                            "",
                        )
                        row.append(cell)
                    if any(c.strip() for c in row):
                        rows.append(row)
                    row_idx += 1
                values[skey][fkey] = rows
            elif ftype == "boolean":
                # Hidden "false" + checkbox "true"
                vals = request.POST.getlist(form_key)
                values[skey][fkey] = "true" if "true" in vals else "false"
            else:
                values[skey][fkey] = request.POST.get(
                    form_key,
                    "",
                )

    new_status = request.POST.get("status", instance.status)
    if new_status in dict(ExDocInstance.Status.choices):
        instance.status = new_status

    instance.values_json = json.dumps(
        values,
        ensure_ascii=False,
    )
    instance.name = request.POST.get("name", instance.name)
    instance.save()

    messages.success(request, "Dokument gespeichert.")
    return redirect(
        "explosionsschutz:ex-doc-instance-edit",
        pk=instance.pk,
    )


# ─── Instance Delete ─────────────────────────────────────────


@login_required
@require_POST
def instance_delete(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Dokument löschen."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        ExDocInstance,
        pk=pk,
        tenant_id=tid,
    )
    name = instance.name
    instance.delete()
    messages.success(request, f"Dokument '{name}' gelöscht.")
    return redirect("explosionsschutz:ex-doc-templates")


# ─── Instance LLM Prefill ────────────────────────────────────


@login_required
@require_POST
def instance_llm_prefill(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """HTMX endpoint: KI-Prefill für ein einzelnes Feld.

    Delegates to explosionsschutz.services.ex_doc_prefill which uses:
    - promptfw Jinja2 templates (maintainable prompts)
    - Real document context via retrievers (SDS, GBU, etc.)
    - aifw.sync_completion direct (quality routing + token tracking)
    - concept_templates.prefill fallback (when installed)
    """
    tid = _tenant_id(request)
    instance = get_object_or_404(
        ExDocInstance.objects.select_related("template"),
        pk=pk,
        tenant_id=tid,
    )

    field_key = request.POST.get("field_key", "")
    llm_hint = request.POST.get("llm_hint", "")
    ai_sources_raw = request.POST.get("ai_sources", "")
    field_type = request.POST.get("field_type", "textarea")

    if not field_key or not llm_hint:
        return HttpResponse(
            "field_key und llm_hint erforderlich",
            status=400,
        )

    ai_sources = [s.strip() for s in ai_sources_raw.split(",") if s.strip()]

    # Existing values for cross-field context
    existing_values = None
    if instance.values_json and instance.values_json != "{}":
        with contextlib.suppress(json.JSONDecodeError, AttributeError):
            existing_values = json.loads(instance.values_json)

    # Extracted texts from linked concept or template source
    extracted_texts = []
    if instance.concept_id:
        extracted_texts = list(
            instance.concept.concept_documents.filter(
                status="analyzed",
                deleted_at__isnull=True,
            ).values_list(
                "extracted_text",
                flat=True,
            )[:2]
        )
    if not extracted_texts and instance.template.source_text:
        extracted_texts = [
            instance.template.source_text[:5000],
        ]

    try:
        from explosionsschutz.services.ex_doc_prefill import (
            prefill_ex_doc_field,
        )

        value = prefill_ex_doc_field(
            field_key=field_key,
            llm_hint=llm_hint,
            ai_sources=ai_sources,
            tenant_id=tid,
            instance=instance,
            existing_values=existing_values,
            extracted_texts=extracted_texts,
            field_type=field_type,
        )
    except Exception as exc:
        logger.warning("LLM prefill failed: %s", exc)
        return HttpResponse(
            f'<span class="text-red-500 text-sm">Fehler: {exc}</span>',
        )

    from django.utils.html import escape

    safe_val = escape(value)
    return HttpResponse(
        f'<textarea name="{field_key}" rows="4" '
        f'class="w-full px-3 py-2 border border-green-300 '
        f"rounded-lg bg-green-50 focus:ring-2 "
        f'focus:ring-orange-500">{safe_val}</textarea>',
    )


# ─── Instance PDF Export ──────────────────────────────────────


@login_required
def instance_pdf_export(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """PDF-Export eines ausgefüllten Dokuments."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        ExDocInstance.objects.select_related("template"),
        pk=pk,
        tenant_id=tid,
    )

    try:
        from concept_templates.document_renderer import (
            render_pdf,
        )
        from concept_templates.schemas import (
            ConceptTemplate,
            FieldType,
            TemplateField,
            TemplateSection,
        )
    except ImportError:
        messages.error(
            request,
            "PDF-Export benötigt concept_templates[render].",
        )
        return redirect(
            "explosionsschutz:ex-doc-instance-edit",
            pk=instance.pk,
        )

    structure = json.loads(instance.template.structure_json)
    values = (
        json.loads(instance.values_json)
        if (instance.values_json and instance.values_json != "{}")
        else {}
    )

    # Convert structure to ConceptTemplate
    sections = []
    for i, s in enumerate(structure.get("sections", [])):
        fields = []
        for f in s.get("fields", []):
            ft = FieldType.TEXTAREA
            if f.get("type") == "text":
                ft = FieldType.TEXT
            elif f.get("type") == "table":
                ft = FieldType.TABLE
            fields.append(
                TemplateField(
                    name=f["key"],
                    label=f.get("label", f["key"]),
                    field_type=ft,
                )
            )
        sections.append(
            TemplateSection(
                name=s["key"],
                title=s.get("label", f"Abschnitt {i + 1}"),
                order=i + 1,
                fields=fields,
            )
        )

    ct = ConceptTemplate(
        name=instance.template.name,
        scope="explosionsschutz",
        version="1.0",
        sections=sections,
    )

    pdf_bytes = render_pdf(
        template=ct,
        values=values,
        title=instance.name,
    )

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )
    safe_name = instance.name.replace(" ", "_")[:80]
    response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
    return response
