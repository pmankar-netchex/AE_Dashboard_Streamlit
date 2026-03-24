import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

import streamlit as st

from src.salesforce_oauth import (
    is_oauth_configured,
    get_authorization_url,
    exchange_code_for_tokens,
    refresh_access_token,
    create_salesforce_client,
)
from src.meta_filters import resolve_time_period, build_filter_params
from src.data_engine import (
    build_dashboard_dataframe,
    get_managers_list,
    get_ae_names_list,
    clear_query_failures,
)
from src.soql_registry import ALL_COLUMNS, COLUMN_BY_ID, build_query, resolve_owner_clauses
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

_LEGACY_SF_TOKEN_FILE = Path.home() / ".salesforce_tokens" / "ae_dashboard.json"


def _clear_legacy_saved_salesforce_tokens():
    """Remove on-disk tokens from older versions (session-only auth now)."""
    if _LEGACY_SF_TOKEN_FILE.exists():
        try:
            _LEGACY_SF_TOKEN_FILE.unlink()
        except OSError:
            pass


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
                    return create_salesforce_client(
                        st.session_state["sf_oauth"]["instance_url"], tokens["access_token"]
                    )
                except Exception:
                    del st.session_state["sf_oauth"]
            else:
                del st.session_state["sf_oauth"]

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
    """Render meta filters in sidebar, return filter_params dict. [spec: Section A]"""
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

    st.title("📊 AE Performance Dashboard")

    if "dashboard_df" not in st.session_state:
        st.session_state["dashboard_df"] = None
        st.session_state["fetch_ts"] = None

    # Auto-refresh when filter params change (fixes period-dependent columns)
    params_key = str(sorted(params.items()))
    if st.session_state.get("last_params_key") != params_key:
        st.session_state["dashboard_df"] = None
        st.session_state["last_params_key"] = params_key

    should_refresh = render_fetch_status(st.session_state.get("fetch_ts"))

    if st.session_state["dashboard_df"] is None or should_refresh:
        if should_refresh:
            clear_query_failures()
        with st.spinner("Fetching data from Salesforce…"):
            overrides = st.session_state.get("soql_overrides", {})
            df = build_dashboard_dataframe(sf, params, overrides)
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

    # --- Test AE selector (replaces DUMMY_ID) ---
    if "soql_test_ae_list" not in st.session_state:
        st.session_state["soql_test_ae_list"] = []
    if st.button("Load AE List", key="load_ae_list") or st.session_state["soql_test_ae_list"]:
        if not st.session_state["soql_test_ae_list"]:
            with st.spinner("Loading AEs from Salesforce..."):
                st.session_state["soql_test_ae_list"] = get_ae_names_list(sf)
        ae_list = st.session_state["soql_test_ae_list"]
        if not ae_list:
            st.warning("No AEs found. Check User_Role_Formula__c filter.")
        else:
            ae_display = [f"{a['name']} ({a['id']})" for a in ae_list]
            selected_idx = st.selectbox(
                "Select AE for testing queries",
                range(len(ae_display)),
                format_func=lambda i: ae_display[i],
                key="soql_test_ae_select",
            )
            selected_ae = ae_list[selected_idx]
            st.session_state["soql_test_ae_id"] = selected_ae["id"]
            st.session_state["soql_test_ae_email"] = selected_ae["email"]
    else:
        st.info("Click 'Load AE List' to select a test AE for running queries.")

    st.divider()

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

            # Show resolved owner clauses
            test_ae_id = st.session_state.get("soql_test_ae_id")
            clause_params = {
                "ae_user_id": test_ae_id or "",
                "ae_email": st.session_state.get("soql_test_ae_email", ""),
                "manager_name": None,
            }
            clauses = resolve_owner_clauses(entry.template, clause_params)
            if clauses:
                for name, placeholder, resolved in clauses:
                    if test_ae_id:
                        st.code(f"{name}: {resolved}", language=None)
                    else:
                        st.caption(f"Uses `{placeholder}` — select test AE to preview")

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
                    test_ae_id = st.session_state.get("soql_test_ae_id")
                    test_ae_email = st.session_state.get("soql_test_ae_email", "")
                    if not test_ae_id:
                        st.warning("Please load and select a test AE above first.")
                    else:
                        test_params = {
                            "ae_user_id": test_ae_id,
                            "ae_email": test_ae_email,
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
                        from src.soql_registry import SOQLEntry as _SOQLEntry, build_query as _bq
                        test_entry = _SOQLEntry(
                            col_id=entry.col_id,
                            display_name=entry.display_name,
                            section=entry.section,
                            description=entry.description,
                            template=new_soql,
                            time_filter=entry.time_filter,
                            aggregation=entry.aggregation,
                        )
                        try:
                            built = _bq(test_entry, test_params)
                            result = sf.query(built.strip())
                            records = result.get("records", [])
                            if records:
                                first = records[0]
                                value = next(
                                    (v for k, v in first.items() if k != "attributes"),
                                    None,
                                )
                                st.success(
                                    f"Query OK — returned **{value}** "
                                    f"({result.get('totalSize', 0)} record(s)). "
                                    f"Click Save to persist."
                                )
                            else:
                                st.success(
                                    "Query OK — returned **0 records** (null). "
                                    "Click Save to persist."
                                )
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

    st.divider()
    if st.button("Refresh Dashboard with Updated Queries"):
        st.session_state["dashboard_df"] = None
        clear_query_failures()
        st.success("Dashboard will refresh on next view.")


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
        me = sf.query("SELECT Id, Name FROM User WHERE Id = UserInfo.getUserId() LIMIT 1")
        if me.get("records"):
            r = me["records"][0]
            st.write(f"**Authenticated User:** {r['Name']}")
    except Exception:
        st.write("**Authenticated User:** Unable to retrieve")

    if st.button("Disconnect Salesforce"):
        _clear_legacy_saved_salesforce_tokens()
        if "sf_oauth" in st.session_state:
            del st.session_state["sf_oauth"]
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
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
