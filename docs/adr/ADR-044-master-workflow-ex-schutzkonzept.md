---
status: proposed
date: 2026-04-22
deciders: [Achim Dehnert]
consulted: []
informed: []
implementation_status: none
---

# ADR-044: Master-Workflow für Ex-Schutzkonzepte

- **Status:** Proposed
- **Datum:** 2026-04-22
- **Entscheider:** Achim Dehnert
- **Betroffene Module:** explosionsschutz, substances, global_sds, projects, exschutzdokument (neu thin)
- **Abhängigkeiten:** ADR-041 (Project-based Workflow), ADR-043 (planned), ADR-012 (Shared SDS Library), ADR-002 (substances/SDS)
- **Vorarbeit:** Memo-Konvergenz Master-Workflow ↔ ADR-041 vom 2026-04-22

## Kontext

Die bisherige Umsetzung in `apps/explosionsschutz/` modelliert ein grundlegendes `ExplosionConcept` mit Zonen, Zündquellen-Assessments und Schutzmaßnahmen. Die Praxis-Analyse von sechs realen Ex-Schutzdokumenten aus verschiedenen Szenarien (Wasserstoff-Öfen mit Inertisierung, Holzstaub-Filteranlage mit echten Zone-20-Klassifikationen, Mehrstoff-Lager, Gefahrstoffschränke, Außenlager, Ofen mit funktionaler Sicherheit) hat gezeigt, dass das aktuelle Datenmodell in mehreren Dimensionen nicht ausreicht:

- Staub-spezifische Kenngrößen (Glimmtemperatur, KSt, Pmax, Brennzahl, Korngröße, Feuchte) fehlen
- Zonen haben nur einen Status (permanent vorhanden), nicht aber konditionale Varianten (messungsgetriggert, tätigkeitsgekoppelt)
- Staubzonen mit der Dualität Wolke/Schicht werden nicht abgebildet
- Mehrstoff-Bewertung ist nicht möglich (nur FK zu einer Substance)
- Die quantitative MSR-Bewertung nach TRGS 725 Tabelle 3 (Performance Level → Klassifizierungsstufe K) fehlt vollständig
- Cybersicherheit als eigenständige GBU-Dimension (ab EU-MVO 2027 verpflichtend) fehlt
- Zonen-Geometrie (Radius, Referenzobjekt, Höhe) ist nicht strukturiert
- Bestandsschutz für Altanlagen ist nicht modelliert
- Die formelle Freigabe-Erklärung mit Juristenformel hat keinen Platz

Der Master-Workflow aus der Praxis-Analyse strukturiert die Konzept-Erstellung in 7 Phasen (A: Kontext, B: Gefährdungsermittlung, C: Schutz-Hierarchie, D: Betriebsregime, E: Validierung, F: Freigabe, G: Lebenszyklus) und bettet sich natürlich in den Project-Container aus ADR-041 ein. Die Konvergenz-Analyse hat gezeigt, dass sich die Anzahl der neuen Modell-Items durch Wiederverwendung von ADR-041-Strukturen (`ProjectDocument`, `OutputDocument`, `SectionSourceReference`) von 22 auf 14 reduziert.

## Considered Options

| Option | Beschreibung | Status |
|--------|-------------|--------|
| **A — Alles in `apps/explosionsschutz/`** | UC-1 und UC-2 im selben App-Namespace, kein `iil-doc-templates` | Abgelehnt |
| **B — Parallele App `apps/exschutzdokument/` mit eigenem Modell** | Eigene Freigabe-Logik, eigene Snapshot-Mechanismen parallel zu UC-1 | Abgelehnt |
| **C — Dünne Wrapper-App `apps/exschutzdokument/`** | ~50 Zeilen Code, kein eigenes Fach-Datenmodell, delegiert an `iil-doc-templates` | **Gewählt** |

**Option A** scheidet aus, weil UC-2 (Freitext-Gutachten) strukturell andere Anforderungen hat als UC-1 (strukturierte Compliance-Daten). Eine gemeinsame App würde die Domänentrennung aus ADR-043 aufweichen.

**Option B** bedeutet doppelte Datenmodell-Komplexität: eigene Freigabe-Logik und eigene Snapshot-Mechanismen parallel zu UC-1. `iil-doc-templates` löst das Problem bereits vollständig und stellt PDF-Export sowie Prefill-Integration bereit.

**Option C** maximiert die Wiederverwendung von `iil-doc-templates`, hält die App-Trennung nach ADR-043 sauber und erfordert minimal Entwicklungsaufwand.

## Entscheidung

Wir erweitern `apps/explosionsschutz/` um 14 neue Modell-Items und zwei Verfeinerungen bestehender Modelle. Alle neuen Strukturen sind exklusiv für UC-1 (interne Compliance). UC-2 (Gutachten) erhält eine dünne Wrapper-App `apps/exschutzdokument/` ohne eigenes Fach-Datenmodell.

### Architektur-Topologie

```
apps/explosionsschutz/   UC-1, Master-Workflow, 14 neue Items
apps/exschutzdokument/   UC-2, ~50 Zeilen Wrapper um iil-doc-templates
apps/projects/           Gemeinsamer Container nach ADR-041
```

Die strikte Trennung aus ADR-043 (planned) bleibt erhalten, wird aber präzisiert: `apps/exschutzdokument/` ist keine parallele Fach-App, sondern ein Domain-Kontext-Anker ohne eigenes Datenmodell.

### Die zwei KI-Prefill-Ebenen

```
UC-1: iil-aifw.sync_completion()    → strukturierte Kapitel
UC-2: iil-fieldprefill.prefill_field() → freie Textfelder pro Abschnitt
```

## 1. Neue Modell-Items (14)

### 1.1 Stoff-Phase und Staub-Kenngrößen

