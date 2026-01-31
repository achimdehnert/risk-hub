# Explosionsschutz-Modul: Migration & Implementierungsplan

> **Version:** 2.0  
> **Datum:** 2026-01-31  
> **Basis:** ADR-001 v5 (Enterprise Edition)

---

## 1. Voraussetzungen

### 1.1 Abhängige Module

| Modul | Status | Beschreibung |
| ----- | ------ | ------------ |
| `tenancy` | ✅ Vorhanden | Organization, Site |
| `identity` | ✅ Vorhanden | User, Rollen |
| `substances` | ⏳ Erforderlich | SDS-Modul muss zuerst implementiert werden |
| `risk` | ✅ Optional | Assessment-Integration |
| `documents` | ✅ Optional | Dokumenten-Upload |
| `audit` | ✅ Optional | Audit-Logging |

### 1.2 Technische Voraussetzungen

```bash
# Django 5.x
# PostgreSQL 16+
# WeasyPrint für PDF
# dateutil für Datumsberechnungen

pip install python-dateutil weasyprint
```

---

## 2. Migrations-Sequenz

### Phase 0: Voraussetzung SDS-Modul (Sprint 1-4)

```bash
# Zuerst substances-Modul implementieren
python manage.py startapp substances
# Siehe: Schutzbar_SDS_Implementierungskonzept.md
```

### Phase 1: App-Struktur (Sprint 5)

```bash
# 1. Django App erstellen
python manage.py startapp explosionsschutz
mv explosionsschutz src/

# 2. In INSTALLED_APPS registrieren
# config/settings/base.py
INSTALLED_APPS = [
    ...
    'explosionsschutz',
]
```

### Phase 2: Stammdaten-Migrationen

```python
# explosionsschutz/migrations/0001_reference_data.py

from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ReferenceStandard',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('category', models.CharField(
                    max_length=20,
                    choices=[
                        ('trgs', 'TRGS'),
                        ('iec', 'IEC'),
                        ('en', 'EN'),
                        ('atex', 'ATEX'),
                        ('other', 'Sonstige'),
                    ],
                    default='trgs'
                )),
                ('url', models.URLField(blank=True, default='')),
                ('description', models.TextField(blank=True, default='')),
            ],
            options={
                'db_table': 'ex_reference_standard',
                'verbose_name': 'Regelwerksreferenz',
                'verbose_name_plural': 'Regelwerksreferenzen',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='MeasureCatalog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True, null=True, blank=True)),
                ('title', models.CharField(max_length=255)),
                ('default_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('primary', 'Primäre Maßnahme'),
                        ('secondary', 'Sekundäre Maßnahme'),
                        ('constructive', 'Konstruktive Maßnahme'),
                    ],
                    default='secondary'
                )),
                ('description_template', models.TextField(blank=True)),
                ('is_global', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'ex_measure_catalog',
                'verbose_name': 'Maßnahmenkatalog',
            },
        ),
    ]
```

### Phase 3: SafetyFunction & EquipmentType

```python
# explosionsschutz/migrations/0002_safety_equipment_type.py

class Migration(migrations.Migration):
    dependencies = [
        ('explosionsschutz', '0001_reference_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='SafetyFunction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('performance_level', models.CharField(max_length=5, blank=True, default='')),
                ('sil_level', models.CharField(max_length=5, blank=True, default='')),
                ('monitoring_method', models.CharField(max_length=255, blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ex_safety_function',
            },
        ),
        migrations.CreateModel(
            name='EquipmentType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True, null=True, blank=True)),
                ('manufacturer', models.CharField(max_length=200)),
                ('model', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('atex_category', models.CharField(max_length=10, blank=True, default='')),
                ('atex_group', models.CharField(max_length=10, blank=True, default='')),
                ('temperature_class', models.CharField(max_length=10, blank=True, default='')),
                ('protection_type', models.CharField(max_length=50, blank=True, default='')),
                ('ip_rating', models.CharField(max_length=10, blank=True, default='')),
                ('default_inspection_interval_months', models.PositiveIntegerField(default=12)),
                ('is_global', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'ex_equipment_type',
            },
        ),
        migrations.AddConstraint(
            model_name='equipmenttype',
            constraint=models.UniqueConstraint(
                fields=['manufacturer', 'model'],
                name='uq_equipment_type_mfr_model'
            ),
        ),
    ]
```

