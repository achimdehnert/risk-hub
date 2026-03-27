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

import json
import logging
import re

from django.contrib import messages
from django.db import models
from django.contrib.auth.decorators import login_required
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
        sections.append({
            "key": s.name,
            "label": s.title,
            "fields": fields,
        })
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
        title, re.IGNORECASE,
    ):
        return False
    if re.match(r"^\d{5}\b", num + title):
        return False
    return True


def _detect_table(content: str) -> list[str] | None:
    """Detect table columns in section content."""
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return None
    structured = [
        ln for ln in lines
        if "\t" in ln or ln.count("  ") >= 2
    ]
    if len(structured) >= 2:
        cols = _split_cols(structured[0])
        if 2 <= len(cols) <= 10:
            return cols
    return None


def _text_to_structure(text: str) -> dict:
    """Extrahierten Text in Template-Struktur umwandeln.

    Delegiert an concept_templates Package falls verfügbar.
    Fallback: Letter headings (A. B. C.) + numbered headings,
    sequential monotonicity filter, table detection.
    """
    if _HAS_PKG:
        ct = _pkg_extract(text)
        return _template_to_dict(ct)

    # Fallback: full extraction with letter + number headings
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", re.MULTILINE,
    )
    letter_pat = re.compile(
        r"^([A-Z])\.\s+(.+)$", re.MULTILINE,
    )

    # Numeric candidates with validation
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

    # Sequential monotonicity filter
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

    # Letter candidates
    letter_cands = []
    for m in letter_pat.finditer(text):
        letter = m.group(1)
        title = _clean_toc(m.group(2).strip())
        if not title:
            continue
        letter_cands.append((m, letter, title))

    # Merge sorted by position
    all_valid = sorted(
        filtered + letter_cands,
        key=lambda x: x[0].start(),
    )

    sections = []
    if all_valid:
        for i, (m, num, title) in enumerate(all_valid):
            if num.isalpha():
                key = f"section_{num.lower()}"
            else:
                key = f"section_{num.replace('.', '_')}"
            label = f"{num}. {title}"

            start = m.end()
            end = (
                all_valid[i + 1][0].start()
                if i + 1 < len(all_valid)
                else len(text)
            )
            content = text[start:end].strip()

            # Detect table in content
            fields = []
            table_cols = _detect_table(content)
            if table_cols:
                fields.append({
                    "key": "tabelle",
                    "label": "Tabelle",
                    "type": "table",
                    "required": False,
                    "columns": table_cols,
                })
            fields.append({
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": content[:3000],
            })

            sections.append({
                "key": key,
                "label": label,
                "fields": fields,
            })
    else:
        sections.append({
            "key": "section_1",
            "label": "1. Dokumentinhalt",
            "fields": [{
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": text[:5000],
            }],
        })

    return {"sections": sections}


def _import_text_into_template(
    text: str, structure: dict,
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
                next_section = (
                    sections[i + 1]
                    if i + 1 < len(sections)
                    else None
                )
                if next_section:
                    next_label = next_section.get(
                        "label", "",
                    )
                    next_num = re.match(
                        r"(\d+(?:\.\d+)*)", next_label,
                    )
                    if next_num:
                        next_pat = re.compile(
                            rf"^{re.escape(next_num.group(1))}\.?\s+",
                            re.MULTILINE,
                        )
                        next_m = next_pat.search(
                            text, start,
                        )
                        end = (
                            next_m.start() if next_m
                            else len(text)
                        )
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
    instances = ExDocInstance.objects.filter(
        tenant_id=tid,
    ).select_related("template").order_by("-updated_at")[:20]

    return render(request, f"{TPL_DIR}/list.html", {
        "templates": templates,
        "instances": instances,
    })


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
            structure, ensure_ascii=False,
        ),
    )
    messages.success(request, f"Vorlage '{name}' erstellt.")
    return redirect(
        "explosionsschutz:ex-doc-template-edit", pk=tmpl.pk,
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
            "_", " ",
        )

    text = _extract_pdf_text(pdf_file)
    if not text:
        messages.warning(
            request,
            "Kein Text aus PDF extrahiert. "
            "Leere Vorlage erstellt.",
        )

    structure = _text_to_structure(text) if text else {
        "sections": [],
    }

    tmpl = ExDocTemplate.objects.create(
        tenant_id=tid,
        name=name,
        description=request.POST.get("description", ""),
        structure_json=json.dumps(
            structure, ensure_ascii=False,
        ),
        source_filename=pdf_file.name,
        source_text=text[:50000],
    )
    messages.success(
        request,
        f"Vorlage '{name}' aus PDF erstellt "
        f"({tmpl.section_count} Abschnitte).",
    )
    return redirect(
        "explosionsschutz:ex-doc-template-edit", pk=tmpl.pk,
    )


