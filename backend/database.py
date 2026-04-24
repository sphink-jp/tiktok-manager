import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

# DB path: prefer /data/, fall back to /tmp/
_data_dir = Path("/data")
if _data_dir.exists() and os.access(str(_data_dir), os.W_OK):
    DB_PATH = "/data/tiktok.db"
else:
    DB_PATH = "/tmp/tiktok.db"

# Allow override via env
_env_url = os.getenv("DATABASE_URL", "")
if _env_url.startswith("sqlite:////"):
    DB_PATH = _env_url.replace("sqlite:////", "/")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            tiktok_open_id    TEXT    UNIQUE NOT NULL,
            display_name      TEXT,
            avatar_url        TEXT,
            access_token      TEXT    NOT NULL,
            refresh_token     TEXT,
            token_expires_at  INTEGER,
            created_at        TEXT    NOT NULL,
            updated_at        TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            publish_id  TEXT,
            video_url   TEXT    NOT NULL,
            caption     TEXT,
            status      TEXT    NOT NULL DEFAULT 'pending',
            created_at  TEXT    NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def upsert_user(
    open_id: str,
    display_name: str,
    avatar_url: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
) -> int:
    """Insert or update a TikTok user record. Returns the row id."""
    now = datetime.now(timezone.utc).isoformat()
    expires_at: int | None = None
    if expires_in:
        expires_at = int(time.time()) + int(expires_in)

    conn = _connect()
    conn.execute(
        """
        INSERT INTO users
            (tiktok_open_id, display_name, avatar_url, access_token,
             refresh_token, token_expires_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tiktok_open_id) DO UPDATE SET
            display_name     = excluded.display_name,
            avatar_url       = excluded.avatar_url,
            access_token     = excluded.access_token,
            refresh_token    = COALESCE(excluded.refresh_token, refresh_token),
            token_expires_at = COALESCE(excluded.token_expires_at, token_expires_at),
            updated_at       = excluded.updated_at
        """,
        (open_id, display_name, avatar_url, access_token, refresh_token, expires_at, now, now),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM users WHERE tiktok_open_id = ?", (open_id,)).fetchone()
    user_id: int = row["id"]
    conn.close()
    return user_id


def get_user_by_open_id(open_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE tiktok_open_id = ?", (open_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


async def refresh_access_token(open_id: str, client_key: str, client_secret: str) -> str | None:
    """Refresh a user's access token via TikTok API. Returns new token or None on failure."""
    user = get_user_by_open_id(open_id)
    if not user or not user.get("refresh_token"):
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TIKTOK_TOKEN_URL,
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": user["refresh_token"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            return None

        tokens = resp.json()
        new_access_token: str | None = tokens.get("access_token")
        new_refresh_token: str | None = tokens.get("refresh_token")
        expires_in: int | None = tokens.get("expires_in")

        if not new_access_token:
            return None

        now = datetime.now(timezone.utc).isoformat()
        expires_at: int | None = None
        if expires_in:
            expires_at = int(time.time()) + int(expires_in)

        conn = _connect()
        conn.execute(
            """
            UPDATE users SET
                access_token     = ?,
                refresh_token    = COALESCE(?, refresh_token),
                token_expires_at = COALESCE(?, token_expires_at),
                updated_at       = ?
            WHERE tiktok_open_id = ?
            """,
            (new_access_token, new_refresh_token, expires_at, now, open_id),
        )
        conn.commit()
        conn.close()
        return new_access_token


def create_video_record(user_id: int, video_url: str, caption: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO videos (user_id, video_url, caption, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (user_id, video_url, caption, now),
    )
    conn.commit()
    video_id = cur.lastrowid
    conn.close()
    return video_id  # type: ignore[return-value]


def update_video_publish_id(video_id: int, publish_id: str, status: str = "processing") -> None:
    conn = _connect()
    conn.execute(
        "UPDATE videos SET publish_id = ?, status = ? WHERE id = ?",
        (publish_id, status, video_id),
    )
    conn.commit()
    conn.close()


def update_video_status(publish_id: str, status: str) -> None:
    conn = _connect()
    conn.execute("UPDATE videos SET status = ? WHERE publish_id = ?", (status, publish_id))
    conn.commit()
    conn.close()


def update_video_status_by_id(video_id: int, status: str) -> None:
    conn = _connect()
    conn.execute("UPDATE videos SET status = ? WHERE id = ?", (status, video_id))
    conn.commit()
    conn.close()


def get_videos_by_user(user_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        """
        SELECT id, publish_id, video_url, caption, status, created_at
        FROM videos WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 50
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_video_by_publish_id(publish_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM videos WHERE publish_id = ?", (publish_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
