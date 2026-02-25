"""Secrets reader for production deployments (ADR-045).

Priority chain (automatic, no manual prefix needed):
  1. /run/secrets/<key_lower>   — CI/CD-decrypted SOPS secrets (production)
  2. os.environ[KEY]            — environment variables / docker-compose env_file
  3. .env file (project root)   — local development (loaded automatically)
  4. default                    — fallback value

Usage in src/config/settings.py:
    from config.secrets import read_secret

    SECRET_KEY = read_secret("DJANGO_SECRET_KEY", required=True)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

SECRETS_DIR = Path(os.environ.get("SECRETS_DIR", "/run/secrets"))

# Auto-load .env from project root (two levels up from src/config/)
# Does NOT override already-set environment variables (override=False)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_FILE.is_file():
    load_dotenv(_ENV_FILE, override=False)


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
    try:
        if secret_file.is_file():
            value = secret_file.read_text().strip()
            if value:
                return value
    except (PermissionError, OSError):
        pass

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
