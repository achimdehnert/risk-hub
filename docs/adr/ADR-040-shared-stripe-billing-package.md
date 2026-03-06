# ADR-040: Shared Stripe Billing Package (`bf-billing`)

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-03-06 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-039 (Windsurf Workflows Standard), ADR-003 (Tenant RBAC), ADR-009 (nl2cad Registry) |

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

Ohne gemeinsames Package entsteht:

| Problem | Konsequenz |
|---------|-----------|
| Copy-Paste der `billing/`-App in jeden Repo | Bugfixes müssen n-fach gepflegt werden |
| Divergierende Webhook-Handler | Inkonsistentes Verhalten über Plattformen |
| Kein gemeinsames Datenmodell | Keine plattformübergreifende Billing-Übersicht |
| Stripe SDK-Version unkoordiniert | Sicherheitslücken bleiben unentdeckt |

### 1.3 Anforderungen

- Wiederverwendbar in Django-Apps **und** reinen Python-Services (nl2cad)
- Framework-agnostischer Kern (kein Django-Zwang auf Service-Ebene)
- Django-Integration als optionaler Extra
- Multi-Tenant-fähig (Org/Tenant als abstraktes Konzept)
- Testbar ohne echte Stripe-Credentials (Fixture-basiert)
- Eigenständig versioniert und via PyPI verteilbar

---

## 2. Entscheidung

**Ein neues Python-Package `bf-billing` wird im Repository `achimdehnert/bf-billing` entwickelt.**

Das Package ist in drei Schichten aufgebaut:

```
bf-billing/
├── src/bf_billing/
│   ├── core/          # Framework-agnostisch: Services, Models (Dataclasses), Webhook-Dispatcher
│   ├── django/        # Django-Integration: Models (ORM), Admin, Context Processor, Views, URLs
│   └── testing/       # Test-Fixtures, Stripe-Mock-Factory
```

### 2.1 Architektur — drei Schichten

#### Schicht 1: `bf_billing.core` (keine Django-Abhängigkeit)

```python
# Reine Dataclasses — keine Django ORM-Abhängigkeit
@dataclass
class BillingCustomer:
    external_id: str        # Stripe customer_id
    tenant_id: str
    email: str

@dataclass
class BillingSubscription:
    external_id: str        # Stripe subscription_id
    tenant_id: str
    status: str             # trial | active | past_due | canceled | suspended
    plan: str
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False

# Service-Interface (abstrakt)
class BillingServiceBase:
    def get_or_create_customer(self, tenant_id: str, email: str) -> BillingCustomer: ...
    def create_checkout_session(self, tenant_id: str, price_id: str, ...) -> str: ...
    def create_portal_session(self, tenant_id: str, return_url: str) -> str: ...
    def activate_subscription(self, tenant_id: str, stripe_sub: dict) -> BillingSubscription: ...
    def suspend_subscription(self, tenant_id: str) -> None: ...

# Webhook-Dispatcher
class WebhookDispatcher:
    def dispatch(self, event: stripe.Event) -> None: ...
    def register(self, event_type: str, handler: Callable) -> None: ...
```

#### Schicht 2: `bf_billing.django` (optional, requires Django)

```python
# ORM-Models (Migration-fähig via AppConfig)
class StripeCustomer(TenantModel): ...
class StripeSubscription(TenantModel): ...
class BillingEvent(TenantModel): ...

# Views: checkout_redirect, portal_redirect, webhook_endpoint, success, cancel
# URLs: bf_billing.django.urls
# Admin: StripeCustomerAdmin, StripeSubscriptionAdmin, BillingEventAdmin
# Context Processor: billing_context(request) -> dict
# Template Tags: {% billing_widget %}
```

#### Schicht 3: `bf_billing.testing`

```python
# Stripe-Event-Factory für Tests
from bf_billing.testing import StripeEventFactory

event = StripeEventFactory.checkout_session_completed(tenant_id="acme")
event = StripeEventFactory.invoice_payment_failed(tenant_id="acme")
```

### 2.2 Tenant-Abstraktion

Das Package kennt keinen konkreten Django-Tenant-Typ.
Stattdessen wird ein `TenantResolver`-Protocol verwendet:

```python
class TenantResolver(Protocol):
    def resolve(self, stripe_customer_id: str) -> str | None:
        """Gibt tenant_id zurück oder None."""
        ...
```

Jede Plattform registriert ihren eigenen Resolver:

```python
# risk-hub settings.py
BF_BILLING_TENANT_RESOLVER = "billing.resolvers.RiskHubTenantResolver"

# coach-hub settings.py
BF_BILLING_TENANT_RESOLVER = "billing.resolvers.CoachHubTenantResolver"
```

### 2.3 Konfiguration via Django Settings

```python
# settings.py — alle Plattformen
BF_BILLING = {
    "STRIPE_SECRET_KEY": env("STRIPE_SECRET_KEY"),
    "STRIPE_PUBLISHABLE_KEY": env("STRIPE_PUBLISHABLE_KEY"),
    "STRIPE_WEBHOOK_SECRET": env("STRIPE_WEBHOOK_SECRET"),
    "TENANT_RESOLVER": "billing.resolvers.MyTenantResolver",
    "TRIAL_DAYS": 14,
    "PLANS": {
        "starter_monthly": env("STRIPE_PRICE_STARTER_MONTHLY"),
        "starter_annual": env("STRIPE_PRICE_STARTER_ANNUAL"),
        # ...
    },
}
```

