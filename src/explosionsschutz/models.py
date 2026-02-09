# src/explosionsschutz/models.py
"""
Explosionsschutz-Modul Models (v5 - Enterprise Edition)

Basiert auf ADR-001 v5.0:
- Hybrid Tenant-Isolation für Stammdaten
- Vollständiger Audit-Trail via Service Layer
- Strukturierte ATEX-Kennzeichnung mit EPL
- Zündquellen-Bewertung nach EN 1127-1
- Zone Extent mit Pydantic-Schema
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()


# =============================================================================
# HYBRID TENANT-ISOLATION INFRASTRUCTURE
# =============================================================================

class TenantScopedMasterDataManager(models.Manager):
    """
    Custom Manager für Stammdaten mit Hybrid-Tenant-Isolation.
    
    Liefert:
    - Globale Daten (tenant_id=NULL) UND
    - Tenant-spezifische Daten für den aktuellen Tenant
    """
    
    def for_tenant(self, tenant_id: uuid.UUID):
        """
        Gibt alle für einen Tenant sichtbaren Einträge zurück:
        - Globale Einträge (tenant_id IS NULL)
        - Eigene Einträge (tenant_id = tenant_id)
        """
        return self.filter(
            models.Q(tenant_id__isnull=True) | 
            models.Q(tenant_id=tenant_id)
        )
    
    def global_only(self):
        """Nur globale System-Einträge"""
        return self.filter(tenant_id__isnull=True, is_system=True)
    
    def tenant_only(self, tenant_id: uuid.UUID):
        """Nur tenant-spezifische Einträge"""
        return self.filter(tenant_id=tenant_id)


class TenantScopedMasterData(models.Model):
    """
    Abstrakte Basisklasse für Stammdaten mit Hybrid-Tenant-Isolation.
    
    tenant_id = NULL + is_system = True  → Globale System-Daten (nicht editierbar)
    tenant_id = UUID + is_system = False → Tenant-spezifische Daten
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant_id = models.UUIDField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="NULL = global/system, UUID = tenant-spezifisch"
    )
    
    is_system = models.BooleanField(
        default=False,
        help_text="System-Daten sind global und nicht editierbar"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantScopedMasterDataManager()
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Validierung: System-Daten müssen global sein"""
        if self.is_system and self.tenant_id is not None:
            raise ValidationError(
                "System-Daten (is_system=True) müssen global sein (tenant_id=NULL)"
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# =============================================================================
# REFERENZDATEN (Stammdaten)
# =============================================================================

class ReferenceStandard(TenantScopedMasterData):
    """
    Normative Referenzen (TRGS, IEC, EN, etc.)
    
    Beispiele (global):
    - TRGS 720: Gefährliche explosionsfähige Atmosphäre - Allgemeines
    - IEC 60079-10-1: Klassifizierung von Bereichen
    
    Beispiele (tenant-spezifisch):
    - Interne Richtlinie XY-001
    """
    
    class Category(models.TextChoices):
        TRGS = "TRGS", "Technische Regeln für Gefahrstoffe"
        IEC = "IEC", "IEC Normen"
        EN = "EN", "Europäische Normen"
        DIN = "DIN", "DIN Normen"
        VDSI = "VDSI", "VDSI Richtlinien"
        INTERNAL = "INTERNAL", "Interne Richtlinien"
    
    code = models.CharField(
        max_length=50,
        help_text="z.B. 'TRGS 720', 'IEC 60079-10-1'"
    )
    title = models.CharField(max_length=500)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TRGS
    )
    url = models.URLField(blank=True, default="", help_text="Link zur offiziellen Quelle")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = "ex_reference_standard"
        verbose_name = "Regelwerksreferenz"
        verbose_name_plural = "Regelwerksreferenzen"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_reference_standard_tenant_code"
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(tenant_id__isnull=True),
                name="uq_reference_standard_global_code"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "category"]),
        ]
    
    def __str__(self):
        return f"{self.code}: {self.title}"


class MeasureCatalog(TenantScopedMasterData):
    """
    Katalog wiederverwendbarer Schutzmaßnahmen-Vorlagen.
    
    Beispiele (global):
    - "Erdung aller leitfähigen Teile"
    - "Technische Lüftung nach DIN EN 60079-10-1"
    
    Beispiele (tenant-spezifisch):
    - "Interne Prozedur ABC-123"
    """
    
    class DefaultType(models.TextChoices):
        PRIMARY = "primary", "Primäre Maßnahme (Vermeidung)"
        SECONDARY = "secondary", "Sekundäre Maßnahme (Zündquellenvermeidung)"
        TERTIARY = "tertiary", "Tertiäre Maßnahme (Auswirkungsbegrenzung)"
        ORGANIZATIONAL = "organizational", "Organisatorische Maßnahme"
    
    code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Optionaler Kurzcode, z.B. 'M-ERD-001'"
    )
    title = models.CharField(max_length=300)
    default_type = models.CharField(
        max_length=20,
        choices=DefaultType.choices,
        default=DefaultType.SECONDARY
    )
    description_template = models.TextField(
        blank=True,
        default="",
        help_text="Vorlage für Beschreibung, kann Platzhalter enthalten"
    )
    reference_standards = models.ManyToManyField(
        ReferenceStandard,
        blank=True,
        related_name="measure_catalog_entries"
    )
    
    class Meta:
        db_table = "ex_measure_catalog"
        verbose_name = "Maßnahmenkatalog"
        verbose_name_plural = "Maßnahmenkataloge"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "title"],
                name="uq_measure_catalog_tenant_title"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "default_type"]),
        ]
    
    def __str__(self):
        prefix = f"[{self.code}] " if self.code else ""
        return f"{prefix}{self.title}"


class SafetyFunction(TenantScopedMasterData):
    """
    MSR-Sicherheitsfunktion nach IEC 62061 / ISO 13849.
    
    Wird verwendet für komplexe Schutzmaßnahmen mit:
    - Performance Level (PLr) nach ISO 13849
    - Safety Integrity Level (SIL) nach IEC 62061
    - Überwachungsanforderungen
    """
    
    class PerformanceLevel(models.TextChoices):
        PL_A = "a", "PL a"
        PL_B = "b", "PL b"
        PL_C = "c", "PL c"
        PL_D = "d", "PL d"
        PL_E = "e", "PL e"
    
    class SILLevel(models.TextChoices):
        SIL_1 = "1", "SIL 1"
        SIL_2 = "2", "SIL 2"
        SIL_3 = "3", "SIL 3"
    
    class MonitoringMethod(models.TextChoices):
        CONTINUOUS = "continuous", "Kontinuierlich"
        PERIODIC = "periodic", "Periodisch"
        DEMAND = "demand", "Bei Anforderung"
    
    name = models.CharField(
        max_length=100,
        help_text="Eindeutiger Name, z.B. 'GW-001' für Gaswarnanlage 001"
    )
    description = models.TextField(blank=True, default="")
    
    performance_level = models.CharField(
        max_length=5,
        choices=PerformanceLevel.choices,
        blank=True,
        default="",
        help_text="Required Performance Level nach ISO 13849"
    )
    sil_level = models.CharField(
        max_length=5,
        choices=SILLevel.choices,
        blank=True,
        default="",
        help_text="Safety Integrity Level nach IEC 62061"
    )
    monitoring_method = models.CharField(
        max_length=20,
        choices=MonitoringMethod.choices,
        default=MonitoringMethod.CONTINUOUS
    )
    
    # Technische Details
    response_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Ansprechzeit in Millisekunden"
    )
    proof_test_interval_months = models.IntegerField(
        null=True,
        blank=True,
        help_text="Proof-Test-Intervall in Monaten"
    )
    
    reference_standards = models.ManyToManyField(
        ReferenceStandard,
        blank=True,
        related_name="safety_functions"
    )
    
    class Meta:
        db_table = "ex_safety_function"
        verbose_name = "Sicherheitsfunktion"
        verbose_name_plural = "Sicherheitsfunktionen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_safety_function_tenant_name"
            ),
        ]
    
    def __str__(self):
        levels = []
        if self.performance_level:
            levels.append(f"PL {self.performance_level}")
        if self.sil_level:
            levels.append(f"SIL {self.sil_level}")
        level_str = " / ".join(levels) if levels else "n/a"
        return f"{self.name} ({level_str})"


# =============================================================================
# ANLAGENSTRUKTUR
# =============================================================================

class Area(models.Model):
    """Betriebsbereich / Anlage innerhalb eines Standorts"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    site_id = models.UUIDField(db_index=True, help_text="FK zu tenancy.Site")
    
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=50, 
        blank=True, 
        default="",
        help_text="Anlagenkennzeichen (z.B. 'E2-50.01')"
    )
    description = models.TextField(blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "ex_area"
        verbose_name = "Betriebsbereich"
        verbose_name_plural = "Betriebsbereiche"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site_id", "code"],
                name="uq_area_code_per_site",
                condition=models.Q(code__gt="")
            )
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name
    
    @property
    def has_explosion_hazard(self) -> bool:
        """Prüft ob Ex-relevante Konzepte im Bereich existieren"""
        return self.explosion_concepts.filter(
            status__in=["approved", "in_review"]
        ).exists()


