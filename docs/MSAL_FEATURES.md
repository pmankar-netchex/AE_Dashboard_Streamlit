# MSAL Authentication Features

## Overview

The dashboard now supports Microsoft Azure AD authentication using MSAL (Microsoft Authentication Library). This is **optional** and provides an additional security layer for controlling who can access the dashboard.

## How It Works

```
User Flow (with MSAL enabled):
1. User visits dashboard
2. → Sign in with Microsoft (Azure AD)
3. → Access granted to dashboard
4. → Connect with Salesforce (existing OAuth flow)
5. → Dashboard loads Salesforce data
```

```
User Flow (without MSAL - default):
1. User visits dashboard
2. → Connect with Salesforce
3. → Dashboard loads Salesforce data
```

## Key Features

### 1. **Optional Authentication**
- MSAL is **off by default** - only activates when configured in `.env`
- Easy to enable/disable by adding or removing Azure AD credentials
- No impact on existing Salesforce OAuth flow

### 2. **Access Control**
Multiple ways to control who can access the dashboard:

#### Domain-Based Access
```bash
# Only users with @company.com emails can access
AZURE_ALLOWED_DOMAINS=company.com
```

#### Email-Based Access
```bash
# Only specific users can access
AZURE_ALLOWED_EMAILS=john@company.com,jane@company.com
```

#### Open Access
```bash
# Any user in your Azure AD tenant can access
# (no AZURE_ALLOWED_DOMAINS or AZURE_ALLOWED_EMAILS)
```

### 3. **User Information Display**
- Shows signed-in user's name and email in sidebar
- Helpful for audit trails and user identification
- Sign out button to clear session

### 4. **Seamless Integration**
- Works alongside Salesforce OAuth (not a replacement)
- User authenticates once with Microsoft, then connects to Salesforce
- Both authentication states are maintained in session

### 5. **Session Management**
- Authentication persists across page refreshes
- Sign out clears Microsoft authentication (Salesforce connection remains until explicitly disconnected)
- Automatic token refresh (handled by MSAL)

## Use Cases

### Use Case 1: Enterprise Security
**Scenario:** Company wants to ensure only employees can access the dashboard

**Solution:**
```bash
AZURE_ALLOWED_DOMAINS=company.com
```

All users with @company.com emails can sign in. No manual user management needed.

### Use Case 2: Restricted Access
**Scenario:** Dashboard should only be accessible by sales managers

**Solution:**
```bash
AZURE_ALLOWED_EMAILS=manager1@company.com,manager2@company.com,director@company.com
```

Only listed users can access the dashboard.

### Use Case 3: Multi-Tenant Access
**Scenario:** Dashboard is used by multiple organizations (consultants, partners)

**Solution:**
```bash
# In Azure AD, set app to multi-tenant
# In .env:
AZURE_ALLOWED_DOMAINS=company1.com,company2.com,partner.com
```

Users from multiple domains can access.

### Use Case 4: Public Dashboard + Salesforce OAuth
**Scenario:** Dashboard is public, but Salesforce data requires authentication

**Solution:**
Don't configure MSAL at all. Only Salesforce OAuth is required.

## Configuration Example

### Minimal Configuration (Required)
```bash
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_TENANT_ID=87654321-4321-4321-4321-cba987654321
AZURE_CLIENT_SECRET=your_secret_value_here
AZURE_REDIRECT_URI=http://localhost:8501
```

### With Access Control
```bash
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_TENANT_ID=87654321-4321-4321-4321-cba987654321
AZURE_CLIENT_SECRET=your_secret_value_here
AZURE_REDIRECT_URI=http://localhost:8501

# Restrict to company domain
AZURE_ALLOWED_DOMAINS=company.com

# Or restrict to specific users
AZURE_ALLOWED_EMAILS=admin@company.com,manager@company.com
```

### Advanced Configuration
```bash
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_TENANT_ID=87654321-4321-4321-4321-cba987654321
AZURE_CLIENT_SECRET=your_secret_value_here
AZURE_REDIRECT_URI=https://dashboard.company.com

# Custom authority (for government cloud, etc.)
AZURE_AUTHORITY=https://login.microsoftonline.com/87654321-4321-4321-4321-cba987654321

# Additional Microsoft Graph scopes
AZURE_SCOPES="User.Read Mail.Read Calendars.Read"

# Multiple allowed domains
AZURE_ALLOWED_DOMAINS=company.com,subsidiary.com,partner.com
```

## Benefits

