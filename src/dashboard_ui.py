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


def display_kpi_widgets(df: pd.DataFrame):
    """Top-of-page KPI widgets showing aggregate totals. [spec: B.1]"""
    if df.empty:
        return
    st.markdown("### Key Performance Indicators")
    cols = st.columns(5)
    kpis = [
        ("Bookings YTD", "S1-COL-D", fmt_currency, False),
        ("Quota YTD", "S1-COL-C", fmt_currency, False),
        ("MTD Attainment (avg)", "S1-COL-H", fmt_percent, True),
        ("Open Pipeline (This Mo)", "S1-COL-I", fmt_currency, False),
        ("Closed Won (Period)", "S1-COL-M", fmt_currency, False),
    ]
    for i, (label, col_id, formatter, is_avg) in enumerate(kpis):
        if col_id in df.columns:
            numeric = pd.to_numeric(df[col_id], errors="coerce")
            val = numeric.mean() if is_avg else numeric.sum()
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
    Main data table with section grouping, search, sort, pagination, tooltips.
    [spec: B.1, B.2, B.6]
    """
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    search = st.text_input("Search AEs", placeholder="Type to filter...", key="table_search")
    filtered = df
    if search:
        mask = df["AE Name"].str.contains(search, case=False, na=False)
        filtered = df[mask]

    page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=0, key="page_size")
    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="page_num")
    start_idx = (page - 1) * page_size
    page_df = filtered.iloc[start_idx: start_idx + page_size]

    display = build_display_df(page_df)

    for section in SECTIONS:
        section_cols = [e for e in ALL_COLUMNS if e.section == section]
        display_name = SECTION_DISPLAY_NAMES.get(section, section)
        col_names = ["AE Name"] + [e.display_name for e in section_cols]
        section_df = display[[c for c in col_names if c in display.columns]]

        with st.expander(f"**{display_name}**", expanded=True):
            # Tooltips legend [spec: B.6]
            tooltip_lines = []
            for e in section_cols:
                tip = TOOLTIPS.get(e.col_id, "")
                if tip:
                    tooltip_lines.append(f"- **{e.display_name}:** {tip}")
            if tooltip_lines:
                with st.expander("Column Descriptions", expanded=False):
                    st.markdown("\n".join(tooltip_lines))

            st.dataframe(
                section_df,
                use_container_width=True,
                hide_index=True,
            )

    st.caption(f"Showing {start_idx + 1}–{min(start_idx + page_size, total)} of {total} AEs")


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