# =============================================================================
# EXPLOSIONSSCHUTZKONZEPT
# =============================================================================

class ExplosionConcept(models.Model):
    """Explosionsschutzkonzept nach TRGS 720ff"""
    
    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        IN_REVIEW = "in_review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        ARCHIVED = "archived", "Archiviert"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    # Beziehungen
    area = models.ForeignKey(
        Area, 
        on_delete=models.CASCADE,
        related_name="explosion_concepts"
    )
    assessment_id = models.UUIDField(
        null=True, 
        blank=True,
        db_index=True,
        help_text="FK zu risk.Assessment (optional)"
    )
    substance_id = models.UUIDField(
        db_index=True,
        help_text="FK zu substances.Substance (UUID)"
    )
    substance_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Cached Stoffname für Anzeige"
    )
    
    # Metadaten
    title = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Validierung
    is_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_concepts"
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_concepts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "ex_concept"
        verbose_name = "Explosionsschutzkonzept"
        verbose_name_plural = "Explosionsschutzkonzepte"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
        ]
    
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    @property
    def sds_data(self) -> dict:
        """Ex-relevante Daten aus aktuellem SDS (read-only)"""
        # Integration mit substances-Modul erfolgt via Service Layer
        return {
            "substance_id": str(self.substance_id),
            "substance_name": self.substance_name,
        }
    
    @property
    def completion_percentage(self) -> int:
        """Fortschritt des Konzepts (für UI)"""
        total = 4
        completed = 0
        
        if self.zones.exists():
            completed += 1
        if self.measures.filter(category="primary").exists():
            completed += 1
        if self.measures.filter(category="secondary").exists():
            completed += 1
        if self.is_validated:
            completed += 1
        
        return int((completed / total) * 100)