### Phase 4: Core Entities

```python
# explosionsschutz/migrations/0003_area_concept.py

class Migration(migrations.Migration):
    dependencies = [
        ('explosionsschutz', '0002_safety_equipment_type'),
        ('substances', '0001_initial'),  # SDS-Modul
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('site_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=50, blank=True, default='')),
                ('description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ex_area',
            },
        ),
        migrations.CreateModel(
            name='ExplosionConcept',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=255)),
                ('version', models.PositiveIntegerField(default=1)),
                ('status', models.CharField(max_length=20, default='draft')),
                ('assessment_id', models.UUIDField(null=True, blank=True, db_index=True)),
                ('is_validated', models.BooleanField(default=False)),
                ('validated_at', models.DateTimeField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('area', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='explosion_concepts',
                    to='explosionsschutz.area'
                )),
                ('substance', models.ForeignKey(
                    on_delete=models.PROTECT,
                    related_name='explosion_concepts',
                    to='substances.substance'
                )),
            ],
            options={
                'db_table': 'ex_concept',
                'ordering': ['-created_at'],
            },
        ),
    ]
```

### Phase 5: Zones & Measures

```python
# explosionsschutz/migrations/0004_zones_measures.py

class Migration(migrations.Migration):
    dependencies = [
        ('explosionsschutz', '0003_area_concept'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZoneDefinition',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('zone_type', models.CharField(max_length=10, default='2')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('justification', models.TextField(blank=True, default='')),
                ('extent', models.JSONField(null=True, blank=True)),
                ('extent_horizontal_m', models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)),
                ('extent_vertical_m', models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)),
                ('reference_section', models.CharField(max_length=50, blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('concept', models.ForeignKey(on_delete=models.CASCADE, related_name='zones', to='explosionsschutz.explosionconcept')),
                ('reference_standard', models.ForeignKey(on_delete=models.SET_NULL, null=True, blank=True, to='explosionsschutz.referencestandard')),
            ],
            options={
                'db_table': 'ex_zone_definition',
            },
        ),
        migrations.CreateModel(
            name='ProtectionMeasure',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('category', models.CharField(max_length=20, default='secondary')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(max_length=20, default='open')),
                ('due_date', models.DateField(null=True, blank=True)),
                ('verified_at', models.DateTimeField(null=True, blank=True)),
                ('verification_notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('concept', models.ForeignKey(on_delete=models.CASCADE, related_name='measures', to='explosionsschutz.explosionconcept')),
                ('catalog_reference', models.ForeignKey(on_delete=models.SET_NULL, null=True, blank=True, to='explosionsschutz.measurecatalog')),
                ('safety_function', models.ForeignKey(on_delete=models.SET_NULL, null=True, blank=True, to='explosionsschutz.safetyfunction')),
            ],
            options={
                'db_table': 'ex_protection_measure',
                'ordering': ['category', 'title'],
            },
        ),
    ]
```

### Phase 6: Equipment & Inspection

