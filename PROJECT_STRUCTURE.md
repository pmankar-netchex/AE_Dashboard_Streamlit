# Project Structure

Clean folder organization for easy navigation and maintenance.

```
AE_Dashboard_Streamlit/
│
├── streamlit_dashboard.py         # Main entry point (run this)
│
├── src/                           # Application modules
│   ├── __init__.py
│   ├── salesforce_queries.py      # ⚙️ SOQL queries by entity
│   ├── dashboard_calculations.py  # ⚙️ Business logic & formulas
│   ├── dashboard_ui.py            # ⚙️ Display & styling
│   ├── salesforce_oauth.py        # Salesforce OAuth 2.0 login flow
│   ├── msal_auth.py               # Azure AD / MSAL authentication
│   └── token_storage.py           # Persistent token storage
│
├── scripts/                       # Setup & deployment
│   ├── setup.sh                   # One-time setup (venv, deps, .env)
│   ├── run.sh                     # Run the dashboard
│   └── .env.example               # Credentials template
│
├── docs/                          # Documentation
│   ├── CUSTOMIZATION_GUIDE.md     # How to customize SOQL/formulas
│   ├── MODULE_STRUCTURE.md        # Code architecture explained
│   ├── SALESFORCE_CONNECTED_APP_SETUP.md  # Salesforce OAuth setup
│   ├── AZURE_AD_SETUP.md          # Azure AD / MSAL setup (optional)
│   └── STREAMLIT_SETUP_GUIDE.md   # Complete setup guide
│
├── .env                           # Your credentials (gitignored)
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Folder Purposes

| Folder | Purpose | Customize? |
|--------|---------|------------|
| `src/` | Application code | ✓ Yes - queries, formulas, UI |
| `scripts/` | Setup & run scripts | Rarely |
| `docs/` | Documentation | No |
| Root | Entry point, config | No |

## Quick Access

**To customize SOQL queries:**
→ `src/salesforce_queries.py`

**To customize business logic:**
→ `src/dashboard_calculations.py`

**To customize UI/styling:**
→ `src/dashboard_ui.py`

**To set up Salesforce OAuth:**
→ `docs/SALESFORCE_CONNECTED_APP_SETUP.md`

**To set up Azure AD authentication (optional):**
→ `docs/AZURE_AD_SETUP.md`

**To run:**
→ `./scripts/run.sh`

## Development Workflow

1. **Setup** (once): `./scripts/setup.sh`
2. **Configure**: Edit `.env` with credentials
3. **Customize**: Edit files in `src/` (see `docs/CUSTOMIZATION_GUIDE.md`)
4. **Run**: `./scripts/run.sh`
5. **Deploy**: See `docs/STREAMLIT_SETUP_GUIDE.md`

## Benefits of This Structure

- ✅ **Separation of concerns** - Code, scripts, docs separated
- ✅ **Easy to find** - Queries in `src/salesforce_queries.py`, not scattered
- ✅ **Clean root** - Only entry point and essential config visible
- ✅ **Scalable** - Easy to add more modules to `src/`
- ✅ **Professional** - Standard Python project layout