# =============================================================================
# ZONENEINTEILUNG
# =============================================================================

class ZoneDefinition(models.Model):
    """Zoneneinteilung nach ATEX"""
    
    class ZoneType(models.TextChoices):
        ZONE_0 = "0", "Zone 0 (Gas/Dampf, ständig)"
        ZONE_1 = "1", "Zone 1 (Gas/Dampf, gelegentlich)"
        ZONE_2 = "2", "Zone 2 (Gas/Dampf, selten)"
        ZONE_20 = "20", "Zone 20 (Staub, ständig)"
        ZONE_21 = "21", "Zone 21 (Staub, gelegentlich)"
        ZONE_22 = "22", "Zone 22 (Staub, selten)"
        NON_EX = "non_ex", "Nicht Ex-Bereich"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    concept = models.ForeignKey(
        ExplosionConcept,
        on_delete=models.CASCADE,
        related_name="zones"
    )
    
    zone_type = models.CharField(
        max_length=10,
        choices=ZoneType.choices,
        default=ZoneType.ZONE_2
    )
    name = models.CharField(
        max_length=200,
        help_text="Bezeichnung der Zone (z.B. 'Abfüllbereich Tank 1')"
    )
    description = models.TextField(blank=True, default="")
    justification = models.TextField(
        blank=True,
        default="",
        help_text="Begründung für Zoneneinteilung"
    )
    
    # Ausdehnung (GeoJSON-kompatibel)
    extent = models.JSONField(
        null=True,
        blank=True,
        help_text="Geometrie als GeoJSON (Point, Polygon, etc.)"
    )
    extent_horizontal_m = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Horizontale Ausdehnung in Metern"
    )
    extent_vertical_m = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Vertikale Ausdehnung in Metern"
    )
    
    # Regelwerksreferenz
    reference_standard = models.ForeignKey(
        ReferenceStandard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zone_definitions"
    )
    reference_section = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Abschnitt im Regelwerk (z.B. '4.2.1')"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "ex_zone_definition"
        verbose_name = "Zonendefinition"
        verbose_name_plural = "Zonendefinitionen"
    
    def __str__(self):
        return f"{self.get_zone_type_display()} - {self.name}"
    
    @property
    def required_equipment_category(self) -> str:
        """Erforderliche Gerätekategorie für diese Zone"""
        mapping = {
            "0": "1G", "1": "2G", "2": "3G",
            "20": "1D", "21": "2D", "22": "3D",
            "non_ex": "non_ex"
        }
        return mapping.get(self.zone_type, "unknown")


