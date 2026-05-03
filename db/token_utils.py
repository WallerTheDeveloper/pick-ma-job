"""Token hashing utilities for secure token storage."""

import hashlib


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token.

    The raw token is generated with ``secrets.token_urlsafe(32)`` (256-bit
    entropy), so SHA-256 does not reduce security — it only removes the
    stored plaintext from the database.
    """
    return hashlib.sha256(token.encode()).hexdigest()
