# Azure AD / MSAL (removed)

The dashboard **no longer** supports optional Microsoft Azure AD sign-in via MSAL. That layer has been removed from the codebase.

**Current authentication**

- **Salesforce OAuth** — users click **Connect with Salesforce** (`src/salesforce_oauth.py`). Tokens live only in **Streamlit session state** for the active session (see README).
- **Username / password** — optional fallback via `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, and `SALESFORCE_SECURITY_TOKEN` in `.env`.

If you need Microsoft (or other IdP) sign-in in front of the app, add it at your **hosting** layer (reverse proxy, identity-aware load balancer, Streamlit Cloud / platform auth, etc.), not inside this repo.

For the old step-by-step Azure app registration instructions, check **git history** from before `src/msal_auth.py` was removed.
