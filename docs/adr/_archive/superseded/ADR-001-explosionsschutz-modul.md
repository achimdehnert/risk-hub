# ADR-001: Explosionsschutz-Modul für Risk-Hub

**Status:** Proposed  
**Datum:** 2026-01-31  
**Autor:** Cascade (AI-Assisted)  
**Entscheidungsträger:** Achim Dehnert

---

## Kontext

Risk-Hub soll um ein vollständiges **Explosionsschutz-Modul** erweitert werden, das folgende regulatorische Anforderungen erfüllt:

### Regulatorischer Rahmen

| Regelwerk | Beschreibung | Relevanz |
|-----------|--------------|----------|
| **ATEX 114** (2014/34/EU) | Geräte für explosionsgefährdete Bereiche | Geräteauswahl |
| **ATEX 153** (1999/92/EG) | Schutz der Arbeitnehmer | Betreiberpflichten |
| **BetrSichV** §§5-16 | Betriebssicherheitsverordnung | Prüfpflichten |
| **GefStoffV** §6(9) | Gefahrstoffverordnung | Ex-Dokument-Pflicht |
| **TRGS 720-725** | Technische Regeln Gefahrstoffe | Zoneneinteilung |
| **TRBS 1111** | Technische Regeln Betriebssicherheit | Gefährdungsbeurteilung |
| **IEC 60079** | Internationale Normenreihe | Geräteauswahl |

### Zoneneinteilung nach ATEX

**Gase/Dämpfe/Nebel:**
- **Zone 0**: Explosionsfähige Atmosphäre ständig/häufig vorhanden
- **Zone 1**: Gelegentlich im Normalbetrieb
- **Zone 2**: Selten und nur kurzzeitig

**Stäube/Fasern:**
- **Zone 20**: Ständig/häufig als Wolke vorhanden
- **Zone 21**: Gelegentlich im Normalbetrieb
- **Zone 22**: Selten und nur kurzzeitig

---

## Bewertung der ChatGPT-Vorschläge

### ✅ Stärken der Vorschläge

1. **Modulare Architektur** - Sinnvolle Trennung in Gefährdungsbeurteilung, Ex-Konzept, Maßnahmen
2. **Django + HTMX** - Passt perfekt zum bestehenden Risk-Hub Stack
3. **Zoneneinteilung mit JSON** - Flexibel für visuelle Darstellung
4. **Dreistufiges Maßnahmenkonzept** (Primär/Sekundär/Konstruktiv) - Entspricht TRGS 722
5. **PDF-Export** - Rechtlich erforderlich für Nachweisführung
6. **Fortschrittsanzeige** - Gute UX für komplexe Formulare

### ⚠️ Schwächen & Verbesserungsbedarf

| Vorschlag | Problem | Empfehlung |
|-----------|---------|------------|
| `Company → Location → Area` | Redundant zu bestehendem `Organization → Site` | **Bestehende Models nutzen** |
| `ExplosionProtectionConcept` als eigenständig | Sollte an `Assessment` gekoppelt sein | **FK zu Assessment** |
| Keine Prüffristen-Logik | §15/§16 BetrSichV erfordert Prüfzyklen | **Inspection-Model erweitern** |
| Keine ATEX-Geräte-Verwaltung | Geräte mit Ex-Kennzeichnung fehlen | **Equipment-Model hinzufügen** |
| Keine Audit-Trail | Änderungen müssen nachvollziehbar sein | **Django-auditlog nutzen** |
| Keine Versionierung | Ex-Dokumente brauchen Versionshistorie | **Document-Model nutzen** |

### ❌ Fehlende Aspekte

1. **PLr-Bewertung nach SISTEMA** - Performance Level für MSR-Einrichtungen
2. **Zündquellenanalyse** - Systematische Erfassung aller 13 Zündquellen nach EN 1127-1
3. **Stoffdatenbank** - UEG, OEG, Zündtemperatur, Explosionsgruppe
4. **Prüfprotokolle** - Strukturierte Erfassung von ZÜS/ZpBP-Prüfungen
5. **Fremdfirmen-Management** - Arbeitsfreigaben für Ex-Bereiche

---

## Entscheidung

### Architektur-Entscheidung

