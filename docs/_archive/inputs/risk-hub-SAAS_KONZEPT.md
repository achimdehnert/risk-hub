## Konzept als review-fähige Markdown-Datei

Speichere die folgende Datei als `RISK_SAAS_KONZEPT.md` (oder direkt in dein Repo unter `/docs/`).

```md
# Enterprise SaaS Risikomanagement – Infrastruktur- & Architekturkonzept (Hetzner Start, Django/HTMX, Postgres)

Stand: 2026-01-28  
Scope: Plattform für Risikomanagement (Brandschutz, Explosionsschutz, Arbeitssicherheit/Arbeitsschutz, Audits, Maßnahmen, Dokumente, Nachweise).

---

## 1. Ziele & Nicht-Ziele

### Ziele
- Mandantenfähige SaaS (Multi-Tenant) mit belastbarer Isolation.
- Auditierbarkeit (wer/was/wann) für risk-relevante Daten.
- Datenbank-getrieben: Constraints, saubere Migrationen, optional RLS als „second line of defense“.
- Service-orientierte Struktur (Bounded Contexts), aber mit pragmatischem Ops-Start auf Hetzner.
- Dokumentenmodul mit S3-kompatiblem Storage (MinIO/Hetzner Object Storage).

### Nicht-Ziele (Initial)
- Vollständige Microservice-Landschaft ab Tag 1.
- Vollumfängliche Analytics/BI, Policy-as-Code, dedizierte Tenant-DBs (später möglich).

---

## 2. Zielarchitektur (pragmatisch service-orientiert)

### 2.1 Deployment-Strategie
**Phase 1 (Hetzner Start): Modularer Monolith**
- Ein Django Deployment (App) mit klar getrennten Domänenmodulen.
- Hintergrundverarbeitung via Outbox Worker (DB Polling; später Queue/Bus).
- Vorteil: schneller Start, weniger Ops, dennoch „service boundaries“ innerhalb des Codes.

**Phase 2 (Wachstum): selektive Auskopplung**
- Module mit hohen Last-/Integrationsanforderungen (Reporting, Document Processing, Integrations) werden zu separaten Services.

### 2.2 Bounded Contexts (Module)
- `tenancy`: Mandanten, Organisationen, Sites
- `identity`: User, Rollen (RBAC später), SSO (OIDC später)
- `risk`: Gefährdungsbeurteilung, Bewertung, Freigaben (Statusmaschine)
- `actions`: Maßnahmen/Tasks, Fristen, Eskalation
- `documents`: Dokumente, Versionierung, Nachweise, Freigaben (später)
- `audit`: Audit Events, Diff/Metadaten
- `outbox`: zuverlässige Event-Ausleitung

---

## 3. Infrastruktur auf Hetzner (SaaS-ready)

### 3.1 Container Runtime
- Docker (VM-basiert) + Nginx als Reverse Proxy + optional Hetzner Load Balancer.
- Später Pfad zu Kubernetes: k3s auf Hetzner (Deployment/Ingress/Secrets nahezu identisch).

### 3.2 Datenhaltung
- Postgres 16 als primärer Store.
- Object Storage (S3-kompatibel): Hetzner Object Storage oder MinIO (dev/staging).
- Redis optional (Cache/Rate limiting / future jobs).

### 3.3 Observability (Minimum)
- Strukturierte Logs (request_id, tenant_id, user_id).
- Metriken (Prometheus/Grafana) und Error Reporting.
- Tracing (OpenTelemetry) optional später.

### 3.4 Security Baseline
- TLS überall (Ingress + HSTS).
- Secrets nicht im Repo (env/secrets mgmt).
- DB nur privat erreichbar (Firewall / private network).
- Backups + Restore Tests als Pflicht.

---

## 4. Multi-Tenancy & Isolation

### 4.1 Tenant Resolution: Subdomain
- Tenant wird über Subdomain identifiziert: `{tenant}.deine-domain.tld`
- In dev: `demo.localhost` (Hosts-Eintrag).
- Mapping: `Organization.slug == subdomain`.

### 4.2 Datenmodell
- Jede fachliche Tabelle führt `tenant_id`.
- Tenant-spezifische Uniqueness: `UNIQUE(tenant_id, <key>)`.

### 4.3 Postgres Row Level Security (RLS)
**Ziel:** defense-in-depth, falls App-Bug Tenant-Filterung umgeht.

Mechanik:
- Middleware setzt pro Request: `SET LOCAL app.current_tenant = '<uuid>'`
- RLS Policy prüft: `tenant_id = current_setting('app.current_tenant')::uuid`

Betriebsmodus:
- Lokal dev: RLS optional aus (weniger Reibung).
- Staging/Prod: RLS an + Monitoring.

---

## 5. Datenbank-getriebenes Design

### 5.1 Constraints (Pflicht)
- Check Constraints (Statuswerte, numerische Bereiche).
- Foreign Keys (Referential Integrity).
- Unique Constraints pro Tenant.
- Indexe für häufige Abfragen (tenant_id, created_at, status).

### 5.2 Migrationen
- Expand/Contract Strategie:
  - Expand: neue Spalten/Tabellen, dual write/dual read.
  - Contract: alte Strukturen entfernen, nachdem Code überall umgestellt ist.
- Keine stillen Defaults für fachliche Felder (bewusstes Datenmodell).

### 5.3 Audit & Historie
- Audit Event bei jedem risk-relevanten Write:
  - category, action, entity_type, entity_id, payload, actor_user_id, request_id, timestamp
- Große Payloads nicht im Audit speichern → Referenz auf Dokument/S3.

---

## 6. Service Layer & Separation of Concerns

### 6.1 Schichtenmodell
- UI (Views/Templates/HTMX): Input -> Service call -> Render.
- Application/Service Layer (`*/services.py`):
  - Use-Case Funktionen/Commands, Transaktionen, Invarianten, Berechtigungen, Audit/Outbox.
- Domain: Statusmaschinen/Policies (später stärker).
- Infrastructure: DB, S3, Integrationen, Background Worker.

### 6.2 Regeln
- Keine Businesslogik in Views/JS.
- Jede Mutation muss über Service Layer erfolgen.
- Jede Mutation erzeugt Audit Event + (falls relevant) Outbox Event.

---

## 7. Naming Konventionen

### 7.1 Python / Django
- App Namen: `tenancy`, `risk`, `documents`, `actions`
- Service Funktionen: `verb_noun` (z.B. `create_document`, `approve_assessment`)
- Commands/DTOs: `<Verb><Noun>Cmd` (z.B. `CreateDocumentCmd`)

### 7.2 DB
- Tabellen: `snake_case`, inhaltlich gruppiert (z.B. `risk_assessment`, `documents_document_version`)
- Spalten:
  - PK: `id` (uuid)
  - Tenant: `tenant_id` (uuid)
  - Timestamps: `created_at`, `updated_at` (wo sinnvoll)

### 7.3 URLs
- Ressourcenorientiert:
  - `/risk/assessments/`
  - `/documents/`
  - `/documents/{id}/upload/`

---

## 8. Dokumentenmodul (S3 / Nachweise / Versionierung)

### 8.1 Fachmodell
- `Document`: Titel, Kategorie, tenant_id
- `DocumentVersion`: Version, sha256, content_type, size, s3_key

### 8.2 Upload
- MVP: Server-seitiger Upload via boto3 `upload_fileobj`.
- Später: Presigned Uploads (direkt Client → S3) + AV-Scan Pipeline.

### 8.3 Zugriff
- Dev: optional public base url (MinIO).
- Prod: bevorzugt private Buckets + signed URLs + CDN.

---

## 9. Outbox Pattern (Integration/Async)

- Jede fachliche Mutation schreibt innerhalb der gleichen DB-Transaktion eine `outbox_message`.
- Worker publiziert zuverlässig und markiert `published_at`.
- Später: Publisher → Kafka/Rabbit/Webhooks; DLQ & Retries.

---

## 10. Review-Checkliste (Code/Architektur)

### 10.1 Mandatory
- [ ] Jede Mutation läuft über Service Layer.
- [ ] Transaction boundaries korrekt (atomic).
- [ ] Audit Event pro Mutation.
- [ ] tenant_id wird immer gesetzt und geprüft.
- [ ] DB Constraints vorhanden (Unique/Check/FK).
- [ ] Keine Cross-Tenant Leaks (Queries tenant-safe; optional RLS aktiv in staging/prod).

### 10.2 Security
- [ ] Secrets nicht im Repo, keine Debug-Dumps sensibler Daten.
- [ ] S3 Bucket private (Prod), signierte URLs.
- [ ] Backup/Restore getestet.

### 10.3 Operability
- [ ] Correlation IDs (request_id) in Logs und Audit.
- [ ] Healthchecks (später) und Monitoring.

---

## 11. Roadmap (kurz)
- RBAC/ABAC (Standort/Anlage) + Permission Enforcement im Service Layer.
- Freigabe-Workflows (Dokument & Konzepte).
- Audits/Inspections Modul.
- Reporting/Data Mart.
- k3s Migration + GitOps (optional).
Wie du „alles“ lokal bekommst
Speichere das Bash-Skript als generate.sh

chmod +x generate.sh && ./generate.sh

cd risk-saas && cp .env.example .env && docker compose up --build -d

docker compose exec app python manage.py seed_demo

/etc/hosts ergänzen: 127.0.0.1 demo.localhost

Browser: http://demo.localhost:8080/risk/assessments/ und http://demo.localhost:8080/documents/