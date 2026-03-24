# AE Ultimate Dashboard - Streamlit + SOQL

A Streamlit dashboard that replicates your Excel AE Dashboard using direct SOQL queries to Salesforce.

**Modular architecture** - SOQL queries, calculations, and UI in separate files for easy customization.

## 🚀 Quick Start (3 steps)

```bash
./setup.sh                    # 1. Setup venv and dependencies
# Edit .env with credentials  # 2. Configure OAuth or username/password
./run.sh                      # 3. Run the dashboard
```

Open `http://localhost:8501` and click "Connect with Salesforce".

---

## Authentication

### Salesforce OAuth Login (Recommended)

The dashboard supports **Salesforce OAuth** – users see a "Connect with Salesforce" button and sign in via the browser (no passwords in config).

1. **Create a Connected App** in Salesforce:
   - Setup → App Manager → New Connected App
   - Enable OAuth Settings
   - Callback URL: `http://localhost:8501` (or your app URL)
   - OAuth Scopes: `api`, `refresh_token`, `offline_access`, `full`
   - Copy Consumer Key and Consumer Secret

2. **Configure `.env`** – see [docs/SALESFORCE_CONNECTED_APP_SETUP.md](docs/SALESFORCE_CONNECTED_APP_SETUP.md) for detailed steps:
```bash
SALESFORCE_CLIENT_ID=your_consumer_key
SALESFORCE_CLIENT_SECRET=your_consumer_secret
SALESFORCE_REDIRECT_URI=http://localhost:8501
SALESFORCE_SANDBOX=false
```

3. **Run** – users click "Connect with Salesforce" to log in.

**Session-only OAuth:** Access and refresh tokens are kept in **Streamlit session state** (server-side, tied to the browser session). They are **not** saved to disk. Users stay connected while the session stays alive; after closing the tab, session timeout, or server restart, they must connect again. The app still refreshes the access token using the refresh token **during** that session when possible.

Optional **Disconnect** clears the session and removes any legacy on-disk file from older versions (`~/.salesforce_tokens/ae_dashboard.json`) if present.

Microsoft Azure AD / MSAL was **removed** from this app. See [docs/AZURE_AD_SETUP.md](docs/AZURE_AD_SETUP.md) for a short note and alternatives at the hosting layer.

### Username/Password (Legacy)

Copy template and set credentials:
```bash
cp scripts/.env.example .env
# Edit .env with username/password
```

## 📊 Features

- **OAuth Login** - n8n-style "Connect with Salesforce" (no passwords in config)
- **Live Salesforce Data** - Direct SOQL queries
- **Modular Architecture** - Separate files for queries, calculations, and UI
- **Fast Performance** - Optimized bulk queries (3 queries total, not 3×N)
- **Easy Customization** - Edit SOQL, formulas, or styling in dedicated modules
- **Interactive** - Month selector, adjustable calculations
- **Export Ready** - Download as CSV

## 📁 Project Structure

Clean, organized folder structure. See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for details.

```
├── streamlit_dashboard.py         Main entry point
├── src/                           Application modules (⚙️ customize here)
├── scripts/                       Setup & run scripts
├── docs/                          Documentation
├── .env                           Your credentials
└── requirements.txt               Dependencies
```

## 🔧 Customization

The dashboard is **modularized** for easy customization. See [docs/CUSTOMIZATION_GUIDE.md](docs/CUSTOMIZATION_GUIDE.md) for detailed instructions.

**Quick examples:**

- **Change stage name**: Edit `src/salesforce_queries.py` line 79 (`'Closed Won'`)
- **Filter users**: Edit `src/salesforce_queries.py` line 23 (add Profile/Role filters)
- **Meeting keywords**: Edit `src/salesforce_queries.py` line 143 (Subject LIKE conditions)
- **Quota formula**: Edit `src/dashboard_calculations.py` line 55
- **Colors/styling**: Edit `src/dashboard_ui.py` line 13 (CSS)

## 📦 Deployment Options

### Local
```bash
streamlit run streamlit_dashboard.py
```

### Streamlit Cloud (Free)
1. Push to GitHub
2. Go to https://share.streamlit.io
3. Connect repo
4. Add secrets in dashboard settings

### Docker
```bash
docker build -t ae-dashboard .
# PORT defaults to 8501; map the same port on the host
docker run --rm -p 8501:8501 \
  -e SALESFORCE_CLIENT_ID=... \
  -e SALESFORCE_CLIENT_SECRET=... \
  -e SALESFORCE_REDIRECT_URI=http://localhost:8501 \
  ae-dashboard
```

