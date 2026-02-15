# Salesforce Connected App Setup Guide

This guide walks you through creating a **Connected App** in Salesforce for OAuth 2.0 authentication. The AE Dashboard uses this to enable the "Connect with Salesforce" login flow (similar to n8n).

## Prerequisites

- A Salesforce account (Production or Sandbox)
- System Administrator or equivalent permissions

---

## Step 1: Open App Manager

1. Log in to your Salesforce org
2. Click the **gear icon** (⚙️) in the top-right → **Setup**
3. In the Quick Find box, search for **App Manager**
4. Click **App Manager**

---

## Step 2: Create New Connected App

1. Click **New Connected App**
2. Fill in the **Basic Information** section:
   - **Connected App Name**: `AE Dashboard` (or any name you prefer)
   - **API Name**: Auto-filled from the name
   - **Contact Email**: Your email address

---

## Step 3: Enable OAuth Settings

1. Check the box **Enable OAuth Settings**
2. The OAuth configuration section will appear below

---

## Step 4: Configure OAuth Settings

### Callback URL (Redirect URI)

Enter the URL where users are redirected after logging in. This must **exactly match** the `SALESFORCE_REDIRECT_URI` in your `.env` file.

| Environment | Callback URL |
|-------------|--------------|
| Local development | `http://localhost:8501` |
| Streamlit Cloud | `https://your-app-name.streamlit.app` |
| Custom deployment | `https://your-domain.com` |

> **Important**: No trailing slash. The URL must match character-for-character.

### Selected OAuth Scopes

**Minimum required** (least privilege). Select scopes that match these **parameter values** in your org's UI:

| Select in Connected App | Parameter value | Purpose |
|-------------------------|-----------------|---------|
| **Manage user data via APIs** | `api` | SOQL, REST API – User/Opportunity/Event |
| **Perform requests at any time** | `refresh_token` / `offline_access` | Refresh tokens |

**If your org uses different labels**, look for scopes whose descriptions mention:
- REST API, Bulk API, or "manage user data via APIs" → use for `api`
- "refresh token", "offline", or "perform requests at any time" → use for `refresh_token`

