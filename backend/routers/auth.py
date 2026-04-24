import os
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from database import upsert_user

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/google/callback")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:8080")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8080/auth/tiktok/callback")

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,avatar_url"

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
async def google_login() -> RedirectResponse:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, error: str | None = None) -> RedirectResponse:
    if error or not code:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=oauth_failed")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=token_exchange_failed")

        tokens = token_res.json()
        access_token = tokens.get("access_token")

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=userinfo_failed")

        user_info = user_res.json()

    request.session["user"] = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "auth_provider": "google",
    }

    return RedirectResponse(FRONTEND_ORIGIN)


@router.get("/tiktok")
async def tiktok_login() -> RedirectResponse:
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "response_type": "code",
        "scope": "user.info.basic,video.publish",
    }
    return RedirectResponse(f"{TIKTOK_AUTH_URL}?{urlencode(params)}")


@router.get("/tiktok/callback")
async def tiktok_callback(request: Request, code: str | None = None, error: str | None = None) -> RedirectResponse:
    if error or not code:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=oauth_failed")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            TIKTOK_TOKEN_URL,
            data={
                "code": code,
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "redirect_uri": TIKTOK_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=token_exchange_failed")

        tokens = token_res.json()
        access_token: str = tokens.get("access_token", "")
        refresh_token: str | None = tokens.get("refresh_token")
        expires_in: int | None = tokens.get("expires_in")
        token_open_id: str = tokens.get("open_id", "")

        # Fetch display name and avatar (requires user.info.basic scope)
        display_name = ""
        avatar_url = ""
        open_id = token_open_id

        user_res = await client.get(
            TIKTOK_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code == 200:
            user_data = user_res.json().get("data", {}).get("user", {})
            display_name = user_data.get("display_name", "")
            avatar_url = user_data.get("avatar_url", "")
            open_id = user_data.get("open_id") or token_open_id

    if not open_id or not access_token:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=missing_token_data")

    upsert_user(
        open_id=open_id,
        display_name=display_name,
        avatar_url=avatar_url,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )

    request.session["user"] = {
        "open_id": open_id,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "auth_provider": "tiktok",
    }
    return RedirectResponse(FRONTEND_ORIGIN)


@router.get("/me")
async def get_me(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/logout")
async def logout(request: Request) -> dict:
    request.session.clear()
    return {"message": "Logged out successfully"}


# Top-level redirects (no /auth prefix)
top_router = APIRouter(tags=["legal"])


@top_router.get("/privacy")
async def privacy_redirect() -> RedirectResponse:
    return RedirectResponse("https://storage.googleapis.com/ichinoclaude-static/privacy.html")


@top_router.get("/tos")
async def tos_redirect() -> RedirectResponse:
    return RedirectResponse("https://storage.googleapis.com/ichinoclaude-static/tos.html")
