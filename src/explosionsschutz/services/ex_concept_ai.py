# src/explosionsschutz/services/ex_concept_ai.py
"""
Section-Level KI-Generierung für ExplosionConcept (ADR-018, Stufe 1).

Tier 2 der LLM-Architektur: iil-aifw → sync_completion().
Kein direkter Anthropic/OpenAI-SDK-Call — model-agnostisch über AIActionType.
"""

import hashlib
import logging
import re
from datetime import UTC, datetime

from aifw.service import LLMResult, sync_completion

from explosionsschutz.ai.dtos import (
    AcceptProposalCmd,
    GenerateProposalCmd,
    GenerationResult,
    RejectProposalCmd,
)
from explosionsschutz.ai.prompts import build_prompt_for_chapter
from explosionsschutz.models.generation_log import (
    ExplosionConceptGenerationLog,
    GenerationStatus,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Du arbeitest als fachkundige Person im Sinne der TRGS 400 / TRBS 1203 "
    "an einem Explosionsschutzdokument nach § 6 Abs. 9 GefStoffV.\n"
    "Liefere nur den angeforderten Abschnitt — keine Präambel, keine Meta-Kommentare.\n"
    "Quellenverweise INLINE als Klammerzusätze, z.B. '(TRGS 722 Nr. 3.2)'.\n"
    "Fehlende oder unsichere Angaben: '[KLÄRUNGSBEDARF: Grund]' — niemals erfinden.\n"
    "Ausgabeformat: Markdown."
)

_KLAERUNGSBEDARF_RE = re.compile(r"\[KLÄRUNGSBEDARF:[^\]]+\]")


