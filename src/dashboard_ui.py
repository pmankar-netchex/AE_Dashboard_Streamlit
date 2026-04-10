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
    "Pipeline & Quota": "Pipeline & Quota",
    "Pipeline Generated": "Pipeline Generated (by Source)",
    "Self-Gen Pipeline Creation": "Self Gen Pipeline Creation (not channel partners – prospects)",
    "SDR Activity": "SDR Activity for This Rep",
    "Channel Partners": "Channel Partners",
    "Marketing": "Marketing",
}

CURRENCY_COLS = {
    "S1-COL-C", "S1-COL-D", "S1-COL-F", "S1-COL-G",
    "S1-COL-I", "S1-COL-J", "S1-COL-L", "S1-COL-M", "S1-COL-N",
    "S6-COL-AF", "S6-COL-AH", "S6-COL-AJ",
}
PERCENT_COLS = {"S1-COL-E", "S1-COL-H"}
LOWER_IS_BETTER = {"S1-COL-N"}

TOOLTIPS: dict[str, str] = {
    "S1-COL-C": "Quota YTD: SUM(ForecastingQuota.QuotaAmount) from fiscal year start to today. Time-filter immune.",
    "S1-COL-D": "Bookings YTD: SUM(Opportunity.Amount) where StageName='Closed Won', fiscal year to date. Time-filter immune.",
    "S1-COL-E": "YTD Quota Attainment %: Bookings YTD / Quota YTD (computed, no SOQL). Time-filter immune.",
    "S1-COL-F": "Quota This Month: SUM(ForecastingQuota.QuotaAmount) for THIS_MONTH. Time-filter immune.",
    "S1-COL-G": "Bookings This Month: SUM(Opportunity.Amount) closed won this month. Time-filter immune.",
    "S1-COL-H": "MTD Quota Attainment %: Bookings This Month / Quota This Month (computed). Time-filter immune.",
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
    "S6-COL-AE": "Self-Gen Opps: COUNT(Id) where AE created the opportunity themselves (CreatedById = OwnerId).",
    "S6-COL-AF": "Self-Gen Pipeline $: SUM(Amount) where AE created the opportunity themselves.",
    "S6-COL-AG": "SDR Opps: COUNT(Id) where the AE's assigned SDR created the opportunity.",
    "S6-COL-AH": "SDR Pipeline $: SUM(Amount) where the AE's assigned SDR created the opportunity.",
    "S6-COL-AI": "CP Opps: COUNT(Id) where LeadSource indicates channel partner. Edit SOQL to match your org.",
    "S6-COL-AJ": "CP Pipeline $: SUM(Amount) where LeadSource indicates channel partner. Edit SOQL to match your org.",
    "S6-COL-AK": "Marketing Opps: BLOCKED — Source__c / LeadSource field values pending confirmation.",
    "S6-COL-AL": "Marketing Pipeline $: BLOCKED — Source__c / LeadSource field values pending confirmation.",
    "S5-COL-AB": "Mtgs from Events: BLOCKED — Source__c field values pending confirmation.",
    "S5-COL-AC": "Mtgs from Inbound: BLOCKED — Source__c field values pending confirmation.",
    "S5-COL-AD": "Mtgs from Other Marketing: BLOCKED — Source__c field values pending confirmation.",
}


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


def _light_heatmap(col, reverse=False):
    """Light heatmap colors: pink (worst) to green (best)."""
    numeric = pd.to_numeric(col, errors="coerce")
    if numeric.isna().all():
        return [""] * len(col)
    vmin, vmax = numeric.min(), numeric.max()
    if pd.isna(vmin) or pd.isna(vmax) or vmin == vmax:
        return [""] * len(col)
    norm = (numeric - vmin) / (vmax - vmin)
    if reverse:
        norm = 1 - norm
    result = []
    for v in norm:
        if pd.isna(v):
            result.append("")
        else:
            r = int(255 - v * 35)
            g = int(230 + v * 25)
            b = int(230 - v * 10)
            result.append(f"background-color: rgb({r}, {g}, {b})")
    return result


def display_kpi_widgets(df: pd.DataFrame):
    """Top-of-page KPI widgets showing aggregate totals. [spec: B.1]"""
    if df.empty:
        return
    st.markdown("### Key Performance Indicators")

    # Row 1 — Quota & Attainment
    row1 = st.columns(6)
    kpi_row1 = [
        ("Quota YTD", "S1-COL-C", fmt_currency, False),
        ("Bookings YTD", "S1-COL-D", fmt_currency, False),
        ("YTD Attainment (avg)", "S1-COL-E", fmt_percent, True),
        ("Quota This Mo", "S1-COL-F", fmt_currency, False),
        ("Bookings This Mo", "S1-COL-G", fmt_currency, False),
        ("MTD Attainment (avg)", "S1-COL-H", fmt_percent, True),
    ]
    for i, (label, col_id, formatter, is_avg) in enumerate(kpi_row1):
        if col_id in df.columns:
            numeric = pd.to_numeric(df[col_id], errors="coerce")
            val = numeric.mean() if is_avg else numeric.sum()
            row1[i].metric(label, formatter(val))

    # Row 2 — Pipeline & Outcomes
    row2 = st.columns(6)
    kpi_row2 = [
        ("Opps Created", "S1-COL-K", fmt_number, False),
        ("Pipeline $ Created", "S1-COL-L", fmt_currency, False),
        ("Open Pipeline (This Mo)", "S1-COL-I", fmt_currency, False),
        ("Open Pipeline (Next Mo)", "S1-COL-J", fmt_currency, False),
        ("Closed Won (Period)", "S1-COL-M", fmt_currency, False),
        ("Closed Lost (Period)", "S1-COL-N", fmt_currency, False),
    ]
    for i, (label, col_id, formatter, is_avg) in enumerate(kpi_row2):
        if col_id in df.columns:
            numeric = pd.to_numeric(df[col_id], errors="coerce")
            val = numeric.mean() if is_avg else numeric.sum()
            row2[i].metric(label, formatter(val))


