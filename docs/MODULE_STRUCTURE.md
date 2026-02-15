# Dashboard Module Structure

Clean, modular architecture for easy customization.

## Architecture

```
AE_Dashboard_Streamlit/
├── streamlit_dashboard.py         # Main entry point (293 lines)
├── src/
│   ├── salesforce_queries.py      # ⚙️ SOQL queries by entity (195 lines)
│   ├── dashboard_calculations.py  # ⚙️ Business logic & formulas (118 lines)
│   ├── dashboard_ui.py            # ⚙️ Display & styling (183 lines)
│   └── salesforce_oauth.py        # OAuth 2.0 flow (127 lines)
├── scripts/
│   ├── setup.sh                   # Setup script
│   ├── run.sh                     # Run script
│   └── .env.example               # Config template
├── docs/
│   ├── CUSTOMIZATION_GUIDE.md     # How to customize
│   ├── MODULE_STRUCTURE.md        # This file
│   ├── SALESFORCE_CONNECTED_APP_SETUP.md
│   └── STREAMLIT_SETUP_GUIDE.md
├── .env                           # Your credentials (gitignored)
└── requirements.txt               # Python deps
```

## What Goes Where

| Change | File | Function/Line |
|--------|------|---------------|
| Closed Won stage | `src/salesforce_queries.py` | Line 79 |
| User profile filter | `src/salesforce_queries.py` | Line 23 |
| Meeting keywords | `src/salesforce_queries.py` | Line 143 |
| RecordType filter | `src/salesforce_queries.py` | Add to line 80/94 |
| Quota formula | `src/dashboard_calculations.py` | Line 55 |
| Meetings formula | `src/dashboard_calculations.py` | Line 17 |
| Dashboard colors | `src/dashboard_ui.py` | Line 13 (CSS) |
| Currency format | `src/dashboard_ui.py` | Line 69 |
| Add metrics | `src/dashboard_ui.py` | Line 99 |
| Add charts | `src/dashboard_ui.py` | Line 121 |

## Benefits

**Before (1 file, 527 lines):**
- Hard to find specific queries
- Business logic mixed with UI
- Changes affect entire file

**After (4 modules, ~293 lines max):**
- ✅ SOQL queries grouped by entity
- ✅ Business logic separate from display
- ✅ Customize one area without touching others
- ✅ Comments explain each section

## Customization Flow

1. **Identify what to change** (see table above)
2. **Open the relevant file** (e.g. `salesforce_queries.py`)
3. **Find the section** (comments mark each entity/use case)
4. **Edit and save** (Streamlit auto-reloads)

See [CUSTOMIZATION_GUIDE.md](CUSTOMIZATION_GUIDE.md) for detailed examples.
