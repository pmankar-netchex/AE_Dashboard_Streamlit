# Dashboard Customization Guide

## Editing SOQL Queries

All metric queries are defined in `src/soql_registry.py` and can be edited live via the **SOQL Management tab** in the dashboard UI.

### Via the UI (recommended)

1. Open the dashboard → **SOQL Management** tab
2. Expand the column you want to edit (e.g. `[S1-COL-M] Total Closed Won`)
3. Edit the SOQL in the text area
4. Click **Test** — the query is executed against your Salesforce org; errors are shown inline
5. If the test passes, click **Save**
6. Click **Refresh Dashboard with Updated Queries** to apply

Saved overrides persist for the current session. To make them permanent, copy the edited query back into `src/soql_registry.py`.

### Via code

Edit the `template` string of the relevant `SOQLEntry` in `src/soql_registry.py`.

**Rules:**
- Never change the filter logic — only parameterize values using `{placeholders}`
- Available placeholders: `{owner_clause}`, `{ae_email_clause}`, `{time_start}`, `{time_end}`, `{time_start_date}`, `{time_end_date}`, `{fiscal_year_start}`, `{this_month_start}`, `{this_month_end}`, `{next_month_start}`, `{next_month_end}`
- Columns with `time_filter=False` must NOT use `{time_start}`/`{time_end}` — they use fixed windows

### Common query edits

#### Change "Closed Won" stage name

In `S1_COL_D`, `S1_COL_G`, `S1_COL_M`:
```sql
-- Before
WHERE StageName = 'Closed Won'

-- After (match your org's stage name)
WHERE StageName = 'Closed/Won'
```

#### Change Channel Partner types

In `S4_COL_X`, `S4_COL_Y`, `S4_COL_Z`, `S4_COL_AA` — edit the `Type__c IN (...)` list:
```sql
AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
```

#### Change fiscal year start month

In `src/meta_filters.py`:
```python
FISCAL_YEAR_START_MONTH = 4  # April fiscal year
```

---

## Adding a New Metric Column

1. Add a new `SOQLEntry` in `src/soql_registry.py`:

```python
MY_NEW_COL = SOQLEntry(
    col_id="S1-COL-NEW",
    display_name="My New Metric",
    section="Pipeline & Quota",
    description="What this measures.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Opportunity
WHERE {owner_clause}
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
  AND RecordType.Name = 'Enterprise'
""",
)
```

2. Add it to `ALL_COLUMNS` in the right position.

3. If it needs currency or percent formatting, add its `col_id` to `CURRENCY_COLS` or `PERCENT_COLS` in `src/dashboard_ui.py`.

4. Add a tooltip entry to the `TOOLTIPS` dict in `src/dashboard_ui.py`.

---

## Changing the Sidebar Filters

### Add a new time period preset

In `streamlit_dashboard.py` — extend the selectbox list:
```python
time_presets = ["Last Week", "This Week", "Last Month", "This Month", "Last Quarter", "Custom"]
```

Then add the resolver in `src/meta_filters.py`:
```python
def last_quarter_range() -> tuple[date, date]:
    ...

mapping = {
    ...
    "Last Quarter": last_quarter_range,
}
```

### Filter AEs by a custom field (e.g. Region)

In `src/data_engine.py`, extend `get_ae_names_list()` to include region, then add a Region selectbox to `render_sidebar_filters()` in `streamlit_dashboard.py`.

---

## Changing the UI

### Dashboard colors / CSS

In `src/dashboard_ui.py`, edit `apply_custom_css()`:
```python
st.markdown("""
<style>
/* Change table header color */
.stDataFrame thead { background-color: #1f2937; color: white; }
</style>
""", unsafe_allow_html=True)
```

### Add a KPI widget

In `src/dashboard_ui.py`, extend the `kpis` list in `display_kpi_widgets()`:
```python
kpis = [
    ...
    ("My New Metric", "S1-COL-NEW", fmt_number, False),
]
```
Tuple format: `(label, col_id, formatter_fn, is_average)`.

### Add a chart

In `src/dashboard_ui.py`, extend `display_charts()`:
```python
with col2:
    if "S1-COL-N" in df.columns:
        chart_df = df[["AE Name", "S1-COL-N"]].copy()
        chart_df["S1-COL-N"] = pd.to_numeric(chart_df["S1-COL-N"], errors="coerce")
        fig = px.bar(chart_df, x="AE Name", y="S1-COL-N", title="Closed Lost by AE")
        st.plotly_chart(fig, use_container_width=True)
```

### Change currency format

In `src/dashboard_ui.py`:
```python
def fmt_currency(val) -> str:
    ...
    return f"£{val:,.0f}"   # Switch to GBP
    # return f"${val:,.2f}" # Show cents
```

---

## Authentication

### Enable Azure AD (MSAL) — optional

Add to `.env`:
```bash
AZURE_CLIENT_ID=your_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_secret
AZURE_REDIRECT_URI=http://localhost:8501
```

See [AZURE_AD_SETUP.md](AZURE_AD_SETUP.md) for full setup steps.

### Add username/password Salesforce auth (fallback)

In `.env` (used only if OAuth tokens are unavailable):
```bash
SALESFORCE_USERNAME=user@company.com
SALESFORCE_PASSWORD=yourpassword
SALESFORCE_SECURITY_TOKEN=yourtoken
```

---

## Testing Changes

After editing any file:
```bash
./scripts/run.sh
```

Streamlit auto-reloads on file save. For query changes, use the SOQL Management tab's Test button to validate before saving.
