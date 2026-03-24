# MSAL / Azure AD features (removed)

Older versions of this project documented optional Azure AD authentication using MSAL. **That integration is removed.**

- **Setup note:** [AZURE_AD_SETUP.md](AZURE_AD_SETUP.md)
- **Current behavior:** Salesforce OAuth only for dashboard access to Salesforce data; OAuth tokens are held in **session state** only, not persisted under `~/.salesforce_tokens/`.

Do not import `msal` or non-existent modules such as `src/msal_auth.py` — they are not part of the app anymore.
