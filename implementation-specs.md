# AE Performance Dashboard — Implementation Spec

You are building a Streamlit dashboard for GTM leadership that displays AE (Account Executive) performance metrics pulled from Salesforce via SOQL. This file is the single source of truth for all metric definitions, query logic, and UI behavior.

**Read this entire document before writing any code. Reference it by section ID (e.g., `[S1-COL-C]`) when implementing.**

---

## CRITICAL RULES

These rules override any assumptions. Violating them is a bug.

1. **Never modify a SOQL query's filter logic or field list.** The queries below are canonical. You may only parameterize the placeholder values (`<AE User Id>`, `<time_period_filter>`, etc.).
2. **Time-filter immunity.** Columns marked `time_filter: false` have fixed time windows (YTD, This Month, Next Month). The meta time-period filter must NEVER override these. Only columns marked `time_filter: true` accept the user's time-period selection.
3. **Per-SOQL error isolation.** If a SOQL query fails, only the columns sourced from that query show an error/NaN. The rest of the dashboard must render normally.
4. **Computed columns have no SOQL.** Columns E and H are calculated in the application layer from other columns. Do not query Salesforce for them.
5. **SDR→AE linkage uses `AEEmail__c`.** Section 3 queries join SDR activity to the AE via `User.AEEmail__c = '<AE Email>'`, NOT via `OwnerId`.
6. **Prospect-only filtering in Section 2** requires checking `Account.RecordType.Name` or `Contact.RecordType.Name` via relationship fields, or handling the `Lead` object (always a prospect). This cannot be done in a single WHERE clause — plan for subquery or post-filter.
7. **Channel Partner exclusions in Section 4** must exclude HubSpot integration records, inbound calls, Gong-logged activities, and Case-related records. All four exclusions are mandatory.

---

## A. META FILTERS

Meta filters are global UI controls in the sidebar. They parameterize ALL SOQL queries.

### A.1 Filter Definitions

```python
META_FILTERS = {
    "manager": {
        "label": "Manager",
        "control": "selectbox",
        "soql_field": "Owner.Manager.Name",
        "behavior": "When selected, aggregate data for ALL AEs under this manager"
    },
    "ae_name": {
        "label": "AE Name",
        "control": "selectbox",
        "soql_field": "Owner.Name",
        "behavior": "When selected, show data for this individual AE only"
    },
    "time_period": {
        "label": "Time Period",
        "control": "selectbox + date_input",
        "presets": ["Last Week", "This Week", "Last Month", "This Month"],
        "custom": "Date range selector for custom range",
        "soql_field": "<date_field> >= <start> AND <date_field> <= <end>"
    }
}
```

### A.2 Meta Filter SOQL Injection Pattern

Every query gets these WHERE clauses appended (unless the column is time-filter-immune):

```sql
WHERE Owner.Name = '<AE Name>'
  AND Owner.Manager.Name = '<Manager Name>'
  AND <date_field> >= <time_period_start>
  AND <date_field> <= <time_period_end>
```

For SDR queries (Section 3), replace `OwnerId = '<AE User Id>'` with the `AEEmail__c` join.

### A.3 Aggregation Logic

- **Manager selected, no AE selected** → query returns data for ALL AEs under that manager. Group by AE in the dashboard table (one row per AE).
- **AE selected** → query returns data for that single AE.
- The SOQL template uses `OwnerId = '<AE User Id>'` as the base. When aggregating by manager, remove the `OwnerId` filter and use `Owner.Manager.Name = '<Manager>'` instead.

---

## B. UI REQUIREMENTS

Build these into the Streamlit app. This is for GTM leadership — optimize for executive-level readability.

### B.1 Layout

- **KPI widgets** at the top of the page showing high-level impact numbers at a glance.
- **Bar charts and line charts** for critical trend/comparison information.
- **Heatmaps** on critical metrics to visually highlight performance outliers.
- **Metric grouping**: group columns by their section (Pipeline & Quota, Self-Gen, SDR Activity, Channel Partners, Marketing). Each group should be collapsible/cascadable.
- **Column freezing**: allow freezing columns (like Excel) so AE name stays visible during horizontal scroll.

### B.2 Table Features

- **Global table search**: search across all visible table data.
- **Per-column filtering**: data-type-aware filters (numeric range for numbers, text match for strings, calendar picker for dates).
- **Date column filtering**: include a calendar picker control.
- **Column visibility menu**: let the user hide/show columns when the dashboard is too wide.
- **Sorting**: clickable column headers to sort ascending/descending.
- **Pagination**: paginate the data table.

