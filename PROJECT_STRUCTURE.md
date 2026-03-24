# Project Structure

Clean folder organization for easy navigation and maintenance.

```
AE_Dashboard_Streamlit/
│
├── streamlit_dashboard.py         # Main entry point (run this)
│
├── src/                           # Application modules
│   ├── salesforce_oauth.py        # Salesforce OAuth 2.0 login flow
│   ├── soql_registry.py           # Canonical SOQL per metric column
│   ├── data_engine.py             # Query execution, DataFrame builder
│   ├── meta_filters.py            # Time period & filter helpers
│   └── dashboard_ui.py            # Display, charts, KPIs, styling
│
├── scripts/                       # Setup & deployment
│   ├── setup.sh                   # One-time setup (venv, deps, .env)
│   ├── run.sh                     # Run the dashboard
│   └── .env.example               # Credentials template
│
├── docs/                          # Documentation
│   ├── CUSTOMIZATION_GUIDE.md     # How to customize SOQL/UI
│   ├── MODULE_STRUCTURE.md        # Code architecture explained
│   ├── SALESFORCE_CONNECTED_APP_SETUP.md  # Salesforce OAuth setup
│   ├── AZURE_AD_SETUP.md          # Note: MSAL removed; hosting-layer IdP
│   ├── MSAL_FEATURES.md          # Note: MSAL removed
│   └── STREAMLIT_SETUP_GUIDE.md   # Complete setup guide
│
├── .env                           # Your credentials (gitignored)
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
└── README.md                      # Overview & quick start
```

## Folder Purposes

| Folder | Purpose | Customize? |
|--------|---------|------------|
| `src/` | Application code | ✓ Yes — SOQL registry, data engine, UI |
| `scripts/` | Setup & run scripts | Rarely |
| `docs/` | Documentation | No |
| Root | Entry point, config | No |

## Quick Access

**To customize SOQL / metrics:**  
→ `src/soql_registry.py` and the **SOQL Management** tab in the app

**To customize UI/styling:**  
→ `src/dashboard_ui.py`

**To set up Salesforce OAuth:**  
→ `docs/SALESFORCE_CONNECTED_APP_SETUP.md`

**To run:**  
→ `./scripts/run.sh`

## Development Workflow

1. **Setup** (once): `./scripts/setup.sh`
2. **Configure**: Edit `.env` with credentials
3. **Customize**: Edit files in `src/` (see `docs/CUSTOMIZATION_GUIDE.md`)
4. **Run**: `./scripts/run.sh`
5. **Deploy**: See `docs/STREAMLIT_SETUP_GUIDE.md`

## Benefits of This Structure

- ✅ **Separation of concerns** — Code, scripts, docs separated
- ✅ **Easy to find** — SOQL in `soql_registry.py`, rendering in `dashboard_ui.py`
- ✅ **Clean root** — Only entry point and essential config visible
- ✅ **Scalable** — Easy to add more modules to `src/`
- ✅ **Professional** — Standard Python project layout
