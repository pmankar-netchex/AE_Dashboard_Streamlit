"""
Salesforce SOQL Queries
Organized by entity for easy customization.
"""
import streamlit as st
import pandas as pd


# ==============================================================================
# USER QUERIES (Account Executives)
# ==============================================================================

def get_ae_by_ids(sf, owner_ids):
    """
    Get User records only for the given OwnerIds (from opportunities).
    Returns AE details for building the dashboard.
    """
    if not owner_ids:
        return pd.DataFrame()

    ids_str = "','".join(owner_ids)
    query = f"""
        SELECT Id, Name,Manager_Name__c,Months_On_Quota__c,Department
        FROM User
        WHERE Id IN ('{ids_str}')
        AND IsActive = true
        AND Department = 'Sales'
        ORDER BY Name
    """
    try:
        result = sf.query(query)
        return pd.DataFrame(result['records']).drop(columns=['attributes'])
    except Exception as e:
        st.warning(f"Error fetching users: {str(e)}")
        return pd.DataFrame()


# ==============================================================================
# OPPORTUNITY QUERIES
# ==============================================================================

def get_all_opportunities(sf, start_date, end_date):
    """
    Get all opportunities in the period (Closed Won + Open Pipeline).
    Returns owner-level aggregates - use these OwnerIds to fetch AE details.
    
    Customize:
    - Closed Won stage name (currently 'Closed/Won')
    - Date field (currently CloseDate)
    - Additional filters (RecordType, Amount > threshold, etc.)
    
    Returns: (closed_won_dict, open_pipeline_dict)
    """
    # QUERY 1: Closed Won opportunities in period
    closed_won_query = f"""
        SELECT OwnerId, SUM(Amount) totalAmount
        FROM Opportunity
        WHERE StageName = 'Closed/Won'
        AND CloseDate >= {start_date}
        AND CloseDate <= {end_date}
        GROUP BY OwnerId
    """

    # QUERY 2: Open Pipeline with close date in period
    open_pipeline_query = f"""
        SELECT OwnerId, SUM(Amount) totalAmount
        FROM Opportunity
        WHERE IsClosed = false
        AND CloseDate >= {start_date}
        AND CloseDate <= {end_date}
        GROUP BY OwnerId
    """
    
    try:
        closed_result = sf.query(closed_won_query)
        pipeline_result = sf.query(open_pipeline_query)
        
        closed_won_dict = {
            r['OwnerId']: float(r['totalAmount'] or 0) 
            for r in closed_result['records']
        }
        
        pipeline_dict = {
            r['OwnerId']: float(r['totalAmount'] or 0) 
            for r in pipeline_result['records']
        }
        
        return closed_won_dict, pipeline_dict
    except Exception as e:
        st.warning(f"Error fetching opportunities: {str(e)}")
        return {}, {}


# ==============================================================================
# FORECASTING QUERIES (Percent to Quota = ForecastAmount / QuotaAmount)
# ==============================================================================

def get_forecast_amounts(sf, ae_ids, start_date, end_date):
    """
    Get SUM(ForecastAmount) by Owner from ForecastingItem for the period.
    Requires ForecastingItem access (View All Forecasts or similar).
    """
    ids_str = "','".join(ae_ids)
    query = f"""
        SELECT OwnerId, SUM(ForecastAmount) totalForecast
        FROM ForecastingItem
        WHERE OwnerId IN ('{ids_str}')
        AND Period.StartDate >= {start_date}
        AND Period.StartDate <= {end_date}
        GROUP BY OwnerId
    """
    try:
        result = sf.query(query)
        return {r['OwnerId']: float(r['totalForecast'] or 0) for r in result['records']}
    except Exception as e:
        st.warning(f"ForecastingItem query failed (forecasting may be disabled): {str(e)}")
        return {}


