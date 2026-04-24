import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

router = APIRouter(prefix="/api", tags=["upload"])

# Maximum allowed upload size: 500 MB
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


def require_auth(request: Request) -> dict:
    """Dependency: raise 401 if the user is not logged in."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@router.post("/upload")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., max_length=150),
    description: str = Form("", max_length=2200),
    privacy: str = Form("public"),
    user: dict = Depends(require_auth),
) -> dict:
    """
    Receive a video file and metadata.

    Currently stores the file locally (or discards it) and returns a mock video ID.
    Replace the body with the actual TikTok Content Posting API call once credentials
    are available.
    """
    # Validate content type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=422, detail="動画ファイルをアップロードしてください")

    # Validate privacy value
    allowed_privacy = {"public", "friends", "private"}
    if privacy not in allowed_privacy:
        raise HTTPException(status_code=422, detail=f"privacyは {allowed_privacy} のいずれかを指定してください")

    # Read & size-check
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="ファイルサイズが上限（500MB）を超えています")

    # ------------------------------------------------------------------
    # TODO: Replace the block below with actual TikTok API integration.
    #
    # Example flow (TikTok Content Posting API v2):
    #   1. POST /v2/post/publish/video/init/  → get upload_url + publish_id
    #   2. PUT <upload_url> with video bytes
    #   3. GET /v2/post/publish/status/fetch/ with publish_id
    # ------------------------------------------------------------------

    video_id = str(uuid.uuid4())

    return {
        "video_id": video_id,
        "title": title,
        "privacy": privacy,
        "uploader": user["email"],
        "status": "queued",
        "message": "アップロードを受け付けました。TikTok連携は準備中です。",
    }
