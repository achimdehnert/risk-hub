# Risk-Hub (Schutztat) — Project Context

## What is this project?

A multi-tenant SaaS platform for German occupational safety (Arbeitsschutz),
covering hazardous substances (Gefahrstoffe), explosion protection
(Explosionsschutz), risk assessments (Gefährdungsbeurteilungen), and
document management.

## Domain: `schutztat.de`

- Base: `schutztat.de` — Landing / marketing
- Tenants: `{slug}.schutztat.de` — e.g. `demo.schutztat.de`

## Key Business Concepts

- **Gefahrstoff (Hazardous Substance)**: Chemical with GHS classification
- **SDB / SDS (Sicherheitsdatenblatt)**: Safety Data Sheet revision
- **H-Sätze / P-Sätze**: Hazard / Precautionary statements (EU GHS)
- **Piktogramme**: GHS pictograms (GHS01-GHS09)
- **Lagerklasse (TRGS 510)**: Storage class for chemicals
- **Gefährdungsbeurteilung**: Risk assessment (legal requirement)
- **Explosionsschutz (ATEX)**: Explosion protection zones and equipment
- **Ex-Zone**: ATEX zone classification (0, 1, 2, 20, 21, 22)
- **Temperaturklasse**: Temperature class for ignition protection

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Multi-tenancy | Row-level `tenant_id` | Simple, works with Django ORM |
| Frontend | Tailwind CDN + HTMX | Fast iteration, no build step |
| Auth | Django built-in + middleware | Subdomain-based tenant resolution |
| Deployment | Docker Compose on Hetzner | Cost-effective, full control |
| CI/CD | Manual (Docker build + push) | Small team, rapid iteration |
| Database | PostgreSQL 16 | Production-grade, JSON support |