The production-oriented `Dockerfile` at the repo root binds Streamlit to `0.0.0.0`, uses headless mode, and reads the listen port from the `PORT` environment variable (default `8501`), which matches Azure Container Apps.

### Deploy to Azure (Container Apps)

This repo includes **Docker**, **Bicep** under `infra/`, and **GitHub Actions** (`.github/workflows/deploy-azure.yml`) for build/push/update. Infrastructure targets an **existing resource group** (you create it first); the template deploys Log Analytics, Azure Container Registry (ACR), a Container Apps environment, and a Container App with **external HTTPS ingress**. The first revision uses Microsoft’s public sample image on **port 80** so the app is healthy until CI runs; each deploy then switches ingress **target port to 8501** for Streamlit and updates the image from ACR.

**Prerequisites**

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) logged in (`az login`)
- An Azure subscription
- A resource group in your chosen region (example: `doldata-rg` in **eastus** — Azure region id is `eastus`, not `east-us`)
- A GitHub repository for this code

**One-time: resource group (if it does not exist yet)**

```bash
az group create --name doldata-rg --location eastus
```

**One-time: GitHub → Azure authentication**

*Option A — OIDC (recommended)*

1. In Microsoft Entra ID, register an **App registration** (single-tenant is typical).
2. Under **Certificates & secrets** → **Federated credentials**, add a credential for GitHub Actions, for example:
   - **Issuer**: `https://token.actions.githubusercontent.com`
   - **Subject identifier**: `repo:YOUR_GITHUB_ORG/YOUR_REPO_NAME:ref:refs/heads/main`
   - For manual **Run workflow** from other branches, add additional federated credentials with the matching `ref:refs/heads/BRANCH` subjects, or use a [GitHub Environment](https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment) and subject `repo:ORG/REPO:environment:YOUR_ENV_NAME`.
3. Grant the app’s service principal access to your Azure resources (simplest: **Contributor** on the target resource group, which includes push/update rights for ACR and Container Apps in that group).

Add these **GitHub repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | App registration (client) ID |
| `AZURE_TENANT_ID` | Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID |

*Option B — Service principal (fallback)*

Create a client secret on the same app registration and store the full JSON output of `az ad sp create-for-rbac` (or equivalent) as **`AZURE_CREDENTIALS`**. In the workflow, replace the **Azure Login (OIDC)** step with:

```yaml
- uses: azure/login@v2
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}
```

**One-time: deploy infrastructure (Bicep)**

From the repo root, using your resource group and a parameters file (copy and edit `infra/parameters.example.json` if you like):

```bash
az deployment group create \
  --resource-group doldata-rg \
  --template-file infra/main.bicep \
  --parameters @infra/parameters.example.json
```

**Important:** `minReplicas` defaults to **1** in the template so the app does not scale to zero (Streamlit avoids painful cold starts). To allow scale-to-zero, set `minReplicas` to `0` in your parameters file and redeploy.

**Contributor vs role assignments:** Granting **AcrPull** via `Microsoft.Authorization/roleAssignments` requires **`Microsoft.Authorization/roleAssignments/write`**, which **Contributor** does not have (only **Owner** or **User Access Administrator** do). This Bicep template therefore enables the **ACR admin account** and configures the Container App to pull with **username + password** (password stored as a Container App secret), which works with **Contributor** on the resource group. To harden later, an admin can disable the ACR admin user, enable a **system-assigned identity** on the Container App, assign **AcrPull** to that identity on the registry, and reconfigure the app to use registry authentication with that identity instead of the stored password.

Capture outputs (names and FQDN):

```bash
az deployment group show \
  --resource-group doldata-rg \
  --name DEPLOYMENT_NAME \
  --query properties.outputs -o json
```

Set these **GitHub Actions variables** (Settings → Secrets and variables → Actions → Variables) to match the deployment outputs:

| Variable | Source (Bicep output) |
|----------|----------------------|
| `AZURE_RESOURCE_GROUP` | Your RG name (e.g. `doldata-rg`) |
| `ACR_NAME` | `acrName` |
| `CONTAINER_APP_NAME` | `containerAppName` |

**Ongoing deploys (one-click)**