`Substance.phase` wird von einer impliziten Annahme (Gas/Dampf) zu einem expliziten Enum mit vier Werten: `GAS`, `VAPOR`, `MIST`, `DUST`. Pflichtfeld, migrierbar aus bestehenden Daten über H-Code-Heuristik (H220/H221/H222/H223 = Gas, H224/H225/H226 = Dampf-bildende Flüssigkeit, H250/H251/H252 = Dust/Solid-Hazard).

Neu: `DustSubstanceProperties` als OneToOne-Erweiterung auf `Substance`, nur befüllt wenn `phase = DUST`:

```python
class DustSubstanceProperties(models.Model):
    substance = models.OneToOneField(
        "substances.Substance",
        on_delete=models.CASCADE,
        related_name="dust_properties",
    )

    # Glimmtemperatur (Schicht, 5 mm)
    glow_temperature_c = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True,
        help_text="Niedrigste Temperatur zum Entzünden einer Staubschicht von 5 mm"
    )

    # KSt-Wert und abgeleitete Klasse
    kst_bar_m_per_s = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True,
        help_text="Höchstwert des zeitlichen Druckanstiegs (normiert)"
    )
    dust_class = models.CharField(
        max_length=4, blank=True,
        choices=[("St0", "St 0 (inert)"), ("St1", "St 1 (schwach)"),
                 ("St2", "St 2 (mittel)"), ("St3", "St 3 (stark)")],
    )

    # Weitere staub-spezifische Werte
    p_max_bar = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Maximaler Explosionsdruck"
    )
    burn_number = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text="Brennzahl BZ 1-6 nach VDI 2263"
    )
    particle_size_median_um = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Korngröße Median (μm), typisch relevant < 400 μm"
    )
    moisture_influence_text = models.TextField(
        blank=True,
        help_text="Einfluss der Feuchte auf Zündempfindlichkeit/Explosionsfähigkeit"
    )
```

Der aktuelle `Stoff` aus HANDOVER-exschutz-integration.md hat bereits `staubexplosionsklasse_kst` und `glimmtemperatur_c` — diese werden in die neue Subset-Tabelle migriert und die Alt-Felder deprecated. Die neuen Felder (p_max, burn_number, particle_size, moisture) kommen hinzu.

### 1.2 Zonen-Erweiterungen

`ZoneDefinition` bekommt vier neue strukturelle Felder:

```python
class AtmosphereForm(models.TextChoices):
    WOLKE = "WOLKE", "Staubwolke (aufgewirbelt)"
    SCHICHT = "SCHICHT", "Staubschicht (abgelagert)"
    HYBRID = "HYBRID", "Beides relevant"

class ZoneConditionType(models.TextChoices):
    PERMANENT = "PERMANENT", "Dauerhaft vorhanden"
    MEASUREMENT_TRIGGERED = "MEAS", "Abhängig von Messung"
    ACTIVITY_LINKED = "ACTIVITY", "Tätigkeitsgebunden"


class ZoneDefinition(models.Model):
    # ... bestehende Felder ...

    # NEU — für Staubzonen
    atmosphere_form = models.CharField(
        max_length=10, choices=AtmosphereForm.choices,
        blank=True,
        help_text="Nur bei Staubzonen 20/21/22 relevant"
    )

    # NEU — für konditionale Zonen
    zone_condition_type = models.CharField(
        max_length=20, choices=ZoneConditionType.choices,
        default=ZoneConditionType.PERMANENT,
    )

    # NEU — strukturierte Geometrie
    geometry = models.JSONField(
        default=dict, blank=True,
        help_text="z.B. {'type': 'sphere', 'radius_m': 1.0, 'reference_object': 'Behälterwandung'}"
    )

    # NEU — regulatorische Begründung aus DGUV-Beispielsammlung
    derived_from_clause = models.ForeignKey(
        "explosionsschutz.ReferenceStandardClause",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
```

Weiterhin: `ConditionalZoneTrigger` als separates Modell für messungs- oder tätigkeitsgetriggerte Zonen:

```python
class ConditionalZoneTrigger(models.Model):
    zone = models.OneToOneField(
        ZoneDefinition, on_delete=models.CASCADE,
        related_name="trigger"
    )
    trigger_type = models.CharField(max_length=20)  # measurement, activity, time
    measured_variable = models.CharField(max_length=100, blank=True)
    threshold_value = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    threshold_unit = models.CharField(max_length=20, blank=True)
    fallback_zone = models.CharField(max_length=10, blank=True)
    activity_name = models.CharField(max_length=200, blank=True)
    activity_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
```

### 1.3 Vier-wertige Zündquellen-Bewertung

`ZoneIgnitionSourceAssessment.assessment_status` ersetzt die bisherigen zwei Booleans `is_present` / `is_mitigated` durch einen Enum-Wert:

```python
class IgnitionAssessmentStatus(models.TextChoices):
    NOT_PRESENT = "NOT_PRESENT", "Nicht vorhanden"
    TECHNICALLY_EXCLUDED = "EXCLUDED", "Vorhanden, aber technisch ausgeschlossen"
    PRESENT_MITIGATED = "MITIGATED", "Vorhanden und wirksam begegnet"
    PRESENT_ACCEPTED = "ACCEPTED", "Vorhanden, akzeptiert mit konstruktivem Schutz"
```

**Breaking Change:** Bestehende Daten werden migriert über eine Mapping-Funktion:
- `is_present=False` → `NOT_PRESENT`
- `is_present=True, is_mitigated=True` → `PRESENT_MITIGATED`
- `is_present=True, is_mitigated=False` → `PRESENT_ACCEPTED`

Die `TECHNICALLY_EXCLUDED`-Kategorie wird nur für neue Einträge verfügbar.

### 1.4 OperationalStateMatrix

