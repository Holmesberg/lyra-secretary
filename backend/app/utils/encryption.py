"""Fernet symmetric encryption for credential-class secrets.

Used by the Moodle Web Services token (alembic 044, 2026-05-01) so the
operator can truthfully tell users "your token is encrypted before
storage". Other credential rows — `moodle_ics_url` (carries authtoken),
`google_refresh_token` — remain plaintext today and are queued for
Phase 6+ when we standardize the trust class.

Key derivation:
  - Source: `settings.SECRET_KEY` (already required ≥32 chars).
  - HKDF/SHA-256 → 32-byte key → urlsafe base64 → Fernet input.
  - Recomputed at module import; rotating SECRET_KEY rotates the
    encryption key in lockstep, which means previously-stored secrets
    must be re-encrypted before rotation. Documented in
    docs/security/credential_rotation.md (TODO; not yet written).

Storage format:
  - Encrypted values are stored as `"fernet:" + base64_token`.
  - The "fernet:" prefix is the migration marker — `decrypt_secret()`
    treats values without the prefix as legacy plaintext and returns
    them unchanged. This lets the operator's existing token (set via
    env before this code shipped) keep working until the next
    re-connect, no forced migration.

Why a prefix marker instead of a separate "encrypted" column:
  - One column = one source of truth for "the secret".
  - Future-proof: if we add another envelope format (e.g.,
    `"kms:..."`), we just add another prefix branch.
  - No risk of forgetting which column holds the canonical value.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

PREFIX = "fernet:"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY. Cached — Fernet construction
    is cheap but stable across calls."""
    secret = settings.SECRET_KEY.encode("utf-8")
    # SHA-256 → 32 bytes → urlsafe base64 → Fernet's required input shape
    digest = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt and prefix. Always produces a `fernet:`-prefixed string;
    callers should treat the return value as opaque."""
    if not plaintext:
        return plaintext
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return PREFIX + token


def decrypt_secret(stored: Optional[str]) -> Optional[str]:
    """Decrypt if `stored` carries the Fernet prefix; otherwise return
    as-is (legacy plaintext path).

    Returns None for None input. On decrypt failure (corrupted value or
    SECRET_KEY rotation), logs at warning level and returns None — the
    caller decides whether to surface as "reconnect needed" or hard fail.
    """
    if stored is None:
        return None
    if not stored.startswith(PREFIX):
        return stored  # legacy plaintext
    try:
        return _fernet().decrypt(stored[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning(
            "encryption: failed to decrypt secret — likely SECRET_KEY rotation"
            " or corruption. Returning None so caller can surface as"
            " 'reconnect needed'."
        )
        return None
