"""Prompt templates for AI hazard analysis — powered by iil-promptfw."""

from promptfw import PromptStack, PromptTemplate, TemplateLayer


def _build_stack() -> PromptStack:
    """Builds and returns the shared PromptStack for hazard analysis."""
    stack = PromptStack()

    stack.register(
        PromptTemplate(
            id="hazard.system",
            layer=TemplateLayer.SYSTEM,
            template=(
                "Du bist ein Experte für Arbeitssicherheit, "
                "Explosionsschutz (ATEX/IECEx) und Gefahrstoffmanagement.\n"
                "Du analysierst Bereiche, Stoffe und Betriebsbedingungen"
                " und gibst strukturierte Gefährdungsbeurteilungen ab.\n"
                "Antworte immer auf Deutsch. Strukturiere deine Antwort als JSON."
            ),
            variables=[],
        )
    )

    stack.register(
        PromptTemplate(
            id="hazard.task.area",
            layer=TemplateLayer.TASK,
            template="""Analysiere den folgenden Bereich und erstelle eine \
Gefährdungsbeurteilung:

**Bereich:** {{ area_name }} ({{ area_code }})
**Ex-Gefährdung:** {{ has_explosion_hazard }}
**Beschreibung:** {{ description }}

**Vorhandene Stoffe:**
{{ substances }}

**Betriebsmittel im Bereich:**
{{ equipment }}

Erstelle eine strukturierte Gefährdungsanalyse im folgenden JSON-Format:
{
  "risk_level": "low|medium|high|critical",
  "summary": "Kurze Zusammenfassung der Gefährdungslage",
  "hazards": [
    {
      "type": "explosion|fire|toxic|chemical|physical",
      "description": "Beschreibung der Gefährdung",
      "severity": "low|medium|high|critical",
      "probability": "unlikely|possible|likely|certain",
      "affected_zones": ["Zone 0", "Zone 1"],
      "recommended_measures": ["Maßnahme 1", "Maßnahme 2"]
    }
  ],
  "zone_recommendations": [
    {"zone_type": "0|1|2|20|21|22", "justification": "Begründung",
     "extent_m": 1.5}
  ],
  "regulatory_references": ["BetrSichV § ...", "TRBS ...", "TRGS ..."]
}""",
            variables=[
                "area_name",
                "area_code",
                "has_explosion_hazard",
                "description",
                "substances",
                "equipment",
            ],
        )
    )

    stack.register(
        PromptTemplate(
            id="hazard.task.substance",
            layer=TemplateLayer.TASK,
            template="""Bewerte das Gefahrenpotenzial des folgenden Gefahrstoffs \
im Kontext von Explosionsschutz:

**Stoff:** {{ name }}
**CAS-Nr.:** {{ cas_number }}
**H-Sätze:** {{ h_statements }}
**Flammpunkt:** {{ flash_point }}
**Explosionsgrenzen:** UEG {{ lel }}% — OEG {{ uel }}%
**Zündtemperatur:** {{ auto_ignition_temp }}

Erstelle eine Risikobewertung als JSON:
{
  "ex_relevance": "none|low|medium|high",
  "temperaturklasse": "T1|T2|T3|T4|T5|T6",
  "explosionsgruppe": "IIA|IIB|IIC",
  "key_risks": ["..."],
  "storage_requirements": ["..."],
  "handling_measures": ["..."],
  "regulatory_references": ["..."]
}""",
            variables=[
                "name",
                "cas_number",
                "h_statements",
                "flash_point",
                "lel",
                "uel",
                "auto_ignition_temp",
            ],
        )
    )

    stack.register(
        PromptTemplate(
            id="brandschutz.system",
            layer=TemplateLayer.SYSTEM,
            template=(
                "Du bist ein Experte für vorbeugenden Brandschutz nach ASR A2.2, "
                "DIN 14096 und Bauordnungsrecht.\
"
                "Du analysierst Brandschutzkonzepte, Brandabschnitte, Fluchtwege "
                "und Löschmittelausstattung.\
"
                "Antworte immer auf Deutsch. Strukturiere deine Antwort als JSON."
            ),
            variables=[],
        )
    )

    stack.register(
        PromptTemplate(
            id="brandschutz.task.concept",
            layer=TemplateLayer.TASK,
            template="""Analysiere das folgende Brandschutzkonzept und identifiziere \
Mängel und Verbesserungsbedarf:

**Konzept:** {{ concept_title }} ({{ concept_type }})
**Standort:** {{ site_name }}
**Status:** {{ status }}
**Gültig bis:** {{ valid_until }}

**Brandabschnitte:** {{ sections_count }}
**Fluchtwege gesamt:** {{ escape_routes_count }}
**Fluchtwege mit Mängeln:** {{ escape_routes_defect }}
**Feuerlöscher gesamt:** {{ extinguishers_count }}
**Feuerlöscher überfällig:** {{ extinguishers_overdue }}
**Offene Maßnahmen:** {{ measures_open }}

Erstelle eine Bewertung im folgenden JSON-Format:
{{
  "compliance_level": "ok|minor_issues|major_issues|critical",
  "summary": "Kurze Zusammenfassung",
  "findings": [
    {{
      "category": "fluchtweg|loescher|brandabschnitt|dokument|massnahme",
      "severity": "info|warning|critical",
      "description": "Beschreibung des Befunds",
      "recommendation": "Empfohlene Maßnahme",
      "legal_reference": "ASR A2.2 / DIN 14096 / ..."
    }}
  ],
  "priority_actions": ["Sofortmaßnahme 1", "Sofortmaßnahme 2"],
  "next_review_recommendation": "Empfehlung für nächste Prüfung"
}}""",
            variables=[
                "concept_title",
                "concept_type",
                "site_name",
                "status",
                "valid_until",
                "sections_count",
                "escape_routes_count",
                "escape_routes_defect",
                "extinguishers_count",
                "extinguishers_overdue",
                "measures_open",
            ],
        )
    )

    return stack


_STACK = _build_stack()


def get_hazard_area_messages(context: dict) -> list[dict]:
    """Returns OpenAI-compatible messages list for area hazard analysis."""
    return _STACK.render_to_messages(
        ["hazard.system", "hazard.task.area"],
        context=context,
    )


def get_substance_risk_messages(context: dict) -> list[dict]:
    """Returns OpenAI-compatible messages list for substance risk analysis."""
    return _STACK.render_to_messages(
        ["hazard.system", "hazard.task.substance"],
        context=context,
    )


def get_fire_concept_messages(context: dict) -> list[dict]:
    """Returns OpenAI-compatible messages list for fire concept analysis."""
    return _STACK.render_to_messages(
        ["brandschutz.system", "brandschutz.task.concept"],
        context=context,
    )
