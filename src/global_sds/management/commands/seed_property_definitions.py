"""Seed SDS Property Definitions (ADR-017 §5.3, idempotent)."""

from django.core.management.base import BaseCommand

from global_sds.models import SdsPropertyDefinition

DEFINITIONS = [
    # SDS Abschnitt 9 — Physikalisch-chemische Eigenschaften
    {
        "key": "flash_point",
        "label_de": "Flammpunkt",
        "label_en": "Flash Point",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "°C",
        "is_promoted": True,
        "promoted_column_name": "flash_point_c",
        "sort_order": 10,
    },
    {
        "key": "ignition_temperature",
        "label_de": "Zündtemperatur",
        "label_en": "Ignition Temperature",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "°C",
        "is_promoted": True,
        "promoted_column_name": "ignition_temperature_c",
        "sort_order": 20,
    },
    {
        "key": "lower_explosion_limit",
        "label_de": "Untere Explosionsgrenze (UEG)",
        "label_en": "Lower Explosion Limit (LEL)",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "Vol.%",
        "is_promoted": True,
        "promoted_column_name": "lower_explosion_limit",
        "sort_order": 30,
    },
    {
        "key": "upper_explosion_limit",
        "label_de": "Obere Explosionsgrenze (OEG)",
        "label_en": "Upper Explosion Limit (UEL)",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "Vol.%",
        "is_promoted": True,
        "promoted_column_name": "upper_explosion_limit",
        "sort_order": 40,
    },
    {
        "key": "vapour_pressure",
        "label_de": "Dampfdruck",
        "label_en": "Vapour Pressure",
        "sds_section": "9.1",
        "value_type": "NUMERIC_AT_TEMP",
        "unit": "hPa",
        "sort_order": 50,
    },
    {
        "key": "density",
        "label_de": "Dichte",
        "label_en": "Density",
        "sds_section": "9.1",
        "value_type": "NUMERIC_AT_TEMP",
        "unit": "g/cm³",
        "sort_order": 60,
    },
    {
        "key": "boiling_point",
        "label_de": "Siedepunkt/-bereich",
        "label_en": "Boiling Point/Range",
        "sds_section": "9.1",
        "value_type": "NUMERIC_RANGE",
        "unit": "°C",
        "sort_order": 70,
    },
    {
        "key": "melting_point",
        "label_de": "Schmelzpunkt/-bereich",
        "label_en": "Melting Point/Range",
        "sds_section": "9.1",
        "value_type": "NUMERIC_RANGE",
        "unit": "°C",
        "sort_order": 80,
    },
    {
        "key": "ph_value",
        "label_de": "pH-Wert",
        "label_en": "pH Value",
        "sds_section": "9.1",
        "value_type": "NUMERIC_RANGE",
        "unit": "",
        "sort_order": 90,
    },
    {
        "key": "viscosity",
        "label_de": "Viskosität",
        "label_en": "Viscosity",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "mPa·s",
        "sort_order": 100,
    },
    {
        "key": "water_solubility",
        "label_de": "Wasserlöslichkeit",
        "label_en": "Water Solubility",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "g/L",
        "sort_order": 110,
    },
    {
        "key": "log_pow",
        "label_de": "Verteilungskoeffizient n-Octanol/Wasser",
        "label_en": "Partition Coefficient n-Octanol/Water",
        "sds_section": "9.1",
        "value_type": "NUMERIC",
        "unit": "",
        "sort_order": 120,
    },
    # SDS Abschnitt 15 — Rechtsvorschriften
    {
        "key": "wgk",
        "label_de": "Wassergefährdungsklasse",
        "label_en": "Water Hazard Class",
        "sds_section": "15.1",
        "value_type": "ENUM",
        "unit": "",
        "is_promoted": True,
        "promoted_column_name": "wgk",
        "sort_order": 200,
    },
    {
        "key": "storage_class",
        "label_de": "Lagerklasse (TRGS 510)",
        "label_en": "Storage Class (TRGS 510)",
        "sds_section": "15.1",
        "value_type": "TEXT",
        "unit": "",
        "is_promoted": True,
        "promoted_column_name": "storage_class_trgs510",
        "sort_order": 210,
    },
    {
        "key": "voc_percent",
        "label_de": "VOC-Gehalt",
        "label_en": "VOC Content",
        "sds_section": "15.1",
        "value_type": "NUMERIC",
        "unit": "%",
        "is_promoted": True,
        "promoted_column_name": "voc_percent",
        "sort_order": 220,
    },
]


class Command(BaseCommand):
    help = "Seed SDS Property Definitions (idempotent, ADR-017 §5.3)"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for defn in DEFINITIONS:
            key = defn.pop("key")
            _, was_created = SdsPropertyDefinition.objects.update_or_create(
                key=key,
                defaults=defn,
            )
            defn["key"] = key
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Property Definitions: {created} created, {updated} updated "
                f"(total {SdsPropertyDefinition.objects.count()})"
            )
        )
