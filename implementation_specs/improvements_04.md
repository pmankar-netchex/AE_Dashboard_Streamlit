<fix01-performance-issues>
- Do not retry in case of "malformed queries" or similar query related error code.
</fix01-performance-issues>

<fix02-soql-issues>
- In task object,  use OwnerId for owner filtering OwnerLogic "Find SDRs from AEEmail field in the User table, and then search for those owner. e.g for Alec Ducan as AE find all SDRs from User object where AEEmail = Alec Ducan's email, and then filter by Ids of those SDRs as owner IDs"
- For Event object - use OwnerId for owner filtering OwnerLogic "Find SDRs from AEEmail field in the User table, and then search for those owner. e.g for Alec Ducan as AE find all SDRs from User object where AEEmail = Alec Ducan's email, and then filter by Ids of those SDRs as owner IDs"
- In tasks object, for hubspot creation use field IsCreatedbyHighspot__c=true
- Subject NOT LIKE '%Gong In%' type of queries are failing for Subject LIKE '%Gong In%' works
- ('Employee Benefits Broker','CPA','Retirement Broker','Financial Advisor','Fractional Executive','Bank','Advisor / Consultant')information exists on Contact Type not on Event Type
</fix02-soql-issues>