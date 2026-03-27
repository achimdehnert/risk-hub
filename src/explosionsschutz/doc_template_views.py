# src/explosionsschutz/doc_template_views.py
"""
Standalone Dokument-Template Views für Explosionsschutz.

UC1: PDF hochladen → Template erstellen → editieren → akzeptieren
UC2: Template auswählen → Inhalte erstellen
UC3: Template + Dokument hochladen → Inhalte einlesen → editieren
"""

import json
import logging
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import ExDocInstance, ExDocTemplate

logger = logging.getLogger(__name__)

TPL_DIR = "explosionsschutz/doc_templates"


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


def _text_to_structure(text: str) -> dict:
    """Extrahierten Text in Template-Struktur umwandeln.

    Erkennt nummerierte Überschriften (1. Titel, 2. Titel, etc.)
    und erstellt Sections mit je einem Textarea-Feld.
    """
    sections = []
    # Nummerierte Überschriften erkennen
    pattern = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", re.MULTILINE,
    )
    matches = list(pattern.finditer(text))

    if matches:
        for i, m in enumerate(matches):
            num = m.group(1).rstrip(".")
            title = m.group(2).strip()
            key = f"section_{num.replace('.', '_')}"

            # Text bis zur nächsten Überschrift
            start = m.end()
            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )
            content = text[start:end].strip()

            sections.append({
                "key": key,
                "label": f"{num}. {title}",
                "fields": [
                    {
                        "key": "inhalt",
                        "label": "Inhalt",
                        "type": "textarea",
                        "required": False,
                        "default": content[:2000],
                    },
                ],
            })
    else:
        # Fallback: ganzer Text als eine Section
        sections.append({
            "key": "section_1",
            "label": "1. Dokumentinhalt",
            "fields": [
                {
                    "key": "inhalt",
                    "label": "Inhalt",
                    "type": "textarea",
                    "required": False,
                    "default": text[:5000],
                },
            ],
        })

    return {"sections": sections}


def _import_text_into_template(
    text: str, structure: dict,
) -> dict:
    """Importiert Text aus Dokument in Template-Werte.

    Versucht den Text anhand der Section-Labels aufzuteilen.
    """
    values = {}
    sections = structure.get("sections", [])

    for i, section in enumerate(sections):
        key = section["key"]
        label = section.get("label", "")

        # Suche nach dem Section-Label im Text
        num_match = re.match(r"(\d+(?:\.\d+)*)", label)
        if num_match:
            num = num_match.group(1)
            pattern = re.compile(
                rf"^{re.escape(num)}\.?\s+",
                re.MULTILINE,
            )
            match = pattern.search(text)
            if match:
                start = match.end()
                # Bis zur nächsten Section
                next_section = (
                    sections[i + 1]
                    if i + 1 < len(sections)
                    else None
                )
                if next_section:
                    next_label = next_section.get("label", "")
                    next_num = re.match(
                        r"(\d+(?:\.\d+)*)", next_label,
                    )
                    if next_num:
                        next_pat = re.compile(
                            rf"^{re.escape(next_num.group(1))}\.?\s+",
                            re.MULTILINE,
                        )
                        next_m = next_pat.search(text, start)
                        end = (
                            next_m.start() if next_m
                            else len(text)
                        )
                    else:
                        end = len(text)
                else:
                    end = len(text)

                content = text[start:end].strip()
                values[key] = {"inhalt": content[:5000]}
                continue

        values[key] = {"inhalt": ""}

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
    tmpl.delete()
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

        return render(
            request, f"{TPL_DIR}/instance_edit.html", {
                "instance": instance,
                "structure": structure,
                "values": values,
            },
        )

    # POST: Werte speichern
    values = {}
    for section in structure.get("sections", []):
        skey = section["key"]
        values[skey] = {}
        for field in section.get("fields", []):
            fkey = field["key"]
            form_key = f"{skey}__{fkey}"
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
