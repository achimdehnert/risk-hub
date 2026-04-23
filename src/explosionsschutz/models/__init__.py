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
- reference: ReferenceStandardClause (ADR-044 Phase 1A)
- annex: AnnexIChecklistItem (ADR-044 Phase 1A)
- msr: TrgsK725Mapping (ADR-044 Phase 1A)
"""

from .anlage import AnlageComponent, OperationalState, OperationalStateAssessment
from .annex import AnnexIChecklistItem
from .approval import ApprovalStatement, ConceptApprovalSnapshot, ConceptDocumentLink
from .base import TenantScopedMasterData, TenantScopedMasterDataManager
from .concept import Area, ExplosionConcept
from .concept_doc import ExConceptDocument, ExConceptTemplateStore, ExFilledTemplate
from .cybersecurity import CybersecurityAssessment
from .doc_template import ExDocInstance, ExDocTemplate
from .document import VerificationDocument
from .dust import DustSubstanceProperties
from .equipment import Equipment, EquipmentATEXCheck, Inspection
from .generation_log import (
    ExplosionConceptGenerationLog,
    GenerationChapter,
    GenerationStatus,
)
from .master_data import EquipmentType, MeasureCatalog, ReferenceStandard, SafetyFunction
from .measure import ProtectionMeasure
from .msr import MsrRealizationType, MsrSafetyFunction, TrgsK725Mapping
from .reference import ReferenceStandardClause
from .review import (
    AnnexIChecklistAssessment,
    AnnexIChecklistAssessmentStatus,
    InspectorRole,
    RegulatoryLayer,
    ReviewScheduleEntry,
)
from .substance_ref import (
    ConceptSubstanceReference,
    ContainerType,
    SubstanceContainer,
    SubstanceRole,
)
from .zone import (
    IgnitionAssessmentStatus,
    IgnitionSource,
    ZoneCalculationResult,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)
from .zone_extensions import AtmosphereForm, ConditionalZoneTrigger, ZoneConditionType

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
    # KI-Augmentierung (ADR-018)
    "ExplosionConceptGenerationLog",
    "GenerationChapter",
    "GenerationStatus",
    # ADR-044 Phase 1A — Seed-Daten
    "ReferenceStandardClause",
    "AnnexIChecklistItem",
    "TrgsK725Mapping",
    # ADR-044 Phase 1B — Staub-Kenngrößen
    "DustSubstanceProperties",
    # ADR-044 Phase 1C — Zonen-Erweiterungen
    "AtmosphereForm",
    "ZoneConditionType",
    "ConditionalZoneTrigger",
    # ADR-044 Phase 2A — Vier-wertige Zündquellen-Bewertung
    "IgnitionAssessmentStatus",
    # ADR-044 Phase 2B — Mehrstoff-Bewertung
    "SubstanceRole",
    "ConceptSubstanceReference",
    "ContainerType",
    "SubstanceContainer",
    # ADR-044 Phase 3A — MSR-Sicherheitsfunktionen
    "MsrRealizationType",
    "MsrSafetyFunction",
    # ADR-044 Phase 3B — Anlage + Betriebszustände
    "AnlageComponent",
    "OperationalState",
    "OperationalStateAssessment",
    # ADR-044 Phase 4A — Cybersecurity
    "CybersecurityAssessment",
    # ADR-044 Phase 4B — Prüfplan + Anhang-I
    "RegulatoryLayer",
    "InspectorRole",
    "ReviewScheduleEntry",
    "AnnexIChecklistAssessmentStatus",
    "AnnexIChecklistAssessment",
    # ADR-044 Phase 5A — Freigabe + Snapshot
    "ApprovalStatement",
    "ConceptDocumentLink",
    "ConceptApprovalSnapshot",
]
