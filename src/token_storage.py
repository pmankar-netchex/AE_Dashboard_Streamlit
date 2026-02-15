"""
Persistent token storage for Salesforce OAuth.
Stores refresh tokens locally so users don't have to re-authenticate every session.
"""
import os
import json
from pathlib import Path


TOKEN_FILE = Path.home() / ".salesforce_tokens" / "ae_dashboard.json"


def save_tokens(access_token: str, refresh_token: str, instance_url: str):
    """
    Save OAuth tokens to local storage.
    
    Args:
        access_token: Current access token (expires after ~2 hours)
        refresh_token: Refresh token (long-lived, used to get new access tokens)
        instance_url: Salesforce instance URL
    """
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "instance_url": instance_url,
    }
    
    # Write with restricted permissions (user-only read/write)
    TOKEN_FILE.write_text(json.dumps(data, indent=2))
    TOKEN_FILE.chmod(0o600)  # rw------- (owner only)


def load_tokens() -> dict:
    """
    Load saved OAuth tokens from local storage.
    
    Returns:
        dict with keys: access_token, refresh_token, instance_url
        Empty dict if no tokens saved or file doesn't exist
    """
    if not TOKEN_FILE.exists():
        return {}
    
    try:
        data = json.loads(TOKEN_FILE.read_text())
        # Validate required fields
        if all(k in data for k in ["access_token", "refresh_token", "instance_url"]):
            return data
    except (json.JSONDecodeError, IOError):
        pass
    
    return {}


def clear_tokens():
    """Delete saved tokens (logout)."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
