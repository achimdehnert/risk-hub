"""Prompt templates for AI hazard analysis."""

HAZARD_ANALYSIS_SYSTEM = """Du bist ein Experte für Arbeitssicherheit, \
Explosionsschutz (ATEX/IECEx) und Gefahrstoffmanagement.
Du analysierst Bereiche, Stoffe und Betriebsbedingungen und gibst \
strukturierte Gefährdungsbeurteilungen ab.
Antworte immer auf Deutsch. Strukturiere deine Antwort als JSON."""

HAZARD_ANALYSIS_PROMPT = """Analysiere den folgenden Bereich und erstelle \
eine Gefährdungsbeurteilung:

**Bereich:** {area_name} ({area_code})
**Ex-Gefährdung:** {has_explosion_hazard}
**Beschreibung:** {description}

**Vorhandene Stoffe:**
{substances}

**Betriebsmittel im Bereich:**
{equipment}

Erstelle eine strukturierte Gefährdungsanalyse im folgenden JSON-Format:
{{
  "risk_level": "low|medium|high|critical",
  "summary": "Kurze Zusammenfassung der Gefährdungslage",
  "hazards": [
    {{
      "type": "explosion|fire|toxic|chemical|physical",
      "description": "Beschreibung der Gefährdung",
      "severity": "low|medium|high|critical",
      "probability": "unlikely|possible|likely|certain",
      "affected_zones": ["Zone 0", "Zone 1", ...],
      "recommended_measures": [
        "Maßnahme 1",
        "Maßnahme 2"
      ]
    }}
  ],
  "zone_recommendations": [
    {{
      "zone_type": "0|1|2|20|21|22",
      "justification": "Begründung",
      "extent_m": 1.5
    }}
  ],
  "regulatory_references": [
    "BetrSichV § ...",
    "TRBS ...",
    "TRGS ..."
  ]
}}"""

SUBSTANCE_RISK_PROMPT = """Bewerte das Gefahrenpotenzial des folgenden \
Gefahrstoffs im Kontext von Explosionsschutz:

**Stoff:** {name}
**CAS-Nr.:** {cas_number}
**H-Sätze:** {h_statements}
**Flammpunkt:** {flash_point}
**Explosionsgrenzen:** UEG {lel}% — OEG {uel}%
**Zündtemperatur:** {auto_ignition_temp}

Erstelle eine Risikobewertung als JSON:
{{
  "ex_relevance": "none|low|medium|high",
  "temperaturklasse": "T1|T2|T3|T4|T5|T6",
  "explosionsgruppe": "IIA|IIB|IIC",
  "key_risks": ["..."],
  "storage_requirements": ["..."],
  "handling_measures": ["..."],
  "regulatory_references": ["..."]
}}"""