```python
# explosionsschutz/migrations/0005_equipment_inspection.py

class Migration(migrations.Migration):
    dependencies = [
        ('explosionsschutz', '0004_zones_measures'),
    ]

    operations = [
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('serial_number', models.CharField(max_length=100, blank=True, default='')),
                ('asset_number', models.CharField(max_length=100, blank=True, default='')),
                ('location_detail', models.CharField(max_length=255, blank=True, default='')),
                ('status', models.CharField(max_length=20, default='active')),
                ('installation_date', models.DateField(null=True, blank=True)),
                ('last_inspection_date', models.DateField(null=True, blank=True)),
                ('next_inspection_date', models.DateField(null=True, blank=True)),
                ('inspection_interval_months', models.PositiveIntegerField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('area', models.ForeignKey(on_delete=models.CASCADE, related_name='equipment', to='explosionsschutz.area')),
                ('equipment_type', models.ForeignKey(on_delete=models.PROTECT, related_name='instances', to='explosionsschutz.equipmenttype')),
                ('zone', models.ForeignKey(on_delete=models.SET_NULL, null=True, blank=True, related_name='equipment', to='explosionsschutz.zonedefinition')),
            ],
            options={
                'db_table': 'ex_equipment',
            },
        ),
        migrations.CreateModel(
            name='Inspection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('inspection_type', models.CharField(max_length=20, default='periodic')),
                ('inspection_date', models.DateField()),
                ('inspector_name', models.CharField(max_length=200)),
                ('inspector_organization', models.CharField(max_length=200, blank=True, default='')),
                ('result', models.CharField(max_length=20, default='pending')),
                ('findings', models.TextField(blank=True, default='')),
                ('recommendations', models.TextField(blank=True, default='')),
                ('certificate_number', models.CharField(max_length=100, blank=True, default='')),
                ('document_id', models.UUIDField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('equipment', models.ForeignKey(on_delete=models.CASCADE, related_name='inspections', to='explosionsschutz.equipment')),
            ],
            options={
                'db_table': 'ex_inspection',
                'ordering': ['-inspection_date'],
            },
        ),
    ]
```

### Phase 7: VerificationDocument

```python
# explosionsschutz/migrations/0006_verification_document.py

class Migration(migrations.Migration):
    dependencies = [
        ('explosionsschutz', '0005_equipment_inspection'),
    ]

    operations = [
        migrations.CreateModel(
            name='VerificationDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=255)),
                ('document_type', models.CharField(max_length=20, default='other')),
                ('description', models.TextField(blank=True, default='')),
                ('file', models.FileField(upload_to='exschutz/docs/%Y/%m/', null=True, blank=True)),
                ('document_version_id', models.UUIDField(null=True, blank=True)),
                ('issued_at', models.DateField(null=True, blank=True)),
                ('issued_by', models.CharField(max_length=200, blank=True, default='')),
                ('valid_until', models.DateField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('concept', models.ForeignKey(on_delete=models.CASCADE, related_name='documents', to='explosionsschutz.explosionconcept')),
            ],
            options={
                'db_table': 'ex_verification_document',
                'ordering': ['-issued_at'],
            },
        ),
    ]
```

### Phase 8: Fixtures (Stammdaten)

```python
# explosionsschutz/migrations/0007_fixtures.py

from django.db import migrations

def load_reference_standards(apps, schema_editor):
    ReferenceStandard = apps.get_model('explosionsschutz', 'ReferenceStandard')
    
    standards = [
        {'code': 'TRGS 720', 'title': 'Gefährliche explosionsfähige Atmosphäre - Allgemeines', 'category': 'trgs'},
        {'code': 'TRGS 721', 'title': 'Gefährliche explosionsfähige Atmosphäre - Beurteilung der Explosionsgefährdung', 'category': 'trgs'},
        {'code': 'TRGS 722', 'title': 'Vermeidung oder Einschränkung gefährlicher explosionsfähiger Atmosphäre', 'category': 'trgs'},
        {'code': 'TRGS 723', 'title': 'Gefährliche explosionsfähige Gemische - Messung und Bewertung', 'category': 'trgs'},
        {'code': 'TRGS 724', 'title': 'Gefährliche explosionsfähige Atmosphäre - Eigenschutznachweis', 'category': 'trgs'},
        {'code': 'TRGS 725', 'title': 'Gefährliche explosionsfähige Atmosphäre - Mess-, Steuer- und Regeleinrichtungen', 'category': 'trgs'},
        {'code': 'IEC 60079-10-1', 'title': 'Explosive atmospheres - Classification of areas - Explosive gas atmospheres', 'category': 'iec'},
        {'code': 'IEC 60079-10-2', 'title': 'Explosive atmospheres - Classification of areas - Combustible dust atmospheres', 'category': 'iec'},
        {'code': 'EN 1127-1', 'title': 'Explosionsfähige Atmosphären - Explosionsschutz - Teil 1: Grundlagen und Methodik', 'category': 'en'},
    ]
    
    for s in standards:
        ReferenceStandard.objects.get_or_create(code=s['code'], defaults=s)

def load_measure_catalog(apps, schema_editor):
    MeasureCatalog = apps.get_model('explosionsschutz', 'MeasureCatalog')
    
    measures = [
        {'title': 'Inertisierung', 'default_type': 'primary', 'is_global': True},
        {'title': 'Ventilation/Lüftung', 'default_type': 'primary', 'is_global': True},
        {'title': 'Konzentrationsbegrenzung', 'default_type': 'primary', 'is_global': True},
        {'title': 'Erdung leitfähiger Teile', 'default_type': 'secondary', 'is_global': True},
        {'title': 'Vermeidung mechanischer Funken', 'default_type': 'secondary', 'is_global': True},
        {'title': 'Vermeidung heißer Oberflächen', 'default_type': 'secondary', 'is_global': True},
        {'title': 'Ex-geschützte Betriebsmittel', 'default_type': 'secondary', 'is_global': True},
        {'title': 'Explosionsdruckfeste Bauweise', 'default_type': 'constructive', 'is_global': True},
        {'title': 'Explosionsdruckentlastung', 'default_type': 'constructive', 'is_global': True},
        {'title': 'Explosionsunterdrückung', 'default_type': 'constructive', 'is_global': True},
    ]
    
    for m in measures:
        MeasureCatalog.objects.get_or_create(title=m['title'], defaults=m)

class Migration(migrations.Migration):
    dependencies = [
        ('explosionsschutz', '0006_verification_document'),
    ]

    operations = [
        migrations.RunPython(load_reference_standards, migrations.RunPython.noop),
        migrations.RunPython(load_measure_catalog, migrations.RunPython.noop),
    ]
```

