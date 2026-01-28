# Enterprise SaaS Risikomanagement – Review-fähiges Gesamt-Konzept (v1.1)
Stand: 2026-01-28  
Zielplattform: Start **Hetzner (VM + Docker)**, Stack **Postgres + Django + HTMX**, **Subdomain Multi-Tenancy**, **S3/MinIO Dokumente**  
Dieses Dokument ergänzt das bestehende Grundkonzept um:
- **RBAC/Permissions Modell (Tenant/Site/Asset-Scope)**
- **Export/Reporting (PDF/Excel) + Audit-konforme Retention**
- **Hetzner Production Blueprint (Sizing, LB, Backups, DR, Monitoring)**

---

## 0. Executive Summary
Wir bauen eine mandantenfähige SaaS-Plattform für EHS/Risikomanagement (Brandschutz, Explosionsschutz, Arbeitsschutz etc.) mit:
- **klaren Domänengrenzen** (Modular Monolith → spätere Auskopplung möglich),
- **DB-getriebenen Invarianten** (Constraints + optional Postgres RLS),
- **Service Layer** als einzige Write-API (Audit/Outbox verpflichtend),
- **Subdomain-Tenant-Auflösung** (`{tenant}.deine-domain.tld`),
- **Dokumentenmodul** mit Versionierung und S3-kompatiblem Storage,
- **RBAC** mit **Scope-Mechanismus** (Tenant/Site/Asset) und optionaler ABAC-Erweiterung,
- **Exports** als nachverfolgbare Artefakte (PDF/Excel) inkl. Retention/Legal Hold,
- **Hetzner Prod-Setup** mit HA-App, abgesichertem Postgres, Backups, DR und Observability.

---

## 1. Architekturprinzipien & Regeln (Review-Kriterien)

### 1.1 DB-getrieben
- Datenbank ist **Source of Truth** für Integrität:
  - `NOT NULL`, FK, Unique pro Tenant, Check Constraints
  - Statusmaschinen **primär in Domain/Service**, DB Check Constraints als Safety Net
- Migrationen nach **Expand/Contract** (keine riskanten Big-Bang Breaking Changes)

### 1.2 Separation of Concerns
- **UI** (HTMX Views/Templates): Input → Service call → Render
- **Service Layer** (Application Layer): Use Cases, Transaktionen, Berechtigungen, Audit, Outbox
- **Domain**: Regeln/Policies/Statusübergänge
- **Infrastructure**: Postgres/S3/Queues/Email/Integrationen

### 1.3 Service-orientiert, pragmatisch
- Start als **Modularer Monolith** mit Bounded Contexts (Apps)
- Klare Grenzen + Outbox Events → spätere Auskopplung ohne Re-Write

### 1.4 Naming Konventionen
- Apps: `tenancy`, `identity`, `permissions`, `risk`, `actions`, `documents`, `audits`, `reporting`
- Tables: `snake_case`, thematisch (`risk_assessment`, `documents_document_version`)
- Spalten: `id`, `tenant_id`, `created_at`, `updated_at` (wo relevant)

---

## 2. Mandantenfähigkeit (Multi-Tenancy)

### 2.1 Tenant Resolution: Subdomain
- Tenant via Host: `{tenant}.deine-domain.tld`
- Mapping: `Organization.slug = tenant`
- Middleware setzt RequestContext + DB Session Variable (für RLS, wenn aktiv)

### 2.2 Tenant Isolation
- Jede fachliche Tabelle enthält `tenant_id`
- Optional in Staging/Prod: **Postgres Row Level Security**
  - `SET LOCAL app.current_tenant = <uuid>`
  - Policy: `tenant_id = current_setting('app.current_tenant')::uuid`

---

## 3. RBAC/Permissions Modell (Tenant / Site / Asset Scope)

### 3.1 Anforderungen
- Enterprise-taugliche Berechtigungen:
  - **Mandant**: Isolation, Rollen pro Mandant
  - **Standort (Site)**: Sichtbarkeit/Schreibrechte nur für bestimmte Standorte
  - **Asset** (Anlage/Gebäude/Arbeitsplatz/Gefahrbereich): feingranulare Rechte
