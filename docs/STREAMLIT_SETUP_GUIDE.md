# AE Ultimate Dashboard - Streamlit Setup Guide

## Overview

This Streamlit dashboard connects directly to your Salesforce org using SOQL queries to pull live data and display it in the exact format of your Excel dashboard.

### ✅ Advantages of the Streamlit Approach

1. **No Salesforce code deployment** - Run externally, no custom Apex needed
2. **Faster development** - Python is easier to modify than Salesforce LWC
3. **More flexibility** - Add charts, graphs, custom logic easily
4. **Better for prototyping** - Test and iterate quickly
5. **Works with any Salesforce edition** - Even if you have limited customization rights
6. **Easy to share** - Deploy to Streamlit Cloud or internal server

### ⚠️ Considerations

- Requires maintaining external application
- API call limits (check your Salesforce edition)
- Need to handle authentication securely
- Runs outside Salesforce (not embedded)

## Prerequisites

### 1. Salesforce Requirements

- Salesforce account with API access
- Salesforce edition: Professional, Enterprise, Unlimited, or Developer
- Custom fields on User object (optional but recommended):
  - `Monthly_Quota__c` (Currency)
  - `Pipeline_Coverage_Ratio__c` (Number)

### 2. Python Environment

- Python 3.8 or higher
- pip (Python package manager)

### 3. Salesforce Security Token

You'll need your Salesforce security token:
1. Login to Salesforce
2. Click your profile picture → Settings
3. Search for "Reset Security Token" in Quick Find
4. Click "Reset Security Token"
5. Check your email for the new token

## Installation Steps

### Step 1: Setup Python Environment

Create a new directory and virtual environment:

```bash
# Create project directory
mkdir ae-dashboard-streamlit
cd ae-dashboard-streamlit

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies

Save the `requirements.txt` file and install:

```bash
pip install -r requirements.txt
```

This installs:
- **streamlit**: Dashboard framework
- **pandas**: Data manipulation
- **simple-salesforce**: Salesforce API connector
- **plotly**: Interactive charts (for future enhancements)

### Step 3: Setup Salesforce Credentials

Create a `.streamlit` directory and secrets file:

```bash
mkdir .streamlit
```

Create `.streamlit/secrets.toml` with your credentials:

```toml
[salesforce]
username = "your_email@company.com"
password = "your_password"
security_token = "your_security_token"
```

**🔒 Security Note:** 
- Never commit `secrets.toml` to version control
- Add `.streamlit/` to your `.gitignore`

### Step 4: Customize SOQL Queries (if needed)

Open `streamlit_dashboard.py` and adjust the queries based on your Salesforce setup:

#### A. User/AE Query (Line ~60)

If your org uses different criteria to identify Account Executives:

```python
# Current query
query = """
    SELECT Id, Name, Monthly_Quota__c, Pipeline_Coverage_Ratio__c
    FROM User
    WHERE IsActive = true
    AND Profile.Name LIKE '%Sales%'
    AND Monthly_Quota__c != null
    ORDER BY Name
"""

# Alternative: Filter by Role
query = """
    SELECT Id, Name, Monthly_Quota__c, Pipeline_Coverage_Ratio__c
    FROM User
    WHERE IsActive = true
    AND UserRole.Name LIKE '%Account Executive%'
    ORDER BY Name
"""

# Alternative: Filter by specific Profile
query = """
    SELECT Id, Name, Monthly_Quota__c, Pipeline_Coverage_Ratio__c
    FROM User
    WHERE IsActive = true
    AND Profile.Name = 'Sales User'
    ORDER BY Name
"""
```

#### B. If Custom Fields Don't Exist

If you haven't created `Monthly_Quota__c` and `Pipeline_Coverage_Ratio__c`:

**Option 1:** Create the custom fields (recommended)
- Go to Setup → Object Manager → User
- Create the fields as outlined in the Salesforce guide

**Option 2:** Use hardcoded values temporarily

```python
# In get_ae_list() function, modify:
df['Monthly_Quota__c'] = 45000  # Default quota
df['Pipeline_Coverage_Ratio__c'] = 3.0  # Default ratio
```

**Option 3:** Store in a separate custom object
- Create a "Sales_Quotas__c" object
- Link to Users via lookup
- Modify queries to join this object

#### C. Closed Won Stage Name

If your Salesforce uses a different stage name for closed deals:

```python
# Line ~95 - Adjust stage name
query = f"""
    SELECT SUM(Amount) totalAmount
    FROM Opportunity
    WHERE OwnerId = '{owner_id}'
    AND StageName = 'Closed Won'  # Change this to match your org
    AND CloseDate >= {start_date}
    AND CloseDate <= {end_date}
"""

