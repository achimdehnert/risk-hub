# ADR-011: Arbeitssicherheit-Dokumentenmanagement — Import, Kategorisierung und Verknüpfung

| Feld | Wert |
|------|------|
| **Status** | **Proposed** |
| **Version** | 1.0 |
| **Datum** | 2026-03-24 |
| **Autor** | Cascade (AI Engineering Agent) |
| **Quellen** | B.E.N.S. Arbeitssicherheit — Dokumentenübersicht (6 Praxis-Dokumente), ADR-008 (Module 1–3), ADR-009 (Gefahrstoffdatenbank) |
| **Bezug** | ADR-002 (substances), ADR-008 (GBU/Compliance/Ex-Schutz), ADR-009 (Gefahrstoffdatenbank v2.0) |

---

## Kurzfassung

Formalisierung des Dokumentenmanagements für Arbeitssicherheit in risk-hub (Schutztat),
abgeleitet aus der Analyse von 6 realen B.E.N.S.-Dokumenten. Definiert Dokumenttypen,
Kategorisierungsschema, Import-Workflow und Verknüpfungsmodell zu bestehenden Modulen
(GBU, Substances, Explosionsschutz).

---

## 1. Kontext

### 1.1 Problem Statement

Unternehmen verwalten Arbeitssicherheitsdokumente (Gefährdungsbeurteilungen, Betriebsanweisungen,
Explosionsschutzdokumente, Unterweisungsnachweise) in heterogenen Formaten: PDF-Scans, Excel-Tabellen,
Word-Dokumente. Diese müssen:

- zentral gespeichert und versioniert werden
- mit den zugehörigen Modulen (GBU, Substances, Explosionsschutz) verknüpft sein
- nach gesetzlichen Kategorien klassifiziert werden
- Prüffristen und Verantwortlichkeiten abbilden

### 1.2 Praxis-Analyse: B.E.N.S. Arbeitssicherheit (6 Dokumente)

| # | Dokumenttyp | Format | Regelwerk | Verknüpfung |
|---|------------|--------|-----------|-------------|
| 1 | GefBU nach BauAV | PDF | BauAV Art. 2 | → `gbu.HazardAssessmentActivity` |
| 2 | GefBU Betriebsspezifik (Absturz) | PDF | DGUV 1, BetrSichV, ArbStättV | → `gbu.HazardAssessmentActivity` |
| 3 | GBF Gefährdungsanalyse | PDF (Scan) | — | → `gbu.HazardAssessmentActivity` |
| 4 | GefBU Robelschraubmaschine | Excel | BetrSichV | → `gbu.HazardAssessmentActivity` + Arbeitsmittel |
| 5 | GefBU Kranhebeeinrichtungen | Excel | BetrSichV, DGUV 100-500 | → `gbu.HazardAssessmentActivity` + Arbeitsmittel |
| 6 | Explosionsschutzdokument | Word | GefStoffV § 6, DIN EN 60079 | → `explosionsschutz` Modul |

### 1.3 Decision Drivers

- **Regulatorische Pflicht**: GefStoffV, BetrSichV, ArbStättV, BauAV verlangen nachweisbare Dokumentation
- **Mandantenfähigkeit**: Dokumente sind tenant-isoliert (ADR-137 RLS)
- **Bulk-Upload**: Unternehmen laden 5–50 Dokumente gleichzeitig hoch (Phase 1 bereits deployed)
- **Verknüpfung**: Dokumente ohne Kontext (GBU, Arbeitsmittel, Gefahrstoff) sind wertlos
- **OCR/Scan-Qualität**: Gescannte PDFs (Dok. 3) erfordern OCR-Pipeline

---

## 2. Considered Options

### Option A: Flache Dokument-Ablage (Status Quo nach Phase 1)

Dokumente werden mit einer Kategorie hochgeladen, aber nicht weiter verknüpft.

- ✅ Bereits implementiert (Bulk-Upload mit 10 Kategorien)
- ❌ Keine Verknüpfung zu GBU-Aktivitäten oder Gefahrstoffen
- ❌ Keine Prüffristen oder Verantwortliche
- ❌ Kein strukturierter Import aus Excel/PDF

### Option B: Verknüpftes Dokumentenmodell (empfohlen)

Dokumente werden über GenericForeignKey oder explizite ForeignKeys mit GBU-Aktivitäten,
Arbeitsmitteln und Gefahrstoffen verknüpft.

- ✅ Kontextbezogene Dokumentenablage
- ✅ Prüffristen-Tracking pro Dokument
- ✅ Import-Pipeline für strukturierte Daten (Excel → GBU-Aktivitäten)
- ⚠️ Höherer Implementierungsaufwand (~3 Sprints)

### Option C: Dokumenten-Graph (Over-Engineering)

Volles Knowledge-Graph-Modell mit Edges zwischen allen Entitäten.

- ❌ Over-Engineering für den aktuellen Scope
- ❌ pgvector reicht für Suche, kein Graph-DB nötig

---

## 3. Decision Outcome

**Gewählt: Option B — Verknüpftes Dokumentenmodell**

### 3.1 Erweiterte Dokumentkategorien

