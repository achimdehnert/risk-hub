"""Tests for tenancy.hmac_utils — HMAC signature verification (ADR-118)."""

import hashlib
import hmac
import time

import pytest

from tenancy.hmac_utils import verify_request, verify_request_dual_secret

SECRET = "test-secret-key-2024"
SECRET_PREV = "old-rotated-secret"


def _sign(body: str, secret: str, ts: int | None = None) -> tuple[str, str]:
    """Create valid HMAC signature + timestamp for testing."""
    ts = ts or int(time.time())
    sig = hmac.new(
        secret.encode(),
        f"{ts}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return str(ts), sig


@pytest.mark.unit
class TestVerifyRequest:
    """verify_request tests."""

    def test_should_accept_valid_signature(self):
        body = '{"tenant_id": "abc"}'
        ts, sig = _sign(body, SECRET)
        assert verify_request(ts, sig, body, SECRET) is True

    def test_should_reject_wrong_signature(self):
        body = '{"tenant_id": "abc"}'
        ts, _ = _sign(body, SECRET)
        assert verify_request(ts, "bad-signature", body, SECRET) is False

    def test_should_reject_wrong_secret(self):
        body = '{"tenant_id": "abc"}'
        ts, sig = _sign(body, SECRET)
        assert verify_request(ts, sig, body, "wrong-secret") is False

    def test_should_reject_tampered_body(self):
        body = '{"tenant_id": "abc"}'
        ts, sig = _sign(body, SECRET)
        assert verify_request(ts, sig, '{"tenant_id": "HACKED"}', SECRET) is False

    def test_should_reject_expired_timestamp(self):
        body = '{"data": 1}'
        old_ts = int(time.time()) - 600  # 10 min ago
        ts, sig = _sign(body, SECRET, ts=old_ts)
        assert verify_request(ts, sig, body, SECRET, max_age_seconds=300) is False

    def test_should_reject_future_timestamp(self):
        body = '{"data": 1}'
        future_ts = int(time.time()) + 600
        ts, sig = _sign(body, SECRET, ts=future_ts)
        assert verify_request(ts, sig, body, SECRET, max_age_seconds=300) is False

    def test_should_reject_invalid_timestamp_string(self):
        assert verify_request("not-a-number", "sig", "body", SECRET) is False

    def test_should_reject_empty_timestamp(self):
        assert verify_request("", "sig", "body", SECRET) is False

    def test_should_reject_none_timestamp(self):
        assert verify_request(None, "sig", "body", SECRET) is False

    def test_should_accept_within_custom_max_age(self):
        body = "test"
        old_ts = int(time.time()) - 50
        ts, sig = _sign(body, SECRET, ts=old_ts)
        assert verify_request(ts, sig, body, SECRET, max_age_seconds=60) is True

    def test_should_handle_empty_body(self):
        body = ""
        ts, sig = _sign(body, SECRET)
        assert verify_request(ts, sig, body, SECRET) is True


@pytest.mark.unit
class TestVerifyRequestDualSecret:
    """verify_request_dual_secret tests for key rotation."""

    def test_should_accept_primary_secret(self):
        body = '{"action": "activate"}'
        ts, sig = _sign(body, SECRET)
        assert verify_request_dual_secret(ts, sig, body, SECRET, SECRET_PREV) is True

    def test_should_accept_secondary_secret(self):
        body = '{"action": "activate"}'
        ts, sig = _sign(body, SECRET_PREV)
        assert verify_request_dual_secret(ts, sig, body, SECRET, SECRET_PREV) is True

    def test_should_reject_unknown_secret(self):
        body = '{"action": "activate"}'
        ts, sig = _sign(body, "totally-unknown")
        assert verify_request_dual_secret(ts, sig, body, SECRET, SECRET_PREV) is False

    def test_should_work_without_secondary_secret(self):
        body = "test"
        ts, sig = _sign(body, SECRET)
        assert verify_request_dual_secret(ts, sig, body, SECRET, None) is True

    def test_should_reject_without_secondary_when_signed_with_old(self):
        body = "test"
        ts, sig = _sign(body, SECRET_PREV)
        assert verify_request_dual_secret(ts, sig, body, SECRET, None) is False
