# Stripe-Monetarisierungskonzept — Schutztat / risk-hub

> Stand: März 2026 | Status: Konzept → Umsetzungsbereit

---

## 1. Ausgangslage

### Bestehende Infrastruktur
- **Multi-Tenant-Architektur** via `django-tenancy` (`Organization`, `ModuleSubscription`, `ModuleMembership`)
- `ModuleSubscription.plan_code` existiert bereits (aktuell `"free"` hardcoded)
- `ModuleSubscription.status`: `trial` / `active` / `suspended` — passt 1:1 zu Stripe-Subscription-States
- 7 Module: `risk`, `ex`, `substances`, `dsb`, `documents`, `actions`, `gbu`
- Stripe: produktiv eingesetzt (Payment-Infrastruktur vorhanden), **aber noch keine Integration in risk-hub**

### Zielgruppe
- **Mittelständische Unternehmen** (20–500 MA) in DE/AT/CH
- Branchen: Industrie, Chemie, Logistik, Handwerk, Baugewerbe
- Käufer: Sicherheitsbeauftragte, DSB (extern/intern), Qualitätsmanager, Geschäftsführer
- **Besonderheit:** Oft externes DSB/Sicherheitsexperte betreut mehrere Mandanten

---

## 2. Produkt-Portfolio & Stripe-Mapping

### 2.1 Kernmodule (Stripe Products)

| Modul | Stripe Product Name | Zielgruppe | Preis-Ankerpunkt |
|-------|--------------------|-----------|-----------------|
| `risk` | Risikobewertung | Sicherheitsbeauftragte | Kern-Modul |
| `ex` | Explosionsschutz | Ex-Beauftragte, Industrie | Spezial-Modul |
| `substances` | Gefahrstoffmanagement | Chemie, Produktion | Spezial-Modul |
| `dsb` | Datenschutz (DSB) | Datenschutzbeauftragte | Kern-Modul |
| `documents` | Dokumentenmanagement | Alle | Add-on |
| `actions` | Maßnahmen-Tracking | Alle | Add-on |
| `gbu` | Gefährdungsbeurteilung | Sicherheitsbeauftragte | Kern-Modul |

### 2.2 Preismodell: Hybrid-Ansatz (per-Seat + per-Modul)

#### Tier-Struktur (Stripe Products mit Prices)

```
PRODUCT: schutztat_starter
  PRICE: 39 €/Monat (monatlich) | 390 €/Jahr (jährlich = 2 Monate gratis)
  Inhalt:
    - 1 Modul nach Wahl
    - bis 3 Nutzer
    - 5 GB Dokumentenspeicher
    - E-Mail-Support

PRODUCT: schutztat_professional  ← EMPFOHLEN / Most Popular
  PRICE: 89 €/Monat | 890 €/Jahr
  Inhalt:
    - bis 3 Module
    - bis 10 Nutzer
    - 25 GB Speicher
    - GBU + Maßnahmen immer inklusive
    - Priority-Support
    - PDF-Export

PRODUCT: schutztat_business
  PRICE: 179 €/Monat | 1.790 €/Jahr
  Inhalt:
    - alle 7 Module
    - bis 25 Nutzer
    - unbegrenzt Speicher
    - API-Zugang
    - Onboarding-Session
    - SLA 99.9%

PRODUCT: schutztat_enterprise
  PRICE: auf Anfrage (Custom / Stripe Quotes)
  Inhalt:
    - Multi-Mandanten-Verwaltung (DSB betreut mehrere Kunden)
    - Unbegrenzte Nutzer & Module
    - Dedicated Support
    - Custom Branding
    - DSGVO-DPA
```

#### Add-on Prices (Stripe Metered / One-Time)

| Add-on | Typ | Preis |
|--------|-----|-------|
| Zusätzlicher Nutzer-Seat | Flat per Unit | 9 €/Nutzer/Monat |
| Zusätzliches Modul | Flat per Unit | 29 €/Modul/Monat |
| Onboarding-Paket | One-Time | 299 € |
| Daten-Export (einmalig) | One-Time | 49 € |

### 2.3 Strategische Modul-Kombinations-Empfehlungen

```
DSB-Berater (extern, mehrere Mandanten)
  → Enterprise Plan + Multi-Mandanten-Feature
  → Upsell: DSB-Modul pro Mandant aktivieren

Industrieunternehmen (Chemie/Ex-Schutz)
  → Professional: risk + ex + substances
  → Upsell: GBU + documents

Handwerksbetrieb / KMU
  → Starter: GBU oder risk
  → Upsell: Maßnahmen-Tracking
```

---

## 3. Stripe-Integration: Technische Architektur

### 3.1 Neue Django-App `billing`

```
src/billing/
├── __init__.py
├── apps.py
├── models.py          # StripeCustomer, StripeSubscription, BillingEvent
├── services.py        # checkout_session, portal_session, sync_subscription
├── webhooks.py        # stripe webhook handler
├── urls.py
└── views.py           # checkout_redirect, portal_redirect, webhook_endpoint
```

### 3.2 Datenmodell

```python
class StripeCustomer(models.Model):
    """Mapping Organization ↔ Stripe Customer."""
    organization = OneToOneField(Organization)
    stripe_customer_id = CharField(max_length=100, unique=True)  # cus_...
    created_at = DateTimeField(auto_now_add=True)

class StripeSubscription(models.Model):
    """Aktive Stripe-Subscription einer Organization."""
    organization = ForeignKey(Organization)
    stripe_subscription_id = CharField(max_length=100)           # sub_...
    stripe_price_id = CharField(max_length=100)                  # price_...
    plan_code = CharField(max_length=50)                         # starter/professional/business
    status = CharField(choices=[trial/active/past_due/canceled])
    current_period_end = DateTimeField()
    cancel_at_period_end = BooleanField(default=False)
    updated_at = DateTimeField(auto_now=True)
```

