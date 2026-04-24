import os
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from database import (
    create_video_record,
    get_user_by_open_id,
    get_video_by_publish_id,
    get_videos_by_user,
    refresh_access_token,
    update_video_publish_id,
    update_video_status,
    update_video_status_by_id,
)

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")

TIKTOK_PUBLISH_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_PUBLISH_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

router = APIRouter(prefix="/api/videos", tags=["videos"])


class PublishRequest(BaseModel):
    video_url: str
    caption: str = ""
    privacy: str = "PUBLIC_TO_EVERYONE"


def _require_tiktok_auth(request: Request) -> dict:
    user = request.session.get("user")
    if not user or user.get("auth_provider") != "tiktok":
        raise HTTPException(status_code=401, detail="TikTok authentication required")
    return user


async def _valid_token(open_id: str) -> str:
    """Return a valid access token, refreshing from TikTok if expiry is near (<5 min)."""
    user = get_user_by_open_id(open_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found in database. Please re-login.")

    expires_at = user.get("token_expires_at")
    if expires_at and int(time.time()) > expires_at - 300:
        new_token = await refresh_access_token(open_id, TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET)
        if new_token:
            return new_token

    return user["access_token"]


@router.post("/publish")
async def publish_video(
    body: PublishRequest,
    session_user: dict = Depends(_require_tiktok_auth),
) -> dict:
    """Submit a video to TikTok via Content Posting API (Pull from URL)."""
    open_id: str = session_user["open_id"]

    db_user = get_user_by_open_id(open_id)
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found in database. Please re-login.")

    access_token = await _valid_token(open_id)
    video_id = create_video_record(db_user["id"], body.video_url, body.caption)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            TIKTOK_PUBLISH_INIT_URL,
            json={
                "post_info": {
                    "title": body.caption[:150],
                    "privacy_level": body.privacy,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": body.video_url,
                },
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
        )

    if resp.status_code != 200:
        update_video_status_by_id(video_id, "failed")
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"TikTok API error: {resp.text}",
        )

    data = resp.json()
    error_info = data.get("error", {})
    if error_info.get("code", "ok") != "ok":
        update_video_status_by_id(video_id, "failed")
        raise HTTPException(
            status_code=400,
            detail=f"TikTok error [{error_info.get('code')}]: {error_info.get('message')}",
        )

    publish_id: str = data.get("data", {}).get("publish_id", "")
    update_video_publish_id(video_id, publish_id, "processing")

    return {"publish_id": publish_id, "status": "processing", "video_db_id": video_id}


@router.get("/status/{publish_id}")
async def get_publish_status(
    publish_id: str,
    session_user: dict = Depends(_require_tiktok_auth),
) -> dict:
    """Fetch current publish status from TikTok and sync to DB."""
    open_id: str = session_user["open_id"]
    access_token = await _valid_token(open_id)
    local_record = get_video_by_publish_id(publish_id)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            TIKTOK_PUBLISH_STATUS_URL,
            json={"publish_id": publish_id},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        tiktok_status: str = data.get("data", {}).get("status", "unknown").lower()
        update_video_status(publish_id, tiktok_status)
        return {
            "publish_id": publish_id,
            "tiktok_status": tiktok_status,
            "local_record": local_record,
        }

    return {"publish_id": publish_id, "local_record": local_record, "tiktok_error": resp.text}


@router.get("/list")
async def list_videos(session_user: dict = Depends(_require_tiktok_auth)) -> list[dict]:
    """Return the last 50 videos for the logged-in TikTok user."""
    open_id: str = session_user["open_id"]
    db_user = get_user_by_open_id(open_id)
    if not db_user:
        return []
    return get_videos_by_user(db_user["id"])
