# ADR-041: Projektbasiertes Arbeiten als zentrales Architekturprinzip

- **Status:** Proposed
- **Datum:** 2026-03-27
- **Entscheider:** Achim Dehnert
- **Betroffene Module:** projects (NEU), explosionsschutz, substances, global_sds, gbu, brandschutz, risk, documents, ai_analysis
- **Use Cases:** [UC-PROJECT-WORKFLOW](../use-cases/UC-PROJECT-WORKFLOW.md)

## Kontext

Schutztat (risk-hub) besteht aus mehreren Fachmodulen (Explosionsschutz, Gefahrstoffe,
GBU, Brandschutz, Risikobewertung), die aktuell unabhängig voneinander arbeiten.

In der Praxis bearbeitet ein Sicherheitsingenieur jedoch immer ein **konkretes Projekt**
(Kundenauftrag, Standortbewertung, Anlagenprüfung), das Elemente aus mehreren Modulen
kombiniert. Die Projektunterlagen (PDFs, Pläne, SDS, Gutachten) werden von mehreren
Modulen gemeinsam genutzt.

### Probleme im Ist-Zustand

1. **Kein Projektcontainer** — Daten sind pro Modul isoliert, kein gemeinsamer Kontext
2. **Dokument-Upload pro Konzept** — Ein SDS oder Anlagenplan betrifft aber mehrere Bereiche
3. **KI-Kontext zu breit** — LLM-Prefill nutzt alle Dokumente blind statt gezielter Quellauswahl
4. **Kein Lebenszyklus** — Kein Abschluss, keine Archivierung, keine Revisionen
5. **Modulauswahl fehlt** — User kann nicht wählen, welche Aspekte ein Auftrag umfasst

## Entscheidung

Wir führen ein **Projekt** als übergeordneten, modulübergreifenden Container ein.

### Architektur

```
Tenant → Site → Project ──→ ProjectDocument[]  (Input: PDFs, DXFs, Links)
                         ──→ ProjectSource[]    (Internet-Referenzen mit Snapshot)
                         ──→ Area[]             (Betriebsbereiche)
                         ──→ ExplosionConcept[] (Ex-Konzepte)
                         ──→ GBU[]              (Gefährdungsbeurteilungen)
                         ──→ Brandschutz[]      (Brandschutzmaßnahmen)
                         ──→ Assessment[]       (Risikobewertungen)
                         ──→ OutputDocument[]   (Ex-Schutzdokument, GBU-Bericht, ...)
                               └── DocumentSection[] (Abschnitte mit KI + Quellen)
```

### Neue App: `projects`

Das `Project`-Model lebt in einer **eigenständigen App** `projects`, da es
modulübergreifend ist und nicht einem einzelnen Fachmodul gehört.

### Kernprinzipien

1. **Projekt = Container** für einen Kundenauftrag mit allen Unterlagen und Ergebnissen
2. **KI-gestützte Projektinitialisierung** — User beschreibt Projekt in Freitext,
   KI empfiehlt Module basierend auf Beschreibung, User bestätigt/passt an
3. **Modulauswahl pro Projekt** — begrenzt durch gebuchte Tenant-Subscriptions (django-module-shop).
   KI weist auf nicht-gebuchte aber empfohlene Module hin (Upselling-Moment)
4. **Dokumente auf Projektebene** — nicht pro Konzept, sondern projektübergreifend
5. **KI-Generierung pro Abschnitt** — User wählt Quellen (Dokumente, Links, DB-Daten) pro Abschnitt
6. **Snapshot + Live-Check** für Internet-Referenzen — juristische Nachvollziehbarkeit
7. **Granulare Quellenzuordnung** — Seite/Absatz, nicht nur Dokument
8. **Archivierung bei Projektabschluss** — User-gesteuert, archivierte Dokumente tenant-weit verfügbar

## Models (Entwurf)

### Project

```python
class Project(models.Model):
    """Zentraler Projektcontainer — modulübergreifend."""
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        ON_HOLD = "on_hold", "Pausiert"
        COMPLETED = "completed", "Abgeschlossen"
        ARCHIVED = "archived", "Archiviert"

    # BigAutoField (Platform-Prinzip) + separates UUID für externe Referenz
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    site = models.ForeignKey("tenancy.Site", on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    project_number = models.CharField(max_length=50, blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)  # Freitext für KI-Analyse

    # Modulzuordnung über separate Tabelle ProjectModule (nicht JSONField)
    # → project.modules.filter(status="active") für aktive Module
    # → project.modules.filter(status="declined") für bewusst abgelehnte

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "project"
```

### ProjectModule (Modul-Zuordnung pro Projekt)

