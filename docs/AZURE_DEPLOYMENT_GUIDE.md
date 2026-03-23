# AE Dashboard — Azure Deployment Guide

Deploy the AE Dashboard to Azure App Service with Azure AD authentication and user-level access restriction.

## Overview

The deployment uses:

- **Azure App Service** (Linux, Python 3.11) to host the Streamlit app via zip deploy
- **Shared App Service Plan** owned by the DOL repo (passed in via `-AppServicePlanId`)
- **Azure Key Vault** for secure Salesforce token storage
- **MSAL (in-app)** for Azure AD authentication — users must sign in with Microsoft
- **Email/domain allowlists** to restrict access to specific users
- **Bicep** (`infra/main.bicep`) for infrastructure-as-code
- **`scripts/deploy.ps1`** to orchestrate the full deployment

---

## Prerequisites

### Tools

| Tool | Install | Verify |
|------|---------|--------|
| **Azure CLI** | [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) | `az version` |
| **PowerShell 7+** | [Install PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell) | `pwsh --version` |
| **Bicep CLI** | `az bicep install` | `az bicep version` |

### Azure Access

- An Azure subscription with permissions to create resources
- Permissions to create App Registrations in Azure AD (or an admin who can)
- Logged in: `az login`

---

## Step 1: Create the Resource Group

Use the same resource group as doldata-lead-gen or create a new one:

```powershell
# Use existing (shared with doldata-lead-gen)
# The RG should already exist — verify:
az group show --name "doldata-rg"

# Or create a new one if needed:
az group create --name "doldata-rg" --location "eastus"
```

---

## Step 2: Register an Azure AD Application

This is the identity the app uses to authenticate users via MSAL.

1. Go to **Azure Portal** > **Microsoft Entra ID** > **App registrations** > **New registration**

2. Fill in:
   - **Name:** `AE Dashboard` (or similar)
   - **Supported account types:** "Accounts in this organizational directory only" (single tenant)
   - **Redirect URI:** Select **Web**, enter:
     ```
     https://<your-app-name>.azurewebsites.net
     ```
     (e.g., `https://ae-dashboard.azurewebsites.net`)

3. Click **Register**

4. On the app's **Overview** page, copy:
   - **Application (client) ID** — this is `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** — this is `AZURE_TENANT_ID`

5. Go to **Certificates & secrets** > **New client secret**:
   - Description: `AE Dashboard production`
   - Expiry: choose appropriate (e.g., 24 months)
   - Click **Add**, copy the **Value** immediately — this is `AZURE_CLIENT_SECRET`

6. Go to **Authentication**:
   - Under **Implicit grant and hybrid flows**, check **ID tokens**
   - Click **Save**

---

## Step 3: Restrict Access to Specific Users (Assignment Required)

This is the primary mechanism for limiting who can access the dashboard.

1. Go to **Azure Portal** > **Microsoft Entra ID** > **Enterprise applications**

2. Search for the app you just registered (e.g., `AE Dashboard`)

3. Go to **Properties**:
   - Set **Assignment required?** to **Yes**
   - Click **Save**

4. Go to **Users and groups** > **Add user/group**:
   - Select the specific users (or groups) who should have access
   - Click **Assign**

> **Important:** With "Assignment required" = Yes, only assigned users can sign in. Everyone else in the tenant gets an error. This is your primary access control gate.

---

## Step 4: Deploy Infrastructure + App

### Option A: Full deployment (first time)

```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "ae-dashboard" `
    -AppServicePlanId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/serverfarms/<plan>" `
    -AzureAdClientId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" `
    -AzureAdTenantId "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy" `
    -AzureAdClientSecret "your-client-secret-value" `
    -AzureAllowedEmails "user1@company.com,user2@company.com"
```

This will:
1. Deploy Bicep infrastructure (App Service, Key Vault)
2. Zip-deploy the application code to App Service
3. Configure App Settings

### Option B: Full deployment + configure Salesforce interactively

```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "ae-dashboard" `
    -AppServicePlanId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/serverfarms/<plan>" `
    -AzureAdClientId "..." `
    -AzureAdTenantId "..." `
    -AzureAdClientSecret "..." `
    -AzureAllowedEmails "user1@company.com,user2@company.com" `
    -ConfigureSettings
```

The `-ConfigureSettings` flag will interactively prompt for Salesforce OAuth credentials and other settings.

### Option C: Code-only redeploy (infra already exists)

```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "ae-dashboard" `
    -SkipInfra
```

### Option D: Update settings only (no redeploy)

```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "ae-dashboard" `
    -SkipInfra -SkipDeploy -ConfigureSettings
```

---

## Step 5: Configure Salesforce OAuth

The Salesforce Connected App credentials must be set as App Settings. You can do this via `-ConfigureSettings` (prompted interactively) or manually:

```powershell
az webapp config appsettings set `
    --resource-group "doldata-rg" `
    --name "ae-dashboard" `
    --settings `
        SALESFORCE_CLIENT_ID="your-sf-client-id" `
        SALESFORCE_CLIENT_SECRET="your-sf-client-secret" `
        SALESFORCE_REDIRECT_URI="https://ae-dashboard.azurewebsites.net" `
        SALESFORCE_SANDBOX="false"
```

