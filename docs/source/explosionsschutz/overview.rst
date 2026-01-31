Überblick
=========

Rechtliche Grundlagen
---------------------

Das Modul basiert auf folgenden Regelwerken:

**EU-Richtlinien:**

- **ATEX 2014/34/EU** - Geräterichtlinie (Produkte)
- **ATEX 1999/92/EG** - Betriebsrichtlinie (Arbeitsplätze)

**Deutsche Verordnungen:**

- **BetrSichV** - Betriebssicherheitsverordnung
- **GefStoffV** - Gefahrstoffverordnung

**Technische Regeln:**

- **TRGS 720** - Gefährliche explosionsfähige Gemische
- **TRGS 721** - Beurteilung der Explosionsgefährdung
- **TRGS 722** - Vermeidung/Einschränkung gefährlicher Atmosphäre
- **TRGS 723** - Gefährliche explosionsfähige Gemische - Vermeidung der Entzündung
- **TRBS 2152** - Technische Regel Betriebssicherheit

**Normen:**

- **EN 60079-10-1** - Zoneneinteilung Gase
- **EN 60079-10-2** - Zoneneinteilung Stäube
- **EN 1127-1** - Zündquellenbewertung
- **EN 13463-1** - Nicht-elektrische Geräte

ATEX-Kennzeichnung
------------------

Betriebsmittel werden nach folgendem Schema gekennzeichnet:

.. code-block:: text

   Ex II 2G Ex d IIB T4 Gb

   │  │ ││ │  │ │   │  │
   │  │ ││ │  │ │   │  └── Equipment Protection Level (EPL)
   │  │ ││ │  │ │   └───── Temperaturklasse
   │  │ ││ │  │ └───────── Explosionsgruppe
   │  │ ││ │  └─────────── Zündschutzart
   │  │ ││ └────────────── Atmosphäre (G=Gas, D=Dust)
   │  │ │└──────────────── Kategorie (1, 2, 3)
   │  │ └───────────────── Gruppe (I=Bergbau, II=Industrie)
   │  └─────────────────── CE-Kennzeichnung
   └────────────────────── Ex-Symbol

Kategorien und Zonen
--------------------

+----------+------------------+------------------------+
| Kategorie| Erlaubte Zonen   | Schutzgrad             |
+==========+==================+========================+
| 1G       | 0, 1, 2          | Sehr hoher Schutz      |
+----------+------------------+------------------------+
| 2G       | 1, 2             | Hoher Schutz           |
+----------+------------------+------------------------+
| 3G       | 2                | Normaler Schutz        |
+----------+------------------+------------------------+
| 1D       | 20, 21, 22       | Sehr hoher Schutz      |
+----------+------------------+------------------------+
| 2D       | 21, 22           | Hoher Schutz           |
+----------+------------------+------------------------+
| 3D       | 22               | Normaler Schutz        |
+----------+------------------+------------------------+

Temperaturklassen
-----------------

+-------+------------------------+
| Klasse| Max. Oberflächentemp.  |
+=======+========================+
| T1    | 450°C                  |
+-------+------------------------+
| T2    | 300°C                  |
+-------+------------------------+
| T3    | 200°C                  |
+-------+------------------------+
| T4    | 135°C                  |
+-------+------------------------+
| T5    | 100°C                  |
+-------+------------------------+
| T6    | 85°C                   |
+-------+------------------------+

Explosionsgruppen
-----------------

+-------+-------------------+------------------------+
| Gruppe| Typische Gase     | MESG (mm)              |
+=======+===================+========================+
| IIA   | Propan, Methan    | > 0.9                  |
+-------+-------------------+------------------------+
| IIB   | Ethylen           | 0.5 - 0.9              |
+-------+-------------------+------------------------+
| IIC   | Wasserstoff, Acetylen | < 0.5              |
+-------+-------------------+------------------------+