def generate_chapter(cmd: GenerateProposalCmd) -> GenerationResult:
    """Generiert einen KI-Vorschlag für einen Abschnitt des Explosionsschutzkonzepts.

    Erstellt GenerationLog (RUNNING), ruft iil-aifw sync_completion(),
    aktualisiert Log (SUCCESS/FAILED), gibt GenerationResult zurück.

    Raises:
        ExplosionConcept.DoesNotExist: Wenn Konzept nicht für Tenant gefunden.
        ValueError: Wenn chapter nicht unterstützt.
    """
    from explosionsschutz.models import ExplosionConcept

    concept = (
        ExplosionConcept.objects.select_related("area")
        .get(pk=cmd.concept_id, tenant_id=cmd.tenant_id)
    )

    user_prompt, input_context = build_prompt_for_chapter(
        chapter=cmd.chapter,
        concept=concept,
        user_notes=cmd.additional_user_notes,
    )

    action_code = f"ex_concept_{cmd.chapter}"
    prompt_hash = hashlib.sha256(
        (SYSTEM_PROMPT + user_prompt).encode("utf-8")
    ).hexdigest()

    # 1. Log anlegen und sofort committen (außerhalb tx, damit RUNNING sichtbar ist)
    log = ExplosionConceptGenerationLog.objects.create(
        tenant_id=cmd.tenant_id,
        concept=concept,
        chapter=cmd.chapter,
        status=GenerationStatus.RUNNING,
        action_code=action_code,
        model_name="",
        prompt_hash=prompt_hash,
        prompt_system=SYSTEM_PROMPT,
        prompt_user=user_prompt,
        input_context=input_context,
    )

    # 2. iil-aifw Call — model-agnostisch über AIActionType DB-Routing
    result: LLMResult = sync_completion(
        action_code=action_code,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        tenant_id=cmd.tenant_id,
        object_id=str(cmd.concept_id),
        metadata={"chapter": cmd.chapter, "gen_log_id": log.pk},
    )

    # 3. Log aktualisieren
    now = datetime.now(UTC)
    if result.success:
        clarifications = _extract_klaerungsbedarf(result.content)
        log.status = GenerationStatus.SUCCESS
        log.response_text = result.content
        log.input_tokens = result.input_tokens
        log.output_tokens = result.output_tokens
        log.model_name = result.model or action_code
        log.finished_at = now
        log.save(update_fields=[
            "status", "response_text", "input_tokens", "output_tokens",
            "model_name", "finished_at", "updated_at",
        ])
        logger.info(
            "ex_concept_ai: chapter=%s concept=%s tokens=%d model=%s log=%d",
            cmd.chapter, cmd.concept_id,
            log.input_tokens + log.output_tokens,
            log.model_name, log.pk,
        )
        return GenerationResult(
            log_id=log.pk,
            success=True,
            text=result.content,
            clarifications=clarifications,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    else:
        log.status = GenerationStatus.FAILED
        log.error_message = result.error or "Unknown error"
        log.finished_at = now
        log.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        logger.error(
            "ex_concept_ai FAILED: chapter=%s concept=%s error=%r log=%d",
            cmd.chapter, cmd.concept_id, result.error, log.pk,
        )
        return GenerationResult(
            log_id=log.pk,
            success=False,
            error=result.error or "LLM call failed",
        )


def _parse_zones_from_text(text: str) -> list[dict]:
    """Parst ### Zone X Abschnitte aus KI-generiertem Markdown-Text.

    Erkennt Zone 0/1/2/20/21/22. Gibt Liste von Dicts zurück:
    [{"zone_type": "1", "name": "Zone 1", "description": "...", "justification": "..."}]
    """
    valid_types = {"0", "1", "2", "20", "21", "22"}
    zones = []
    # Split auf ### Zone N (auch mit trailing text wie "### Zone 1 — Lager")
    section_re = re.compile(r"^###\s+Zone\s+(\d{1,2})\b", re.MULTILINE)
    positions = [(m.start(), m.group(1)) for m in section_re.finditer(text)]

    for i, (start, zone_num) in enumerate(positions):
        if zone_num not in valid_types:
            continue
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        section = text[start:end].strip()

        # Begründung extrahieren (Zeilen nach "Begründung:")
        justification = ""
        begr_match = re.search(r"\*{0,2}Begründung:\*{0,2}(.+?)(?=\n-\s+\*{0,2}(?:Hinweis|Ausdehnung)|$)",
                               section, re.DOTALL)
        if begr_match:
            justification = begr_match.group(1).strip()

        # Ausdehnung extrahieren
        extent_match = re.search(r"Ausdehnung[^:]*:\*{0,2}\s*(.+)", section)
        extent_text = extent_match.group(1).strip() if extent_match else ""

        zones.append({
            "zone_type": zone_num,
            "name": f"Zone {zone_num}",
            "description": section,
            "justification": justification or section,
            "extent_text": extent_text,
        })
    return zones


def _apply_zones_to_concept(concept, zones: list[dict], tenant_id) -> list:
    """Erstellt oder aktualisiert ZoneDefinition-Objekte aus geparsten Zonen.

    Strategie: get_or_create nach (concept, zone_type) — Update wenn vorhanden.
    Gibt Liste der bearbeiteten ZoneDefinition-Objekte zurück.
    """
    from django.apps import apps
    ZoneDefinition = apps.get_model("explosionsschutz", "ZoneDefinition")

    result = []
    for z in zones:
        obj, created = ZoneDefinition.objects.get_or_create(
            concept=concept,
            zone_type=z["zone_type"],
            defaults={"tenant_id": tenant_id, "name": z["name"]},
        )
        obj.name = z["name"]
        obj.description = z["description"]
        obj.justification = z["justification"]
        obj.save(update_fields=["name", "description", "justification", "updated_at"])
        result.append((obj, created))
    return result


def _parse_measures_from_text(text: str) -> list[dict]:
    """Parst nummerierte Maßnahmen-Liste aus KI-generiertem Text.

    Erkennt Zeilen wie:
      N. **Primär (...)** / **Sekundär (...)** / **Tertiär (...)**
         - **Bezeichnung:** Titel der Maßnahme
         - **Norm-Verweis:** ...
    Gibt Liste von Dicts zurück: [{"category": "primary", "title": "...", "description": "..."}]
    """
    _CAT_MAP = {
        "primär": "primary",
        "sekundär": "secondary",
        "tertiär": "tertiary",
        "organisatorisch": "organizational",
    }

    measures = []
    # Trenne nach nummeriertem Eintrag (1. / 2. etc.)
    item_re = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)
    positions = [(m.start(), m.group(1)) for m in item_re.finditer(text)]

    for i, (start, header) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        block = text[start:end]

        # Kategorie aus Header-Text
        category = "secondary"
        for key, val in _CAT_MAP.items():
            if key in header.lower():
                category = val
                break

        # Bezeichnung (Pflicht)
        bez_match = re.search(r"\*{0,2}Bezeichnung:\*{0,2}\s*(.+)", block)
        title = bez_match.group(1).strip() if bez_match else header.strip("()")

        # Beschreibung aus restlichen Bullet-Zeilen
        desc_lines = []
        for line in block.splitlines():
            stripped = line.strip().lstrip("-").strip()
            if stripped.startswith("**Bezeichnung"):
                continue
            if stripped.startswith("**"):
                desc_lines.append(re.sub(r"\*{1,2}", "", stripped))
        description = " | ".join(desc_lines[:3])

        if title:
            measures.append({
                "category": category,
                "title": title[:255],
                "description": description[:500],
            })
    return measures


