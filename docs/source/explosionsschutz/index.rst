Explosionsschutz-Modul
======================

Das Explosionsschutz-Modul implementiert die vollständige Verwaltung von 
Explosionsschutzkonzepten nach ATEX/TRGS 720ff für die Risk-Hub Plattform.

.. toctree::
   :maxdepth: 2
   :caption: Inhalte:

   overview
   models
   api
   admin

Features
--------

- **Zoneneinteilung** nach ATEX 1999/92/EG (Zone 0, 1, 2 für Gase; Zone 20, 21, 22 für Stäube)
- **Schutzmaßnahmen** (primär, sekundär, tertiär, organisatorisch)
- **Betriebsmittel-Management** mit ATEX-Kennzeichnung und Prüffristen
- **Zündquellenbewertung** nach EN 1127-1 (13 Zündquellenarten)
- **Hybrid-Tenant-Isolation** für Stammdaten
- **Vollständiger Audit-Trail** via Service Layer

Architektur
-----------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                      API Layer (DRF)                        │
   ├─────────────────────────────────────────────────────────────┤
   │                    Service Layer                            │
   │  - Command DTOs    - Audit Events    - Outbox Messages      │
   ├─────────────────────────────────────────────────────────────┤
   │                    Model Layer                              │
   │  - Core Entities   - Master Data     - Hybrid Isolation     │
   ├─────────────────────────────────────────────────────────────┤
   │                 PostgreSQL + RLS                            │
   └─────────────────────────────────────────────────────────────┘

Schnellstart
------------

1. Migration ausführen::

      python manage.py migrate explosionsschutz

2. Seed-Daten laden::

      python manage.py loaddata explosionsschutz/fixtures/reference_standards.json
      python manage.py loaddata explosionsschutz/fixtures/measure_catalog.json

3. Admin-Interface: ``/admin/explosionsschutz/``

4. API-Endpoints: ``/api/ex/``
