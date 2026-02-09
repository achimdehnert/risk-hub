"""AI hazard analysis service."""

import json
import logging
from uuid import UUID

from ai_analysis.llm_client import llm_complete_sync
from ai_analysis.prompts import (
    HAZARD_ANALYSIS_PROMPT,
    HAZARD_ANALYSIS_SYSTEM,
    SUBSTANCE_RISK_PROMPT,
)

logger = logging.getLogger(__name__)


def analyze_area(area_id: UUID, tenant_id: UUID) -> dict:
    """
    Run AI hazard analysis on an area.

    Collects area data, substances, and equipment, then
    sends to LLM Gateway for structured analysis.
    """
    from explosionsschutz.models import Area, Equipment

    area = Area.objects.get(id=area_id, tenant_id=tenant_id)

    # Collect equipment in this area
    equipment_qs = Equipment.objects.filter(
        area=area, tenant_id=tenant_id,
    ).select_related("equipment_type")

    equipment_lines = []
    for eq in equipment_qs[:20]:
        line = f"- {eq.serial_number}"
        if eq.equipment_type:
            line += f" ({eq.equipment_type.name})"
        if eq.next_inspection_date:
            line += f" [Prüfung: {eq.next_inspection_date}]"
        equipment_lines.append(line)

    # Collect substances (from concepts in this area)
    substance_lines = _collect_area_substances(area)

    prompt = HAZARD_ANALYSIS_PROMPT.format(
        area_name=area.name,
        area_code=area.code,
        has_explosion_hazard="Ja" if area.has_explosion_hazard else "Nein",
        description=getattr(area, "description", "") or "Keine Beschreibung",
        substances="\n".join(substance_lines) or "Keine Stoffe erfasst",
        equipment="\n".join(equipment_lines) or "Keine Betriebsmittel",
    )

    try:
        raw = llm_complete_sync(
            prompt=prompt,
            system=HAZARD_ANALYSIS_SYSTEM,
            temperature=0.2,
            max_tokens=3000,
        )
        result = _parse_json_response(raw)
        result["_raw"] = raw
        result["_area_id"] = str(area_id)
        return result
    except Exception as exc:
        logger.exception("AI analysis failed for area %s", area_id)
        return {
            "error": str(exc),
            "_area_id": str(area_id),
        }


def analyze_substance(
    substance_id: UUID,
    tenant_id: UUID,
) -> dict:
    """Run AI risk assessment on a substance."""
    from substances.models import Substance

    sub = Substance.objects.get(
        id=substance_id, tenant_id=tenant_id,
    )

    # Build substance data from available fields
    prompt = SUBSTANCE_RISK_PROMPT.format(
        name=sub.name,
        cas_number=getattr(sub, "cas_number", "") or "unbekannt",
        h_statements=getattr(sub, "h_statements", "") or "keine",
        flash_point=getattr(sub, "flash_point", "") or "unbekannt",
        lel=getattr(sub, "lel", "") or "?",
        uel=getattr(sub, "uel", "") or "?",
        auto_ignition_temp=getattr(sub, "auto_ignition_temp", "") or "unbekannt",
    )

    try:
        raw = llm_complete_sync(
            prompt=prompt,
            system=HAZARD_ANALYSIS_SYSTEM,
            temperature=0.2,
            max_tokens=2000,
        )
        result = _parse_json_response(raw)
        result["_raw"] = raw
        result["_substance_id"] = str(substance_id)
        return result
    except Exception as exc:
        logger.exception(
            "AI analysis failed for substance %s", substance_id,
        )
        return {
            "error": str(exc),
            "_substance_id": str(substance_id),
        }


def _collect_area_substances(area) -> list[str]:
    """Collect substance info from concepts in an area."""
    lines = []
    try:
        for concept in area.explosion_concepts.all()[:5]:
            if hasattr(concept, "substance_id") and concept.substance_id:
                lines.append(f"- Stoff-ID: {concept.substance_id}")
    except Exception:
        pass
    return lines


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM response (handles markdown fences)."""
    text = raw.strip()

    # Strip markdown code fences
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"_raw_text": raw, "_parse_error": True}
