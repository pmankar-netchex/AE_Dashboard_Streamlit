# Dashboard Customization Guide

The dashboard is modularized for easy customization. Each file has a specific purpose.

## File Structure

```
streamlit_dashboard.py          Main app (OAuth, flow control)
├── src/salesforce_oauth.py     OAuth login flow
├── src/salesforce_queries.py   ⚙️ SOQL queries by entity
├── src/dashboard_calculations.py  ⚙️ Business logic & formulas
└── src/dashboard_ui.py         ⚙️ Display & styling
```

Files marked with ⚙️ contain customization points documented below.

---

## Customize SOQL Queries → `src/salesforce_queries.py`

All Salesforce queries are in this file, organized by entity.

### Change Closed Won Stage Name

```python
# Line 79
AND StageName = 'Closed Won'
```

Change to your org's stage name: `'Won'`, `'Closed-Won'`, etc.

### Filter Users by Profile/Role

```python
# Line 23 - Add after Monthly_Quota__c != null
AND Profile.Name LIKE '%Sales%'
# Or:
AND UserRole.Name LIKE '%AE%'
```

### Change Meeting Keywords

```python
# Line 143
AND (Subject LIKE '%meeting%' OR Subject LIKE '%call%' OR Subject LIKE '%demo%')
```

Add your keywords: `'%discovery%'`, `'%follow-up%'`, etc.

### Add Custom Fields

```python
# Line 19 - User query
SELECT Id, Name, Monthly_Quota__c, Pipeline_Coverage_Ratio__c, Region__c, Team__c
```

### Filter by RecordType

```python
# Line 80 - Add to Opportunity query
AND RecordType.Name = 'Enterprise'
```

### Exclude Recurring Meetings

```python
# Line 143 - Add to Event query
AND IsRecurrence = false
```

### Minimum Opportunity Amount

```python
# Line 80 - Add to Opportunity query
AND Amount > 1000
```

**See comments in `salesforce_queries.py` for more examples.**

---

## Customize Calculations → `src/dashboard_calculations.py`

Business logic and formulas.

### Change Quota Calculation

```python
# Line 55
remainder = monthly_quota - closed_won
```

Change to: `remainder = max(0, monthly_quota - closed_won)` (never negative).

### Adjust Pipeline Coverage Formula

```python
# Line 56
pipeline_should_have = remainder * pipeline_coverage_ratio
```

Customize based on your methodology.

### Update Meetings Needed Formula

```python
# Lines 17-35
def calculate_meetings_needed(remaining_quota, avg_deal_size=5000, win_rate=0.20):
    deals_needed = remaining_quota / avg_deal_size
    meetings_needed = deals_needed / win_rate
    return int(meetings_needed)
```

Change defaults or the entire formula.

### Add More Columns

```python
# Line 63 - In dashboard_data.append()
'Manager': row.get('Manager__r', {}).get('Name', 'N/A'),
'Region': row.get('Region__c', 'N/A'),
```

**See comments in `dashboard_calculations.py` for more.**

---

## Customize UI → `src/dashboard_ui.py`

Display formatting and styling.

### Change Dashboard Colors

```python
# Lines 13-31
h1 { color: #1f77b4; }  # Change title color
.oauth-btn { background: #00a1e0; }  # Change button color
```

### Update Currency Format

```python
# Line 69
col: '${:,.0f}' for col in currency_cols
```

Change to: `'${:,.2f}'` for cents, `'£{:,.0f}'` for pounds, etc.

### Add More Metrics

```python
# In display_summary_metrics(), after col4:
with col5:
    avg_attainment = df['Closed Won'].sum() / df['Monthly Quota'].sum()
    st.metric("Avg Attainment", f"{avg_attainment:.1%}")
```

### Add Charts

```python
# In display_insights() or main
import plotly.express as px
fig = px.bar(df, x='AE Name', y='Closed Won', title='Closed Won by AE')
st.plotly_chart(fig)
```

### Conditional Formatting

```python
# In style_dataframe()
def highlight_high_attainment(val):
    if val > 100: return 'background-color: #ccffcc'
    if val < 50: return 'background-color: #ffcccc'
    return ''
```

**See comments in `dashboard_ui.py` for more.**

---

## Quick Reference

| What to customize | File | Section |
|-------------------|------|---------|
| Stage names | `src/salesforce_queries.py` | Line 79 |
| User filters | `src/salesforce_queries.py` | Line 23 |
| Meeting keywords | `src/salesforce_queries.py` | Line 143 |
| Quota formula | `src/dashboard_calculations.py` | Line 55 |
| Meetings needed | `src/dashboard_calculations.py` | Line 17 |
| Colors/CSS | `src/dashboard_ui.py` | Line 13 |
| Currency format | `src/dashboard_ui.py` | Line 69 |
| Metrics shown | `src/dashboard_ui.py` | Line 99 |
| Insights/charts | `src/dashboard_ui.py` | Line 121 |

---

## Testing Changes

After editing any file:

```bash
./scripts/run.sh
```

Changes are applied immediately (Streamlit auto-reloads).
