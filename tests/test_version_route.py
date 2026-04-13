"""Unit tests for GET /api/version endpoint and VERSION file loading."""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


# ── _read_version ─────────────────────────────────────────────────────────────

def test_read_version_returns_version_string(tmp_path):
    version_file = tmp_path / "VERSION"
    version_file.write_text("2.2.0\n")

    with patch("main.os.path.dirname", return_value=str(tmp_path)):
        from main import _read_version
        assert _read_version() == "2.2.0"


def test_read_version_missing_file_raises(tmp_path):
    with patch("main.os.path.dirname", return_value=str(tmp_path)):
        from main import _read_version
        with pytest.raises(RuntimeError, match="VERSION file not found"):
            _read_version()


# ── GET /api/version ──────────────────────────────────────────────────────────

def test_api_version_returns_version():
    from main import create_app
    app = create_app()
    app.state.version = "2.2.0"

    client = TestClient(app, raise_server_exceptions=True)
    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json() == {"version": "2.2.0"}


def test_api_version_no_auth_required():
    """The /api/version endpoint must be accessible without a session cookie."""
    from main import create_app
    app = create_app()
    app.state.version = "2.2.0"

    client = TestClient(app, raise_server_exceptions=True)
    # Deliberately send no cookies
    response = client.get("/api/version", cookies={})

    assert response.status_code == 200


def test_api_version_route_registered():
    from main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/api/version" in routes