### Security Benefits
- ✅ **Centralized access control** - Manage users in Azure AD, not in the app
- ✅ **MFA support** - Leverage Azure AD's multi-factor authentication
- ✅ **Audit logs** - Track who accesses the dashboard via Azure AD sign-in logs
- ✅ **Conditional access** - Apply Azure AD conditional access policies
- ✅ **Zero trust** - Verify user identity before granting dashboard access

### User Benefits
- ✅ **Single Sign-On** - Users sign in with existing Microsoft account
- ✅ **No new passwords** - Leverage existing corporate credentials
- ✅ **Familiar login** - Microsoft login screen is familiar to most users

### Admin Benefits
- ✅ **Easy onboarding** - Add users to Azure AD group, they automatically get access
- ✅ **Easy offboarding** - Disable user in Azure AD, access immediately revoked
- ✅ **No user database** - No need to maintain separate user list in the app
- ✅ **Compliance** - Meets enterprise authentication requirements

## API Reference

### Check if MSAL is Configured
```python
from src.msal_auth import is_msal_configured

if is_msal_configured():
    print("MSAL is enabled")
```

### Check if User is Authenticated
```python
from src.msal_auth import is_authenticated

if is_authenticated():
    print("User is signed in")
```

### Get Current User Info
```python
from src.msal_auth import get_cached_user

user = get_cached_user()
if user:
    user_info = user.get("user_info", {})
    print(f"Name: {user_info.get('displayName')}")
    print(f"Email: {user_info.get('mail')}")
```

### Check Authorization
```python
from src.msal_auth import check_user_authorization

# Check domain
if check_user_authorization(allowed_domains=["company.com"]):
    print("User is authorized")

# Check email
if check_user_authorization(allowed_emails=["admin@company.com"]):
    print("User is authorized")
```

### Sign Out User
```python
from src.msal_auth import clear_user_cache

clear_user_cache()
st.rerun()
```

## Migration Guide

### From No Authentication → MSAL

1. Set up Azure AD app registration (see `AZURE_AD_SETUP.md`)
2. Add MSAL credentials to `.env`
3. Restart dashboard
4. Users will now see Microsoft sign-in screen

### From MSAL → No MSAL

1. Remove or comment out MSAL variables in `.env`:
```bash
# AZURE_CLIENT_ID=...
# AZURE_TENANT_ID=...
# AZURE_CLIENT_SECRET=...
```
2. Restart dashboard
3. Users go directly to Salesforce OAuth

## Troubleshooting

### Problem: Sign-in button doesn't appear
**Solution:** Check that all three required variables are set in `.env`:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET`

### Problem: "Access Denied" after successful sign-in
**Solution:** Check `AZURE_ALLOWED_DOMAINS` or `AZURE_ALLOWED_EMAILS`. Your email/domain might not be in the allowed list.

### Problem: Redirect loop after sign-in
**Solution:** Verify `AZURE_REDIRECT_URI` in `.env` matches exactly what's configured in Azure AD app registration.

### Problem: Can't sign in from mobile/different browser
**Solution:** MSAL session is browser-specific. User needs to sign in on each browser/device.

## FAQ

**Q: Is MSAL required?**
A: No, it's completely optional. The dashboard works without MSAL.

**Q: Can I use MSAL without Salesforce OAuth?**
A: No, Salesforce OAuth is still required to access Salesforce data. MSAL only controls who can access the dashboard itself.

**Q: Does MSAL replace Salesforce OAuth?**
A: No, they work together. MSAL authenticates the user to the dashboard, then Salesforce OAuth authenticates to Salesforce.

**Q: What happens if MSAL credentials expire?**
A: User will see sign-in screen again. Check Azure AD for client secret expiration and renew before it expires.

**Q: Can I use social accounts (Google, Facebook)?**
A: Only if your Azure AD is configured for B2C (Business-to-Consumer) identity. Standard Azure AD only supports work/school accounts.

**Q: How do I add more users?**
A: If using domain-based access, just add them to Azure AD. If using email-based access, add their email to `AZURE_ALLOWED_EMAILS`.

**Q: Can I use Azure AD groups?**
A: Yes, but requires custom code. Request `Groups.Read.All` scope and check group membership via Microsoft Graph API.

## Next Steps

- **Setup Guide:** [AZURE_AD_SETUP.md](AZURE_AD_SETUP.md)
- **Customization:** See inline comments in `src/msal_auth.py`
- **Microsoft Graph:** [Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
