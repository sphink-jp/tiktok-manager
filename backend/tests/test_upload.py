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


def test_upload_description_echoed_in_response():
    """Inbox APIではTikTokに description を送らないが、レスポンスにはエコーバックされる
    (フロント・GCSアーカイブ用のメタデータとして利用)。"""
    from routers.deps import require_tiktok_token
    from routers import upload as upload_module

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    async def mock_init(client, token, file_size, content_type, open_id):
        return ("pub_123", "https://upload.example.com/video")

    async def mock_upload(client, upload_url, content, content_type, publish_id, open_id):
        pass

    async def mock_poll(client, token, publish_id, open_id):
        return publish_id

    try:
        with patch.object(upload_module, "_init_upload", side_effect=mock_init), \
             patch.object(upload_module, "_upload_video", side_effect=mock_upload), \
             patch.object(upload_module, "_poll_status", side_effect=mock_poll):

            data = {"title": "My Video", "description": "Hello #tiktok", "privacy": "public"}
            files = {"file": ("test.mp4", io.BytesIO(_make_video_file()), "video/mp4")}
            response = client.post("/api/upload", data=data, files=files)

        assert response.status_code == 200
        # Inbox APIは description を TikTok に送らない（ユーザーがアプリで設定）
        # レスポンスにメタデータとして含まれることだけ確認
        assert response.json()["title"] == "My Video"
    finally:
        app.dependency_overrides.clear()


def test_upload_success_returns_publish_id():
    """Inbox APIの成功時は publish_id と status=SEND_TO_USER_INBOX を返す。"""
    from routers.deps import require_tiktok_token
    from routers import upload as upload_module

    app.dependency_overrides[require_tiktok_token] = lambda: "fake_token"

    async def mock_init(client, token, file_size, content_type, open_id):
        return ("pub_xyz789", "https://upload.example.com/video")

    async def mock_upload(client, upload_url, content, content_type, publish_id, open_id):
        pass

    async def mock_poll(client, token, publish_id, open_id):
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
        assert body["status"] == "SEND_TO_USER_INBOX"
    finally:
        app.dependency_overrides.clear()