```python
class ProjectModule(models.Model):
    """Modul-Zuordnung pro Projekt — ersetzt JSONField.

    Vorteile gegenüber JSONField:
    - Referenzielle Integrität und DB-Index
    - Metadaten pro Modul (KI-Empfehlung, Aktivierungsdatum)
    - enabled + declined in einer Tabelle
    - Abfragbar: Project.objects.filter(modules__module="ex", modules__status="active")
    - Erweiterbar ohne Migration bei neuen Modulen
    """
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        DECLINED = "declined", "Bewusst abgelehnt"
        DEACTIVATED = "deactivated", "Nachträglich deaktiviert"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="modules")
    module = models.CharField(max_length=50, db_index=True)  # "explosionsschutz", "gbu", ...

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_ai_recommended = models.BooleanField(default=False)
    ai_reason = models.TextField(blank=True)  # KI-Begründung für Empfehlung
    activated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_module"
        unique_together = [("project", "module")]
```

**Nutzung:**
```python
# Aktive Module
project.modules.filter(status="active").values_list("module", flat=True)
# Bewusst abgelehnt (mit KI-Begründung)
project.modules.filter(status="declined")
# Alle Projekte mit Ex-Schutz
Project.objects.filter(modules__module="explosionsschutz", modules__status="active")
```

### ProjectDocument (Input-Unterlagen)

```python
class ProjectDocument(models.Model):
    """Hochgeladene Projektunterlage mit OCR und KI-Summary."""
    class DocType(models.TextChoices):
        SDS = "sds", "Sicherheitsdatenblatt"
        PLAN = "plan", "Grundriss/Anlagenplan"
        GUTACHTEN = "gutachten", "Bestehendes Gutachten"
        REGULATION = "regulation", "Regelwerk/Norm"
        PROCESS = "process", "Verfahrensbeschreibung"
        OTHER = "other", "Sonstiges"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")

    title = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    file = models.FileField(upload_to="projects/docs/%Y/%m/")

    # Extraktion
    extracted_text = models.TextField(blank=True)
    page_count = models.IntegerField(null=True)
    ai_summary = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "project_document"
```

### ProjectSource (Internet-Referenzen mit Snapshot)

```python
class ProjectSource(models.Model):
    """Externe Quelle mit Snapshot für Nachvollziehbarkeit."""
    class SourceType(models.TextChoices):
        URL = "url", "Internet-Link"
        REGULATION = "regulation", "Regelwerk (TRGS, EN, ...)"
        STANDARD = "standard", "Norm (DIN, ISO, ...)"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sources")

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    title = models.CharField(max_length=255)
    url = models.URLField()

    # Snapshot
    snapshot_text = models.TextField(blank=True)
    snapshot_date = models.DateTimeField(null=True)
    snapshot_hash = models.CharField(max_length=64, blank=True)  # SHA256

    # Aktualitätsprüfung
    last_checked = models.DateTimeField(null=True)
    has_changed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "project_source"
```

### OutputDocument + DocumentSection (Ex-Schutzdokument)

```python
class OutputDocument(models.Model):
    """Generiertes Ausgabedokument (Ex-Schutzdokument, GBU-Bericht, ...)."""
    # kind als CharField (nicht TextChoices) — erweiterbar ohne Migration
    # Bekannte Werte: ex_schutz, gbu, brandschutz, risk,
    # betriebsanweisung, schulungsnachweis, ...

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="output_documents")

    kind = models.CharField(max_length=50)  # Frei erweiterbar, keine TextChoices
    title = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "project_output_document"


class DocumentSection(models.Model):
    """Abschnitt im Ausgabedokument mit KI-Generierung und Quellenzuordnung."""
    document = models.ForeignKey(OutputDocument, on_delete=models.CASCADE, related_name="sections")

    section_key = models.CharField(max_length=50)   # "1_allgemeines", "4_zoneneinteilung"
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    content = models.TextField(blank=True)           # Generierter/bearbeiteter Text
    is_ai_generated = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_document_section"
        ordering = ["order"]


class SectionSourceReference(models.Model):
    """Granulare Quellenzuordnung pro Abschnitt (Seite/Absatz)."""
    section = models.ForeignKey(DocumentSection, on_delete=models.CASCADE, related_name="source_refs")

    # Quelle: entweder Dokument oder externe Quelle
    document = models.ForeignKey(ProjectDocument, on_delete=models.CASCADE, null=True, blank=True)
    source = models.ForeignKey(ProjectSource, on_delete=models.CASCADE, null=True, blank=True)

    # Granularität
    page_from = models.IntegerField(null=True, blank=True)
    page_to = models.IntegerField(null=True, blank=True)
    paragraph = models.TextField(blank=True)        # Relevanter Textauszug
    relevance_note = models.TextField(blank=True)   # Warum diese Quelle hier

    class Meta:
        db_table = "project_section_source_ref"
```

### ArchivedDocument (Tenant-weite Dokumentenbibliothek)