### B.3 Data Freshness

- On dashboard open, automatically fetch latest data from Salesforce.
- Display a **fetch timestamp** showing when data was last pulled.
- Provide a **Refresh button** on the dashboard that re-fetches all data and updates the timestamp.

### B.4 SOQL Management Tab (separate Streamlit tab)

Build a second tab with these features:

- Display each SOQL query with its **name**, **description**, and **full query text**.
- Allow humans to **edit** the SOQL text inline.
- Provide a **Test** button per SOQL that executes it against Salesforce and shows results/errors.
- Only allow **saving** a SOQL if it executed successfully (no saving broken queries).
- After a SOQL is updated and saved, provide a **Refresh Dashboard** button to re-fetch all data.

### B.5 Salesforce Connection Tab (separate Streamlit tab)

- Show Salesforce connection status (connected/disconnected, instance URL, authenticated user).

### B.6 Tooltips

- Add tooltips on each metric column header explaining the computation logic and filtering rules in plain language for non-technical reviewers.

---

## C. SALESFORCE OBJECT REFERENCE

Use this as a lookup when building queries and parsing responses.

```python
SF_OBJECTS = {
    "Opportunity": {
        "api_name": "Opportunity",
        "fields": ["Amount", "StageName", "CloseDate", "OwnerId", "CreatedDate", "IsClosed"]
    },
    "ForecastingQuota": {
        "api_name": "ForecastingQuota",
        "fields": ["QuotaAmount", "StartDate", "OwnerId"]
    },
    "ForecastingQuotaItem": {
        "api_name": "ForecastingQuotaItem",
        "fields": [],  # related to ForecastingQuota
        "note": "Used for quota splits"
    },
    "ForecastingSplit": {
        "api_name": "ForecastingSplit",
        "fields": ["SplitType"],
        "note": "SplitType: Revenue = Reps, Overlay = Managers"
    },
    "Task": {
        "api_name": "Task",
        "fields": ["ActivityType", "TaskSubtype", "WhoId", "WhatId", "OwnerId",
                    "ActivityDate", "Subject", "Inbound_Call__c", "Type__c", "Related_To_Object__c"]
    },
    "Event": {
        "api_name": "Event",
        "fields": ["RecordTypeId", "Meeting_Type__c", "Meeting_Specifics__c",
                    "Meeting_Status__c", "WhoId", "WhatId", "OwnerId", "CreatedById",
                    "ActivityDate", "Type__c", "Source__c"]
    },
    "User": {
        "api_name": "User",
        "fields": ["Name", "UserRoleId", "AEEmail__c", "ManagerId"],
        "note": "AEEmail__c is a custom field linking SDR to their paired AE"
    },
    "UserRole": {
        "api_name": "UserRole",
        "fields": ["Name"]
    },
    "Account": {
        "api_name": "Account",
        "fields": ["RecordTypeId", "RecordType.Name"]
    },
    "Contact": {
        "api_name": "Contact",
        "fields": ["RecordTypeId", "RecordType.Name"]
    },
    "Lead": {
        "api_name": "Lead",
        "fields": [],
        "note": "Always treated as prospect — no RecordType filtering needed"
    }
}
```

---

## D. METRIC DEFINITIONS — Column-by-Column

Each column has an ID like `[S1-COL-C]` (Section 1, Column C). Use these IDs in code comments, SOQL registry names, and error messages.

### D.1 Section 1 — Pipeline & Quota (Columns C–N)

**Section display name:** `"Pipeline Generated"`

---

#### `[S1-COL-C]` Quota YTD

- **Object:** `ForecastingQuota`
- **Fields:** `QuotaAmount`, `StartDate`, `OwnerId`
- **Filter:** `StartDate` within current fiscal year; join to `User` via `OwnerId`
- **Aggregation:** `SUM(QuotaAmount)`
- **Time filter:** `false` — always fiscal year start to today

```sql
SELECT SUM(QuotaAmount)
FROM ForecastingQuota
WHERE OwnerId = '<AE User Id>'
  AND StartDate >= <fiscal_year_start>
  AND StartDate <= TODAY
```

---

#### `[S1-COL-D]` Bookings YTD

- **Object:** `Opportunity`
- **Fields:** `Amount`, `StageName`, `CloseDate`, `OwnerId`
- **Filter:** `StageName = 'Closed Won'`; `CloseDate` within current fiscal year
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `false` — always fiscal year start to today

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND OwnerId = '<AE User Id>'
  AND CloseDate >= <fiscal_year_start>
  AND CloseDate <= TODAY
