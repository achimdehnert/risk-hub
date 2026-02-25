# ADR-001: Explosionsschutz-Modul für Risk-Hub

| Metadaten | |
|-----------|---|
| **Status** | 🔄 REVIEW REQUESTED |
| **Version** | 3.0 |
| **Datum** | 2026-01-31 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Reviewer** | _ausstehend_ |
| **Entscheidungsdatum** | _ausstehend_ |

---

## 📋 Executive Summary

Dieses ADR beschreibt die Architektur für ein **Explosionsschutz-Modul** innerhalb der Risk-Hub-Plattform. Das Modul ermöglicht die digitale Erstellung, Verwaltung und Dokumentation von Explosionsschutzkonzepten gemäß ATEX-Richtlinien, BetrSichV und TRGS 720-725.

### Kernentscheidungen

| # | Entscheidung | Begründung |
|---|--------------|------------|
| 1 | Integration in bestehendes `Assessment`-Model | Vermeidet Datensilos, nutzt vorhandene Workflows |
| 2 | Nutzung von `Organization → Site → Area` Hierarchie | Konsistenz mit Risk-Hub Core |
| 3 | HTMX für interaktive UI-Komponenten | Bewährter Stack, keine SPA-Komplexität |
| 4 | WeasyPrint für PDF-Generierung | Open Source, CSS-basiert, Docker-kompatibel |
| 5 | Separates `Equipment`-Model mit ATEX-Kennzeichnung | Prüfpflichten nach BetrSichV §§14-16 |
| 6 | **Integration mit `substances`-Modul (SDS)** | Stoffdaten als Basis für Ex-Bewertung |

---

## 1. Kontext und Problemstellung

### 1.1 Geschäftsanforderung

Risk-Hub-Kunden benötigen ein digitales Werkzeug zur:

- **Erstellung** von Explosionsschutzkonzepten nach TRGS 720ff
- **Dokumentation** der Zoneneinteilung nach ATEX
- **Verwaltung** von Schutzmaßnahmen (primär, sekundär, konstruktiv)
- **Nachverfolgung** von Prüffristen für Ex-geschützte Betriebsmittel
- **Generierung** rechtssicherer Explosionsschutzdokumente (§6 GefStoffV)

### 1.2 Regulatorischer Rahmen

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EUROPÄISCHE EBENE                                │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │ ATEX 114 (2014/34)  │    │ ATEX 153 (1999/92)  │                │
│  │ Gerätehersteller    │    │ Betreiberpflichten  │                │
│  └─────────────────────┘    └─────────────────────┘                │
├─────────────────────────────────────────────────────────────────────┤
│                    NATIONALE EBENE (DE)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  BetrSichV   │  │  GefStoffV   │  │   ArbSchG    │              │
│  │  §§5-16      │  │  §6(9)       │  │              │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│                    TECHNISCHE REGELN                                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│  │TRGS 720│ │TRGS 721│ │TRGS 722│ │TRGS 723│ │TRGS 725│           │
│  │Grundl. │ │Beurteig│ │Maßnahm.│ │Gefährl.│ │Gase    │           │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘           │
│  ┌────────┐ ┌────────┐                                             │
│  │TRBS1111│ │TRBS2152│                                             │
│  │Gef.Beu.│ │Prüfung │                                             │
│  └────────┘ └────────┘                                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 ATEX-Zoneneinteilung

| Zone | Atmosphäre | Häufigkeit | Gerätekategorie |
|------|------------|------------|-----------------|
| **Zone 0** | Gas/Dampf/Nebel | Ständig/langanhaltend | 1G |
| **Zone 1** | Gas/Dampf/Nebel | Gelegentlich im Normalbetrieb | 2G |
| **Zone 2** | Gas/Dampf/Nebel | Selten, kurzzeitig | 3G |
| **Zone 20** | Staub | Ständig/langanhaltend | 1D |
| **Zone 21** | Staub | Gelegentlich im Normalbetrieb | 2D |
| **Zone 22** | Staub | Selten, kurzzeitig | 3D |

---

## 2. Entscheidungstreiber

### 2.1 Funktionale Anforderungen

