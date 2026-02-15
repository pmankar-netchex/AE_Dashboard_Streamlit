import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import pandas as pd
from simple_salesforce import Salesforce
from datetime import datetime, date
import calendar

# Import modules
from src.salesforce_oauth import (
    is_oauth_configured,
    get_authorization_url,
    exchange_code_for_tokens,
    refresh_access_token,
    create_salesforce_client,
)
from src.token_storage import (
    save_tokens,
    load_tokens,
    clear_tokens,
)
from src.salesforce_queries import (
    get_ae_by_ids,
    get_all_opportunities,
    get_all_meetings,
    get_activity_by_type,
    get_forecast_amounts,
    get_quota_amounts,
    get_historic_pipeline_ratios,
)
from src.dashboard_calculations import (
    get_month_date_range,
    build_dashboard_data,
)
from src.dashboard_ui import (
    apply_custom_css,
    prepare_display_df,
    get_column_config,
    style_negative_gaps,
    display_summary_metrics,
    display_insights,
)

# Page configuration
st.set_page_config(
    page_title="AE Ultimate Dashboard",
    page_icon="📊",
    layout="wide"
)

apply_custom_css()


# ==============================================================================
# AUTH HELPERS
# ==============================================================================

def get_salesforce_connection():
    """
    Connect to Salesforce with priority:
    1. Session state (current session)
    2. Saved tokens (persistent across sessions)
    3. Username/password (fallback)
    """
    # 1. Try session state first (already authenticated this session)
    if "sf_oauth" in st.session_state:
        oauth = st.session_state["sf_oauth"]
        try:
            return create_salesforce_client(oauth["instance_url"], oauth["access_token"])
        except Exception as e:
            # Access token expired, try refresh
            if oauth.get("refresh_token"):
                try:
                    tokens = refresh_access_token(oauth["refresh_token"])
                    st.session_state["sf_oauth"]["access_token"] = tokens["access_token"]
                    st.session_state["sf_oauth"]["instance_url"] = tokens.get("instance_url", oauth["instance_url"])
                    save_tokens(tokens["access_token"], oauth["refresh_token"], st.session_state["sf_oauth"]["instance_url"])
                    return create_salesforce_client(st.session_state["sf_oauth"]["instance_url"], tokens["access_token"])
                except Exception:
                    # Refresh failed, clear session
                    del st.session_state["sf_oauth"]
            else:
                del st.session_state["sf_oauth"]

    # 2. Try loading saved tokens (persistent storage)
    if is_oauth_configured():
        saved = load_tokens()
        if saved:
            try:
                # Try using saved access token
                sf = create_salesforce_client(saved["instance_url"], saved["access_token"])
                # Test the connection with a simple query
                sf.query("SELECT Id FROM User LIMIT 1")
                # Success! Store in session
                st.session_state["sf_oauth"] = saved
                return sf
            except Exception:
                # Access token expired, try refresh token
                if saved.get("refresh_token"):
                    try:
                        tokens = refresh_access_token(saved["refresh_token"])
                        new_oauth = {
                            "access_token": tokens["access_token"],
                            "refresh_token": saved["refresh_token"],
                            "instance_url": tokens.get("instance_url", saved["instance_url"]),
                        }
                        save_tokens(new_oauth["access_token"], new_oauth["refresh_token"], new_oauth["instance_url"])
                        st.session_state["sf_oauth"] = new_oauth
                        return create_salesforce_client(new_oauth["instance_url"], new_oauth["access_token"])
                    except Exception:
                        # Refresh failed, clear saved tokens
                        clear_tokens()

    # 3. Fallback to username/password if configured
    username = os.environ.get("SALESFORCE_USERNAME")
    password = os.environ.get("SALESFORCE_PASSWORD")
    security_token = os.environ.get("SALESFORCE_SECURITY_TOKEN")
    if all([username, password, security_token]):
        try:
            return Salesforce(username=username, password=password, security_token=security_token)
        except Exception as e:
            st.error(f"Failed to connect: {str(e)}")
            return None
    
    return None


