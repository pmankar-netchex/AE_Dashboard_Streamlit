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
        ("S1-COL-C", fmt_currency, False),
        ("S1-COL-D", fmt_currency, False),
        ("S1-COL-E", fmt_percent, True),
        ("S1-COL-F", fmt_currency, False),
        ("S1-COL-G", fmt_currency, False),
        ("S1-COL-H", fmt_percent, True),
    ]
    for i, (col_id, formatter, is_avg) in enumerate(kpi_row1):
        if col_id in df.columns:
            numeric = pd.to_numeric(df[col_id], errors="coerce")
            val = numeric.mean() if is_avg else numeric.sum()
            row1[i].metric(COLUMN_BY_ID[col_id].display_name, formatter(val))

    # Row 2 — Pipeline & Outcomes
    row2 = st.columns(6)
    kpi_row2 = [
        ("S1-COL-K", fmt_number, False),
        ("S1-COL-L", fmt_currency, False),
        ("S1-COL-I", fmt_currency, False),
        ("S1-COL-J", fmt_currency, False),
        ("S1-COL-M", fmt_currency, False),
        ("S1-COL-N", fmt_currency, False),
    ]
    for i, (col_id, formatter, is_avg) in enumerate(kpi_row2):
        if col_id in df.columns:
            numeric = pd.to_numeric(df[col_id], errors="coerce")
            val = numeric.mean() if is_avg else numeric.sum()
            row2[i].metric(COLUMN_BY_ID[col_id].display_name, formatter(val))


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
                if e.blocked:
                    tip = "Pending — field mapping not yet confirmed for this org."
                else:
                    tip = e.description
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
