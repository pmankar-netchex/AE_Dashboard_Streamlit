"""
Salesforce OAuth 2.0 Web Server Flow
Similar to n8n's "Connect my account" - redirects user to Salesforce login.
"""
import os
import urllib.parse
import requests
from simple_salesforce import Salesforce


# OAuth endpoints
PRODUCTION = {
    "authorize": "https://login.salesforce.com/services/oauth2/authorize",
    "token": "https://login.salesforce.com/services/oauth2/token",
}
SANDBOX = {
    "authorize": "https://test.salesforce.com/services/oauth2/authorize",
    "token": "https://test.salesforce.com/services/oauth2/token",
}

def _get_scopes():
    """OAuth scopes - override via SALESFORCE_OAUTH_SCOPES if your org restricts."""
    return os.environ.get("SALESFORCE_OAUTH_SCOPES", "api refresh_token offline_access")


def get_oauth_config():
    """Load OAuth config from environment."""
    client_id = os.environ.get("SALESFORCE_CLIENT_ID") or os.environ.get("SALESFORCE_CONSUMER_KEY")
    client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET") or os.environ.get("SALESFORCE_CONSUMER_SECRET")
    redirect_uri = os.environ.get("SALESFORCE_REDIRECT_URI", "http://localhost:8501")
    use_sandbox = os.environ.get("SALESFORCE_SANDBOX", "").lower() in ("true", "1", "yes")

    # Custom domain overrides both authorize and token endpoints
    custom_url = os.environ.get("SALESFORCE_LOGIN_URL") or os.environ.get("SALESFORCE_DOMAIN")
    if custom_url:
        base = custom_url.rstrip("/")
        endpoints = {
            "authorize": f"{base}/services/oauth2/authorize",
            "token": f"{base}/services/oauth2/token",
        }
    else:
        endpoints = SANDBOX if use_sandbox else PRODUCTION

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "endpoints": endpoints,
    }


def is_oauth_configured():
    """Check if OAuth credentials are set."""
    config = get_oauth_config()
    return bool(config["client_id"] and config["client_secret"])


def get_authorization_url(state: str = "salesforce") -> str:
    """
    Build the Salesforce OAuth authorization URL.
    User will be redirected here to log in.
    """
    config = get_oauth_config()
    params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": _get_scopes(),
        "state": state,
        "prompt": "login",  # Always show login screen (like n8n)
    }
    url = f"{config['endpoints']['authorize']}?{urllib.parse.urlencode(params)}"
    return url


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange authorization code for access and refresh tokens.
    Returns dict with access_token, refresh_token, instance_url, etc.
    """
    config = get_oauth_config()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"],
    }
    response = requests.post(
        config["endpoints"]["token"],
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # Add response body to error for debugging
    if not response.ok:
        error_detail = f"{response.status_code} {response.reason}"
        try:
            error_body = response.json()
            error_detail += f" - {error_body}"
        except:
            error_detail += f" - {response.text}"
        raise Exception(error_detail)
    return response.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token using the refresh token."""
    config = get_oauth_config()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
    }
    response = requests.post(
        config["endpoints"]["token"],
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    return response.json()


def create_salesforce_client(instance_url: str, access_token: str) -> Salesforce:
    """Create a simple-salesforce client from OAuth tokens."""
    return Salesforce(instance_url=instance_url, session_id=access_token)
