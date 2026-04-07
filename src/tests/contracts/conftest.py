"""
tests/contracts/conftest.py — Contract-Test Marker Registration.

ADR: ADR-155
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "contract: Contract-Tests für API-Signaturen und Adapter (ADR-155)",
    )