```

---

#### `[S1-COL-E]` YTD Quota Attainment %

- **Type:** Computed — no SOQL
- **Formula:** `[S1-COL-D] / [S1-COL-C]` (Bookings YTD / Quota YTD)
- **Spreadsheet equivalent:** `=D5/C5`
- **Objects referenced:** `Opportunity` (for D), `ForecastingQuota` + `ForecastingQuotaItem` (for C)
- **Time filter:** `false` — derived from YTD metrics
- **Note:** Uses `ForecastingQuotaItem` for quota splits; `ForecastingSplit` for rep = Revenue Split, manager = Overlay Split.

---

#### `[S1-COL-F]` Quota This Month

- **Object:** `ForecastingQuota`
- **Fields:** `QuotaAmount`, `StartDate`, `OwnerId`
- **Filter:** `StartDate` within current calendar month
- **Aggregation:** `SUM(QuotaAmount)`
- **Time filter:** `false` — always current calendar month

```sql
SELECT SUM(QuotaAmount)
FROM ForecastingQuota
WHERE OwnerId = '<AE User Id>'
  AND StartDate = THIS_MONTH
```

---

#### `[S1-COL-G]` Bookings This Month

- **Object:** `Opportunity`
- **Fields:** `Amount`, `StageName`, `CloseDate`, `OwnerId`
- **Filter:** `StageName = 'Closed Won'`; `CloseDate` = this month
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `false` — always current calendar month

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND OwnerId = '<AE User Id>'
  AND CloseDate = THIS_MONTH
```

---

#### `[S1-COL-H]` Month-to-Date Quota Attainment %

- **Type:** Computed — no SOQL
- **Formula:** `[S1-COL-G] / [S1-COL-F]` (Bookings This Month / Quota This Month)
- **Spreadsheet equivalent:** `=G5/F5`
- **Objects referenced:** `Opportunity` (for G), `ForecastingQuota` + `ForecastingQuotaItem` + `ForecastingSplit` (for F)
- **Time filter:** `false` — derived from current-month metrics
- **Note:** Reps → Revenue Splits; Managers → Overlay Splits.

---

#### `[S1-COL-I]` Total Open Pipeline (Close Date = Current Month)

- **Object:** `Opportunity`
- **Fields:** `Amount`, `StageName`, `CloseDate`, `OwnerId`
- **Filter:** Stage is NOT Closed; `CloseDate` within current month
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `false` — always current month

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE IsClosed = false
  AND OwnerId = '<AE User Id>'
  AND CloseDate = THIS_MONTH
```

---

#### `[S1-COL-J]` Total Open Pipeline (Close Date = Next Month)

- **Object:** `Opportunity`
- **Fields:** `Amount`, `StageName`, `CloseDate`, `OwnerId`
- **Filter:** Stage is NOT Closed; `CloseDate` within next month
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `false` — always next month

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE IsClosed = false
  AND OwnerId = '<AE User Id>'
  AND CloseDate = NEXT_MONTH
```

---

#### `[S1-COL-K]` Total # Opportunities Created (in time period)

- **Object:** `Opportunity`
- **Fields:** `Id`, `CreatedDate`, `OwnerId`
- **Filter:** `CreatedDate` within selected time period
- **Aggregation:** `COUNT(Id)`
- **Time filter:** `true` — uses `<time_period_filter>`

```sql
SELECT COUNT(Id)
FROM Opportunity
WHERE OwnerId = '<AE User Id>'
  AND CreatedDate = <time_period_filter>
```

---

#### `[S1-COL-L]` Total Pipeline $ Created (in time period)

- **Object:** `Opportunity`
- **Fields:** `Amount`, `CreatedDate`, `OwnerId`
- **Filter:** `CreatedDate` within selected time period
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `true` — uses `<time_period_filter>`

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE OwnerId = '<AE User Id>'
  AND CreatedDate = <time_period_filter>
```

---

#### `[S1-COL-M]` Total Closed Won (in time period)

- **Object:** `Opportunity`
- **Fields:** `Amount`, `StageName`, `CloseDate`, `OwnerId`
- **Filter:** `StageName = 'Closed Won'`; `CloseDate` within time period
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `true` — uses `<time_period_filter>`

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE StageName = 'Closed Won'
  AND OwnerId = '<AE User Id>'
  AND CloseDate = <time_period_filter>
```

---

#### `[S1-COL-N]` Total Closed Lost (in time period)

