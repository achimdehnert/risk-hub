"""CSV Import Service for VVT, TOM, and AVV data.

Supports semicolon-delimited CSVs in both generell (template)
and tenant-specific (MAROLD-style) formats.
"""

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from uuid import UUID

from django.db import transaction
from django.utils.text import slugify

from dsb.models import (
    DataProcessingAgreement,
    Mandate,
    OrganizationalMeasure,
    ProcessingActivity,
    RetentionRule,
    TechnicalMeasure,
    ThirdCountryTransfer,
)
from dsb.models.choices import MeasureStatus
from dsb.models.lookups import TomCategory

logger = logging.getLogger(__name__)

_LEGAL_BASIS_MAP: dict[str, str] = {
    "lit. a": "consent",
    "lit. b": "contract",
    "lit. c": "legal_obligation",
    "lit. d": "vital_interest",
    "lit. e": "public_interest",
    "lit. f": "legitimate_interest",
}


@dataclass
class ImportResult:
    """Summary of a CSV import run."""

    csv_type: str = ""
    rows_total: int = 0
    vvt_created: int = 0
    tom_tech_created: int = 0
    tom_org_created: int = 0
    avv_created: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def detect_csv_type(headers: list[str]) -> str:
    """Detect CSV type from header row. Returns 'vvt' or 'tom'."""
    h_lower = [h.strip().lower() for h in headers]
    if "verarbeitungstaetigkeit" in h_lower:
        return "vvt"
    if "tom-kategorie" in h_lower or "massnahme" in h_lower:
        return "tom"
    raise ValueError(
        f"Unbekanntes CSV-Format. Header: {', '.join(headers[:5])}"
    )


def _map_legal_basis(text: str) -> str:
    t = text.lower()
    for pattern, value in _LEGAL_BASIS_MAP.items():
        if pattern in t:
            return value
    return "legitimate_interest"


def _map_status(text: str) -> str:
    t = re.sub(r"^\[.\]\s*", "", text.strip()).lower()
    if "umgesetzt" in t:
        return MeasureStatus.IMPLEMENTED
    return MeasureStatus.PLANNED


