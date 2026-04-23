# src/explosionsschutz/models/substance_ref.py
"""
Mehrstoff-Bewertung: ConceptSubstanceReference und SubstanceContainer.

ConceptSubstanceReference: Ersetzt ExplosionConcept.substance_id (UUID).
Bindet SDS-Revisionen für Compliance-Snapshot (ADR-012 Impact-Event).

SubstanceContainer: Strukturierte Gebinde-Erfassung (TRGS 510 Schwellen).

ADR-044 Phase 2B.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class SubstanceRole(models.TextChoices):
    PRIMARY = "PRIMARY", "Maßgeblicher Stoff für die Beurteilung"
    SECONDARY = "SECONDARY", "Weiterer Stoff"
    COMPARISON = "COMPARISON", "Vergleichsstoff"


class ConceptSubstanceReference(models.Model):
    """
    Verknüpft ein ExplosionConcept mit einer exakten SDS-Revision.

    Compliance-kritisch: Bindet den Stoff an die Revision zum Erstellungszeitpunkt.
    Ändert sich das SDB später, ändert sich NICHT diese Bewertung. Stattdessen
    löst das ADR-012 Impact-Event (SAFETY_CRITICAL bei H-Code-Änderung) einen
    REVIEW_REQUIRED-Status am Konzept aus.

    Migrationshinweis (ADR-044 Phase 2):
    Bestehende ExplosionConcept.substance_id wird als PRIMARY-Referenz
    mit der aktuellen SDS-Revision angelegt. ExplosionConcept.substance_id
    wird danach deprecated und nach 6 Monaten entfernt.
    """

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="substance_references",
    )
    sds_revision = models.ForeignKey(
        "global_sds.GlobalSdsRevision",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=(
            "Exakte SDS-Revision zum Erstellungszeitpunkt (Snapshot-Binding, ADR-012). "
            "Darf NULL sein während der Datenmigration (substance_id → ConceptSubstanceReference). "
            "Nach Phase 4 Deprecation: null=False erzwingen."
        ),
    )
    role = models.CharField(
        max_length=15,
        choices=SubstanceRole.choices,
    )
    release_rate_text = models.TextField(
        blank=True,
        help_text="Freitext-Angabe zur Freisetzungsrate für diese Substanz in diesem Konzept",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_concept_substance_reference"
        verbose_name = "Konzept-Stoff-Referenz"
        verbose_name_plural = "Konzept-Stoff-Referenzen"
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "sds_revision", "role"],
                name="uniq_sds_role_per_concept",
            ),
        ]

    def __str__(self) -> str:
        concept_title = self.concept.title if self.concept_id else "?"
        return f"{self.get_role_display()} — {concept_title}"


class ContainerType(models.TextChoices):
    DRUM = "DRUM", "Fass"
    CANISTER = "CAN", "Kanister"
    IBC = "IBC", "Intermediate Bulk Container"
    PRESSURE_CYLINDER = "PRESS", "Druckgasflasche"
    TANK = "TANK", "Ortsfester Tank"
    SPRAY_CAN = "SPRAY", "Spraydose"
    CARTRIDGE = "CART", "Kartusche"


class SubstanceContainer(models.Model):
    """
    Strukturierte Gebinde-Erfassung für TRGS 510 Schwellen-Prüfung.

    Verbindet Konzept + Stoff-Referenz mit physischen Gebinden.
    Ermöglicht automatische TRGS 510 Mengenschwellen-Prüfung.
    """

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="containers",
    )
    substance_reference = models.ForeignKey(
        ConceptSubstanceReference,
        on_delete=models.CASCADE,
        related_name="containers",
    )
    container_type = models.CharField(
        max_length=10,
        choices=ContainerType.choices,
    )
    volume_liters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Nennvolumen in Litern",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Anzahl Gebinde dieses Typs",
    )
    h_category = models.CharField(
        max_length=5,
        blank=True,
        help_text="Maßgebliche H-Kategorie für TRGS 510, z.B. H224, H225, H226",
    )
    total_mass_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gesamtmasse (Füllgewicht) in kg (quantity × Einzelmasse)",
    )
    protective_cap_valve = models.BooleanField(
        default=False,
        help_text="Druckgas: Schutzkappe / Ventilschutz vorhanden (DIN EN ISO 11117)",
    )
    passive_storage = models.BooleanField(
        default=True,
        help_text="Passive Lagerung ohne Entnahme im laufenden Betrieb",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_substance_container"
        verbose_name = "Stoff-Gebinde"
        verbose_name_plural = "Stoff-Gebinde"

    def __str__(self) -> str:
        return f"{self.get_container_type_display()} × {self.quantity}"
