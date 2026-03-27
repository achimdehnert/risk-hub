# src/explosionsschutz/models/__init__.py
"""
Explosionsschutz-Modul Models (v6 - Split Edition)

Basiert auf ADR-001 v5.0 + Input-Review v6:
- Hybrid Tenant-Isolation für Stammdaten
- Vollständiger Audit-Trail via Service Layer
- Strukturierte ATEX-Kennzeichnung mit EPL
- Zündquellen-Bewertung nach EN 1127-1
- Zone Extent mit Pydantic-Schema

Split in Sub-Module für bessere Wartbarkeit:
- base: TenantScopedMasterData Infrastructure
- master_data: ReferenceStandard, MeasureCatalog, SafetyFunction, EquipmentType
- concept: Area, ExplosionConcept
- zone: ZoneDefinition, IgnitionSource, ZoneIgnitionSourceAssessment, ZoneCalculationResult
- measure: ProtectionMeasure
- equipment: Equipment, Inspection, EquipmentATEXCheck
- document: VerificationDocument
"""

from .base import TenantScopedMasterData, TenantScopedMasterDataManager
from .concept import Area, ExplosionConcept
from .concept_doc import ExConceptDocument, ExConceptTemplateStore, ExFilledTemplate
from .doc_template import ExDocInstance, ExDocTemplate
from .document import VerificationDocument
from .equipment import Equipment, EquipmentATEXCheck, Inspection
from .master_data import EquipmentType, MeasureCatalog, ReferenceStandard, SafetyFunction
from .measure import ProtectionMeasure
from .zone import (
    IgnitionSource,
    ZoneCalculationResult,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)

__all__ = [
    # Base
    "TenantScopedMasterDataManager",
    "TenantScopedMasterData",
    # Master Data
    "ReferenceStandard",
    "MeasureCatalog",
    "SafetyFunction",
    "EquipmentType",
    # Concept
    "Area",
    "ExplosionConcept",
    # Zone
    "ZoneDefinition",
    "IgnitionSource",
    "ZoneIgnitionSourceAssessment",
    "ZoneCalculationResult",
    # Measure
    "ProtectionMeasure",
    # Equipment
    "Equipment",
    "Inspection",
    "EquipmentATEXCheck",
    # Document
    "VerificationDocument",
    # Concept Templates (ADR-147)
    "ExConceptDocument",
    "ExConceptTemplateStore",
    "ExFilledTemplate",
    # Dokument-Templates (standalone)
    "ExDocTemplate",
    "ExDocInstance",
]