# ─── Template Edit (UC1 continued) ──────────────────────────


@login_required
def template_edit(
    request: HttpRequest, pk: int,
) -> HttpResponse:
    """Template-Struktur bearbeiten."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate, pk=pk, tenant_id=tid,
    )

    if request.method == "GET":
        try:
            structure = json.loads(tmpl.structure_json)
        except (json.JSONDecodeError, TypeError):
            structure = {"sections": []}

        return render(request, f"{TPL_DIR}/edit.html", {
            "tmpl": tmpl,
            "structure": structure,
            "structure_json": json.dumps(
                structure, ensure_ascii=False, indent=2,
            ),
        })

    # POST: Struktur speichern
    raw_json = request.POST.get("structure_json", "")
    try:
        structure = json.loads(raw_json)
        if "sections" not in structure:
            raise ValueError("Missing 'sections' key")
    except (json.JSONDecodeError, ValueError) as exc:
        messages.error(
            request, f"Ungültiges JSON: {exc}",
        )
        return render(request, f"{TPL_DIR}/edit.html", {
            "tmpl": tmpl,
            "structure": {"sections": []},
            "structure_json": raw_json,
        })

    tmpl.structure_json = json.dumps(
        structure, ensure_ascii=False,
    )
    tmpl.name = request.POST.get("name", tmpl.name)
    tmpl.description = request.POST.get(
        "description", tmpl.description,
    )
    new_status = request.POST.get("status", tmpl.status)
    if new_status in dict(ExDocTemplate.Status.choices):
        tmpl.status = new_status
    tmpl.save()

    messages.success(request, "Vorlage gespeichert.")
    if tmpl.status == ExDocTemplate.Status.ACCEPTED:
        return redirect("explosionsschutz:ex-doc-templates")
    return redirect(
        "explosionsschutz:ex-doc-template-edit", pk=tmpl.pk,
    )


# ─── Template Delete ─────────────────────────────────────────


@login_required
@require_POST
def template_delete(
    request: HttpRequest, pk: int,
) -> HttpResponse:
    """Dokumentvorlage löschen."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate, pk=pk, tenant_id=tid,
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
    request: HttpRequest, template_pk: int,
) -> HttpResponse:
    """Neues Dokument aus Template erstellen (leer oder Import)."""
    tid = _tenant_id(request)
    tmpl = get_object_or_404(
        ExDocTemplate, pk=template_pk, tenant_id=tid,
    )

    if request.method == "GET":
        return render(request, f"{TPL_DIR}/instance_create.html", {
            "tmpl": tmpl,
        })

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
                text, structure,
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
            values, ensure_ascii=False,
        ),
        source_filename=source_filename,
    )
    return redirect(
        "explosionsschutz:ex-doc-instance-edit",
        pk=instance.pk,
    )


# ─── Instance Edit ───────────────────────────────────────────


@login_required
def instance_edit(
    request: HttpRequest, pk: int,
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

        # Merge values into structure for easy rendering
        for section in structure.get("sections", []):
            skey = section["key"]
            svals = values.get(skey, {})
            for field in section.get("fields", []):
                fkey = field["key"]
                ftype = field.get("type", "textarea")
                val = svals.get(fkey, "")
                if ftype == "table":
                    field["table_rows"] = val if isinstance(
                        val, list,
                    ) else field.get("default_rows", [])
                    # Ensure min 3 empty rows
                    cols = field.get("columns", [])
                    while len(field["table_rows"]) < 3:
                        field["table_rows"].append(
                            [""] * len(cols),
                        )
                else:
                    field["field_value"] = val or field.get(
                        "default", "",
                    )

        return render(
            request, f"{TPL_DIR}/instance_edit.html", {
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
                        f"{row_key}__col_0", None,
                    )
                    if first_col is None:
                        break
                    row = []
                    for ci in range(len(columns)):
                        cell = request.POST.get(
                            f"{row_key}__col_{ci}", "",
                        )
                        row.append(cell)
                    if any(c.strip() for c in row):
                        rows.append(row)
                    row_idx += 1
                values[skey][fkey] = rows
            else:
                values[skey][fkey] = request.POST.get(
                    form_key, "",
                )

    new_status = request.POST.get("status", instance.status)
    if new_status in dict(ExDocInstance.Status.choices):
        instance.status = new_status

    instance.values_json = json.dumps(
        values, ensure_ascii=False,
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
    request: HttpRequest, pk: int,
) -> HttpResponse:
    """Dokument löschen."""
    tid = _tenant_id(request)
    instance = get_object_or_404(
        ExDocInstance, pk=pk, tenant_id=tid,
    )
    name = instance.name
    instance.delete()
    messages.success(request, f"Dokument '{name}' gelöscht.")
    return redirect("explosionsschutz:ex-doc-templates")
