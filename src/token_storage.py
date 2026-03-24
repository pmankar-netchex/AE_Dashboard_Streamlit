"""
Persistent token storage for Salesforce OAuth.
Stores refresh tokens locally so users don't have to re-authenticate every session.

Backends:
  - Filesystem (default): ~/.salesforce_tokens/ae_dashboard.json (0o600 perms)
  - Azure Key Vault: when KEY_VAULT_NAME env var is set; secret name: salesforce-tokens
"""
import os
import json
from pathlib import Path


TOKEN_FILE = Path.home() / ".salesforce_tokens" / "ae_dashboard.json"

# Key Vault secret name (single JSON-encoded secret, same schema as filesystem)
_KV_SECRET_NAME = "salesforce-tokens"

# Lazily-initialised Key Vault client — created once on first KV use
_kv_client = None


def _get_kv_client():
    """Return a cached SecretClient, creating it on first call.

    Azure SDK packages are imported only inside this function so they are never
    loaded when KEY_VAULT_NAME is not set (filesystem-only mode).
    """
    global _kv_client
    if _kv_client is not None:
        return _kv_client

    from azure.identity import DefaultAzureCredential          # lazy import
    from azure.keyvault.secrets import SecretClient            # lazy import

    key_vault_name = os.environ["KEY_VAULT_NAME"]
    vault_url = f"https://{key_vault_name}.vault.azure.net"
    # Exclude EnvironmentCredential — AZURE_CLIENT_ID/SECRET env vars are for MSAL
    # (the app registration), not the managed identity that has Key Vault access.
    _kv_client = SecretClient(
        vault_url=vault_url,
        credential=DefaultAzureCredential(exclude_environment_credential=True),
    )
    return _kv_client


def _use_key_vault() -> bool:
    """Return True when Key Vault mode is active (KEY_VAULT_NAME env var is set)."""
    return bool(os.environ.get("KEY_VAULT_NAME"))


# =============================================================================
# Public API — signatures unchanged
# =============================================================================

def save_tokens(access_token: str, refresh_token: str, instance_url: str):
    """
    Save OAuth tokens to persistent storage.

    Args:
        access_token: Current access token (expires after ~2 hours)
        refresh_token: Refresh token (long-lived, used to get new access tokens)
        instance_url: Salesforce instance URL
    """
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "instance_url": instance_url,
    }

    if _use_key_vault():
        client = _get_kv_client()
        client.set_secret(_KV_SECRET_NAME, json.dumps(data))
    else:
        # Filesystem backend (default)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps(data, indent=2))
        TOKEN_FILE.chmod(0o600)  # rw------- (owner only)


def load_tokens() -> dict:
    """
    Load saved OAuth tokens from persistent storage.

    Returns:
        dict with keys: access_token, refresh_token, instance_url
        Empty dict if no tokens saved or secret/file doesn't exist
    """
    if _use_key_vault():
        from azure.core.exceptions import ResourceNotFoundError  # lazy import

        try:
            client = _get_kv_client()
            secret_value = client.get_secret(_KV_SECRET_NAME).value
            data = json.loads(secret_value)
            if all(k in data for k in ["access_token", "refresh_token", "instance_url"]):
                return data
        except ResourceNotFoundError:
            return {}
        except (json.JSONDecodeError, Exception):
            pass
        return {}
    else:
        # Filesystem backend (default)
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
    if _use_key_vault():
        from azure.core.exceptions import ResourceNotFoundError  # lazy import

        try:
            client = _get_kv_client()
            client.begin_delete_secret(_KV_SECRET_NAME)
        except ResourceNotFoundError:
            pass  # Already absent — treat as success
    else:
        # Filesystem backend (default)
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
