<fix01: soql_fixes>
- In the Task object, 
    - Use IsClosed=true to see if it's actually completed
    - Use Type as ActivityType
    - Use OwnerId filtering task

</fix01: soql_fixes>

<fix02: ui_fixes>
- I need heatmaps in tables to highlight best and worst performing scales
    - use lighter colors for better readablity
    - read column description to make sense is positive numbers is good or negative number is good
    - Search AE remove this as there is AE name filter already
    - Add AE Manager to the tables
    - Rows per page,Page shouldn't be pagewide - maybe move them to the left bar, taking too much space
    - Use Playwright MCP to check UX experience and improve as per the proper production dashbaord standards
</fix02: ui_fixes>

<fix03: calculation_errors>
- Closed Won (Period) should change as per period
</fix03: calculation_errors>