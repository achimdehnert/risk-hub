# src/global_sds/services/dtos.py
"""Frozen DTOs for the SDS Upload Pipeline (ADR-017 §5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ParsedSdsData:
    """Immutable DTO carrying extracted SDS data through the pipeline.

    Created by the parser, consumed by IdentityResolver, VersionDetector,
    and UploadPipeline. No ORM dependency.
    """

    product_name: str = ""
    manufacturer_name: str = ""
    cas_number: str = ""
    revision_date: date | None = None
    version_number: str = ""
    signal_word: str = ""
    flash_point_c: float | None = None
    ignition_temperature_c: float | None = None
    lower_explosion_limit: float | None = None
    upper_explosion_limit: float | None = None
    wgk: int | None = None
    storage_class_trgs510: str = ""
    voc_percent: float | None = None
    voc_g_per_l: float | None = None
    h_codes: tuple[str, ...] = ()
    p_codes: tuple[str, ...] = ()
    components: tuple[dict, ...] = ()
    parse_confidence: float = 0.0
    llm_corrections: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        """Convert to dict for pipeline consumption."""
        result = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if val is not None and val != "" and val != () and val != 0.0:
                if isinstance(val, date):
                    result[f] = val.isoformat()
                elif isinstance(val, tuple):
                    result[f] = list(val)
                else:
                    result[f] = val
        return result
