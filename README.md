# AE Performance Dashboard

> **Overhaul in progress on `overhaul/v2`.** The Streamlit app is being replaced
> by a FastAPI backend + React/Tailwind/TanStack frontend with Entra ID auth,
> client-credentials Salesforce flow, admin/user roles, and scheduled email
> digests. See `/Users/apple/.claude/plans/we-are-going-to-fancy-lagoon.md`.
>
> New layout:
> - `backend/` — FastAPI service (`cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`)
> - `frontend/` — Vite + React (`cd frontend && npm install && npm run dev`)
> - `infra/` — Bicep for Azure Container Apps deployment
>
> The legacy Streamlit app (`streamlit_dashboard.py`, `src/`) is preserved
> on `overhaul/v2` until cutover (milestone M15) and remains the production
> code on `main` for now.

---

## Legacy Streamlit app (current production)

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
├── Dockerfile                     Container image for Azure / Docker
├── infra/                         Azure Bicep (optional IaC)
├── src/                           Application modules (⚙️ customize here)
├── scripts/                       Setup, run, deploy_containerapp_local.sh
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

## 🗂 SOQL templates — Azure Table Storage + snapshot

Active SOQL templates for every dashboard column live in an Azure Table Storage table (`queries` on `staedashboardens2xr`) rather than in the image. This means edits made from the in-app SOQL test tab **persist across Container App revisions** — they are not wiped by a redeploy.

`src/soql_registry.py` still declares every column (id, display name, section, aggregation, default template) — treat those defaults as the seed values. On cold start, `seed_missing()` inserts any new column's default into the table; the table value is the runtime source of truth from then on.

### queries_snapshot.json (git-tracked)

`queries_snapshot.json` at the repo root is an audit-friendly export of the table, committed to git. It is the disaster-recovery source if the table is ever wiped.

### Sync script

```bash
python scripts/sync_queries.py --export   # Table → queries_snapshot.json
python scripts/sync_queries.py --import   # queries_snapshot.json → Table (recovery)
python scripts/sync_queries.py --diff     # show pending differences
python scripts/sync_queries.py --check    # exit 1 if out of sync (for CI/hooks)
```

All modes require `AZURE_STORAGE_CONNECTION_STRING` pointing at the dashboard storage account.

### Pre-push guard + deploy guard

- `.githooks/pre-push` runs `--check` before every push. Aborts if the table has edits the snapshot doesn't reflect.
- `scripts/deploy_containerapp_local.sh` runs `--export` before building so a deploy never clobbers unmerged table edits. Override with `SKIP_SYNC=1` only if deliberate.

### One-time setup on a new workstation

```bash
# 1. Enable the pre-push hook
git config core.hooksPath .githooks

# 2. Persist the storage connection string in your shell rc
#    (get the value from: az storage account show-connection-string \
#        --name staedashboardens2xr --resource-group doldata-rg -o tsv)
echo 'export AZURE_STORAGE_CONNECTION_STRING="<paste value>"' >> ~/.zshrc
source ~/.zshrc
```

After this, the pre-push hook runs automatically on every `git push` and the deploy script auto-exports. If the hook aborts, run `python scripts/sync_queries.py --export && git add queries_snapshot.json` and retry the push.

---

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

**Bicep** under `infra/` provisions an **existing resource group**: Log Analytics, Azure Container Registry (ACR), a Container Apps environment, and a Container App with **external HTTPS ingress**. The first revision uses Microsoft’s public sample image on **port 80**; after you run the local deploy script, the app uses your image and ingress **target port 8501** for Streamlit.

**Prerequisites**

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az login`)
- A subscription and a resource group (example: `doldata-rg` in **eastus**)
- [Docker](https://docs.docker.com/get-docker/) on the machine you deploy from

**One-time: resource group (if needed)**

```bash
az group create --name doldata-rg --location eastus
```

**One-time: infrastructure (Bicep)**

From the repo root (copy and edit `infra/parameters.example.json` if you like):

```bash
az deployment group create \
  --resource-group doldata-rg \
  --template-file infra/main.bicep \
  --parameters @infra/parameters.example.json
```

**Important:** `minReplicas` defaults to **1** so the app does not scale to zero (Streamlit avoids painful cold starts). Set `minReplicas` to `0` in parameters if you want scale-to-zero.

**Contributor vs role assignments:** Granting **AcrPull** via `Microsoft.Authorization/roleAssignments` requires **Owner** or **User Access Administrator**. **Contributor** cannot create those assignments. This template enables the **ACR admin user** and stores the registry password as a Container App secret so **Contributor** on the resource group can deploy. To harden later, an admin can switch to managed identity + **AcrPull** and disable the ACR admin user.

Save deployment outputs (you will pass them to the deploy script or use `--from-deployment`):

```bash
az deployment group show \
  --resource-group doldata-rg \
  --name DEPLOYMENT_NAME \
  --query properties.outputs -o json