- **Object:** `Opportunity`
- **Fields:** `Amount`, `StageName`, `CloseDate`, `OwnerId`
- **Filter:** `StageName = 'Closed Lost'`; `CloseDate` within time period
- **Aggregation:** `SUM(Amount)`
- **Time filter:** `true` — uses `<time_period_filter>`

```sql
SELECT SUM(Amount)
FROM Opportunity
WHERE StageName = 'Closed Lost'
  AND OwnerId = '<AE User Id>'
  AND CloseDate = <time_period_filter>
```

---

### D.2 Section 2 — Self-Gen Pipeline Creation (Columns O–S)

**Section display name:** `"Self Gen Pipeline Creation (not channel partners – prospects)"`

These metrics cover AE-originated outbound activity to **prospect accounts only**. Exclude channel partners, account managers, and SDRs.

#### Common Filters for ALL Columns O–S

Apply these to every query in this section:

```python
SECTION_2_COMMON_FILTERS = {
    "role_include": "Owner.UserRole.Name LIKE '%Sales Rep%'",
    "role_exclude": [
        "Owner.UserRole.Name NOT LIKE '%Account Manager%'",
        "Owner.UserRole.Name NOT LIKE '%SDR%'"
    ],
    "prospect_only": [
        "Account.RecordType.Name = 'Prospect Account'",
        "OR Contact.RecordType.Name = 'Prospect Contact'",
        "OR object is Lead (always a prospect)"
    ]
}
```

> **Implementation challenge:** Prospect filtering requires checking `Account.RecordType.Name` or `Contact.RecordType.Name` via relationship fields or a subquery on the `What`/`Who` polymorphic fields. Plan for subquery or post-query filtering.

---

#### `[S2-COL-O]` Unique Email Recipients

- **Object:** `Task`
- **Fields:** `ActivityType`, `TaskSubtype`, `WhoId`, `OwnerId`, `WhatId`, `ActivityDate`
- **Filter:** `ActivityType = 'Email'` OR `TaskSubtype = 'Email'`; plus all Section 2 common filters
- **Aggregation:** `COUNT_DISTINCT(WhoId)` — unique contacts or leads
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhoId)
FROM Task
WHERE (ActivityType = 'Email' OR TaskSubtype = 'Email')
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND Owner.UserRole.Name NOT LIKE '%Account Manager%'
  AND Owner.UserRole.Name NOT LIKE '%SDR%'
  AND ActivityDate = <time_period_filter>
  AND OwnerId = '<AE User Id>'
```

---

#### `[S2-COL-P]` Unique Call Recipients

- **Object:** `Task`
- **Fields:** `ActivityType`, `TaskSubtype`, `WhoId`, `OwnerId`, `ActivityDate`
- **Filter:** `ActivityType` contains `Call` OR `TaskSubtype` contains `Call`; plus all Section 2 common filters
- **Aggregation:** `COUNT_DISTINCT(WhoId)`
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhoId)
FROM Task
WHERE (ActivityType LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND Owner.UserRole.Name NOT LIKE '%Account Manager%'
  AND Owner.UserRole.Name NOT LIKE '%SDR%'
  AND ActivityDate = <time_period_filter>
  AND OwnerId = '<AE User Id>'
```

---

#### `[S2-COL-Q]` Unique Voicemail Recipients

- **Status:** `TBD` — field mapping not yet defined
- **Likely object:** `Task`
- **Expected pattern:** Same as `[S2-COL-P]` (calls), with an additional filter on a voicemail indicator field (e.g., `TaskSubtype = 'Voicemail'` or a custom field)
- **Time filter:** `true` (expected)

> **BLOCKED:** Do not implement until the voicemail indicator field is confirmed. Stub this column with a placeholder/empty state.

---

#### `[S2-COL-R]` Unique Accounts with Foot Canvass

- **Object:** `Event`
- **Fields:** `RecordTypeId`, `Meeting_Type__c`, `Meeting_Specifics__c`, `WhatId`, `WhoId`, `OwnerId`, `ActivityDate`
- **Filter:** `RecordType.Name = 'Sales Event'`; `Meeting_Type__c = 'Prospect Meeting'`; `Meeting_Specifics__c = 'Foot Canvass'`; role filters (Sales Rep, not AM/SDR)
- **Aggregation:** `COUNT_DISTINCT(WhatId)` → unique accounts. Also available: `COUNT_DISTINCT(WhoId)` → unique leads
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhatId)
FROM Event
WHERE RecordType.Name = 'Sales Event'
  AND Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Foot Canvass'
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND OwnerId = '<AE User Id>'
  AND ActivityDate = <time_period_filter>
