"""AuthService — magic link authentication business logic."""

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

import resend

from repositories.magic_link import MagicLinkRepository
from repositories.session import SessionRepository
from repositories.user import UserRepository, UserRow

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAGIC_LINK_TTL_SECONDS = 15 * 60       # 15 minutes
SESSION_TTL_DAYS = 30
RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW_SECONDS = 10 * 60    # 10 minutes


class AuthError(Exception):
    """Raised for expected auth failures (invalid token, rate limit, etc.)."""


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        magic_link_repo: MagicLinkRepository,
        session_repo: SessionRepository,
        resend_api_key: str,
        email_from: str,
        base_url: str,
        skip_email: bool = False,
    ) -> None:
        self._user_repo = user_repo
        self._magic_link_repo = magic_link_repo
        self._session_repo = session_repo
        self._email_from = email_from
        self._base_url = base_url.rstrip("/")
        self._skip_email = skip_email
        resend.api_key = resend_api_key

    # ── Public API ────────────────────────────────────────────────────────────

    async def request_magic_link(self, email: str) -> None:
        """Send a magic link to the given email address.

        Creates the user if they don't exist yet.
        Always returns without revealing whether the email was already registered.
        Raises AuthError if the email is invalid or rate limit is exceeded.
        """
        if not _EMAIL_RE.match(email):
            raise AuthError("Invalid email address.")

        user = await self._user_repo.find_by_email(email)
        if user is None:
            user = await self._user_repo.create(email)

        recent = await self._magic_link_repo.count_recent_for_user(
            user.id, RATE_LIMIT_WINDOW_SECONDS
        )
        if recent >= RATE_LIMIT_MAX:
            raise AuthError("Too many login attempts. Please wait a few minutes and try again.")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=MAGIC_LINK_TTL_SECONDS)
        await self._magic_link_repo.create(user.id, token, expires_at)

        magic_url = f"{self._base_url}/auth/verify?token={token}"

        if self._skip_email:
            logger.debug("SKIP_EMAIL=true — magic link for %s: %s...", email, magic_url[:40])
        else:
            await self._send_magic_link_email(email, magic_url)

    async def verify_magic_link(self, token: str) -> str:
        """Validate a magic link token and return a new session token.

        Raises AuthError if the token is invalid, expired, or already used.
        The claim() call is atomic — no TOCTOU race between checking and marking used.
        """
        link = await self._magic_link_repo.claim(token)
        if link is None:
            raise AuthError("Invalid or expired login link.")

        now = datetime.now(timezone.utc)
        await self._user_repo.update_last_login(link.user_id)

        session_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(days=SESSION_TTL_DAYS)
        await self._session_repo.create(link.user_id, session_token, expires_at)

        logger.info("User %s logged in via magic link", link.user_id)
        return session_token

    async def get_user_from_session(self, session_token: str) -> UserRow | None:
        """Return the user for a valid session token, or None if invalid/expired."""
        session = await self._session_repo.find_by_token(session_token)
        if session is None:
            return None
        return await self._user_repo.find_by_id(session.user_id)

    async def logout(self, session_token: str) -> None:
        """Invalidate the session associated with the given token."""
        session = await self._session_repo.find_by_token(session_token)
        if session is not None:
            await self._session_repo.delete(session.id)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _send_magic_link_email(self, to: str, magic_url: str) -> None:
        """Send the magic link email via Resend."""
        try:
            resend.Emails.send({
                "from": self._email_from,
                "to": to,
                "subject": "Your pick-ma-job login link",
                "html": (
                    f"<p>Click the link below to log in. "
                    f"It expires in 15 minutes.</p>"
                    f'<p><a href="{magic_url}">Log in to pick-ma-job</a></p>'
                    f"<p>If you didn't request this, you can ignore this email.</p>"
                ),
            })
            logger.info("Magic link email sent to %s", to)
        except Exception:
            logger.exception("Failed to send magic link email to %s", to)
            raise AuthError("Failed to send login email. Please try again.")
