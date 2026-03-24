# src/ — Business Logic Modules

All Salesforce data fetching, metric calculations, UI rendering, and authentication live here. Functions only — no classes.

## OVERVIEW

7 modules, clear single-responsibility: queries → calculations → UI, plus auth + token persistence.

## WHERE TO LOOK

| Task | File | Key Function(s) |
|------|------|------------------|
| Add/change SOQL queries | `salesforce_queries.py` | `get_all_opportunities()`, `get_all_meetings()`, etc. |
| Change metric formulas | `dashboard_calculations.py` | `build_dashboard_data()` (line 39), `calculate_meetings_needed()` |
| Modify CSS/table styling | `dashboard_ui.py` | `apply_custom_css()` (line 13), `get_column_config()` |
| Add display columns | `dashboard_ui.py` | `prepare_display_df()`, `get_column_config()` |
| Change Salesforce OAuth | `salesforce_oauth.py` | `exchange_code_for_tokens()`, `refresh_access_token()` |
| Change Azure AD flow | `msal_auth.py` | `exchange_code_for_token()`, `check_user_authorization()` |
| Change token persistence | `token_storage.py` | `save_tokens()`, `load_tokens()` — path: `~/.salesforce_tokens/` |

## MODULE MAP

| Module | Lines | Depends On | Consumed By |
|--------|-------|------------|-------------|
| `salesforce_queries.py` | 372 | `streamlit`, `pandas`, Salesforce client | `streamlit_dashboard.py` via `load_dashboard_data()` |
| `dashboard_calculations.py` | 129 | `pandas` | `streamlit_dashboard.py` via `load_dashboard_data()` |
| `dashboard_ui.py` | 329 | `streamlit`, `pandas` | `streamlit_dashboard.py` main display |
| `salesforce_oauth.py` | 126 | `requests`, env vars | `streamlit_dashboard.py` auth section |
| `msal_auth.py` | 366 | `msal`, `streamlit`, env vars | `streamlit_dashboard.py` MSAL gate |
| `token_storage.py` | 60 | `pathlib`, `json` | `salesforce_oauth.py`, `streamlit_dashboard.py` |

## CONVENTIONS

- **Section headers** — `# ===...===` blocks separate entity groups within files
- **Query pattern** — all SOQL functions accept `(sf, ...)` where `sf` is a `simple_salesforce.Salesforce` instance
- **Bulk aggregation** — queries use `GROUP BY OwnerId` and return `dict[owner_id → value]`, never per-user queries
- **Error handling** — SOQL functions catch exceptions and return empty DataFrames/dicts with `st.warning()`
- **Sentinel value** — `NO_HISTORIC_DATA = -99` in `dashboard_calculations.py`; never use `None` or `0` for missing historic data
- **Token file perms** — `0o600` on `~/.salesforce_tokens/ae_dashboard.json`; never weaken

## ANTI-PATTERNS

- **Never query per-user** — always bulk fetch with `GROUP BY` or `IN (ids)` clauses
- **Never import between src modules** — each module is consumed only by `streamlit_dashboard.py`; no circular deps
- **Never suppress SOQL errors silently** — always `st.warning()` on failure
- **Never store tokens in session_state alone** — `token_storage.py` persists to disk for cross-session survival

## NOTES

- `msal_auth.py` (366 lines) is the largest module but entirely optional — skipped when `AZURE_CLIENT_ID` is unset
- `ForecastingItem`/`ForecastingQuota` queries in `salesforce_queries.py` fail if Forecasting isn't enabled in the org; callers handle empty results
- `dashboard_ui.py` column ordering is hardcoded in `prepare_display_df()` — add new metric columns there AND in `get_column_config()`
- Custom field `Manager_Name__c` is expected on User object; `Months_On_Quota__c` also queried but optional