Neues Modell für die 5-Betriebszustände-GBU-Matrix (Normalbetrieb, An-/Abfahrvorgänge, Fehlbedienung, Energieausfall, Wartung):

```python
class OperationalState(models.TextChoices):
    NORMAL = "NORMAL", "Normalbetrieb"
    STARTUP_SHUTDOWN = "START_STOP", "An-/Abfahrvorgänge"
    MALFUNCTION = "MALFUNC", "Fehlbedienung / Störung"
    ENERGY_FAILURE = "ENERGY", "Energieausfall"
    MAINTENANCE = "MAINT", "Wartung / Instandhaltung"


class OperationalStateAssessment(models.Model):
    # concept über component.concept ableitbar — kein eigenes FK (ADR-044: Redundanz vermieden)
    component = models.ForeignKey(
        "AnlageComponent", on_delete=models.CASCADE,
        related_name="operational_state_assessments",
    )
    state = models.CharField(max_length=12, choices=OperationalState.choices)

    failure_possible = models.BooleanField()
    mitigation_measure_text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["component", "state"],
                name="uniq_state_assessment_per_component"
            )
        ]
```

### 1.5 Anlagen-Hierarchie

Neue 3-Ebenen-Hierarchie `Area → AnlageComponent → SubComponent`, die in den Praxis-Dokumenten durchgängig sichtbar war:

```python
class AnlageComponent(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="components"
    )
    parent_component = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE,
        related_name="children"
    )

    name = models.CharField(max_length=200)
    component_type = models.CharField(max_length=50)  # ofen, filter, gebinde, leitung, ...

    commissioning_date = models.DateField(null=True, blank=True)
    legacy_installation = models.BooleanField(
        default=False,
        help_text="Bestandsanlage ohne ATEX-Zulassung (§ 15 BetrSichV entfällt)"
    )

    mobility_type = models.CharField(
        max_length=20, blank=True,
        choices=[("STATIONARY", "Stationär"), ("MOBILE", "Mobil"),
                 ("TRANSPORTABLE", "Transportabel")]
    )
```

Das Bestandsschutz-Flag `legacy_installation` beeinflusst automatisch die Anhang-I-Checkliste (1.8(2-3) entfällt) und die Prüfpflichten (§ 15 BetrSichV entfällt vor Inbetriebnahme).

### 1.6 MSR-Safety-Function mit TRGS 725 Klassifizierung

Das Herzstück der quantitativen MSR-Bewertung nach TRGS 725 Tabelle 3:

```python
class MsrRealizationType(models.TextChoices):
    TECHNICAL = "TECH", "Technische MSR-Einrichtung"
    ORGANIZATIONAL = "ORG", "Organisatorisches Verfahren"
    COMBINED = "COMB", "Kombiniert technisch und organisatorisch"


class MsrSafetyFunction(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.PROTECT,
        related_name="safety_functions"
    )
    function_name = models.CharField(max_length=200)
    realization_type = models.CharField(
        max_length=10, choices=MsrRealizationType.choices
    )

    # Performance Level nach EN ISO 13849-1
    performance_level = models.CharField(
        max_length=1, blank=True,
        choices=[("a", "PL a"), ("b", "PL b"), ("c", "PL c"),
                 ("d", "PL d"), ("e", "PL e")],
    )
    verification_report_ref = models.CharField(
        max_length=200, blank=True,
        help_text="z.B. 'Marquis-AF-23-0135-001-1'"
    )
    verification_method = models.CharField(
        max_length=50, blank=True,
        choices=[("SISTEMA", "SISTEMA"), ("MANUAL", "Manuelle FMEA"),
                 ("EXTERNAL", "Externer Prüfbericht")]
    )

    # TRGS 725 Klassifizierungsstufe
    technical_k_level = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="K=1/2/3 rein technisch aus PL abgeleitet"
    )
    organizational_contribution_text = models.TextField(blank=True)
    resulting_k_level = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="K=1/2/3 final (technisch + organisatorisch kombiniert)"
    )

    # Ziel-Zone ohne/mit MSR — beide als FK für strukturelle Konsistenz
    zone_without_msr = models.ForeignKey(
        "ZoneDefinition", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="msr_functions_initial_zone",
        help_text="Zone-Klassifikation vor MSR-Maßnahme",
    )
    target_zone = models.ForeignKey(
        "ZoneDefinition", on_delete=models.PROTECT,
        null=True, blank=True
    )

    evaluation_narrative = models.TextField()
```

Die PL → K-Mapping-Tabelle wird als seedbare Referenzdaten in einer separaten Tabelle `TrgsK725Mapping` gehalten, nicht als Code-Konstante. Damit können TRGS-Aktualisierungen ohne Release gepflegt werden.

```python
class TrgsK725Mapping(models.Model):
    """Seedbare Tabelle: Performance Level → K-Klassifizierungsstufe (TRGS 725 Tabelle 3)."""
    performance_level = models.CharField(
        max_length=1,
        choices=[("a", "PL a"), ("b", "PL b"), ("c", "PL c"),
                 ("d", "PL d"), ("e", "PL e")],
    )
    technical_k_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    applicable_from = models.DateField(
        help_text="Gültig ab TRGS-Version (Ausgabedatum)"
    )
    applicable_until = models.DateField(
        null=True, blank=True,
        help_text="NULL = aktuell gültig"
    )
    trgs_version_note = models.CharField(
        max_length=100, blank=True,
        help_text="z.B. 'TRGS 725, Ausgabe März 2024'"
    )

    class Meta:
        db_table = "trgs_k725_mapping"
        verbose_name = "TRGS 725 PL→K Mapping"
        ordering = ["-applicable_from", "performance_level"]
```

### 1.7 Cybersecurity-Assessment

