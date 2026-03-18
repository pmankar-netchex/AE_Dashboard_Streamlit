# Improve the dashbaord and fix the error

<Fix 01 - Dashbaord error>
Fix dashboard error - StreamlitAPIException: Expanders may not be nested inside other expanders.

Traceback:
File "/Users/apple/Documents/Workspace/Projects/AE_Dashboard_Streamlit/streamlit_dashboard.py", line 451, in <module>
    main()
File "/Users/apple/Documents/Workspace/Projects/AE_Dashboard_Streamlit/streamlit_dashboard.py", line 443, in main
    render_dashboard_tab(sf)
File "/Users/apple/Documents/Workspace/Projects/AE_Dashboard_Streamlit/streamlit_dashboard.py", line 247, in render_dashboard_tab
    display_dashboard_table(df)
File "/Users/apple/Documents/Workspace/Projects/AE_Dashboard_Streamlit/src/dashboard_ui.py", line 167, in display_dashboard_table
    with st.expander("Column Descriptions", expanded=False):
</Fix 01 - Dashbaord error>


<Fix 02 - SOQL performance>

    -  ALl SOQLs are seems to be being triggerd in sequence, if we could parallelize some of them it would improve performance

</Fix 02 -  SOQL performance>