See [SALESFORCE_CONNECTED_APP_SETUP.md](SALESFORCE_CONNECTED_APP_SETUP.md) for creating the Connected App in Salesforce.

---

## Step 6: Verify the Deployment

1. Wait 1-2 minutes for the app to start
2. Visit `https://ae-dashboard.azurewebsites.net`
3. You should be redirected to the Microsoft login page
4. Sign in with an assigned user account
5. After login, the AE Dashboard should load

### Troubleshooting

Check logs:
```powershell
az webapp log tail --resource-group "doldata-rg" --name "ae-dashboard"
```

Health endpoint:
```
https://ae-dashboard.azurewebsites.net/_stcore/health
```

---

## How User Restriction Works

Access is controlled at two layers:

### Layer 1: Azure AD Enterprise App (Assignment Required)
- Set in the Azure Portal (Step 3 above)
- Blocks any user not explicitly assigned to the app
- Managed by adding/removing users or groups in the Enterprise App
- **This is the primary control** — changes are immediate, no redeployment needed

### Layer 2: App-Level Email/Domain Filtering (Defense in Depth)
- Configured via App Settings:
  - `AZURE_ALLOWED_EMAILS` — comma-separated email addresses (e.g., `user1@company.com,user2@company.com`)
  - `AZURE_ALLOWED_DOMAINS` — comma-separated domains (e.g., `company.com`)
- Set during deployment or updated anytime:

```powershell
az webapp config appsettings set `
    --resource-group "doldata-rg" `
    --name "ae-dashboard" `
    --settings AZURE_ALLOWED_EMAILS="user1@company.com,user2@company.com"
```

- If both are empty, any authenticated user in the tenant can access the app (restricted only by Layer 1)
- If either is set, the user's email must match

### Adding/Removing Users

| Action | Where |
|--------|-------|
| Add a user | Enterprise App > Users and groups > Add |
| Remove a user | Enterprise App > Users and groups > select > Remove |
| Add to email allowlist | Update `AZURE_ALLOWED_EMAILS` App Setting |
| Allow entire domain | Update `AZURE_ALLOWED_DOMAINS` App Setting |

---

## Parameter Reference

### deploy.ps1 Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `ResourceGroupName` | Yes | — | Azure resource group (must exist) |
| `AppName` | Yes | — | Base name for all resources |
| `AppServicePlanId` | Yes | — | Resource ID of the shared App Service Plan (owned by DOL repo) |
| `Location` | No | `eastus` | Azure region |
| `AzureAdClientId` | No | `''` | Azure AD app client ID |
| `AzureAdTenantId` | No | `''` | Azure AD tenant ID |
| `AzureAdClientSecret` | No | `''` | Azure AD client secret |
| `AzureAllowedDomains` | No | `''` | Comma-separated allowed domains |
| `AzureAllowedEmails` | No | `''` | Comma-separated allowed emails |
| `SkipInfra` | No | `false` | Skip infrastructure deployment (Bicep) |
| `SkipDeploy` | No | `false` | Skip zip deployment |
| `ConfigureSettings` | No | `false` | Interactively configure App Settings |

### App Settings (Environment Variables)

| Setting | Required | Description |
|---------|----------|-------------|
| `AZURE_CLIENT_ID` | Yes (for auth) | Azure AD app registration client ID |
| `AZURE_TENANT_ID` | Yes (for auth) | Azure AD tenant ID |
| `AZURE_CLIENT_SECRET` | Yes (for auth) | Azure AD client secret |
| `AZURE_REDIRECT_URI` | No | Defaults to `https://<appName>.azurewebsites.net` |
| `AZURE_SCOPES` | No | Defaults to `User.Read` |
| `AZURE_ALLOWED_DOMAINS` | No | Comma-separated domain allowlist |
| `AZURE_ALLOWED_EMAILS` | No | Comma-separated email allowlist |
| `SALESFORCE_CLIENT_ID` | Yes | Salesforce Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | Yes | Salesforce Connected App consumer secret |
| `SALESFORCE_REDIRECT_URI` | Yes | Must match Connected App redirect URI |
| `SALESFORCE_SANDBOX` | No | `true` or `false` (default: `false`) |
| `KEY_VAULT_NAME` | Auto | Set by Bicep, used for Salesforce token storage |

---

## Azure DevOps Pipeline (CI/CD)

The `azure-pipelines.yml` handles automated deployments on push to `main`:

1. **Build**: Install dependencies and create zip package
2. **Deploy**: Zip-deploy to Azure App Service

### Required Pipeline Variables

Set these in Azure DevOps (Pipeline > Edit > Variables):

| Variable | Description |
|----------|-------------|
| `AZURE_SERVICE_CONNECTION` | Service connection to Azure subscription |
| `APP_NAME` | App Service name (e.g., `ae-dashboard`) |
| `RESOURCE_GROUP_NAME` | Resource group name |

> **Note:** The pipeline deploys code changes only. Infrastructure changes (Bicep) and App Settings are managed via `deploy.ps1`.
