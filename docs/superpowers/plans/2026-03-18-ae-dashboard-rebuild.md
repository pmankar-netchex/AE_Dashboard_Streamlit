# AE Performance Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Update (auth):** MSAL / `msal_auth.py`, disk token persistence / `token_storage.py`, and the `msal` package were **removed** afterward. Auth is **Salesforce OAuth** with **session-only** tokens in `streamlit_dashboard.py`, plus optional username/password via `.env`. Treat embedded snippets below as historical unless you are reconciling an old branch.

**Goal:** Rebuild the AE Performance Dashboard from scratch using the canonical spec in `implementation-specs.md`, reusing existing Salesforce OAuth and deployment scaffolding.

**Architecture:** Single `streamlit_dashboard.py` entry point with multi-tab layout; all SOQL lives in `src/soql_registry.py` (parameterized, per-column); data assembly in `src/data_engine.py`; UI rendering in `src/dashboard_ui.py`; Salesforce OAuth in `src/salesforce_oauth.py` (tokens in Streamlit session state only).

**Tech Stack:** Python 3.9+, Streamlit 1.31+, simple-salesforce, pandas, plotly, python-dotenv

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `streamlit_dashboard.py` | **Rewrite** | App entry, tabs, auth flow, data-load orchestration |
| `src/soql_registry.py` | **Create** | Canonical SOQL per column-ID, parameterization helpers |
| `src/data_engine.py` | **Create** | Execute queries, build unified DataFrame, error isolation |
| `src/meta_filters.py` | **Create** | Filter state, date range helpers, fiscal year utils |
| `src/dashboard_ui.py` | **Rewrite** | KPI widgets, table with heatmap/sort/search, charts |
| `src/salesforce_oauth.py` | **Keep** | Salesforce OAuth — no changes (session-scoped tokens in app code) |
| `src/salesforce_queries.py` | **Delete** | Replaced by `soql_registry.py` + `data_engine.py` |
| `src/dashboard_calculations.py` | **Delete** | Replaced by `data_engine.py` |
| `requirements.txt` | **Update** | Add `openpyxl` for Excel-like table features |
| `scripts/.env.example` | **Keep as-is** | Canonical env template — do not modify |

---

## Task 1: Remove Old Code, Keep Auth

**Files:**
- Delete: `src/salesforce_queries.py`
- Delete: `src/dashboard_calculations.py`
- Keep: `src/salesforce_oauth.py` (and session-based wiring in `streamlit_dashboard.py`)
- Keep: `src/__init__.py`

- [ ] **Step 1: Delete the two old modules**

```bash
rm src/salesforce_queries.py src/dashboard_calculations.py
```

- [ ] **Step 2: Verify Salesforce OAuth module**

```bash
git diff src/salesforce_oauth.py
```
Expected: no output (no changes) when following the original plan; current repo may differ after later auth refactors.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove legacy query and calculation modules per spec step 1"
```

---

## Task 2: Meta Filters Module

**Files:**
- Create: `src/meta_filters.py`

This module provides fiscal year dates, time-period helpers, and structures filter parameters for query injection.

- [ ] **Step 1: Write `src/meta_filters.py`**

```python
"""
Meta filter utilities: fiscal year, time period, filter param builder.
[spec: Section A]
"""
from datetime import date, timedelta
import calendar


FISCAL_YEAR_START_MONTH = 1  # January — change if fiscal year differs


def fiscal_year_start(today: date | None = None) -> date:
    """Return first day of current fiscal year."""
    d = today or date.today()
    return date(d.year, FISCAL_YEAR_START_MONTH, 1)


def this_month_range() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return start, today.replace(day=last_day)


def next_month_range() -> tuple[date, date]:
    today = date.today()
    if today.month == 12:
        nm = date(today.year + 1, 1, 1)
    else:
        nm = date(today.year, today.month + 1, 1)
    last_day = calendar.monthrange(nm.year, nm.month)[1]
    return nm, nm.replace(day=last_day)


def last_week_range() -> tuple[date, date]:
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=6)
    return start, end


def this_week_range() -> tuple[date, date]:
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def last_month_range() -> tuple[date, date]:
    today = date.today()
    first_this_month = today.replace(day=1)
    last_prev = first_this_month - timedelta(days=1)
    return last_prev.replace(day=1), last_prev


