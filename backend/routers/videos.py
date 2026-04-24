import httpx
from fastapi import APIRouter, Depends, HTTPException

from routers.deps import require_tiktok_token

TIKTOK_VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"
TIKTOK_VIDEO_LIST_FIELDS = "id,title,create_time,cover_image_url,share_url,video_description,duration,view_count,like_count,comment_count,share_count"

router = APIRouter(prefix="/api", tags=["videos"])


@router.get("/videos")
async def list_videos(
    max_count: int = 20,
    cursor: str = "",
    token: str = Depends(require_tiktok_token),
) -> dict:
    """Fetch the user's TikTok video list via the TikTok Content Posting API."""
    payload: dict = {"max_count": max_count}
    if cursor:
        payload["cursor"] = cursor

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{TIKTOK_VIDEO_LIST_URL}?fields={TIKTOK_VIDEO_LIST_FIELDS}",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="TikTok token expired or invalid")

    if not resp.content or resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="TikTok API error")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    error_info = data.get("error", {})
    if error_info.get("code", "ok") != "ok":
        raise HTTPException(
            status_code=502,
            detail=f"TikTok error [{error_info.get('code')}]: {error_info.get('message')}",
        )

    result = data.get("data", {})
    videos = result.get("videos", [])
    tiktok_cursor = result.get("cursor", 0)
    has_more = result.get("has_more", False)

    return {
        "videos": videos,
        "cursor": str(tiktok_cursor),
        "has_more": has_more,
    }
