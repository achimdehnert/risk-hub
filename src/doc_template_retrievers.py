"""Source retrievers for AI field prefill (ADR-107).

Registers real document content from risk-hub models via
fieldprefill.retrievers.register_retriever so the LLM gets
actual data instead of just source type labels.

Registered in SubstancesConfig.ready() to ensure models are loaded.
"""

import logging

from fieldprefill.retrievers import register_retriever

logger = logging.getLogger(__name__)


@register_retriever("sds")
def _get_sds_texts(tenant_id, instance=None):
    """Retrieve SDS data for all active substances of the tenant."""
    from substances.models import Substance

    substances = Substance.objects.filter(
        tenant_id=tenant_id, status="active",
    ).only(
        "name", "flash_point_c", "ignition_temperature_c",
        "lower_explosion_limit", "upper_explosion_limit",
        "temperature_class", "explosion_group",
        "fire_protection", "protective_measures",
        "first_aid", "storage_info",
    )[:20]

    texts = []
    for s in substances:
        parts = [f"Stoff: {s.name}"]
        if s.flash_point_c is not None:
            parts.append(f"Flammpunkt: {s.flash_point_c}°C")
        if s.ignition_temperature_c is not None:
            parts.append(f"Zündtemperatur: {s.ignition_temperature_c}°C")
        if s.lower_explosion_limit is not None:
            parts.append(f"UEG: {s.lower_explosion_limit} Vol.%")
        if s.upper_explosion_limit is not None:
            parts.append(f"OEG: {s.upper_explosion_limit} Vol.%")
        if s.temperature_class:
            parts.append(f"Temperaturklasse: {s.temperature_class}")
        if s.explosion_group:
            parts.append(f"Explosionsgruppe: {s.explosion_group}")
        if s.fire_protection:
            parts.append(f"Brand-/Explosionsschutz: {s.fire_protection[:500]}")
        if s.protective_measures:
            parts.append(f"Schutzmaßnahmen: {s.protective_measures[:500]}")
        texts.append("\n".join(parts))

    return texts


@register_retriever("gefaehrdungsbeurteilung")
def _get_gefaehrdungsbeurteilung_texts(tenant_id, instance=None):
    """Retrieve hazard assessments (GBU) for the tenant."""
    from risk.models import Assessment, Hazard

    assessments = Assessment.objects.filter(
        tenant_id=tenant_id,
    ).prefetch_related("hazards").order_by("-updated_at")[:10]

    texts = []
    for a in assessments:
        parts = [
            f"GBU: {a.title} ({a.get_status_display()})",
        ]
        if a.description:
            parts.append(f"Beschreibung: {a.description[:500]}")
        for h in a.hazards.all()[:10]:
            severity = dict(Hazard.Severity.choices).get(h.severity, "")
            parts.append(
                f"  Gefährdung: {h.title} "
                f"(Schwere: {severity}, Score: {h.risk_score})"
            )
            if h.mitigation:
                parts.append(f"  Maßnahme: {h.mitigation[:300]}")
        texts.append("\n".join(parts))

    return texts


@register_retriever("brandschutz")
def _get_brandschutz_texts(tenant_id, instance=None):
    """Retrieve fire safety documents for the tenant."""
    from documents.models import Document

    docs = Document.objects.filter(
        tenant_id=tenant_id, category="brandschutz",
    ).order_by("-updated_at")[:5]

    texts = []
    for d in docs:
        texts.append(f"Brandschutz-Dokument: {d.title}")

    return texts


@register_retriever("betriebsanweisung")
def _get_betriebsanweisung_texts(tenant_id, instance=None):
    """Retrieve operating instructions for the tenant."""
    from documents.models import Document

    docs = Document.objects.filter(
        tenant_id=tenant_id, category="betriebsanweisung",
    ).order_by("-updated_at")[:5]

    return [f"Betriebsanweisung: {d.title}" for d in docs]


@register_retriever("pruefbericht")
def _get_pruefbericht_texts(tenant_id, instance=None):
    """Retrieve test reports and certificates."""
    from documents.models import Document

    docs = Document.objects.filter(
        tenant_id=tenant_id, category="pruefbericht",
    ).order_by("-updated_at")[:5]

    return [f"Prüfbericht: {d.title}" for d in docs]


@register_retriever("risikobewertung")
def _get_risikobewertung_texts(tenant_id, instance=None):
    """Retrieve risk assessments."""
    from risk.models import Assessment

    assessments = Assessment.objects.filter(
        tenant_id=tenant_id, status="approved",
    ).order_by("-updated_at")[:5]

    texts = []
    for a in assessments:
        parts = [f"Risikobewertung: {a.title}"]
        if a.description:
            parts.append(a.description[:500])
        texts.append("\n".join(parts))

    return texts


def register_all_retrievers():
    """Register all source document retrievers + domain system prompt.

    Called from SubstancesConfig.ready().
    Retrievers are auto-registered via @register_retriever decorators above.
    This function registers the domain-specific system prompt.
    """
    from fieldprefill.prompts import register_system_prompt

    register_system_prompt(
        scope="explosionsschutz.ex_doc",
        prompt=(
            "Du bist ein Experte für Explosionsschutz und "
            "technische Dokumentation nach GefStoffV, TRGS 720ff "
            "und ATEX-Richtlinien. "
            "Schreibe fachlich korrekte, präzise Texte auf Deutsch. "
            "Antworte NUR mit dem Feldinhalt, keine "
            "Erklärungen oder Einleitungen."
        ),
    )

    logger.info(
        "fieldprefill retrievers registered (6 source types) + "
        "system prompt for scope 'explosionsschutz.ex_doc'"
    )