# Examples of other common stage names:
# 'Closed - Won'
# 'Won'
# 'Contract Signed'
```

#### D. Meeting Event Filtering

Customize how meetings are identified:

```python
# Line ~140
query = f"""
    SELECT COUNT() 
    FROM Event
    WHERE OwnerId = '{owner_id}'
    AND ActivityDate >= {start_date}
    AND ActivityDate <= {end_date}
    AND (Subject LIKE '%meeting%' OR Subject LIKE '%call%' OR Subject LIKE '%demo%')
"""

# Add your meeting keywords:
# AND (Subject LIKE '%meeting%' OR Subject LIKE '%discovery%' OR Subject LIKE '%presentation%')

# Or filter by Event Type:
# AND Type = 'Meeting'
```

### Step 5: Run the Dashboard

```bash
streamlit run streamlit_dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Using the Dashboard

### Main Features

1. **Month/Year Selector** (Sidebar)
   - Choose any month to view historical data
   - Defaults to current month

2. **Calculation Settings** (Sidebar)
   - Adjust Average Deal Size
   - Adjust Win Rate percentage
   - These affect "Meetings Needed" calculations

3. **Summary Metrics** (Top Row)
   - Total Quota across all AEs
   - Total Closed Won with attainment %
   - Total Pipeline
   - Total Pipeline Gap

4. **Main Table**
   - All 11 columns from your Excel dashboard
   - Live data from Salesforce
   - Currency formatting
   - Sortable columns

5. **Download Button**
   - Export data as CSV
   - Filename includes month/year

6. **Additional Insights** (Expandable)
   - Top 5 performers by quota attainment
   - Top 5 AEs with largest pipeline gaps

### Keyboard Shortcuts

- `R` - Refresh the page
- `C` - Clear cache and reload data

## Deployment Options

### Option 1: Local Development

Run locally for testing:
```bash
streamlit run streamlit_dashboard.py
```

### Option 2: Streamlit Community Cloud (Free)

Deploy for free on Streamlit Cloud:

1. Push code to GitHub repository
2. Go to https://share.streamlit.io
3. Connect your GitHub account
4. Deploy the app
5. Add secrets in the Streamlit Cloud dashboard

**Secrets in Streamlit Cloud:**
- Go to App Settings → Secrets
- Add your Salesforce credentials:
```toml
[salesforce]
username = "your_email@company.com"
password = "your_password"
security_token = "your_security_token"
```

### Option 3: Internal Server

Deploy on your company's server:

1. Install dependencies on server
2. Use a process manager like `supervisor` or `systemd`
3. Run with: `streamlit run streamlit_dashboard.py --server.port=8501`
4. Setup reverse proxy (nginx/Apache) for HTTPS
5. Configure authentication if needed

### Option 4: Docker Container

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t ae-dashboard .
docker run -p 8501:8501 ae-dashboard
```

## Troubleshooting

### Issue: "Authentication failed"

**Solution:**
- Verify username, password, and security token
- Ensure no extra spaces in credentials
- Try resetting your security token
- Check if your IP is whitelisted in Salesforce

### Issue: "INVALID_FIELD" error

**Solution:**
- Custom fields don't exist on User object
- Either create the fields in Salesforce
- Or modify the code to use hardcoded values (see Step 4B)

### Issue: "API limit exceeded"

**Solution:**
- Reduce refresh frequency
- Check Salesforce edition API limits
- Consider caching data
- Add `@st.cache_data` decorators with longer TTL

### Issue: Data loading slowly

**Solution:**
- The app makes one API call per AE
- For 50 AEs, that's 150+ API calls (Closed Won + Pipeline + Meetings per AE)
- **Optimization options:**
  1. Use bulk queries (get all data in fewer calls)
  2. Implement caching
  3. Run queries in parallel

### Issue: Different Salesforce field names

**Solution:**
- Check your Salesforce object field names
- Modify queries to match your schema
- Use Salesforce Workbench to test SOQL queries

## Advanced Customization

### Add Charts and Visualizations

Add Plotly charts for better insights:

```python
import plotly.express as px

