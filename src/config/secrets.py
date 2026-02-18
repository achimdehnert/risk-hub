"""Secrets reader for production deployments (ADR-045).

Reads secrets from /run/secrets/ files (SOPS-decrypted by CI/CD),
falls back to environment variables for backward compatibility.

Usage in src/config/settings.py:
    from config.secrets import read_secret

    SECRET_KEY = read_secret("DJANGO_SECRET_KEY", required=True)
"""

import os
from pathlib import Path

SECRETS_DIR = Path(os.environ.get("SECRETS_DIR", "/run/secrets"))


def read_secret(
    key: str,
    default: str = "",
    required: bool = False,
) -> str:
    """Read secret from /run/secrets/ file, fall back to env var.

    Priority: /run/secrets/<key_lower> -> os.environ[KEY] -> default.
    Raises ValueError in production if required=True and no value found.
    """
    secret_file = SECRETS_DIR / key.lower()
    if secret_file.is_file():
        value = secret_file.read_text().strip()
        if value:
            return value

    value = os.environ.get(key, "")
    if value:
        return value

    if required and os.environ.get(
        "DJANGO_SETTINGS_MODULE", ""
    ).endswith("production"):
        raise ValueError(
            f"Required secret {key!r} not found in "
            f"{SECRETS_DIR} or environment"
        )

    return default