### 2.4 Integration in Django-Apps

```python
# settings.py
INSTALLED_APPS = [
    ...
    "bf_billing.django",  # bringt Migrations, Admin, Context Processor
]

# urls.py
path("billing/", include("bf_billing.django.urls")),
```

### 2.5 Migration in bestehenden Repos

1. `src/billing/` App durch `bf_billing.django` ersetzen
2. Eigene `billing/` Migrations via `replaces`-Mechanismus bridgen
3. Plattform-spezifische `TenantResolver` in `src/billing/resolvers.py` implementieren
4. Settings auf `BF_BILLING`-Dict umstellen

---

## 3. Implementierungsplan

### Sprint 1 — Package-Grundstruktur (1 Woche)

| Task | Ergebnis |
|------|----------|
| Repo `bf-billing` anlegen | `pyproject.toml`, `src/bf_billing/`, CI |
| `core/` implementieren | Dataclasses, `BillingServiceBase`, `WebhookDispatcher` |
| `django/` implementieren | Models (von risk-hub portiert), Views, URLs |
| `testing/` implementieren | `StripeEventFactory` mit 6 Event-Typen |
| Tests: 100 % Core-Coverage | pytest, kein Stripe-API-Call |
| Publish `bf-billing==0.1.0` | PyPI (privat oder public) |

### Sprint 2 — Migration risk-hub (2 Tage)

| Task | Ergebnis |
|------|----------|
| `bf-billing>=0.1` in `requirements.txt` | Dependency resolved |
| `src/billing/` auf Shim reduzieren | Nur `TenantResolver` + platform-spezifische Konstanten |
| Migration-Bridge via `replaces` | Keine Datenverluste |
| CI grün | Tests laufen durch |

### Sprint 3 — Migration coach-hub + nl2cad (3 Tage)

- coach-hub: analog risk-hub
- nl2cad: nur `bf_billing.core` (kein Django), `BillingServiceBase` verwenden

### Sprint 4 — Rollout pptx-hub, travel-beat, writing-hub

- Integration pro Repo ~1 Tag (nur `TenantResolver` + Settings)

---

## 4. Konsequenzen

### 4.1 Positiv

- **Single source of truth** für Stripe-Logik — ein Bugfix gilt für alle Plattformen
- **Versionierbar** — Breaking Changes via SemVer kontrollierbar
- **Testbar** — `StripeEventFactory` eliminiert Mocks in Consumer-Tests
- **Framework-agnostisch** — nl2cad und zukünftige FastAPI-Services nutzbar
- **Stripe SDK-Upgrades** zentral in `bf-billing` — sofortige Wirkung auf alle Consumer

### 4.2 Negativ / Risiken

- **Neues Repo** — zusätzlicher Maintenance-Aufwand (CI, Releases, Changelog)
- **Migration-Aufwand** — bestehende `billing/`-Apps in risk-hub und coach-hub müssen migriert werden
- **Private PyPI** oder GitHub Packages nötig wenn nicht open-source

### 4.3 Mitigation

| Risiko | Mitigation |
|--------|------------|
| Migration-Datenverlust | `replaces`-Mechanismus in Django-Migrations |
| Package-Verfügbarkeit in CI | GitHub Packages mit PAT oder `pip install git+https://...` |
| Breaking Changes | SemVer strict: `0.x` erlaubt Breaking, ab `1.0` deprecation cycle |
| Zu abstrakt / over-engineered | Sprint 1 liefert nur was risk-hub schon hat — kein YAGNI |

---

## 5. Alternativen (verworfen)

| Alternative | Grund für Ablehnung |
|-------------|--------------------|
| Copy-Paste in jeden Repo | Nicht skalierbar, Divergenz unvermeidlich |
| Zentraler Billing-Microservice | Operativer Overhead, Latenz, Single Point of Failure |
| Git Subtree / Submodule | Schlechte DX, keine semantische Versionierung |
| Monorepo für alle Plattformen | Zu großer Umbau, inkompatibel mit bisheriger Repo-Strategie |

---

## 6. Offene Fragen (für Review)

1. **PyPI-Strategie**: Public PyPI (`bf-billing`) oder privat via GitHub Packages?
2. **Tenant-Abstraktion**: Reicht `TenantResolver`-Protocol oder brauchen wir Django-Signals?
3. **Stripe-Webhook-URL**: Zentraler Webhook-Endpunkt (`billing.iil.pet`) oder weiterhin pro Plattform?
4. **nl2cad-Integration**: `bf_billing.core` direkt oder eigenes `nl2cad-billing`-Package im nl2cad-Monorepo?
5. **Migration-Timing**: risk-hub direkt nach Sprint 1 migrieren oder parallel betreiben?

---

## 7. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-03-06 | Achim Dehnert | Initial draft |