def render_oauth_login_screen():
    st.markdown(f"""
        <div class="oauth-login-box">
            <h2>📊 AE Ultimate Dashboard</h2>
            <p>Connect your Salesforce account to view the dashboard</p>
            <a href="{get_authorization_url()}" class="oauth-btn">Connect with Salesforce</a>
        </div>
    """, unsafe_allow_html=True)
    with st.expander("ℹ️ Setup required"):
        st.markdown("Add SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, SALESFORCE_REDIRECT_URI to `.env`. Create a Connected App in Salesforce.")


def handle_oauth_callback():
    """Exchange OAuth code for tokens and save them for future use."""
    code = st.query_params.get("code")
    if not code:
        return False
    code = code[0] if isinstance(code, list) else code

    if "last_oauth_code" in st.session_state and st.session_state["last_oauth_code"] == code:
        st.query_params.clear()
        return "sf_oauth" in st.session_state

    try:
        tokens = exchange_code_for_tokens(code)
        oauth_data = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "instance_url": tokens["instance_url"],
        }
        
        # Save to session state
        st.session_state["sf_oauth"] = oauth_data
        st.session_state["last_oauth_code"] = code
        
        # Save to persistent storage (so you don't have to re-authenticate next time)
        if oauth_data.get("refresh_token"):
            save_tokens(oauth_data["access_token"], oauth_data["refresh_token"], oauth_data["instance_url"])
        
        st.query_params.clear()
        return True
    except Exception as e:
        err_str = str(e).lower()
        if "expired" in err_str or "invalid_grant" in err_str:
            st.query_params.clear()
            return False
        st.error(f"Login failed: {str(e)}")
        st.query_params.clear()
        return False


# ==============================================================================
# DATA LOADER
# ==============================================================================