- Push to **`main`**, or
- Actions → **Deploy to Azure Container Apps** → **Run workflow**

The workflow builds the root `Dockerfile`, pushes `YOUR_ACR.azurecr.io/ae-dashboard:<git-sha>` and `:latest`, runs `az containerapp update` for the new image, then `az containerapp ingress update --target-port 8501` so Streamlit’s listen port matches ingress.

**Environment variables / secrets for Salesforce**

Never commit real secrets. For local Docker, use `-e` or an env file (not copied into the image; `.dockerignore` excludes `.env`). For Container Apps:

- **Portal**: Container App → **Settings** → **Environment variables** and **Secrets** (reference secrets from env vars).
- **CLI**: create a secret, then bind it (example pattern):

```bash
az containerapp secret set \
  --name YOUR_CONTAINER_APP_NAME \
  --resource-group YOUR_RG \
  --secrets "salesforce-client-secret=REPLACE_WITH_VALUE"

az containerapp update \
  --name YOUR_CONTAINER_APP_NAME \
  --resource-group YOUR_RG \
  --set-env-vars "SALESFORCE_CLIENT_SECRET=secretref:salesforce-client-secret"
```

Expected application variables (see root `.env.example` and `scripts/.env.example` for detail):

| Variable | Notes |
|----------|--------|
| `SALESFORCE_CLIENT_ID` | Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | Use a secret reference in production |
| `SALESFORCE_REDIRECT_URI` | **Must exactly match** the callback URL in Salesforce and your app URL (e.g. `https://<container-app-fqdn>/` — use the HTTPS URL shown on the Container App **Overview**; include or omit a trailing slash to match the Connected App callback **exactly**) |
| `SALESFORCE_SANDBOX` | `true` / `false` |
| `SALESFORCE_LOGIN_URL` | Optional custom login domain |
| `SALESFORCE_OAUTH_SCOPES` | Optional; defaults suit typical Connected Apps |

Use **GitHub Actions secrets** for the pipeline’s Azure login only; Salesforce credentials belong in Container Apps secrets/env, not in the repo.

**Optional:** Azure Key Vault integration is not included here to keep scope small; add it later if you want centralized secret storage.

## 🔒 Security Notes

- Never commit `.env` (it's in .gitignore)
- **OAuth** – no passwords stored; users sign in via Salesforce; tokens stay in session only
- Username/password – credentials in env vars only
- Enable HTTPS for cloud deployments

## 📈 Performance

- 3 bulk queries (vs 150+ individual queries)
- 5-minute cache
- Loads 50 AEs in ~2-3 seconds

## 🆘 Troubleshooting

### Can't connect to Salesforce
- **OAuth**: Ensure Callback URL in Connected App matches `SALESFORCE_REDIRECT_URI` exactly
- **Username/password**: Verify security token is current (reset if needed)
- Test with Salesforce Workbench

### Custom fields not found
- Create `Monthly_Quota__c` on User object
- Create `Pipeline_Coverage_Ratio__c` on User object
- Or use hardcoded values (see setup guide)

### Different stage names
- Check your Salesforce stage values
- Modify queries to match your org

## 📚 Documentation

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Folder organization
- **[docs/CUSTOMIZATION_GUIDE.md](docs/CUSTOMIZATION_GUIDE.md)** - How to customize
- **[docs/SALESFORCE_CONNECTED_APP_SETUP.md](docs/SALESFORCE_CONNECTED_APP_SETUP.md)** - OAuth setup
- **[docs/AZURE_AD_SETUP.md](docs/AZURE_AD_SETUP.md)** - Why Azure AD / MSAL is not in this app anymore

See [docs/STREAMLIT_SETUP_GUIDE.md](docs/STREAMLIT_SETUP_GUIDE.md) for:
- Detailed installation steps
- SOQL query customization
- Deployment options
- Advanced features

## 🆚 vs Native Salesforce

**Advantages:**
- ✅ No code deployment to Salesforce
- ✅ Faster development and iteration
- ✅ More flexible (add charts, custom logic)
- ✅ Works with any Salesforce edition

**Trade-offs:**
- ⚠️ External application to maintain
- ⚠️ Separate authentication
- ⚠️ API call limits apply

## 🤝 Support

For issues:
1. Check `STREAMLIT_SETUP_GUIDE.md`
2. Test SOQL queries in Salesforce Workbench
3. Review error messages in terminal

## 📄 License

MIT License - Free to use and modify
