# src/global_sds/services/diff_service.py
"""
SdsRevisionDiffService — Feldvergleich + Impact-Klassifizierung (ADR-012 §6).

Vergleicht zwei Revisionen, klassifiziert Änderungen und
persistiert den Diff als SdsRevisionDiffRecord.
"""

import logging
from dataclasses import dataclass, field

from django.conf import settings

from global_sds.models import (
    GlobalSdsRevision,
    ImpactLevel,
    SdsRevisionDiffRecord,
)

logger = logging.getLogger(__name__)

# Impact-Zuordnung pro Feld (ADR-012 §6.1, konfigurierbar via settings)
SAFETY_CRITICAL_FIELDS = frozenset(
    getattr(
        settings,
        "SDS_SAFETY_CRITICAL_FIELDS",
        {
            "flash_point_c",
            "ignition_temperature_c",
            "lower_explosion_limit",
            "upper_explosion_limit",
        },
    )
)

REGULATORY_FIELDS = frozenset(
    getattr(
        settings,
        "SDS_REGULATORY_FIELDS",
        {
            "wgk",
            "storage_class_trgs510",
            "voc_percent",
            "voc_g_per_l",
        },
    )
)

INFORMATIONAL_FIELDS = frozenset(
    {
        "manufacturer_name",
        "version_number",
    }
)


@dataclass
class FieldDiff:
    """Einzelner Feldunterschied."""

    field_name: str
    old_value: str
    new_value: str
    impact: str  # ImpactLevel value


@dataclass
class DiffResult:
    """Gesamtes Diff-Ergebnis."""

    field_diffs: list[FieldDiff] = field(default_factory=list)
    added_h_codes: list[str] = field(default_factory=list)
    removed_h_codes: list[str] = field(default_factory=list)
    changed_components: list[str] = field(default_factory=list)
    overall_impact: str = ImpactLevel.INFORMATIONAL

    @property
    def has_changes(self) -> bool:
        return bool(self.field_diffs or self.added_h_codes or self.removed_h_codes)


class SdsRevisionDiffService:
    """
    Vergleicht zwei Revisionen und klassifiziert Änderungen.

    Persistiert den Diff als immutable SdsRevisionDiffRecord.
    """

    COMPARED_FIELDS = (
        SAFETY_CRITICAL_FIELDS
        | REGULATORY_FIELDS
        | INFORMATIONAL_FIELDS
        | {"signal_word", "parse_confidence"}
    )

    def compute_diff(
        self,
        old_revision: GlobalSdsRevision,
        new_revision: GlobalSdsRevision,
    ) -> DiffResult:
        """Diff berechnen."""
        result = DiffResult()

        # Skalare Felder vergleichen
        for fname in self.COMPARED_FIELDS:
            old_val = getattr(old_revision, fname, None)
            new_val = getattr(new_revision, fname, None)
            if old_val != new_val:
                impact = self._classify_field(fname)
                result.field_diffs.append(
                    FieldDiff(
                        field_name=fname,
                        old_value=str(old_val or ""),
                        new_value=str(new_val or ""),
                        impact=impact,
                    )
                )

        # H-Sätze vergleichen
        old_h = set(old_revision.hazard_statements.values_list("code", flat=True))
        new_h = set(new_revision.hazard_statements.values_list("code", flat=True))
        result.added_h_codes = sorted(new_h - old_h)
        result.removed_h_codes = sorted(old_h - new_h)

        # H-Satz-Änderungen sind Safety-Critical
        if result.added_h_codes or result.removed_h_codes:
            result.field_diffs.append(
                FieldDiff(
                    field_name="hazard_statements",
                    old_value=",".join(sorted(old_h)),
                    new_value=",".join(sorted(new_h)),
                    impact=ImpactLevel.SAFETY_CRITICAL,
                )
            )

        # Gesamt-Impact = höchster Einzelimpact
        result.overall_impact = self._compute_overall(
            result.field_diffs,
        )

        logger.info(
            "Diff %s → %s: %d changes, impact=%s",
            old_revision.pk,
            new_revision.pk,
            len(result.field_diffs),
            result.overall_impact,
        )
        return result

    def persist_diff(
        self,
        old_revision: GlobalSdsRevision,
        new_revision: GlobalSdsRevision,
        diff_result: DiffResult,
    ) -> SdsRevisionDiffRecord:
        """Diff als immutable Record persistieren."""
        record, created = SdsRevisionDiffRecord.objects.get_or_create(
            old_revision=old_revision,
            new_revision=new_revision,
            defaults={
                "overall_impact": diff_result.overall_impact,
                "field_diffs": [
                    {
                        "field": d.field_name,
                        "old": d.old_value,
                        "new": d.new_value,
                        "impact": d.impact,
                    }
                    for d in diff_result.field_diffs
                ],
                "added_h_codes": diff_result.added_h_codes,
                "removed_h_codes": diff_result.removed_h_codes,
                "changed_components": (diff_result.changed_components),
            },
        )
        if created:
            logger.info(
                "Persisted DiffRecord %s",
                record.pk,
            )
        return record

    def _classify_field(self, field_name: str) -> str:
        """Impact-Stufe für ein Feld bestimmen."""
        if field_name in SAFETY_CRITICAL_FIELDS:
            return ImpactLevel.SAFETY_CRITICAL
        if field_name in REGULATORY_FIELDS:
            return ImpactLevel.REGULATORY
        return ImpactLevel.INFORMATIONAL

    def _compute_overall(
        self,
        diffs: list[FieldDiff],
    ) -> str:
        """Höchsten Impact aller Diffs bestimmen."""
        priority = {
            ImpactLevel.SAFETY_CRITICAL: 3,
            ImpactLevel.REGULATORY: 2,
            ImpactLevel.INFORMATIONAL: 1,
        }
        if not diffs:
            return ImpactLevel.INFORMATIONAL
        return max(
            (d.impact for d in diffs),
            key=lambda x: priority.get(x, 0),
        )
