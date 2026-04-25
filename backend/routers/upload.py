import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

from routers.deps import require_tiktok_token

logger = logging.getLogger(__name__)

# Thread pool for GCS I/O (synchronous google-cloud-storage library)
_gcs_executor = ThreadPoolExecutor(max_workers=2)

router = APIRouter(prefix="/api", tags=["upload"])

# Maximum allowed upload size: 500 MB
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

# Inbox Upload API: video.upload scopeで利用可（TikTokアプリの下書きにアップロード）
# Direct Post API (/v2/post/publish/video/init/) は video.publish scope (App Review必須)
# のため未使用。承認取れたらDirect Postに切り替え検討。
TIKTOK_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# Inbox APIではタイトル等は設定できない（ユーザーがTikTokアプリ側で設定）
# privacy指定もユーザー側に委ねる
PRIVACY_LEVEL_MAP: dict[str, str] = {
    "public": "PUBLIC_TO_EVERYONE",
    "friends": "MUTUAL_FOLLOW_FRIENDS",
    "private": "SELF_ONLY",
}

# Polling: 6 attempts × 5 seconds = 30 seconds max
POLL_ATTEMPTS = 6
POLL_INTERVAL_SECONDS = 5


async def _init_upload(
    client: httpx.AsyncClient,
    token: str,
    file_size: int,
    content_type: str,
    open_id: str,
) -> tuple[str, str]:
    """Step 1: Call TikTok Inbox init endpoint, return (publish_id, upload_url).

    Inbox APIは post_info を持たない。タイトル・説明・公開範囲は
    ユーザーがTikTokアプリ側で設定する。
    """
    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        },
    }
    logger.info(
        "tiktok_init_request open_id=%s file_size=%d content_type=%s",
        open_id, file_size, content_type,
    )
    response = await client.post(
        TIKTOK_INIT_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    body_text = response.text[:1000] if response.content else ""
    logger.info(
        "tiktok_init_response open_id=%s http_status=%d body=%s",
        open_id, response.status_code, body_text,
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

    # upload_url にはアップ用の認証付きURLパラメータが付くので末尾だけログ
    logger.info(
        "tiktok_init_success open_id=%s publish_id=%s upload_url_host=%s",
        open_id, publish_id, upload_url.split("?")[0][:80],
    )
    return publish_id, upload_url


async def _upload_video(
    client: httpx.AsyncClient,
    upload_url: str,
    content: bytes,
    content_type: str,
    publish_id: str,
    open_id: str,
) -> None:
    """Step 2: PUT raw video bytes to TikTok's upload URL."""
    file_size = len(content)
    logger.info(
        "tiktok_put_request open_id=%s publish_id=%s file_size=%d",
        open_id, publish_id, file_size,
    )
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
    logger.info(
        "tiktok_put_response open_id=%s publish_id=%s http_status=%d resp_body=%s",
        open_id, publish_id, response.status_code, response.text[:500] if response.content else "",
    )
    if response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=502, detail="TikTokへの動画アップロードに失敗しました")


async def _poll_status(
    client: httpx.AsyncClient,
    token: str,
    publish_id: str,
    open_id: str,
) -> str:
    """Step 3: Poll until SEND_TO_USER_INBOX (Inbox APIの最終状態) or failure.

    Inbox APIでは「公開完了」ではなく「ユーザーのInboxに届いた」が成功状態。
    """
    last_status = ""
    last_body = ""
    for attempt in range(1, POLL_ATTEMPTS + 1):
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
        last_body = response.text[:500] if response.content else ""
        if response.status_code != 200:
            logger.warning(
                "tiktok_poll_http_error attempt=%d/%d open_id=%s publish_id=%s http_status=%d body=%s",
                attempt, POLL_ATTEMPTS, open_id, publish_id, response.status_code, last_body,
            )
            continue

        data = response.json().get("data", {})
        last_status = data.get("status", "")
        logger.info(
            "tiktok_poll attempt=%d/%d open_id=%s publish_id=%s status=%s body=%s",
            attempt, POLL_ATTEMPTS, open_id, publish_id, last_status, last_body,
        )

        # Inbox API の成功状態
        if last_status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            logger.info(
                "tiktok_publish_done open_id=%s publish_id=%s final_status=%s",
                open_id, publish_id, last_status,
            )
            return publish_id
        if last_status == "FAILED":
            fail_reason = data.get("fail_reason", "不明なエラー")
            logger.error(
                "tiktok_publish_failed open_id=%s publish_id=%s fail_reason=%s",
                open_id, publish_id, fail_reason,
            )
            raise HTTPException(status_code=502, detail=f"TikTokアップロード失敗: {fail_reason}")

    logger.warning(
        "tiktok_poll_timeout open_id=%s publish_id=%s last_status=%s last_body=%s",
        open_id, publish_id, last_status, last_body,
    )
    raise HTTPException(
        status_code=504,
        detail=f"TikTokの処理がタイムアウトしました(last_status={last_status or 'unknown'})。"
               f"後ほどTikTokアプリの下書き(Inbox)で確認してください。"
               f"Sandbox状態だとAPI成功でもInboxに届かない既知の制限があります "
               f"(App Audit通過必要)",
    )


@router.post("/upload")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form("", max_length=150),
    description: str = Form("", max_length=2200),
    privacy: str = Form("public"),
    token: str = Depends(require_tiktok_token),
) -> dict:
    """Upload a video to TikTok Inbox (video.upload scope, 3-step flow).

    Inbox APIなので動画はTikTokアプリの下書きに送られる。
    タイトル・説明・公開範囲はユーザーがTikTokアプリ側で最終決定する。
    （ここで受け取る title/description/privacy はGCSアーカイブ時のメタデータ用）
    """
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

    if len(content) == 0:
        raise HTTPException(status_code=422, detail="空のファイルはアップロードできません")

    mime_type = file.content_type or "video/mp4"

    # 診断ログ用に open_id を取り出す（無くても続行）
    open_id = (request.session.get("user") or {}).get("open_id") or "unknown"

    logger.info(
        "upload_start open_id=%s filename=%s file_size=%d mime=%s title_len=%d desc_len=%d privacy=%s",
        open_id, file.filename, len(content), mime_type, len(title), len(description), privacy,
    )

    async with httpx.AsyncClient() as client:
        publish_id, upload_url = await _init_upload(
            client, token, len(content), mime_type, open_id,
        )
        await _upload_video(client, upload_url, content, mime_type, publish_id, open_id)
        await _poll_status(client, token, publish_id, open_id)

    # Archive video to GCS after successful TikTok inbox upload (best-effort, non-blocking)
    gcs_uri: str | None = None
    try:
        import gcs as gcs_module
        loop = asyncio.get_event_loop()
        ext = (file.filename or "video.mp4").rsplit(".", 1)[-1] if file.filename else "mp4"
        blob_name = f"tiktok-uploads/{publish_id}-{uuid.uuid4().hex[:8]}.{ext}"
        gcs_uri = await loop.run_in_executor(
            _gcs_executor,
            lambda: gcs_module.upload_video(content, blob_name, mime_type),
        )
        logger.info("Video archived to GCS: %s", gcs_uri)
    except Exception as exc:
        # GCS failure must not break the upload response — just log it
        logger.warning("GCS archive failed (non-fatal): %s", exc)

    return {
        "publish_id": publish_id,
        "title": title,
        "privacy": privacy,
        "status": "SEND_TO_USER_INBOX",
        "message": "TikTokアプリの下書き(Inbox)に動画を送信しました。アプリで開いてタイトル等を設定し投稿を完了してください",
        "gcs_uri": gcs_uri,
    }