- Auditierbar: jede relevante Admin-Änderung an Roles/Assignments muss auditiert werden

### 3.2 Modell: RBAC mit Scope (hierarchisch)
Wir nutzen **RBAC** (Rollen → Permissions), erweitert um **Scopes**:
- `TENANT` (gesamter Mandant)
- `SITE` (eine oder mehrere Sites)
- `ASSET` (ein oder mehrere Assets)
- Optional später: `DEPARTMENT`, `PROJECT`, `DOCUMENT_CATEGORY`

Hierarchie (implizite Vererbung):
- Tenant Scope umfasst alle Sites/Assets im Tenant
- Site Scope umfasst Assets der Site
- Asset Scope umfasst nur das Asset

### 3.3 Permission Taxonomie (Beispiele)
Permissions sind **strings** mit stabilem Naming:
- `risk.assessment.read`, `risk.assessment.write`, `risk.assessment.approve`
- `actions.action.read`, `actions.action.write`, `actions.action.close`
- `documents.document.read`, `documents.document.write`, `documents.document.approve`
- `report.export.create`, `report.export.read`
- `admin.roles.manage`, `admin.users.manage`, `admin.sites.manage`

Guideline:
- `*.read`, `*.write`, `*.approve`, `*.delete` (sparsam), `admin.*`

### 3.4 Rollen (Beispiele)
Vordefinierte Rollen (pro Tenant konfigurierbar):
- `Tenant Admin`: volle Admin-Rechte, Rollenverwaltung
- `EHS Manager`: write/approve für Risk & Docs, Maßnahmen
- `Site Safety Officer`: write für Site Scope, approve optional
- `Auditor`: read-only, export read, audit read
- `Worker`: read + limited write (z. B. Findings/Maßnahmen erstellen)

### 3.5 Datenmodell (Django/Postgres – Vorschlag)
**Kern-Tabellen:**
- `permissions_permission`  
  - `id`, `code` (unique), `description`
- `permissions_role`  
  - `id`, `tenant_id`, `name` (unique per tenant), `is_system`
- `permissions_role_permission` (m2m)
  - `role_id`, `permission_id`
- `permissions_scope`  
  - `id`, `tenant_id`, `scope_type` (`TENANT|SITE|ASSET`), `site_id?`, `asset_id?`  
  - DB Checks: je nach `scope_type` muss genau die passende FK gesetzt sein
- `permissions_assignment`  
  - `id`, `tenant_id`, `user_id`, `role_id`, `scope_id`, `created_at`, `created_by_user_id`

**Assets** (vereinheitlicht):
- `assets_asset` (oder in `assets` App)
  - `id`, `tenant_id`, `site_id`, `asset_type`, `name`, …

### 3.6 Enforcement (entscheidend)
**Regel**: Kein ORM Query ohne Scope-Filter in Write/Read-Pfaden mit sensiblen Daten.

Implementierung:
1) Middleware setzt `tenant_id` im Kontext.
2) Service Layer ruft `authorize(user, permission, object_ref)`:
   - Ermittelt Assignments des Users im Tenant
   - Prüft Permission in Role
   - Prüft Scope:
     - `TENANT` → OK
     - `SITE` → object.site_id muss in Scope.site_id
     - `ASSET` → object.asset_id muss in Scope.asset_id
3) Repository/Query Helper erzwingt für Listen:
   - Allowed scopes werden zu Filterkriterien aggregiert (z. B. `site_id IN (...)`)

**Performance-Strategie:**
- Materialized Access Cache (optional):  
  pro User+Tenant eine Tabelle/Cache mit erlaubten Site/Asset IDs
- Indizes:
  - `assignment (tenant_id, user_id)`
  - `scope (tenant_id, scope_type, site_id, asset_id)`