# =============================================================================
# SCHUTZMASSNAHMEN
# =============================================================================

class ProtectionMeasure(models.Model):
    """Schutzmaßnahme (primär, sekundär, tertiär, organisatorisch)"""
    
    class Category(models.TextChoices):
        PRIMARY = "primary", "Primäre Maßnahme (Vermeidung)"
        SECONDARY = "secondary", "Sekundäre Maßnahme (Zündquellenvermeidung)"
        TERTIARY = "tertiary", "Tertiäre Maßnahme (Auswirkungsbegrenzung)"
        ORGANIZATIONAL = "organizational", "Organisatorische Maßnahme"
    
    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        DONE = "done", "Umgesetzt"
        VERIFIED = "verified", "Verifiziert"
        OBSOLETE = "obsolete", "Obsolet"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    concept = models.ForeignKey(
        ExplosionConcept,
        on_delete=models.CASCADE,
        related_name="measures"
    )
    
    # Klassifikation
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SECONDARY
    )
    catalog_reference = models.ForeignKey(
        MeasureCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Vorlage aus Maßnahmenkatalog"
    )
    
    # Inhalt
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    
    # MSR-Bewertung (optional)
    safety_function = models.ForeignKey(
        SafetyFunction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="measures"
    )
    
    # Status & Verantwortung
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    responsible_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_measures"
    )
    due_date = models.DateField(null=True, blank=True)
    
    # Verifizierung
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_measures"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, default="")
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "ex_protection_measure"
        verbose_name = "Schutzmaßnahme"
        verbose_name_plural = "Schutzmaßnahmen"
        ordering = ["category", "title"]
    
    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
    
    @property
    def is_safety_device(self) -> bool:
        """Prüft ob Maßnahme eine MSR-Sicherheitsfunktion ist"""
        return self.safety_function is not None


# =============================================================================
# BETRIEBSMITTEL
# =============================================================================