| ID | Anforderung | Priorität | Quelle |
|----|-------------|-----------|--------|
| FR-01 | Erfassung von Explosionsschutzkonzepten | Must | GefStoffV §6 |
| FR-02 | Zoneneinteilung mit Begründung | Must | TRGS 720 |
| FR-03 | Dokumentation Schutzmaßnahmen (3-stufig) | Must | TRGS 722 |
| FR-04 | Verwaltung Ex-geschützter Betriebsmittel | Must | BetrSichV §14 |
| FR-05 | Prüffristenverwaltung mit Erinnerungen | Must | BetrSichV §16 |
| FR-06 | PDF-Export Explosionsschutzdokument | Must | GefStoffV §6(9) |
| FR-07 | Versionierung von Ex-Dokumenten | Should | Nachweispflicht |
| FR-08 | Import von Stoffdaten (UEG, OEG, Zündtemp.) | Should | Usability |
| FR-09 | Visualisierung Zoneneinteilung | Could | Usability |
| FR-10 | MSR-Bewertung (PLr/SIL) | Could | TRGS 725 |

### 2.2 Nicht-funktionale Anforderungen

| ID | Anforderung | Zielwert |
|----|-------------|----------|
| NFR-01 | Multi-Tenancy | Vollständige Datenisolation |
| NFR-02 | Audit-Trail | Alle Änderungen nachvollziehbar |
| NFR-03 | Response Time | < 2s für Seitenaufbau |
| NFR-04 | PDF-Generierung | < 5s für Dokument |
| NFR-05 | Offline-Fähigkeit | Nicht erforderlich (Phase 1) |

---

## 3. Betrachtete Optionen

### Option A: Standalone Ex-Schutz-App (abgelehnt)

```
[Separate Django App] ←→ [Eigene DB] ←→ [Eigenes Auth]
```

**Vorteile:**
- Unabhängige Entwicklung
- Eigener Release-Zyklus

**Nachteile:**
- Datensilos (keine Verknüpfung zu bestehenden Assessments)
- Doppelte Benutzerverwaltung
- Inkonsistente UI/UX
- Höherer Wartungsaufwand

### Option B: Integration in Risk-Hub Core (gewählt ✅)

