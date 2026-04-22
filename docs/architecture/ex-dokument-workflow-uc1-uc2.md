# Ex-Dokument — Prozessworkflow UC-1 & UC-2

> **Stand:** 2026-04-22  
> **Zweck:** Schrittweise Prozessführung für beide Wege zur Erstellung eines
> Explosionsschutzdokuments nach § 6 Abs. 9 GefStoffV in risk-hub (Schutztat).

---

## Welcher Weg ist der richtige?

```mermaid
flowchart TD
    START([Explosionsschutzdokument\nerstellen]) --> F1{Worum geht es?}

    F1 -->|Bestehende Anlage\npflegen oder erstmalig\ndokumentieren| UC1
    F1 -->|Beratungsauftrag:\nNeubau, Umbau,\nexternes Gutachten| UC2
    F1 -->|Unsicher| HINT

    HINT --> |Anlage bereits in Betrieb?| UC1
    HINT --> |Ich bin externer Berater| UC2

    UC1["✅ UC-1: Compliance\nNavbar → Explosionsschutz\n/ex/\nBetreiber · SiFa · HSE-Manager"]
    UC2["📋 UC-2: Gutachten\nNavbar → Vorlagen\n/doc-templates/\nSachverständiger · Berater"]

    style START fill:#1e293b,color:#fff
    style UC1  fill:#f97316,color:#fff
    style UC2  fill:#3b82f6,color:#fff
    style HINT fill:#e2e8f0,color:#374151
```

---

## UC-1: Compliance-Workflow

> Navbar → **Explosionsschutz** · Persona: Betreiber, SiFa, HSE-Manager  
> Output: §6(9)-Pflichtdokument als PDF · Wiederholung alle 24 Monate (TRGS 720 Nr. 5)

```mermaid
flowchart TD
    classDef step    fill:#fff7ed,stroke:#f97316,color:#1e293b
    classDef ki      fill:#eff6ff,stroke:#3b82f6,color:#1e293b
    classDef gate    fill:#faf5ff,stroke:#8b5cf6,color:#1e293b
    classDef done    fill:#f0fdf4,stroke:#22c55e,color:#1e293b
    classDef repeat  fill:#fefce8,stroke:#eab308,color:#1e293b

    S1["① BEREICH ANLEGEN\n/ex/areas/create/\nName · Standort · Verantwortlicher"]:::step
    S2["② KONZEPT ERSTELLEN\n/ex/concepts/new/\nTitel · Betriebsbereich · Stoff (SDS)"]:::step
    S3["③ ZONEN KLASSIFIZIEREN\nTab: Zonen\nZone 0 / 1 / 2 · Typ · Ausdehnung · Begründung"]:::step
    KI1["🤖 KI: Zonen-Vorschlag\n/ex/concepts/pk/ai/zones/\nVorschlag annehmen oder korrigieren"]:::ki
    S4["④ ZÜNDQUELLEN BEWERTEN\nTab: Zonen → Zündquellen\n13 Arten nach EN 1127-1\nje Zone bewerten"]:::step
    KI2["🤖 KI: Zündquellen-Vorschlag\n/ex/concepts/pk/ai/ignition/\nVorschlag annehmen oder korrigieren"]:::ki
    S5["⑤ SCHUTZMASSNAHMEN ERFASSEN\nTab: Maßnahmen\nTechnisch / Organisatorisch / Substitution\nFälligkeitsdatum setzen"]:::step
    KI3["🤖 KI: Maßnahmen-Vorschlag\n/ex/concepts/pk/ai/measures/\nVorschlag annehmen oder korrigieren"]:::ki
    S6["⑥ BETRIEBSMITTEL PRÜFEN\n/ex/equipment/\nATEX-Kategorie · Schutzart · Temperaturklasse\nPrüfprotokoll anlegen"]:::step
    S7["⑦ VALIDIEREN\n/ex/concepts/pk/validate/\nVollständigkeit prüfen\nKlärungsbedarf lösen"]:::gate
    KI4["🤖 KI: Zusammenfassung\n/ex/concepts/pk/ai/summary/\nAudit-sichere Zusammenfassung"]:::ki
    S8["⑧ EXPORTIEREN & ARCHIVIEREN\n/ex/concepts/pk/export/pdf/\nPDF · Status: approved\nnext_review_date setzen"]:::done
    REV["� REVISION\nnach Änderung oder alle 24 Monate\n→ zurück zu Schritt ②"]:::repeat

    S1 --> S2 --> S3
    S3 <-.->|optional| KI1
    S3 --> S4
    S4 <-.->|optional| KI2
    S4 --> S5
    S5 <-.->|optional| KI3
    S5 --> S6 --> S7
    S7 <-.->|optional| KI4
    S7 --> S8 --> REV
    REV --> S2
```

