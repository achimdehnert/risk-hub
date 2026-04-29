from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .models import IntakeUpload, IntakeResult

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, "IntakeHandler"] = {}


@runtime_checkable
class IntakeHandler(Protocol):
    target_code: str
    label: str
    icon: str

    def can_handle(self, doc_type: str) -> bool: ...
    def run(self, upload: "IntakeUpload") -> "IntakeResult": ...


def register(handler: IntakeHandler) -> None:
    _REGISTRY[handler.target_code] = handler
    logger.debug("intake handler registered: %s", handler.target_code)


def get_handler(target_code: str) -> IntakeHandler | None:
    return _REGISTRY.get(target_code)


def all_handlers() -> list[IntakeHandler]:
    return list(_REGISTRY.values())


def suggested_for(doc_type: str) -> list[str]:
    return [h.target_code for h in _REGISTRY.values() if h.can_handle(doc_type)]
