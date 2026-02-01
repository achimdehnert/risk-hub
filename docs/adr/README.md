# Architecture Decision Records (ADR)

Dieses Verzeichnis enthält die Architecture Decision Records für Risk-Hub.

## Übersicht

| ADR | Titel | Status | Datum |
|-----|-------|--------|-------|
| [ADR-001](ADR-001-explosionsschutz-modul-v4.md) | Explosionsschutz-Modul | ✅ APPROVED | 2026-01-31 |
| [ADR-002](ADR-002-substances-sds-modul.md) | Substances/SDS-Modul | ✅ APPROVED | 2026-01-31 |
| [ADR-003](ADR-003-tenant-rbac-architektur.md) | Multi-Tenant & RBAC | ✅ APPROVED | 2026-02-01 |
| [ADR-004](ADR-004-api-versionierung.md) | API-Versionierung & Contracts | ✅ APPROVED | 2026-02-01 |
| [ADR-005](ADR-005-event-driven-architecture.md) | Event-Driven Architecture | ✅ APPROVED | 2026-02-01 |
| [ADR-006](ADR-006-audit-compliance.md) | Audit & Compliance | ✅ APPROVED | 2026-02-01 |

## Kategorien

### Core Architecture
- **ADR-003**: Multi-Tenant & RBAC - Tenant-Isolation, Permissions, RLS
- **ADR-004**: API-Versionierung - REST API v1/v2, OpenAPI, Deprecation

### Integration & Events
- **ADR-005**: Event-Driven - Outbox Pattern, Domain Events, Webhooks

### Compliance & Security
- **ADR-006**: Audit & Compliance - BetrSichV, ISO 27001, DSGVO

### Domain Modules
- **ADR-001**: Explosionsschutz - Ex-Zonen, Equipment, Konzepte
- **ADR-002**: Substances - Gefahrstoffe, SDS-Parser, H/P-Sätze

## ADR-Format

Jedes ADR folgt diesem Format:

```markdown
# ADR-XXX: Titel

| Metadaten | |
| --------- | --- |
| **Status** | PROPOSED / APPROVED / DEPRECATED |
| **Datum** | YYYY-MM-DD |
| **Depends On** | ADR-XXX (optional) |

## Executive Summary
## Kontext
## Architektur-Entscheidungen
## Konsequenzen
## Referenzen
```

## Status-Definitionen

| Status | Bedeutung |
|--------|-----------|
| **PROPOSED** | In Diskussion, noch nicht final |
| **APPROVED** | Akzeptiert und verbindlich |
| **DEPRECATED** | Veraltet, ersetzt durch neueres ADR |
| **SUPERSEDED** | Vollständig ersetzt |

## Abhängigkeiten

```
ADR-003 (Tenant/RBAC)
    ├── ADR-004 (API)
    ├── ADR-005 (Events)
    └── ADR-006 (Audit)

ADR-001 (Explosionsschutz)
    └── ADR-002 (Substances) ──► Integration
```
