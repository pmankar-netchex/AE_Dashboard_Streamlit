"""
SOQL Registry — canonical queries per column ID.
[spec: Section D]

CRITICAL RULES (from spec):
1. Never change filter logic; only parameterize placeholders.
2. time_filter=False columns ignore the meta time-period filter.
3. Per-SOQL error isolation: if one query fails, only its columns show NaN/error.
4. Columns E and H are computed — no SOQL.
5. SDR queries use OwnerId IN (Assigned_SDR_Outbound__c from the AE’s User record).
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
    """Build the OwnerId / Manager filter clause for Opportunity."""
    if p.get("manager_name") and not p.get("ae_user_id"):
        return f"Owner.Manager.Name = '{p['manager_name']}'"
    if p.get("ae_user_id"):
        return f"OwnerId = '{p['ae_user_id']}'"
    return "OwnerId != null"


def _quota_owner_clause(p: dict) -> str:
    """Build the QuotaOwnerId filter clause for ForecastingQuota."""
    if p.get("ae_user_id"):
        return f"QuotaOwnerId = '{p['ae_user_id']}'"
    return "QuotaOwnerId != null"


def _custom_owner_clause(p: dict) -> str:
    """Build the Assigned_ID_Custom__c filter clause for Task/Event objects."""
    if p.get("ae_user_id"):
        return f"Assigned_ID_Custom__c = '{p['ae_user_id']}'"
    return "Assigned_ID_Custom__c != null"


def _ae_email_clause(p: dict) -> str:
    """SDR→AE linkage via AEEmail__c."""
    return f"Owner.AEEmail__c = '{p.get('ae_email', '')}'"


def _sdr_owner_clause(p: dict) -> str:
    """Build OwnerId IN (subquery) from AE's Assigned_SDR_Outbound__c — SDR(s) associated with the given AE."""
    ae_id = p.get("ae_user_id", "")
    if not ae_id:
        return "OwnerId != null"
    # AE User has Assigned_SDR_Outbound__c pointing to SDR User(s); use those as owner IDs
    return (
        f"OwnerId IN (SELECT Assigned_SDR_Outbound__c FROM User WHERE Id = '{ae_id}'"
        f" AND Assigned_SDR_Outbound__c != null)"
    )


_CLAUSE_BUILDERS = {
    "{owner_clause}": ("Owner Clause", _owner_clause),
    "{quota_owner_clause}": ("Quota Owner Clause", _quota_owner_clause),
    "{custom_owner_clause}": ("Custom Owner Clause", _custom_owner_clause),
    "{ae_email_clause}": ("AE Email Clause", _ae_email_clause),
    "{sdr_owner_clause}": ("SDR Owner Clause", _sdr_owner_clause),
}

# Mapping of batchable clause placeholders → GROUP BY field
BATCH_FIELD_MAP = {
    "{owner_clause}": "OwnerId",
    "{quota_owner_clause}": "QuotaOwnerId",
    "{custom_owner_clause}": "Assigned_ID_Custom__c",
}


def resolve_owner_clauses(template: str, params: dict) -> list[tuple[str, str, str]]:
    """Return [(display_name, placeholder, resolved)] for owner clauses in the template."""
    result = []
    for placeholder, (name, builder) in _CLAUSE_BUILDERS.items():
        if placeholder in template:
            result.append((name, placeholder, builder(params)))
    return result


