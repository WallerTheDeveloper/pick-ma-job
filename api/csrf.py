"""CSRF token utilities — Double Submit Cookie pattern.

The CSRF token is derived from the session token via HMAC-SHA256 using the
MAGIC_LINK_SECRET. This avoids storing CSRF tokens in the database while
remaining unpredictable to any party that does not know the secret.

Usage:
- On login (verify_magic_link), set the csrf_token cookie (non-HttpOnly).
- HTMX reads the cookie and sends it as the X-CSRF-Token header on every
  state-mutating request (POST, PUT, PATCH, DELETE) via an htmx:configRequest
  event handler in base.html.
- Add ``Depends(require_csrf)`` to any mutating route handler.
"""

import hashlib
import hmac
import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

CSRF_COOKIE = "csrf_token"
_CSRF_HEADER = "X-CSRF-Token"
_SESSION_COOKIE = "session_token"


def derive_csrf_token(session_token: str) -> str:
    """Derive a CSRF token from a session token using HMAC-SHA256."""
    secret = os.environ["MAGIC_LINK_SECRET"].encode()
    return hmac.new(secret, session_token.encode(), hashlib.sha256).hexdigest()


async def require_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """FastAPI dependency that validates the CSRF token on state-mutating requests.

    Raises HTTP 403 if the token is missing or does not match the expected value
    derived from the session cookie.
    """
    session_token = request.cookies.get(_SESSION_COOKIE)
    if not session_token:
        # No session — let get_current_user raise 401; we only care about CSRF here.
        return

    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    expected = derive_csrf_token(session_token)
    if not hmac.compare_digest(expected, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid",
        )
