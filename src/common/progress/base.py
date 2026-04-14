# common/progress/base.py
"""
BaseProgressService — Gemeinsame Basisklasse für alle Progress-Services.

Verhindert Duplizierung über GBU, Ex-Schutz und zukünftige Module.

Verwendung:
    class MyProgressService(BaseProgressService):
        STEP_DEFS = [
            StepDef(1, "Schritt A", "_check_a", "Gesetz §X"),
            StepDef(2, "Schritt B", "_check_b", "Gesetz §Y"),
        ]

        def _check_a(self, doc, ctx) -> StepStatus:
            ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StepState(StrEnum):
    """Zustand eines Workflow-Schritts."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass
class StepDef:
    """Deklarative Schritt-Definition."""

    step: int
    label: str
    checker: str
    law_reference: str = ""


@dataclass
class StepStatus:
    """Fortschritts-Status eines einzelnen Workflow-Schritts."""

    step: int
    label: str
    state: StepState
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    law_reference: str = ""
    item_count: int = 0
    completion_percent: int = 0

    @property
    def is_complete(self) -> bool:
        return self.state == StepState.COMPLETE

    @property
    def icon(self) -> str:
        return {
            StepState.COMPLETE: "✓",
            StepState.PARTIAL: "◐",
            StepState.EMPTY: "○",
            StepState.ERROR: "⚠",
            StepState.BLOCKED: "!",
        }[self.state]

    @property
    def css_class(self) -> str:
        return str(self.state)


@dataclass
class DocumentProgress:
    """Aggregierter Fortschritt eines Dokuments/Assessments."""

    steps: list[StepStatus]
    can_approve: bool
    blocking_reasons: list[str]
    overall_percent: int

    @property
    def complete_count(self) -> int:
        return sum(1 for s in self.steps if s.is_complete)

    @property
    def error_count(self) -> int:
        return sum(1 for s in self.steps if s.state in (StepState.ERROR, StepState.BLOCKED))

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def step_by_number(self, n: int) -> StepStatus | None:
        return next((s for s in self.steps if s.step == n), None)


class BaseProgressService:
    """
    Abstrakte Basisklasse für modulare Fortschritts-Services.

    Subklassen definieren STEP_DEFS und _check_*() Methoden.
    Jeder Checker hat die Signatur: (document, ctx: dict) → StepStatus.
    """

    STEP_DEFS: list[StepDef] = []

    def get_progress(self, document: Any) -> DocumentProgress:
        """Berechnet den Gesamtfortschritt. Liest die DB — schreibt nichts."""
        ctx = self._build_context(document)
        steps = []
        for step_def in self.STEP_DEFS:
            checker = getattr(self, step_def.checker)
            status = checker(document, ctx)
            # Ensure step metadata is set
            status.step = step_def.step
            status.label = step_def.label
            status.law_reference = step_def.law_reference
            steps.append(status)

        can, reasons = self._can_approve(document, steps)
        done = sum(1 for s in steps if s.is_complete)
        total = len(steps) or 1
        return DocumentProgress(
            steps=steps,
            can_approve=can,
            blocking_reasons=reasons,
            overall_percent=round(done / total * 100),
        )

    def _can_approve(
        self,
        document: Any,
        steps: list[StepStatus],
    ) -> tuple[bool, list[str]]:
        """Gate: Freigabe nur wenn ALLE Steps COMPLETE. Überschreibbar."""
        blocking = []
        for s in steps:
            if not s.is_complete:
                label = f"Schritt {s.step} ({s.label})"
                if s.issues:
                    blocking.append(f"{label}: {'; '.join(s.issues)}")
                else:
                    blocking.append(f"{label}: nicht abgeschlossen")
        return len(blocking) == 0, blocking

    def _build_context(self, document: Any) -> dict[str, Any]:
        """Hook: Liefert Kontext-Daten für alle Checker. Default: leer."""
        return {}

    # ── Factory-Methoden für Checker ────────────────────────────────────────

    @staticmethod
    def _empty(issue: str, **kwargs: Any) -> StepStatus:
        return StepStatus(step=0, label="", state=StepState.EMPTY, issues=[issue], **kwargs)

    @staticmethod
    def _partial(issues: list[str], pct: int = 50, **kwargs: Any) -> StepStatus:
        return StepStatus(
            step=0,
            label="",
            state=StepState.PARTIAL,
            issues=issues,
            completion_percent=pct,
            **kwargs,
        )

    @staticmethod
    def _complete(info: list[str] | None = None, **kwargs: Any) -> StepStatus:
        return StepStatus(
            step=0,
            label="",
            state=StepState.COMPLETE,
            info=info or [],
            completion_percent=100,
            **kwargs,
        )

    @staticmethod
    def _error(issues: list[str], **kwargs: Any) -> StepStatus:
        return StepStatus(step=0, label="", state=StepState.ERROR, issues=issues, **kwargs)

    @staticmethod
    def _blocked(issue: str, **kwargs: Any) -> StepStatus:
        return StepStatus(step=0, label="", state=StepState.BLOCKED, issues=[issue], **kwargs)
