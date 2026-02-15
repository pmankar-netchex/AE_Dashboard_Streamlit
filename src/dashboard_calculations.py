"""
Dashboard Business Logic and Calculations
Customize formulas, defaults, and data processing here.
"""
from datetime import datetime
import calendar
import pandas as pd


def get_month_date_range(year, month):
    """Get the first and last day of a given month for SOQL queries."""
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')


def calculate_meetings_needed(remaining_quota, avg_deal_size=5000, win_rate=0.20):
    """
    Calculate number of meetings needed to hit quota.
    
    Formula: meetings = (remaining_quota / avg_deal_size) / win_rate
    
    Customize:
    - avg_deal_size: Your typical deal value
    - win_rate: Conversion rate (0.20 = 20%)
    """
    if remaining_quota <= 0:
        return 0
    
    deals_needed = remaining_quota / avg_deal_size
    meetings_needed = deals_needed / win_rate
    
    return int(meetings_needed)


NO_HISTORIC_DATA = -99


def build_dashboard_data(sf, ae_df, closed_won_dict, pipeline_dict, meetings_dict,
                        activity_email_dict, activity_phone_dict, forecast_dict, quota_dict,
                        pipeline_ratio_dict, avg_deal_size, win_rate):
    """
    Build the complete dashboard dataset from Salesforce data.

    Pipeline Coverage Ratio = SUM(total pipeline last 6 months) / SUM(closed-won last 6 months)
        per owner (inverse win rate).
    Falls back to 5.0x if no historic data is available.
    """
    dashboard_data = []

    for _, row in ae_df.iterrows():
        ae_id = row['Id']
        ae_name = row['Name']
        manager_name = row.get('Manager_Name__c', 'N/A')

        # Get metrics from bulk queries
        closed_won = closed_won_dict.get(ae_id, 0.0)
        open_pipeline = pipeline_dict.get(ae_id, 0.0)
        meetings_scheduled = meetings_dict.get(ae_id, 0)
        activity_email = activity_email_dict.get(ae_id, 0)
        activity_phone = activity_phone_dict.get(ae_id, 0)
        forecast_amount = forecast_dict.get(ae_id, 0.0)
        quota_amount = quota_dict.get(ae_id, 0.0)

        # Percent to Quota = ForecastingItem.ForecastAmount:SUM / ForecastingQuota.QuotaAmount:SUM
        percent_to_quota = (forecast_amount / quota_amount * 100) if quota_amount > 0 else 0.0

        # Historic Pipeline Coverage Ratio (avg last 6 months, -99 for display if unavailable)
        pipeline_coverage_ratio = pipeline_ratio_dict.get(ae_id, NO_HISTORIC_DATA)

        # Use 5.0x default for calculations when no historic data; -99 is display-only
        effective_ratio = pipeline_coverage_ratio if pipeline_coverage_ratio != NO_HISTORIC_DATA else 5.0
        remainder = quota_amount - closed_won
        pipeline_should_have = remainder * effective_ratio
        pipeline_gap = open_pipeline - pipeline_should_have
        meetings_needed = calculate_meetings_needed(remainder, avg_deal_size, win_rate)
        meeting_gap = meetings_scheduled - meetings_needed

        dashboard_data.append({
            'AE Name': ae_name,
            'Manager Name': manager_name,
            'Forecast Amount': forecast_amount,
            'Quota Amount': quota_amount,
            'Percent to Quota (%)': percent_to_quota,
            'Closed Won': closed_won,
            'Remainder': remainder,
            'Pipeline Coverage Ratio': pipeline_coverage_ratio,
            'Pipeline You Should Have': pipeline_should_have,
            'Open Pipeline with CW Date in Month': open_pipeline,
            'Pipeline Gap': pipeline_gap,
            'Activity Email': activity_email,
            'Activity Phone': activity_phone,
            'Activity Total': activity_email + activity_phone,
            'Meetings Needed': meetings_needed,
            'Meetings Scheduled': meetings_scheduled,
            'Meeting Gap': meeting_gap
        })

    return pd.DataFrame(dashboard_data)


# ==============================================================================
# CUSTOMIZATION NOTES
# ==============================================================================

"""
Common customizations:

1. CHANGE QUOTA CALCULATION:
   Line 55: remainder = monthly_quota - closed_won
   → Add: remainder = max(0, monthly_quota - closed_won)  # Never negative

2. CHANGE PIPELINE COVERAGE FORMULA:
   Line 56: pipeline_should_have = remainder * pipeline_coverage_ratio
   → Customize based on your methodology

3. ADJUST MEETINGS NEEDED FORMULA:
   Line 23-35: Update avg_deal_size and win_rate defaults
   → Or change the entire formula

4. ADD MORE COLUMNS:
   In dashboard_data.append(), add:
   'Manager': row.get('Manager__r', {}).get('Name', 'N/A')
   'Region': row.get('Region__c', 'N/A')

5. CHANGE DEFAULT VALUES:
   Line 55-56: Default quota 45000, ratio 3.0
   → Adjust to match your org's averages
"""
