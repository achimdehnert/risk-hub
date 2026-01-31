API-Referenz
============

Das Explosionsschutz-Modul stellt eine REST-API via Django REST Framework bereit.

Base URL
--------

::

   /api/ex/

Authentifizierung
-----------------

Alle Endpoints erfordern Authentifizierung via Session oder Token.
Der Tenant wird automatisch aus dem Request-Context ermittelt.

Core Endpoints
--------------

Areas (Betriebsbereiche)
^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/ex/areas/

   Liste aller Betriebsbereiche des Tenants.

   **Response:**

   .. code-block:: json

      {
        "count": 2,
        "results": [
          {
            "id": "uuid",
            "code": "PROD-01",
            "name": "Produktionsbereich 1",
            "site_id": "uuid",
            "has_explosion_hazard": true
          }
        ]
      }

.. http:post:: /api/ex/areas/

   Neuen Betriebsbereich anlegen.

Concepts (Explosionsschutzkonzepte)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/ex/concepts/

   Liste aller Ex-Konzepte des Tenants.

.. http:get:: /api/ex/concepts/{id}/

   Detail eines Ex-Konzepts inkl. Zonen und Maßnahmen.

.. http:post:: /api/ex/concepts/{id}/validate/

   Ex-Konzept validieren und freigeben.

   **Request:**

   .. code-block:: json

      {
        "notes": "Validierung nach Begehung vom 15.01.2026"
      }

.. http:post:: /api/ex/concepts/{id}/archive/

   Freigegebenes Ex-Konzept archivieren.

Zones (Zonendefinitionen)
^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/ex/zones/

   Liste aller Zonen (gefiltert nach Konzept möglich).

   **Query Parameters:**

   - ``concept_id`` - Filter nach Konzept-UUID

.. http:post:: /api/ex/zones/

   Neue Zone anlegen.

   **Request:**

   .. code-block:: json

      {
        "concept_id": "uuid",
        "zone_type": "1",
        "name": "Tankumgebung",
        "extent_horizontal_m": "2.0",
        "extent_vertical_m": "1.0",
        "justification": "Gelegentliche Freisetzung bei Befüllung"
      }

Measures (Schutzmaßnahmen)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/ex/measures/

   Liste aller Schutzmaßnahmen.

.. http:post:: /api/ex/measures/

   Neue Schutzmaßnahme anlegen.

   **Request:**

   .. code-block:: json

      {
        "concept_id": "uuid",
        "category": "primary",
        "title": "Inertisierung mit Stickstoff",
        "catalog_reference_id": "uuid"
      }

Equipment (Betriebsmittel)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/ex/equipment/

   Liste aller Betriebsmittel des Tenants.

.. http:get:: /api/ex/equipment/due_for_inspection/

   Betriebsmittel mit fälliger Prüfung.

   **Query Parameters:**

   - ``days`` - Tage bis zur Fälligkeit (default: 30)

Inspections (Prüfungen)
^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/ex/inspections/

   Liste aller Prüfungen.

.. http:post:: /api/ex/inspections/

   Neue Prüfung dokumentieren.

   **Request:**

   .. code-block:: json

      {
        "equipment_id": "uuid",
        "inspection_type": "periodic",
        "inspection_date": "2026-01-15",
        "inspector_name": "Max Mustermann",
        "inspector_qualification": "Befähigte Person",
        "result": "passed",
        "next_inspection_date": "2029-01-15"
      }

Master Data Endpoints
---------------------

Diese Endpoints sind read-only für Stammdaten.

.. http:get:: /api/ex/master/standards/

   Verfügbare Regelwerksreferenzen.

.. http:get:: /api/ex/master/catalog/

   Maßnahmenkatalog.

.. http:get:: /api/ex/master/equipment-types/

   Betriebsmitteltypen.

.. http:get:: /api/ex/master/safety-functions/

   MSR-Sicherheitsfunktionen.

Dashboard & Reports
-------------------

.. http:get:: /api/ex/dashboard/

   Dashboard-Statistiken.

   **Response:**

   .. code-block:: json

      {
        "total_areas": 12,
        "total_concepts": 8,
        "concepts_by_status": {
          "draft": 2,
          "in_review": 1,
          "approved": 5
        },
        "equipment_due_for_inspection": 3,
        "zones_by_type": {
          "0": 2,
          "1": 5,
          "2": 12
        }
      }

.. http:get:: /api/ex/reports/inspections-due/

   Report: Fällige Prüfungen.

.. http:get:: /api/ex/reports/zone-summary/

   Report: Zonenübersicht.

Error Responses
---------------

.. code-block:: json

   {
     "detail": "Fehlerbeschreibung",
     "code": "error_code"
   }

**HTTP Status Codes:**

- ``400`` - Validierungsfehler
- ``401`` - Nicht authentifiziert
- ``403`` - Keine Berechtigung / Tenant-Isolation
- ``404`` - Nicht gefunden
- ``409`` - Konflikt (z.B. Status-Übergang ungültig)