### Schritte auf einen Blick — UC-1

| # | Schritt | URL | Ergebnis |
|---|---------|-----|----------|
| ① | Bereich anlegen | `/ex/areas/create/` | `Area` mit Standort |
| ② | Konzept erstellen | `/ex/concepts/new/` | `ExplosionConcept` status=draft |
| ③ | Zonen klassifizieren | Konzept-Detail → Tab Zonen | `ZoneDefinition` (Zone 0/1/2) |
| ④ | Zündquellen bewerten | Konzept-Detail → Tab Zonen | `ZoneIgnitionSourceAssessment` (13 Arten) |
| ⑤ | Schutzmaßnahmen | Konzept-Detail → Tab Maßnahmen | `ProtectionMeasure` (TOPS) |
| ⑥ | Betriebsmittel | `/ex/equipment/` | `Equipment` + `Inspection` |
| ⑦ | Validieren | `/ex/concepts/pk/validate/` | Status: in_review |
| ⑧ | Export + Archiv | `/ex/concepts/pk/export/pdf/` | PDF, Status: approved |
| 🔄 | Revision | alle 24 Monate / bei Änderung | neues Konzept aus Schritt ② |

---

## UC-2: Gutachten-Workflow

> Navbar → **Vorlagen** · Persona: Sachverständiger, externer Berater  
> Output: Ausformuliertes Gutachten (Word/PDF) · Einmalig je Projekt

```mermaid
flowchart TD
    classDef step  fill:#eff6ff,stroke:#3b82f6,color:#1e293b
    classDef ki    fill:#f0fdf4,stroke:#22c55e,color:#1e293b
    classDef gate  fill:#faf5ff,stroke:#8b5cf6,color:#1e293b
    classDef done  fill:#f0fdf4,stroke:#22c55e,color:#1e293b
    classDef opt   fill:#fefce8,stroke:#eab308,color:#1e293b,stroke-dasharray:4 3

    T1A["① a  PDF HOCHLADEN\n/doc-templates/upload/\nBestehendes Ex-Dokument als Basis\n→ Abschnitte auto-erkannt"]:::step
    T1B["① b  LEERE VORLAGE\n/doc-templates/create/\nStruktur von Grund auf aufbauen"]:::step
    T2["② VORLAGE STRUKTURIEREN\n/doc-templates/pk/edit/\nAbschnitte benennen\nFeld-Typen wählen:\nFreitext · Tabelle · Kurztext · Ja/Nein"]:::step
    T3["③ KI-HINTS KONFIGURIEREN\nPro Feld: 🤖 KI EIN / AUS\nllm_hint = Beschreibung was generiert werden soll\nScope = explosionsschutz"]:::step
    T4["④ DOKUMENT ERSTELLEN\n/doc-templates/pk/instance/create/\nDocumentInstance anlegen\nName · Projekt · Mandant"]:::step
    T5["⑤ KAPITEL AUSFÜLLEN\n/doc-templates/instance/pk/edit/\nFeld für Feld bearbeiten"]:::step
    KI1["🤖 KI: Feld-Prefill\n/doc-templates/instance/pk/prefill/\niil-fieldprefill · pro Feld\nVorschlag annehmen / korrigieren"]:::ki
    KI2["🤖 KI: Bulk-Prefill\n/doc-templates/instance/pk/bulk-prefill/\nAlle KI-Felder auf einmal befüllen"]:::ki
    T6["⑥ FACHLICH PRÜFEN\nSachverständiger-Review\nInhalt verantworten · Korrekturen einarbeiten\nStatus: review"]:::gate
    T7["⑦ FREIGEBEN & EXPORTIEREN\n/doc-templates/instance/pk/pdf/\nStatus: approved\nExport: PDF oder Word"]:::done
    BRIDGE["⑧ OPTIONAL: ÜBERGABE AN UC-1\nExConceptImportService ⏳\nNur strukturierte Daten\n(Zonen, Maßnahmen — kein Freitext)\n→ ExplosionConcept status=draft"]:::opt

    T1A --> T2
    T1B --> T2
    T2 --> T3 --> T4 --> T5
    T5 <-.->|pro Feld| KI1
    T5 <-.->|alle Felder| KI2
    T5 --> T6 --> T7
    T7 -.->|optional| BRIDGE
```