### 3.7 ABAC (optional später)
Zusätzliche Regeln über Attribute:
- Beispiel: Zugriff auf Explosionsschutz nur für Benutzer mit Qualifikation X
- Technisch: Policy Engine (OPA) oder DSL im Service Layer
- Start: RBAC+Scope reicht (einfach, reviewbar)

### 3.8 Audit-Anforderungen für Permissions
- Jede Änderung an:
  - Roles, RolePermissions, Assignments, Scopes
  muss ein `audit_event` erzeugen (`category=permissions.*`)

---

## 4. Export/Reporting (PDF/Excel) + Audit-konforme Retention

### 4.1 Anforderungen
- Exports müssen:
  - reproduzierbar (Parameter + Datenstand referenzierbar),
  - auditierbar (wer hat wann was exportiert),
  - ggf. unveränderlich (WORM/Retention, Legal Hold),
  - tenant-isoliert (keine Cross-Tenant Daten).

### 4.2 Export Arten
- **PDF**
  - z. B. Brandschutzkonzept, Gefährdungsbeurteilung, Auditbericht
- **Excel**
  - Maßnahmenliste, Audit Findings, Anlagenregister, KPI Exports

### 4.3 Architektur: Export als „Artefakt“
Neues Modul: `reporting`

**Tabellen:**
- `reporting_export_job`
  - `id`, `tenant_id`, `requested_by_user_id`, `type`, `params_json`
  - `status` (`queued|running|done|failed`)
  - `started_at`, `finished_at`, `error`
  - `output_document_version_id` (FK in documents) oder `s3_key`
  - `retention_policy_id` (optional)
- `reporting_report_template` (optional, später)
  - Vorlagenversionen, Branding, Layout

**Flow:**
1) UI triggert `create_export_job(type, params)`
2) Service:
   - `authorize(user, report.export.create, scope)`
   - speichert Job + Outbox Event `report.export.requested`
3) Worker verarbeitet:
   - Jobstatus `running`
   - Datenabfrage **scope-gesichert**
   - Generiert Datei:
     - PDF via Report Engine (z. B. ReportLab oder HTML→PDF)
     - Excel via `openpyxl`
   - Speichert Ergebnis als `DocumentVersion` (S3)
   - Jobstatus `done`
   - Audit event `report.export.created`

### 4.4 PDF Strategie (Django)
Option A (robust, deterministic): **ReportLab**
- Vorteil: deterministische Layouts, weniger Abhängigkeit vom Browser-Rendering
- Gut für Compliance-Dokumente

Option B (template-driven): HTML → PDF (WeasyPrint/wkhtmltopdf)
- Vorteil: HTML Templates wiederverwendbar, schneller für komplexe Layouts
- Risiko: Rendering/Fonts/OS Dependencies, muss sauber im Container gebaked werden

Empfehlung:
- Für „Compliance-Kernberichte“: ReportLab
- Für „schöne Berichte/Layouts“: HTML→PDF später

### 4.5 Excel Strategie
- `openpyxl` mit:
  - fixen Spalten, Styles, Header Freeze, Data Validations
- Export Spezifikation versionieren (Template-Version in Job speichern)

### 4.6 Audit-Konformität
Jeder Export erzeugt:
- Audit Event: `report.export.created` mit:
  - `job_id`, `type`, `params_hash`, `output_doc_version_id`, `row_count`, `created_at`
- Optional: Signatur/Checksumme
  - SHA256 der Datei in `DocumentVersion`

### 4.7 Retention & WORM (Audit-konform)
Wir unterscheiden **Operational** vs. **Compliance** Retention:

**Operational Retention (Default)**
- z. B. Exports 90 Tage, Logs 30 Tage

**Compliance Retention (Policy-basiert)**
- Retention Policies pro Kategorie:
  - `brandschutz`: 10 Jahre
  - `explosionsschutz`: 10 Jahre
  - `audit_reports`: 6 Jahre
  - `training_records`: 6 Jahre
- Policy Felder:
  - `name`, `years`, `legal_hold_allowed`, `delete_mode` (`soft|hard|never`)