```
┌─────────────────────────────────────────────────────────────────┐
│                        RISK-HUB CORE                            │
├─────────────────────────────────────────────────────────────────┤
│  Organization ──► Site ──► Area ──► Equipment                   │
│       │              │        │          │                      │
│       └──────────────┴────────┴──────────┘                      │
│                      │                                          │
│              Assessment (category=explosionsschutz)             │
│                      │                                          │
│       ┌──────────────┼──────────────┐                          │
│       ▼              ▼              ▼                          │
│   Hazard    ExplosionConcept    Measure                        │
│       │              │              │                          │
│       │      ┌───────┴───────┐      │                          │
│       │      ▼               ▼      │                          │
│       │   ZoneDefinition  ProtectionMeasure                    │
│       │                              │                          │
│       └──────────────────────────────┘                          │
│                      │                                          │
│              Inspection ◄── InspectionSchedule                  │
│                      │                                          │
│              Document ◄── DocumentVersion                       │
└─────────────────────────────────────────────────────────────────┘
```

### Neue Models

#### 1. Area (Bereich/Anlage)
```python
class Area(models.Model):
    """Betriebsbereich oder Anlage innerhalb eines Standorts."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="areas")
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True)  # z.B. "E2-50.01"
    description = models.TextField(blank=True)
    
    # Ex-Relevanz
    has_explosion_hazard = models.BooleanField(default=False)
    substances = models.JSONField(default=list)  # ["H2", "CH4", ...]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 2. ExplosionConcept (Explosionsschutzkonzept)
```python
class ExplosionConcept(models.Model):
    """Explosionsschutzkonzept nach TRGS 720ff."""
    
    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("review", "In Prüfung"),
        ("approved", "Freigegeben"),
        ("archived", "Archiviert"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    
    # Verknüpfungen
    assessment = models.OneToOneField(
        Assessment, 
        on_delete=models.CASCADE,
        related_name="explosion_concept",
        limit_choices_to={"category": "explosionsschutz"}
    )
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="explosion_concepts")
    
    # Stoffdaten
    substance_name = models.CharField(max_length=100)  # z.B. "Wasserstoff"
    substance_formula = models.CharField(max_length=20, blank=True)  # z.B. "H2"
    explosion_group = models.CharField(max_length=10, blank=True)  # IIA, IIB, IIC
    temperature_class = models.CharField(max_length=10, blank=True)  # T1-T6
    lower_explosion_limit = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Vol-%
    upper_explosion_limit = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ignition_temperature = models.IntegerField(null=True)  # °C
    
    # Substitutionsprüfung
    substitution_possible = models.BooleanField(default=False)
    substitution_reason = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_validated = models.BooleanField(default=False)
    validated_by_id = models.UUIDField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    
    # Review-Zyklus (§6(9) GefStoffV: mind. alle 3 Jahre)
    next_review_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 3. ZoneDefinition (Zoneneinteilung)
