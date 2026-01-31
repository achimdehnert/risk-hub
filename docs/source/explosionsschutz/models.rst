Datenmodell
===========

Entity-Relationship-Diagramm
----------------------------

.. code-block:: text

   ┌─────────────────┐     ┌─────────────────┐
   │ ReferenceStandard│    │  MeasureCatalog │
   │ (Stammdaten)    │◄───┤  (Stammdaten)   │
   └────────┬────────┘     └────────┬────────┘
            │                       │
            │                       │
   ┌────────▼────────┐     ┌────────▼────────┐
   │  ZoneDefinition │     │ProtectionMeasure│
   │                 │     │                 │
   └────────┬────────┘     └─────────────────┘
            │                       ▲
            │                       │
   ┌────────▼────────┐     ┌────────┴────────┐
   │   Equipment     │     │ ExplosionConcept│
   │                 ├────►│                 │
   └────────┬────────┘     └────────┬────────┘
            │                       │
   ┌────────▼────────┐     ┌────────▼────────┐
   │   Inspection    │     │      Area       │
   └─────────────────┘     └─────────────────┘

Stammdaten (Master Data)
------------------------

ReferenceStandard
^^^^^^^^^^^^^^^^^

Regelwerksreferenzen (Normen, Richtlinien, TRGS).

.. py:class:: ReferenceStandard

   :ivar code: Kurzbezeichnung (z.B. "EN 60079-10-1")
   :ivar title: Vollständiger Titel
   :ivar category: norm | directive | trgs | other
   :ivar is_system: True = globale Systemdaten

MeasureCatalog
^^^^^^^^^^^^^^

Vordefinierte Schutzmaßnahmen aus TRGS 722/723.

.. py:class:: MeasureCatalog

   :ivar code: Eindeutiger Code
   :ivar title: Maßnahmentitel
   :ivar default_type: primary | secondary | tertiary | organizational
   :ivar reference_standards: Verknüpfte Regelwerke

EquipmentType
^^^^^^^^^^^^^

Betriebsmitteltypen mit ATEX-Kennzeichnung.

.. py:class:: EquipmentType

   :ivar manufacturer: Hersteller
   :ivar model: Modellbezeichnung
   :ivar atex_group: I (Bergbau) | II (Industrie)
   :ivar atex_category: 1, 2, 3
   :ivar protection_type: Zündschutzart (d, e, i, p, etc.)
   :ivar explosion_group: IIA, IIB, IIC
   :ivar temperature_class: T1-T6
   :ivar epl: Equipment Protection Level (Ga, Gb, Gc, Da, Db, Dc)

Core Entities
-------------

Area
^^^^

Betriebsbereich/Anlage innerhalb eines Standorts.

.. py:class:: Area

   :ivar site_id: Zugehöriger Standort
   :ivar code: Eindeutiger Bereichscode
   :ivar name: Bereichsname
   :ivar has_explosion_hazard: Ex-relevant?

ExplosionConcept
^^^^^^^^^^^^^^^^

Explosionsschutzkonzept nach TRGS 720ff.

.. py:class:: ExplosionConcept

   :ivar area: Zugehöriger Betriebsbereich
   :ivar substance_id: Hauptgefahrstoff (UUID)
   :ivar title: Konzepttitel
   :ivar version: Versionsnummer
   :ivar status: draft | in_review | approved | archived
   :ivar is_validated: Validierungsstatus

ZoneDefinition
^^^^^^^^^^^^^^

Zoneneinteilung nach ATEX.

.. py:class:: ZoneDefinition

   :ivar concept: Zugehöriges Ex-Konzept
   :ivar zone_type: 0, 1, 2, 20, 21, 22, non_ex
   :ivar name: Zonenbezeichnung
   :ivar extent: Geometrie (JSON)
   :ivar extent_horizontal_m: Horizontale Ausdehnung
   :ivar extent_vertical_m: Vertikale Ausdehnung
   :ivar justification: Begründung

ProtectionMeasure
^^^^^^^^^^^^^^^^^

Schutzmaßnahme innerhalb eines Ex-Konzepts.

.. py:class:: ProtectionMeasure

   :ivar concept: Zugehöriges Ex-Konzept
   :ivar category: primary | secondary | tertiary | organizational
   :ivar title: Maßnahmentitel
   :ivar status: open | in_progress | implemented | verified
   :ivar safety_function: Verknüpfte MSR-Sicherheitsfunktion

Equipment
^^^^^^^^^

Betriebsmittel in einer Zone.

.. py:class:: Equipment

   :ivar equipment_type: Betriebsmitteltyp
   :ivar area: Betriebsbereich
   :ivar zone: Zugeordnete Zone
   :ivar serial_number: Seriennummer
   :ivar status: active | inactive | decommissioned
   :ivar next_inspection_date: Nächste Prüfung

Inspection
^^^^^^^^^^

Wiederkehrende Prüfung eines Betriebsmittels.

.. py:class:: Inspection

   :ivar equipment: Geprüftes Betriebsmittel
   :ivar inspection_type: initial | periodic | extraordinary
   :ivar inspection_date: Prüfdatum
   :ivar result: passed | passed_with_conditions | failed
   :ivar findings: Feststellungen
   :ivar next_inspection_date: Nächste Prüfung

ZoneIgnitionSourceAssessment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Zündquellenbewertung nach EN 1127-1.

.. py:class:: ZoneIgnitionSourceAssessment

   :ivar zone: Bewertete Zone
   :ivar ignition_source: Zündquellenart (13 Typen)
   :ivar is_present: Zündquelle vorhanden?
   :ivar is_effective: Zündquelle wirksam?
   :ivar mitigation: Gegenmaßnahmen

Hybrid-Tenant-Isolation
-----------------------

Stammdaten unterstützen sowohl globale System-Daten als auch 
tenant-spezifische Anpassungen:

.. code-block:: python

   # Alle für einen Tenant sichtbaren Standards
   standards = ReferenceStandard.objects.for_tenant(tenant_id)
   
   # Nur globale System-Standards
   system_standards = ReferenceStandard.objects.global_only()
   
   # Nur tenant-eigene Standards
   custom_standards = ReferenceStandard.objects.tenant_only(tenant_id)
