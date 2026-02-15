"""
Microsoft Authentication Library (MSAL) Integration
Provides Azure AD authentication for the Streamlit dashboard.
"""
import os
import msal
import streamlit as st
from typing import Optional, Dict, Any
import json


# ==============================================================================
# MSAL CONFIGURATION
# ==============================================================================

def get_msal_config() -> Dict[str, Any]:
    """
    Load MSAL configuration from environment variables.
    
    Required environment variables:
    - AZURE_CLIENT_ID: Application (client) ID from Azure AD app registration
    - AZURE_TENANT_ID: Directory (tenant) ID from Azure AD
    - AZURE_CLIENT_SECRET: Client secret value from Azure AD app registration
    - AZURE_REDIRECT_URI: Redirect URI (e.g., http://localhost:8501)
    
    Optional:
    - AZURE_AUTHORITY: Authority URL (defaults to https://login.microsoftonline.com/{tenant_id})
    - AZURE_SCOPES: Space-separated scopes (defaults to "User.Read")
    """
    client_id = os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    redirect_uri = os.environ.get("AZURE_REDIRECT_URI", "http://localhost:8501")
    
    if not all([client_id, tenant_id, client_secret]):
        return {}
    
    authority = os.environ.get(
        "AZURE_AUTHORITY",
        f"https://login.microsoftonline.com/{tenant_id}"
    )
    
    scopes = os.environ.get("AZURE_SCOPES", "User.Read").split()
    
    return {
        "client_id": client_id,
        "tenant_id": tenant_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "authority": authority,
        "scopes": scopes,
    }


def is_msal_configured() -> bool:
    """Check if MSAL is properly configured."""
    config = get_msal_config()
    return bool(config.get("client_id") and config.get("tenant_id") and config.get("client_secret"))


# ==============================================================================
# MSAL CLIENT
# ==============================================================================

def get_msal_app() -> Optional[msal.ConfidentialClientApplication]:
    """Create and return MSAL confidential client application."""
    config = get_msal_config()
    if not config:
        return None
    
    try:
        app = msal.ConfidentialClientApplication(
            config["client_id"],
            authority=config["authority"],
            client_credential=config["client_secret"],
        )
        return app
    except Exception as e:
        st.error(f"Failed to create MSAL app: {str(e)}")
        return None


# ==============================================================================
# AUTHENTICATION FLOW
# ==============================================================================

def get_authorization_url() -> str:
    """
    Generate the authorization URL for the user to authenticate.
    Returns the URL to redirect the user to for login.
    """
    config = get_msal_config()
    app = get_msal_app()
    
    if not app:
        return ""
    
    # Generate auth URL with state for security
    auth_url = app.get_authorization_request_url(
        scopes=config["scopes"],
        redirect_uri=config["redirect_uri"],
        state=st.session_state.get("msal_state", "defaultstate")
    )
    
    return auth_url


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from the callback
        
    Returns:
        Token response with access_token, id_token, etc.
        
    Raises:
        Exception if token exchange fails
    """
    config = get_msal_config()
    app = get_msal_app()
    
    if not app:
        raise Exception("MSAL not configured")
    
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=config["scopes"],
        redirect_uri=config["redirect_uri"]
    )
    
    if "error" in result:
        raise Exception(f"Token exchange failed: {result.get('error_description', result['error'])}")
    
    return result


def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get user information from Microsoft Graph API.
    
    Args:
        access_token: Valid access token
        
    Returns:
        User information dict with fields like displayName, mail, userPrincipalName
    """
    import requests
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"Failed to get user info: {str(e)}")
        return None