```text
┌───────────────────────────────────────────────────────────────────┐
│                         RISK-HUB PLATFORM                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │  tenancy    │  │  identity   │  │  documents  │               │
│  │  (Org/Site) │  │  (User/Role)│  │  (S3/MinIO) │               │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │
│         │                │                │                       │
│  ┌──────┴────────────────┴────────────────┴──────┐               │
│  │                    risk                        │               │
│  │             (Assessment + Hazard)              │               │
│  └────────────────────┬───────────────────────────┘               │
│                       │                                           │
│         ┌─────────────┴─────────────┐                            │
│         │                           │                            │
│         ▼                           ▼                            │
│  ┌─────────────────┐        ┌─────────────────┐                  │
│  │   substances    │◄──────►│explosionsschutz │  ← NEU          │
│  │   (SDS-Modul)   │        │  (Ex-Konzept)   │                  │
│  │                 │        │                 │                  │
│  │ • Substance     │        │ • Area          │                  │
│  │ • SdsRevision   │        │ • ExConcept     │                  │
│  │ • H-/P-Sätze    │        │ • Zone          │                  │
│  │ • Inventory     │        │ • Measure       │                  │
│  │ • Pictograms    │        │ • Equipment     │                  │
│  └─────────────────┘        │ • Inspection    │                  │
│                             └─────────────────┘                  │
└───────────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- Nutzt bestehende Infrastruktur (Auth, Tenancy, Audit)
- Verknüpfung mit vorhandenen Gefährdungsbeurteilungen
- Konsistente UI/UX
- Gemeinsames Dokumentenmanagement

**Nachteile:**
- Abhängigkeit von Risk-Hub Core Releases
- Komplexeres Datenbankschema

### Option C: Microservice-Architektur (zurückgestellt)

Für Phase 2+ bei Bedarf nach höherer Skalierbarkeit.

---

## 4. Entscheidung

### 4.1 Gewählte Option

**Option B: Integration in Risk-Hub Core** als neue Django-App `explosionsschutz`.

### 4.2 Begründung

1. **Konsistenz**: Einheitliche Benutzererfahrung innerhalb Risk-Hub
2. **Effizienz**: Wiederverwendung bestehender Models und Services
3. **Rechtssicherheit**: Gemeinsamer Audit-Trail für alle Risikobewertungen
4. **Time-to-Market**: Schnellere Implementierung durch vorhandene Basis

---

## 5. Integration mit Substances-Modul (SDS)

### 5.1 SDS als "Domain Anchor"

Das `substances`-Modul (Sicherheitsdatenblatt-Register) dient als zentrale Datenbasis für alle EHS-Module, einschließlich Explosionsschutz. Die Stoffdaten aus dem SDS liefern die sicherheitsrelevanten Parameter für die Ex-Bewertung.

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    SDS ALS "DOMAIN ANCHOR"                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                       ┌─────────────┐                               │
│                       │  Substance  │                               │
│                       │  (SDS-Daten)│                               │
│                       └──────┬──────┘                               │
│                              │                                      │
│         ┌────────────────────┼────────────────────┐                │
│         │                    │                    │                │
│         ▼                    ▼                    ▼                │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │
│  │    GBU      │     │   Lager     │     │ Betriebsan- │          │
│  │ Gefahrstoff │     │  TRGS 510   │     │   weisung   │          │
│  └─────────────┘     └─────────────┘     └─────────────┘          │
│         │                    │                    │                │
│         ▼                    ▼                    ▼                │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │
│  │ ▶ Ex-Schutz │     │   Audits    │     │Unterweisung │          │
│  │   ATEX      │     │             │     │             │          │
│  └─────────────┘     └─────────────┘     └─────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Ex-relevante Daten aus SDS

| SDS-Abschnitt | Datenfeld | Ex-Relevanz |
|---------------|-----------|-------------|
| **Abschnitt 2** | H-Sätze (H220, H225, H226...) | Entzündbarkeit, Ex-Gruppe |
| **Abschnitt 2** | GHS-Piktogramme (GHS02) | Kennzeichnung Ex-Bereiche |
| **Abschnitt 9** | Flammpunkt | Zoneneinteilung |
| **Abschnitt 9** | UEG/OEG (Vol-%) | Ex-Grenzen für Bewertung |
| **Abschnitt 9** | Zündtemperatur | Temperaturklasse (T1-T6) |
| **Abschnitt 9** | Dampfdruck | Freisetzungsverhalten |
| **Abschnitt 14** | Explosionsgruppe (IIA/IIB/IIC) | Geräteauswahl |

### 5.3 Verknüpfung Substance ↔ ExplosionConcept

```python
# Erweiterung ExplosionConcept Model

class ExplosionConcept(models.Model):
    """Explosionsschutzkonzept - erweitert um Substance-Verknüpfung"""
    
    # ... bestehende Felder ...
    
    # NEU: Verknüpfung zum Substances-Modul
    substance = models.ForeignKey(
        "substances.Substance",
        on_delete=models.PROTECT,
        related_name="explosion_concepts",
        help_text="Verknüpfter Gefahrstoff aus SDS-Register"
    )
    
    # Stoffdaten werden aus SDS übernommen (read-only, cached)
    @property
    def sds_data(self) -> dict:
        """Explosionsrelevante Daten aus aktuellem SDS"""
        sds = self.substance.current_sds
        if not sds:
            return {}
        
        return {
            "substance_name": self.substance.name,
            "cas_number": self.substance.cas_number,
            "h_statements": [h.code for h in sds.hazard_statements.all()],
            "pictograms": [p.code for p in sds.pictograms.all()],
            "signal_word": sds.classification.signal_word if hasattr(sds, 'classification') else None,
            "storage_class": self.substance.storage_class,
            "is_cmr": self.substance.is_cmr,
        }
    
    @property
    def is_explosive_atmosphere_possible(self) -> bool:
        """Prüft ob explosionsfähige Atmosphäre möglich (H220-H226)"""
        explosive_h_codes = {"H220", "H221", "H222", "H223", "H224", "H225", "H226"}
        return bool(set(self.sds_data.get("h_statements", [])) & explosive_h_codes)
```

### 5.4 SiteInventoryItem als Auslöser für Ex-Bewertung

Wenn ein Gefahrstoff mit Ex-relevanten H-Sätzen einem Standort hinzugefügt wird, sollte automatisch eine Ex-Prüfung angestoßen werden:

```python
# substances/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

EXPLOSIVE_H_CODES = {"H220", "H221", "H222", "H223", "H224", "H225", "H226", 
                     "H228", "H240", "H241", "H242"}

