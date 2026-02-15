"""
Dashboard UI Components
Formatting, styling, and display utilities.
"""
import streamlit as st
import pandas as pd


# ==============================================================================
# CSS STYLES
# ==============================================================================

def apply_custom_css():
    """Apply custom CSS for the dashboard."""
    st.markdown("""
        <style>
        .main { padding: 0rem 1rem; }
        h1 { color: #1f77b4; padding-bottom: 1rem; }
        .oauth-login-box {
            max-width: 420px; margin: 4rem auto; padding: 2.5rem;
            background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;
            text-align: center; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        .oauth-login-box h2 { color: #1e293b; margin-bottom: 0.5rem; }
        .oauth-login-box p { color: #64748b; margin-bottom: 1.5rem; font-size: 0.95rem; }
        .oauth-btn {
            display: inline-block; padding: 12px 24px; background: #00a1e0;
            color: white !important; text-decoration: none; border-radius: 8px;
            font-weight: 600; font-size: 1rem;
        }
        .oauth-btn:hover { background: #0086b8; }

        /* Dashboard table */
        .ae-table-wrap { overflow: auto; margin: 1rem 0; max-height: 500px; }
        .ae-table {
            border-collapse: collapse; width: 100%;
            font-size: 0.82rem; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .ae-table th, .ae-table td {
            padding: 7px 10px; text-align: right; white-space: nowrap;
            border-bottom: 1px solid #e5e7eb;
        }
        .ae-table td:first-child, .ae-table th:first-child { text-align: left; }
        .ae-table .super-header th {
            position: sticky; top: 0; z-index: 2;
            text-align: center; font-weight: 700; font-size: 0.78rem;
            text-transform: uppercase; letter-spacing: 0.04em;
            color: #fff; padding: 6px 10px; border: none;
            box-shadow: 0 2px 2px -1px rgba(0,0,0,0.1);
        }
        .ae-table .sub-header th {
            position: sticky; top: 32px; z-index: 2;
            background: #f8fafc; font-weight: 600; color: #475569;
            font-size: 0.75rem; border-bottom: 2px solid #cbd5e1;
            box-shadow: 0 2px 2px -1px rgba(0,0,0,0.06);
        }
        .ae-table .ae-name { font-weight: 600; color: #1e293b; }
        .ae-table tbody tr:nth-child(even) { background: #f9fafb; }
        .ae-table tbody tr:hover { background: #eff6ff; }
        .ae-table .ae-name { font-weight: 600; color: #1e293b; }
        .ae-table .negative { color: #dc2626; font-weight: 600; }
        .ae-table .positive { color: #16a34a; font-weight: 600; }

        .grp-ae    { background: #334155; }
        .grp-quota { background: #1d4ed8; }
        .grp-pipe  { background: #7c3aed; }
        .grp-act   { background: #0891b2; }
        .grp-meet  { background: #059669; }
        </style>
        """, unsafe_allow_html=True)


# ==============================================================================
# COLUMN DEFINITIONS
# ==============================================================================

COLUMN_ORDER = [
    'AE Name',
    'Manager Name',
    'Forecast Amount', 'Quota Amount', 'Percent to Quota (%)',
    'Closed Won', 'Remainder', 'Pipeline Coverage Ratio',
    'Pipeline You Should Have', 'Open Pipeline with CW Date in Month', 'Pipeline Gap',
    'Activity Email', 'Activity Phone', 'Activity Total',
    'Meetings Needed', 'Meetings Scheduled', 'Meeting Gap',
]


def prepare_display_df(df):
    """
    Prepare the dataframe for st.dataframe display.
    - Replaces -99 ratio with None
    - Reorders columns to the canonical order
    """
    if df.empty:
        return df
    out = df.copy()
    if 'Pipeline Coverage Ratio' in out.columns:
        import numpy as np
        out['Pipeline Coverage Ratio'] = out['Pipeline Coverage Ratio'].replace(-99, np.nan)
    ordered = [c for c in COLUMN_ORDER if c in out.columns]
    extra = [c for c in out.columns if c not in ordered]
    return out[ordered + extra]