# After the main table, add:
st.subheader("Quota Attainment by AE")
fig = px.bar(
    df, 
    x='AE Name', 
    y=['Closed Won', 'Monthly Quota'],
    barmode='group',
    title='Quota Attainment Comparison'
)
st.plotly_chart(fig, use_container_width=True)
```

### Add Filters

Allow users to filter by team, region, etc:

```python
# In sidebar
team_filter = st.multiselect(
    "Filter by Team",
    options=df['Team'].unique(),
    default=df['Team'].unique()
)

# Filter dataframe
filtered_df = df[df['Team'].isin(team_filter)]
```

### Schedule Automated Emails

Use `schedule` library to send daily/weekly reports:

```python
pip install schedule

# Create a separate script to email reports
import schedule
import time

def send_report():
    # Generate report
    # Email it using smtplib or SendGrid
    pass

schedule.every().day.at("08:00").do(send_report)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Add Historical Trends

Track performance over time:

```python
# Store daily snapshots in a database
# Plot trends over weeks/months
# Compare current vs previous periods
```

## Performance Optimization

### Use Caching

Add caching to reduce API calls:

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_closed_won_amount(sf, owner_id, start_date, end_date):
    # ... existing code
```

### Bulk Queries

Instead of querying per AE, query all at once:

```python
def get_all_closed_won(sf, ae_ids, start_date, end_date):
    """Get closed won for all AEs in one query"""
    ids_str = "','".join(ae_ids)
    query = f"""
        SELECT OwnerId, SUM(Amount) totalAmount
        FROM Opportunity
        WHERE OwnerId IN ('{ids_str}')
        AND StageName = 'Closed Won'
        AND CloseDate >= {start_date}
        AND CloseDate <= {end_date}
        GROUP BY OwnerId
    """
    result = sf.query(query)
    return {r['OwnerId']: r['totalAmount'] for r in result['records']}
```

## Security Best Practices

1. **Never commit credentials**
   - Use `.gitignore` for secrets
   - Use environment variables in production

2. **Use OAuth instead of password**
   - More secure than username/password
   - Easier to revoke access

3. **Implement user authentication**
   - Add login to your Streamlit app
   - Restrict access to authorized users

4. **Enable HTTPS**
   - Always use SSL in production
   - Especially important for cloud deployments

5. **Rotate credentials regularly**
   - Change security token periodically
   - Use different credentials for dev/prod

## Next Steps

1. **Test with your data** - Run locally first
2. **Customize queries** - Adjust to match your Salesforce setup
3. **Add visualizations** - Include charts for better insights
4. **Deploy** - Choose deployment option based on needs
5. **Gather feedback** - Share with AE team and iterate

## Support Resources

- Streamlit Docs: https://docs.streamlit.io
- Simple Salesforce: https://github.com/simple-salesforce/simple-salesforce
- Salesforce SOQL: https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta
- Streamlit Community: https://discuss.streamlit.io

## Comparison: Streamlit vs Native Salesforce

| Feature | Streamlit | Native Salesforce |
|---------|-----------|-------------------|
| Development Speed | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐ Moderate |
| Customization | ⭐⭐⭐⭐⭐ Highly flexible | ⭐⭐⭐ Limited by platform |
| Deployment | ⭐⭐⭐⭐ Easy (external) | ⭐⭐⭐⭐⭐ Integrated |
| User Access | ⭐⭐⭐ Separate login | ⭐⭐⭐⭐⭐ SSO built-in |
| Data Freshness | ⭐⭐⭐⭐ Real-time API | ⭐⭐⭐⭐⭐ Native queries |
| Cost | ⭐⭐⭐⭐⭐ Free/low cost | ⭐⭐⭐ License dependent |
| Maintenance | ⭐⭐⭐ External app | ⭐⭐⭐⭐ Platform managed |

**Choose Streamlit if:**
- You want rapid prototyping
- Need advanced analytics/visualizations
- Have limited Salesforce customization rights
- Want to iterate quickly

**Choose Native Salesforce if:**
- Need tight Salesforce integration
- Want single sign-on experience
- Have Salesforce development resources
- Require embedded dashboards in Salesforce UI
