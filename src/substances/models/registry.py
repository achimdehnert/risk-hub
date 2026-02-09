"""Hazardous substance registry models (TRGS 510, Seveso III)."""

import uuid

from django.db import models
from django.utils import timezone


class StorageClass(models.TextChoices):
    """TRGS 510 Lagerklassen."""

    LGK_1 = "1", "LGK 1 – Explosive Stoffe"
    LGK_2A = "2A", "LGK 2A – Verdichtete Gase (brennbar)"
    LGK_2B = "2B", "LGK 2B – Verdichtete Gase (nicht brennbar)"
    LGK_3 = "3", "LGK 3 – Entzündbare Flüssigkeiten"
    LGK_4_1 = "4.1", "LGK 4.1 – Entzündbare feste Stoffe"
    LGK_4_2 = "4.2", "LGK 4.2 – Selbstentzündliche Stoffe"
    LGK_4_3 = "4.3", "LGK 4.3 – Stoffe mit Wasserreaktion"
    LGK_5_1 = "5.1", "LGK 5.1 – Oxidierende Stoffe"
    LGK_5_2 = "5.2", "LGK 5.2 – Organische Peroxide"
    LGK_6_1 = "6.1", "LGK 6.1 – Giftige Stoffe"
    LGK_6_2 = "6.2", "LGK 6.2 – Ansteckungsgefährliche Stoffe"
    LGK_7 = "7", "LGK 7 – Radioaktive Stoffe"
    LGK_8 = "8", "LGK 8 – Ätzende Stoffe"
    LGK_10 = "10", "LGK 10 – Brennbare Flüssigkeiten (nicht LGK 3)"
    LGK_11 = "11", "LGK 11 – Brennbare Feststoffe"
    LGK_12 = "12", "LGK 12 – Nicht brennbare Flüssigkeiten"
    LGK_13 = "13", "LGK 13 – Nicht brennbare Feststoffe"


class SevesoCategory(models.TextChoices):
    """Seveso III Kategorien (12. BImSchV)."""

    NONE = "none", "Nicht Seveso-relevant"
    LOWER = "lower", "Untere Klasse (Grundpflichten)"
    UPPER = "upper", "Obere Klasse (Erweiterte Pflichten)"


class LocationSubstanceEntry(models.Model):
    """
    A substance stored at a specific location.

    Tracks quantities, storage classes, and Seveso relevance
    per tenant location for regulatory compliance.
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(db_index=True)

    # Location reference (to explosionsschutz.Area)
    area_id = models.UUIDField(
        db_index=True,
        help_text="Standort/Bereich (Area-ID)",
    )

    # Substance reference
    substance_id = models.UUIDField(
        db_index=True,
        help_text="Gefahrstoff (Substance-ID)",
    )
    substance_name = models.CharField(
        max_length=300,
        help_text="Denormalisierter Stoffname für schnelle Anzeige",
    )
    cas_number = models.CharField(
        max_length=30, blank=True, default="",
    )

    # Quantities
    max_quantity_kg = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Maximale Lagermenge in kg",
    )
    current_quantity_kg = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Aktuelle Lagermenge in kg",
    )

    # TRGS 510 classification
    storage_class = models.CharField(
        max_length=5,
        choices=StorageClass.choices,
        blank=True,
        default="",
        db_index=True,
        help_text="Lagerklasse nach TRGS 510",
    )

    # Seveso III
    seveso_category = models.CharField(
        max_length=10,
        choices=SevesoCategory.choices,
        default=SevesoCategory.NONE,
        db_index=True,
    )
    seveso_threshold_lower_t = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Untere Mengenschwelle (Tonnen)",
    )
    seveso_threshold_upper_t = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Obere Mengenschwelle (Tonnen)",
    )

    # GHS / H-Statements
    h_statements = models.TextField(
        blank=True, default="",
        help_text="H-Sätze (kommagetrennt)",
    )
    ghs_pictograms = models.CharField(
        max_length=200, blank=True, default="",
        help_text="GHS-Piktogramme (z.B. GHS02, GHS06)",
    )

    # Metadata
    notes = models.TextField(blank=True, default="")
    last_inventory_date = models.DateField(
        null=True, blank=True,
        help_text="Letzte Bestandserfassung",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "substances_location_entry"
        ordering = ["substance_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "area_id", "substance_id"],
                name="uq_location_substance",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "area_id"],
                name="loc_substance_area_idx",
            ),
            models.Index(
                fields=["tenant_id", "seveso_category"],
                name="loc_substance_seveso_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.substance_name} @ Area {self.area_id}"
            f" ({self.current_quantity_kg} kg)"
        )

    @property
    def seveso_utilization_pct(self) -> float | None:
        """Calculate Seveso threshold utilization."""
        threshold = self.seveso_threshold_lower_t
        if not threshold or threshold == 0:
            return None
        qty_t = float(self.current_quantity_kg) / 1000
        return round(qty_t / float(threshold) * 100, 1)