def style_negative_gaps(df):
    """
    Apply styling to highlight negative gaps in red AND format all columns.
    Returns a pandas Styler object with both formatting and conditional styling.
    """
    def highlight_negative(val):
        """Return red color for negative values."""
        try:
            if pd.isna(val):
                return ''
            if float(val) < 0:
                return 'color: #dc2626; font-weight: 600;'
            return ''
        except (ValueError, TypeError):
            return ''
    
    # Start with styling
    styled = df.style
    
    # Apply red highlighting to gap columns (use map for newer pandas, applymap for older)
    try:
        if 'Pipeline Gap' in df.columns:
            styled = styled.map(highlight_negative, subset=['Pipeline Gap'])
        if 'Meeting Gap' in df.columns:
            styled = styled.map(highlight_negative, subset=['Meeting Gap'])
    except AttributeError:
        # Fallback to applymap for older pandas versions
        if 'Pipeline Gap' in df.columns:
            styled = styled.applymap(highlight_negative, subset=['Pipeline Gap'])
        if 'Meeting Gap' in df.columns:
            styled = styled.applymap(highlight_negative, subset=['Meeting Gap'])
    
    # Apply formatting to all columns
    format_dict = {}
    
    # Dollar columns
    dollar_cols = [
        'Forecast Amount', 'Quota Amount', 'Closed Won', 'Remainder',
        'Pipeline You Should Have', 'Open Pipeline with CW Date in Month', 'Pipeline Gap'
    ]
    for col in dollar_cols:
        if col in df.columns:
            format_dict[col] = '${:,.0f}'
    
    # Percentage columns
    if 'Percent to Quota (%)' in df.columns:
        format_dict['Percent to Quota (%)'] = '{:.1f}%'
    
    # Ratio columns
    if 'Pipeline Coverage Ratio' in df.columns:
        format_dict['Pipeline Coverage Ratio'] = '{:.1f}x'
    
    # Integer columns
    int_cols = [
        'Activity Email', 'Activity Phone', 'Activity Total',
        'Meetings Needed', 'Meetings Scheduled', 'Meeting Gap'
    ]
    for col in int_cols:
        if col in df.columns:
            format_dict[col] = '{:.0f}'
    
    # Apply all formatting
    styled = styled.format(format_dict, na_rep='-')
    
    return styled


def get_column_config(df):
    """
    Build a column_config dict for st.dataframe.
    Provides column labels (formatting is handled by Styler for proper red highlighting).
    """
    config = {}

    config['AE Name'] = st.column_config.TextColumn('AE Name', width='medium')
    config['Manager Name'] = st.column_config.TextColumn('Manager', width='medium')

    # Dollar columns - use Column (not NumberColumn) to avoid format conflicts with Styler
    dollar_cols = {
        'Forecast Amount': 'Forecast',
        'Quota Amount': 'Quota Amt',
        'Closed Won': 'Closed Won',
        'Remainder': 'Remainder',
        'Pipeline You Should Have': 'Should Have',
        'Open Pipeline with CW Date in Month': 'Open Pipeline',
    }
    for col, label in dollar_cols.items():
        if col in df.columns:
            config[col] = st.column_config.Column(label)
    
    # Pipeline Gap with help text
    if 'Pipeline Gap' in df.columns:
        config['Pipeline Gap'] = st.column_config.Column('Pipeline Gap', help="Negative = shortfall")

    if 'Percent to Quota (%)' in df.columns:
        config['Percent to Quota (%)'] = st.column_config.Column('% to Quota')

    if 'Pipeline Coverage Ratio' in df.columns:
        config['Pipeline Coverage Ratio'] = st.column_config.Column('Ratio (6mo avg)')

    int_cols = {
        'Activity Email': 'Email',
        'Activity Phone': 'Phone',
        'Activity Total': 'Total',
        'Meetings Needed': 'Needed',
        'Meetings Scheduled': 'Scheduled',
    }
    for col, label in int_cols.items():
        if col in df.columns:
            config[col] = st.column_config.Column(label)
    
    # Meeting Gap with help text
    if 'Meeting Gap' in df.columns:
        config['Meeting Gap'] = st.column_config.Column('Meeting Gap', help="Negative = shortfall")

    return config


