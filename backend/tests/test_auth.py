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
    """TikTok login must request user.info.basic + video.upload scopes.

    video.upload は Inbox API（TikTokアプリの下書きへのアップロード）に必要。
    video.publish は Direct Post API用で App Review承認が必要なため未使用。
    """
    response = client.get("/auth/tiktok", follow_redirects=False)
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "user.info.basic" in location
    assert "video.upload" in location
    # video.publish は App Review承認が必要なので承認取れるまで使わない
    assert "video.publish" not in location


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


def test_google_refresh_without_session_returns_401():
    """POST /auth/google/refresh without a refresh token in session should return 401."""
    response = client.post("/auth/google/refresh")
    assert response.status_code == 401


@patch("routers.auth.httpx.AsyncClient")
def test_google_callback_saves_refresh_token_and_has_tiktok_false(mock_httpx):
    """Google callback should save refresh_token; /auth/me should return has_tiktok=False."""
    mock_token_res = MagicMock()
    mock_token_res.status_code = 200
    mock_token_res.json.return_value = {
        "access_token": "google_access_123",
        "refresh_token": "google_refresh_456",
    }

    mock_user_res = MagicMock()
    mock_user_res.status_code = 200
    mock_user_res.json.return_value = {
        "sub": "user-sub-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
    }

    mock_ctx = AsyncMock()
    mock_ctx.post = AsyncMock(return_value=mock_token_res)
    mock_ctx.get = AsyncMock(return_value=mock_user_res)
    mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

    from urllib.parse import urlparse, parse_qs

    with TestClient(app, raise_server_exceptions=False) as c:
        login_res = c.get("/auth/google", follow_redirects=False)
        location = login_res.headers["location"]
        state = parse_qs(urlparse(location).query)["state"][0]

        callback_res = c.get(
            f"/auth/google/callback?code=fake_code&state={state}",
            follow_redirects=False,
        )
        assert callback_res.status_code in (302, 307)

        me_res = c.get("/auth/me")
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["has_tiktok"] is False
        assert "tiktok_token_expires_at" in data


@patch("routers.auth.httpx.AsyncClient")
def test_tiktok_callback_saves_expires_at(mock_httpx):
    """TikTok callback should store tiktok_token_expires_at; /auth/me returns it."""
    mock_token_res = MagicMock()
    mock_token_res.status_code = 200
    mock_token_res.json.return_value = {
        "access_token": "tiktok_access_abc",
        "refresh_token": "tiktok_refresh_xyz",
        "expires_in": 86400,
    }

    mock_user_res = MagicMock()
    mock_user_res.status_code = 200
    mock_user_res.json.return_value = {
        "data": {
            "user": {
                "open_id": "tiktok-open-id-001",
                "display_name": "TikTok User",
                "avatar_url": "https://tiktok.com/avatar.jpg",
            }
        }
    }

    mock_ctx = AsyncMock()
    mock_ctx.post = AsyncMock(return_value=mock_token_res)
    mock_ctx.get = AsyncMock(return_value=mock_user_res)
    mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

    import time
    from urllib.parse import urlparse, parse_qs

    with TestClient(app, raise_server_exceptions=False) as c:
        login_res = c.get("/auth/tiktok", follow_redirects=False)
        location = login_res.headers["location"]
        state = parse_qs(urlparse(location).query)["state"][0]

        before = time.time()
        callback_res = c.get(
            f"/auth/tiktok/callback?code=fake_code&state={state}",
            follow_redirects=False,
        )
        after = time.time()
        assert callback_res.status_code in (302, 307)

        me_res = c.get("/auth/me")
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["has_tiktok"] is True
        expires_at = data["tiktok_token_expires_at"]
        assert expires_at is not None
        assert before + 86400 <= expires_at <= after + 86400