### Schritte auf einen Blick — UC-2

| # | Schritt | URL | Ergebnis |
|---|---------|-----|----------|
| ① a | PDF hochladen | `/doc-templates/upload/` | `DocumentTemplate` aus PDF-Extraktion |
| ① b | Leere Vorlage | `/doc-templates/create/` | `DocumentTemplate` leer |
| ② | Vorlage strukturieren | `/doc-templates/pk/edit/` | Abschnitte + Felder konfiguriert |
| ③ | KI-Hints setzen | (in Schritt ②) | `llm_hint` pro Feld, `scope=explosionsschutz` |
| ④ | Dokument erstellen | `/doc-templates/pk/instance/create/` | `DocumentInstance` status=draft |
| ⑤ | Kapitel ausfüllen | `/doc-templates/instance/pk/edit/` | `values_json` befüllt |
| ⑥ | Review | (manuell) | Status: review, Berater-Verantwortung |
| ⑦ | Export | `/doc-templates/instance/pk/pdf/` | PDF/Word, Status: approved |
| ⑧ | → UC-1 übergeben | `ExConceptImportService` ⏳ | `ExplosionConcept` status=draft |

---

## Beide Workflows im Vergleich

```mermaid
flowchart LR
    subgraph UC1["🟠 UC-1  Compliance  /ex/"]
        direction TB
        U1_1["① Bereich"] --> U1_2["② Konzept"]
        U1_2 --> U1_3["③ Zonen"]
        U1_3 --> U1_4["④ Zündquellen"]
        U1_4 --> U1_5["⑤ Maßnahmen"]
        U1_5 --> U1_6["⑥ Betriebsmittel"]
        U1_6 --> U1_7["⑦ Validieren"]
        U1_7 --> U1_8["⑧ PDF Export"]
    end

    subgraph UC2["🔵 UC-2  Gutachten  /doc-templates/"]
        direction TB
        U2_1["① Vorlage\n(PDF oder leer)"] --> U2_2["② Struktur\ndefinieren"]
        U2_2 --> U2_3["③ KI-Hints\nsetzen"]
        U2_3 --> U2_4["④ Dokument\nerstellen"]
        U2_4 --> U2_5["⑤ Kapitel\nausfüllen"]
        U2_5 --> U2_6["⑥ Review"]
        U2_6 --> U2_7["⑦ Export\nWord/PDF"]
    end

    U2_7 -.->|"⑧ optional\nExConceptImportService ⏳\nnur strukturierte Daten"| U1_2

    style UC1 fill:#fff7ed,stroke:#f97316
    style UC2 fill:#eff6ff,stroke:#3b82f6
```

| Kriterium | UC-1 Compliance | UC-2 Gutachten |
|-----------|:-:|:-:|
| **Einstieg** | Bereich anlegen | PDF hochladen / leer |
| **Struktur** | fest (Zone, Maßnahme, Equipment) | frei (JSON-Felder je Vorlage) |
| **KI-Ebene** | Kapitel-Level (Zonen, Maßnahmen, Summary) | Feld-Level (jedes Textfeld) |
| **Output** | WeasyPrint-PDF | Word oder PDF |
| **Verantwortung** | Betreiber (laufende Pflicht) | Sachverständiger (Projektauftrag) |
| **Audit** | `GenerationLog` + `AuditEvent` | `values_json` |
| **Wiederholung** | alle 24 Monate | einmalig je Projekt |

---

*Erstellt: 2026-04-22 · `iil-doc-templates` v0.3.0 · `iil-aifw` (Groq Llama 3.3 70B) · `iil-fieldprefill`*