def _parse_csv(content: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    headers = reader.fieldnames or []
    rows = [r for r in reader if any(v.strip() for v in r.values())]
    return headers, rows


def _resolve_tom_category(
    cat_name: str,
) -> tuple[TomCategory | None, str]:
    """Resolve TOM category from DB. Returns (category, measure_type).

    Looks up TomCategory by key/label. If not found, creates it
    with measure_type='technical' as default.
    """
    if not cat_name.strip():
        return None, "technical"
    key = slugify(cat_name.strip())[:80]
    cat = TomCategory.objects.filter(key=key).first()
    if cat:
        return cat, cat.measure_type
    # Fallback: create with default type 'technical'
    cat = TomCategory.objects.create(
        key=key,
        label=cat_name.strip(),
        measure_type=TomCategory.MeasureType.TECHNICAL,
    )
    return cat, cat.measure_type


def _build_vvt_desc(row: dict[str, str]) -> str:
    parts: list[str] = []
    for csv_key, label in [
        ("Gruppe", "Gruppe"), ("Zweck", "Zweck"),
        ("Betroffene Personen", "Betroffene Personen"),
        ("Datenkategorien", "Datenkategorien"),
        ("Empfaenger", "Empf\u00e4nger"),
        ("TOM-Verweis", "TOM-Verweis"),
        ("Eingesetzte Systeme MAROLD", "Eingesetzte Systeme"),
        ("Drittland-Absicherung", "Drittland-Absicherung"),
    ]:
        val = row.get(csv_key, "").strip()
        if val:
            parts.append(f"**{label}:** {val}")
    return "\n".join(parts)


def _build_tom_desc(row: dict[str, str]) -> str:
    parts: list[str] = []
    desc = (
        row.get("Beschreibung", "").strip()
        or row.get("Konkrete Umsetzung MAROLD", "").strip()
    )
    if desc:
        parts.append(desc)
    for csv_key, label in [
        ("Betroffene Systeme", "Systeme"),
        ("Rechtsgrundlage", "Rechtsgrundlage"),
        ("Pruefintervall", "Pr\u00fcfintervall"),
        ("Verantwortlich", "Verantwortlich"),
    ]:
        val = row.get(csv_key, "").strip()
        if val:
            parts.append(f"**{label}:** {val}")
    return "\n".join(parts)


def _extract_country(text: str) -> str:
    if "usa" in text.lower():
        return "USA"
    if "eu" in text.lower():
        return "EU"
    return text[:100]


def _detect_safeguard(text: str) -> str:
    t = text.lower()
    if "scc" in t:
        return "scc"
    if "dpf" in t:
        return "dpf"
    if "bcr" in t:
        return "bcr"
    if "angemessenheit" in t:
        return "adequacy"
    return "other"


@transaction.atomic
def import_vvt(
    content: str,
    mandate: Mandate,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> ImportResult:
    """Import VVT CSV into ProcessingActivity records."""
    result = ImportResult(csv_type="vvt")
    _, rows = _parse_csv(content)
    result.rows_total = len(rows)

    for row in rows:
        try:
            nr_raw = row.get("Nr", "").strip()
            number = int(re.sub(r"\D", "", nr_raw)) if nr_raw else 0
            name = row.get("Verarbeitungstaetigkeit", "").strip()
            if not name:
                result.skipped += 1
                continue

            pa, created = ProcessingActivity.objects.update_or_create(
                tenant_id=tenant_id, mandate=mandate, number=number,
                defaults={
                    "name": name[:300],
                    "legal_basis": _map_legal_basis(
                        row.get("Rechtsgrundlage", ""),
                    ),
                    "description": _build_vvt_desc(row),
                    "created_by_id": user_id,
                    "updated_by_id": user_id,
                },
            )
            if created:
                result.vvt_created += 1

            frist = row.get("Loeschfrist", "").strip()
            if frist and created:
                RetentionRule.objects.create(
                    tenant_id=tenant_id,
                    processing_activity=pa,
                    condition="Standard",
                    period=frist[:100],
                )

            transfer = row.get("Drittlandtransfer", "").strip()
            if transfer and created and "nicht" not in transfer.lower():
                sg_text = row.get("Drittland-Absicherung", "").strip()
                ThirdCountryTransfer.objects.create(
                    tenant_id=tenant_id,
                    processing_activity=pa,
                    country=_extract_country(transfer),
                    recipient_entity=transfer[:200],
                    safeguard=_detect_safeguard(sg_text),
                )
        except Exception as exc:
            result.errors.append(f"VVT Nr {row.get('Nr', '?')}: {exc}")
            logger.warning("VVT import error: %s", exc)

    return result


@transaction.atomic
def import_tom(
    content: str,
    mandate: Mandate,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> ImportResult:
    """Import TOM CSV into Tech/Org Measures + AVV records."""
    result = ImportResult(csv_type="tom")
    _, rows = _parse_csv(content)
    result.rows_total = len(rows)

    for row in rows:
        try:
            cat_name = row.get("TOM-Kategorie", "").strip()
            title = row.get("Massnahme", "").strip()
            if not title:
                result.skipped += 1
                continue

            cat, mtype = _resolve_tom_category(cat_name)
            desc = _build_tom_desc(row)
            status = _map_status(row.get("Status", ""))

            if mtype == TomCategory.MeasureType.AVV:
                DataProcessingAgreement.objects.update_or_create(
                    tenant_id=tenant_id, mandate=mandate,
                    partner_name=title[:300],
                    defaults={
                        "subject_matter": desc,
                        "status": "draft",
                        "created_by_id": user_id,
                    },
                )
                result.avv_created += 1
            elif mtype == TomCategory.MeasureType.ORGANIZATIONAL:
                OrganizationalMeasure.objects.update_or_create(
                    tenant_id=tenant_id, mandate=mandate,
                    title=title[:255],
                    defaults={
                        "category": cat,
                        "description": desc,
                        "status": status,
                        "created_by_id": user_id,
                    },
                )
                result.tom_org_created += 1
            else:
                TechnicalMeasure.objects.update_or_create(
                    tenant_id=tenant_id, mandate=mandate,
                    title=title[:255],
                    defaults={
                        "category": cat,
                        "description": desc,
                        "status": status,
                        "created_by_id": user_id,
                    },
                )
                result.tom_tech_created += 1
        except Exception as exc:
            result.errors.append(f"TOM '{title[:30]}': {exc}")
            logger.warning("TOM import error: %s", exc)

    return result


def import_csv(
    content: str,
    mandate: Mandate,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> ImportResult:
    """Auto-detect CSV type and import."""
    headers, _ = _parse_csv(content)
    csv_type = detect_csv_type(headers)
    if csv_type == "vvt":
        return import_vvt(content, mandate, tenant_id, user_id)
    return import_tom(content, mandate, tenant_id, user_id)
