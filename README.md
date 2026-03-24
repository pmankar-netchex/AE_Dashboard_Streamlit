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

### Microsoft Azure AD (Optional)

**NEW:** The dashboard supports optional Azure AD / MSAL authentication to control who can access the dashboard.

- When enabled, users must sign in with their Microsoft account **before** accessing the dashboard
- Then they connect to Salesforce as usual
- Perfect for enterprise deployments requiring centralized access control

**Setup:** See [docs/AZURE_AD_SETUP.md](docs/AZURE_AD_SETUP.md) for complete configuration guide.

**Quick Enable:**
```bash
# Add to .env after setting up Azure AD app registration
AZURE_CLIENT_ID=your_azure_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_azure_secret
AZURE_REDIRECT_URI=http://localhost:8501

# Optional: Restrict to specific domains
AZURE_ALLOWED_DOMAINS=company.com
```

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

**🔒 Persistent Authentication:** After your first login, the dashboard saves your refresh token locally in `~/.salesforce_tokens/ae_dashboard.json`. You won't need to reconnect unless:
- You click "Disconnect"
- The refresh token expires (typically after 90 days of inactivity, or per your org's session settings)
- The token becomes invalid

The dashboard automatically refreshes your access token when needed, so you can just refresh the page and keep working.

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
├── startup.sh                     Azure App Service startup script
├── src/                           Application modules
│   ├── msal_auth.py               Azure AD / MSAL authentication
│   ├── salesforce_oauth.py        Salesforce OAuth flow
│   ├── token_storage.py           Token persistence (Key Vault or filesystem)
│   ├── soql_registry.py           SOQL query definitions
│   ├── data_engine.py             Data processing and dataframe assembly
│   ├── meta_filters.py            Time period and filter logic
│   └── dashboard_ui.py            UI components, CSS, charts
├── infra/                         Azure Bicep infrastructure-as-code
├── scripts/                       Deployment and setup scripts
├── docs/                          Documentation
├── .streamlit/config.toml         Streamlit server configuration
├── .env                           Your credentials (not committed)
└── requirements.txt               Python dependencies
```

## 🔧 Customization

The dashboard is **modularized** for easy customization. See [docs/CUSTOMIZATION_GUIDE.md](docs/CUSTOMIZATION_GUIDE.md) for detailed instructions.

**Quick examples:**

- **Change SOQL queries**: Edit `src/soql_registry.py` (column definitions, query builder)
- **Filter logic**: Edit `src/meta_filters.py` (time periods, filter parameters)
- **Data processing**: Edit `src/data_engine.py` (dataframe assembly, manager/AE lists)
- **Colors/styling**: Edit `src/dashboard_ui.py` (CSS, KPI widgets, charts)

## 📦 Deployment Options

### Local Development
```bash
streamlit run streamlit_dashboard.py
```

### Azure Deployment (from your machine)

Deploy to Azure App Service using the CLI. Requires Azure CLI and PowerShell 7+.

**Prerequisites:**
```powershell
az login                     # Sign into Azure
az bicep install             # Install Bicep CLI (if not already)
```

**1. Create the resource group** (skip if already exists):
```powershell
az group create --name "doldata-rg" --location "eastus"
```

**2. Register an Azure AD app** (for user authentication):
- Azure Portal > Microsoft Entra ID > App registrations > New registration
- Name: `AE Dashboard`, Single tenant, Redirect URI: `https://netchex-ae-dashboard.azurewebsites.net`
- Copy the **Client ID** and **Tenant ID** from the Overview page
- Create a **Client secret** under Certificates & secrets
- See [docs/AZURE_DEPLOYMENT_GUIDE.md](docs/AZURE_DEPLOYMENT_GUIDE.md) for detailed steps

**3. Restrict access to specific users:**
- Azure Portal > Microsoft Entra ID > Enterprise applications > find `AE Dashboard`
- Properties > set **Assignment required?** = **Yes** > Save
- Users and groups > Add the specific users who should have access

**4. Deploy:**
```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "netchex-ae-dashboard" `
    -AppServicePlanId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/serverfarms/<plan>" `
    -AzureAdClientId "your-client-id" `
    -AzureAdTenantId "your-tenant-id" `
    -AzureAdClientSecret "your-client-secret" `
    -AzureAllowedEmails "user1@company.com,user2@company.com"
```

This provisions infrastructure (Bicep), zip-deploys the application code, and configures the App Service. The app shares an App Service Plan with the DOL app (passed via `-AppServicePlanId`).

**5. Configure Salesforce credentials:**
```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "netchex-ae-dashboard" `
    -AppServicePlanId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/serverfarms/<plan>" `
    -SkipInfra -SkipDeploy -ConfigureSettings
```

**6. Verify:** Visit `https://netchex-ae-dashboard.azurewebsites.net` — you should see the Microsoft login page.

For code-only redeployments (infra already exists):
```powershell
.\scripts\deploy.ps1 `
    -ResourceGroupName "doldata-rg" `
    -AppName "netchex-ae-dashboard" `
    -AppServicePlanId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/serverfarms/<plan>" `
    -SkipInfra
```

**Tip:** After updating App Settings manually (via `az webapp config appsettings set`), restart the app to pick up changes:
```powershell
az webapp restart --resource-group "doldata-rg" --name "netchex-ae-dashboard"
```

See [docs/AZURE_DEPLOYMENT_GUIDE.md](docs/AZURE_DEPLOYMENT_GUIDE.md) for the full guide including troubleshooting, parameter reference, and CI/CD pipeline setup.

## 🔒 Security Notes

- Never commit `.env` (it's in .gitignore)
- **Azure AD** – MSAL authentication gates access; restrict users via Enterprise App assignments + email/domain allowlists
- **Salesforce OAuth** – no passwords stored; users sign in via Salesforce
- **Key Vault** – Salesforce refresh tokens stored in Azure Key Vault (via App Service managed identity); falls back to local filesystem for dev
- **HTTPS** – enforced by Azure App Service (`httpsOnly: true` in Bicep)

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

- **[docs/AZURE_DEPLOYMENT_GUIDE.md](docs/AZURE_DEPLOYMENT_GUIDE.md)** - Full Azure deployment guide (Bicep, zip deploy, CI/CD)
- **[docs/AZURE_AD_SETUP.md](docs/AZURE_AD_SETUP.md)** - Azure AD / MSAL authentication setup
- **[docs/SALESFORCE_CONNECTED_APP_SETUP.md](docs/SALESFORCE_CONNECTED_APP_SETUP.md)** - Salesforce OAuth setup
- **[docs/CUSTOMIZATION_GUIDE.md](docs/CUSTOMIZATION_GUIDE.md)** - How to customize queries, UI, and logic
- **[docs/STREAMLIT_SETUP_GUIDE.md](docs/STREAMLIT_SETUP_GUIDE.md)** - Local development setup
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Folder organization

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
