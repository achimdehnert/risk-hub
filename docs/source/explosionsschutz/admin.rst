Admin-Interface
===============

Das Django-Admin-Interface bietet eine vollständige Verwaltungsoberfläche 
für das Explosionsschutz-Modul.

Zugriff
-------

::

   /admin/explosionsschutz/

Features
--------

Tenant-Awareness
^^^^^^^^^^^^^^^^

Alle Admin-Ansichten sind automatisch auf den aktuellen Tenant gefiltert.
Benutzer sehen nur Daten ihres eigenen Tenants.

Read-Only für System-Daten
^^^^^^^^^^^^^^^^^^^^^^^^^^

Globale Stammdaten (``is_system=True``) sind schreibgeschützt und 
können nicht bearbeitet oder gelöscht werden.

Inline-Editing
^^^^^^^^^^^^^^

Verwandte Objekte können direkt in der Detailansicht bearbeitet werden:

- **ExplosionConcept**: Zonen, Maßnahmen, Dokumente als Inlines
- **Equipment**: Prüfungen als Inline

Status-Badges
^^^^^^^^^^^^^

Farbcodierte Badges für bessere Übersicht:

- **Konzept-Status**: Draft (grau), In Review (blau), Approved (grün), Archived (gelb)
- **Maßnahmen-Status**: Open (rot), In Progress (orange), Implemented (blau), Verified (grün)
- **Prüfergebnis**: Passed (grün), Conditions (gelb), Failed (rot)

Workflow-Actions
^^^^^^^^^^^^^^^^

Direkte Aktionen für Statusübergänge:

- **Konzept validieren**: Setzt Status auf "approved" und markiert als validiert
- **Konzept archivieren**: Archiviert freigegebene Konzepte

Konfiguration
-------------

ExplosionConceptAdmin
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   @admin.register(ExplosionConcept)
   class ExplosionConceptAdmin(TenantAwareAdmin):
       list_display = [
           "title", "version", "area", 
           "substance_name", "status_badge", 
           "completion_badge", "validated_at"
       ]
       list_filter = ["status", "is_validated", "created_at"]
       search_fields = ["title", "area__name", "substance_name"]
       inlines = [
           ZoneDefinitionInline, 
           ProtectionMeasureInline, 
           VerificationDocumentInline
       ]
       actions = ["validate_concepts", "archive_concepts"]

EquipmentAdmin
^^^^^^^^^^^^^^

.. code-block:: python

   @admin.register(Equipment)
   class EquipmentAdmin(TenantAwareAdmin):
       list_display = [
           "serial_number", "equipment_type",
           "area", "zone", "status_badge",
           "next_inspection_date", "inspection_overdue"
       ]
       list_filter = [
           "status", "equipment_type__atex_category",
           InspectionDueFilter
       ]
       inlines = [InspectionInline]

Custom Filters
^^^^^^^^^^^^^^

- **InspectionDueFilter**: Filtert nach fälligen Prüfungen (30/60/90 Tage)
- **ZoneTypeFilter**: Filtert nach Zonentyp

Berechtigungen
--------------

Folgende Permissions werden verwendet:

- ``explosionsschutz.add_explosionconcept``
- ``explosionsschutz.change_explosionconcept``
- ``explosionsschutz.delete_explosionconcept``
- ``explosionsschutz.view_explosionconcept``
- ``explosionsschutz.can_validate_concept`` (custom)
- ``explosionsschutz.can_archive_concept`` (custom)

Gleiche Struktur für alle anderen Models.
