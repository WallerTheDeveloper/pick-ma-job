"""Unit tests for AuthService — all external dependencies are mocked."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from repositories.magic_link import MagicLinkRow
from repositories.session import SessionRow
from repositories.user import UserRow
from services.auth import AuthError, AuthService


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_user(email: str = "test@example.com") -> UserRow:
    return UserRow(id=uuid4(), email=email, created_at=datetime.now(timezone.utc), last_login=None)


def _make_magic_link(user_id, token: str, used: bool = False, expired: bool = False) -> MagicLinkRow:
    expires_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    return MagicLinkRow(
        id=uuid4(),
        user_id=user_id,
        token=token,
        used=used,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
    )


def _make_session(user_id) -> SessionRow:
    return SessionRow(
        id=uuid4(),
        user_id=user_id,
        token="session-tok",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )


def _make_service(
    user_repo=None,
    magic_link_repo=None,
    session_repo=None,
    skip_email: bool = True,
) -> AuthService:
    return AuthService(
        user_repo=user_repo or MagicMock(),
        magic_link_repo=magic_link_repo or MagicMock(),
        session_repo=session_repo or MagicMock(),
        resend_api_key="re_test",
        email_from="noreply@example.com",
        base_url="http://localhost:8000",
        skip_email=skip_email,
    )


# ── request_magic_link ────────────────────────────────────────────────────────

async def test_request_magic_link_invalid_email_raises():
    svc = _make_service()
    with pytest.raises(AuthError, match="Invalid email"):
        await svc.request_magic_link("not-an-email")


async def test_request_magic_link_creates_new_user(monkeypatch):
    user_repo = MagicMock()
    ml_repo = MagicMock()

    user = _make_user()
    user_repo.find_by_email = AsyncMock(return_value=None)
    user_repo.create = AsyncMock(return_value=user)
    ml_repo.count_recent_for_user = AsyncMock(return_value=0)
    ml_repo.create = AsyncMock(return_value=MagicMock())

    svc = _make_service(user_repo=user_repo, magic_link_repo=ml_repo)
    await svc.request_magic_link("new@example.com")

    user_repo.create.assert_awaited_once_with("new@example.com")
    ml_repo.create.assert_awaited_once()


async def test_request_magic_link_existing_user_no_duplicate_create():
    user_repo = MagicMock()
    ml_repo = MagicMock()

    user = _make_user("existing@example.com")
    user_repo.find_by_email = AsyncMock(return_value=user)
    ml_repo.count_recent_for_user = AsyncMock(return_value=0)
    ml_repo.create = AsyncMock(return_value=MagicMock())

    svc = _make_service(user_repo=user_repo, magic_link_repo=ml_repo)
    await svc.request_magic_link("existing@example.com")

    user_repo.create.assert_not_called()
    ml_repo.create.assert_awaited_once()


async def test_request_magic_link_rate_limited_raises():
    user_repo = MagicMock()
    ml_repo = MagicMock()

    user = _make_user()
    user_repo.find_by_email = AsyncMock(return_value=user)
    ml_repo.count_recent_for_user = AsyncMock(return_value=3)  # at limit

    svc = _make_service(user_repo=user_repo, magic_link_repo=ml_repo)
    with pytest.raises(AuthError, match="Too many"):
        await svc.request_magic_link("test@example.com")

    ml_repo.create.assert_not_called()


async def test_request_magic_link_sends_email():
    user_repo = MagicMock()
    ml_repo = MagicMock()

    user = _make_user()
    user_repo.find_by_email = AsyncMock(return_value=user)
    ml_repo.count_recent_for_user = AsyncMock(return_value=0)
    ml_repo.create = AsyncMock(return_value=MagicMock())

    svc = _make_service(user_repo=user_repo, magic_link_repo=ml_repo, skip_email=False)

    with patch("resend.Emails.send") as mock_send:
        await svc.request_magic_link("test@example.com")
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[0][0]
        assert call_kwargs["to"] == "test@example.com"
        assert "/auth/verify?token=" in call_kwargs["html"]


# ── verify_magic_link ─────────────────────────────────────────────────────────

async def test_verify_valid_token_creates_session():
    user_repo = MagicMock()
    ml_repo = MagicMock()
    session_repo = MagicMock()

    user = _make_user()
    token = "valid-token-abc"
    link = _make_magic_link(user.id, token)

    # claim() atomically marks the link used and returns it
    ml_repo.claim = AsyncMock(return_value=link)
    user_repo.update_last_login = AsyncMock()
    session_repo.create = AsyncMock(return_value=_make_session(user.id))

    svc = _make_service(user_repo=user_repo, magic_link_repo=ml_repo, session_repo=session_repo)
    session_token = await svc.verify_magic_link(token)

    assert session_token is not None
    ml_repo.claim.assert_awaited_once_with(token)
    user_repo.update_last_login.assert_awaited_once_with(user.id)
    session_repo.create.assert_awaited_once()


async def test_verify_nonexistent_token_raises():
    ml_repo = MagicMock()
    ml_repo.claim = AsyncMock(return_value=None)

    svc = _make_service(magic_link_repo=ml_repo)
    with pytest.raises(AuthError, match="Invalid or expired"):
        await svc.verify_magic_link("ghost-token")


async def test_verify_used_token_raises():
    # claim() returns None for used tokens — DB handles this atomically
    ml_repo = MagicMock()
    ml_repo.claim = AsyncMock(return_value=None)

    svc = _make_service(magic_link_repo=ml_repo)
    with pytest.raises(AuthError, match="Invalid or expired"):
        await svc.verify_magic_link("used-token")


async def test_verify_expired_token_raises():
    # claim() returns None for expired tokens — DB handles this atomically
    ml_repo = MagicMock()
    ml_repo.claim = AsyncMock(return_value=None)

    svc = _make_service(magic_link_repo=ml_repo)
    with pytest.raises(AuthError, match="Invalid or expired"):
        await svc.verify_magic_link("expired-token")


# ── get_user_from_session ─────────────────────────────────────────────────────

async def test_get_user_from_session_valid():
    user_repo = MagicMock()
    session_repo = MagicMock()

    user = _make_user()
    session = _make_session(user.id)
    session_repo.find_by_token = AsyncMock(return_value=session)
    user_repo.find_by_id = AsyncMock(return_value=user)

    svc = _make_service(user_repo=user_repo, session_repo=session_repo)
    result = await svc.get_user_from_session("session-tok")

    assert result is not None
    assert result.id == user.id


async def test_get_user_from_session_invalid_returns_none():
    session_repo = MagicMock()
    session_repo.find_by_token = AsyncMock(return_value=None)

    svc = _make_service(session_repo=session_repo)
    result = await svc.get_user_from_session("bad-token")

    assert result is None


# ── logout ────────────────────────────────────────────────────────────────────

async def test_logout_deletes_session():
    session_repo = MagicMock()
    user = _make_user()
    session = _make_session(user.id)

    session_repo.find_by_token = AsyncMock(return_value=session)
    session_repo.delete = AsyncMock()

    svc = _make_service(session_repo=session_repo)
    await svc.logout("session-tok")

    session_repo.delete.assert_awaited_once_with(session.id)


async def test_logout_no_session_is_silent():
    session_repo = MagicMock()
    session_repo.find_by_token = AsyncMock(return_value=None)
    session_repo.delete = AsyncMock()

    svc = _make_service(session_repo=session_repo)
    await svc.logout("nonexistent-token")  # Should not raise

    session_repo.delete.assert_not_awaited()
