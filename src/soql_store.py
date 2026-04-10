"""Persistent SOQL override storage (shared across all users and sessions)."""
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_OVERRIDES_FILE = Path(__file__).resolve().parent.parent / "soql_overrides.json"


def load_overrides() -> dict:
    """Load saved SOQL overrides from disk."""
    if not _OVERRIDES_FILE.exists():
        return {}
    try:
        return json.loads(_OVERRIDES_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load SOQL overrides: %s", e)
        return {}


def save_override(col_id: str, soql: str):
    """Save a single SOQL override to disk (merges with existing)."""
    overrides = load_overrides()
    overrides[col_id] = soql
    _OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))