def build_query(entry: SOQLEntry, params: dict) -> str:
    """
    Substitute params into the SOQL template.
    params keys defined by meta_filters.build_filter_params().
    """
    owner = _owner_clause(params)
    quota_owner = _quota_owner_clause(params)
    custom_owner = _custom_owner_clause(params)
    ae_email = _ae_email_clause(params)
    sdr_owner = _sdr_owner_clause(params)
    return entry.template.format(
        owner_clause=owner,
        quota_owner_clause=quota_owner,
        custom_owner_clause=custom_owner,
        ae_email_clause=ae_email,
        sdr_owner_clause=sdr_owner,
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
WHERE {quota_owner_clause}
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
WHERE StageName = 'Closed/Won'
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
WHERE {quota_owner_clause}
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
WHERE StageName = 'Closed/Won'
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
WHERE StageName = 'Closed/Won'
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
WHERE StageName = 'Closed/Lost'
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
WHERE (Type = 'Email' OR TaskSubtype = 'Email')
  AND IsClosed = true
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
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
WHERE (Type LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND IsClosed = true
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
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
WHERE (Type = 'Email' OR TaskSubtype = 'Email')
  AND IsClosed = true
  AND {sdr_owner_clause}
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
WHERE (Type LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND IsClosed = true
  AND {sdr_owner_clause}
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
  AND {sdr_owner_clause}
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
  AND {sdr_owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

# ============================================================
# SECTION 4 — Channel Partners  [S4-COL-X through S4-COL-AA]
# ============================================================
# NOTE [spec rule 7]: All four exclusions mandatory:
#   HubSpot integration, inbound calls, Gong-logged (BOTH filters), Case-related.

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
WHERE (Type = 'Email' OR TaskSubtype = 'Email')
  AND IsClosed = true
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Inbound_Call__c = false
  AND (NOT Subject LIKE '%Gong In%')
  AND (NOT Subject LIKE '%[ ref:!%')
  AND Related_To_Object__c != 'Case'
  AND WhoId IN (SELECT Id FROM Contact WHERE Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant'))
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
WHERE (Type LIKE '%Call%' OR TaskSubtype LIKE '%Call%')
  AND IsClosed = true
  AND CreatedBy.Name != 'Hubspot Integration'
  AND Inbound_Call__c = false
  AND (NOT Subject LIKE '%Gong In%')
  AND (NOT Subject LIKE '%[ ref:!%')
  AND Related_To_Object__c != 'Case'
  AND WhoId IN (SELECT Id FROM Contact WHERE Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
                  'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant'))
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
  AND WhoId IN (SELECT Id FROM Contact WHERE Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
               'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant'))
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
  AND WhoId IN (SELECT Id FROM Contact WHERE Type__c IN ('Employee Benefits Broker','CPA','Retirement Broker',
               'Financial Advisor','Fractional Executive','Bank','Advisor / Consultant'))
  AND {owner_clause}
  AND ActivityDate >= {time_start_date}
  AND ActivityDate <= {time_end_date}
""",
)

# ============================================================
# SECTION 6 — Pipeline Generated  [S6-COL-AE through S6-COL-AL]
# ============================================================
# Breaks down pipeline creation by source: Self-Gen, SDR, Channel Partner, Marketing.
# Self-Gen and SDR queries use {ae_user_id} directly (per-AE, not batchable).
# CP queries use {owner_clause} + LeadSource (batchable). Marketing is BLOCKED.

S6_COL_AE = SOQLEntry(
    col_id="S6-COL-AE",
    display_name="Self-Gen Opps",
    section="Self-Gen Pipeline Creation",
    description="Opportunities created by the AE themselves (CreatedById = OwnerId).",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Opportunity
WHERE OwnerId = '{ae_user_id}'
  AND CreatedById = '{ae_user_id}'
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S6_COL_AF = SOQLEntry(
    col_id="S6-COL-AF",
    display_name="Self-Gen Pipeline $",
    section="Self-Gen Pipeline Creation",
    description="Pipeline dollars from opportunities the AE created themselves.",
    aggregation="SUM(Amount)",
    time_filter=True,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE OwnerId = '{ae_user_id}'
  AND CreatedById = '{ae_user_id}'
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S6_COL_AG = SOQLEntry(
    col_id="S6-COL-AG",
    display_name="SDR Opps",
    section="SDR Activity",
    description="Opportunities created by the AE's assigned SDR.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Opportunity
WHERE OwnerId = '{ae_user_id}'
  AND CreatedById IN (SELECT Assigned_SDR_Outbound__c FROM User
                      WHERE Id = '{ae_user_id}' AND Assigned_SDR_Outbound__c != null)
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S6_COL_AH = SOQLEntry(
    col_id="S6-COL-AH",
    display_name="SDR Pipeline $",
    section="SDR Activity",
    description="Pipeline dollars from opportunities created by the AE's assigned SDR.",
    aggregation="SUM(Amount)",
    time_filter=True,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE OwnerId = '{ae_user_id}'
  AND CreatedById IN (SELECT Assigned_SDR_Outbound__c FROM User
                      WHERE Id = '{ae_user_id}' AND Assigned_SDR_Outbound__c != null)
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S6_COL_AI = SOQLEntry(
    col_id="S6-COL-AI",
    display_name="CP Opps",
    section="Channel Partners",
    description="Channel partner-sourced opportunities. Edit SOQL to match your org's LeadSource values.",
    aggregation="COUNT(Id)",
    time_filter=True,
    template="""
SELECT COUNT(Id) total
FROM Opportunity
WHERE {owner_clause}
  AND LeadSource LIKE '%Partner%'
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S6_COL_AJ = SOQLEntry(
    col_id="S6-COL-AJ",
    display_name="CP Pipeline $",
    section="Channel Partners",
    description="Pipeline dollars from channel partner-sourced opportunities. Edit SOQL to match your org's LeadSource values.",
    aggregation="SUM(Amount)",
    time_filter=True,
    template="""
SELECT SUM(Amount) total
FROM Opportunity
WHERE {owner_clause}
  AND LeadSource LIKE '%Partner%'
  AND CreatedDate >= {time_start}
  AND CreatedDate <= {time_end}
""",
)

S6_COL_AK = SOQLEntry(
    col_id="S6-COL-AK",
    display_name="Marketing Opps",
    section="Marketing",
    description="BLOCKED: Source__c / LeadSource field values pending confirmation.",
    aggregation="COUNT (TBD)",
    time_filter=True,
    blocked=True,
    template="",
)

S6_COL_AL = SOQLEntry(
    col_id="S6-COL-AL",
    display_name="Marketing Pipeline $",
    section="Marketing",
    description="BLOCKED: Source__c / LeadSource field values pending confirmation.",
    aggregation="SUM (TBD)",
    time_filter=True,
    blocked=True,
    template="",
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
    # Section 1 — Pipeline & Quota
    S1_COL_C, S1_COL_D, S1_COL_E, S1_COL_F, S1_COL_G, S1_COL_H,
    S1_COL_I, S1_COL_J, S1_COL_K, S1_COL_L, S1_COL_M, S1_COL_N,
    # Section 2 — Self-Gen: *Pipeline $, Opps*, Emails, Calls, Voicemail, Foot Canvass, Net New
    S6_COL_AF, S6_COL_AE, S2_COL_O, S2_COL_P, S2_COL_Q, S2_COL_R, S2_COL_S,
    # Section 3 — SDR: *Pipeline $, Opps*, Emails, Calls, Mtgs Scheduled, Mtgs Held
    S6_COL_AH, S6_COL_AG, S3_COL_T, S3_COL_U, S3_COL_V, S3_COL_W,
    # Section 4 — CP: *Pipeline $, Opps*, Emails, Calls, Mtgs Scheduled, Mtgs Held
    S6_COL_AJ, S6_COL_AI, S4_COL_X, S4_COL_Y, S4_COL_Z, S4_COL_AA,
    # Section 5 — Marketing: *Pipeline $, Opps*, Events, Inbound, Other
    S6_COL_AL, S6_COL_AK, S5_COL_AB, S5_COL_AC, S5_COL_AD,
]

COLUMN_BY_ID: dict[str, SOQLEntry] = {c.col_id: c for c in ALL_COLUMNS}

SECTIONS: list[str] = [
    "Pipeline & Quota",
    "Self-Gen Pipeline Creation",
    "SDR Activity",
    "Channel Partners",
    "Marketing",
]