```

**Ongoing: deploy from your laptop**

Uses the root `Dockerfile`, **`az login`**, Docker build/push to ACR, and `az containerapp update` (same flow as the removed CI pipeline, without GitHub secrets):

```bash
az login
# optional: az account set --subscription <id>
./scripts/deploy_containerapp_local.sh \
  --resource-group doldata-rg \
  --from-deployment YOUR_DEPLOYMENT_NAME
```

Or pass ACR and Container App names explicitly:

```bash
./scripts/deploy_containerapp_local.sh \
  --resource-group doldata-rg \
  --acr-name YOUR_ACR_NAME \
  --app-name YOUR_CONTAINER_APP_NAME
```

You need permission to **push to ACR** and **update** the Container App (e.g. Contributor on the RG). The script tags the image with the short git SHA (or a timestamp) and updates `:latest`.

**Apple Silicon / ARM laptops:** Container Apps need **linux/amd64** images. The script uses `docker build --platform linux/amd64` by default. If cross-build is slow or flaky, build in Azure instead (no local Docker build):

```bash
./scripts/deploy_containerapp_local.sh --resource-group doldata-rg --from-deployment YOUR_NAME --acr-build
```

**Environment variables / secrets for Salesforce**

Never commit real secrets. For local Docker, use `-e` or an env file (`.dockerignore` excludes `.env`). For Container Apps:

- **Portal**: Container App → **Settings** → **Environment variables** and **Secrets**
- **CLI** — same fields as `.env.example` / `scripts/.env.example` (replace placeholders; **omit** optional `--set-env-vars` pairs you do not use):

**OAuth (recommended)** — set `SALESFORCE_REDIRECT_URI` to your Container App HTTPS URL (must match the Connected App callback exactly):

```bash
APP_NAME=YOUR_CONTAINER_APP_NAME
RG=YOUR_RESOURCE_GROUP

az containerapp secret set \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --secrets "salesforce-client-secret=PASTE_CONSUMER_SECRET_HERE"

az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --set-env-vars \
    "SALESFORCE_CLIENT_ID=PASTE_CONSUMER_KEY_HERE" \
    "SALESFORCE_CLIENT_SECRET=secretref:salesforce-client-secret" \
    "SALESFORCE_REDIRECT_URI=https://YOUR_CONTAINER_APP_FQDN/" \
    "SALESFORCE_SANDBOX=false" \
    "SALESFORCE_LOGIN_URL=https://your-org.my.salesforce.com" \
    "SALESFORCE_OAUTH_SCOPES=api refresh_token offline_access"
```

Remove the `SALESFORCE_LOGIN_URL` line if you use default login hosts; remove `SALESFORCE_OAUTH_SCOPES` to use the app’s built-in default (`api refresh_token offline_access`).

**Username / password (legacy)** — add secrets, then extend env vars (only if you use this mode):

```bash
az containerapp secret set \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --secrets \
    "salesforce-password=PASTE_PASSWORD" \
    "salesforce-security-token=PASTE_SECURITY_TOKEN"

az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --set-env-vars \
    "SALESFORCE_USERNAME=your_email@company.com" \
    "SALESFORCE_PASSWORD=secretref:salesforce-password" \
    "SALESFORCE_SECURITY_TOKEN=secretref:salesforce-security-token"
```

**Optional:** append `"DEBUG=1"` to a `--set-env-vars` list to match `scripts/.env.example` debug mode.

Expected variables (see `.env.example` and `scripts/.env.example`):

| Variable | Notes |
|----------|--------|
| `SALESFORCE_CLIENT_ID` | Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | Prefer a secret reference in Azure |
| `SALESFORCE_REDIRECT_URI` | **Must exactly match** the Connected App callback and your app URL (e.g. `https://<container-app-fqdn>/` — match trailing slash **exactly**) |
| `SALESFORCE_SANDBOX` | `true` / `false` |
| `SALESFORCE_LOGIN_URL` | Optional |
| `SALESFORCE_OAUTH_SCOPES` | Optional |
| `SALESFORCE_USERNAME` | Legacy login only |
| `SALESFORCE_PASSWORD` | Legacy; use a secret reference in Azure |
| `SALESFORCE_SECURITY_TOKEN` | Legacy; use a secret reference in Azure |
| `DEBUG` | Optional; `1` to show extra filter debug in the app |

Keep Salesforce credentials in Container Apps (or Key Vault), not in git.

**Optional:** Azure Key Vault is not wired in this template; add it if you want centralized secrets.

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

### Container App: `no child with platform linux/amd64` (invalid image)

The image in ACR was built for **ARM64** (e.g. Mac M-series) only. Rebuild for **amd64** and redeploy:

- Run the latest `./scripts/deploy_containerapp_local.sh` (it defaults to `--platform linux/amd64`), or use **`--acr-build`** so ACR builds the image in Azure.

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