class EquipmentType(TenantScopedMasterData):
    """
    Stammdaten für Betriebsmittel-Typen mit strukturierter ATEX-Kennzeichnung.
    
    ATEX-Kennzeichnung Struktur:
    ╔══════════════════════════════════════════════════════════════════╗
    ║  II 2G Ex d IIB T4 Gb                                            ║
    ║  ├─ Gruppe (I=Bergbau, II=Industrie)                             ║
    ║  │  ├─ Kategorie (1/2/3 + G=Gas oder D=Staub)                    ║
    ║  │  │     ├─ Schutzart (Ex d, Ex e, Ex i, ...)                   ║
    ║  │  │     │       ├─ Explosionsgruppe (IIA/IIB/IIC)              ║
    ║  │  │     │       │      ├─ Temperaturklasse (T1-T6)             ║
    ║  │  │     │       │      │    └─ EPL (Ga/Gb/Gc oder Da/Db/Dc)    ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    
    class AtexGroup(models.TextChoices):
        GROUP_I = "I", "Gruppe I (Bergbau)"
        GROUP_II = "II", "Gruppe II (Industrie)"
    
    class AtexCategory(models.TextChoices):
        CAT_1G = "1G", "Kategorie 1G (Zone 0)"
        CAT_2G = "2G", "Kategorie 2G (Zone 0, 1)"
        CAT_3G = "3G", "Kategorie 3G (Zone 0, 1, 2)"
        CAT_1D = "1D", "Kategorie 1D (Zone 20)"
        CAT_2D = "2D", "Kategorie 2D (Zone 20, 21)"
        CAT_3D = "3D", "Kategorie 3D (Zone 20, 21, 22)"
    
    class ProtectionType(models.TextChoices):
        EX_D = "Ex d", "Druckfeste Kapselung"
        EX_E = "Ex e", "Erhöhte Sicherheit"
        EX_I = "Ex i", "Eigensicherheit"
        EX_P = "Ex p", "Überdruckkapselung"
        EX_M = "Ex m", "Vergusskapselung"
        EX_O = "Ex o", "Ölkapselung"
        EX_Q = "Ex q", "Sandkapselung"
        EX_N = "Ex n", "Nicht-funkend"
        EX_T = "Ex t", "Schutz durch Gehäuse (Staub)"
    
    class ExplosionGroup(models.TextChoices):
        IIA = "IIA", "IIA (Propan)"
        IIB = "IIB", "IIB (Ethylen)"
        IIC = "IIC", "IIC (Wasserstoff, Acetylen)"
        IIIA = "IIIA", "IIIA (brennbare Flusen)"
        IIIB = "IIIB", "IIIB (nicht leitfähiger Staub)"
        IIIC = "IIIC", "IIIC (leitfähiger Staub)"
    
    class TemperatureClass(models.TextChoices):
        T1 = "T1", "T1 (≤450°C)"
        T2 = "T2", "T2 (≤300°C)"
        T3 = "T3", "T3 (≤200°C)"
        T4 = "T4", "T4 (≤135°C)"
        T5 = "T5", "T5 (≤100°C)"
        T6 = "T6", "T6 (≤85°C)"
    
    class EPL(models.TextChoices):
        """Equipment Protection Level"""
        GA = "Ga", "Ga (sehr hohes Schutzniveau)"
        GB = "Gb", "Gb (hohes Schutzniveau)"
        GC = "Gc", "Gc (erhöhtes Schutzniveau)"
        DA = "Da", "Da (sehr hohes Schutzniveau - Staub)"
        DB = "Db", "Db (hohes Schutzniveau - Staub)"
        DC = "Dc", "Dc (erhöhtes Schutzniveau - Staub)"
    
    # Hersteller & Modell
    manufacturer = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    
    # Strukturierte ATEX-Kennzeichnung
    atex_group = models.CharField(
        max_length=5,
        choices=AtexGroup.choices,
        default=AtexGroup.GROUP_II
    )
    atex_category = models.CharField(
        max_length=5,
        choices=AtexCategory.choices,
        blank=True,
        default=""
    )
    protection_type = models.CharField(
        max_length=10,
        choices=ProtectionType.choices,
        blank=True,
        default=""
    )
    explosion_group = models.CharField(
        max_length=10,
        choices=ExplosionGroup.choices,
        blank=True,
        default=""
    )
    temperature_class = models.CharField(
        max_length=5,
        choices=TemperatureClass.choices,
        blank=True,
        default=""
    )
    epl = models.CharField(
        max_length=5,
        choices=EPL.choices,
        blank=True,
        default="",
        help_text="Equipment Protection Level"
    )
    
    # Zusätzliche technische Daten
    ip_rating = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="z.B. IP65, IP66"
    )
    ambient_temp_min = models.IntegerField(
        null=True,
        blank=True,
        help_text="Min. Umgebungstemperatur in °C"
    )
    ambient_temp_max = models.IntegerField(
        null=True,
        blank=True,
        help_text="Max. Umgebungstemperatur in °C"
    )
    
    # Dokumentation
    datasheet_url = models.URLField(blank=True, default="")
    certificate_number = models.CharField(max_length=100, blank=True, default="")
    notified_body = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="z.B. 'PTB', 'DEKRA', 'TÜV'"
    )
    
    # Prüfintervall
    default_inspection_interval_months = models.PositiveIntegerField(
        default=12,
        help_text="Standard-Prüfintervall in Monaten"
    )
    
    class Meta:
        db_table = "ex_equipment_type"
        verbose_name = "Betriebsmitteltyp"
        verbose_name_plural = "Betriebsmitteltypen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "manufacturer", "model"],
                name="uq_equipment_type_tenant_mfr_model"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "atex_category"]),
            models.Index(fields=["tenant_id", "manufacturer"]),
        ]
    
    def __str__(self):
        return f"{self.manufacturer} {self.model} ({self.full_atex_marking})"
    
    @property
    def full_atex_marking(self) -> str:
        """Vollständige ATEX-Kennzeichnung aus Einzelfeldern"""
        parts = [self.atex_group]
        if self.atex_category:
            parts.append(self.atex_category)
        if self.protection_type:
            parts.append(self.protection_type)
        if self.explosion_group:
            parts.append(self.explosion_group)
        if self.temperature_class:
            parts.append(self.temperature_class)
        if self.epl:
            parts.append(self.epl)
        return " ".join(parts) if len(parts) > 1 else "N/A"
    
    @property
    def allowed_zones(self) -> list:
        """Liste der Zonen, in denen dieses Gerät eingesetzt werden darf"""
        CATEGORY_ZONES = {
            "1G": ["0", "1", "2"],
            "2G": ["1", "2"],
            "3G": ["2"],
            "1D": ["20", "21", "22"],
            "2D": ["21", "22"],
            "3D": ["22"],
        }
        return CATEGORY_ZONES.get(self.atex_category, [])


class Equipment(models.Model):
    """Konkretes Ex-geschütztes Betriebsmittel"""
    
    class Status(models.TextChoices):
        ACTIVE = "active", "In Betrieb"
        INACTIVE = "inactive", "Außer Betrieb"
        MAINTENANCE = "maintenance", "In Wartung"
        DECOMMISSIONED = "decommissioned", "Stillgelegt"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    # Beziehungen
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.PROTECT,
        related_name="instances"
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="equipment"
    )
    zone = models.ForeignKey(
        ZoneDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment"
    )
    
    # Identifikation
    serial_number = models.CharField(max_length=100, blank=True, default="")
    asset_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Interne Anlagennummer"
    )
    location_detail = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Genauer Standort (z.B. 'Halle 3, Ebene 2')"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    installation_date = models.DateField(null=True, blank=True)
    
    # Prüfungen
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_date = models.DateField(null=True, blank=True)
    inspection_interval_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Überschreibt Standard-Intervall des Typs"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "ex_equipment"
        verbose_name = "Betriebsmittel"
        verbose_name_plural = "Betriebsmittel"
        indexes = [
            models.Index(fields=["tenant_id", "next_inspection_date"]),
        ]
    
    def __str__(self):
        return f"{self.equipment_type} ({self.asset_number or self.serial_number or 'N/A'})"
    
    @property
    def is_inspection_due(self) -> bool:
        """Prüft ob Inspektion fällig"""
        from django.utils import timezone
        if not self.next_inspection_date:
            return False
        return self.next_inspection_date <= timezone.now().date()
    
    @property
    def is_suitable_for_zone(self) -> bool:
        """Prüft ob Gerätekategorie zur Zone passt"""
        if not self.zone:
            return True
        
        required = self.zone.required_equipment_category
        actual = self.equipment_type.atex_category
        
        if required == "non_ex":
            return True
        if not actual:
            return False
        
        # Höhere Kategorie ist immer zulässig
        category_order = {"1G": 1, "2G": 2, "3G": 3, "1D": 1, "2D": 2, "3D": 3}
        return category_order.get(actual, 99) <= category_order.get(required, 0)


# =============================================================================
# PRÜFUNGEN
# =============================================================================

class Inspection(models.Model):
    """Prüfung eines Betriebsmittels nach BetrSichV"""
    
    class InspectionType(models.TextChoices):
        INITIAL = "initial", "Erstprüfung"
        PERIODIC = "periodic", "Wiederkehrende Prüfung"
        SPECIAL = "special", "Sonderprüfung"
        REPAIR = "repair", "Prüfung nach Instandsetzung"
    
    class Result(models.TextChoices):
        PASSED = "passed", "Bestanden"
        PASSED_WITH_NOTES = "passed_notes", "Bestanden mit Hinweisen"
        FAILED = "failed", "Nicht bestanden"
        PENDING = "pending", "Ausstehend"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="inspections"
    )
    
    inspection_type = models.CharField(
        max_length=20,
        choices=InspectionType.choices,
        default=InspectionType.PERIODIC
    )
    inspection_date = models.DateField()
    inspector_name = models.CharField(max_length=200)
    inspector_organization = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="z.B. ZÜS, befähigte Person"
    )
    
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.PENDING
    )
    findings = models.TextField(blank=True, default="")
    recommendations = models.TextField(blank=True, default="")
    
    # Dokumente
    certificate_number = models.CharField(max_length=100, blank=True, default="")
    document_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="FK zu documents.Document"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = "ex_inspection"
        verbose_name = "Prüfung"
        verbose_name_plural = "Prüfungen"
        ordering = ["-inspection_date"]
    
    def __str__(self):
        return f"{self.get_inspection_type_display()} - {self.equipment} ({self.inspection_date})"
    
    # NOTE: Equipment inspection date updates are handled in
    # explosionsschutz.services.create_inspection() to keep
    # the model free of hidden side-effects (F-07).


# =============================================================================
# NACHWEISDOKUMENTE
# =============================================================================

# =============================================================================
# ZÜNDQUELLEN-BEWERTUNG (EN 1127-1)
# =============================================================================

class IgnitionSource(models.TextChoices):
    """13 Zündquellen nach EN 1127-1"""
    S1_HOT_SURFACES = "S1", "Heiße Oberflächen"
    S2_FLAMES = "S2", "Flammen und heiße Gase"
    S3_MECHANICAL_SPARKS = "S3", "Mechanisch erzeugte Funken"
    S4_ELECTRICAL = "S4", "Elektrische Anlagen"
    S5_STRAY_CURRENTS = "S5", "Kathodischer Korrosionsschutz / Streuströme"
    S6_STATIC = "S6", "Statische Elektrizität"
    S7_LIGHTNING = "S7", "Blitzschlag"
    S8_ELECTROMAGNETIC = "S8", "Elektromagnetische Felder (HF)"
    S9_OPTICAL = "S9", "Optische Strahlung"
    S10_IONIZING = "S10", "Ionisierende Strahlung"
    S11_ULTRASOUND = "S11", "Ultraschall"
    S12_ADIABATIC = "S12", "Adiabatische Kompression / Stoßwellen"
    S13_EXOTHERMIC = "S13", "Exotherme Reaktionen"


class ZoneIgnitionSourceAssessment(models.Model):
    """
    Bewertung der 13 Zündquellen pro Zone nach EN 1127-1.
    
    Für jede Zone müssen alle 13 Zündquellen bewertet werden:
    - is_present: Ist die Zündquelle vorhanden?
    - is_effective: Kann sie eine Zündung verursachen?
    - mitigation: Welche Maßnahmen werden ergriffen?
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    zone = models.ForeignKey(
        ZoneDefinition,
        on_delete=models.CASCADE,
        related_name="ignition_assessments"
    )
    ignition_source = models.CharField(
        max_length=10,
        choices=IgnitionSource.choices
    )
    
    is_present = models.BooleanField(
        default=False,
        help_text="Ist diese Zündquelle im Bereich vorhanden?"
    )
    is_effective = models.BooleanField(
        default=False,
        help_text="Kann diese Zündquelle wirksam werden (Energie ausreichend)?"
    )
    mitigation = models.TextField(
        blank=True,
        default="",
        help_text="Beschreibung der Schutzmaßnahmen gegen diese Zündquelle"
    )
    
    assessed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "ex_zone_ignition_assessment"
        verbose_name = "Zündquellen-Bewertung"
        verbose_name_plural = "Zündquellen-Bewertungen"
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "ignition_source"],
                name="uq_zone_ignition_source"
            ),
        ]
    
    def __str__(self):
        status = "wirksam" if self.is_effective else (
            "vorhanden" if self.is_present else "nicht vorhanden"
        )
        return f"{self.zone.name} - {self.get_ignition_source_display()}: {status}"