### 3.3 Webhook-Events (kritisch)

| Stripe Event | Aktion in risk-hub |
|-------------|-------------------|
| `checkout.session.completed` | `ModuleSubscription` aktivieren, `StripeSubscription` anlegen |
| `customer.subscription.updated` | Status + Plan synchronisieren |
| `customer.subscription.deleted` | `ModuleSubscription.status = suspended` |
| `invoice.payment_failed` | Tenant benachrichtigen, Grace-Period starten |
| `invoice.payment_succeeded` | `current_period_end` updaten |

### 3.4 Checkout-Flow

```
Landingpage → "14 Tage testen" CTA
    ↓
/billing/checkout/?plan=professional
    ↓
Stripe Checkout Session (hosted)
    ↓
Stripe verarbeitet Zahlung
    ↓
Webhook: checkout.session.completed
    ↓
billing.services.activate_subscription()
    ↓
ModuleSubscription(status=active) für gebuchte Module
    ↓
Redirect: /dashboard/ (eingeloggt, Module aktiv)
```

### 3.5 Self-Service Portal

```
/billing/portal/ → Stripe Customer Portal
```
- Upgrade/Downgrade Plan
- Kündigung (cancel_at_period_end)
- Rechnungen herunterladen
- Zahlungsmethode ändern

### 3.6 plan_code → Module Mapping

```python
PLAN_MODULES = {
    "starter":      ["gbu"],                                          # 1 Modul (GBU als Default)
    "professional": ["risk", "dsb", "gbu", "actions", "documents"],   # Top 3 + Standard
    "business":     ["risk", "ex", "substances", "dsb", "gbu",
                     "documents", "actions"],                          # alle Module
}
```

---

## 4. Umsatzoptimierung: Konkrete Maßnahmen

### 4.1 14-Tage-Trial (kein Kreditkarte erforderlich)
- Neuer Tenant → `ModuleSubscription(status=trial, plan_code=professional)` für 14 Tage
- Tag 10: automatische E-Mail (Notifications-App bereits vorhanden)
- Tag 14: Downgrade auf Starter oder Sperrung
- **Stripe Trial**: `subscription_data.trial_period_days=14` im Checkout

### 4.2 Jährliche Zahlung pushen
- Rabatt: 2 Monate gratis (ca. 17%)
- Stripe: separater `price_annual` mit `billing_period=year`
- Toggle auf Pricing-Sektion der Landingpage (monatlich/jährlich)

### 4.3 Upsell-Flows
- In-App: `require_module` gibt 403 → Banner "Modul freischalten" mit Link zu `/billing/checkout/?add_module=ex`
- Dashboard-Widget: "Sie nutzen 2 von 7 Modulen — jetzt upgraden"

### 4.4 Extern-DSB / Agentur-Modell
- Enterprise: ein Stripe-Kunde = eine DSB-Agentur
- Pro betreutem Mandant: +X €/Mandant/Monat (Stripe Metered Billing)
- Mandanten-Verwaltung über bestehende `Mandate`-Struktur im DSB-Modul

---

## 5. Stripe-Setup Checkliste

### Stripe Dashboard
- [ ] 7 Products anlegen (je Modul + Bundles)
- [ ] Prices anlegen (monatlich + jährlich je Plan)
- [ ] Customer Portal aktivieren und konfigurieren
- [ ] Webhook-Endpoint registrieren: `https://schutztat.de/billing/webhook/`
- [ ] Events aktivieren: siehe 3.3
- [ ] Test-Mode → Live-Mode nach Validierung

### Umgebungsvariablen (`.env`)
```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER_MONTHLY=price_...
STRIPE_PRICE_STARTER_ANNUAL=price_...
STRIPE_PRICE_PROFESSIONAL_MONTHLY=price_...
STRIPE_PRICE_PROFESSIONAL_ANNUAL=price_...
STRIPE_PRICE_BUSINESS_MONTHLY=price_...
STRIPE_PRICE_BUSINESS_ANNUAL=price_...
```

### Python-Abhängigkeit
```bash
pip install stripe>=7.0  # aktuell stripe>=7 empfohlen
```

---

## 6. Rollout-Phasen

| Phase | Inhalt | Aufwand |
|-------|--------|--------|
| **Phase 1** | Landingpage Pricing-Sektion + Trial-Formular (kein Stripe nötig) | 1 Tag |
| **Phase 2** | `billing` App: Models + Checkout → Stripe Checkout hosted | 2–3 Tage |
| **Phase 3** | Webhook-Handler + automatische Modul-Aktivierung | 1–2 Tage |
| **Phase 4** | Stripe Customer Portal + In-App Upsell-Banner | 1 Tag |
| **Phase 5** | Enterprise/Metered Billing für DSB-Agenturen | 2–3 Tage |

**Phase 1 ist sofort umsetzbar** — Pricing sichtbar machen, Trial-Anfragen sammeln, bevor Stripe vollständig integriert ist.

---

## 7. Erwarteter ARR (Hochrechnung)

| Szenario | Kunden | Ø Plan | MRR | ARR |
|----------|--------|--------|-----|-----|
| Konservativ | 20 | Professional 89 € | 1.780 € | 21.360 € |
| Realistisch | 50 | Mix 110 € | 5.500 € | 66.000 € |
| Optimistisch | 150 | Mix 130 € | 19.500 € | 234.000 € |

Enterprise/Agentur-Kunden (5+ Mandanten) verdoppeln den ARR-Hebel.
