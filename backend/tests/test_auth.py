"""Tests for auth router: TikTok OAuth scope, state validation, session storage."""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("HTTPS_ONLY", "false")

from main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def test_tiktok_login_redirects_with_correct_scope():
    """TikTok login must request video.publish scope (not video.upload)."""
    response = client.get("/auth/tiktok", follow_redirects=False)
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "video.publish" in location
    assert "video.query" in location
    # Legacy scope should NOT be used
    assert "video.upload" not in location


def test_tiktok_login_sets_state_in_redirect():
    """TikTok login must include a CSRF state parameter."""
    response = client.get("/auth/tiktok", follow_redirects=False)
    location = response.headers["location"]
    assert "state=" in location


def test_tiktok_callback_missing_code_returns_error_redirect():
    """TikTok callback with no code should redirect with error."""
    response = client.get("/auth/tiktok/callback?error=access_denied", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "error=oauth_failed" in response.headers["location"]


def test_tiktok_callback_invalid_state_returns_error_redirect():
    """TikTok callback with mismatched state should redirect with invalid_state error."""
    # Provide a code but a wrong state — session has no stored state
    response = client.get(
        "/auth/tiktok/callback?code=testcode&state=wrongstate",
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    assert "error=invalid_state" in response.headers["location"]


def test_google_login_redirects():
    """Google login must redirect to accounts.google.com."""
    response = client.get("/auth/google", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "accounts.google.com" in response.headers["location"]


def test_get_me_unauthenticated_returns_401():
    """Unauthenticated /auth/me should return 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_logout_clears_session():
    """POST /auth/logout should return 200 with success message."""
    response = client.post("/auth/logout")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_privacy_redirect():
    """GET /privacy should redirect to the hosted privacy policy."""
    response = client.get("/privacy", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "privacy" in response.headers["location"].lower()


def test_tos_redirect():
    """GET /tos should redirect to the hosted terms of service."""
    response = client.get("/tos", follow_redirects=False)
    assert response.status_code in (302, 307)


def test_refresh_token_without_session_returns_401():
    """POST /auth/tiktok/refresh without a refresh token in session should return 401."""
    response = client.post("/auth/tiktok/refresh")
    assert response.status_code == 401