Als OneToOne auf `ExplosionConcept`, optional. Ab EU-MVO 2027 und NIS2 verpflichtend bei kritischen Anlagen:

```python
class CybersecurityAssessment(models.Model):
    concept = models.OneToOneField(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="cybersecurity_assessment"
    )

    assessment_framework = models.CharField(
        max_length=30, blank=True,
        choices=[("IEC_62443", "IEC 62443"), ("NIS2", "NIS2"),
                 ("MVO_2027", "EU-Maschinenverordnung 2027"),
                 ("CUSTOM", "Anlagen-spezifisch")]
    )

    ot_zone_classification = models.CharField(max_length=30, blank=True)
    it_network_isolated = models.BooleanField(default=True)

    access_control_type = models.CharField(
        max_length=30,
        default="STAND_ALONE",
        choices=[("STAND_ALONE", "Stand-Alone"),
                 ("INTEGRATED", "In IT-Infrastruktur integriert"),
                 ("REMOTE", "Fernzugriff möglich")],
    )
    hmi_authentication_required = models.BooleanField(default=False)
    security_levels_differentiated = models.BooleanField(default=False)

    last_security_audit_date = models.DateField(null=True, blank=True)

    threat_analysis_narrative = models.TextField()
    mitigation_measures_narrative = models.TextField()
```

### 1.8 Annex-I-Checklist-Assessment

Die 22 Mindestanforderungen aus Anhang I GefStoffV Nummer 1 werden als seedbare Referenztabelle `AnnexIChecklistItem` gehalten. Das Assessment ist ein separates Modell:

```python
class AnnexIChecklistItem(models.Model):
    # Seed-Daten, global (keine Tenant-Zuordnung)
    clause_number = models.CharField(max_length=20, unique=True)  # z.B. "1.2(3)"
    requirement_text = models.TextField()
    category = models.CharField(max_length=50)  # storage, zone_marking, etc.


class AnnexIChecklistAssessment(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="annex_i_assessments"
    )
    item = models.ForeignKey(AnnexIChecklistItem, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=20,
        choices=[("NOT_APPLICABLE", "Nicht erforderlich"),
                 ("COMPLIANT", "Erfüllt"),
                 ("NON_COMPLIANT", "Nicht erfüllt"),
                 ("PENDING", "In Bearbeitung")]
    )
    evidence_text = models.TextField(blank=True)
    corrective_action_link = models.ForeignKey(
        "actions.Action", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "item"],
                name="uniq_annex_i_per_concept"
            )
        ]
```

### 1.9 ReviewScheduleEntry mit regulatorischer Schicht

Das Modell modelliert die 4 parallelen Fristen-Achsen (TRGS 722, 723, 724, 725) plus Brand und Wirksamkeit:

```python
class RegulatoryLayer(models.TextChoices):
    PRIMARY = "TRGS_722", "Primärer Schutz (TRGS 722)"
    SECONDARY = "TRGS_723", "Sekundärer Schutz (TRGS 723)"
    TERTIARY = "TRGS_724", "Konstruktiver Schutz (TRGS 724)"
    MSR = "TRGS_725", "MSR-Schutz (TRGS 725)"
    FIRE = "FIRE", "Brandschutz"
    EFFECTIVENESS = "EFFECT", "Wirksamkeitsprüfung (§ 6(9) GefStoffV)"


class InspectorRole(models.TextChoices):
    ZPBP        = "zPbP", "Zur Prüfung befähigte Person (zPbP)"
    ZUES        = "ZUeS", "Zugelassene Überwachungsstelle (ZÜS)"
    ARBEITGEBER = "AG",   "Arbeitgeber"
    FACHFIRMA   = "FF",   "Fachfirma"


class ReviewScheduleEntry(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="review_schedule_entries"
    )
    regulatory_layer = models.CharField(
        max_length=15, choices=RegulatoryLayer.choices
    )
    measure_description = models.CharField(max_length=200)
    legal_basis = models.CharField(max_length=100)  # z.B. "TRGS 722 i.V.m. § 7(7) GefStoffV"
    interval_months = models.PositiveIntegerField(null=True, blank=True)
    first_due_date = models.DateField(null=True, blank=True)
    last_completed_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    inspector_role = models.CharField(max_length=10, choices=InspectorRole.choices)
```

### 1.10 SubstanceContainer

Für die strukturierte Erfassung von Gebinden und Druckgasflaschen:

```python
class ContainerType(models.TextChoices):
    DRUM = "DRUM", "Fass"
    CANISTER = "CAN", "Kanister"
    IBC = "IBC", "Intermediate Bulk Container"
    PRESSURE_CYLINDER = "PRESS", "Druckgasflasche"
    TANK = "TANK", "Ortsfester Tank"
    SPRAY_CAN = "SPRAY", "Spraydose"
    CARTRIDGE = "CART", "Kartusche"


class SubstanceContainer(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="containers"
    )
    substance_reference = models.ForeignKey(
        "ConceptSubstanceReference", on_delete=models.CASCADE,
    )
    container_type = models.CharField(max_length=10, choices=ContainerType.choices)
    volume_liters = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)

    # TRGS 510 Schwellen-Prüfung
    h_category = models.CharField(max_length=5, blank=True)  # H224, H225, H226
    total_mass_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Sicherheits-Features
    protective_cap_valve = models.BooleanField(default=False)  # für Druckgas
    passive_storage = models.BooleanField(default=True)
```

### 1.11 EquipmentAtexRating

Strukturierte ATEX-Kennzeichnung statt Freitext:

```python
class EquipmentAtexRating(models.Model):
    equipment = models.OneToOneField(
        "Equipment", on_delete=models.CASCADE,
        related_name="atex_rating"
    )

    # II 2G Ex db IIB T4 Gb
    equipment_group = models.CharField(
        max_length=3,
        choices=[("I", "I (Bergbau)"), ("II", "II (nicht Bergbau)"), ("III", "III (Staub)")]
    )
    equipment_category = models.CharField(
        max_length=5,
        choices=[("1G", "1G"), ("2G", "2G"), ("3G", "3G"),
                 ("1D", "1D"), ("2D", "2D"), ("3D", "3D")]
    )
    ignition_protection_type = models.CharField(
        max_length=10, blank=True,
        help_text="z.B. 'db', 'ia', 'nA', 'mb'"
    )
    explosion_group = models.CharField(
        max_length=5, blank=True,
        choices=[("IIA", "IIA"), ("IIB", "IIB"), ("IIC", "IIC"),
                 ("IIIA", "IIIA"), ("IIIB", "IIIB"), ("IIIC", "IIIC")]
    )
    temperature_class = models.CharField(max_length=3, blank=True)  # T1-T6
    equipment_protection_level = models.CharField(max_length=3, blank=True)  # Ga/Gb/Gc, Da/Db/Dc
```

### 1.12 ApprovalStatement

Für die formelle Freigabe-Erklärung (Valmet/DHRW-Stil):

```python
class ApprovalStatement(models.Model):
    concept = models.OneToOneField(
        "ExplosionConcept", on_delete=models.PROTECT,
        related_name="approval_statement"
    )

    statement_template_id = models.CharField(max_length=50)
    rendered_text = models.TextField()  # Template nach Variablen-Ersetzung
    legal_framework_reference = models.CharField(
        max_length=100,
        help_text="z.B. '§ 6(9) GefStoffV i.V.m. § 6(4) BetrSichV'"
    )

    signatory_role = models.CharField(
        max_length=50,
        choices=[("ARBEITGEBER", "Arbeitgeber"),
                 ("BETREIBER", "Betreiber"),
                 ("ARBEITGEBER_BETREIBER", "Arbeitgeber/Betreiber")]
    )

    # approved_by_id ist UUIDField (Compliance-Pflicht, kein FK)
    signed_by_id = models.UUIDField()
    signed_by_name = models.CharField(max_length=200)
    signed_by_role = models.CharField(max_length=100)
    signed_at = models.DateTimeField()

    # Digitale Signatur optional
    digital_signature_hash = models.CharField(max_length=128, blank=True)
```

### 1.13 ReferenceStandardClause

Hierarchische Absatz-Referenzen für DGUV-Beispielsammlung und andere Regelwerke:

```python
class ReferenceStandardClause(models.Model):
    # Global, tenant-unabhängig, seed-basiert
    standard = models.ForeignKey(
        "explosionsschutz.ReferenceStandard", on_delete=models.CASCADE,
        related_name="clauses"
    )
    clause_path = models.JSONField(
        help_text="Hierarchische Absatz-Nummerierung, z.B. [2, 3, 1, 2, 'b3']"
    )
    clause_label = models.CharField(
        max_length=50,
        help_text="Lesbare Darstellung, z.B. '2.3.1.2 b3)'"
    )
    title = models.CharField(max_length=200, blank=True)
    content_excerpt = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["standard", "clause_label"]),
        ]
```

### 1.14 ConceptApprovalSnapshot

Der immutable Audit-Freeze bei Freigabe:

```python
class ConceptApprovalSnapshot(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.PROTECT,
        related_name="approval_snapshots"
    )
    snapshot_version = models.PositiveIntegerField()

    # Serialisierte strukturierte Daten zum Freigabe-Zeitpunkt
    zones_snapshot_json = models.JSONField()
    ignition_sources_snapshot_json = models.JSONField()
    safety_functions_snapshot_json = models.JSONField()
    review_schedule_snapshot_json = models.JSONField()
    annex_i_assessment_snapshot_json = models.JSONField()
    substance_references_snapshot_json = models.JSONField()
    operational_states_snapshot_json = models.JSONField(
        default=list,
        help_text="OperationalStateAssessments zum Freigabe-Zeitpunkt eingefroren",
    )

    # FK statt UUIDField: ApprovalStatement hat BigAutoField-PK (ADR-022)
    approval_statement = models.ForeignKey(
        "ApprovalStatement",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    # immutable — kein updated_at, kein status

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "snapshot_version"],
                name="uniq_snapshot_per_version"
            )
        ]
```

Snapshots werden ausschließlich durch den `ConceptApprovalService` erstellt, niemals manuell bearbeitet. Die Beziehung zu `OutputDocument` läuft über `approval_statement` (FK).

### 1.15 ConceptDocumentLink

Die M2M-Verknüpfung zwischen `ExplosionConcept` und den Quell-Dokumenten des Project-Dokumentenpools (aus ADR-041 Konvergenz-Memo: ersetzt `AssociatedDocument`). Ein SDB für Wasserstoff kann so von mehreren Konzepten im selben Projekt geteilt werden, ohne dupliziert zu werden:

```python
class ConceptDocumentLink(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="document_links",
    )
    document = models.ForeignKey(
        "projects.ProjectDocument", on_delete=models.PROTECT,
        related_name="concept_links",
    )
    relevance_note = models.CharField(
        max_length=200, blank=True,
        help_text="z.B. 'Primäres SDB für Zonenbewertung' oder 'Verfahrensplan Raum 04.01'"
    )

    class Meta:
        db_table = "concept_document_link"
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "document"],
                name="uniq_document_per_concept"
            )
        ]
```

## 2. Verfeinerungen bestehender Modelle (2)

### 2.1 ConceptSubstanceReference (ManyToMany mit Snapshot)

`ExplosionConcept.substance = FK(substances.Substance)` wird ersetzt durch:

