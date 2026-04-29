---
description: Markdown → PDF (Design: iil) — risk-hub / Schutztat
---
# /create-pdf — IIL Print Agent

Erzeugt ein PDF aus einer Markdown-Datei mit dem IIL Corporate Design.

**SSoT:** `achimdehnert/platform` → `tools/print_agent/` (lokal: `${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/`)

**Design:** `iil`
**Output:** `docs/pdf/`

---

## Schritt 1 — Datei bestimmen

Wenn der User einen vollständigen Pfad angibt: direkt verwenden.
Sonst: Datei in `docs/` suchen (guides, adr, reference).

## Schritt 2 — PDF erzeugen

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
REPO="${GITHUB_DIR:-$HOME/github}/risk-hub"
python3 "$PRINT_AGENT" \
  "<vollständiger_pfad_zur_md_datei>" \
  "$REPO/docs/pdf/" \
  --design iil
```

## Schritt 3 — Ergebnis prüfen

// turbo
```bash
ls -lh "${GITHUB_DIR:-$HOME/github}/risk-hub/docs/pdf/"
```

## Schritt 4 — Commit (optional)

```bash
git -C "${GITHUB_DIR:-$HOME/github}/risk-hub" add docs/pdf/
git -C "${GITHUB_DIR:-$HOME/github}/risk-hub" commit -m "docs: PDF aktualisiert"
git -C "${GITHUB_DIR:-$HOME/github}/risk-hub" push
```
