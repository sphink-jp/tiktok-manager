import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from routers.auth import router as auth_router
from routers.auth import top_router as legal_router
from routers.upload import router as upload_router

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(title="TikTok Manager API", version="1.0.0")

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="tiktok_session",
    same_site="lax",
    https_only=True,    # Cloud Run always serves HTTPS
    max_age=60 * 60 * 24 * 7,  # 7 days
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(legal_router)
app.include_router(upload_router)

# ── Static file serving (Vue SPA) ────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    # Serve assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str) -> FileResponse:
        """
        Serve index.html for any route not matched by the API.
        This enables Vue Router's history mode to work correctly.
        """
        # Try to serve an exact static file first (favicon, robots.txt, etc.)
        candidate = STATIC_DIR / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(str(STATIC_DIR / "index.html"))