```python
class ZoneDefinition(models.Model):
    """Zoneneinteilung nach ATEX."""
    
    ZONE_CHOICES = [
        ("zone_0", "Zone 0 (Gas/Dampf - ständig)"),
        ("zone_1", "Zone 1 (Gas/Dampf - gelegentlich)"),
        ("zone_2", "Zone 2 (Gas/Dampf - selten)"),
        ("zone_20", "Zone 20 (Staub - ständig)"),
        ("zone_21", "Zone 21 (Staub - gelegentlich)"),
        ("zone_22", "Zone 22 (Staub - selten)"),
        ("non_ex", "Nicht explosionsgefährdet"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(ExplosionConcept, on_delete=models.CASCADE, related_name="zones")
    
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES)
    description = models.TextField()  # Begründung der Einstufung
    
    # Ausdehnung
    extent_description = models.TextField(blank=True)  # Textuelle Beschreibung
    extent_geometry = models.JSONField(null=True, blank=True)  # GeoJSON oder SVG-Koordinaten
    
    # Referenz
    trgs_reference = models.CharField(max_length=50, blank=True)  # z.B. "TRGS 722 Kap. 3.2"
    
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 4. ProtectionMeasure (Schutzmaßnahme)
```python
class ProtectionMeasure(models.Model):
    """Explosionsschutzmaßnahme nach TRGS 722."""
    
    MEASURE_TYPE_CHOICES = [
        ("primary", "Primär (Vermeidung)"),
        ("secondary", "Sekundär (Zündquellenvermeidung)"),
        ("constructive", "Konstruktiv (Auswirkungsbegrenzung)"),
        ("organizational", "Organisatorisch"),
    ]
    
    VERIFICATION_STATUS = [
        ("pending", "Ausstehend"),
        ("verified", "Verifiziert"),
        ("failed", "Nicht bestanden"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(ExplosionConcept, on_delete=models.CASCADE, related_name="measures")
    
    measure_type = models.CharField(max_length=20, choices=MEASURE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Technische Details
    gas_type = models.CharField(max_length=50, blank=True)  # z.B. "N2" für Inertisierung
    flow_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    
    # MSR-Einrichtung
    is_msr = models.BooleanField(default=False)
    performance_level = models.CharField(max_length=5, blank=True)  # PLa-PLe
    sil_level = models.IntegerField(null=True, blank=True)  # SIL 1-3
    
    # Verifikation
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default="pending")
    verification_document = models.ForeignKey(
        "documents.Document", 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 5. Equipment (Betriebsmittel mit ATEX-Kennzeichnung)
```python
class Equipment(models.Model):
    """Betriebsmittel/Gerät mit optionaler ATEX-Kennzeichnung."""
    
    EQUIPMENT_CATEGORY = [
        ("1G", "Kategorie 1G (Zone 0/1/2)"),
        ("2G", "Kategorie 2G (Zone 1/2)"),
        ("3G", "Kategorie 3G (Zone 2)"),
        ("1D", "Kategorie 1D (Zone 20/21/22)"),
        ("2D", "Kategorie 2D (Zone 21/22)"),
        ("3D", "Kategorie 3D (Zone 22)"),
        ("non_ex", "Nicht-Ex"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="equipment")
    
    name = models.CharField(max_length=200)
    manufacturer = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    
    # ATEX-Kennzeichnung
    is_atex_certified = models.BooleanField(default=False)
    atex_marking = models.CharField(max_length=100, blank=True)  # z.B. "II 2G Ex d IIC T6"
    equipment_category = models.CharField(max_length=10, choices=EQUIPMENT_CATEGORY, default="non_ex")
    explosion_group = models.CharField(max_length=10, blank=True)
    temperature_class = models.CharField(max_length=10, blank=True)
    protection_type = models.CharField(max_length=50, blank=True)  # Ex d, Ex e, Ex i, etc.
    
    # Prüffristen
    inspection_interval_months = models.IntegerField(default=12)
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_date = models.DateField(null=True, blank=True)
    
    # Dokumentation
    certificate_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="certified_equipment"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 6. Inspection (Prüfung)
```python
class Inspection(models.Model):
    """Wiederkehrende Prüfung nach BetrSichV §§14-16."""
    
    INSPECTION_TYPE = [
        ("visual", "Sichtprüfung"),
        ("detailed", "Eingehende Prüfung"),
        ("zusp", "Prüfung durch ZÜS"),
        ("internal", "Interne Prüfung"),
    ]
    
    RESULT_CHOICES = [
        ("passed", "Bestanden"),
        ("passed_with_remarks", "Bestanden mit Auflagen"),
        ("failed", "Nicht bestanden"),
        ("postponed", "Verschoben"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="inspections")
    inspection_type = models.CharField(max_length=20, choices=INSPECTION_TYPE)
    
    scheduled_date = models.DateField()
    performed_date = models.DateField(null=True, blank=True)
    performed_by_id = models.UUIDField(null=True, blank=True)
    performed_by_external = models.CharField(max_length=200, blank=True)  # ZÜS-Name
    
    result = models.CharField(max_length=30, choices=RESULT_CHOICES, null=True, blank=True)
    findings = models.TextField(blank=True)
    
    # Protokoll
    protocol_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Folgeprüfung
    next_inspection_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

### HTMX-Komponenten

#### Empfohlene Partials-Struktur
```
templates/
└── explosionsschutz/
    ├── concept_detail.html          # Hauptansicht Ex-Konzept
    ├── concept_form.html             # Formular Ex-Konzept
    ├── partials/
    │   ├── zone_list.html            # Zonenliste (HTMX-fähig)
    │   ├── zone_form.html            # Zone hinzufügen/bearbeiten
    │   ├── measure_list.html         # Maßnahmenliste nach Typ
    │   ├── measure_form.html         # Maßnahme hinzufügen
    │   ├── progress_bar.html         # Fortschrittsanzeige
    │   ├── equipment_selector.html   # Geräteauswahl
    │   └── inspection_schedule.html  # Prüfkalender
    └── pdf/
        └── explosionsschutzdokument.html  # PDF-Template
```

#### HTMX-Attribute für Live-Interaktion
```html
<!-- Maßnahme inline bearbeiten -->
<button hx-get="/ex/measure/{{id}}/edit/"
        hx-target="#measure-{{id}}"
        hx-swap="outerHTML">
    Bearbeiten
</button>

<!-- Zone hinzufügen -->
<button hx-get="/ex/concept/{{concept.id}}/zone/add/"
        hx-target="#zone-list"
        hx-swap="beforeend">
    + Zone hinzufügen
</button>

<!-- Live-Fortschritt -->
<div hx-get="/ex/concept/{{concept.id}}/progress/"
     hx-trigger="load, every 10s"
     hx-swap="innerHTML">
</div>
```

---

## Konsequenzen

### Positive Konsequenzen

1. **Rechtssicherheit** - Vollständige Abdeckung der regulatorischen Anforderungen
2. **Integration** - Nutzt bestehende Risk-Hub-Infrastruktur (Tenancy, Documents, Audit)
3. **Skalierbarkeit** - Multi-Tenant-fähig von Anfang an
4. **UX** - HTMX ermöglicht flüssige Interaktion ohne SPA-Komplexität
5. **Nachvollziehbarkeit** - Audit-Trail für alle Änderungen

### Negative Konsequenzen

1. **Komplexität** - 6 neue Models erhöhen Datenbankschema-Komplexität
2. **Migration** - Bestehende Daten müssen ggf. migriert werden
3. **Schulung** - Benutzer müssen mit ATEX-Terminologie vertraut sein

### Risiken

| Risiko | Eintrittswahrscheinlichkeit | Auswirkung | Mitigation |
|--------|---------------------------|------------|------------|
| Regulatorische Änderungen | Mittel | Hoch | Konfigurierbare Regelwerks-Referenzen |
| Performance bei vielen Zonen | Niedrig | Mittel | Pagination, Lazy Loading |
| PDF-Generierung langsam | Mittel | Niedrig | Async mit Celery |

---

## Implementierungsplan

### Phase 1: Core Models (2 Wochen)
- [ ] Area Model + Migration
- [ ] ExplosionConcept Model + Migration
- [ ] ZoneDefinition Model + Migration
- [ ] ProtectionMeasure Model + Migration
- [ ] Admin-Interface für alle Models

### Phase 2: Equipment & Inspections (2 Wochen)
- [ ] Equipment Model + Migration
- [ ] Inspection Model + Migration
- [ ] Prüffristenlogik (automatische Berechnung)
- [ ] Benachrichtigungen bei fälligen Prüfungen

### Phase 3: UI/UX (3 Wochen)
- [ ] Concept Detail View mit HTMX
- [ ] Zone-Editor (Drag & Drop optional)
- [ ] Maßnahmen-Management inline
- [ ] Fortschrittsanzeige
- [ ] Equipment-Zuordnung

### Phase 4: PDF & Export (1 Woche)
- [ ] PDF-Template Explosionsschutzdokument
- [ ] WeasyPrint Integration
- [ ] Export-API

### Phase 5: Integration & Test (2 Wochen)
- [ ] Integration in bestehendes Assessment-Modul
- [ ] Berechtigungsprüfung
- [ ] E2E-Tests
- [ ] Dokumentation

---

## Referenzen

- [ATEX Directive 2014/34/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014L0034)
- [TRGS 720-725](https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS.html)
- [BetrSichV](https://www.gesetze-im-internet.de/betrsichv_2015/)
- [IEC 60079-10-1:2020](https://webstore.iec.ch/en/publication/63327)
- [ChatGPT Vorschlag](../concepts/ex%20schutz.md)

---

## Entscheidungsprotokoll

| Datum | Entscheidung | Begründung |
|-------|--------------|------------|
| 2026-01-31 | ADR erstellt | Initiale Architekturentscheidung |
| | | |

