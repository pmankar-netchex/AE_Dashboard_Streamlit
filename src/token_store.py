"""Per-user server-side session/token storage."""
from __future__ import annotations
import json
import logging
import secrets
from pathlib import Path

log = logging.getLogger(__name__)

_SESSION_DIR = Path(__file__).resolve().parent.parent / ".sessions"


def _ensure_dir():
    _SESSION_DIR.mkdir(exist_ok=True)


def create_session(oauth_data: dict) -> str:
    """Store OAuth tokens server-side and return a new session ID."""
    _ensure_dir()
    session_id = secrets.token_urlsafe(32)
    path = _SESSION_DIR / f"{session_id}.json"
    path.write_text(json.dumps(oauth_data))
    return session_id


def load_session(session_id: str) -> dict | None:
    """Load stored OAuth tokens for a session ID."""
    if not session_id:
        return None
    if "/" in session_id or "\\" in session_id or ".." in session_id:
        return None
    path = _SESSION_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load session %s: %s", session_id, e)
        return None


def update_session(session_id: str, oauth_data: dict):
    """Update stored tokens (e.g. after access token refresh)."""
    if not session_id:
        return
    _ensure_dir()
    path = _SESSION_DIR / f"{session_id}.json"
    path.write_text(json.dumps(oauth_data))


def delete_session(session_id: str):
    """Remove a stored session."""
    if not session_id:
        return
    if "/" in session_id or "\\" in session_id or ".." in session_id:
        return
    path = _SESSION_DIR / f"{session_id}.json"
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
