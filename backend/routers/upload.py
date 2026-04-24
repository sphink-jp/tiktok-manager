import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

router = APIRouter(prefix="/api", tags=["upload"])

# Maximum allowed upload size: 500 MB
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

TIKTOK_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

PRIVACY_LEVEL_MAP: dict[str, str] = {
    "public": "PUBLIC_TO_EVERYONE",
    "friends": "MUTUAL_FOLLOW_FRIENDS",
    "private": "SELF_ONLY",
}

# Polling: 6 attempts × 5 seconds = 30 seconds max
POLL_ATTEMPTS = 6
POLL_INTERVAL_SECONDS = 5


def require_tiktok_token(request: Request) -> str:
    """Dependency: return TikTok access token from session, or raise 401."""
    token = request.session.get("tiktok_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="TikTok認証が必要です")
    return token


async def _init_upload(
    client: httpx.AsyncClient,
    token: str,
    title: str,
    privacy_level: str,
    file_size: int,
    content_type: str,
) -> tuple[str, str]:
    """Step 1: Call TikTok init endpoint, return (publish_id, upload_url)."""
    payload = {
        "post_info": {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        },
    }
    response = await client.post(
        TIKTOK_INIT_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    if response.status_code != 200:
        body = response.json() if response.content else {}
        detail = body.get("error", {}).get("message", "TikTok初期化に失敗しました")
        raise HTTPException(status_code=502, detail=detail)

    data = response.json().get("data", {})
    publish_id = data.get("publish_id")
    upload_url = data.get("upload_url")
    if not publish_id or not upload_url:
        raise HTTPException(status_code=502, detail="TikTokからupload_urlを取得できませんでした")

    return publish_id, upload_url


async def _upload_video(
    client: httpx.AsyncClient,
    upload_url: str,
    content: bytes,
    content_type: str,
) -> None:
    """Step 2: PUT raw video bytes to TikTok's upload URL."""
    file_size = len(content)
    response = await client.put(
        upload_url,
        content=content,
        headers={
            "Content-Type": content_type,
            "Content-Length": str(file_size),
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
        },
        timeout=300.0,
    )
    if response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=502, detail="TikTokへの動画アップロードに失敗しました")


async def _poll_status(
    client: httpx.AsyncClient,
    token: str,
    publish_id: str,
) -> str:
    """Step 3: Poll publish status until PUBLISH_COMPLETE or failure."""
    for _ in range(POLL_ATTEMPTS):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

        response = await client.post(
            TIKTOK_STATUS_URL,
            json={"publish_id": publish_id},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        if response.status_code != 200:
            continue

        data = response.json().get("data", {})
        status = data.get("status", "")

        if status == "PUBLISH_COMPLETE":
            return publish_id
        if status == "FAILED":
            fail_reason = data.get("fail_reason", "不明なエラー")
            raise HTTPException(status_code=502, detail=f"TikTok公開失敗: {fail_reason}")

    raise HTTPException(
        status_code=504,
        detail="TikTokの処理がタイムアウトしました。後ほどTikTokアプリで確認してください",
    )


@router.post("/upload")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., max_length=150),
    description: str = Form("", max_length=2200),
    privacy: str = Form("public"),
    token: str = Depends(require_tiktok_token),
) -> dict:
    """Upload a video to TikTok using Content Posting API v2 (3-step flow)."""
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=422, detail="動画ファイルをアップロードしてください")

    if privacy not in PRIVACY_LEVEL_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"privacyは {set(PRIVACY_LEVEL_MAP.keys())} のいずれかを指定してください",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="ファイルサイズが上限（500MB）を超えています")

    privacy_level = PRIVACY_LEVEL_MAP[privacy]
    mime_type = file.content_type or "video/mp4"

    async with httpx.AsyncClient() as client:
        publish_id, upload_url = await _init_upload(
            client, token, title, privacy_level, len(content), mime_type
        )
        await _upload_video(client, upload_url, content, mime_type)
        await _poll_status(client, token, publish_id)

    return {
        "publish_id": publish_id,
        "title": title,
        "privacy": privacy,
        "status": "PUBLISH_COMPLETE",
        "message": "TikTokへの投稿が完了しました",
    }
