# AE Performance Dashboard

A sales analytics dashboard for the CRO and AE leadership team. The primary
view is the **All Source Summary** — per-AE pipeline and bookings split by
source (Self-Gen, SDR, Channel, Marketing) — backed by parameterized SOQL
against Salesforce.

> Branch `overhaul/v2` replaces the original single-file Streamlit app with
> a FastAPI backend + React/Tailwind/TanStack frontend. The legacy
> `streamlit_dashboard.py` and `src/` modules have been removed.

## Architecture

```
                    ┌──────────────────────────┐
   user (Entra)──▶  │ UI Container App (nginx) │  external ingress + Easy Auth
                    │   + React/Tailwind build │
                    └─────────────┬────────────┘
                                  │ /api/* (internal HTTPS, X-MS-CLIENT-PRINCIPAL forwarded)
                    ┌─────────────▼────────────┐
                    │ API Container App        │  internal ingress, 1 replica
                    │   FastAPI + APScheduler  │
                    └──┬───────────────┬───────┘
        Salesforce ◀───┘               └──▶ Azure Table Storage
        (client_credentials)                (queries, querieshistory, users,
                                             schedules, audit)
                                  │
                                  ▼
                              SendGrid (scheduled digests)
```

## Repository layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI backend. `app/` is the package; `app/legacy/` holds the ported `data_engine` / `soql_registry` / `soql_store` / `time_filters` modules. |
| `frontend/` | Vite + React + TypeScript + Tailwind + TanStack Router/Query/Table. Built as static assets served by nginx. |
| `infra/` | Bicep IaC. `main.bicep` composes per-resource modules under `modules/`. |
| `scripts/` | `sync_queries.py` for SOQL snapshot sync against Azure Table Storage. |
| `queries_snapshot.json` | Git-tracked snapshot of production SOQL templates. |

## Quick start (local dev)

### Backend

```bash
cd backend
python3.13 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env  # edit values
uvicorn app.main:app --reload --port 8000
pytest
```

`ENV=dev` skips auth entirely; `DEV_ROLE=admin|user` + `DEV_USER_EMAIL` seed
the identity. Without `AZURE_STORAGE_CONNECTION_STRING`, the user/schedule
services fall back to in-memory dicts and SOQL overrides fall back to
`soql_overrides.json`.

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxies /api to :8000)
npm run typecheck && npm run build
```

### Run both together

Backend on `:8000`, frontend on `:5173`. Vite proxies `/api/*` to the
backend; visit `http://localhost:5173`.

## Production deploy

See `infra/README.md`. Summary:

1. `az group create` + `az deployment group create` to provision Azure
   resources (Log Analytics, ACR, Storage with 6 tables, Key Vault, UI +
   API Container Apps). First deploy can omit `entraClientId` and run
   without Easy Auth.
2. Build and push `backend` and `frontend` images to ACR.
3. `az containerapp update --image ...` to point each app at the new image.
4. Redeploy Bicep with `entraClientId` set to enable Easy Auth.
5. Flip `ALLOW_PROD_QUERY_WRITES=true` on the API app only when admins
   intend to mutate SOQL templates from the UI.

## Feature inventory (vs legacy Streamlit)

Every feature from the original `streamlit_dashboard.py` has been ported:

- **All Source Summary** — per-AE Total Pipeline / Total Bookings + Self-Gen / SDR / Channel / Marketing pairs with pink→green heatmap.
- **12 KPI cards** in two rows of six, with the exact aggregation rules from `dashboard_ui.display_kpi_widgets` (sum for $, average for %).
- **5 sectioned data tables** (collapsed by default) preserving column order from `soql_registry.ALL_COLUMNS`, `Pending` placeholders for blocked columns, tooltip descriptions.
- **Two Plotly bar charts** → Recharts (Bookings YTD, YTD Quota Attainment %).
- **Performance Heatmap** → Tailwind grid with the RdYlGn ramp.
- **SOQL Management** — column list, editor with Test-before-Save gate, resolved-SOQL preview, history. Now admin-only with a `ALLOW_PROD_QUERY_WRITES` write-gate.
- **Filters** — Manager, AE, Time Period (preset + custom range), now in a sticky top bar.

Added:

- **AE drill-down drawer** on row-click.
- **Reports / Schedules** — cron-scheduled email digests of the All Source Summary.
- **User Management** (admin/user roles, hybrid Entra-identity + app-managed roles).
- **Activity / Audit log**.
- **Salesforce Connection** page with client-credentials status.

## Background

Originally a single-file Streamlit app for fast iteration; the rewrite
addresses (1) CRO UX (story-telling order, drill-down), (2) auth model
(server-to-server SF, app-level roles), (3) admin tooling, (4) delivery
(scheduled email). Plan: `/Users/apple/.claude/plans/we-are-going-to-fancy-lagoon.md`.