```python
class Category(models.TextChoices):
    # Bestehend (Phase 1)
    SDB = "sdb", "Sicherheitsdatenblatt"
    GEFAEHRDUNGSBEURTEILUNG = "gefaehrdungsbeurteilung", "Gefährdungsbeurteilung"
    BETRIEBSANWEISUNG = "betriebsanweisung", "Betriebsanweisung"
    UNTERWEISUNG = "unterweisung", "Unterweisungsnachweis"
    PRUEFBERICHT = "pruefbericht", "Prüfbericht"
    # Neu (Phase 2)
    EXPLOSIONSSCHUTZ = "explosionsschutz", "Explosionsschutzdokument"
    BAUAV = "bauav", "GefBU nach BauAV"
    ARBEITSMITTEL_GEFBU = "arbeitsmittel_gefbu", "GefBU Arbeitsmittel"
    COMPLIANCE_NACHWEIS = "compliance_nachweis", "Compliance-Nachweis"
    WARTUNGSPROTOKOLL = "wartungsprotokoll", "Wartungsprotokoll"
    SCHULUNGSNACHWEIS = "schulungsnachweis", "Schulungsnachweis"
    SONSTIGES = "sonstiges", "Sonstiges"
```

### 3.2 Verknüpfungsmodell (Phase 2)

```python
class DocumentLink(TenantModel):
    """Verknüpft ein Dokument mit einer Entität (GBU, Arbeitsmittel, Gefahrstoff)."""
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.BigIntegerField()
    linked_object = GenericForeignKey("content_type", "object_id")
    link_type = models.CharField(max_length=30, choices=[
        ("evidence", "Nachweis"),
        ("source", "Quelle/Grundlage"),
        ("result", "Ergebnis/Output"),
        ("reference", "Referenz"),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
```

### 3.3 Prüffristen-Erweiterung (Phase 3)

```python
class DocumentReviewSchedule(TenantModel):
    """Prüffristen und Verantwortlichkeiten für Dokumente."""
    document = models.OneToOneField("documents.Document", on_delete=models.CASCADE)
    review_interval_months = models.PositiveSmallIntegerField(default=12)
    next_review_date = models.DateField()
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    last_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_documents"
    )
```

### 3.4 Risikomatrix aus B.E.N.S.-Dokumenten

Die GefBU-Excel-Dokumente verwenden eine W×S→R Risikomatrix:

| Wahrscheinlichkeit (W) | Schwere (S) | Risikostufe (R) |
|------------------------|-------------|-----------------|
| A (unwahrscheinlich) | I (gering) | I (vernachlässigbar) |
| B (selten) | II (mittel) | II (akzeptabel mit Maßnahmen) |
| C (gelegentlich) | III (schwer) | III (bedeutsam) |
| D (häufig) | IV (katastrophal) | STOP (nicht akzeptabel) |
| E (sehr häufig) | — | — |

Diese Matrix wird in `gbu.RiskAssessment` abgebildet (bereits in ADR-008 spezifiziert).

### 3.5 Maßnahmentypen (TOPS-Hierarchie)

```python
class MeasureType(models.TextChoices):
    TECHNICAL = "T", "Technisch (Substitution, Kapselung)"
    ORGANIZATIONAL = "O", "Organisatorisch (Unterweisung, Rotation)"
    PERSONAL = "P", "Persönlich (PSA)"
    STOP = "STOP", "Sofortmaßnahme / Nutzungsverbot"
```

---

## 4. Implementierungsplan

| Phase | Sprint | Deliverable | Abhängigkeit |
|-------|--------|-------------|-------------|
| 1 ✅ | Done | Bulk-Upload mit 10 Kategorien, Drag&Drop UI | — |
| 2 | S1 | `DocumentLink` Model + Admin + GBU-Verknüpfung | Phase 1 |
| 2 | S1 | 2 neue Kategorien (Explosionsschutz, BauAV) + Migration | Phase 1 |
| 3 | S2 | `DocumentReviewSchedule` + Prüffristen-Dashboard | Phase 2 |
| 3 | S2 | Excel-Import für GefBU-Tabellen → GBU-Aktivitäten | Phase 2 |
| 4 | S3 | OCR-Pipeline für gescannte PDFs (Celery Task) | Phase 2 |
| 4 | S3 | Regelwerk-Referenz-Datenbank (DGUV, BetrSichV, etc.) | — |

---

## 5. Consequences

### 5.1 Positive

- **Nachweisbarkeit**: Alle Dokumente sind mit GBU/Gefahrstoff/Arbeitsmittel verknüpft
- **Prüffristen**: Automatische Erinnerungen an Dokumenten-Reviews
- **Strukturierter Import**: Excel-GefBU-Tabellen werden direkt zu GBU-Aktivitäten
- **Mandanten-Isolation**: Alle neuen Models erben `TenantModel` (RLS-enforced)
- **Audit-Trail**: `DocumentVersion` + `DocumentLink` ergeben vollständigen Nachweis

### 5.2 Negative / Risiken

| Risiko | Mitigation |
|--------|-----------|
| OCR-Qualität bei Scans | Fallback: manuelles Tagging, OCR nur als Suggestion |
| Excel-Format-Varianz | Template-basierter Import mit Validierung, nicht generisch |
| GenericForeignKey Performance | Index auf (content_type, object_id), kein JOIN über alle Typen |
| Regelwerk-Updates | Jährlicher Review-Zyklus, DGUV-Newsletter als Trigger |

---

## 6. Verwandte ADRs

| ADR | Bezug |
|-----|-------|
| ADR-002 | Substances/SDS-Modul — SDB-Dokumente als Unterkategorie |
| ADR-008 | Module 1–3 (GBU, Compliance, Ex-Schutz) — Hauptkonsument |
| ADR-009 | Gefahrstoffdatenbank v2.0 — Substanzen verlinkt zu SDB-Dokumenten |
| ADR-137 | Tenant-Isolation — alle neuen Models via TenantModel + RLS |

---

*Erstellt aus B.E.N.S. Arbeitssicherheit Dokumentenübersicht (6 Praxis-Dokumente) am 2026-03-24.*
