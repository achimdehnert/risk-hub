CSV Import
==========

The CSV import feature allows bulk upload of VVT, TOM, and AVV data from
semicolon-delimited CSV files.

Access
------

- **URL**: ``/dsb/import/``
- **URL name**: ``dsb:csv-import``
- **Template**: ``templates/dsb/import_upload.html``
- **View**: ``dsb.views.csv_import``

Supported CSV Types
-------------------

.. list-table::
   :header-rows: 1
   :widths: 15 40 45

   * - Type
     - Description
     - Required Headers
   * - VVT
     - Verarbeitungsverzeichnis (processing records)
     - ``Nr;Verarbeitungstaetigkeit;Gruppe;Zweck;...``
   * - TOM
     - Technische/Organisatorische Maßnahmen
     - ``Nr;TOM-Kategorie;Massnahme;Beschreibung;...``
   * - AVV
     - Auftragsverarbeitungsverträge
     - ``Nr;Dienstleister;Zweck;...``

CSV Format
----------

- **Delimiter**: Semicolon (``;``)
- **Encoding**: UTF-8
- **Type detection**: Automatic based on column headers (or manual override)

TOM Category Classification
---------------------------

TOM records are classified into categories using database-driven lookup via
the ``TomCategory`` model. Categories have a ``measure_type`` field:

- ``technical`` — Technische Maßnahmen
- ``organizational`` — Organisatorische Maßnahmen
- ``avv`` — AVV-bezogene Maßnahmen

Seed the categories with::

    python manage.py seed_tom_categories

This command is included in the CI/CD deploy pipeline.

Form Fields
-----------

- **CSV-Datei**: File upload (required)
- **Datentyp**: Auto / VVT / TOM (dropdown)
- **Mandat**: Tenant-filtered mandate selector (optional)

Import Flow
-----------

1. User uploads CSV file and selects type/mandate
2. System detects CSV type from headers (if auto)
3. Rows are parsed and mapped to Django models
4. Records are created with ``tenant_id`` and ``created_by`` from request
5. Results summary (created/skipped/errors) is displayed

Code Structure
--------------

.. code-block:: text

   src/dsb/
   ├── import_csv.py              # Core parsing + import logic
   ├── forms.py                   # CsvImportForm
   ├── views.py                   # csv_import view
   ├── urls.py                    # path("import/", ...)
   ├── models/lookups.py          # TomCategory model
   └── management/commands/
       └── seed_tom_categories.py # Seed command

   src/templates/dsb/
   └── import_upload.html          # Upload UI

Navigation
----------

CSV Import buttons are available on:

- DSB Dashboard (quick-access section)
- VVT list page
- TOM list page
- AVV list page