```

---

#### `[S2-COL-S]` Unique Accounts with Net New Meetings Created by AE

- **Object:** `Event`
- **Fields:** `RecordTypeId`, `Meeting_Type__c`, `Meeting_Specifics__c`, `WhatId`, `WhoId`, `OwnerId`, `ActivityDate`
- **Filter:** `RecordType.Name = 'Sales Event'`; `Meeting_Type__c = 'Prospect Meeting'`; `Meeting_Specifics__c = 'Net New'`; same role filters as `[S2-COL-R]`
- **Aggregation:** `COUNT_DISTINCT(WhatId)` (accounts) or `COUNT_DISTINCT(WhoId)` (leads)
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhatId)
FROM Event
WHERE RecordType.Name = 'Sales Event'
  AND Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Net New'
  AND Owner.UserRole.Name LIKE '%Sales Rep%'
  AND OwnerId = '<AE User Id>'
  AND ActivityDate = <time_period_filter>
```

---

### D.3 Section 3 — SDR Activity (Columns T–W)

**Section display name:** `"SDR Activity for This Rep"`

Tracks SDR-originated activity that supports the AE. The `User` object has a custom field `AEEmail__c` that links an SDR to their paired AE.

#### Key Join (applies to all Section 3 queries)

```sql
Owner.AEEmail__c = '<AE Email>'
```

This replaces the standard `OwnerId = '<AE User Id>'` filter. It connects SDR-owned activities to the AE they support.

---

#### `[S3-COL-T]` SDR Unique Email Recipients

- **Object:** `Task`
- **Fields:** `ActivityType`, `TaskSubtype`, `WhoId`, `OwnerId`, `ActivityDate`
- **Filter:** `ActivityType = 'Email'` OR `TaskSubtype = 'Email'`; `Owner.UserRole.Name` contains `SDR`; prospect only (`Account.RecordType.Name = 'Prospect Account'` or related `Lead`); join via `Owner.AEEmail__c = '<AE Email>'`
- **Aggregation:** `COUNT_DISTINCT(WhoId)`
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhoId)
FROM Task
WHERE (ActivityType = 'Email' OR TaskSubtype = 'Email')
  AND Owner.UserRole.Name LIKE '%SDR%'
  AND Owner.AEEmail__c = '<AE Email>'
  AND ActivityDate = <time_period_filter>
```

---

#### `[S3-COL-U]` SDR Unique Call Recipients

- **Object:** `Task`
- **Fields:** `ActivityType`, `TaskSubtype`, `WhoId`, `OwnerId`, `ActivityDate`
- **Filter:** `ActivityType` contains `Call` OR `TaskSubtype` contains `Call`; `Owner.UserRole.Name` contains `SDR`; join via `Owner.AEEmail__c = '<AE Email>'`
- **Aggregation:** `COUNT_DISTINCT(WhoId)`
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhoId)
FROM Task
WHERE (ActivityType LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND Owner.UserRole.Name LIKE '%SDR%'
  AND Owner.AEEmail__c = '<AE Email>'
  AND ActivityDate = <time_period_filter>
```

---

#### `[S3-COL-V]` SDR Unique Meetings Scheduled

- **Object:** `Event`
- **Fields:** `RecordTypeId`, `Meeting_Type__c`, `Meeting_Specifics__c`, `OwnerId`, `CreatedById`, `ActivityDate`
- **Filter:** `RecordType.Name = 'Sales Event'`; `Meeting_Type__c = 'Prospect Meeting'`; `Meeting_Specifics__c = 'Net New'`; `CreatedBy.UserRole.Name` contains `Sales Rep`; does NOT contain `Account Manager`, `SDR`
- **Aggregation:** `COUNT(Id)`
- **Time filter:** `true`

```sql
SELECT COUNT(Id)
FROM Event
WHERE RecordType.Name = 'Sales Event'
  AND Meeting_Type__c = 'Prospect Meeting'
  AND Meeting_Specifics__c = 'Net New'
  AND CreatedBy.UserRole.Name LIKE '%Sales Rep%'
  AND CreatedBy.UserRole.Name NOT LIKE '%Account Manager%'
  AND CreatedBy.UserRole.Name NOT LIKE '%SDR%'
  AND ActivityDate = <time_period_filter>
```

> **WARNING:** May need to use `Source__c` field to reliably identify SDR-sourced meetings. Verify during testing.

---

#### `[S3-COL-W]` SDR Unique Meetings Held

