import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

router = APIRouter(prefix="/api", tags=["videos"])

TIKTOK_VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"
VIDEO_FIELDS = (
    "id,title,create_time,cover_image_url,share_url,"
    "view_count,like_count,comment_count,share_count,duration,height,width"
)


def require_tiktok_token(request: Request) -> str:
    """Dependency: return TikTok access token from session, or raise 401."""
    token = request.session.get("tiktok_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="TikTok認証が必要です")
    return token


@router.get("/videos")
async def list_videos(
    token: str = Depends(require_tiktok_token),
) -> dict:
    """Fetch the authenticated user's TikTok video list (up to 20 videos)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TIKTOK_VIDEO_LIST_URL}?fields={VIDEO_FIELDS}",
            json={"max_count": 20},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="TikTokトークンが無効または期限切れです")

    if response.status_code != 200:
        body = response.json() if response.content else {}
        detail = body.get("error", {}).get("message", "TikTok動画一覧の取得に失敗しました")
        raise HTTPException(status_code=502, detail=detail)

    return response.json()