**Legal Hold**
- Flag auf `Document`/`DocumentVersion`:
  - verhindert Löschung unabhängig von Laufzeit
- Audit event bei Set/Unset

**WORM/Immutability**
- In S3/Hetzner Object Storage: idealerweise Bucket-Features für Object Lock (wenn verfügbar).
- Falls nicht verfügbar:
  - Applikationsseitig: „no overwrite“ (nur new versions), kein delete bei legal hold, plus regelmäßige Integrity Checks
  - Optional: zusätzliches Archiv in Storage Box (append-only via borg/restic) als zweite Kopie

### 4.8 Löschkonzept (DSGVO vs. Compliance)
- PII (User-Daten) kann pseudonymisiert werden, während Compliance-Dokumente erhalten bleiben.
- Trennung:
  - `identity_user` (PII) → anonymisierbar
  - `documents` / `audit` → retention-gesteuert

---

## 5. Hetzner Production Blueprint (Sizing, LB, Backups, DR, Monitoring)

### 5.1 Ziel: HA für App, solide Datenbank, klare Betriebsprozesse
Wir planen 3 Umgebungen:
- `dev` (compose lokal)
- `staging` (prod-ähnlich, RLS aktiv, kleine Größen)
- `prod` (HA App, gesichertes Postgres, Backups/DR, Monitoring)

### 5.2 Netzwerk & Security Layout (Prod)
- Hetzner Cloud Network (privates Netz):
  - `public` Subnet: LB / reverse proxy
  - `private` Subnet: app/worker/db/monitoring
- Firewall:
  - inbound public: 80/443 nur LB
  - inbound private: DB nur von app/worker
- SSH:
  - nur per VPN oder Bastion Host (oder Hetzner SSH keys + IP allowlist)

### 5.3 VM Sizing (Startpunkt, skalierbar)
**Small/Start (bis niedrige zweistellige Kunden, moderate Nutzung)**
- `lb-1`: CX22 (oder shared) reicht (oder Hetzner LB managed)
- `app-1`, `app-2`: CPX31 (4 vCPU / 8 GB)
- `worker-1`: CPX21 (2 vCPU / 4 GB)
- `db-1`: CPX41 (8 vCPU / 16 GB) + NVMe (oder Volume), je nach Last
- `mon-1`: CX32 (4 vCPU / 8 GB) für Prometheus/Grafana/Loki

**Medium (mehr Tenants, mehr Docs/Exports)**
- `app`: CPX41 (8/16) x2-3
- `worker`: CPX31 x2 (separat für exports)
- `db`: Dedicated / größere CPX + Tuning + ggf. read replica

Wichtiger als exakte Größen:
- App horizontal skalieren, DB vertikal + ggf. replizieren

### 5.4 Load Balancing & TLS
Option A (einfach, gut): **Hetzner Load Balancer**
- TLS Termination am LB (cert automation)
- Weiterleitung an `app-*` im privaten Netz

Option B (self-managed): Nginx/Traefik auf `lb-1`
- Mehr Kontrolle, aber mehr Ops

Empfehlung: Hetzner LB, Traefik nur wenn ihr spezielle Routing/ACME-Anforderungen habt.

### 5.5 Postgres Betrieb (Prod)
Minimum:
- `db-1` Postgres 16
- Tuning:
  - `shared_buffers`, `work_mem`, `effective_cache_size`, autovacuum
- Connection Pooler:
  - `pgbouncer` zwischen app und db (reduziert DB connection churn)

Optional HA:
- `db-1` primary + `db-2` standby (Streaming Replication)
- Failover manuell oder via Patroni (mehr Ops, aber robust)

### 5.6 Backups & PITR (Pflicht)
**Ziel:** Jederzeit Restore auf Punkt-in-Zeit (PITR).

Konzept:
- **WAL Archiving** + regelmäßige Base Backups
- Tooling:
  - `wal-g` oder `pgBackRest`
