import os
import secrets
import time
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
async def google_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=oauth_failed")

    stored_state = request.session.pop("google_oauth_state", None)
    if not stored_state or stored_state != state:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=invalid_state")

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
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=userinfo_failed")

        user_info = user_res.json()

    expires_at = time.time() + int(expires_in) if expires_in else None

    request.session["user"] = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "auth_provider": "google",
    }
    request.session["google_access_token"] = access_token
    if refresh_token:
        request.session["google_refresh_token"] = refresh_token
    if expires_at:
        request.session["google_token_expires_at"] = expires_at

    return RedirectResponse(FRONTEND_ORIGIN)


@router.post("/google/refresh")
async def google_refresh(request: Request) -> dict:
    """Refresh Google access token using stored refresh token."""
    refresh_token = request.session.get("google_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No Google refresh token in session")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

    if token_res.status_code != 200:
        raise HTTPException(status_code=401, detail="Google token refresh failed")

    tokens = token_res.json()
    new_access_token = tokens.get("access_token")
    new_expires_in = tokens.get("expires_in", 3600)
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Google token refresh returned no token")

    expires_at = time.time() + int(new_expires_in)
    request.session["google_access_token"] = new_access_token
    request.session["google_token_expires_at"] = expires_at

    return {"access_token": new_access_token, "expires_at": expires_at}


@router.get("/tiktok")
async def tiktok_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    request.session["tiktok_oauth_state"] = state
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "response_type": "code",
        "scope": "user.info.basic",
        "state": state,
    }
    return RedirectResponse(f"{TIKTOK_AUTH_URL}?{urlencode(params)}")


@router.get("/tiktok/callback")
async def tiktok_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=oauth_failed")

    stored_state = request.session.pop("tiktok_oauth_state", None)
    if not stored_state or stored_state != state:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?error=invalid_state")

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

    expires_at: float | None = None
    if expires_in:
        expires_at = time.time() + int(expires_in)

    request.session["user"] = {
        "open_id": open_id,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "auth_provider": "tiktok",
    }
    request.session["tiktok_access_token"] = access_token
    if refresh_token:
        request.session["tiktok_refresh_token"] = refresh_token
    if expires_in:
        request.session["tiktok_token_expires_in"] = expires_in
    if expires_at is not None:
        request.session["tiktok_token_expires_at"] = expires_at

    return RedirectResponse(FRONTEND_ORIGIN)


@router.post("/tiktok/refresh")
async def tiktok_refresh(request: Request) -> dict:
    """Refresh TikTok access token using stored refresh token."""
    refresh_token = request.session.get("tiktok_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No TikTok refresh token in session")

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

    if token_res.status_code != 200:
        raise HTTPException(status_code=401, detail="TikTok token refresh failed")

    tokens = token_res.json()
    new_access_token = tokens.get("access_token")
    new_refresh_token = tokens.get("refresh_token")
    new_expires_in = tokens.get("expires_in", 86400)
    if not new_access_token:
        raise HTTPException(status_code=401, detail="TikTok token refresh returned no token")

    expires_at = time.time() + int(new_expires_in)
    request.session["tiktok_access_token"] = new_access_token
    if new_refresh_token:
        request.session["tiktok_refresh_token"] = new_refresh_token
    request.session["tiktok_token_expires_in"] = new_expires_in
    request.session["tiktok_token_expires_at"] = expires_at

    # Update DB if we have open_id in session
    open_id = (request.session.get("user") or {}).get("open_id")
    if open_id:
        upsert_user(
            open_id=open_id,
            display_name="",
            avatar_url="",
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=new_expires_in,
        )

    return {"access_token": new_access_token, "expires_at": expires_at}


@router.get("/me")
async def get_me(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    has_tiktok = bool(request.session.get("tiktok_access_token"))
    tiktok_expires_at = request.session.get("tiktok_token_expires_at")

    return {
        **user,
        "has_tiktok": has_tiktok,
        "tiktok_token_expires_at": tiktok_expires_at,
    }


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
