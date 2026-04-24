import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import init_db
from routers.auth import router as auth_router
from routers.auth import top_router as legal_router
from routers.upload import router as upload_router
from routers.videos import router as videos_router

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:8080")

# Cloud Run: repo is cloned to /workspace-tiktok/; local dev: relative to this file
_default_frontend = "/workspace-tiktok/frontend"
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", _default_frontend))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TikTok Manager", version="2.0.0", lifespan=lifespan)

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="tiktok_session",
    same_site="lax",
    https_only=False,   # Cloud Run terminates TLS upstream
    max_age=60 * 60 * 24 * 7,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ─────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(legal_router)
app.include_router(upload_router)
app.include_router(videos_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


# ── Frontend static files (SPA) ─────────────────────────────────────────────
# Mounted last so API routes always take priority.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