```python
class ArchivedDocument(models.Model):
    """Archiviertes Dokument — tenant-weit verfügbar für alle Projekte.

    Eigene Tabelle statt Flag auf ProjectDocument für:
    - Eigene Metadaten (Kategorien, Freigabe, Zugriffsrechte)
    - Performante tenant-weite Suche (eigener Index)
    - Cross-Projekt-Sharing ohne Projekt-FK
    - Zukunftssicher erweiterbar (Versionierung, ACLs)
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    # Referenz zum Originaldokument (kann null sein für manuell archivierte)
    source_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="archived_documents",
    )
    source_document = models.ForeignKey(
        ProjectDocument, on_delete=models.SET_NULL, null=True, blank=True,
    )

    title = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=50)
    file = models.FileField(upload_to="archive/docs/%Y/%m/")
    extracted_text = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)

    # Archiv-Metadaten
    category = models.CharField(max_length=50, blank=True)  # sds, gutachten, norm, ...
    tags = models.JSONField(default=list, blank=True)
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    archived_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "archived_document"
        indexes = [
            models.Index(fields=["tenant_id", "doc_type"], name="ix_archive_tenant_type"),
            models.Index(fields=["tenant_id", "category"], name="ix_archive_tenant_cat"),
        ]
```

## FK-Änderungen an bestehenden Models

Alle bestehenden Models erhalten ein **optionales** FK zum Projekt:

| Model | Änderung |
|-------|----------|
| `explosionsschutz.Area` | + `project = FK(Project, null=True, blank=True)` |
| `explosionsschutz.ExplosionConcept` | + `project = FK(Project, null=True, blank=True)` |
| `gbu.HazardAssessmentActivity` | + `project = FK(Project, null=True, blank=True)` |
| `risk.Assessment` | + `project = FK(Project, null=True, blank=True)` |
| `brandschutz.*` | + `project = FK(Project, null=True, blank=True)` |

`null=True` gewährleistet Rückwärtskompatibilität — bestehende Daten ohne Projekt
funktionieren weiterhin.

## Implementierungsplan

| Phase | Inhalt | Aufwand |
|-------|--------|---------|
| **P1** | `projects` App: Model, Migration, Dashboard, CRUD | 1–2 Sessions |
| **P2** | ProjectDocument: Upload, OCR, KI-Klassifizierung, Summary | 1–2 Sessions |
| **P3** | FK-Integration: Area, Concept an Project binden | 1 Session |
| **P4** | OutputDocument + Abschnitt-Editor + Quell-Auswahl + KI-Generierung | 2–3 Sessions |
| **P5** | ProjectSource: Internet-Referenzen mit Snapshot + Live-Check | 1 Session |
| **P6** | Projektabschluss: Archivierungsdialog, Status-Workflow | 1 Session |
| **P7** | PDF-Export des fertigen Dokuments mit Quellenverzeichnis | 1 Session |
| **P8** | GBU + Brandschutz Integration in Projektkontext | 1–2 Sessions |

**Gesamtaufwand:** ~10–14 Sessions (iterativ lieferbar ab Phase 1)

## Alternativen (betrachtet, verworfen)

### A) ExplosionConcept zum Projekt aufwerten

**Verworfen:** ExplosionConcept ist fachlich zu granular (pro Stoff/Bereich) und
gehört nur zum Ex-Schutz-Modul. Ein Projekt umfasst mehrere Konzepte und Module.

### B) Projekt in `common`-App

**Verworfen:** `common` enthält Utilities, kein Fachkonzept. Eine eigene App
`projects` hat klare Boundaries und eigene URL-Patterns.

### C) Kein Projekt-Entity, nur Tags/Labels

**Verworfen:** Ohne strukturelles Containment keine echte Modulverknüpfung,
kein Lifecycle, kein Dashboard. Tags lösen das Problem nicht.

## Konsequenzen

### Positiv
- Realer Kundenauftrag wird 1:1 im System abgebildet
- KI-Generierung mit gezielter Quellauswahl → bessere Ergebnisse
- Modulübergreifende Zusammenarbeit ermöglicht
- Nachvollziehbare Quellen (juristisch relevant)
- Klarer Lebenszyklus: Aktiv → Abgeschlossen → Archiviert

### Negativ
- Initialer Aufwand: 10–14 Sessions
- Alle Module müssen optional FK zum Projekt unterstützen
- Migration bestehender Daten erfordert manuelle Zuordnung durch User

### Neutral
- Dashboard wird projektbasiert (bestehende Modul-Direkteinstiege bleiben als Shortcut)
- Bestehende URLs/APIs bleiben funktional (Rückwärtskompatibilität)

## Referenzen

- [UC-PROJECT-WORKFLOW](../use-cases/UC-PROJECT-WORKFLOW.md) — Detaillierte Use Cases
- ADR-001: Explosionsschutz-Modul (wird durch Projekt-Integration erweitert)
- ADR-008: Module 1-3 GBU/Compliance/Ex-Dokument
- ADR-040: django-module-shop (Subscription-System für Modulauswahl)
