# ADR-040: Stripe Billing — `billing-hub` als zentraler aktiver Service

| Metadata | Value |
|----------|-------|
| **Status** | Accepted |
| **Date** | 2026-03-06 |
| **Author** | Achim Dehnert |
| **Reviewers** | Achim Dehnert (06.03.2026) |
| **Supersedes** | — |
| **Related** | billing-hub ADR-001, ADR-039 (Windsurf Workflows Standard), ADR-003 (Tenant RBAC) |

> **Canonical ADR:** `billing-hub/docs/adr/ADR-001`. Dieses ADR ist der Cross-Referenz-Eintrag für risk-hub.

---

## 1. Entscheidung (Kurzfassung)

**`billing-hub` ist ein aktiver Django-Service** unter `https://billing.iil.pet`
mit zentralem Stripe-Webhook-Endpunkt, eigenem Deploy und eigener DB.

Alle Plattformen (risk-hub, coach-hub, pptx-hub, travel-beat, writing-hub, nl2cad)
nutzen `billing-hub` als Single Source of Truth für Subscription-Status.

## 2. Review-Entscheidungen

| # | Entscheidung |
|---|-------------|
| 1 | **Privates PyPI** (GitHub Packages) |
| 2 | **`TenantResolver`-Protocol** — erweiterbar auf Django Signals |
| 3 | **Option B: Zentraler Webhook** — `POST /api/webhook/stripe/` in billing-hub |
| 4 | **`core` direkt** für nl2cad — kein Django |
| 5 | **Parallel** — risk-hub behält `billing/` bis Sprint 2 abgeschlossen |

## 3. Webhook-Endpunkt

```
https://billing.iil.pet/api/webhook/stripe/   ← 1 Stripe-Endpunkt für alle Plattformen
https://billing.iil.pet/api/access/{platform}/{email}/{module}/
https://billing.iil.pet/api/customer/{email}/
https://billing.iil.pet/api/platforms/
```

## 4. Consumer-Integration (risk-hub)

```python
# src/billing/client.py
import httpx
from django.conf import settings

class BillingHubClient:
    def check_access(
        self, platform_slug: str, email: str, module_id: str
    ) -> dict:
        resp = httpx.get(
            f"{settings.BILLING_HUB_URL}/api/access/"
            f"{platform_slug}/{email}/{module_id}/",
            headers={"X-Internal-Secret": settings.BILLING_HUB_SECRET},
        )
        return resp.json()
```

Stripe-Webhook in `src/billing/webhooks.py` entfällt nach Sprint 2.

## 5. Migration-Timing

- risk-hub behält eigene `billing/` **parallel** bis billing-hub auf `billing.iil.pet` deployed
- Sprint 2 startet nach billing-hub Sprint 1 (Webhook-Handler + Tests + Deploy)

## 6. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-03-06 | Achim Dehnert | Initial draft |
| 2026-03-06 | Achim Dehnert | Option B gewählt, Status Accepted |