# =============================================================================
# NACHWEISDOKUMENTE
# =============================================================================

class VerificationDocument(models.Model):
    """Nachweis- und Prüfdokumente zum Ex-Konzept"""
    
    class DocumentType(models.TextChoices):
        CERTIFICATE = "certificate", "Prüfbescheinigung"
        REPORT = "report", "Prüfbericht"
        MSR_TEST = "msr_test", "MSR-Prüfprotokoll"
        PHOTO = "photo", "Foto/Dokumentation"
        DRAWING = "drawing", "Zeichnung/Plan"
        APPROVAL = "approval", "Genehmigung"
        OTHER = "other", "Sonstige"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    concept = models.ForeignKey(
        ExplosionConcept,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    
    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    description = models.TextField(blank=True, default="")
    
    # Datei
    file = models.FileField(
        upload_to="exschutz/docs/%Y/%m/",
        null=True,
        blank=True
    )
    document_version_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="FK zu documents.DocumentVersion"
    )
    
    # Metadaten
    issued_at = models.DateField(null=True, blank=True)
    issued_by = models.CharField(max_length=200, blank=True, default="")
    valid_until = models.DateField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = "ex_verification_document"
        verbose_name = "Nachweisdokument"
        verbose_name_plural = "Nachweisdokumente"
        ordering = ["-issued_at"]
    
    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
