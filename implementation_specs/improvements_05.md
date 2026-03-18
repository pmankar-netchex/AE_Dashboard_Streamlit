<SOQL-fixes>
1. use OwnerId for owner clause in Events
2. Filter AEs where User_Role_Formula__c contains 'Sales Rep' but doesn't contain SDR or Account
3. All AEs have Assigned_SDR_Outbound__c field in User object which tells corresponding SDR use this field to find SDR activities for columns T,U,V,W
4. For COlumns X,Y,Z,AA remove highspot condition and add  AND CreatedBy.Name != 'Hubspot Integration' condition
</SOQL-fixes>