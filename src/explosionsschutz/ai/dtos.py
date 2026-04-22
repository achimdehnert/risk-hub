# src/explosionsschutz/ai/dtos.py
"""
Commands und Results für KI-Generierung (ADR-018).
Frozen dataclasses — keine Mutation nach Erstellung.
"""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class GenerateProposalCmd:
    """Command: KI-Vorschlag für einen Abschnitt generieren."""

    concept_id: int
    tenant_id: UUID
    chapter: str
    additional_user_notes: str = ""


@dataclass(frozen=True)
class AcceptProposalCmd:
    """Command: KI-Vorschlag durch Experten übernehmen."""

    generation_log_id: int
    accepted_by_user_id: int
    changes_made: str = ""


@dataclass(frozen=True)
class RejectProposalCmd:
    """Command: KI-Vorschlag durch Experten ablehnen."""

    generation_log_id: int
    rejected_by_user_id: int


@dataclass(frozen=True)
class GenerationResult:
    """Result einer KI-Generierung."""

    log_id: int
    success: bool
    text: str = ""
    clarifications: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    error: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