def get_quota_amounts(sf, ae_ids, start_date, end_date):
    """
    Get SUM(QuotaAmount) by QuotaOwnerId from ForecastingQuota for the period.
    Requires ForecastingQuota access (Manage Quotas or similar).
    """
    ids_str = "','".join(ae_ids)
    query = f"""
        SELECT QuotaOwnerId, SUM(QuotaAmount) totalQuota
        FROM ForecastingQuota
        WHERE QuotaOwnerId IN ('{ids_str}')
        AND StartDate >= {start_date}
        AND StartDate <= {end_date}
        GROUP BY QuotaOwnerId
    """
    try:
        result = sf.query(query)
        return {r['QuotaOwnerId']: float(r['totalQuota'] or 0) for r in result['records']}
    except Exception as e:
        st.warning(f"ForecastingQuota query failed (forecasting may be disabled): {str(e)}")
        return {}


# ==============================================================================
# HISTORIC PIPELINE COVERAGE RATIO (avg last 6 months)
# ==============================================================================

def get_historic_pipeline_ratios(sf, ae_ids, current_year, current_month):
    """
    Compute historic Pipeline Coverage Ratio per owner across the last 6 months.

    Pipeline Coverage Ratio = SUM(Total Pipeline last 6 months) / SUM(Closed Won last 6 months)
    This is the inverse of win-rate: e.g. 5.0x means 20% conversion,
    so you need $5 of pipeline for every $1 you need to close.

    Returns: {owner_id: ratio}  (e.g. 5.0 means 5.0x coverage needed)
    """
    from datetime import datetime
    import calendar

    if not ae_ids:
        return {}

    ids_str = "','".join(ae_ids)

    # Build the 6 prior month date range (start of 6 months ago to end of last month)
    y, m = current_year, current_month
    for _ in range(6):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    
    # Start = first day of 6 months ago
    start_date = datetime(y, m, 1).strftime('%Y-%m-%d')
    
    # End = last day of the month before current month
    y2, m2 = current_year, current_month
    m2 -= 1
    if m2 == 0:
        m2 = 12
        y2 -= 1
    end_date = datetime(y2, m2, calendar.monthrange(y2, m2)[1]).strftime('%Y-%m-%d')

    # Aggregate total pipeline across 6 months per owner
    total_pipeline_dict = {}
    try:
        q = f"""
            SELECT OwnerId, SUM(Amount) totalAmount
            FROM Opportunity
            WHERE OwnerId IN ('{ids_str}')
            AND CloseDate >= {start_date}
            AND CloseDate <= {end_date}
            GROUP BY OwnerId
        """
        result = sf.query(q)
        for r in result['records']:
            total_pipeline_dict[r['OwnerId']] = float(r['totalAmount'] or 0)
    except Exception:
        pass

    # Aggregate closed-won across 6 months per owner
    closed_won_dict = {}
    try:
        q = f"""
            SELECT OwnerId, SUM(Amount) wonAmount
            FROM Opportunity
            WHERE OwnerId IN ('{ids_str}')
            AND CloseDate >= {start_date}
            AND CloseDate <= {end_date}
            AND StageName = 'Closed/Won'
            GROUP BY OwnerId
        """
        result = sf.query(q)
        for r in result['records']:
            closed_won_dict[r['OwnerId']] = float(r['wonAmount'] or 0)
    except Exception:
        pass

    # Ratio = Total Pipeline / Closed Won (across all 6 months)
    ratios = {}
    for owner_id in total_pipeline_dict:
        total_pipe = total_pipeline_dict[owner_id]
        closed_won = closed_won_dict.get(owner_id, 0)
        if closed_won > 0 and total_pipe > 0:
            ratios[owner_id] = total_pipe / closed_won

    return ratios


# ==============================================================================
# ACTIVITY VOLUME (Email + Phone split)
# ==============================================================================

