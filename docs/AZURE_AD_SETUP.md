# Azure AD / MSAL Authentication Setup Guide

This guide walks you through setting up Microsoft Azure AD authentication for the AE Dashboard using MSAL (Microsoft Authentication Library).

## Overview

MSAL authentication adds a layer of security by requiring users to sign in with their Microsoft/Azure AD account before accessing the dashboard. This is in addition to the Salesforce OAuth authentication.

**Authentication Flow:**
1. User visits dashboard → Sign in with Microsoft → Access granted
2. User then connects to Salesforce → Dashboard loads data

## Prerequisites

- Azure subscription (or Microsoft 365 subscription with Azure AD)
- Global Administrator or Application Administrator role in Azure AD
- Your dashboard's redirect URI (e.g., `http://localhost:8501` for local development)

## Step 1: Register an Application in Azure AD

### 1.1 Access Azure Portal

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** (search in the top search bar)
3. Click **App registrations** in the left sidebar
4. Click **+ New registration**

### 1.2 Configure App Registration

Fill in the registration form:

**Name:** `AE Dashboard` (or any name you prefer)

**Supported account types:** Choose based on your needs:
- **Single tenant** (recommended): Only users in your organization can sign in
- **Multi-tenant**: Users from any Azure AD directory can sign in
- **Multi-tenant + personal**: Users with work/school or personal Microsoft accounts

**Redirect URI:**
- Platform: **Web**
- URI: `http://localhost:8501` (for local development)
  - For production, use your deployed URL (e.g., `https://dashboard.company.com`)

Click **Register**

### 1.3 Copy Important Values

After registration, you'll see the **Overview** page. Copy these values:

1. **Application (client) ID** - You'll need this for `AZURE_CLIENT_ID`
2. **Directory (tenant) ID** - You'll need this for `AZURE_TENANT_ID`

## Step 2: Create a Client Secret

1. In your app registration, go to **Certificates & secrets** in the left sidebar
2. Click **+ New client secret**
3. Description: `AE Dashboard Secret` (or any description)
4. Expires: Choose expiration period (recommended: 24 months)
5. Click **Add**
6. **IMPORTANT:** Copy the **Value** immediately (you'll need this for `AZURE_CLIENT_SECRET`)
   - ⚠️ This value is only shown once! Store it securely.

## Step 3: Configure API Permissions

1. Go to **API permissions** in the left sidebar
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Search and check: **User.Read** (basic user profile)
6. Click **Add permissions**
7. Click **Grant admin consent for [Your Organization]** (requires admin role)
8. Confirm by clicking **Yes**

### Optional: Additional Permissions

For advanced features, you can add more permissions:

- **Mail.Read**: Read user's email
- **Calendars.Read**: Read user's calendar
- **Groups.Read.All**: Read group memberships (for group-based access control)
- **User.ReadBasic.All**: Read all users' basic profiles

## Step 4: Configure Redirect URI (if needed)

If you need to add more redirect URIs (e.g., for multiple environments):

1. Go to **Authentication** in the left sidebar
2. Under **Platform configurations** → **Web**, click **Add URI**
3. Add your URIs:
   - Development: `http://localhost:8501`
   - Staging: `https://staging-dashboard.company.com`
   - Production: `https://dashboard.company.com`
4. Click **Save**

## Step 5: Configure Environment Variables

Add these to your `.env` file:

```bash
# Azure AD / MSAL Authentication
AZURE_CLIENT_ID=your_application_client_id_here
AZURE_TENANT_ID=your_directory_tenant_id_here
AZURE_CLIENT_SECRET=your_client_secret_value_here
AZURE_REDIRECT_URI=http://localhost:8501
```

### Optional Configuration

```bash
# Custom authority (if needed)
AZURE_AUTHORITY=https://login.microsoftonline.com/your_tenant_id_here

# Additional scopes (space-separated)
AZURE_SCOPES="User.Read Mail.Read"

# Restrict access by email domain
AZURE_ALLOWED_DOMAINS=company.com,subsidiary.com

# Restrict access by specific emails
AZURE_ALLOWED_EMAILS=admin@company.com,manager@company.com
```

## Step 6: Test Authentication

1. Restart your Streamlit dashboard
2. Visit `http://localhost:8501`
3. You should see a "Sign in with Microsoft" button
4. Click it and sign in with your Microsoft account
5. You should be redirected back to the dashboard
6. Your name and email should appear in the sidebar

## Access Control Options

### Option 1: Domain-Based Access Control

Restrict access to users from specific email domains:

```bash
# Only users with @company.com or @subsidiary.com emails can access
AZURE_ALLOWED_DOMAINS=company.com,subsidiary.com
```

### Option 2: Email-Based Access Control

Restrict access to specific users:

```bash
# Only these users can access the dashboard
AZURE_ALLOWED_EMAILS=john.doe@company.com,jane.smith@company.com,admin@company.com
```

### Option 3: Group-Based Access Control

For advanced scenarios, you can check group membership in code:

1. Add `Groups.Read.All` permission in Azure AD
2. Get user's groups via Microsoft Graph API
3. Check if user is in allowed group

## Troubleshooting

### Error: "AADSTS50011: The reply URL specified in the request does not match"

**Solution:** Make sure the redirect URI in your `.env` file exactly matches one of the redirect URIs configured in Azure AD (including http/https and trailing slashes).

### Error: "AADSTS65001: The user or administrator has not consented"

**Solution:** 
1. Go to Azure AD → App registrations → Your app → API permissions
2. Click "Grant admin consent for [Your Organization]"
3. Try signing in again

### Error: "Access Denied" after successful sign-in

**Solution:** Check your `AZURE_ALLOWED_DOMAINS` or `AZURE_ALLOWED_EMAILS` configuration. Your email/domain might not be in the allowed list.

### Users can't sign in from outside the organization

**Solution:** 
1. Go to Azure AD → App registrations → Your app → Authentication
2. Under "Supported account types", change to multi-tenant if needed
3. Or, only allow users from your organization (single tenant)

## Security Best Practices

1. **Use HTTPS in production** - Never use `http://` for production redirect URIs
2. **Rotate client secrets regularly** - Set expiration and create new secrets before they expire
3. **Use least privilege** - Only request the minimum scopes needed
4. **Monitor sign-in logs** - Check Azure AD sign-in logs for suspicious activity
5. **Enable MFA** - Require multi-factor authentication for users
6. **Don't commit secrets** - Never commit `.env` file to version control

## Production Deployment

### For Streamlit Cloud

1. Add a redirect URI in Azure AD: `https://your-app.streamlit.app`
2. In Streamlit Cloud secrets, add:
   ```toml
   [env]
   AZURE_CLIENT_ID = "your_client_id"
   AZURE_TENANT_ID = "your_tenant_id"
   AZURE_CLIENT_SECRET = "your_secret"
   AZURE_REDIRECT_URI = "https://your-app.streamlit.app"
   ```

### For Docker/Self-Hosted

1. Add redirect URI in Azure AD: `https://dashboard.company.com`
2. Set environment variables in your deployment configuration
3. Ensure your SSL/TLS certificates are valid

## Additional Resources

- [Azure AD App Registration Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/overview)
- [Azure AD Authentication Flows](https://docs.microsoft.com/en-us/azure/active-directory/develop/authentication-flows-app-scenarios)

## Support

If you encounter issues:
1. Check Azure AD sign-in logs (Azure AD → Sign-in logs)
2. Enable debug mode in `.env`: `DEBUG=1`
3. Check Streamlit app logs for detailed error messages
4. Verify all Azure AD configuration matches your `.env` file