**Full scope list** (from [Salesforce docs](https://developer.salesforce.com/docs/platform/mobile-sdk/guide/oauth-scope-parameter-values.html)):

| UI label | Value |
|----------|-------|
| Manage user data via APIs | `api` |
| Manage user data via Web browsers | `web` |
| Perform requests at any time | `refresh_token`, `offline_access` |
| Access Connect REST API resources | `chatter_api` |
| Full access | `full` |
| Access unique user identifiers | `openid` |
| Access custom permissions | `custom_permissions` |
| Access Lightning applications | `lightning` |
| Access content resources | `content` |
| Access Analytics REST API resources | `wave_api` |
| Manage Pardot services | `pardot_api` |
| Access identity URL service | `id`, `profile`, `email`, `address`, `phone` |

**Fallback**: If only "Full access" is available, add it in Connected App and set in `.env`:
```bash
SALESFORCE_OAUTH_SCOPES=full refresh_token
```
(You must include `refresh_token` – `full` alone does not return refresh tokens.)

**Scopes not in the list?** Some orgs (e.g. Salesforce Setup, industry clouds) may show a reduced scope list. Try: (1) `web` + `refresh_token` if `api` isn't available; (2) Contact your Salesforce admin – scopes can be org-dependent.

### Flow Enablement (required)

Check **Enable Authorization Code and Credentials Flow**. This enables the OAuth 2.0 Web Server Flow used by the dashboard. Without this, you may get `invalid_client_id` errors.

> If you don't see this option, your org may use the classic OAuth Settings UI – enabling "Enable OAuth Settings" is sufficient there.

### Optional Settings

- **Require Secret for Web Server Flow**: Leave **checked** (default) – we use the client secret
- **Require Proof Key for Code Exchange (PKCE)**: Leave **unchecked** for this app
- **Require Secret for Refresh Token Flow**: Leave **checked** (or unchecked – both work)

---

## Step 5: Save and Get Credentials

1. Click **Save**
2. Click **Continue** on the confirmation dialog
3. You may need to wait a few minutes for the app to propagate

### Retrieve Consumer Key and Consumer Secret

1. In App Manager, find your new Connected App
2. Click the **dropdown arrow** (▼) next to it → **View**
3. Scroll to **API (Enable OAuth Settings)** section
4. Click **Manage Consumer Details**
5. Verify your identity (e.g., enter verification code sent to email)
6. Copy:
   - **Consumer Key** → use as `SALESFORCE_CLIENT_ID`
   - **Consumer Secret** → use as `SALESFORCE_CLIENT_SECRET`

---

## Step 6: Add to .env

Add the credentials to your `.env` file:

```bash
SALESFORCE_CLIENT_ID=your_consumer_key_here
SALESFORCE_CLIENT_SECRET=your_consumer_secret_here
SALESFORCE_REDIRECT_URI=http://localhost:8501
SALESFORCE_SANDBOX=false
```

**OAuth scope mapping** (select these in Connected App; app requests them by default):

| Connected App scope              | Env value              |
|----------------------------------|------------------------|
| Manage user data via APIs       | `api`                  |
| Perform requests at any time    | `refresh_token` / `offline_access` |

Optional: Override via `SALESFORCE_OAUTH_SCOPES=api refresh_token offline_access` if needed.

- **SALESFORCE_SANDBOX**: Set to `true` if using a Sandbox org (uses `test.salesforce.com` instead of `login.salesforce.com`)
- **SALESFORCE_LOGIN_URL**: For custom domains (My Domain), set your org's login URL, e.g. `https://netchex.my.salesforce.com` (no trailing slash). The auth code must be exchanged at the same domain it was issued from.

---

## Sandbox vs Production

| Org Type | Login URL | SALESFORCE_SANDBOX |
|----------|-----------|--------------------|
| Production | `login.salesforce.com` | `false` |
| Sandbox | `test.salesforce.com` | `true` |

For Sandbox, create the Connected App in the Sandbox org and set `SALESFORCE_SANDBOX=true`.

---

## Custom Domain (My Domain)

If your org uses a custom login URL (e.g. `https://netchex.my.salesforce-setup.com`), add to `.env`:

```bash
SALESFORCE_LOGIN_URL=https://netchex.my.salesforce-setup.com
```

Use the base URL **without** a trailing slash. This overrides the default `login.salesforce.com` / `test.salesforce.com` endpoints.

---

## Troubleshooting

### `invalid_client_id` / "client identifier invalid"

Salesforce doesn't recognize the Consumer Key. Check:

0. **Flow Enablement** – In your Connected App settings, ensure **Enable Authorization Code and Credentials Flow** is **checked** (Flow Enablement section). If it's unchecked, the app won't accept OAuth requests.

1. **Environment mismatch** – Consumer Key from **Production** only works with `login.salesforce.com`. Key from **Sandbox** only works with `test.salesforce.com`.
   - Production org → `SALESFORCE_SANDBOX=false`
   - Sandbox org → `SALESFORCE_SANDBOX=true`

2. **Copy the correct value** – In Salesforce: App Manager → your app ▼ → View → API (Enable OAuth Settings) → **Consumer Key** (not Consumer Secret).

3. **No extra characters** – No spaces, quotes, or line breaks in `.env`:
   ```bash
   SALESFORCE_CLIENT_ID=3MVG9xxxxxxxxxxxxxxxx
   ```
   Not: `SALESFORCE_CLIENT_ID="3MVG9..."` or `SALESFORCE_CLIENT_ID= 3MVG9...`

4. **App propagation** – Wait 2–10 minutes after creating the Connected App.

5. **Restart the app** – After changing `.env`, restart Streamlit (`./run.sh` or `streamlit run ...`).

### `invalid_scope` / "the requested scope is not allowed"

The app requests scopes that aren't enabled in your Connected App. Fix in one of two ways:

**Option A – Add scopes to the Connected App** (recommended):
- Edit your Connected App → OAuth Scopes
- Add: **Access and manage your data (api)** and **Perform requests at any time (refresh_token, offline_access)**

**Option B – Match app to your Connected App**:
- If your app only has e.g. "Full access (full)", add to `.env`:
  ```bash
  SALESFORCE_OAUTH_SCOPES=full
  ```
- Restart the app

### "Redirect URI mismatch" or "redirect_uri not valid"

- Callback URL in Salesforce must **exactly** match `SALESFORCE_REDIRECT_URI`
- No trailing slash, correct protocol (http vs https)
- For localhost: `http://localhost:8501` (not `http://127.0.0.1:8501` unless that's what you use)

### "Invalid client credentials"

- Verify Consumer Key and Consumer Secret are correct
- Ensure no extra spaces when copying to `.env`
- Wait 2–10 minutes after creating the app for propagation

### "User hasn't approved this consumer"

- In Salesforce: Setup → Manage Connected Apps → your app → **Edit Policies**
- Set **Permitted Users** to "All users may self-authorize" (or configure approved profiles)
- For some orgs: Enable "Approve Connected Apps for Non-Admins" on the user's profile

### `OAUTH_APPROVAL_ERROR_GENERIC` / "unexpected error during authentication"

This occurs during the approval step after login. Try:

1. **Admin pre-authorization** – Salesforce may require admins to install the app first:
   - Setup → **Manage Connected Apps** → your app → **Edit Policies**
   - Set **Permitted Users** to **"All users may self-authorize"** (or add the user's profile to "Admin approved users")
   - If using "Admin approved users", add the connecting user's profile via **Manage** → assign permission set

2. **IP Relaxation** – If your org uses IP restrictions:
   - Setup → **Manage Connected Apps** → your app → **Edit**
   - Find **IP Relaxation** → set to **"Relax IP restrictions"** (allows OAuth from any IP)

3. **User profile permission** – Enable "Approve Connected Apps for Non-Admins":
   - Setup → **Profiles** → select the user's profile → **Edit**
   - In Administrative Permissions, enable **"Approve Connected Apps for Non-Admins"** (or "Approve apps connected not installed")

4. **OAuth scopes** – Ensure the Connected App has: `api`, `web` (or `full`), and `refresh_token` / `offline_access`

5. **Try incognito/private window** – Clears cached session issues

### Multiple callback URLs

- Salesforce allows multiple callback URLs in newer versions
- Add each environment (localhost, production URL) as a separate line

---

## Security Notes

- Never commit the Consumer Secret to version control
- Use environment variables or a secrets manager in production
- Rotate the Consumer Secret periodically via Setup → Manage Connected Apps
- For production, use HTTPS and a proper domain for the callback URL