def load_dashboard_data(sf, month, year):
    """Fetch all data from Salesforce and build dashboard dataframe."""
    start_date, end_date = get_month_date_range(year, month)

    with st.spinner("Fetching opportunity data..."):
        closed_won_dict, pipeline_dict = get_all_opportunities(sf, start_date, end_date)

    # Get AE records only for opportunity owners
    opportunity_owner_ids = list(set(closed_won_dict.keys()) | set(pipeline_dict.keys()))
    ae_df = get_ae_by_ids(sf, opportunity_owner_ids)
    ae_ids = ae_df['Id'].tolist() if not ae_df.empty else []

    if ae_ids:
        with st.spinner("Fetching meeting data..."):
            meetings_dict = get_all_meetings(sf, ae_ids, start_date, end_date)

        with st.spinner("Fetching activity data..."):
            activity_email_dict, activity_phone_dict = get_activity_by_type(sf, ae_ids, start_date, end_date)

        with st.spinner("Fetching forecast & quota data..."):
            forecast_dict = get_forecast_amounts(sf, ae_ids, start_date, end_date)
            quota_dict = get_quota_amounts(sf, ae_ids, start_date, end_date)

        with st.spinner("Computing historic pipeline ratios (last 6 months)..."):
            pipeline_ratio_dict = get_historic_pipeline_ratios(sf, ae_ids, year, month)
    else:
        meetings_dict = {}
        activity_email_dict = {}
        activity_phone_dict = {}
        forecast_dict = {}
        quota_dict = {}
        pipeline_ratio_dict = {}

    return build_dashboard_data(sf, ae_df, closed_won_dict, pipeline_dict, meetings_dict,
                                activity_email_dict, activity_phone_dict, forecast_dict, quota_dict,
                                pipeline_ratio_dict, 5000, 0.20)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    # --- OAuth callback (user returning from Salesforce login) ---
    if st.query_params.get("code"):
        if handle_oauth_callback():
            st.rerun()
        return

    # --- Connect to Salesforce ---
    sf = get_salesforce_connection()
    if sf is None and is_oauth_configured():
        st.title("📊 AE Ultimate Dashboard")
        render_oauth_login_screen()
        return
    if sf is None:
        st.title("📊 AE Ultimate Dashboard")
        st.error("❌ Unable to connect to Salesforce")
        st.info("💡 Use OAuth or set SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN")
        return

    # --- Title ---
    st.title("📊 AE Ultimate Dashboard")
    st.success("✅ Connected to Salesforce")

    # --- Month and Year selector ---
    now = datetime.now()
    
    def _parse_int(val, default):
        if val is None:
            return default
        v = val[0] if isinstance(val, list) else val
        try:
            return int(v)
        except (ValueError, TypeError):
            return default

    # Initialize filters from query params on first load
    if "dashboard_filters" not in st.session_state:
        p_m = _parse_int(st.query_params.get("month"), now.month)
        p_y = _parse_int(st.query_params.get("year"), now.year)
        p_m = max(1, min(12, p_m))
        st.session_state["dashboard_filters"] = {"month": p_m, "year": p_y}

    # --- Month and Year pickers ---
    col1, col2 = st.columns(2)
    
    # Generate year options (current year and 2 years back)
    year_options = list(range(now.year, now.year - 3, -1))
    
    # Month names for dropdown
    month_options = {i: calendar.month_name[i] for i in range(1, 13)}
    
    with col1:
        selected_month = st.selectbox(
            "Month",
            options=list(month_options.keys()),
            format_func=lambda x: month_options[x],
            index=list(month_options.keys()).index(st.session_state["dashboard_filters"]["month"]),
            key="filter_month"
        )
    
    with col2:
        selected_year = st.selectbox(
            "Year",
            options=year_options,
            index=year_options.index(st.session_state["dashboard_filters"]["year"]) if st.session_state["dashboard_filters"]["year"] in year_options else 0,
            key="filter_year"
        )
    
    p_month, p_year = selected_month, selected_year
    st.session_state["dashboard_filters"] = {"month": p_month, "year": p_year}
    st.query_params["month"] = str(p_month)
    st.query_params["year"] = str(p_year)

    # --- Debug (only when DEBUG=1 in .env or ?debug=1 in URL) ---
    debug_mode = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes") or str(st.query_params.get("debug", "")).lower() in ("1", "true", "yes")
    if debug_mode:
        with st.expander("🔧 Filter debug", expanded=False):
            st.write("**Values used for query**: ", f"month={p_month}, year={p_year}")

    # Disconnect button
    if "sf_oauth" in st.session_state:
        if st.button("🚪 Disconnect"):
            del st.session_state["sf_oauth"]
            clear_tokens()  # Also clear saved tokens
            st.rerun()

    # --- Show what we're querying ---
    start_date, end_date = get_month_date_range(p_year, p_month)
    st.markdown(f"### {calendar.month_name[p_month]} {p_year}")
    st.caption(f"📅 Querying: {start_date} to {end_date}")
    st.markdown("---")

    # --- Load data ---
    try:
        t0 = datetime.now()
        df = load_dashboard_data(sf, p_month, p_year)
    except Exception as e:
        err = str(e).lower()
        if "sf_oauth" in st.session_state and any(k in err for k in ["session", "token", "401", "expired"]):
            # Token expired during query - clear and ask to reconnect
            st.error("Session expired. Please reconnect.")
            del st.session_state["sf_oauth"]
            clear_tokens()
            st.stop()
        else:
            raise

    load_time = (datetime.now() - t0).total_seconds()
    st.caption(f"⏱️ Loaded in {load_time:.2f}s")

    # --- Display ---
    if df.empty or len(df.columns) == 0:
        st.info("No opportunity owners found for the selected period.")
    else:
        # --- Amazon-Style Filter Pane (Sidebar) ---
        with st.sidebar:
            st.markdown("### 🔍 Filters")
            
            # Reset all filters button at top
            if st.button("🔄 Clear All Filters", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key.startswith('filter_'):
                        del st.session_state[key]
                st.rerun()
            
            st.markdown("---")
            
            # Initialize filter values
            selected_managers = []
            selected_aes = []
            quota_range = None
            closed_won_range = None
            pipeline_range = None
            meetings_range = None
            
            # === CATEGORICAL FILTERS ===
            
            # Manager filter (expandable)
            with st.expander("**Manager**", expanded=True):
                all_managers = sorted(df['Manager Name'].dropna().unique().tolist()) if 'Manager Name' in df.columns else []
                
                if all_managers:
                    # Quick actions
                    col1, col2 = st.columns(2)
                    with col1:
                        select_all_mgr = st.button("All", key="btn_all_mgr", use_container_width=True)
                    with col2:
                        clear_mgr = st.button("None", key="btn_none_mgr", use_container_width=True)
                    
                    # Determine default selection
                    if select_all_mgr:
                        st.session_state['filter_managers'] = all_managers
                    elif clear_mgr:
                        st.session_state['filter_managers'] = []
                    
                    default_mgr = st.session_state.get('filter_managers', all_managers)
                    
                    selected_managers = st.multiselect(
                        "Select managers",
                        options=all_managers,
                        default=default_mgr,
                        key="manager_filter",
                        label_visibility="collapsed",
                        placeholder="Choose managers..."
                    )
                    
                    st.session_state['filter_managers'] = selected_managers
                    
                    # Show selection count
                    if len(selected_managers) < len(all_managers):
                        st.caption(f"✓ {len(selected_managers)} of {len(all_managers)} selected")
            
            # AE Name filter (expandable)
            with st.expander("**AE Name**", expanded=False):
                all_aes = sorted(df['AE Name'].dropna().unique().tolist()) if 'AE Name' in df.columns else []
                
                if all_aes:
                    # Quick actions
                    col1, col2 = st.columns(2)
                    with col1:
                        select_all_ae = st.button("All", key="btn_all_ae", use_container_width=True)
                    with col2:
                        clear_ae = st.button("None", key="btn_none_ae", use_container_width=True)
                    
                    # Determine default selection
                    if select_all_ae:
                        st.session_state['filter_aes'] = all_aes
                    elif clear_ae:
                        st.session_state['filter_aes'] = []
                    
                    default_ae = st.session_state.get('filter_aes', all_aes)
                    
                    selected_aes = st.multiselect(
                        "Select AEs",
                        options=all_aes,
                        default=default_ae,
                        key="ae_filter",
                        label_visibility="collapsed",
                        placeholder="Choose AEs..."
                    )
                    
                    st.session_state['filter_aes'] = selected_aes
                    
                    # Show selection count
                    if len(selected_aes) < len(all_aes):
                        st.caption(f"✓ {len(selected_aes)} of {len(all_aes)} selected")
            
            # === NUMERIC FILTERS ===
            
            # % to Quota filter (expandable)
            if '% to Quota' in df.columns and df['% to Quota'].notna().any():
                with st.expander("**% to Quota**", expanded=False):
                    quota_min = float(df['% to Quota'].min())
                    quota_max = float(df['% to Quota'].max())
                    
                    # Radio for filter type
                    quota_filter_type = st.radio(
                        "Filter type",
                        ["Range", "Minimum", "Maximum"],
                        key="quota_filter_type",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    
                    if quota_filter_type == "Range":
                        quota_range = st.slider(
                            "Select range",
                            min_value=0.0,
                            max_value=max(200.0, quota_max),
                            value=(0.0, max(200.0, quota_max)),
                            step=5.0,
                            format="%.0f%%",
                            label_visibility="collapsed"
                        )
                    elif quota_filter_type == "Minimum":
                        min_val = st.number_input(
                            "Minimum %",
                            min_value=0.0,
                            max_value=max(200.0, quota_max),
                            value=0.0,
                            step=5.0,
                            label_visibility="collapsed"
                        )
                        quota_range = (min_val, max(200.0, quota_max))
                    else:  # Maximum
                        max_val = st.number_input(
                            "Maximum %",
                            min_value=0.0,
                            max_value=max(200.0, quota_max),
                            value=max(200.0, quota_max),
                            step=5.0,
                            label_visibility="collapsed"
                        )
                        quota_range = (0.0, max_val)
                    
                    # Check if filter is active
                    if quota_range != (0.0, max(200.0, quota_max)):
                        st.caption(f"✓ {quota_range[0]:.0f}% - {quota_range[1]:.0f}%")
            
            # Closed Won filter (expandable)
            if 'Closed Won' in df.columns and df['Closed Won'].notna().any():
                with st.expander("**Closed Won**", expanded=False):
                    cw_min = float(df['Closed Won'].min())
                    cw_max = float(df['Closed Won'].max())
                    
                    closed_won_filter_type = st.radio(
                        "Filter type",
                        ["Range", "Minimum", "Maximum"],
                        key="cw_filter_type",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    
                    if closed_won_filter_type == "Range":
                        closed_won_range = st.slider(
                            "Select range",
                            min_value=0.0,
                            max_value=cw_max,
                            value=(0.0, cw_max),
                            step=max(10000.0, cw_max / 100),
                            format="$%.0f",
                            label_visibility="collapsed"
                        )
                    elif closed_won_filter_type == "Minimum":
                        min_val = st.number_input(
                            "Minimum $",
                            min_value=0.0,
                            max_value=cw_max,
                            value=0.0,
                            step=10000.0,
                            label_visibility="collapsed"
                        )
                        closed_won_range = (min_val, cw_max)
                    else:  # Maximum
                        max_val = st.number_input(
                            "Maximum $",
                            min_value=0.0,
                            max_value=cw_max,
                            value=cw_max,
                            step=10000.0,
                            label_visibility="collapsed"
                        )
                        closed_won_range = (0.0, max_val)
                    
                    if closed_won_range != (0.0, cw_max):
                        st.caption(f"✓ ${closed_won_range[0]:,.0f} - ${closed_won_range[1]:,.0f}")
            
            # Pipeline filter (expandable)
            if 'Pipeline' in df.columns and df['Pipeline'].notna().any():
                with st.expander("**Pipeline**", expanded=False):
                    pipe_min = float(df['Pipeline'].min())
                    pipe_max = float(df['Pipeline'].max())
                    
                    pipeline_filter_type = st.radio(
                        "Filter type",
                        ["Range", "Minimum", "Maximum"],
                        key="pipe_filter_type",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    
                    if pipeline_filter_type == "Range":
                        pipeline_range = st.slider(
                            "Select range",
                            min_value=0.0,
                            max_value=pipe_max,
                            value=(0.0, pipe_max),
                            step=max(10000.0, pipe_max / 100),
                            format="$%.0f",
                            label_visibility="collapsed"
                        )
                    elif pipeline_filter_type == "Minimum":
                        min_val = st.number_input(
                            "Minimum $",
                            min_value=0.0,
                            max_value=pipe_max,
                            value=0.0,
                            step=10000.0,
                            label_visibility="collapsed"
                        )
                        pipeline_range = (min_val, pipe_max)
                    else:  # Maximum
                        max_val = st.number_input(
                            "Maximum $",
                            min_value=0.0,
                            max_value=pipe_max,
                            value=pipe_max,
                            step=10000.0,
                            label_visibility="collapsed"
                        )
                        pipeline_range = (0.0, max_val)
                    
                    if pipeline_range != (0.0, pipe_max):
                        st.caption(f"✓ ${pipeline_range[0]:,.0f} - ${pipeline_range[1]:,.0f}")
            
            # Meetings filter (expandable)
            if 'Meetings' in df.columns and df['Meetings'].notna().any():
                with st.expander("**Meetings**", expanded=False):
                    meet_min = int(df['Meetings'].min())
                    meet_max = int(df['Meetings'].max())
                    
                    meetings_filter_type = st.radio(
                        "Filter type",
                        ["Range", "Minimum", "Maximum"],
                        key="meet_filter_type",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    
                    if meetings_filter_type == "Range":
                        meetings_range = st.slider(
                            "Select range",
                            min_value=0,
                            max_value=max(100, meet_max),
                            value=(0, max(100, meet_max)),
                            step=1,
                            label_visibility="collapsed"
                        )
                    elif meetings_filter_type == "Minimum":
                        min_val = st.number_input(
                            "Minimum",
                            min_value=0,
                            max_value=max(100, meet_max),
                            value=0,
                            step=1,
                            label_visibility="collapsed"
                        )
                        meetings_range = (min_val, max(100, meet_max))
                    else:  # Maximum
                        max_val = st.number_input(
                            "Maximum",
                            min_value=0,
                            max_value=max(100, meet_max),
                            value=max(100, meet_max),
                            step=1,
                            label_visibility="collapsed"
                        )
                        meetings_range = (0, max_val)
                    
                    if meetings_range != (0, max(100, meet_max)):
                        st.caption(f"✓ {meetings_range[0]} - {meetings_range[1]}")

        # Apply filters
        filtered_df = df.copy()
        
        # Apply manager filter
        if 'Manager Name' in filtered_df.columns:
            if selected_managers:
                filtered_df = filtered_df[filtered_df['Manager Name'].isin(selected_managers)]
            else:
                filtered_df = pd.DataFrame(columns=filtered_df.columns)
        
        # Apply AE filter
        if 'AE Name' in filtered_df.columns:
            if selected_aes:
                filtered_df = filtered_df[filtered_df['AE Name'].isin(selected_aes)]
            else:
                filtered_df = pd.DataFrame(columns=filtered_df.columns)
        
        # Apply numeric filters
        if quota_range and '% to Quota' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['% to Quota'] >= quota_range[0]) & 
                (filtered_df['% to Quota'] <= quota_range[1])
            ]
        
        if closed_won_range and 'Closed Won' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['Closed Won'] >= closed_won_range[0]) & 
                (filtered_df['Closed Won'] <= closed_won_range[1])
            ]
        
        if pipeline_range and 'Pipeline' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['Pipeline'] >= pipeline_range[0]) & 
                (filtered_df['Pipeline'] <= pipeline_range[1])
            ]
        
        if meetings_range and 'Meetings' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['Meetings'] >= meetings_range[0]) & 
                (filtered_df['Meetings'] <= meetings_range[1])
            ]
        
        # Display summary metrics (always show full dataset metrics)
        display_summary_metrics(df)
        st.markdown("---")

        st.subheader("Detailed AE Performance")
        
        # Show active filters summary
        active_filters = []
        all_managers = sorted(df['Manager Name'].dropna().unique().tolist()) if 'Manager Name' in df.columns else []
        all_aes = sorted(df['AE Name'].dropna().unique().tolist()) if 'AE Name' in df.columns else []
        
        if len(selected_managers) < len(all_managers):
            active_filters.append(f"{len(selected_managers)} manager(s)")
        if len(selected_aes) < len(all_aes):
            active_filters.append(f"{len(selected_aes)} AE(s)")
        
        # Check numeric filters
        if quota_range and '% to Quota' in df.columns:
            quota_max_check = max(200.0, float(df['% to Quota'].max()) if df['% to Quota'].notna().any() else 200.0)
            if quota_range != (0.0, quota_max_check):
                active_filters.append(f"Quota: {quota_range[0]:.0f}%-{quota_range[1]:.0f}%")
        
        if closed_won_range and 'Closed Won' in df.columns:
            cw_max_check = float(df['Closed Won'].max()) if df['Closed Won'].notna().any() else 0
            if closed_won_range != (0.0, cw_max_check):
                active_filters.append(f"Closed Won: ${closed_won_range[0]:,.0f}-${closed_won_range[1]:,.0f}")
        
        if pipeline_range and 'Pipeline' in df.columns:
            pipe_max_check = float(df['Pipeline'].max()) if df['Pipeline'].notna().any() else 0
            if pipeline_range != (0.0, pipe_max_check):
                active_filters.append(f"Pipeline: ${pipeline_range[0]:,.0f}-${pipeline_range[1]:,.0f}")
        
        if meetings_range and 'Meetings' in df.columns:
            meet_max_check = max(100, int(df['Meetings'].max()) if df['Meetings'].notna().any() else 100)
            if meetings_range != (0, meet_max_check):
                active_filters.append(f"Meetings: {meetings_range[0]}-{meetings_range[1]}")
        
        if active_filters:
            st.info(f"🔍 Active filters: {', '.join(active_filters)} | Showing **{len(filtered_df)}** of **{len(df)}** AEs")
        else:
            st.caption(f"Showing all {len(df)} AEs")

        # Streamlit native dataframe with styling and formatting
        display_df = prepare_display_df(filtered_df)
        col_config = get_column_config(display_df)
        styled_df = style_negative_gaps(display_df)

        st.dataframe(
            styled_df,
            column_config=col_config,
            use_container_width=True,
            hide_index=True,
            height=500,
        )

        st.markdown("---")
        st.download_button(
            label="📥 Download as CSV",
            data=filtered_df.to_csv(index=False),
            file_name=f"ae_dashboard_{p_year}_{p_month:02d}.csv",
            mime="text/csv"
        )

        display_insights(filtered_df)


if __name__ == "__main__":
    main()