def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh the access token using a refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New token response
        
    Raises:
        Exception if refresh fails
    """
    config = get_msal_config()
    app = get_msal_app()
    
    if not app:
        raise Exception("MSAL not configured")
    
    result = app.acquire_token_by_refresh_token(
        refresh_token,
        scopes=config["scopes"]
    )
    
    if "error" in result:
        raise Exception(f"Token refresh failed: {result.get('error_description', result['error'])}")
    
    return result


# ==============================================================================
# SESSION MANAGEMENT
# ==============================================================================

def get_cached_user() -> Optional[Dict[str, Any]]:
    """Get cached user from session state."""
    return st.session_state.get("msal_user")


def cache_user(token_response: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None):
    """
    Cache user authentication in session state.
    
    Args:
        token_response: Token response from MSAL
        user_info: Optional user info from Graph API
    """
    st.session_state["msal_user"] = {
        "access_token": token_response.get("access_token"),
        "id_token": token_response.get("id_token"),
        "refresh_token": token_response.get("refresh_token"),
        "expires_in": token_response.get("expires_in"),
        "user_info": user_info or {},
    }


def clear_user_cache():
    """Clear user authentication from session state."""
    if "msal_user" in st.session_state:
        del st.session_state["msal_user"]
    if "msal_state" in st.session_state:
        del st.session_state["msal_state"]


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return "msal_user" in st.session_state and st.session_state["msal_user"].get("access_token")


# ==============================================================================
# UI HELPERS
# ==============================================================================

def render_login_screen():
    """Render the Azure AD login screen."""
    st.markdown("""
        <div class="oauth-login-box">
            <h2>🔐 Sign In Required</h2>
            <p>Please sign in with your Microsoft account to access the dashboard</p>
            <a href="#" onclick="window.location.href='{auth_url}'" class="oauth-btn">Sign in with Microsoft</a>
        </div>
    """.format(auth_url=get_authorization_url()), unsafe_allow_html=True)
    
    with st.expander("ℹ️ Setup Information"):
        st.markdown("""
        **Azure AD Authentication**
        
        This dashboard uses Microsoft Azure AD for authentication.
        
        If you're seeing this page, it means:
        1. MSAL is configured in the `.env` file
        2. You need to sign in with your Microsoft account
        3. Your account must have access to this application
        
        **For administrators:** Configure AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET in `.env`
        """)


def display_user_info():
    """Display authenticated user information in sidebar."""
    user = get_cached_user()
    if not user:
        return
    
    user_info = user.get("user_info", {})
    display_name = user_info.get("displayName", "User")
    email = user_info.get("mail") or user_info.get("userPrincipalName", "")
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 Signed in as")
        st.markdown(f"**{display_name}**")
        if email:
            st.caption(email)
        
        if st.button("🚪 Sign Out", key="msal_signout", use_container_width=True):
            clear_user_cache()
            st.rerun()


# ==============================================================================
# AUTHORIZATION CHECKS
# ==============================================================================

def check_user_authorization(allowed_domains: Optional[list] = None, allowed_emails: Optional[list] = None) -> bool:
    """
    Check if authenticated user is authorized based on domain or email.
    
    Args:
        allowed_domains: List of allowed email domains (e.g., ["company.com", "subsidiary.com"])
        allowed_emails: List of allowed email addresses
        
    Returns:
        True if user is authorized, False otherwise
    """
    user = get_cached_user()
    if not user:
        return False
    
    user_info = user.get("user_info", {})
    email = user_info.get("mail") or user_info.get("userPrincipalName", "")
    
    if not email:
        return False
    
    # Check email whitelist
    if allowed_emails:
        if email.lower() in [e.lower() for e in allowed_emails]:
            return True
        # If email whitelist exists but user not in it, deny
        if not allowed_domains:
            return False
    
    # Check domain whitelist
    if allowed_domains:
        email_domain = email.split("@")[-1].lower()
        return email_domain in [d.lower() for d in allowed_domains]
    
    # If no restrictions, allow
    return True


# ==============================================================================
# CUSTOMIZATION NOTES
# ==============================================================================

"""
MSAL Customization Examples:

1. RESTRICT ACCESS BY DOMAIN:
   In streamlit_dashboard.py:
   
   if not check_user_authorization(allowed_domains=["company.com", "subsidiary.com"]):
       st.error("Access denied. Only company.com users can access this dashboard.")
       st.stop()

2. RESTRICT ACCESS BY EMAIL:
   
   if not check_user_authorization(allowed_emails=["admin@company.com", "manager@company.com"]):
       st.error("Access denied. Contact your administrator.")
       st.stop()

3. USE MICROSOFT GRAPH API:
   
   user = get_cached_user()
   access_token = user["access_token"]
   
   # Call Graph API
   import requests
   response = requests.get(
       "https://graph.microsoft.com/v1.0/me/photo/$value",
       headers={"Authorization": f"Bearer {access_token}"}
   )

4. CUSTOM SCOPES:
   In .env file:
   AZURE_SCOPES="User.Read Mail.Read Calendars.Read"

5. GROUP-BASED ACCESS:
   Request Groups.Read.All scope and check user's group membership
"""