- **Object:** `Event`
- **Fields:** `Meeting_Type__c`, `Meeting_Specifics__c`, `OwnerId`, `CreatedById`, `ActivityDate`
- **Filter:** `Meeting_Type__c = 'Prospect Meeting'`; `Meeting_Specifics__c = 'Net New'`; `CreatedBy.UserRole.Name` contains `SDR`
- **Owner role INCLUDE:** starts with `Sales Rep`, `Channel`, `Inbound`, `Sales Rep-HigherMe/Account Manager`
- **Owner role EXCLUDE:** does NOT contain `SDR`, `Client Success`, `Account Manager`, `Sales Engineer`, `Manager`, `Director`
- **Aggregation:** `COUNT(Id)`
- **Time filter:** `true`

```sql
SELECT COUNT(Id)
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
  AND ActivityDate = <time_period_filter>
```

---

### D.4 Section 4 — Channel Partners (Columns X–AA)

**Section display name:** `"Channel Partners"`

Tracks AE outreach and meetings with channel partner contacts (brokers, advisors, etc.). Excludes HubSpot integration records, inbound calls, and Gong-logged activities.

#### Common Filters for ALL Columns X–AA

Apply these to every query in this section:

```python
SECTION_4_COMMON_FILTERS = {
    "exclude_hubspot": "CreatedBy.Name != 'Hubspot Integration'",
    "exclude_inbound": "Inbound_Call__c = false",
    "exclude_gong": [
        "Subject NOT LIKE '%[Gong In]%'",
        "Subject NOT LIKE '%[ ref:!%'"
    ],
    "exclude_cases": "Related_To_Object__c != 'Case'",
    "partner_types": [
        "Employee Benefits Broker", "CPA", "Retirement Broker",
        "Financial Advisor", "Fractional Executive", "Bank",
        "Advisor / Consultant"
    ],
    "record_type": "Account.RecordType.Name = 'Channel Partner Contact' OR Contact.RecordType.Name = 'Channel Partner Contact'"
}
```

---

#### `[S4-COL-X]` Channel Partner Unique Emails

- **Object:** `Task`
- **Fields:** `ActivityType`, `TaskSubtype`, `WhoId`, `WhatId`, `OwnerId`, `CreatedById`, `Inbound_Call__c`, `Subject`, `Type__c`
- **Filter:** All Section 4 common filters + `ActivityType = 'Email'` OR `TaskSubtype = 'Email'`
- **Aggregation:** `COUNT_DISTINCT(WhoId)`
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhoId)
FROM Task
WHERE (ActivityType = 'Email' OR TaskSubtype = 'Email')
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Inbound_Call__c = false
  AND Subject NOT LIKE '%[Gong In]%'
  AND Subject NOT LIKE '%[ ref:!%'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND OwnerId = '<AE User Id>'
  AND ActivityDate = <time_period_filter>
