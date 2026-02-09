# substances/services/substance_import.py
"""
Import-Service für Gefahrstoffe.

Importiert reale Gefahrstoffdaten aus JSON-Dateien in die Datenbank.
Unterstützt:
- Stammdaten (Name, CAS, EC, Beschreibung)
- GHS-Klassifikation (H-/P-Sätze, Piktogramme, Signalwort)
- TRGS 510 Lagerklassen
- Ex-Schutz-relevante Daten (Flammpunkt, Zündtemperatur, UEG/OEG)
- Upsert-Logik (update_or_create) für idempotenten Import
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from django.db import transaction

from substances.models import (
    HazardStatementRef,
    Identifier,
    PictogramRef,
    PrecautionaryStatementRef,
    SdsRevision,
    Substance,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DATA_FILE = DATA_DIR / "common_substances.json"


@dataclass
class ImportStats:
    """Tracks import statistics."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated + self.skipped

    def summary(self) -> str:
        lines = [
            f"Import: {self.total} Stoffe verarbeitet",
            f"  Neu: {self.created}",
            f"  Aktualisiert: {self.updated}",
            f"  Übersprungen: {self.skipped}",
        ]
        if self.errors:
            lines.append(f"  Fehler: {len(self.errors)}")
            for err in self.errors[:10]:
                lines.append(f"    - {err}")
        return "\n".join(lines)


class SubstanceImportService:
    """Importiert Gefahrstoffe aus strukturierten JSON-Daten."""

    def __init__(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.user_id = user_id

    def import_from_file(
        self,
        path: Path | None = None,
        *,
        dry_run: bool = False,
    ) -> ImportStats:
        """Import substances from a JSON file.

        Args:
            path: Path to JSON file. Uses default if None.
            dry_run: If True, validate but don't write.

        Returns:
            ImportStats with counts and errors.
        """
        data_path = path or DEFAULT_DATA_FILE
        if not data_path.exists():
            raise FileNotFoundError(
                f"Datendatei nicht gefunden: {data_path}"
            )

        with open(data_path, encoding="utf-8") as f:
            records: list[dict[str, Any]] = json.load(f)

        logger.info(
            "Importiere %d Stoffe aus %s (dry_run=%s)",
            len(records), data_path.name, dry_run,
        )
        return self._import_records(records, dry_run=dry_run)

    def import_from_records(
        self,
        records: list[dict[str, Any]],
        *,
        dry_run: bool = False,
    ) -> ImportStats:
        """Import substances from a list of dicts."""
        return self._import_records(records, dry_run=dry_run)

    def _import_records(
        self,
        records: list[dict[str, Any]],
        *,
        dry_run: bool = False,
    ) -> ImportStats:
        stats = ImportStats()

        for idx, record in enumerate(records, 1):
            name = record.get("name", f"<unbenannt #{idx}>")
            try:
                if dry_run:
                    self._validate_record(record)
                    stats.skipped += 1
                else:
                    created = self._upsert_substance(record)
                    if created:
                        stats.created += 1
                    else:
                        stats.updated += 1
            except Exception as exc:
                msg = f"{name}: {exc}"
                logger.warning("Import-Fehler: %s", msg)
                stats.errors.append(msg)

        logger.info(stats.summary())
        return stats

    @transaction.atomic
    def _upsert_substance(
        self, record: dict[str, Any],
    ) -> bool:
        """Create or update a single substance. Returns True if created."""
        name = record["name"]

        substance, created = Substance.objects.update_or_create(
            tenant_id=self.tenant_id,
            name=name,
            defaults={
                "trade_name": record.get("trade_name", ""),
                "description": record.get("description", ""),
                "status": Substance.Status.ACTIVE,
                "storage_class": record.get("storage_class", ""),
                "is_cmr": record.get("is_cmr", False),
                "flash_point_c": record.get("flash_point_c"),
                "ignition_temperature_c": record.get(
                    "ignition_temperature_c"
                ),
                "lower_explosion_limit": record.get(
                    "lower_explosion_limit"
                ),
                "upper_explosion_limit": record.get(
                    "upper_explosion_limit"
                ),
                "temperature_class": record.get(
                    "temperature_class", ""
                ),
                "explosion_group": record.get("explosion_group", ""),
                "vapor_density": record.get("vapor_density"),
                "created_by": self.user_id,
            },
        )

        self._upsert_identifiers(substance, record)
        self._upsert_sds(substance, record)

        action = "erstellt" if created else "aktualisiert"
        logger.debug("Stoff %s: %s", name, action)
        return created

    def _upsert_identifiers(
        self,
        substance: Substance,
        record: dict[str, Any],
    ) -> None:
        """Create/update CAS, EC, and other identifiers."""
        id_map = {
            "cas": Identifier.IdType.CAS,
            "ec": Identifier.IdType.EC,
        }
        for key, id_type in id_map.items():
            value = record.get(key)
            if not value:
                continue
            Identifier.objects.update_or_create(
                tenant_id=self.tenant_id,
                substance=substance,
                id_type=id_type,
                defaults={
                    "id_value": value,
                    "created_by": self.user_id,
                },
            )

    def _upsert_sds(
        self,
        substance: Substance,
        record: dict[str, Any],
    ) -> None:
        """Create an initial SDS revision with H/P statements."""
        h_codes = record.get("h_statements", [])
        p_codes = record.get("p_statements", [])
        pictogram_codes = record.get("pictograms", [])
        signal_word = record.get("signal_word", "none")

        if not h_codes and not p_codes:
            return

        from django.utils import timezone

        sds, _ = SdsRevision.objects.update_or_create(
            substance=substance,
            revision_number=1,
            defaults={
                "tenant_id": self.tenant_id,
                "created_by": self.user_id,
                "revision_date": timezone.now().date(),
                "status": SdsRevision.Status.APPROVED,
                "signal_word": signal_word,
                "approved_by": self.user_id,
                "approved_at": timezone.now(),
                "notes": "Auto-Import aus Referenzdaten",
            },
        )

        if h_codes:
            refs = HazardStatementRef.objects.filter(
                code__in=h_codes
            )
            sds.hazard_statements.set(refs)

        if p_codes:
            refs = PrecautionaryStatementRef.objects.filter(
                code__in=p_codes
            )
            sds.precautionary_statements.set(refs)

        if pictogram_codes:
            refs = PictogramRef.objects.filter(
                code__in=pictogram_codes
            )
            sds.pictograms.set(refs)

    @staticmethod
    def _validate_record(record: dict[str, Any]) -> None:
        """Validate a record without writing to DB."""
        if not record.get("name"):
            raise ValueError("Feld 'name' fehlt")
        if not record.get("cas"):
            raise ValueError("Feld 'cas' fehlt")
        signal = record.get("signal_word", "none")
        valid_signals = {c.value for c in SdsRevision.SignalWord}
        if signal not in valid_signals:
            raise ValueError(
                f"Ungültiges Signalwort: {signal}"
            )
