import os
import secrets
import time
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8000/auth/tiktok/callback")

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
# video.publish is required for Content Posting API v2 (video.upload is the legacy scope)
TIKTOK_SCOPES = "user.info.basic,video.list,video.publish"
TIKTOK_USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,avatar_url"

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
async def google_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Google's OAuth2 consent screen."""
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
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Exchange the authorization code for tokens, fetch user info, save to session."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=oauth_failed")

    expected_state = request.session.pop("google_oauth_state", None)
    if not state or state != expected_state:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=invalid_state")

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
            return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=token_exchange_failed")

        tokens = token_res.json()
        access_token = tokens.get("access_token")
        google_refresh_token = tokens.get("refresh_token")

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=userinfo_failed")

        user_info = user_res.json()

    request.session["user"] = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "auth_provider": "google",
    }
    request.session["google_access_token"] = access_token
    if google_refresh_token:
        request.session["google_refresh_token"] = google_refresh_token

    return RedirectResponse(f"{FRONTEND_ORIGIN}/dashboard")


@router.post("/google/refresh")
async def google_refresh_token(request: Request) -> dict:
    """Refresh Google access token using the stored refresh token."""
    refresh_token = request.session.get("google_refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Googleリフレッシュトークンがありません。再度ログインしてください。",
        )

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
        body = token_res.json() if token_res.content else {}
        detail = body.get("error_description", "Googleトークンのリフレッシュに失敗しました")
        raise HTTPException(status_code=502, detail=detail)

    tokens = token_res.json()
    new_access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in", 3600)

    if not new_access_token:
        raise HTTPException(status_code=502, detail="新しいアクセストークンを取得できませんでした")

    request.session["google_access_token"] = new_access_token

    return {"message": "Googleトークンを更新しました", "expires_in": expires_in}


@router.get("/tiktok")
async def tiktok_login(request: Request) -> RedirectResponse:
    """Redirect the browser to TikTok's OAuth2 consent screen."""
    state = secrets.token_urlsafe(32)
    request.session["tiktok_oauth_state"] = state
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "response_type": "code",
        "scope": TIKTOK_SCOPES,
        "state": state,
    }
    url = f"{TIKTOK_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/tiktok/callback")
async def tiktok_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Exchange the authorization code for tokens, fetch TikTok user info, save to session."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=oauth_failed")

    expected_state = request.session.pop("tiktok_oauth_state", None)
    if not state or state != expected_state:
        return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=invalid_state")

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
            return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=token_exchange_failed")

        tokens = token_res.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 86400)

        user_res = await client.get(
            TIKTOK_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            return RedirectResponse(f"{FRONTEND_ORIGIN}/login?error=userinfo_failed")

        user_data = user_res.json().get("data", {}).get("user", {})

    request.session["user"] = {
        "open_id": user_data.get("open_id"),
        "display_name": user_data.get("display_name"),
        "avatar_url": user_data.get("avatar_url"),
        "auth_provider": "tiktok",
    }
    # Store TikTok tokens so upload/video endpoints can use them
    request.session["tiktok_access_token"] = access_token
    if refresh_token:
        request.session["tiktok_refresh_token"] = refresh_token
    request.session["tiktok_token_expires_in"] = expires_in
    request.session["tiktok_token_expires_at"] = time.time() + expires_in

    return RedirectResponse(f"{FRONTEND_ORIGIN}/dashboard")


@router.post("/tiktok/refresh")
async def tiktok_refresh_token(request: Request) -> dict:
    """Refresh TikTok access token using the stored refresh token."""
    refresh_token = request.session.get("tiktok_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="リフレッシュトークンがありません。再度TikTokログインしてください。")

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
        body = token_res.json() if token_res.content else {}
        detail = body.get("error_description", "トークンのリフレッシュに失敗しました")
        raise HTTPException(status_code=502, detail=detail)

    tokens = token_res.json()
    new_access_token = tokens.get("access_token")
    new_refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 86400)

    if not new_access_token:
        raise HTTPException(status_code=502, detail="新しいアクセストークンを取得できませんでした")

    request.session["tiktok_access_token"] = new_access_token
    if new_refresh_token:
        request.session["tiktok_refresh_token"] = new_refresh_token
    request.session["tiktok_token_expires_in"] = expires_in
    request.session["tiktok_token_expires_at"] = time.time() + expires_in

    return {"message": "トークンを更新しました", "expires_in": expires_in}


@router.get("/me")
async def get_me(request: Request) -> dict:
    """Return the currently logged-in user, or 401 if not authenticated."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    has_tiktok = bool(request.session.get("tiktok_access_token"))
    return {
        **user,
        "has_tiktok": has_tiktok,
        "tiktok_token_expires_at": request.session.get("tiktok_token_expires_at"),
    }


@router.post("/logout")
async def logout(request: Request) -> dict:
    """Clear the session."""
    request.session.clear()
    return {"message": "Logged out successfully"}


# Top-level redirect routes (registered without /auth prefix)
top_router = APIRouter(tags=["legal"])


@top_router.get("/privacy")
async def privacy_redirect() -> RedirectResponse:
    """Redirect to hosted privacy policy page."""
    return RedirectResponse("https://storage.googleapis.com/ichinoclaude-static/privacy.html")


@top_router.get("/tos")
async def tos_redirect() -> RedirectResponse:
    """Redirect to hosted terms of service page."""
    return RedirectResponse("https://storage.googleapis.com/ichinoclaude-static/tos.html")