def get_activity_by_type(sf, ae_ids, start_date, end_date):
    """
    Get activity counts split by Email and Phone per owner.
    - Email: Tasks with Type = 'Email'
    - Phone: Tasks with Type = 'Call' (or similar) + Events (meetings/calls)
    Returns: (email_dict, phone_dict) each {owner_id: count}
    """
    if not ae_ids:
        return {}, {}

    ids_str = "','".join(ae_ids)
    email_dict = {}
    phone_dict = {}

    # Email: Tasks with Type = 'Email'
    try:
        email_query = f"""
            SELECT OwnerId, COUNT(Id) cnt
            FROM Task
            WHERE OwnerId IN ('{ids_str}')
            AND ActivityDate >= {start_date}
            AND ActivityDate <= {end_date}
            AND Type = 'Email'
            GROUP BY OwnerId
        """
        result = sf.query(email_query)
        for r in result['records']:
            email_dict[r['OwnerId']] = int(r['cnt'] or 0)
    except Exception:
        pass

    # Phone: Tasks (Call types) + Events
    try:
        # Tasks: Call, Outbound Call, Inbound Call
        phone_task_query = f"""
            SELECT OwnerId, COUNT(Id) cnt
            FROM Task
            WHERE OwnerId IN ('{ids_str}')
            AND ActivityDate >= {start_date}
            AND ActivityDate <= {end_date}
            AND (Type = 'Call' OR Type = 'Outbound Call' OR Type = 'Inbound Call')
            GROUP BY OwnerId
        """
        result = sf.query(phone_task_query)
        for r in result['records']:
            phone_dict[r['OwnerId']] = phone_dict.get(r['OwnerId'], 0) + int(r['cnt'] or 0)
    except Exception:
        pass

    try:
        # Events: meetings, calls (all events count as phone/meeting activity)
        event_query = f"""
            SELECT OwnerId, COUNT(Id) cnt
            FROM Event
            WHERE OwnerId IN ('{ids_str}')
            AND ActivityDate >= {start_date}
            AND ActivityDate <= {end_date}
            GROUP BY OwnerId
        """
        result = sf.query(event_query)
        for r in result['records']:
            phone_dict[r['OwnerId']] = phone_dict.get(r['OwnerId'], 0) + int(r['cnt'] or 0)
    except Exception:
        pass

    return email_dict, phone_dict


# ==============================================================================
# EVENT/MEETING QUERIES
# ==============================================================================

def get_all_meetings(sf, ae_ids, start_date, end_date):
    """
    Get count of meetings for all AEs in bulk (optimized).
    
    Args:
        ae_ids: tuple of AE Salesforce IDs
        start_date, end_date: YYYY-MM-DD format (cache key includes these)
    
    Customize:
    - Subject keywords (currently 'meeting', 'call', 'demo')
    - Date field (currently ActivityDate)
    - Event types/RecordTypes
    - Additional filters (IsRecurrence = false, etc.)
    
    Returns: meetings_dict {owner_id: count}
    """
    ids_str = "','".join(ae_ids)
    
    query = f"""
        SELECT OwnerId, COUNT(Id) meetingCount
        FROM Event
        WHERE OwnerId IN ('{ids_str}')
        AND ActivityDate >= {start_date}
        AND ActivityDate <= {end_date}
        AND IsRecurrence = false
        AND (Subject LIKE '%meeting%' OR Subject LIKE '%call%' OR Subject LIKE '%demo%')
        GROUP BY OwnerId
    """
    
    try:
        result = sf.query(query)
        meetings_dict = {
            r['OwnerId']: int(r['meetingCount']) 
            for r in result['records']
        }
        return meetings_dict
    except Exception as e:
        st.warning(f"Error fetching meetings: {str(e)}")
        return {}


# ==============================================================================
# CUSTOMIZATION NOTES
# ==============================================================================

"""
Common customizations:

1. CHANGE CLOSED WON STAGE:
   get_all_opportunities: AND StageName = 'Closed/Won'
   → Change to your org's stage name (e.g. 'Won', 'Closed-Won')

2. ADD CUSTOM FIELDS TO USER (get_ae_by_ids):
   SELECT Id, Name → Add: , Region__c, Team__c, Manager__c

3. FILTER OPPORTUNITIES BY RECORDTYPE:
   get_all_opportunities: Add AND RecordType.Name = 'Enterprise'

4. CHANGE MEETING KEYWORDS:
   get_all_meetings: AND (Subject LIKE '%meeting%' OR Subject LIKE '%call%' OR Subject LIKE '%demo%')
   → Customize keywords to match your org

5. EXCLUDE RECURRING EVENTS:
   get_all_meetings: Add AND IsRecurrence = false

6. MINIMUM OPPORTUNITY AMOUNT:
   get_all_opportunities: Add AND Amount > 1000
"""