def _apply_measures_to_concept(concept, measures: list[dict], tenant_id) -> list:
    """Erstellt ProtectionMeasure-Objekte aus geparsten Maßnahmen.

    Strategie: get_or_create nach (concept, title) — Update wenn vorhanden.
    Gibt Liste der bearbeiteten (obj, created) Tupeln zurück.
    """
    from django.apps import apps
    ProtectionMeasure = apps.get_model("explosionsschutz", "ProtectionMeasure")

    result = []
    for m in measures:
        obj, created = ProtectionMeasure.objects.get_or_create(
            concept=concept,
            title=m["title"],
            defaults={"tenant_id": tenant_id, "category": m["category"]},
        )
        obj.category = m["category"]
        obj.description = m["description"]
        obj.save(update_fields=["category", "description", "updated_at"])
        result.append((obj, created))
    return result


def accept_proposal(cmd: AcceptProposalCmd) -> tuple:
    """Markiert einen Vorschlag als vom Experten übernommen.

    Bei chapter='zones': parst editierten Text und erstellt/aktualisiert ZoneDefinition.
    Bei chapter='measures': parst Text und erstellt/aktualisiert ProtectionMeasure.
    Gibt (log, zone_results) zurück — zone_results ist Liste von (obj, created) Tupeln.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    log = ExplosionConceptGenerationLog.objects.select_related("concept").get(
        pk=cmd.generation_log_id
    )

    if log.status != GenerationStatus.SUCCESS:
        raise ValueError(
            f"Nur SUCCESS-Logs können übernommen werden (status={log.status})"
        )

    final_text = cmd.proposal_text.strip() if cmd.proposal_text.strip() else log.response_text
    now = datetime.now(UTC)
    log.status = GenerationStatus.ACCEPTED
    log.accepted_at = now
    log.accepted_by = User.objects.get(pk=cmd.accepted_by_user_id)
    log.changes_on_adoption = cmd.changes_made
    log.response_text = final_text
    log.save(update_fields=[
        "status", "accepted_at", "accepted_by", "changes_on_adoption",
        "response_text", "updated_at",
    ])

    zone_results = []
    if log.chapter == "zones":
        zones = _parse_zones_from_text(final_text)
        zone_results = _apply_zones_to_concept(
            log.concept, zones, log.tenant_id
        )
        logger.info(
            "accept_proposal: %d Zonen für Konzept %s erzeugt/aktualisiert",
            len(zone_results), log.concept_id,
        )
    elif log.chapter in ("measures", "ignition"):
        measures = _parse_measures_from_text(final_text)
        zone_results = _apply_measures_to_concept(
            log.concept, measures, log.tenant_id
        )
        logger.info(
            "accept_proposal: %d Maßnahmen für Konzept %s erzeugt/aktualisiert",
            len(zone_results), log.concept_id,
        )

    return log, zone_results


def reject_proposal(cmd: RejectProposalCmd) -> ExplosionConceptGenerationLog:
    """Markiert einen Vorschlag als vom Experten abgelehnt."""
    log = ExplosionConceptGenerationLog.objects.get(pk=cmd.generation_log_id)

    if log.status not in (GenerationStatus.SUCCESS, GenerationStatus.ACCEPTED):
        raise ValueError(
            f"Nur SUCCESS/ACCEPTED-Logs können abgelehnt werden (status={log.status})"
        )

    log.status = GenerationStatus.REJECTED
    log.save(update_fields=["status", "updated_at"])
    return log


def _extract_klaerungsbedarf(text: str) -> list[str]:
    """Extrahiert alle [KLÄRUNGSBEDARF: ...]-Marker aus dem LLM-Output."""
    return _KLAERUNGSBEDARF_RE.findall(text)
