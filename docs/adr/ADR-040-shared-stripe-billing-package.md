# ADR-040: Shared Stripe Billing Package (`bf-billing`)

| Metadata | Value |
|----------|-------|
| **Status** | Accepted |
| **Date** | 2026-03-06 |
| **Author** | Achim Dehnert |
| **Reviewers** | Achim Dehnert (06.03.2026) |
| **Supersedes** | — |
| **Related** | billing-hub ADR-001, ADR-039 (Windsurf Workflows Standard), ADR-003 (Tenant RBAC), ADR-009 (nl2cad Registry) |

---

## 1. Kontext und Problemstellung

### 1.1 Ist-Stand

Stripe-Billing wurde zuerst in `risk-hub` implementiert (`src/billing/`):
- `StripeCustomer`, `StripeSubscription`, `BillingEvent` (Django-Models)
- `BillingService` (Customer, Checkout, Portal, Subscription-Sync)
- Webhook-Handler (`checkout.session.completed`, `invoice.*`, `customer.subscription.*`)
- `create_trial` Management-Command
- Context Processor + Dashboard-Widget
- CI/CD-Step zur Secret-Injektion

Die gleiche Logik wird identisch auf **coach-hub**, **nl2cad** und zukünftig auf
`pptx-hub`, `travel-beat`, `writing-hub` u.a. benötigt.

### 1.2 Problem

| Problem | Konsequenz |
|---------|-----------|
| Copy-Paste der `billing/`-App in jeden Repo | Bugfixes müssen n-fach gepflegt werden |
| Divergierende Webhook-Handler | Inkonsistentes Verhalten über Plattformen |
| Stripe SDK-Version unkoordiniert | Sicherheitslücken bleiben unentdeckt |

---

## 2. Entscheidung

**Canonical ADR in `billing-hub/docs/adr/ADR-001`. Dieses ADR ist der Cross-Referenz-Eintrag für risk-hub.**

### 2.1 Review-Entscheidungen

| # | Frage | Entscheidung |
|---|-------|-------------|
| 1 | **PyPI-Strategie** | **Privates PyPI** (GitHub Packages) |
| 2 | **Tenant-Abstraktion** | **`TenantResolver`-Protocol** — ASAP erweiterbar auf Django Signals |
| 3 | **Stripe-Webhook-URL** | **Pro Plattform** — `billing-hub` bleibt reines Package |
| 4 | **nl2cad-Integration** | **`core` direkt** — kein Django |
| 5 | **Migration-Timing** | **Parallel** — risk-hub behält eigene `billing/` bis `bf-billing==1.0` |

### 2.2 Zu Entscheidung 3 — Webhook-Strategie

#### Gewählt: Option A — Pro Plattform
```
risk-hub  → https://schutztat.de/billing/webhook/
coach-hub → https://coach.iil.pet/billing/webhook/
pptx-hub  → https://prezimo.de/billing/webhook/
```
- Stripe Dashboard: n Endpunkte, einer pro Plattform
- `billing-hub` bleibt **reines Package** — keine eigene Infra
- Kein zentraler SPOF

#### Zukünftige Option B — Zentraler Endpunkt (wenn Cross-Platform-Reporting nötig)
```
billing-hub → https://billing.iil.pet/api/webhook/stripe/
```
- 1 Stripe-Endpunkt, routing per `stripe_customer_id` → Plattform
- Voraussetzung: `billing-hub` wird aktiver Service mit eigenem Deploy

### 2.3 Migration risk-hub

- risk-hub behält `src/billing/` **parallel** bis `bf-billing==1.0` stabil ist
- Danach: `src/billing/` wird auf Shim mit `TenantResolver` reduziert
- Migration via Django `replaces`-Mechanismus — keine Datenverluste

### 2.4 nl2cad-Integration

- Nur `bf_billing.core` — Dataclasses + `BillingServiceBase`
- Kein Django ORM, keine Migrations
- Erlaubt in `nl2cad-nlp` (externe Deps dort zulässig)

---

## 3. Implementierungsplan

Siehe `billing-hub/docs/adr/ADR-001` für vollständigen Plan.

### Sprint-Übersicht

| Sprint | Scope | Timing |
|--------|-------|--------|
| 1 | `core/` + `django_billing/` + `testing/` + `bf-billing==0.1.0` | Jetzt |
| 2 | Migration risk-hub | Nach `bf-billing==1.0` |
| 3 | coach-hub + nl2cad | Nach Sprint 2 |
| 4 | pptx-hub, travel-beat, writing-hub | ~1 Tag/Plattform |

---

## 4. Konsequenzen

### 4.1 Positiv
- Single source of truth für Stripe-Logik
- SemVer-Versionierung — Breaking Changes kontrollierbar
- `StripeEventFactory` für Tests ohne echte Credentials
- Framework-agnostisch: Django + nl2cad + FastAPI

### 4.2 Risiken + Mitigation

| Risiko | Mitigation |
|--------|------------|
| Migration-Datenverlust | Django `replaces`-Mechanismus |
| CI-Zugriff auf privates Package | `GH_PAT` als GitHub Secret |
| Parallelbetärieb Komplexität | risk-hub `billing/` bleibt bis `1.0` unverändert |

---

## 5. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-03-06 | Achim Dehnert | Initial draft |
| 2026-03-06 | Achim Dehnert | Review-Entscheidungen eingetragen — Status Accepted |
