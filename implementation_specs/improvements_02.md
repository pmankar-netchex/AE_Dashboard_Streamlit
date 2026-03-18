#Implement the fixes

<fix-01: dummy-values>
Test method on SOQL management page breaks becayse it tries with DUMMY_ID, and ther's no place to put that information. Give option to select one of the owner as dummy_id from the dropdown on this page.
</fix-01: dummy-values>

<fix-02: query-resu>
show test query result as well, to see if it returned some valid data.
</fix-02: dummy-values>

<fix-03: soql_fixes>
    - ForecastingQuota object doesn't support OwnerId instead use QuotaOwnerId as OwnerId
    - Opportunity Invalid ID field because of DUMMY_ID, give option to add dummy ID
    - StageName format is Closed/Won, Closed/Lost - this is incorrect in queries
    - In tasks object there is no owner instead there is Assigned_ID_Custom__c which is OwnerId
    - In Events object use Type and EvenetSubtype instead of Type__c
    - In Events object use Assigned_ID_Custom__c as OwnerId
</fix-03: soql_fixes>