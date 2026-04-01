"""Tests for the main.py app factory — validate_env and create_app."""

import pytest
from fastapi import FastAPI


# ── validate_env ──────────────────────────────────────────────────────────────

def test_validate_env_all_present_passes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "test@example.com")

    from main import validate_env
    validate_env()  # should not raise


def test_validate_env_missing_single_var_raises(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.delenv("EMAIL_FROM", raising=False)

    from main import validate_env
    with pytest.raises(RuntimeError, match="EMAIL_FROM"):
        validate_env()


def test_validate_env_missing_multiple_vars_lists_all(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MAGIC_LINK_SECRET", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "test@example.com")

    from main import validate_env
    with pytest.raises(RuntimeError) as exc_info:
        validate_env()

    msg = str(exc_info.value)
    assert "DATABASE_URL" in msg
    assert "MAGIC_LINK_SECRET" in msg


# ── create_app ────────────────────────────────────────────────────────────────

def test_create_app_returns_fastapi_instance():
    from main import create_app
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_includes_auth_routes():
    from main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/auth/login" in routes
    assert "/auth/magic-link" in routes
    assert "/auth/verify" in routes
    assert "/auth/logout" in routes