- Storage:
  - Hetzner Object Storage oder Storage Box (SFTP) als Backup Target
- Policy:
  - Base Backup: täglich
  - WAL: kontinuierlich
  - Retention: 14–30 Tage PITR, plus Monatsarchive (compliance-abhängig)

**Restore Tests**
- Staging „Restore Drill“ (monatlich/quarterly):
  - Backup zurückspielen, Smoke Tests, RLS check

### 5.7 DR (Disaster Recovery)
Zielwerte (als Startpunkt, später anpassen):
- RPO: 15 Minuten (mit WAL)
- RTO: 2–4 Stunden (initial), später <1h möglich

DR Setup:
- Replikation/Backups in **zweite Region** (Hetzner: zweites Datacenter)
- IaC (Terraform/Ansible) für Neuaufbau
- Runbook:
  - DNS cutover
  - Secrets restore
  - DB restore/promote
  - App deploy

### 5.8 Monitoring & Logging
Minimum Set:
- **Prometheus**: CPU/RAM/Disk, Postgres exporter, Nginx metrics, app metrics
- **Grafana**: Dashboards + Alerts
- **Loki** (oder ELK): zentralisierte Logs
- App Logging:
  - structured JSON logs mit `request_id`, `tenant_id`, `user_id`

Alerts:
- DB: replication lag, disk usage, slow queries, connection saturation
- App: 5xx rate, latency p95, worker backlog, export job failures
- Infra: node down, cert expiry

### 5.9 Security & Compliance Ops
- regelmäßige OS Patching windows
- Dependency scanning / image scanning
- Secrets rotation (DB, S3)
- Audit log retention (mindestens analog compliance)

---

## 6. Review-Checkliste (Architektur & Implementierung)

### 6.1 RBAC
- [ ] Permissions als stabile Codes (`module.resource.action`)
- [ ] Rollen pro Tenant, Assignments mit Scope
- [ ] Scope Checks in jedem Service Use Case (read/write/export)
- [ ] Indizes & Query Helper für performante Scope-Filter
- [ ] Audit Events für Role/Assignment Änderungen

### 6.2 Export/Reporting
- [ ] Export ist Job/Artefakt mit Parametern + Status
- [ ] Job Ergebnis als versioniertes Dokument (S3) mit SHA256
- [ ] Audit Event pro Export
- [ ] Retention Policy je Kategorie + Legal Hold

### 6.3 Ops/Prod
- [ ] LB + TLS sauber (Subdomain Routing)
- [ ] Postgres Backups + PITR + Restore Tests
- [ ] Monitoring + Alerts definiert
- [ ] DR Runbook vorhanden

---

## 7. Konkrete nächste Implementierungs-Schritte (kurz, review-orientiert)
1) `permissions` App:
   - Datenmodell (Role, Permission, Scope, Assignment)
   - `authorize()` Library + Tests
2) Service Layer Enforcement:
   - alle Use Cases nutzen `authorize()`
   - Liste/Query Helpers: `filter_by_scopes(queryset, user, permission)`
3) `reporting` App:
   - ExportJob + Worker + PDF/Excel Generator
   - Speicherung als `documents.DocumentVersion`
4) Retention Policies:
   - `documents.retention_policy` + Legal Hold
   - Cleanup job (nur wenn erlaubt)
5) Prod-Betrieb:
   - pgbouncer + wal-g/pgBackRest + Monitoring Stack
   - IaC + Runbooks (Backup/Restore/DR)

---

## 8. Anhang: Minimaler Permission/Sichtbarkeits-Algorithmus (Pseudo)
- `allowed_scopes = assignments(user, tenant).where(permission)`
- if any scope.type == TENANT → allow
- else if object has site_id:
  - allow if object.site_id in scopes.site_ids
- else if object has asset_id:
  - allow if object.asset_id in scopes.asset_ids
- lists:
  - tenant-wide: `WHERE tenant_id = ? AND (site_id IN (...) OR asset_id IN (...))`
  - careful: join assets for site filtering if needed

---

Ende.
