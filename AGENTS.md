# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-26
**Commit:** 599c8be
**Branch:** main

## OVERVIEW

Streamlit dashboard querying Salesforce via SOQL to display AE (Account Executive) performance metrics. Dual auth: Salesforce OAuth + optional Azure AD/MSAL. Single-page app, modular `src/` backend.

## STRUCTURE

```
./
├── streamlit_dashboard.py    # Monolithic entry (803 lines) — auth + filters + UI
├── src/                      # Business logic modules (see src/AGENTS.md)
│   ├── salesforce_queries.py # SOQL by entity (Users, Opps, Forecast, Activity, Meetings)
│   ├── dashboard_calculations.py  # Metrics formulas
│   ├── dashboard_ui.py       # CSS, column config, display helpers
│   ├── salesforce_oauth.py   # OAuth 2.0 Web Server Flow
│   ├── msal_auth.py          # Azure AD (optional pre-gate)
│   └── token_storage.py      # Persistent refresh tokens (~/.salesforce_tokens/)
├── scripts/                  # setup.sh, run.sh, .env.example
└── docs/                     # 6 markdown guides (setup, customization, Azure AD)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/modify SOQL queries | `src/salesforce_queries.py` | Organized by entity with section headers |
| Change metric formulas | `src/dashboard_calculations.py` | `build_dashboard_data()` line 39 |
| Modify table styling/columns | `src/dashboard_ui.py` | CSS in `apply_custom_css()`, columns in `get_column_config()` |
| Change auth flow | `src/salesforce_oauth.py` or `src/msal_auth.py` | OAuth is primary, MSAL is optional gate |
| Add sidebar filters | `streamlit_dashboard.py` lines 402-693 | Amazon-style expander pattern |
| Configure credentials | `scripts/.env.example` → `.env` | 20+ env vars, grouped by feature |
| Change stage name | `src/salesforce_queries.py` line 79 | Currently `'Closed/Won'` |
| Adjust meetings formula | `src/dashboard_calculations.py` line 17 | `avg_deal_size`, `win_rate` params |

## CONVENTIONS

- **No linter/formatter configured** — follow implicit PEP 8 style in existing code
- **Pinned deps** — `requirements.txt` with exact versions, no ranges
- **Section headers** — `# ===...===` comment blocks to organize code within files
- **Docstrings** — module-level + function-level, concise
- **Imports** — stdlib → third-party → local, blank lines between groups
- **Env vars** — ALL_CAPS_UNDERSCORE, all secrets in `.env` (gitignored), never hardcoded
- **Functions over classes** — entire codebase is function-based, no OOP

## ANTI-PATTERNS (THIS PROJECT)

- **Never hardcode credentials** — all secrets via `.env` / env vars
- **Never commit `.env`** — it's in `.gitignore`
- **Plotly is unused** — listed in requirements but no imports; don't add Plotly usage without removing or acknowledging this
- **Token storage uses local filesystem** — `~/.salesforce_tokens/ae_dashboard.json` with `0o600` perms; not suitable for multi-user deployments
- **No tests exist** — no pytest, no test directory, no coverage; manual testing only via `streamlit run`
- **No CI/CD** — no GitHub Actions, no Dockerfile in repo (only documented in docs)

## UNIQUE STYLES

- **Dual auth system** — Salesforce OAuth (primary) + Azure AD/MSAL (optional pre-gate). OAuth callbacks distinguished by presence of `state` query param (SF has both `code`+`state`, MSAL has only `code`)
- **Persistent OAuth tokens** — refresh tokens survive app restarts via `token_storage.py`; auto-refresh on expiry
- **Amazon-style sidebar filters** — categorical (multiselect with All/None buttons) + numeric (Range/Min/Max radio toggle), all in `st.sidebar` expanders
- **3-query bulk pattern** — fetches all opportunities in 3 SOQL queries, not N per user; aggregation at Salesforce level via `GROUP BY OwnerId`
- **`NO_HISTORIC_DATA = -99` sentinel** — used in `dashboard_calculations.py` to distinguish "no data" from zero; falls back to 5.0x coverage ratio
- **Query params as state** — month/year persisted in URL via `st.query_params` for bookmarkable views

## COMMANDS

```bash
./setup.sh                              # Create venv, install deps, generate .env
./run.sh                                # Activate venv, load .env, run streamlit
streamlit run streamlit_dashboard.py    # Direct run (after manual venv activation)
```

## DATA FLOW

```
streamlit_dashboard.py::main()
  → MSAL auth check (optional)
  → Salesforce OAuth / saved tokens / username-password fallback
  → load_dashboard_data(sf, month, year)
    → src/salesforce_queries.py  (7 SOQL functions, bulk fetch)
    → src/dashboard_calculations.py::build_dashboard_data()  (metrics + formulas)
  → Sidebar filters (categorical + numeric)
  → src/dashboard_ui.py  (prepare_display_df → style → st.dataframe)
  → CSV export + insights
```

## NOTES

- `streamlit_dashboard.py` is 803 lines — monolithic; auth, filters, and display are interleaved. Read `main()` (line 240) for the full flow.
- MSAL is entirely optional — if `AZURE_CLIENT_ID` is not set, the entire Azure AD flow is skipped.
- `ForecastingItem` and `ForecastingQuota` SOQL queries may fail if Forecasting is not enabled in the Salesforce org.
- Filter state is fragile — multiselect defaults reconstruct from `st.session_state` on every rerun. Adding new filter types requires careful state initialization.
- `DEBUG=1` or `?debug=1` enables filter value display in an expander.
