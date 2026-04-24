"""Shared FastAPI dependencies for TikTok Manager routers."""
from fastapi import HTTPException, Request


def require_tiktok_token(request: Request) -> str:
    """Dependency: return TikTok access token from session, or raise 401."""
    token = request.session.get("tiktok_access_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="TikTok認証が必要です。設定ページからTikTokアカウントと連携してください。",
        )
    return token
