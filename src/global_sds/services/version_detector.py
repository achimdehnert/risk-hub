# src/global_sds/services/version_detector.py
"""
SdsVersionDetector — Versionserkennung (ADR-012 §5 Stufe 3).

Erkennt ob ein hochgeladenes SDS eine neue Version einer
bekannten Substanz ist, oder ob ein Konflikt vorliegt.
"""

import logging
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from global_sds.models import GlobalSdsRevision, GlobalSubstance

logger = logging.getLogger(__name__)


class VersionOutcome(StrEnum):
    """Ergebnis der Versionserkennung."""

    FIRST_REVISION = "FIRST_REVISION"
    NEW_REVISION = "NEW_REVISION"
    CONFLICT = "CONFLICT"


@dataclass
class VersionResult:
    """Ergebnis der Versionserkennung."""

    outcome: VersionOutcome
    previous_revision: GlobalSdsRevision | None = None
    reason: str = ""


class SdsVersionDetector:
    """
    Vergleicht Datum/Versionsnummer mit bestehenden Revisionen.

    - revision_date neu > alt → Supersession
    - version_number neu > alt → Supersession
    - Datum/Version konfliktär → Kuration-Queue
    - Erste Revision → direkt VERIFIED
    """

    def detect(
        self,
        substance: GlobalSubstance,
        revision_date: date | None,
        version_number: str = "",
    ) -> VersionResult:
        """Version erkennen."""
        current = (
            GlobalSdsRevision.objects.filter(substance=substance)
            .exclude(status=GlobalSdsRevision.Status.REJECTED)
            .order_by("-revision_date", "-created_at")
            .first()
        )

        if current is None:
            return VersionResult(
                outcome=VersionOutcome.FIRST_REVISION,
                reason="Erste Revision dieser Substanz",
            )

        # Datums-Vergleich
        if revision_date and current.revision_date:
            if revision_date > current.revision_date:
                return VersionResult(
                    outcome=VersionOutcome.NEW_REVISION,
                    previous_revision=current,
                    reason=(f"Neuer: {revision_date} > {current.revision_date}"),
                )
            if revision_date < current.revision_date:
                return VersionResult(
                    outcome=VersionOutcome.CONFLICT,
                    previous_revision=current,
                    reason=(f"Retrograd: {revision_date} < {current.revision_date}"),
                )

        # Versionsnummer-Vergleich
        if version_number and current.version_number:
            try:
                new_ver = self._parse_version(version_number)
                old_ver = self._parse_version(
                    current.version_number,
                )
                if new_ver > old_ver:
                    return VersionResult(
                        outcome=VersionOutcome.NEW_REVISION,
                        previous_revision=current,
                        reason=(f"Version {version_number} > {current.version_number}"),
                    )
                if new_ver == old_ver and revision_date:
                    return VersionResult(
                        outcome=VersionOutcome.CONFLICT,
                        previous_revision=current,
                        reason=("Gleiche Version, anderer Inhalt"),
                    )
            except ValueError:
                logger.warning(
                    "Cannot parse version: '%s' or '%s'",
                    version_number,
                    current.version_number,
                )

        # Kein eindeutiges Ergebnis
        return VersionResult(
            outcome=VersionOutcome.CONFLICT,
            previous_revision=current,
            reason="Datum/Version nicht eindeutig",
        )

    def _parse_version(self, version: str) -> tuple:
        """Version string in vergleichbares Tuple parsen.

        Handles formats: "4", "1.2.3", "3a", "1.2-beta".
        Non-numeric suffixes are stripped; only numeric parts are compared.
        """
        import re

        parts = version.strip().split(".")
        result = []
        for part in parts:
            match = re.match(r"(\d+)", part)
            if match:
                result.append(int(match.group(1)))
            else:
                raise ValueError(f"Cannot parse version part: {part!r}")
        if not result:
            raise ValueError(f"No numeric parts in version: {version!r}")
        return tuple(result)
