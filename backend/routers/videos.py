import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from routers.deps import require_tiktok_token

router = APIRouter(prefix="/api", tags=["videos"])

TIKTOK_VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"
VIDEO_FIELDS = (
    "id,title,create_time,cover_image_url,share_url,"
    "view_count,like_count,comment_count,share_count,duration,height,width"
)


@router.get("/videos")
async def list_videos(
    max_count: int = Query(default=20, ge=1, le=20),
    cursor: str | None = Query(default=None),
    token: str = Depends(require_tiktok_token),
) -> dict:
    req_body: dict = {"max_count": max_count}
    if cursor is not None:
        try:
            req_body["cursor"] = int(cursor)
        except ValueError:
            req_body["cursor"] = cursor

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TIKTOK_VIDEO_LIST_URL}?fields={VIDEO_FIELDS}",
            json=req_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="TikTokトークンが無効または期限切れです。設定ページから再ログインしてください。",
        )

    if response.status_code != 200:
        err_body = response.json() if response.content else {}
        detail = err_body.get("error", {}).get("message", "TikTok動画一覧の取得に失敗しました")
        raise HTTPException(status_code=502, detail=detail)

    tiktok_data = response.json().get("data", {})
    return {
        "videos": tiktok_data.get("videos", []),
        "cursor": str(tiktok_data.get("cursor", "")),
        "has_more": bool(tiktok_data.get("has_more", False)),
    }
