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


def accept_proposal(cmd: AcceptProposalCmd) -> ExplosionConceptGenerationLog:
    """Markiert einen Vorschlag als vom Experten übernommen.

    Nur SUCCESS-Logs können übernommen werden.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    log = ExplosionConceptGenerationLog.objects.get(pk=cmd.generation_log_id)

    if log.status != GenerationStatus.SUCCESS:
        raise ValueError(
            f"Nur SUCCESS-Logs können übernommen werden (status={log.status})"
        )

    now = datetime.now(UTC)
    log.status = GenerationStatus.ACCEPTED
    log.accepted_at = now
    log.accepted_by = User.objects.get(pk=cmd.accepted_by_user_id)
    log.changes_on_adoption = cmd.changes_made
    log.save(update_fields=[
        "status", "accepted_at", "accepted_by", "changes_on_adoption", "updated_at"
    ])
    return log


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
