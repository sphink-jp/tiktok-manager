"""Shared FastAPI dependencies for TikTok Manager routers."""
import os
import time
import httpx
from fastapi import HTTPException, Request

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

# Proactive refresh threshold: refresh token if it expires within 5 minutes
_REFRESH_THRESHOLD_SECONDS = 300


async def require_tiktok_token(request: Request) -> str:
    """Dependency: return TikTok access token from session, or raise 401.

    Auto-refreshes the token if it expires within 5 minutes.
    """
    token = request.session.get("tiktok_access_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="TikTok認証が必要です。設定ページからTikTokアカウントと連携してください。",
        )

    expires_at = request.session.get("tiktok_token_expires_at")
    if expires_at and time.time() > expires_at - _REFRESH_THRESHOLD_SECONDS:
        refresh_token = request.session.get("tiktok_refresh_token")
        if refresh_token:
            async with httpx.AsyncClient() as client:
                token_res = await client.post(
                    TIKTOK_TOKEN_URL,
                    data={
                        "client_key": TIKTOK_CLIENT_KEY,
                        "client_secret": TIKTOK_CLIENT_SECRET,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            if token_res.status_code == 200:
                tokens = token_res.json()
                new_access_token = tokens.get("access_token")
                new_refresh_token = tokens.get("refresh_token")
                new_expires_in = tokens.get("expires_in", 86400)
                if new_access_token:
                    request.session["tiktok_access_token"] = new_access_token
                    if new_refresh_token:
                        request.session["tiktok_refresh_token"] = new_refresh_token
                    request.session["tiktok_token_expires_in"] = new_expires_in
                    request.session["tiktok_token_expires_at"] = time.time() + new_expires_in
                    token = new_access_token

    return token


def require_google_token(request: Request) -> str:
    """Dependency: return Google access token from session, or raise 401."""
    token = request.session.get("google_access_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google認証が必要です。ログインしてください。",
        )
    return token
