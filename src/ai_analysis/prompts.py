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