---

## 3. Ausführung

```bash
# 1. Migrationen erstellen (falls noch nicht vorhanden)
python manage.py makemigrations explosionsschutz

# 2. Migrationen anwenden
python manage.py migrate explosionsschutz

# 3. Fixtures laden (falls separate Datei)
python manage.py loaddata explosionsschutz/fixtures/reference_standards.json

# 4. Admin registrieren
# → siehe explosionsschutz/admin.py
```

---

## 4. Validierung

```bash
# 1. Schema prüfen
python manage.py inspectdb --database=default | grep "^class Ex"

# 2. Modell-Checks
python manage.py check explosionsschutz

# 3. Tests ausführen
python manage.py test explosionsschutz
```

---

## 5. Rollback-Plan

```bash
# Bei Problemen: Migration rückgängig machen
python manage.py migrate explosionsschutz 0006  # Zu vorheriger Version
python manage.py migrate explosionsschutz zero  # Komplett zurücksetzen

# Tabellen manuell löschen (Notfall)
DROP TABLE ex_verification_document CASCADE;
DROP TABLE ex_inspection CASCADE;
DROP TABLE ex_equipment CASCADE;
DROP TABLE ex_protection_measure CASCADE;
DROP TABLE ex_zone_definition CASCADE;
DROP TABLE ex_concept CASCADE;
DROP TABLE ex_area CASCADE;
DROP TABLE ex_equipment_type CASCADE;
DROP TABLE ex_safety_function CASCADE;
DROP TABLE ex_measure_catalog CASCADE;
DROP TABLE ex_reference_standard CASCADE;
```

---

## 6. Checkliste

### Vor Deployment

- [ ] substances-Modul ist migriert
- [ ] Backup der Datenbank erstellt
- [ ] Migrationen auf Staging getestet
- [ ] Admin-Interface funktioniert
- [ ] Fixtures geladen

### Nach Deployment

- [ ] Stammdaten verifiziert (ReferenceStandard, MeasureCatalog)
- [ ] Test: Area anlegen
- [ ] Test: ExplosionConcept mit Substance-Verknüpfung
- [ ] Test: ZoneDefinition mit ReferenceStandard
- [ ] Test: ProtectionMeasure mit SafetyFunction
- [ ] Test: Equipment mit EquipmentType
- [ ] Test: Inspection erstellen
- [ ] Test: PDF-Export