# ==============================================================================
# SUMMARY METRICS
# ==============================================================================

def display_summary_metrics(df):
    """
    Display top-level summary metrics.
    
    Percent to Quota = ForecastingItem.ForecastAmount:SUM / ForecastingQuota.QuotaAmount:SUM
    """
    if df.empty or len(df.columns) == 0:
        st.info("No opportunity owners found for the selected period.")
        return

    def _safe_sum(col):
        return df[col].sum() if col in df.columns else 0

    total_quota = _safe_sum('Quota Amount')
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Quota", f"${total_quota:,.0f}")
    
    with col2:
        total_forecast = _safe_sum('Forecast Amount')
        percent_to_quota = (total_forecast / total_quota * 100) if total_quota > 0 else 0
        st.metric("Total Forecast", f"${total_forecast:,.0f}",
                 f"{percent_to_quota:.1f}% to quota")

    with col3:
        total_closed = _safe_sum('Closed Won')
        st.metric("Total Closed Won", f"${total_closed:,.0f}")

    with col4:
        total_pipeline = _safe_sum('Open Pipeline with CW Date in Month')
        st.metric("Total Pipeline", f"${total_pipeline:,.0f}")

    with col5:
        total_gap = _safe_sum('Pipeline Gap')
        gap_color = "inverse" if total_gap > 0 else "normal"
        st.metric("Total Pipeline Gap", f"${total_gap:,.0f}",
                 delta_color=gap_color)


# ==============================================================================
# INSIGHTS SECTION
# ==============================================================================

def display_insights(df):
    """
    Display additional insights (top performers, gaps, etc.).
    
    Customize:
    - Add more insight panels
    - Change ranking logic
    - Add charts/visualizations
    """
    with st.expander("📈 View Additional Insights"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Performers (Percent to Quota)")
            top_col = 'Percent to Quota (%)' if 'Percent to Quota (%)' in df.columns else 'Attainment %'
            top_performers = df.copy()
            if top_col not in top_performers.columns:
                top_performers['Attainment %'] = 0.0
                top_col = 'Attainment %'
            display_cols = ['AE Name', 'Forecast Amount', top_col] if 'Forecast Amount' in df.columns else ['AE Name', 'Closed Won', top_col]
            display_cols = [c for c in display_cols if c in top_performers.columns]
            top_performers = top_performers.nlargest(5, top_col)[display_cols]
            st.dataframe(top_performers, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Largest Pipeline Gaps")
            gaps = df.nlargest(5, 'Pipeline Gap')[
                ['AE Name', 'Pipeline Gap', 'Meetings Needed']
            ]
            st.dataframe(gaps, use_container_width=True, hide_index=True)


# ==============================================================================
# CUSTOMIZATION NOTES
# ==============================================================================

"""
UI Customization Ideas:

1. ADD CHARTS:
   import plotly.express as px
   fig = px.bar(df, x='AE Name', y='Closed Won', title='Closed Won by AE')
   st.plotly_chart(fig)

2. CHANGE COLORS:
   Line 13-25: Update hex colors for branding
   
3. ADD MORE METRICS:
   In display_summary_metrics(), add a 5th column:
   with col5:
       avg_attainment = df['Closed Won'].sum() / df['Monthly Quota'].sum()
       st.metric("Avg Attainment", f"{avg_attainment:.1%}")

4. CONDITIONAL FORMATTING:
   def highlight_high_attainment(val):
       if val > 100: return 'background-color: #ccffcc'
       if val < 50: return 'background-color: #ffcccc'
       return ''
"""
