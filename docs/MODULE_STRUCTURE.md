# Dashboard Module Structure

## Architecture

```
AE_Dashboard_Streamlit/
├── streamlit_dashboard.py        # Main entry point — auth, 3-tab layout, orchestration
├── src/
│   ├── soql_registry.py          # ⚙️ Canonical SOQL for all 28 metric columns
│   ├── data_engine.py            # ⚙️ Query execution, error isolation, DataFrame builder
│   ├── meta_filters.py           # ⚙️ Time period helpers, filter param builder
│   ├── dashboard_ui.py           # ⚙️ KPI widgets, charts, heatmap, table, tooltips
│   ├── salesforce_oauth.py       # Salesforce OAuth 2.0 flow
│   ├── msal_auth.py              # Azure AD / MSAL authentication
│   └── token_storage.py          # Persistent OAuth token storage
├── scripts/
│   ├── setup.sh                  # Setup script (venv + deps)
│   ├── run.sh                    # Run script
│   └── .env.example              # Config template
├── docs/
│   ├── MODULE_STRUCTURE.md       # This file
│   ├── CUSTOMIZATION_GUIDE.md    # How to customize queries and UI
│   ├── AZURE_AD_SETUP.md         # Azure AD / MSAL setup guide
│   ├── MSAL_FEATURES.md          # MSAL feature reference
│   ├── SALESFORCE_CONNECTED_APP_SETUP.md
│   └── STREAMLIT_SETUP_GUIDE.md
├── implementation-specs.md       # Canonical metric definitions and SOQL spec
├── .env                          # Your credentials (gitignored)
└── requirements.txt              # Python deps
```

## Module Responsibilities

### `src/soql_registry.py` — SOQL Registry
The single source of truth for all metric queries. Contains 28 `SOQLEntry` objects (columns C–AD as defined in `implementation-specs.md`), each with:
- Column ID (e.g. `S1-COL-C`), display name, section, description
- Parameterized SOQL template with `{owner_clause}`, `{time_start_date}`, etc.
- `time_filter` flag — `False` means the column uses fixed date windows (fiscal year, this month, next month) and is immune to the meta time-period selector

**Do not edit filter logic here.** Only edit SOQL via the SOQL Management tab in the dashboard UI (which validates queries against Salesforce before saving).

### `src/data_engine.py` — Data Engine
Executes registry queries and builds the unified DataFrame:
- `fetch_column()` — runs one SOQL with per-query error isolation (failure → `None` for that column only, rest of dashboard unaffected)
- `fetch_all_columns()` — runs all columns for one AE; computes columns E and H (quota attainment %) in Python
- `build_dashboard_dataframe()` — iterates AEs, calls `fetch_all_columns`, returns one-row-per-AE DataFrame
- `get_managers_list()` / `get_ae_names_list()` — populate sidebar filter dropdowns
- Accepts `overrides` dict from SOQL Management tab so saved query edits take effect immediately

### `src/meta_filters.py` — Filter Utilities
Date math and filter parameter builder:
- `resolve_time_period()` — converts "Last Week", "This Month", etc. to `(start, end)` dates
- `build_filter_params()` — returns the complete params dict passed to every SOQL query (AE ID, email, manager name, all date keys)
- `fiscal_year_start()` — returns the first day of the current fiscal year (Jan 1 by default; change `FISCAL_YEAR_START_MONTH` to adjust)

### `src/dashboard_ui.py` — UI Components
All visual rendering functions:
- `display_kpi_widgets()` — 5 aggregate KPIs at page top
- `display_dashboard_table()` — paginated, section-grouped table with global search and per-section tooltip legends
- `display_charts()` — Bookings YTD and YTD Attainment % bar charts
- `display_heatmap()` — normalized performance heatmap across all live columns
- `render_fetch_status()` — last-fetched timestamp + Refresh button
- `TOOLTIPS` dict — plain-language description of every column for non-technical reviewers

### `streamlit_dashboard.py` — App Entry Point
- Auth gate: MSAL (Azure AD) → Salesforce OAuth, in that order
- Sidebar meta filters (Manager, AE Name, Time Period)
- Three tabs: **Dashboard** · **SOQL Management** · **Salesforce Connection**
- SOQL Management tab: inline query editor with Test (must succeed) → Save workflow; override dict passed to data engine on next refresh

## What Goes Where

| Change | File | How |
|--------|------|-----|
| Edit a SOQL query | SOQL Management tab in the UI | Test → Save → Refresh Dashboard |
| Add a new metric column | `src/soql_registry.py` | Add a new `SOQLEntry`; wire into `ALL_COLUMNS` |
| Change fiscal year start | `src/meta_filters.py` | `FISCAL_YEAR_START_MONTH = <month_int>` |
| Change time period presets | `src/meta_filters.py` + `streamlit_dashboard.py` | Add entry to `mapping` dict and sidebar selectbox |
| Add a KPI widget | `src/dashboard_ui.py` | Extend the `kpis` list in `display_kpi_widgets()` |
| Change dashboard colors / CSS | `src/dashboard_ui.py` | Edit the `apply_custom_css()` CSS block |
| Change currency / percent format | `src/dashboard_ui.py` | Edit `fmt_currency()` / `fmt_percent()` |
| Add a chart | `src/dashboard_ui.py` | Extend `display_charts()` |
| Add an AE filter dimension | `src/data_engine.py` | Extend `get_ae_names_list()` and update sidebar |
| Change Salesforce auth method | `src/salesforce_oauth.py` | OAuth config; or add username/password to `.env` |
| Enable/disable Azure AD auth | `.env` | Add/remove `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` |