@receiver(post_save, sender=SiteInventoryItem)
def check_explosion_hazard(sender, instance, created, **kwargs):
    """Prüft bei neuem Inventareintrag auf Ex-Gefährdung"""
    if not created:
        return
    
    substance = instance.substance
    current_sds = substance.current_sds
    
    if not current_sds:
        return
    
    h_codes = set(h.code for h in current_sds.hazard_statements.all())
    
    if h_codes & EXPLOSIVE_H_CODES:
        # Ex-relevanter Stoff am Standort → Hinweis/Task erstellen
        from outbox.models import OutboxMessage
        OutboxMessage.objects.create(
            tenant_id=instance.tenant_id,
            topic="explosionsschutz.review_required",
            payload={
                "site_id": str(instance.site_id),
                "substance_id": str(substance.id),
                "substance_name": substance.name,
                "h_codes": list(h_codes & EXPLOSIVE_H_CODES),
                "reason": "Neuer Ex-relevanter Gefahrstoff am Standort"
            }
        )
```

### 5.5 Abhängigkeiten substances → explosionsschutz

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    MODULE DEPENDENCIES                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  explosionsschutz ──────┬───────► substances (Substance, SDS)      │
│       │                 │                                           │
│       │                 ├───────► tenancy (Organization, Site)     │
│       │                 │                                           │
│       │                 ├───────► risk (Assessment)                │
│       │                 │                                           │
│       │                 ├───────► documents (DocumentVersion, S3)  │
│       │                 │                                           │
│       │                 ├───────► identity (User)                  │
│       │                 │                                           │
│       │                 ├───────► permissions (RBAC, Scope)        │
│       │                 │                                           │
│       │                 └───────► audit (AuditEvent)               │
│       │                                                             │
│       └─────────────────────────► outbox (OutboxMessage)           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Technische Architektur

### 6.1 Datenmodell

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BESTEHENDE MODELS                           │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐  │
│  │  Organization  │────►│      Site      │────►│   Assessment   │  │
│  │  (tenancy)     │     │   (tenancy)    │     │    (risk)      │  │
│  └────────────────┘     └───────┬────────┘     └───────┬────────┘  │
│                                 │                      │           │
├─────────────────────────────────┼──────────────────────┼───────────┤
│                         NEUE MODELS                    │           │
│                                 │                      │           │
│                         ┌───────▼────────┐     ┌──────▼─────────┐ │
│                         │      Area      │     │ExplosionConcept│ │
│                         │ (Betriebsber.) │◄────│  (Ex-Konzept)  │ │
│                         └───────┬────────┘     └───────┬────────┘ │
│                                 │                      │          │
│                         ┌───────▼────────┐     ┌──────▼─────────┐ │
│                         │   Equipment    │     │ ZoneDefinition │ │
│                         │ (Betriebsmit.) │     │ (Zoneneinteil.)│ │
│                         └───────┬────────┘     └────────────────┘ │
│                                 │                      │          │
│                         ┌───────▼────────┐     ┌──────▼─────────┐ │
│                         │   Inspection   │     │ProtectionMeas. │ │
│                         │   (Prüfung)    │     │ (Schutzmaßn.)  │ │
│                         └────────────────┘     └────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Model-Definitionen

#### Area (Betriebsbereich)
```python
class Area(models.Model):
    """Betriebsbereich oder Anlage innerhalb eines Standorts."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    site = models.ForeignKey("tenancy.Site", on_delete=models.CASCADE)
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True)  # z.B. "E2-50.01"
    description = models.TextField(blank=True)
    
    has_explosion_hazard = models.BooleanField(default=False)
    substances = models.JSONField(default=list)  # ["H2", "CH4"]
    
    class Meta:
        db_table = "ex_area"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site", "code"],
                name="uq_area_code_per_site"
            )
        ]
```

#### ExplosionConcept (Explosionsschutzkonzept)
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
        "risk.Assessment",
        on_delete=models.CASCADE,
        limit_choices_to={"category": "explosionsschutz"}
    )
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    
    # Stoffdaten
    substance_name = models.CharField(max_length=100)
    substance_formula = models.CharField(max_length=20, blank=True)
    explosion_group = models.CharField(max_length=10, blank=True)  # IIA/IIB/IIC
    temperature_class = models.CharField(max_length=10, blank=True)  # T1-T6
    lower_explosion_limit = models.DecimalField(
        max_digits=5, decimal_places=2, null=True,
        help_text="Untere Explosionsgrenze in Vol-%"
    )
    upper_explosion_limit = models.DecimalField(
        max_digits=5, decimal_places=2, null=True,
        help_text="Obere Explosionsgrenze in Vol-%"
    )
    ignition_temperature = models.IntegerField(
        null=True,
        help_text="Zündtemperatur in °C"
    )
    
    # Substitutionsprüfung (§6 GefStoffV)
    substitution_checked = models.BooleanField(default=False)
    substitution_possible = models.BooleanField(default=False)
    substitution_reason = models.TextField(blank=True)
    
    # Status & Validierung
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    validated_by = models.ForeignKey(
        "identity.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    
    # Review-Zyklus (§6(9) GefStoffV: mind. alle 3 Jahre)
    review_interval_months = models.IntegerField(default=36)
    next_review_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "ex_concept"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "next_review_date"]),
        ]
```

#### ZoneDefinition (Zoneneinteilung)
```python
class ZoneDefinition(models.Model):
    """Zoneneinteilung nach ATEX."""
    
    ZONE_CHOICES = [
        ("0", "Zone 0"),
        ("1", "Zone 1"),
        ("2", "Zone 2"),
        ("20", "Zone 20"),
        ("21", "Zone 21"),
        ("22", "Zone 22"),
        ("non_ex", "Nicht Ex"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        ExplosionConcept, on_delete=models.CASCADE, related_name="zones"
    )
    
    zone = models.CharField(max_length=10, choices=ZONE_CHOICES)
    location_description = models.CharField(max_length=200)
    justification = models.TextField(help_text="Begründung der Einstufung")
    
    # Ausdehnung
    extent_horizontal = models.CharField(max_length=100, blank=True)
    extent_vertical = models.CharField(max_length=100, blank=True)
    extent_geometry = models.JSONField(null=True, blank=True)  # GeoJSON
    
    # Referenzen
    trgs_reference = models.CharField(max_length=100, blank=True)
    
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = "ex_zone"
        ordering = ["order"]
```

#### ProtectionMeasure (Schutzmaßnahme)
```python
class ProtectionMeasure(models.Model):
    """Explosionsschutzmaßnahme nach TRGS 722."""
    
    TYPE_CHOICES = [
        ("primary", "Primär (Vermeidung expl. Atmosphäre)"),
        ("secondary", "Sekundär (Zündquellenvermeidung)"),
        ("constructive", "Konstruktiv (Auswirkungsbegrenzung)"),
        ("organizational", "Organisatorisch"),
    ]
    
    VERIFICATION_CHOICES = [
        ("pending", "Ausstehend"),
        ("verified", "Verifiziert"),
        ("failed", "Nicht bestanden"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        ExplosionConcept, on_delete=models.CASCADE, related_name="measures"
    )
    
    measure_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Technische Details (optional je nach Maßnahmentyp)
    inert_gas = models.CharField(max_length=20, blank=True)  # N2, CO2
    concentration_limit = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    monitoring_method = models.CharField(max_length=200, blank=True)
    
    # MSR-Sicherheitseinrichtung
    is_safety_device = models.BooleanField(default=False)
    performance_level = models.CharField(
        max_length=5, blank=True,
        help_text="PLa bis PLe nach ISO 13849"
    )
    sil_level = models.IntegerField(
        null=True, blank=True,
        help_text="SIL 1-3 nach IEC 61508"
    )
    
    # Verifikation
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default="pending"
    )
    verification_date = models.DateField(null=True, blank=True)
    verification_document = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL, null=True, blank=True
    )
    
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = "ex_measure"
        ordering = ["measure_type", "order"]
```

#### Equipment (Betriebsmittel)
```python
class Equipment(models.Model):
    """Betriebsmittel mit optionaler ATEX-Kennzeichnung."""
    
    CATEGORY_CHOICES = [
        ("1G", "1G (Zone 0/1/2)"),
        ("2G", "2G (Zone 1/2)"),
        ("3G", "3G (Zone 2)"),
        ("1D", "1D (Zone 20/21/22)"),
        ("2D", "2D (Zone 21/22)"),
        ("3D", "3D (Zone 22)"),
        ("non_ex", "Nicht-Ex"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="equipment")
    
    # Identifikation
    name = models.CharField(max_length=200)
    equipment_number = models.CharField(max_length=50, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    
    # ATEX-Kennzeichnung
    is_atex_certified = models.BooleanField(default=False)
    atex_marking = models.CharField(
        max_length=100, blank=True,
        help_text="z.B. II 2G Ex d IIC T6 Gb"
    )
    equipment_category = models.CharField(
        max_length=10, choices=CATEGORY_CHOICES, default="non_ex"
    )
    protection_type = models.CharField(
        max_length=50, blank=True,
        help_text="Ex d, Ex e, Ex i, Ex p, Ex n, etc."
    )
    
    # Prüffristen
    inspection_interval_months = models.IntegerField(
        default=12,
        help_text="Prüfintervall in Monaten"
    )
    last_inspection = models.DateField(null=True, blank=True)
    next_inspection = models.DateField(null=True, blank=True)
    
    # Dokumentation
    certificate = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+"
    )
    
    is_active = models.BooleanField(default=True)
    decommissioned_at = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = "ex_equipment"
        indexes = [
            models.Index(fields=["tenant_id", "next_inspection"]),
            models.Index(fields=["tenant_id", "is_active"]),
        ]
```

#### Inspection (Prüfung)
```python
class Inspection(models.Model):
    """Wiederkehrende Prüfung nach BetrSichV."""
    
    TYPE_CHOICES = [
        ("visual", "Sichtprüfung"),
        ("close", "Nahprüfung"),
        ("detailed", "Eingehende Prüfung"),
        ("zus", "Prüfung durch ZÜS"),
    ]
    
    RESULT_CHOICES = [
        ("passed", "Bestanden"),
        ("conditional", "Bestanden mit Auflagen"),
        ("failed", "Nicht bestanden"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="inspections"
    )
    
    inspection_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    scheduled_date = models.DateField()
    
    # Durchführung
    performed_date = models.DateField(null=True, blank=True)
    performed_by = models.ForeignKey(
        "identity.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    external_inspector = models.CharField(max_length=200, blank=True)
    
    # Ergebnis
    result = models.CharField(
        max_length=20, choices=RESULT_CHOICES, null=True, blank=True
    )
    findings = models.TextField(blank=True)
    corrective_actions = models.TextField(blank=True)
    
    # Protokoll
    protocol = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # Folgeprüfung
    next_inspection_date = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = "ex_inspection"
        ordering = ["-scheduled_date"]
```

### 5.3 API-Endpunkte

```python
# urls.py (explosionsschutz app)
urlpatterns = [
    # Concepts
    path("concepts/", views.ConceptListView.as_view(), name="concept-list"),
    path("concepts/<uuid:pk>/", views.ConceptDetailView.as_view(), name="concept-detail"),
    path("concepts/<uuid:pk>/pdf/", views.concept_pdf, name="concept-pdf"),
    
    # HTMX Partials
    path("concepts/<uuid:pk>/zones/", views.zone_list, name="zone-list"),
    path("concepts/<uuid:pk>/zones/add/", views.zone_create, name="zone-create"),
    path("zones/<uuid:pk>/edit/", views.zone_edit, name="zone-edit"),
    path("zones/<uuid:pk>/delete/", views.zone_delete, name="zone-delete"),
    
    path("concepts/<uuid:pk>/measures/", views.measure_list, name="measure-list"),
    path("concepts/<uuid:pk>/measures/add/", views.measure_create, name="measure-create"),
    path("measures/<uuid:pk>/edit/", views.measure_edit, name="measure-edit"),
    path("measures/<uuid:pk>/delete/", views.measure_delete, name="measure-delete"),
    
    path("concepts/<uuid:pk>/progress/", views.concept_progress, name="concept-progress"),
    
    # Equipment
    path("equipment/", views.EquipmentListView.as_view(), name="equipment-list"),
    path("equipment/<uuid:pk>/", views.EquipmentDetailView.as_view(), name="equipment-detail"),
    path("equipment/due/", views.equipment_due_inspections, name="equipment-due"),
    
    # Inspections
    path("inspections/", views.InspectionListView.as_view(), name="inspection-list"),
    path("inspections/<uuid:pk>/complete/", views.inspection_complete, name="inspection-complete"),
]
```

### 5.4 HTMX-Komponenten

```
templates/explosionsschutz/
├── concept_list.html
├── concept_detail.html
├── concept_form.html
├── equipment_list.html
├── equipment_detail.html
├── inspection_list.html
├── partials/
│   ├── zone_list.html           # hx-get refreshable
│   ├── zone_form.html           # hx-post inline
│   ├── zone_row.html            # Single zone row
│   ├── measure_list.html        # Grouped by type
│   ├── measure_form.html        # hx-post inline
│   ├── measure_row.html         # Single measure row
│   ├── progress_bar.html        # Completion indicator
│   ├── equipment_card.html      # Equipment summary
│   └── inspection_modal.html    # Complete inspection
└── pdf/
    └── explosionsschutzdokument.html
```

#### Beispiel: Maßnahmenliste mit HTMX
```html
<!-- partials/measure_list.html -->
<div id="measures-{{ measure_type }}" class="space-y-2">
  {% for measure in measures %}
  <div id="measure-{{ measure.id }}" 
       class="p-4 border rounded-lg bg-white shadow-sm">
    <div class="flex justify-between items-start">
      <div>
        <h4 class="font-medium">{{ measure.title }}</h4>
        <p class="text-sm text-gray-600">{{ measure.description|truncatewords:20 }}</p>
        {% if measure.is_safety_device %}
        <span class="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
          MSR {{ measure.performance_level }}
        </span>
        {% endif %}
      </div>
      <div class="flex gap-2">
        <button hx-get="{% url 'explosionsschutz:measure-edit' measure.id %}"
                hx-target="#measure-{{ measure.id }}"
                hx-swap="outerHTML"
                class="text-blue-600 hover:text-blue-800">
          Bearbeiten
        </button>
        <button hx-delete="{% url 'explosionsschutz:measure-delete' measure.id %}"
                hx-target="#measure-{{ measure.id }}"
                hx-swap="outerHTML swap:1s"
                hx-confirm="Maßnahme wirklich löschen?"
                class="text-red-600 hover:text-red-800">
          Löschen
        </button>
      </div>
    </div>
  </div>
  {% empty %}
  <p class="text-gray-500 italic">Keine Maßnahmen definiert.</p>
  {% endfor %}
  
  <button hx-get="{% url 'explosionsschutz:measure-create' concept.id %}?type={{ measure_type }}"
          hx-target="#measures-{{ measure_type }}"
          hx-swap="beforeend"
          class="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg 
                 text-gray-500 hover:border-blue-500 hover:text-blue-500">
    + Maßnahme hinzufügen
  </button>
</div>
```

---

## 6. Konsequenzen

### 6.1 Positive Konsequenzen

| # | Konsequenz | Nutzen |
|---|------------|--------|
| 1 | Integrierte Datenbasis | Keine Datensilos zwischen Modulen |
| 2 | Gemeinsamer Audit-Trail | Rechtssichere Nachvollziehbarkeit |
| 3 | Konsistente UI/UX | Reduzierte Einarbeitungszeit |
| 4 | Automatische Prüferinnerungen | Compliance-Sicherheit |
| 5 | PDF-Export | Erfüllt Dokumentationspflicht |

### 6.2 Negative Konsequenzen

| # | Konsequenz | Mitigation |
|---|------------|------------|
| 1 | Schema-Komplexität (+6 Models) | Saubere Dokumentation |
| 2 | Migration bestehender Daten | Migrationsscript bereitstellen |
| 3 | ATEX-Fachwissen erforderlich | Tooltip/Hilfe in UI |

### 6.3 Risiken

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| Regulatorische Änderungen | Mittel | Mittel | Konfigurierbare Regelwerksreferenzen |
| Performance bei vielen Zonen | Niedrig | Niedrig | Pagination, Lazy Loading |
| PDF-Generierung langsam | Mittel | Niedrig | Async mit Celery Task |

---

## 8. Implementierungsplan

### Voraussetzung: substances-Modul (SDS)

> **WICHTIG:** Das `explosionsschutz`-Modul setzt das `substances`-Modul voraus.  
> SDS-Implementierung gemäß [Schutzbar_SDS_Implementierungskonzept.md](../concepts/Schutzbar_SDS_Implementierungskonzept.md)

```text
Phase 0: SDS-Modul Basis (Voraussetzung, Sprint 1-4)
├── Substance + Party + Identifier Models
├── SdsRevision + Classification Models
├── H-/P-Sätze + Piktogramme
├── SiteInventoryItem
└── Referenztabellen (H-/P-Satz-Texte)

Phase 1: Ex-Core Models (Sprint 5-6)
├── Area Model + Migration
├── ExplosionConcept Model + Substance-FK
├── ZoneDefinition Model + Migration
├── ProtectionMeasure Model + Migration
├── Signal: SiteInventoryItem → Ex-Review-Trigger
├── Admin Interface
└── Unit Tests

Phase 2: Equipment & Inspections (Sprint 7-8)
├── Equipment Model + ATEX-Kennzeichnung
├── Inspection Model + ZÜS-Protokoll
├── Prüffristenlogik (auto next_inspection)
├── Benachrichtigungsservice (Outbox)
└── Unit Tests

Phase 3: UI/UX (Sprint 9-11)
├── Concept CRUD Views
├── Substance-Selector (aus SDS-Modul)
├── Zone Editor (HTMX)
├── Measure Management (HTMX)
├── SDS-Daten-Anzeige (read-only)
├── Progress Indicator
├── Equipment Views
└── E2E Tests (Playwright)

Phase 4: PDF & Integration (Sprint 12)
├── PDF Template Explosionsschutzdokument
├── WeasyPrint Integration
├── Assessment-Verknüpfung
├── SDS-Daten im PDF (H-Sätze, Piktogramme)
└── API Documentation

Phase 5: QA & Release (Sprint 13-14)
├── Security Review
├── Performance Tests
├── User Documentation
└── Production Deployment
```

### Gantt-Übersicht

```text
Sprint:  1   2   3   4   5   6   7   8   9  10  11  12  13  14
         │   │   │   │   │   │   │   │   │   │   │   │   │   │
Phase 0  ████████████████████                              (SDS)
Phase 1                      ██████████                      (Ex Core)
Phase 2                                  ██████████              (Equipment)
Phase 3                                              ███████████████  (UI)
Phase 4                                                          █████  (PDF)
Phase 5                                                              ██████████ (QA)
```

---

## 8. Review-Checkliste

### Für Reviewer

- [ ] Sind alle regulatorischen Anforderungen abgedeckt?
- [ ] Ist das Datenmodell normalisiert und konsistent?
- [ ] Sind die HTMX-Patterns mit bestehenden Risk-Hub-Konventionen kompatibel?
- [ ] Ist der Implementierungsplan realistisch?
- [ ] Fehlen wichtige Use Cases?

### Offene Fragen

1. ~~Soll eine Stoffdatenbank (UEG, OEG, Zündtemperatur) integriert werden?~~  
   → **Gelöst:** Wird über `substances`-Modul (SDS) bereitgestellt
2. Ist eine visuelle Zonendarstellung (CAD-Import, SVG-Editor) in Phase 1 erforderlich?
3. Welche Benutzerrollen benötigen Zugriff (SiFa, Betreiber, ZÜS)?
4. **NEU:** Soll der Ex-Review-Trigger (bei neuem SiteInventoryItem) automatisch Tasks erstellen?

---

## 9. Referenzen

| Dokument | Link |
|----------|------|
| ATEX 114 Richtlinie | [EUR-Lex](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32014L0034) |
| TRGS 720-725 | [BAuA](https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS.html) |
| BetrSichV | [Gesetze im Internet](https://www.gesetze-im-internet.de/betrsichv_2015/) |
| IEC 60079-10-1 | [IEC Webstore](https://webstore.iec.ch/publication/63327) |
| ChatGPT Vorschlag | [ex schutz.md](../concepts/ex%20schutz.md) |
| **Schutzbar SDS Konzept** | [Schutzbar_SDS_Implementierungskonzept.md](../concepts/Schutzbar_SDS_Implementierungskonzept.md) |

---

## 10. Änderungshistorie

| Version | Datum | Autor | Änderung |
|---------|-------|-------|----------|
| 1.0 | 2026-01-31 | Cascade | Initial Draft |
| 2.0 | 2026-01-31 | Cascade | Review-Ready Version |
| 3.0 | 2026-01-31 | Cascade | **SDS-Integration** - Schutzbar SDS-Konzept integriert |

---

**Review angefordert von:** Achim Dehnert  
**Review-Deadline:** _zu definieren_  
**Nächster Schritt nach Approval:** Phase 1 Implementierung starten
