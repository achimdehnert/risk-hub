# PDF-Dokumentation — Schutztat (risk-hub)

Alle PDFs werden aus Markdown-Quellen via `/create-pdf` generiert (Design: `iil`).

→ **Aktueller Status aller Dokumente:** [STATUS.md](STATUS.md)

---

## Verzeichnisstruktur

```
docs/pdf/
├── STATUS.md          ← Freigabe-Status aller Dokumente
├── README.md          ← Diese Datei
├── user/              ← Für Endnutzer / Sachbearbeiter
├── technical/         ← Für IT-Admins / Entwickler
└── management/        ← Für Entscheider / Product Owner
```

## Aktuelle Dokumente

*(noch keine PDFs generiert — siehe [STATUS.md](STATUS.md) für geplante Dokumente)*

## Erzeugen / Aktualisieren

```bash
# In Windsurf:
/create-pdf
```

Nach Erzeugung: `STATUS.md` aktualisieren (Zeile in Tabelle ergänzen/anpassen).

## Namenskonvention

```
<subdir>/<kebab-case-titel>_vX.Y.pdf
```

Beispiele:
- `user/benutzerhandbuch_v1.0.pdf`
- `technical/deployment-guide_v1.0.pdf`
- `management/produktuebersicht_v0.1.pdf`