```

---

#### `[S4-COL-Y]` Channel Partner Unique Calls

- **Object:** `Task`
- **Fields:** same as `[S4-COL-X]`
- **Filter:** All Section 4 common filters + `ActivityType` contains `Call` OR `TaskSubtype` contains `Call`
- **Aggregation:** `COUNT_DISTINCT(WhoId)`
- **Time filter:** `true`

```sql
SELECT COUNT_DISTINCT(WhoId)
FROM Task
WHERE (ActivityType LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Inbound_Call__c = false
  AND Subject NOT LIKE '%[Gong In]%'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND OwnerId = '<AE User Id>'
  AND ActivityDate = <time_period_filter>
```

---

#### `[S4-COL-Z]` Channel Partner Unique Meetings Scheduled

- **Object:** `Event`
- **Fields:** `RecordTypeId`, `Meeting_Type__c`, `Meeting_Status__c`, `OwnerId`, `CreatedById`, `Type__c`, `ActivityDate`
- **Filter:** `RecordType.Name = 'Partner Event'`; `Meeting_Type__c = 'Channel Partner Meeting'`; `Meeting_Status__c = 'Scheduled'`; Section 4 common filters (no HubSpot, Type IN list)
- **Aggregation:** `COUNT(Id)`
- **Time filter:** `true`

```sql
SELECT COUNT(Id)
FROM Event
WHERE RecordType.Name = 'Partner Event'
  AND Meeting_Type__c = 'Channel Partner Meeting'
  AND Meeting_Status__c = 'Scheduled'
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND OwnerId = '<AE User Id>'
  AND ActivityDate = <time_period_filter>
```

---

#### `[S4-COL-AA]` Channel Partner Unique Meetings Held

- **Object:** `Event`
- **Fields:** same as `[S4-COL-Z]`
- **Filter:** `RecordType.Name = 'Partner Event'`; `Meeting_Type__c = 'Channel Partner Meeting'`; `Meeting_Status__c` starts with `Attended`; Section 4 common filters
- **Aggregation:** `COUNT(Id)`
- **Time filter:** `true`

```sql
SELECT COUNT(Id)
FROM Event
WHERE RecordType.Name = 'Partner Event'
  AND Meeting_Type__c = 'Channel Partner Meeting'
  AND Meeting_Status__c LIKE 'Attended%'
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')
  AND OwnerId = '<AE User Id>'
  AND ActivityDate = <time_period_filter>
```

---

### D.5 Section 5 — Marketing (Columns AB–AD)

**Section display name:** `"Marketing"`

Tracks meetings attributed to marketing-generated sources.

> **BLOCKED: All three columns require confirmation of the specific `Source__c` or `LeadSource` field values used in this Salesforce org.** Stub these columns with placeholder/empty state until field values are confirmed.

---

#### `[S5-COL-AB]` Meetings from Events

- **Object:** `Event`
- **Filter:** Meeting source = marketing event (specific `Source__c` or `LeadSource` field TBD)
- **Aggregation:** `COUNT` of meetings
- **Status:** `BLOCKED` — pending field confirmation

---

#### `[S5-COL-AC]` Meetings from Inbound

- **Object:** `Event` or `Task`
- **Filter:** `Inbound_Call__c = true` OR `LeadSource` = Inbound type
- **Aggregation:** `COUNT` of meetings/activities
- **Status:** `BLOCKED` — pending field confirmation

---

#### `[S5-COL-AD]` Meetings from Other Marketing

- **Object:** `Event` or `Task`
- **Filter:** Source field identifies other marketing attribution (e.g., `LeadSource IN ('Web', 'Campaign', ...)`)
- **Aggregation:** `COUNT` of meetings
- **Status:** `BLOCKED` — pending field confirmation

---

## E. COLUMN REGISTRY (quick-reference)

Use this as the source of truth for building the SOQL config registry and the unified DataFrame.

| Column ID | Display Name | Section | Object | Aggregation | Time Filter | Computed |
|---|---|---|---|---|---|---|
| `S1-COL-C` | Quota YTD | Pipeline & Quota | ForecastingQuota | SUM(QuotaAmount) | `false` | no |
| `S1-COL-D` | Bookings YTD | Pipeline & Quota | Opportunity | SUM(Amount) | `false` | no |
| `S1-COL-E` | YTD Quota Attainment % | Pipeline & Quota | — | D / C | `false` | **yes** |
| `S1-COL-F` | Quota This Month | Pipeline & Quota | ForecastingQuota | SUM(QuotaAmount) | `false` | no |
| `S1-COL-G` | Bookings This Month | Pipeline & Quota | Opportunity | SUM(Amount) | `false` | no |
| `S1-COL-H` | MTD Quota Attainment % | Pipeline & Quota | — | G / F | `false` | **yes** |
| `S1-COL-I` | Open Pipeline (This Month) | Pipeline & Quota | Opportunity | SUM(Amount) | `false` | no |
| `S1-COL-J` | Open Pipeline (Next Month) | Pipeline & Quota | Opportunity | SUM(Amount) | `false` | no |
| `S1-COL-K` | # Opportunities Created | Pipeline & Quota | Opportunity | COUNT(Id) | `true` | no |
| `S1-COL-L` | Pipeline $ Created | Pipeline & Quota | Opportunity | SUM(Amount) | `true` | no |
| `S1-COL-M` | Total Closed Won | Pipeline & Quota | Opportunity | SUM(Amount) | `true` | no |
| `S1-COL-N` | Total Closed Lost | Pipeline & Quota | Opportunity | SUM(Amount) | `true` | no |
| `S2-COL-O` | Unique Email Recipients | Self-Gen Pipeline | Task | COUNT_DISTINCT(WhoId) | `true` | no |
| `S2-COL-P` | Unique Call Recipients | Self-Gen Pipeline | Task | COUNT_DISTINCT(WhoId) | `true` | no |
| `S2-COL-Q` | Unique Voicemail Recipients | Self-Gen Pipeline | Task | TBD | `true` | no |
| `S2-COL-R` | Unique Accts w/ Foot Canvass | Self-Gen Pipeline | Event | COUNT_DISTINCT(WhatId) | `true` | no |
| `S2-COL-S` | Unique Accts w/ Net New Mtgs | Self-Gen Pipeline | Event | COUNT_DISTINCT(WhatId) | `true` | no |
| `S3-COL-T` | SDR Unique Emails | SDR Activity | Task | COUNT_DISTINCT(WhoId) | `true` | no |
| `S3-COL-U` | SDR Unique Calls | SDR Activity | Task | COUNT_DISTINCT(WhoId) | `true` | no |
| `S3-COL-V` | SDR Unique Mtgs Scheduled | SDR Activity | Event | COUNT(Id) | `true` | no |
| `S3-COL-W` | SDR Unique Mtgs Held | SDR Activity | Event | COUNT(Id) | `true` | no |
| `S4-COL-X` | CP Unique Emails | Channel Partners | Task | COUNT_DISTINCT(WhoId) | `true` | no |
| `S4-COL-Y` | CP Unique Calls | Channel Partners | Task | COUNT_DISTINCT(WhoId) | `true` | no |
| `S4-COL-Z` | CP Mtgs Scheduled | Channel Partners | Event | COUNT(Id) | `true` | no |
| `S4-COL-AA` | CP Mtgs Held | Channel Partners | Event | COUNT(Id) | `true` | no |
| `S5-COL-AB` | Mtgs from Events | Marketing | Event | COUNT (TBD) | `true` | no |
| `S5-COL-AC` | Mtgs from Inbound | Marketing | Event/Task | COUNT (TBD) | `true` | no |
| `S5-COL-AD` | Mtgs from Other Marketing | Marketing | Event/Task | COUNT (TBD) | `true` | no |

---

## F. IMPLEMENTATION STEPS

Follow these in order. Do not skip ahead. Each step should be verifiable before moving to the next.

### Step 0 - Review existing code and reuse

Some critical information like .env.example try to maintain as is so there's minimal changes there

### Step 1 — Foundation & Codebase Cleanup

- Review existing codebase and reuse the following:
  - MSAL Authentication
  - Salesforce Connection setup
  - Deployment-related items (Bicep files, etc.)
- Remove older guides and structures to build new ones later.
- Do not introduce new SOQL or UI at this step.

### Step 2 — Meta Filtering UI + Query Parameterization

- Implement meta filtering fields in the Streamlit sidebar (Manager, AE Name, Time Period).
- Build the ability to send filter parameters from UI to the query module.
- Implement aggregation logic:
  - When **Manager** is selected → remove `OwnerId` filter, use `Owner.Manager.Name` filter, aggregate across all AEs.
  - When **AE Name** is selected → use `OwnerId` filter for that individual AE.

### Step 3 — SOQL Query Implementation

- Go through each metric in Section D and write the SOQL.
- Prefer **one SOQL per section** that pulls all required metrics for that section, where possible.
- Every SOQL must accept meta filter parameters. Do not hardcode AE IDs or date ranges.
- Reference each query by its column ID (e.g., `[S1-COL-C]`).

### Step 4 — Cross-Check Queries Against This Spec

- After writing all SOQLs, go back through each column definition in Section D and verify:
  - Filter logic matches exactly.
  - Fields match exactly.
  - Meta filter injection works correctly.
  - Join logic is correct (especially SDR → AE via `AEEmail__c`).
- Fix any deviations.

### Step 5 — Data Integration & Unified Table

- Verify the data structure returned from each SOQL response.
- Figure out joins between section data and meta filter dimensions.
- Build one unified DataFrame/table with:
  - Proper column ordering (C through AD as defined in Section E).
  - Meta filter application.
  - Graceful handling of missing/null data (show NaN or dash, not crash).

### Step 6 — SOQL Management UI + Dashboard Features

- Add proper naming for each SOQL with description of which columns it populates.
- Build the SOQL Management tab (see Section B.4 for full requirements).
- Build the Salesforce Connection tab (see Section B.5).
- Implement auto-fetch on load + fetch timestamp display.
- Add Refresh button on dashboard.

### Step 7 — Cleanup & Error Resilience

- Remove ALL residual SOQLs or code from any previous implementation. Zero dead code.
- Implement per-SOQL error isolation (see Critical Rule #3):
  - If one SOQL fails → only its columns become empty/NaN/error.
  - Rest of dashboard renders normally.

### Step 8 — UX Polish & Final Verification

- Verify the main dashboard UI/UX meets all requirements in Section B.
- Ensure logical traceability: given any column, you can find which SOQL populates it and update the query.
- Handle the time-filter edge cases:
  - Columns with `time_filter: false` must NOT be affected by the meta time-period filter.
  - Document these exceptions visibly in the SOQL Management tab.
- Add tooltips on metric column headers explaining computation and filter logic for non-technical users.