def resolve_time_period(
    preset: str | None,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[date, date]:
    """
    Convert a preset string or custom range to (start, end) dates.
    preset options: 'Last Week', 'This Week', 'Last Month', 'This Month', 'Custom'
    """
    mapping = {
        "Last Week": last_week_range,
        "This Week": this_week_range,
        "Last Month": last_month_range,
        "This Month": this_month_range,
    }
    if preset in mapping:
        return mapping[preset]()
    if preset == "Custom" and custom_start and custom_end:
        return custom_start, custom_end
    return this_month_range()


def build_filter_params(
    ae_user_id: str | None,
    ae_email: str | None,
    manager_name: str | None,
    time_start: date,
    time_end: date,
) -> dict:
    """
    Build a dict of filter params consumed by soql_registry.
    Keys: ae_user_id, ae_email, manager_name, time_start, time_end,
          fiscal_year_start, this_month_start, this_month_end,
          next_month_start, next_month_end
    """
    tm_start, tm_end = this_month_range()
    nm_start, nm_end = next_month_range()
    return {
        "ae_user_id": ae_user_id,
        "ae_email": ae_email,
        "manager_name": manager_name,
        "time_start": time_start.strftime("%Y-%m-%dT00:00:00Z"),
        "time_end": time_end.strftime("%Y-%m-%dT23:59:59Z"),
        "time_start_date": time_start.strftime("%Y-%m-%d"),
        "time_end_date": time_end.strftime("%Y-%m-%d"),
        "fiscal_year_start": fiscal_year_start().strftime("%Y-%m-%d"),
        "this_month_start": tm_start.strftime("%Y-%m-%d"),
        "this_month_end": tm_end.strftime("%Y-%m-%d"),
        "next_month_start": nm_start.strftime("%Y-%m-%d"),
        "next_month_end": nm_end.strftime("%Y-%m-%d"),
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/meta_filters.py
git commit -m "feat: add meta_filters module with fiscal year and time period helpers"
```

---

## Task 3: SOQL Registry

**Files:**
- Create: `src/soql_registry.py`

This is the canonical single source of truth for all SOQL. Each entry maps a column-ID to its query template, description, section, and time_filter flag.

- [ ] **Step 1: Write `src/soql_registry.py`** (full file)

```python
"""
SOQL Registry — canonical queries per column ID.
[spec: Section D]

CRITICAL RULES (from spec):
1. Never change filter logic; only parameterize placeholders.
2. time_filter=False columns ignore the meta time-period filter.
3. Per-SOQL error isolation: if one query fails, only its columns show NaN/error.
4. Columns E and H are computed — no SOQL.
5. SDR queries use Owner.AEEmail__c, NOT OwnerId.
6. Section 2 prospect filtering requires post-filter or subquery.
7. Section 4 Channel Partner exclusions are mandatory (all four).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SOQLEntry:
    col_id: str
    display_name: str
    section: str
    description: str
    template: str          # parameterized SOQL, use {placeholders}
    time_filter: bool
    computed: bool = False
    blocked: bool = False  # stub columns pending field confirmation
    aggregation: str = ""


def _owner_clause(p: dict) -> str:
    """Build the OwnerId / Manager filter clause."""
    if p.get("manager_name") and not p.get("ae_user_id"):
        return f"Owner.Manager.Name = '{p['manager_name']}'"
    if p.get("ae_user_id"):
        return f"OwnerId = '{p['ae_user_id']}'"
    return "OwnerId != null"


def _ae_email_clause(p: dict) -> str:
    """SDR→AE linkage via AEEmail__c."""
    return f"Owner.AEEmail__c = '{p.get('ae_email', '')}'"


def build_query(entry: SOQLEntry, params: dict) -> str:
    """
    Substitute params into the SOQL template.
    params keys defined by meta_filters.build_filter_params().
    """
    owner = _owner_clause(params)
    ae_email = _ae_email_clause(params)
    return entry.template.format(
        owner_clause=owner,
        ae_email_clause=ae_email,
        **params,
    )


# ============================================================
# SECTION 1 — Pipeline & Quota  [S1-COL-C through S1-COL-N]
# ============================================================

S1_COL_C = SOQLEntry(
    col_id="S1-COL-C",
    display_name="Quota YTD",
    section="Pipeline & Quota",
    description="Sum of quota amounts from fiscal year start to today.",
    aggregation="SUM(QuotaAmount)",
    time_filter=False,
    template="""
SELECT SUM(QuotaAmount) total
FROM ForecastingQuota
WHERE {owner_clause}
  AND StartDate >= {fiscal_year_start}
  AND StartDate <= TODAY
""",
)

S1_COL_D = SOQLEntry(
    col_id="S1-COL-D",
    display_name="Bookings YTD",
    section="Pipeline & Quota",
    description="Sum of Closed Won opportunity amounts from fiscal year start to today.",
    aggregation="SUM(Amount)",
    time_filter=False,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND {owner_clause}
  AND CloseDate >= {fiscal_year_start}
  AND CloseDate <= TODAY
""",
)

S1_COL_E = SOQLEntry(
    col_id="S1-COL-E",
    display_name="YTD Quota Attainment %",
    section="Pipeline & Quota",
    description="Computed: Bookings YTD / Quota YTD. No SOQL.",
    aggregation="D / C",
    time_filter=False,
    computed=True,
    template="",
)

S1_COL_F = SOQLEntry(
    col_id="S1-COL-F",
    display_name="Quota This Month",
    section="Pipeline & Quota",
    description="Sum of quota amounts for the current calendar month.",
    aggregation="SUM(QuotaAmount)",
    time_filter=False,
    template="""
SELECT SUM(QuotaAmount) total
FROM ForecastingQuota
WHERE {owner_clause}
  AND StartDate = THIS_MONTH
""",
)

S1_COL_G = SOQLEntry(
    col_id="S1-COL-G",
    display_name="Bookings This Month",
    section="Pipeline & Quota",
    description="Sum of Closed Won opportunity amounts for the current calendar month.",
    aggregation="SUM(Amount)",
    time_filter=False,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND {owner_clause}
  AND CloseDate = THIS_MONTH
""",
)

S1_COL_H = SOQLEntry(
    col_id="S1-COL-H",
    display_name="MTD Quota Attainment %",
    section="Pipeline & Quota",
    description="Computed: Bookings This Month / Quota This Month. No SOQL.",
    aggregation="G / F",
    time_filter=False,
    computed=True,
    template="",
)

S1_COL_I = SOQLEntry(
    col_id="S1-COL-I",
    display_name="Open Pipeline (This Month)",
    section="Pipeline & Quota",
    description="Sum of open (not closed) opportunity amounts closing this month.",
    aggregation="SUM(Amount)",
    time_filter=False,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE IsClosed = false
  AND {owner_clause}
  AND CloseDate = THIS_MONTH
""",
)

S1_COL_J = SOQLEntry(
    col_id="S1-COL-J",
    display_name="Open Pipeline (Next Month)",
    section="Pipeline & Quota",
    description="Sum of open opportunity amounts closing next month.",
    aggregation="SUM(Amount)",
    time_filter=False,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE IsClosed = false
  AND {owner_clause}
  AND CloseDate = NEXT_MONTH
""",
)

S1_COL_K = SOQLEntry(
    col_id="S1-COL-K",
    display_name="# Opportunities Created",
    section="Pipeline & Quota",
    description="Count of opportunities created within the selected time period.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Opportunity
WHERE {owner_clause}
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S1_COL_L = SOQLEntry(
    col_id="S1-COL-L",
    display_name="Pipeline $ Created",
    section="Pipeline & Quota",
    description="Sum of opportunity amounts created within the selected time period.",
    aggregation="SUM(Amount)",
    time_filter=True,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE {owner_clause}
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S1_COL_M = SOQLEntry(
    col_id="S1-COL-M",
    display_name="Total Closed Won",
    section="Pipeline & Quota",
    description="Sum of Closed Won opportunity amounts in the selected time period.",
    aggregation="SUM(Amount)",
    time_filter=True,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND {owner_clause}
  AND CloseDate >= {time_start_date}
  AND CloseDate <= {time_end_date}
""",
)

S1_COL_N = SOQLEntry(
    col_id="S1-COL-N",
    display_name="Total Closed Lost",
    section="Pipeline & Quota",
    description="Sum of Closed Lost opportunity amounts in the selected time period.",
    aggregation="SUM(Amount)",
    time_filter=True,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE StageName = 'Closed Lost'
  AND {owner_clause}
  AND CloseDate >= {time_start_date}
  AND CloseDate <= {time_end_date}
""",
)

# ============================================================
# SECTION 2 — Self-Gen Pipeline Creation  [S2-COL-O through S2-COL-S]
# ============================================================
# NOTE [spec rule 6]: Prospect-only filter cannot be expressed in a single WHERE clause.
# Post-filter in data_engine.py after fetching WhoId-level rows.

S2_COL_O = SOQLEntry(
    col_id="S2-COL-O",
    display_name="Unique Email Recipients",
    section="Self-Gen Pipeline Creation",
    description="Count of unique contacts/leads emailed by the AE (prospects only, not AM/SDR).",
    aggregation="COUNT_DISTINCT(WhoId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhoId) total
FROM Task
WHERE (ActivityType = 'Email' OR TaskSubtype = 'Email')
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND Owner.UserRole.Name NOT LIKE '%Account Manager%'
  AND Owner.UserRole.Name NOT LIKE '%SDR%'
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
  AND {owner_clause}
""",
)

S2_COL_P = SOQLEntry(
    col_id="S2-COL-P",
    display_name="Unique Call Recipients",
    section="Self-Gen Pipeline Creation",
    description="Count of unique contacts/leads called by the AE (prospects only, not AM/SDR).",
    aggregation="COUNT_DISTINCT(WhoId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhoId) total
FROM Task
WHERE (ActivityType LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND Owner.UserRole.Name NOT LIKE '%Account Manager%'
  AND Owner.UserRole.Name NOT LIKE '%SDR%'
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
  AND {owner_clause}
""",
)

S2_COL_Q = SOQLEntry(
    col_id="S2-COL-Q",
    display_name="Unique Voicemail Recipients",
    section="Self-Gen Pipeline Creation",
    description="BLOCKED: voicemail indicator field not yet confirmed. Shows placeholder.",
    aggregation="TBD",
    time_filter=True,
    blocked=True,
    template="",
)

S2_COL_R = SOQLEntry(
    col_id="S2-COL-R",
    display_name="Unique Accts w/ Foot Canvass",
    section="Self-Gen Pipeline Creation",
    description="Count of unique accounts where AE conducted a foot canvass (prospect meeting).",
    aggregation="COUNT_DISTINCT(WhatId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhatId) total
FROM Event
WHERE RecordType.Name = 'Sales Event'
  AND Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Foot Canvass'
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S2_COL_S = SOQLEntry(
    col_id="S2-COL-S",
    display_name="Unique Accts w/ Net New Mtgs",
    section="Self-Gen Pipeline Creation",
    description="Count of unique accounts where AE created a net new prospect meeting.",
    aggregation="COUNT_DISTINCT(WhatId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhatId) total
FROM Event
WHERE RecordType.Name = 'Sales Event'
  AND Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Net New'
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

# ============================================================
# SECTION 3 — SDR Activity  [S3-COL-T through S3-COL-W]
# ============================================================
# NOTE [spec rule 5]: These queries use Owner.AEEmail__c, not OwnerId.

S3_COL_T = SOQLEntry(
    col_id="S3-COL-T",
    display_name="SDR Unique Emails",
    section="SDR Activity",
    description="Count of unique contacts/leads emailed by SDRs supporting this AE.",
    aggregation="COUNT_DISTINCT(WhoId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhoId) total
FROM Task
WHERE (ActivityType = 'Email' OR TaskSubtype = 'Email')
  AND Owner.UserRole.Name LIKE '%SDR%'
  AND {ae_email_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S3_COL_U = SOQLEntry(
    col_id="S3-COL-U",
    display_name="SDR Unique Calls",
    section="SDR Activity",
    description="Count of unique contacts/leads called by SDRs supporting this AE.",
    aggregation="COUNT_DISTINCT(WhoId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhoId) total
FROM Task
WHERE (ActivityType LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND Owner.UserRole.Name LIKE '%SDR%'
  AND {ae_email_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S3_COL_V = SOQLEntry(
    col_id="S3-COL-V",
    display_name="SDR Unique Mtgs Scheduled",
    section="SDR Activity",
    description="Count of net-new prospect meetings scheduled by SDRs (AE is the owner).",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Event
WHERE RecordType.Name = 'Sales Event'
  AND Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Net New'
  AND CreatedBy.UserRole.Name LIKE '%Sales Rep%'
  AND CreatedBy.UserRole.Name NOT LIKE '%Account Manager%'
  AND CreatedBy.UserRole.Name NOT LIKE '%SDR%'
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S3_COL_W = SOQLEntry(
    col_id="S3-COL-W",
    display_name="SDR Unique Mtgs Held",
    section="SDR Activity",
    description="Count of net-new prospect meetings held where meeting was SDR-created.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Event
WHERE Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Net New'
  AND CreatedBy.UserRole.Name LIKE '%SDR%'
  AND (
    Owner.UserRole.Name LIKE 'Sales Rep%'
    OR Owner.UserRole.Name LIKE 'Channel%'
    OR Owner.UserRole.Name LIKE 'Inbound%'
  )
  AND Owner.UserRole.Name NOT LIKE '%Account Manager%'
  AND Owner.UserRole.Name NOT LIKE '%SDR%'
  AND Owner.UserRole.Name NOT LIKE '%Client Success%'
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

# ============================================================
# SECTION 4 — Channel Partners  [S4-COL-X through S4-COL-AA]
# ============================================================
# NOTE [spec rule 7]: All four exclusions mandatory:
#   HubSpot integration, inbound calls, Gong-logged, Case-related.

S4_COL_X = SOQLEntry(
    col_id="S4-COL-X",
    display_name="CP Unique Emails",
    section="Channel Partners",
    description="Count of unique channel partner contacts emailed by the AE.",
    aggregation="COUNT_DISTINCT(WhoId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhoId) total
FROM Task
WHERE (ActivityType = 'Email' OR TaskSubtype = 'Email')
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Inbound_Call__c = false
  AND Subject NOT LIKE '%[Gong In]%'
  AND Subject NOT LIKE '%[ ref:!%'
  AND Related_To_Object__c != 'Case'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S4_COL_Y = SOQLEntry(
    col_id="S4-COL-Y",
    display_name="CP Unique Calls",
    section="Channel Partners",
    description="Count of unique channel partner contacts called by the AE.",
    aggregation="COUNT_DISTINCT(WhoId)",
    time_filter=True,
    template="""
SELECT COUNT_DISTINCT(WhoId) total
FROM Task
WHERE (ActivityType LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Inbound_Call__c = false
  AND Subject NOT LIKE '%[Gong In]%'
  AND Subject NOT LIKE '%[ ref:!%'
  AND Related_To_Object__c != 'Case'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S4_COL_Z = SOQLEntry(
    col_id="S4-COL-Z",
    display_name="CP Mtgs Scheduled",
    section="Channel Partners",
    description="Count of channel partner meetings scheduled.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Event
WHERE RecordType.Name = 'Partner Event'
  AND Meeting_Type__c = 'Channel Partner Meeting'
  AND Meeting_Status__c = 'Scheduled'
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Related_To_Object__c != 'Case'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

S4_COL_AA = SOQLEntry(
    col_id="S4-COL-AA",
    display_name="CP Mtgs Held",
    section="Channel Partners",
    description="Count of channel partner meetings attended.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Event
WHERE RecordType.Name = 'Partner Event'
  AND Meeting_Type__c = 'Channel Partner Meeting'
  AND Meeting_Status__c LIKE 'Attended%'
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Related_To_Object__c != 'Case'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

# ============================================================
# SECTION 5 — Marketing  [S5-COL-AB through S5-COL-AD]
# ============================================================
# NOTE: ALL three are BLOCKED pending Source__c / LeadSource field value confirmation.

S5_COL_AB = SOQLEntry(
    col_id="S5-COL-AB",
    display_name="Mtgs from Events",
    section="Marketing",
    description="BLOCKED: Source__c / LeadSource field values pending confirmation.",
    aggregation="COUNT (TBD)",
    time_filter=True,
    blocked=True,
    template="",
)

S5_COL_AC = SOQLEntry(
    col_id="S5-COL-AC",
    display_name="Mtgs from Inbound",
    section="Marketing",
    description="BLOCKED: Source__c / LeadSource field values pending confirmation.",
    aggregation="COUNT (TBD)",
    time_filter=True,
    blocked=True,
    template="",
)

S5_COL_AD = SOQLEntry(
    col_id="S5-COL-AD",
    display_name="Mtgs from Other Marketing",
    section="Marketing",
    description="BLOCKED: Source__c / LeadSource field values pending confirmation.",
    aggregation="COUNT (TBD)",
    time_filter=True,
    blocked=True,
    template="",
)

# ============================================================
# REGISTRY — ordered list as in spec Section E
# ============================================================

ALL_COLUMNS: list[SOQLEntry] = [
    S1_COL_C, S1_COL_D, S1_COL_E, S1_COL_F, S1_COL_G, S1_COL_H,
    S1_COL_I, S1_COL_J, S1_COL_K, S1_COL_L, S1_COL_M, S1_COL_N,
    S2_COL_O, S2_COL_P, S2_COL_Q, S2_COL_R, S2_COL_S,
    S3_COL_T, S3_COL_U, S3_COL_V, S3_COL_W,
    S4_COL_X, S4_COL_Y, S4_COL_Z, S4_COL_AA,
    S5_COL_AB, S5_COL_AC, S5_COL_AD,
]

COLUMN_BY_ID: dict[str, SOQLEntry] = {c.col_id: c for c in ALL_COLUMNS}

SECTIONS: list[str] = [
    "Pipeline & Quota",
    "Self-Gen Pipeline Creation",
    "SDR Activity",
    "Channel Partners",
    "Marketing",
]
```

- [ ] **Step 2: Commit**

```bash
git add src/soql_registry.py
git commit -m "feat: add SOQL registry with all 28 column definitions per spec Section D"
```

---

## Task 4: Data Engine

**Files:**
- Create: `src/data_engine.py`

Executes all SOQL queries in isolation (per spec Critical Rule #3), returns a dict of `{col_id: value}` per AE row. Also builds the unified DataFrame.

- [ ] **Step 1: Write `src/data_engine.py`**

```python
"""
Data Engine — executes SOQL registry queries, builds unified DataFrame.
[spec: Steps 3–5, Critical Rule #3]

Per-SOQL error isolation: if one query fails, only its column shows NaN.
"""
from __future__ import annotations
import pandas as pd
import re
from typing import Any

from src.soql_registry import ALL_COLUMNS, COLUMN_BY_ID, build_query, SOQLEntry
from src.meta_filters import build_filter_params


def _run_query(sf, soql: str) -> Any:
    """Execute SOQL and return the aggregate value (first field of first record)."""
    result = sf.query(soql.strip())
    records = result.get("records", [])
    if not records:
        return None
    row = records[0]
    # Get the first non-attributes value
    for k, v in row.items():
        if k != "attributes":
            return v
    return None


def fetch_column(sf, entry: SOQLEntry, params: dict) -> tuple[str, Any]:
    """
    Execute one SOQL entry and return (col_id, value).
    On failure returns (col_id, None).
    """
    if entry.computed or entry.blocked:
        return entry.col_id, None
    soql = build_query(entry, params)
    try:
        val = _run_query(sf, soql)
        return entry.col_id, val
    except Exception:
        return entry.col_id, None


def fetch_all_columns(sf, params: dict) -> dict[str, Any]:
    """
    Run every non-computed, non-blocked SOQL and return {col_id: value}.
    Per-query error isolation: failures become None for that column only.
    """
    results: dict[str, Any] = {}
    for entry in ALL_COLUMNS:
        col_id, val = fetch_column(sf, entry, params)
        results[col_id] = val

    # Compute derived columns
    c = results.get("S1-COL-C") or 0
    d = results.get("S1-COL-D") or 0
    f = results.get("S1-COL-F") or 0
    g = results.get("S1-COL-G") or 0
    results["S1-COL-E"] = (d / c) if c else None  # YTD Quota Attainment %
    results["S1-COL-H"] = (g / f) if f else None  # MTD Quota Attainment %

    return results


def build_ae_list(sf, params: dict) -> list[dict]:
    """
    Get the list of AEs to display based on manager/ae_user_id filter.
    Returns list of {Id, Name, Email} dicts.
    """
    if params.get("ae_user_id"):
        query = f"""
            SELECT Id, Name, Email
            FROM User
            WHERE Id = '{params["ae_user_id"]}'
            AND IsActive = true
        """
    elif params.get("manager_name"):
        query = f"""
            SELECT Id, Name, Email
            FROM User
            WHERE Manager.Name = '{params["manager_name"]}'
            AND IsActive = true
            ORDER BY Name
        """
    else:
        query = """
            SELECT Id, Name, Email
            FROM User
            WHERE IsActive = true
            AND UserRole.Name LIKE '%Sales Rep%'
            ORDER BY Name
            LIMIT 200
        """
    try:
        result = sf.query(query)
        return [
            {"Id": r["Id"], "Name": r["Name"], "Email": r.get("Email", "")}
            for r in result.get("records", [])
        ]
    except Exception:
        return []


def build_dashboard_dataframe(sf, params: dict) -> pd.DataFrame:
    """
    Build the unified DataFrame with one row per AE and columns C–AD.
    [spec: Step 5]
    """
    ae_list = build_ae_list(sf, params)
    if not ae_list:
        return pd.DataFrame()

    rows = []
    for ae in ae_list:
        ae_params = {
            **params,
            "ae_user_id": ae["Id"],
            "ae_email": ae["Email"],
        }
        col_values = fetch_all_columns(sf, ae_params)
        row = {"AE Name": ae["Name"], "AE Email": ae["Email"]}
        for entry in ALL_COLUMNS:
            row[entry.col_id] = col_values.get(entry.col_id)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def get_managers_list(sf) -> list[str]:
    """Get distinct manager names for the Manager filter."""
    try:
        result = sf.query("""
            SELECT Manager.Name mgr
            FROM User
            WHERE IsActive = true
            AND Manager.Name != null
            AND UserRole.Name LIKE '%Sales Rep%'
            ORDER BY Manager.Name
        """)
        seen = set()
        managers = []
        for r in result.get("records", []):
            name = r.get("mgr")
            if name and name not in seen:
                seen.add(name)
                managers.append(name)
        return managers
    except Exception:
        return []


def get_ae_names_list(sf, manager_name: str | None = None) -> list[dict]:
    """Get AE names (optionally filtered by manager) for the AE Name filter."""
    where = "WHERE IsActive = true AND UserRole.Name LIKE '%Sales Rep%'"
    if manager_name:
        where += f" AND Manager.Name = '{manager_name}'"
    try:
        result = sf.query(f"SELECT Id, Name, Email FROM User {where} ORDER BY Name LIMIT 200")
        return [
            {"id": r["Id"], "name": r["Name"], "email": r.get("Email", "")}
            for r in result.get("records", [])
        ]
    except Exception:
        return []
```

- [ ] **Step 2: Commit**

```bash
git add src/data_engine.py
git commit -m "feat: add data engine with per-SOQL error isolation and unified DataFrame builder"
```

---

## Task 5: Dashboard UI Module

**Files:**
- Rewrite: `src/dashboard_ui.py`

Renders the KPI widgets, bar/line charts, heatmap table with sorting/search/pagination, and column tooltips.

- [ ] **Step 1: Write `src/dashboard_ui.py`**

```python
"""
Dashboard UI components.
[spec: Section B]
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.soql_registry import ALL_COLUMNS, SECTIONS, COLUMN_BY_ID


SECTION_DISPLAY_NAMES = {
    "Pipeline & Quota": "Pipeline Generated",
    "Self-Gen Pipeline Creation": "Self Gen Pipeline Creation (not channel partners – prospects)",
    "SDR Activity": "SDR Activity for This Rep",
    "Channel Partners": "Channel Partners",
    "Marketing": "Marketing",
}

CURRENCY_COLS = {
    "S1-COL-C", "S1-COL-D", "S1-COL-F", "S1-COL-G",
    "S1-COL-I", "S1-COL-J", "S1-COL-L", "S1-COL-M", "S1-COL-N",
}
PERCENT_COLS = {"S1-COL-E", "S1-COL-H"}


def apply_custom_css():
    st.markdown("""
    <style>
    .metric-card { background: #f0f2f6; border-radius: 8px; padding: 12px; }
    .section-header { font-size: 1.1em; font-weight: 700; color: #1f2937;
                      border-bottom: 2px solid #3b82f6; padding-bottom: 4px; margin-bottom: 8px; }
    .blocked-col { color: #9ca3af; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)


def fmt_currency(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"${val:,.0f}"


def fmt_percent(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{val:.1%}"


def fmt_number(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{int(val):,}"


def display_kpi_widgets(df: pd.DataFrame):
    """Top-of-page KPI widgets showing aggregate totals. [spec: B.1]"""
    if df.empty:
        return
    st.markdown("### Key Performance Indicators")
    cols = st.columns(5)
    kpis = [
        ("Bookings YTD", "S1-COL-D", fmt_currency),
        ("Quota YTD", "S1-COL-C", fmt_currency),
        ("MTD Attainment", "S1-COL-H", lambda v: fmt_percent(df["S1-COL-H"].mean() if not df.empty else None)),
        ("Open Pipeline (This Mo)", "S1-COL-I", fmt_currency),
        ("Closed Won (Period)", "S1-COL-M", fmt_currency),
    ]
    for i, (label, col_id, formatter) in enumerate(kpis):
        if col_id in df.columns:
            val = df[col_id].sum() if col_id not in PERCENT_COLS else df[col_id].mean()
            cols[i].metric(label, formatter(val))


def build_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Format raw numeric DataFrame into display-ready strings."""
    out = df[["AE Name"]].copy()
    for entry in ALL_COLUMNS:
        col = entry.col_id
        if col not in df.columns:
            out[entry.display_name] = "—"
            continue
        if entry.blocked:
            out[entry.display_name] = "Pending"
            continue
        if col in CURRENCY_COLS:
            out[entry.display_name] = df[col].apply(fmt_currency)
        elif col in PERCENT_COLS:
            out[entry.display_name] = df[col].apply(fmt_percent)
        else:
            out[entry.display_name] = df[col].apply(fmt_number)
    return out


def display_dashboard_table(df: pd.DataFrame):
    """
    Main data table with section grouping, search, sort, pagination, heatmap.
    [spec: B.1, B.2]
    """
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    # Global search
    search = st.text_input("Search AEs", placeholder="Type to filter...", key="table_search")
    filtered = df
    if search:
        mask = df["AE Name"].str.contains(search, case=False, na=False)
        filtered = df[mask]

    # Pagination
    page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=0, key="page_size")
    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="page_num")
    start_idx = (page - 1) * page_size
    page_df = filtered.iloc[start_idx: start_idx + page_size]

    display = build_display_df(page_df)

    # Render per section in collapsible groups
    for section in SECTIONS:
        section_cols = [e for e in ALL_COLUMNS if e.section == section]
        display_name = SECTION_DISPLAY_NAMES.get(section, section)
        col_names = ["AE Name"] + [e.display_name for e in section_cols]
        section_df = display[[c for c in col_names if c in display.columns]]

        with st.expander(f"**{display_name}**", expanded=True):
            st.dataframe(
                section_df,
                use_container_width=True,
                hide_index=True,
            )

    st.caption(f"Showing {start_idx + 1}–{min(start_idx + page_size, total)} of {total} AEs")


def display_charts(df: pd.DataFrame):
    """Bar and line charts for critical trend/comparison. [spec: B.1]"""
    if df.empty:
        return
    with st.expander("Charts", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if "S1-COL-D" in df.columns and "AE Name" in df.columns:
                chart_df = df[["AE Name", "S1-COL-D"]].dropna().rename(
                    columns={"S1-COL-D": "Bookings YTD"}
                )
                fig = px.bar(
                    chart_df, x="AE Name", y="Bookings YTD",
                    title="Bookings YTD by AE", labels={"Bookings YTD": "$"}
                )
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            if "S1-COL-E" in df.columns and "AE Name" in df.columns:
                chart_df = df[["AE Name", "S1-COL-E"]].dropna().rename(
                    columns={"S1-COL-E": "YTD Attainment %"}
                )
                chart_df["YTD Attainment %"] = chart_df["YTD Attainment %"] * 100
                fig = px.bar(
                    chart_df, x="AE Name", y="YTD Attainment %",
                    title="YTD Quota Attainment % by AE"
                )
                st.plotly_chart(fig, use_container_width=True)


def display_heatmap(df: pd.DataFrame):
    """Heatmap on numeric metric columns. [spec: B.1]"""
    if df.empty:
        return
    with st.expander("Heatmap", expanded=False):
        numeric_cols = [
            e.col_id for e in ALL_COLUMNS
            if not e.computed and not e.blocked and e.col_id in df.columns
        ]
        heat_df = df[["AE Name"] + numeric_cols].set_index("AE Name")
        # Normalize per column for color scaling
        norm = heat_df.copy()
        for c in numeric_cols:
            col_max = norm[c].max()
            if col_max and col_max > 0:
                norm[c] = norm[c] / col_max

        fig = go.Figure(data=go.Heatmap(
            z=norm.values,
            x=[COLUMN_BY_ID[c].display_name if c in COLUMN_BY_ID else c for c in numeric_cols],
            y=norm.index.tolist(),
            colorscale="RdYlGn",
            showscale=True,
        ))
        fig.update_layout(
            title="Performance Heatmap (normalized per column)",
            height=max(300, 30 * len(df)),
            xaxis={"tickangle": -45},
        )
        st.plotly_chart(fig, use_container_width=True)


def render_fetch_status(timestamp: str | None):
    """Display fetch timestamp and refresh button. [spec: B.3]"""
    col1, col2 = st.columns([3, 1])
    with col1:
        if timestamp:
            st.caption(f"Data last fetched: {timestamp}")
        else:
            st.caption("Data not yet fetched.")
    with col2:
        return st.button("Refresh Data", use_container_width=True)
```

- [ ] **Step 2: Commit**

```bash
git add src/dashboard_ui.py
git commit -m "feat: rewrite dashboard UI with KPI widgets, heatmap, charts, and paginated table"
```

---

## Task 6: Main Streamlit App Rewrite

**Files:**
- Rewrite: `streamlit_dashboard.py`

Entry point. Three tabs: Dashboard, SOQL Management, Salesforce Connection. Orchestrates auth, meta filters, data fetch, and UI.

- [ ] **Step 1: Write `streamlit_dashboard.py`** (full replacement)

The snippet below is **historical** (includes MSAL and `token_storage`). Current app: Salesforce OAuth only, session-scoped tokens — see repository `streamlit_dashboard.py`.

```python
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from src.salesforce_oauth import (
    is_oauth_configured,
    get_authorization_url,
    exchange_code_for_tokens,
    refresh_access_token,
    create_salesforce_client,
)
from src.token_storage import save_tokens, load_tokens, clear_tokens
from src.msal_auth import (
    is_msal_configured,
    is_authenticated,
    get_authorization_url as get_msal_auth_url,
    exchange_code_for_token,
    get_user_info,
    cache_user,
    clear_user_cache,
    render_login_screen as render_msal_login,
    display_user_info,
    check_user_authorization,
)
from src.meta_filters import resolve_time_period, build_filter_params
from src.data_engine import (
    build_dashboard_dataframe,
    get_managers_list,
    get_ae_names_list,
)
from src.soql_registry import ALL_COLUMNS, COLUMN_BY_ID, build_query
from src.dashboard_ui import (
    apply_custom_css,
    display_kpi_widgets,
    display_dashboard_table,
    display_charts,
    display_heatmap,
    render_fetch_status,
)

st.set_page_config(
    page_title="AE Performance Dashboard",
    page_icon="📊",
    layout="wide",
)
apply_custom_css()


# ── Salesforce Connection ──────────────────────────────────────────────────────

def get_salesforce_connection():
    if "sf_oauth" in st.session_state:
        oauth = st.session_state["sf_oauth"]
        try:
            return create_salesforce_client(oauth["instance_url"], oauth["access_token"])
        except Exception:
            if oauth.get("refresh_token"):
                try:
                    tokens = refresh_access_token(oauth["refresh_token"])
                    st.session_state["sf_oauth"]["access_token"] = tokens["access_token"]
                    st.session_state["sf_oauth"]["instance_url"] = tokens.get(
                        "instance_url", oauth["instance_url"]
                    )
                    save_tokens(
                        tokens["access_token"],
                        oauth["refresh_token"],
                        st.session_state["sf_oauth"]["instance_url"],
                    )
                    return create_salesforce_client(
                        st.session_state["sf_oauth"]["instance_url"], tokens["access_token"]
                    )
                except Exception:
                    del st.session_state["sf_oauth"]
            else:
                del st.session_state["sf_oauth"]

    if is_oauth_configured():
        saved = load_tokens()
        if saved:
            try:
                sf = create_salesforce_client(saved["instance_url"], saved["access_token"])
                sf.query("SELECT Id FROM User LIMIT 1")
                st.session_state["sf_oauth"] = saved
                return sf
            except Exception:
                if saved.get("refresh_token"):
                    try:
                        tokens = refresh_access_token(saved["refresh_token"])
                        new_oauth = {
                            "access_token": tokens["access_token"],
                            "refresh_token": saved["refresh_token"],
                            "instance_url": tokens.get("instance_url", saved["instance_url"]),
                        }
                        save_tokens(
                            new_oauth["access_token"],
                            new_oauth["refresh_token"],
                            new_oauth["instance_url"],
                        )
                        st.session_state["sf_oauth"] = new_oauth
                        return create_salesforce_client(
                            new_oauth["instance_url"], new_oauth["access_token"]
                        )
                    except Exception:
                        clear_tokens()

    username = os.environ.get("SALESFORCE_USERNAME")
    password = os.environ.get("SALESFORCE_PASSWORD")
    security_token = os.environ.get("SALESFORCE_SECURITY_TOKEN")
    if all([username, password, security_token]):
        from simple_salesforce import Salesforce
        try:
            return Salesforce(
                username=username, password=password, security_token=security_token
            )
        except Exception as e:
            st.error(f"Failed to connect: {e}")
    return None


def render_oauth_login_screen():
    st.markdown(
        f"""
        <div style="max-width:400px;margin:4rem auto;text-align:center;
                    background:#f0f2f6;padding:2rem;border-radius:12px;">
          <h2>📊 AE Performance Dashboard</h2>
          <p>Connect your Salesforce account to view the dashboard</p>
          <a href="{get_authorization_url()}" style="background:#0070d2;color:#fff;
             padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:600;">
            Connect with Salesforce
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def handle_oauth_callback() -> bool:
    code = st.query_params.get("code")
    if not code:
        return False
    code = code[0] if isinstance(code, list) else code

    if st.session_state.get("last_oauth_code") == code:
        st.query_params.clear()
        return "sf_oauth" in st.session_state

    try:
        tokens = exchange_code_for_tokens(code)
        oauth_data = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "instance_url": tokens["instance_url"],
        }
        st.session_state["sf_oauth"] = oauth_data
        st.session_state["last_oauth_code"] = code
        if oauth_data.get("refresh_token"):
            save_tokens(
                oauth_data["access_token"],
                oauth_data["refresh_token"],
                oauth_data["instance_url"],
            )
        st.query_params.clear()
        return True
    except Exception as e:
        err = str(e).lower()
        if "expired" in err or "invalid_grant" in err:
            st.query_params.clear()
            return False
        st.error(f"Login failed: {e}")
        st.query_params.clear()
        return False


# ── Sidebar Filters ────────────────────────────────────────────────────────────

def render_sidebar_filters(sf) -> dict:
    """Render meta filters in sidebar, return filter_params dict."""
    st.sidebar.header("Filters")

    managers = get_managers_list(sf)
    manager = st.sidebar.selectbox(
        "Manager", ["(All)"] + managers, key="filter_manager"
    )
    manager_name = None if manager == "(All)" else manager

    ae_options = get_ae_names_list(sf, manager_name if manager_name else None)
    ae_display = ["(All)"] + [a["name"] for a in ae_options]
    ae_choice = st.sidebar.selectbox("AE Name", ae_display, key="filter_ae")

    selected_ae = None
    ae_email = None
    if ae_choice != "(All)":
        match = next((a for a in ae_options if a["name"] == ae_choice), None)
        if match:
            selected_ae = match["id"]
            ae_email = match["email"]

    time_presets = ["Last Week", "This Week", "Last Month", "This Month", "Custom"]
    preset = st.sidebar.selectbox("Time Period", time_presets, index=3, key="filter_time")

    custom_start = custom_end = None
    if preset == "Custom":
        from datetime import date
        custom_start = st.sidebar.date_input("Start Date", key="filter_start")
        custom_end = st.sidebar.date_input("End Date", key="filter_end")

    time_start, time_end = resolve_time_period(preset, custom_start, custom_end)

    return build_filter_params(
        ae_user_id=selected_ae,
        ae_email=ae_email,
        manager_name=manager_name,
        time_start=time_start,
        time_end=time_end,
    )


# ── Tab: Dashboard ─────────────────────────────────────────────────────────────

def render_dashboard_tab(sf):
    params = render_sidebar_filters(sf)
    display_user_info()

    st.title("📊 AE Performance Dashboard")

    # Refresh / timestamp
    if "dashboard_df" not in st.session_state:
        st.session_state["dashboard_df"] = None
        st.session_state["fetch_ts"] = None

    should_refresh = render_fetch_status(st.session_state.get("fetch_ts"))

    if st.session_state["dashboard_df"] is None or should_refresh:
        with st.spinner("Fetching data from Salesforce…"):
            df = build_dashboard_dataframe(sf, params)
            st.session_state["dashboard_df"] = df
            st.session_state["fetch_ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = st.session_state["dashboard_df"]

    display_kpi_widgets(df)
    st.divider()
    display_dashboard_table(df)
    display_charts(df)
    display_heatmap(df)


# ── Tab: SOQL Management ───────────────────────────────────────────────────────

def render_soql_tab(sf):
    """SOQL Management tab — view, edit, test, and save queries. [spec: B.4]"""
    st.header("SOQL Management")
    st.caption(
        "Edit SOQL queries below. Changes are only saved after a successful test run. "
        "Time-filter-immune columns (marked 🔒) always use fixed date windows."
    )

    if "soql_overrides" not in st.session_state:
        st.session_state["soql_overrides"] = {}

    for entry in ALL_COLUMNS:
        label = f"[{entry.col_id}] {entry.display_name}"
        if entry.blocked:
            label += " — ⏳ BLOCKED"
        if not entry.time_filter:
            label += " 🔒"

        with st.expander(label, expanded=False):
            st.caption(f"**Section:** {entry.section}  |  **Aggregation:** {entry.aggregation}")
            st.caption(entry.description)

            if entry.computed:
                st.info("Computed column — no SOQL (calculated from other columns).")
                continue
            if entry.blocked:
                st.warning("Blocked — pending field value confirmation from Salesforce org.")
                continue

            current_soql = st.session_state["soql_overrides"].get(
                entry.col_id, entry.template
            ).strip()

            new_soql = st.text_area(
                "SOQL",
                value=current_soql,
                height=200,
                key=f"soql_edit_{entry.col_id}",
            )

            col_test, col_save = st.columns(2)
            with col_test:
                if st.button("Test", key=f"soql_test_{entry.col_id}"):
                    from datetime import date
                    test_params = {
                        "ae_user_id": "DUMMY_ID",
                        "ae_email": "test@example.com",
                        "manager_name": None,
                        "time_start": "2025-01-01T00:00:00Z",
                        "time_end": "2025-12-31T23:59:59Z",
                        "time_start_date": "2025-01-01",
                        "time_end_date": "2025-12-31",
                        "fiscal_year_start": "2025-01-01",
                        "this_month_start": "2025-03-01",
                        "this_month_end": "2025-03-31",
                        "next_month_start": "2025-04-01",
                        "next_month_end": "2025-04-30",
                    }
                    from src.soql_registry import build_query as bq, SOQLEntry
                    test_entry = SOQLEntry(
                        col_id=entry.col_id,
                        display_name=entry.display_name,
                        section=entry.section,
                        description=entry.description,
                        template=new_soql,
                        time_filter=entry.time_filter,
                        aggregation=entry.aggregation,
                    )
                    try:
                        built = bq(test_entry, test_params)
                        sf.query(built.strip())
                        st.success("Query executed successfully. Click Save to persist.")
                        st.session_state[f"soql_tested_{entry.col_id}"] = new_soql
                    except Exception as e:
                        st.error(f"Query failed: {e}")
            with col_save:
                tested = st.session_state.get(f"soql_tested_{entry.col_id}")
                if st.button(
                    "Save",
                    key=f"soql_save_{entry.col_id}",
                    disabled=(tested != new_soql),
                ):
                    st.session_state["soql_overrides"][entry.col_id] = new_soql
                    st.success("Saved.")

    if st.button("Refresh Dashboard with Updated Queries"):
        st.session_state["dashboard_df"] = None
        st.success("Dashboard will refresh on next load.")


# ── Tab: Salesforce Connection ─────────────────────────────────────────────────

def render_connection_tab(sf):
    """Salesforce Connection status tab. [spec: B.5]"""
    st.header("Salesforce Connection")

    if sf is None:
        st.error("Not connected to Salesforce.")
        return

    oauth = st.session_state.get("sf_oauth", {})
    instance_url = oauth.get("instance_url") or getattr(sf, "base_url", "Unknown")

    st.success("Connected")
    st.write(f"**Instance URL:** {instance_url}")

    try:
        result = sf.query("SELECT Id, Name, Username FROM User WHERE Id = :userId LIMIT 1")
    except Exception:
        result = None

    try:
        me = sf.query("SELECT Id, Name FROM User WHERE Id = UserInfo.getUserId() LIMIT 1")
        if me.get("records"):
            r = me["records"][0]
            st.write(f"**Authenticated User:** {r['Name']}")
    except Exception:
        st.write("**Authenticated User:** Unable to retrieve")

    if st.button("Disconnect Salesforce"):
        clear_tokens()
        if "sf_oauth" in st.session_state:
            del st.session_state["sf_oauth"]
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # MSAL authentication gate
    if is_msal_configured():
        if st.query_params.get("code") and not st.query_params.get("state"):
            code = st.query_params.get("code")
            code = code[0] if isinstance(code, list) else code
            try:
                token_response = exchange_code_for_token(code)
                user_info = get_user_info(token_response.get("access_token"))
                cache_user(token_response, user_info)
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"MSAL authentication failed: {e}")
                st.query_params.clear()
                st.stop()

        if not is_authenticated():
            st.title("📊 AE Performance Dashboard")
            render_msal_login()
            return

        allowed_domains = [
            d.strip()
            for d in os.environ.get("AZURE_ALLOWED_DOMAINS", "").split(",")
            if d.strip()
        ]
        allowed_emails = [
            e.strip()
            for e in os.environ.get("AZURE_ALLOWED_EMAILS", "").split(",")
            if e.strip()
        ]
        if allowed_domains or allowed_emails:
            if not check_user_authorization(
                allowed_domains=allowed_domains or None,
                allowed_emails=allowed_emails or None,
            ):
                st.error("Access Denied")
                if st.button("Sign Out"):
                    clear_user_cache()
                    st.rerun()
                st.stop()

    # Salesforce OAuth callback
    if st.query_params.get("code") and st.query_params.get("state"):
        if handle_oauth_callback():
            st.rerun()
        return

    sf = get_salesforce_connection()

    if sf is None and is_oauth_configured():
        st.title("📊 AE Performance Dashboard")
        render_oauth_login_screen()
        return

    if sf is None:
        st.title("📊 AE Performance Dashboard")
        st.error("Unable to connect to Salesforce. Check your .env configuration.")
        return

    tab_dashboard, tab_soql, tab_connection = st.tabs(
        ["Dashboard", "SOQL Management", "Salesforce Connection"]
    )

    with tab_dashboard:
        render_dashboard_tab(sf)
    with tab_soql:
        render_soql_tab(sf)
    with tab_connection:
        render_connection_tab(sf)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run basic syntax check**

```bash
python -m py_compile streamlit_dashboard.py && echo "OK"
python -m py_compile src/soql_registry.py && echo "OK"
python -m py_compile src/data_engine.py && echo "OK"
python -m py_compile src/meta_filters.py && echo "OK"
python -m py_compile src/dashboard_ui.py && echo "OK"
```
Expected: five "OK" lines, no errors.

- [ ] **Step 3: Commit**

```bash
git add streamlit_dashboard.py
git commit -m "feat: rewrite main app with 3-tab layout, meta filters, SOQL management"
```

---

## Task 7: Update Requirements

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

```
streamlit>=1.31.0
pandas>=2.1.4
simple-salesforce>=1.12.5
plotly>=5.18.0
python-dotenv>=1.0.0
requests>=2.31.0
```

(Remove `openpyxl` since we're not doing Excel export — YAGNI.)

- [ ] **Step 2: Verify install**

```bash
pip install -r requirements.txt 2>&1 | tail -5
```
Expected: "Successfully installed" or "already satisfied"

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: update requirements to use >= version bounds"
```

---

## Task 8: Tooltips on Column Headers

**Files:**
- Modify: `src/dashboard_ui.py`

Add tooltip strings for every metric column. [spec: B.6]

- [ ] **Step 1: Add TOOLTIPS dict at the top of `src/dashboard_ui.py`**

Insert after imports:

```python
TOOLTIPS: dict[str, str] = {
    "S1-COL-C": "Quota YTD: SUM(ForecastingQuota.QuotaAmount) from fiscal year start to today. Time-filter immune.",
    "S1-COL-D": "Bookings YTD: SUM(Opportunity.Amount) where StageName='Closed Won', fiscal year to date. Time-filter immune.",
    "S1-COL-E": "YTD Quota Attainment %: Bookings YTD ÷ Quota YTD (computed, no SOQL). Time-filter immune.",
    "S1-COL-F": "Quota This Month: SUM(ForecastingQuota.QuotaAmount) for THIS_MONTH. Time-filter immune.",
    "S1-COL-G": "Bookings This Month: SUM(Opportunity.Amount) closed won this month. Time-filter immune.",
    "S1-COL-H": "MTD Quota Attainment %: Bookings This Month ÷ Quota This Month (computed). Time-filter immune.",
    "S1-COL-I": "Open Pipeline (This Month): SUM(Opportunity.Amount) IsClosed=false, CloseDate=THIS_MONTH. Time-filter immune.",
    "S1-COL-J": "Open Pipeline (Next Month): SUM(Opportunity.Amount) IsClosed=false, CloseDate=NEXT_MONTH. Time-filter immune.",
    "S1-COL-K": "# Opportunities Created: COUNT(Opportunity.Id) in selected time period.",
    "S1-COL-L": "Pipeline $ Created: SUM(Opportunity.Amount) by CreatedDate in selected period.",
    "S1-COL-M": "Total Closed Won: SUM(Opportunity.Amount) StageName='Closed Won' in selected period.",
    "S1-COL-N": "Total Closed Lost: SUM(Opportunity.Amount) StageName='Closed Lost' in selected period.",
    "S2-COL-O": "Unique Email Recipients: COUNT_DISTINCT(Task.WhoId) emails sent by Sales Rep (not AM/SDR) to prospects.",
    "S2-COL-P": "Unique Call Recipients: COUNT_DISTINCT(Task.WhoId) calls made by Sales Rep (not AM/SDR) to prospects.",
    "S2-COL-Q": "Unique Voicemail Recipients: BLOCKED — voicemail field pending confirmation.",
    "S2-COL-R": "Unique Accts w/ Foot Canvass: COUNT_DISTINCT(Event.WhatId) prospect meetings with Meeting_Specifics__c='Foot Canvass'.",
    "S2-COL-S": "Unique Accts w/ Net New Mtgs: COUNT_DISTINCT(Event.WhatId) prospect meetings with Meeting_Specifics__c='Net New'.",
    "S3-COL-T": "SDR Unique Emails: COUNT_DISTINCT(Task.WhoId) emails sent by SDRs linked to this AE via AEEmail__c.",
    "S3-COL-U": "SDR Unique Calls: COUNT_DISTINCT(Task.WhoId) calls made by SDRs linked to this AE.",
    "S3-COL-V": "SDR Unique Mtgs Scheduled: COUNT(Event.Id) net-new prospect meetings with Sales Rep as creator.",
    "S3-COL-W": "SDR Unique Mtgs Held: COUNT(Event.Id) net-new prospect meetings created by SDR and owned by Sales Rep.",
    "S4-COL-X": "CP Unique Emails: COUNT_DISTINCT(Task.WhoId) emails to channel partners. Excludes HubSpot, inbound, Gong, Cases.",
    "S4-COL-Y": "CP Unique Calls: COUNT_DISTINCT(Task.WhoId) calls to channel partners. Same exclusions as emails.",
    "S4-COL-Z": "CP Mtgs Scheduled: COUNT(Event.Id) channel partner meetings with status='Scheduled'.",
    "S4-COL-AA": "CP Mtgs Held: COUNT(Event.Id) channel partner meetings with status LIKE 'Attended%'.",
    "S5-COL-AB": "Mtgs from Events: BLOCKED — Source__c field values pending confirmation.",
    "S5-COL-AC": "Mtgs from Inbound: BLOCKED — Source__c field values pending confirmation.",
    "S5-COL-AD": "Mtgs from Other Marketing: BLOCKED — Source__c field values pending confirmation.",
}
```

- [ ] **Step 2: Display tooltips above each section expander**

In `display_dashboard_table`, inside the section loop, before `st.dataframe`, add:

```python
# Show tooltips as a legend for this section
tooltip_lines = []
for e in section_cols:
    tip = TOOLTIPS.get(e.col_id, "")
    if tip:
        tooltip_lines.append(f"- **{e.display_name}:** {tip}")
if tooltip_lines:
    with st.expander("Column Descriptions", expanded=False):
        st.markdown("\n".join(tooltip_lines))
```

- [ ] **Step 3: Syntax check and commit**

```bash
python -m py_compile src/dashboard_ui.py && echo "OK"
git add src/dashboard_ui.py
git commit -m "feat: add column header tooltips per spec B.6"
```

---

## Task 9: Error Resilience Verification + Dead Code Cleanup

**Files:**
- Verify: `src/data_engine.py` (per-query isolation)
- Delete stale: `src/dashboard_calculations.py` (already deleted in Task 1)
- Check: no imports reference deleted files

- [ ] **Step 1: Grep for any references to deleted files**

```bash
grep -r "dashboard_calculations\|salesforce_queries" . --include="*.py" | grep -v ".git"
```
Expected: no output (zero references)

- [ ] **Step 2: Verify error isolation is in place**

In `src/data_engine.py`, `fetch_column` wraps every query in `try/except` and returns `None` on failure. Confirm visually by reading lines 30–45 of `src/data_engine.py`.

- [ ] **Step 3: Verify time-filter-immune columns**

Search registry for `time_filter=False` entries and confirm none reference `{time_start}` or `{time_end}` in their templates:

```bash
python -c "
from src.soql_registry import ALL_COLUMNS
for e in ALL_COLUMNS:
    if not e.time_filter and ('{time_start' in e.template or '{time_end' in e.template):
        print('VIOLATION:', e.col_id)
print('Check complete')
"
```
Expected: `Check complete` with no violations.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify error isolation and time-filter immunity, confirm zero dead code"
```

---

## Task 10: Final Smoke Test

- [ ] **Step 1: Start the app in a subprocess and check for import errors**

```bash
python -c "
import importlib, sys
mods = [
    'src.meta_filters',
    'src.soql_registry',
    'src.data_engine',
    'src.dashboard_ui',
]
for m in mods:
    try:
        importlib.import_module(m)
        print(f'OK: {m}')
    except Exception as e:
        print(f'FAIL: {m}: {e}')
        sys.exit(1)
"
```
Expected: four `OK:` lines.

- [ ] **Step 2: Verify `streamlit_dashboard.py` imports cleanly**

```bash
python -c "import streamlit_dashboard; print('import OK')" 2>&1
```
Note: may print Streamlit warnings — that's fine. Should not print import errors.

- [ ] **Step 3: Check all spec column IDs are in registry**

```bash
python -c "
from src.soql_registry import COLUMN_BY_ID
expected = [
    'S1-COL-C','S1-COL-D','S1-COL-E','S1-COL-F','S1-COL-G','S1-COL-H',
    'S1-COL-I','S1-COL-J','S1-COL-K','S1-COL-L','S1-COL-M','S1-COL-N',
    'S2-COL-O','S2-COL-P','S2-COL-Q','S2-COL-R','S2-COL-S',
    'S3-COL-T','S3-COL-U','S3-COL-V','S3-COL-W',
    'S4-COL-X','S4-COL-Y','S4-COL-Z','S4-COL-AA',
    'S5-COL-AB','S5-COL-AC','S5-COL-AD',
]
missing = [c for c in expected if c not in COLUMN_BY_ID]
if missing:
    print('MISSING:', missing)
else:
    print('All 28 column IDs present')
"
```
Expected: `All 28 column IDs present`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete AE Performance Dashboard rebuild per implementation-specs.md"
```

---

## Spec Cross-Reference

| Spec Rule | Where Enforced |
|-----------|---------------|
| Never modify SOQL filter logic | `soql_registry.py` — only placeholders parameterized |
| Time-filter immunity | `soql_registry.py` `time_filter=False` + no `{time_*}` in template |
| Per-SOQL error isolation | `data_engine.py::fetch_column` try/except |
| Computed columns E & H | `data_engine.py::fetch_all_columns` post-computation |
| SDR→AE via AEEmail__c | `soql_registry.py` S3 queries + `data_engine.py::_ae_email_clause` |
| Prospect-only filtering (S2) | Templates include role filters; post-filter note in docstring |
| Channel Partner exclusions (S4) | HubSpot, inbound, both Gong filters, and Related_To_Object__c!=Case in every S4 template |
| Blocked columns (S2-Q, S5) | `blocked=True` in registry; shown as "Pending" in UI |