```python
class SubstanceRole(models.TextChoices):
    PRIMARY = "PRIMARY", "Maßgeblicher Stoff für die Beurteilung"
    SECONDARY = "SECONDARY", "Weiterer Stoff"
    COMPARISON = "COMPARISON", "Vergleichsstoff"


class ConceptSubstanceReference(models.Model):
    concept = models.ForeignKey(
        "ExplosionConcept", on_delete=models.CASCADE,
        related_name="substance_references"
    )
    sds_revision = models.ForeignKey(
        "global_sds.SdsRevision",
        on_delete=models.PROTECT,
        help_text="Exakte SDS-Revision zum Erstellungszeitpunkt (Snapshot-Binding)"
    )
    role = models.CharField(max_length=15, choices=SubstanceRole.choices)
    release_rate_text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "sds_revision", "role"],
                name="uniq_sds_role_per_concept",
                # gleiche SDS-Revision kann mit unterschiedlichen Rollen referenziert werden
            )
        ]
```

Das SDS-Revisions-Binding ist compliance-kritisch: Ändert sich später ein SDB, ändert sich **nicht** automatisch die Bewertung. Das Impact-Event aus ADR-012 (`SAFETY_CRITICAL` bei H-Code-Änderung) löst stattdessen einen `REVIEW_REQUIRED`-Status am Konzept aus.

### 2.2 ExplosionConcept-Erweiterungen

`ExplosionConcept` bekommt neue Felder:

```python
class ExplosionConcept(models.Model):
    # ... bestehende Felder ...

    # NEU — Project-Einbettung (ADR-041, Entscheidung E2)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        null=True, blank=True,  # für 3 Monate nach Release
        related_name="explosion_concepts"
    )
    # Nach Migrationsphase: null=False, Auto-Projekt bei Direkteinstieg

    # NEU — Storage-Mode (aktive vs passive Lagerung)
    storage_mode = models.CharField(
        max_length=10, blank=True,
        choices=[("ACTIVE", "Aktive Lagerung"),
                 ("PASSIVE", "Passive Lagerung"),
                 ("PROCESS", "Verfahrensanlage")]
    )

    # NEU — Status mit Gates-Verfeinerung
    status = models.CharField(
        max_length=30,
        choices=[
            ("DRAFT", "Entwurf"),
            ("IN_PROGRESS", "In Bearbeitung"),
            ("REVIEW", "In Prüfung"),
            ("APPROVED", "Freigegeben"),
            ("APPROVED_WITH_ACTIONS", "Freigegeben mit offenen Maßnahmen"),
            ("REVIEW_REQUIRED", "Überprüfung erforderlich"),
            ("ARCHIVED", "Archiviert"),
        ]
    )

    # NEU — Revisionszähler
    revision_number = models.PositiveIntegerField(default=1)
```

Der Status `APPROVED_WITH_ACTIONS` ist neu und bildet den Praxis-Befund ab, dass freigegebene Dokumente offene Maßnahmen tragen können (siehe Raimann Filteranlage — "Betriebsanweisungen Staub offen, noch nicht erstellt").

## 3. Master-Workflow-Phasen (7 Phasen A–G operationalisiert)

Der Master-Workflow wird als Service-Layer in `apps/explosionsschutz/services/master_workflow.py` implementiert, nicht als separates Workflow-Engine-Modell. Jede Phase ist eine Service-Methode:

```python
class MasterWorkflowService:
    # concept_id ist int (BigAutoField PK, ADR-022) — NICHT UUID
    def phase_a_setup_context(self, concept_id: int, **kwargs) -> PhaseResult: ...
    def phase_b_gbu_matrix(self, concept_id: int, **kwargs) -> PhaseResult: ...
    def phase_c_protection_hierarchy(self, concept_id: int, **kwargs) -> PhaseResult: ...
    def phase_d_operational_regime(self, concept_id: int, **kwargs) -> PhaseResult: ...
    def phase_e_validation_gates(self, concept_id: int, **kwargs) -> PhaseResult: ...
    def phase_f_approval(self, concept_id: int, **kwargs) -> PhaseResult: ...
    def phase_g_lifecycle_management(self, concept_id: int, **kwargs) -> PhaseResult: ...
```

Phase E hat vier explizite Gates (als reine Validation-Checks, kein eigenes Modell):

- `AnnexIChecklistGate`: alle AnnexIChecklistAssessments entweder `NOT_APPLICABLE` oder `COMPLIANT`
- `AtexValidationMatrixGate`: alle Zonen haben mindestens ein kompatibles Equipment mit ATEX-Rating
- `TrgsMinimumRequirementsGate`: alle regulatorisch zwingenden ReviewScheduleEntries sind gesetzt
- `MsrSafetyFunctionGate`: alle `MsrSafetyFunction`-Einträge haben ein `resulting_k_level` — Pflicht bei Anlagen mit technischen MSR-Einrichtungen (EN ISO 13849-1)

Die Transition von `REVIEW` nach `APPROVED` ruft alle vier Gates sequentiell auf. Scheitert ein Gate, wird die Transition verweigert und die Begründung als Validation-Error geliefert.

## 4. KI-Prefill-Integration

Zwei klar getrennte Wege:

### 4.1 UC-1: aifw.service.sync_completion()

KI-Unterstützung in UC-1 arbeitet auf **zwei Ebenen**:

- **Strukturierte Vorschläge** (Zonen, Zündquellen, Maßnahmen): KI generiert einen Vorschlag, der **manuell bestätigt werden muss** — der Nutzer prüft, korrigiert und akzeptiert explizit. Strukturierte Daten werden **niemals automatisch** in die Modelle geschrieben.
- **Freitext-Kapitel** (Anlagenbeschreibung, Verfahrensbeschreibung in Phase F): KI generiert Textentwürfe, die direkt übernommen oder manuell überarbeitet werden können.

In beiden Fällen läuft der Call über `iil-aifw` mit dem korrekten Modul-Import:

```python
# Korrekt: Package = iil-aifw, Python-Modul = aifw
from aifw.service import sync_completion

result = sync_completion(
    action_code="ex_concept_zones",  # oder ex_concept_measures, ex_concept_summary
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": render_prompt_from_concept(concept, section_key)},
    ],
    tenant_id=concept.tenant_id,
    object_id=str(concept.pk),  # int PK als str, kein UUID
)
```

Der Vorschlag landet im `ExplosionConceptGenerationLog` (status=PENDING). Erst nach expliziter Nutzer-Bestätigung (`ConceptAiAcceptView`) werden strukturierte Felder aktualisiert — nie automatisch.

### 4.2 UC-2: fieldprefill.prefill_field() und ExSchutzGutachten-Modell

UC-2 wird durch die dünne Wrapper-App `apps/exschutzdokument/` realisiert (Option C aus Memo). Das Kernmodell:

```python
# apps/exschutzdokument/models.py
from doc_templates.models import DocumentInstance

class ExSchutzGutachten(models.Model):
    """UC-2: Wrapper um iil-doc-templates für den Project-Container (ADR-041)."""
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ex_schutz_gutachten",
    )
    document_instance = models.OneToOneField(
        DocumentInstance,
        on_delete=models.CASCADE,
        related_name="ex_schutz_gutachten",
    )
    # Optionale Verlinkung zu UC-1 Konzept (read-only Referenz)
    compliance_anchor = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="Verknüpftes UC-1 Konzept als fachliche Referenz (kein automatischer Datenaustausch)",
    )
    tenant_id  = models.UUIDField(db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_schutz_gutachten"
        verbose_name = "Ex-Schutz-Gutachten"
```

KI-Prefill für UC-2 nutzt `iil-fieldprefill` mit korrektem Modul-Import:

```python
# Korrekt: Package = iil-fieldprefill, Python-Modul = fieldprefill
from fieldprefill import prefill_field

value = prefill_field(
    field_key="gutachten_zusammenfassung",
    prompt=llm_hint,
    action_code="ex_doc_field_prefill",
    tenant_id=str(gutachten.tenant_id),
)
```

UC-2 greift **nicht** auf UC-1-Strukturmodelle zu. Der `compliance_anchor` ist eine reine Lese-Referenz — die Übernahme von Zonen oder Maßnahmen in das Gutachten ist bewusste Redaktionsarbeit des Gutachters, keine automatische Übernahme.

## 5. Migrationsstrategie

### Phase 1 (Release): Additive Migrationen

- Neue Modelle werden hinzugefügt
- `ExplosionConcept.project` ist `null=True` (Migrationsphase, 3 Monate)
- Bestehende Daten bleiben funktional
- `Substance.phase` wird aus H-Codes heuristisch befüllt, manuelle Prüfung im Admin

### Phase 2 (+4 Wochen): Datenmigration

- `Substance.flammpunkt_c`, `ueg_vol_prozent` etc. bleiben — keine Änderung
- Bestehende `Substance.staubexplosionsklasse_kst` und `glimmtemperatur_c` werden in `DustSubstanceProperties` migriert, Alt-Felder deprecated
- Bestehende `ZoneIgnitionSourceAssessment` werden via Mapping-Funktion auf neue Enum-Werte migriert
- Bestehende `ExplosionConcept.substance` wird als `PRIMARY`-`ConceptSubstanceReference` angelegt, FK deprecated

### Phase 3 (+3 Monate): Project-FK-Härtung

- Data Migration: Konzepte ohne Projekt werden einem Auto-Projekt zugeordnet (Naming: `Auto-ExSchutz-{Bereich.name}-{created_at.date()}`)
- `ExplosionConcept.project.null` wird auf `False` gesetzt
- Dashboard zeigt Auto-Projekte separat gruppiert, Hinweis zur Konsolidierung

### Phase 4 (+6 Monate): Deprecated-Felder entfernen

- `Substance.staubexplosionsklasse_kst` und `glimmtemperatur_c` werden entfernt (Daten in `DustSubstanceProperties`)
- `ExplosionConcept.substance` FK wird entfernt
- `ZoneIgnitionSourceAssessment.is_present` und `is_mitigated` werden entfernt

## 6. Offene Detailfragen — Entscheidungen

Die vier Detailfragen aus dem Konvergenz-Memo werden hier explizit entschieden:

### O1 — Section-Template-Varianz

**Entscheidung:** Initial ein Template für UC-1 (Rempel-nahe, deterministisch) und zwei Templates für UC-2 (Rempel-Style und DHRW-Style). Weitere Varianten können später ergänzt werden. Die Templates leben in `templates/explosionsschutz/output/` als Django-Templates (`.html`) mit `section_key`-Mapping. Jinja2 wird in risk-hub nicht verwendet — Standard-Django-Template-Engine.

### O2 — Audit-Trail-Granularität

**Entscheidung:** Nur Status-Transitions (`DRAFT → IN_PROGRESS → REVIEW → APPROVED`) erzeugen Audit-Events via `emit_audit_event()`. Phasen-Transitionen innerhalb von `IN_PROGRESS` erzeugen keine Events (fließend). Ausnahme: Gate-Failures in Phase E werden audit-geloggt.

### O3 — Phase D Prüfplan

**Entscheidung:** Default aus einem Project-Level-Template `InspectionCalendarTemplate`, das regulatorische Standard-Intervalle pro `RegulatoryLayer` vorgibt. Pro ExplosionConcept kann jede `ReviewScheduleEntry` überschrieben werden (Intervall, Inspector-Role). Das Template lebt global (seedbar) als Referenzdaten.

### O4 — TRGS 725 Tabelle 3 PL→K-Mapping

