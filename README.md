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

### OAuth Login (Recommended – like n8n)

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
docker run -p 8501:8501 ae-dashboard
```

## 🔒 Security Notes

- Never commit `.env` (it's in .gitignore)
- **OAuth** – no passwords stored; users sign in via Salesforce
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
