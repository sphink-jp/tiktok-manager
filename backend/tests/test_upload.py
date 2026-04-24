"""Tests for upload router: validation, auth guard, API flow."""
import io
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("HTTPS_ONLY", "false")

from main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def _make_video_file(size: int = 1024) -> bytes:
    return b"\x00" * size


def test_upload_requires_tiktok_auth():
    """Upload without TikTok session token should return 401."""
    data = {"title": "Test Video", "privacy": "public"}
    files = {"file": ("test.mp4", io.BytesIO(_make_video_file()), "video/mp4")}
    response = client.post("/api/upload", data=data, files=files)
    assert response.status_code == 401


def test_upload_non_video_returns_422():
    """Uploading a non-video file should return 422."""
    # Inject a fake session token to bypass auth
    with client as c:
        # Manually set session by calling a mocked endpoint is complex;
        # instead patch the dependency
        pass

    from routers.deps import require_tiktok_token
    from fastapi import Request

    # Override dependency to simulate authenticated TikTok session
    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    try:
        data = {"title": "Test", "privacy": "public"}
        files = {"file": ("image.jpg", io.BytesIO(b"JFIF"), "image/jpeg")}
        response = client.post("/api/upload", data=data, files=files)
        assert response.status_code == 422
        assert "動画" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_upload_invalid_privacy_returns_422():
    """Uploading with an invalid privacy value should return 422."""
    from routers.deps import require_tiktok_token
    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    try:
        data = {"title": "Test", "privacy": "invalid_value"}
        files = {"file": ("test.mp4", io.BytesIO(_make_video_file()), "video/mp4")}
        response = client.post("/api/upload", data=data, files=files)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_upload_empty_file_returns_422():
    """Uploading an empty video file should return 422."""
    from routers.deps import require_tiktok_token
    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    try:
        data = {"title": "Test", "privacy": "public"}
        files = {"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")}
        response = client.post("/api/upload", data=data, files=files)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_upload_title_too_long_returns_422():
    """Title exceeding 150 chars at form level should be rejected."""
    from routers.deps import require_tiktok_token
    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    try:
        long_title = "a" * 151
        data = {"title": long_title, "privacy": "public"}
        files = {"file": ("test.mp4", io.BytesIO(_make_video_file()), "video/mp4")}
        response = client.post("/api/upload", data=data, files=files)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_upload_description_included_in_init_payload():
    """Description must be passed to TikTok init as video_description."""
    from routers.deps import require_tiktok_token
    from routers import upload as upload_module

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    captured_payload = {}

    async def mock_init(client, token, title, description, privacy_level, file_size, content_type):
        captured_payload["description"] = description
        return ("pub_123", "https://upload.example.com/video")

    async def mock_upload(client, upload_url, content, content_type):
        pass

    async def mock_poll(client, token, publish_id):
        return publish_id

    try:
        with patch.object(upload_module, "_init_upload", side_effect=mock_init), \
             patch.object(upload_module, "_upload_video", side_effect=mock_upload), \
             patch.object(upload_module, "_poll_status", side_effect=mock_poll):

            data = {"title": "My Video", "description": "Hello #tiktok", "privacy": "public"}
            files = {"file": ("test.mp4", io.BytesIO(_make_video_file()), "video/mp4")}
            response = client.post("/api/upload", data=data, files=files)

        assert response.status_code == 200
        assert captured_payload.get("description") == "Hello #tiktok"
    finally:
        app.dependency_overrides.clear()


def test_upload_success_returns_publish_id():
    """Successful upload should return publish_id and status PUBLISH_COMPLETE."""
    from routers.deps import require_tiktok_token
    from routers import upload as upload_module

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    async def mock_init(client, token, title, description, privacy_level, file_size, content_type):
        return ("pub_xyz789", "https://upload.example.com/video")

    async def mock_upload(client, upload_url, content, content_type):
        pass

    async def mock_poll(client, token, publish_id):
        return publish_id

    try:
        with patch.object(upload_module, "_init_upload", side_effect=mock_init), \
             patch.object(upload_module, "_upload_video", side_effect=mock_upload), \
             patch.object(upload_module, "_poll_status", side_effect=mock_poll):

            data = {"title": "Great Video", "privacy": "private"}
            files = {"file": ("test.mp4", io.BytesIO(_make_video_file()), "video/mp4")}
            response = client.post("/api/upload", data=data, files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["publish_id"] == "pub_xyz789"
        assert body["status"] == "PUBLISH_COMPLETE"
    finally:
        app.dependency_overrides.clear()