def display_dashboard_table(df: pd.DataFrame):
    """
    Main data table with section grouping, heatmap styling, pagination.
    [spec: B.1, B.2, B.6]
    """
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    # Pagination in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Pagination")
    page_size = st.sidebar.selectbox(
        "Rows per page", [10, 25, 50, 100], index=1, key="page_size"
    )
    total = len(df)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.sidebar.number_input(
        "Page", min_value=1, max_value=total_pages, value=1, key="page_num"
    )
    start_idx = (page - 1) * page_size
    page_df = df.iloc[start_idx : start_idx + page_size]

    for section in SECTIONS:
        section_cols = [e for e in ALL_COLUMNS if e.section == section]
        display_name = SECTION_DISPLAY_NAMES.get(section, section)

        # Build section DataFrame with numeric values and display-name columns
        section_data = pd.DataFrame()
        section_data["AE Name"] = page_df["AE Name"].values
        if "AE Manager" in page_df.columns:
            section_data["AE Manager"] = page_df["AE Manager"].values

        format_dict = {}
        heatmap_cols = []

        for entry in section_cols:
            name = entry.display_name
            if entry.col_id not in page_df.columns:
                section_data[name] = None
            elif entry.blocked:
                section_data[name] = "Pending"
            else:
                section_data[name] = pd.to_numeric(
                    page_df[entry.col_id].values, errors="coerce"
                )
                if entry.col_id in CURRENCY_COLS:
                    format_dict[name] = fmt_currency
                elif entry.col_id in PERCENT_COLS:
                    format_dict[name] = fmt_percent
                else:
                    format_dict[name] = fmt_number
                heatmap_cols.append((name, entry.col_id in LOWER_IS_BETTER))

        with st.expander(f"**{display_name}**", expanded=True):
            tooltip_lines = []
            for e in section_cols:
                tip = TOOLTIPS.get(e.col_id, "")
                if tip:
                    tooltip_lines.append(f"- **{e.display_name}:** {tip}")
            if tooltip_lines:
                if st.checkbox(
                    "Show Column Descriptions",
                    key=f"tooltips_{section}",
                    value=False,
                ):
                    st.markdown("\n".join(tooltip_lines))

            styler = section_data.style
            if format_dict:
                styler = styler.format(format_dict, na_rep="—")
            for col_name, reverse in heatmap_cols:
                if col_name in section_data.columns:
                    styler = styler.apply(
                        _light_heatmap, reverse=reverse, subset=[col_name]
                    )

            st.dataframe(styler, use_container_width=True, hide_index=True)

    st.caption(
        f"Showing {start_idx + 1}–{min(start_idx + page_size, total)} of {total} AEs"
    )


def display_charts(df: pd.DataFrame):
    """Bar charts for critical comparison. [spec: B.1]"""
    if df.empty:
        return
    with st.expander("Charts", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if "S1-COL-D" in df.columns and "AE Name" in df.columns:
                chart_df = df[["AE Name", "S1-COL-D"]].copy()
                chart_df["S1-COL-D"] = pd.to_numeric(chart_df["S1-COL-D"], errors="coerce")
                chart_df = chart_df.dropna().rename(columns={"S1-COL-D": "Bookings YTD"})
                fig = px.bar(
                    chart_df, x="AE Name", y="Bookings YTD",
                    title="Bookings YTD by AE", labels={"Bookings YTD": "$"}
                )
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            if "S1-COL-E" in df.columns and "AE Name" in df.columns:
                chart_df = df[["AE Name", "S1-COL-E"]].copy()
                chart_df["S1-COL-E"] = pd.to_numeric(chart_df["S1-COL-E"], errors="coerce")
                chart_df = chart_df.dropna().rename(columns={"S1-COL-E": "YTD Attainment %"})
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
        if not numeric_cols:
            return
        heat_df = df[["AE Name"] + numeric_cols].copy()
        heat_df = heat_df.set_index("AE Name")
        for c in numeric_cols:
            heat_df[c] = pd.to_numeric(heat_df[c], errors="coerce")
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


def render_fetch_status(timestamp: str | None) -> bool:
    """Display fetch timestamp and return True if Refresh was clicked. [spec: B.3]"""
    col1, col2 = st.columns([3, 1])
    with col1:
        if timestamp:
            st.caption(f"Data last fetched: {timestamp}")
        else:
            st.caption("Data not yet fetched.")
    with col2:
        return st.button("Refresh Data", use_container_width=True)
