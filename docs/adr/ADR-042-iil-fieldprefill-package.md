# ADR-042: Use `iil-fieldprefill` as shared AI field enrichment layer — Cross-Referenz

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-04-06 |
| **Amended** | 2026-04-06 |
| **Author** | Achim Dehnert |
| **Canonical ADR** | **Platform ADR-107** (`mcp-hub/docs/ADR-107-iil-fieldprefill-package.md`) |

> **Dies ist ein Cross-Referenz-Eintrag.** Das kanonische ADR liegt auf Platform-Ebene,
> da `iil-fieldprefill` ein shared Package für 5+ Repos ist (risk-hub, weltenhub,
> trading-hub, ausschreibungs-hub, cad-hub).

---

## Kurzfassung

Neues PyPI-Package `iil-fieldprefill` für AI-Anreicherung von Formularfeldern
mit Umgebungsinformationen. Reviewed 2026-04-06 (extern + Cascade), alle
Blocker gefixt (Auth-Guard, tenant_id Union-Type, Pydantic v2 Result, async API).

### Betroffene risk-hub Dateien (Phase 1 Migration)

| Datei | Wird ersetzt durch |
|-------|--------------------|
| `explosionsschutz/services/ex_doc_prefill.py` | `fieldprefill.prefill_field()` |
| `explosionsschutz/concept_template_views.py` (Prefill-Teil) | `fieldprefill.django.PrefillViewMixin` |
| `brandschutz/views.py` (Prefill-Teil) | `fieldprefill.prefill_field()` |
| `doc_template_retrievers.py` | `@fieldprefill.register_retriever()` |

### Vollständige Details

→ Siehe [Platform ADR-107](https://github.com/achimdehnert/mcp-hub/blob/main/docs/ADR-107-iil-fieldprefill-package.md)
