"""Tests for videos router: auth guard, TikTok API integration."""
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("HTTPS_ONLY", "false")

from main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def test_list_videos_requires_tiktok_auth():
    """GET /api/videos without TikTok session token should return 401."""
    response = client.get("/api/videos")
    assert response.status_code == 401


def test_list_videos_returns_tiktok_response():
    """GET /api/videos should return transformed video list with cursor and has_more."""
    from routers.deps import require_tiktok_token

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    mock_tiktok_response = {
        "data": {
            "videos": [
                {
                    "id": "vid_001",
                    "title": "My TikTok",
                    "create_time": 1700000000,
                    "view_count": 12345,
                    "like_count": 500,
                    "comment_count": 30,
                    "share_count": 10,
                }
            ],
            "cursor": 0,
            "has_more": False,
        },
        "error": {"code": "ok", "message": "", "log_id": ""},
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"content"
    mock_response.json.return_value = mock_tiktok_response

    try:
        with patch("routers.videos.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.post.return_value = mock_response

            response = client.get("/api/videos")

        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        assert len(data["videos"]) == 1
        assert data["videos"][0]["id"] == "vid_001"
        assert "cursor" in data
        assert "has_more" in data
        assert data["has_more"] is False
    finally:
        app.dependency_overrides.clear()


def test_list_videos_tiktok_401_returns_401():
    """When TikTok returns 401, the endpoint should propagate 401."""
    from routers.deps import require_tiktok_token

    app.dependency_overrides[require_tiktok_token] = lambda: "expired_token"

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.content = b""

    try:
        with patch("routers.videos.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.post.return_value = mock_response

            response = client.get("/api/videos")

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_list_videos_tiktok_502_returns_502():
    """When TikTok returns 5xx, the endpoint should return 502."""
    from routers.deps import require_tiktok_token

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.content = b'{"error": {"message": "Service unavailable"}}'
    mock_response.json.return_value = {"error": {"message": "Service unavailable"}}

    try:
        with patch("routers.videos.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.post.return_value = mock_response

            response = client.get("/api/videos")

        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_list_videos_passes_cursor_param():
    """cursor query param should be forwarded in the TikTok request body."""
    from routers.deps import require_tiktok_token

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    mock_tiktok_response = {
        "data": {"videos": [], "cursor": 99, "has_more": False},
        "error": {"code": "ok", "message": "", "log_id": ""},
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"content"
    mock_response.json.return_value = mock_tiktok_response

    try:
        with patch("routers.videos.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.post.return_value = mock_response

            response = client.get("/api/videos?cursor=abc123")

        assert response.status_code == 200
        call_kwargs = mock_client_instance.post.call_args
        assert call_kwargs.kwargs["json"]["cursor"] == "abc123"
    finally:
        app.dependency_overrides.clear()


def test_list_videos_has_more_true():
    """has_more flag from TikTok should be reflected in the response."""
    from routers.deps import require_tiktok_token

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    mock_tiktok_response = {
        "data": {
            "videos": [{"id": "v1", "title": "A"}],
            "cursor": 999,
            "has_more": True,
        },
        "error": {"code": "ok", "message": "", "log_id": ""},
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"content"
    mock_response.json.return_value = mock_tiktok_response

    try:
        with patch("routers.videos.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.post.return_value = mock_response

            response = client.get("/api/videos")

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True
        assert data["cursor"] == "999"
    finally:
        app.dependency_overrides.clear()