**Entscheidung:** Seedbare Tabelle `TrgsK725Mapping`. Bei TRGS-Aktualisierungen wird nur die Referenzdaten-Migration nötig, kein Code-Release. Die aktuelle Version der TRGS 725 wird im `applicable_from` und `applicable_until` Feldern verwaltet, sodass historische Berechnungen nachvollziehbar bleiben.

## 7. Konsequenzen

### Positiv

- Fachliche Lücken aus der Praxis-Analyse vollständig geschlossen (Staub, Mehrstoff, MSR quantitativ, Cybersecurity)
- Saubere Trennung UC-1 (strukturiert) / UC-2 (freitext mit iil-doc-templates)
- ADR-041 Project-Container wird sinnvoll befüllt, keine Doppelstrukturen
- Die 14 neuen Items sind fokussiert — kein Über-Engineering
- Audit-Trail und Compliance-Nachweisbarkeit durch Snapshot-Mechanismen gesichert

### Negativ

- Migrationsaufwand: Die vier Phasen der Datenmigration brauchen Koordination, insbesondere für Tenants mit vielen bestehenden Konzepten
- Breaking Change bei `ZoneIgnitionSourceAssessment`: Automatische Migration ist möglich, aber TECHNICALLY_EXCLUDED-Fälle müssen manuell durchgesehen werden
- Drei-Monats-Pflichtphase für Project-FK erfordert UX-Entscheidung im Dashboard (Hinweis-Banner, Auto-Projekt-Erklärung)
- Die KI-Integration über zwei verschiedene Libraries (`iil-aifw` und `iil-fieldprefill`) erhöht die Abhängigkeiten, ist aber architektonisch die saubere Trennung

### Neutral

- `apps/exschutzdokument/` bleibt dünn (~50 Zeilen), keine größere Entwicklungs-Investition
- Die bestehende Wizard-UI in `apps/explosionsschutz/` wird um die neuen Modell-Items erweitert, nicht neu geschrieben
- Die Phase-Service-Methoden werden schrittweise implementiert (ein PR pro Phase möglich)

## 8. Implementierungs-Roadmap

| Phase | Inhalt | Aufwand |
|---|---|---|
| **1A** | Seed-Daten: `AnnexIChecklistItem`, `ReferenceStandardClause` (DGUV 113-001), `TrgsK725Mapping` | 1 Session |
| **1B** | `DustSubstanceProperties`, `Substance.phase`-Enum, Migration Alt-Felder | 1 Session |
| **1C** | `ZoneDefinition`-Erweiterungen, `ConditionalZoneTrigger`, Geometrie-Helper-Services | 2 Sessions |
| **2A** | Vier-wertige `ZoneIgnitionSourceAssessment`, Breaking-Change-Migration | 1 Session |
| **2B** | `ConceptSubstanceReference`, `SubstanceContainer`, Mehrstoff-Service `ConcernSubstanceAggregator` | 2 Sessions |
| **3A** | `MsrSafetyFunction` mit PL/K-Berechnung, `EquipmentAtexRating` | 2-3 Sessions |
| **3B** | `OperationalStateAssessment`, `AnlageComponent`-Hierarchie | 1 Session |
| **4A** | `CybersecurityAssessment` mit Templates | 1 Session |
| **4B** | `AnnexIChecklistAssessment`, `ReviewScheduleEntry` mit Gate-Services | 2 Sessions |
| **5A** | `ApprovalStatement`, `ConceptApprovalSnapshot`, Freigabe-Service | 2 Sessions |
| **5B** | Master-Workflow-Service mit 7 Phasen (A–G) als Methoden | 2-3 Sessions |
| **6** | `ExSchutzGutachten` thin app mit `compliance_anchor` | 1 Session |
| **7** | Project-FK-Härtung, Auto-Projekt-Mechanismus | 1 Session |

**Gesamtaufwand:** ~20-22 Sessions, iterativ lieferbar.

## Confirmation

Die Implementierung gilt als korrekt wenn:

- Alle 15 neuen Modelle in `src/explosionsschutz/models/` existieren, migriert und in der Admin-Oberfläche registriert sind
- `src/exschutzdokument/models.py` hat ≤ 100 Zeilen Code (kein eigenes Fach-Datenmodell)
- `MasterWorkflowService` in `services/master_workflow.py` hat alle 7 Phasen-Methoden (A–G) aufrufbar
- Alle vier Gates in Phase E geben `ValidationError` zurück wenn die entsprechenden Daten unvollständig sind
- `ConceptApprovalSnapshot` hat kein `updated_at`-Feld und keine `change`/`delete`-Permission
- `ExplosionConcept.project` ist nach Phase 3 der Datenmigration `null=False`
- `pytest src/explosionsschutz/` durchläuft fehlerfrei nach jeder Implementierungsphase
- `iil-aifw` und `iil-fieldprefill` sind als Package-Dependencies in `requirements.txt` eingetragen

## 9. Referenzen

- ADR-041 (Project-based Workflow) — Projekt-Container, OutputDocument, SectionSourceReference
- ADR-043 (planned: Two Use Cases Ex-Dokument) — UC-1/UC-2-Trennung mit thin app wird dort spezifiziert; dieses ADR implementiert den Entscheid
- ADR-012 (Shared SDS Library) — SdsRevision-Snapshot-Binding
- ADR-002 (substances/SDS) — Substance und SdsRevision als Datenquelle
- Memo Konvergenz Master-Workflow ↔ ADR-041 vom 2026-04-22
- Praxis-Sammlung: 6 reale Ex-Schutzdokumente analysiert (Thales, Rempel, DHRW)
- TRGS 720, 721, 722, 723, 724, 725
- DGUV Regel 113-001
- EN ISO 13849-1, IEC 62443, NIS2, EU-MVO 2023/1230
- GefStoffV Anhang I Nummer 1, § 6(9)

---

**Ende ADR-044**
