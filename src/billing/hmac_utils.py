"""HMAC verification for billing-hub internal API calls (ADR-118).

Verifies X-Billing-Timestamp + X-Billing-Signature headers.
Supports dual-secret rotation (primary + previous secret).
"""

from __future__ import annotations

import hashlib
import hmac
import time


def verify_request(
    timestamp_header: str,
    signature_header: str,
    body: str,
    secret: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify HMAC-SHA256 signature with replay protection.

    Checks timestamp is within max_age_seconds (default 5 min).
    """
    try:
        ts = int(timestamp_header)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts) > max_age_seconds:
        return False

    expected = hmac.new(
        secret.encode(),
        f"{ts}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)


def verify_request_dual_secret(
    timestamp_header: str,
    signature_header: str,
    body: str,
    primary_secret: str,
    secondary_secret: str | None = None,
    max_age_seconds: int = 300,
) -> bool:
    """Verify with dual-secret support for rotation (ADR-118)."""
    if verify_request(timestamp_header, signature_header, body, primary_secret, max_age_seconds):
        return True
    if secondary_secret:
        return verify_request(
            timestamp_header, signature_header, body, secondary_secret, max_age_seconds
        )
    return False
