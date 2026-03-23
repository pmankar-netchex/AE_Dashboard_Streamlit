import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    _env = Path(__file__).resolve().parent
    load_dotenv(_env.parent / ".env")
    load_dotenv(_env / ".env")
except ImportError:
    pass  # DOL_API_KEY from os.environ only

def get_datasets():
    collect = []
    page = 1
    while True:
        url = f"https://apiprod.dol.gov/v4/datasets?page={page}"
        response = requests.get(url)
        datasets_api_json = response.json()["datasets"]
        if not datasets_api_json:
            break
        collect.append(pd.DataFrame(datasets_api_json))
        page += 1
    return pd.concat(collect, ignore_index=True)

# def get_whd_enforcement_fl(api_key: Optional[str] = None, limit: int = 5000):
#     """Fetch WHD enforcement data filtered by act_id = FL (Fair Labor Standards Act)."""
#     # filter_object = {
#     #     "field": "act_id",
#     #     "operator": "eq",
#     #     "value": "WHD",
#     # }
#     # url = "https://apiprod.dol.gov/v4/get/WHD/enforcement/json"
#     # params = {
#     #     "filter_object": json.dumps(filter_object),
#     #     "limit": limit,
#     #     "offset": 0,
#     # }
#     # if api_key:
#     #     params["X-API-KEY"] = api_key  # ✅ Correct — key goes in query params per DOL docs
#     url = "https://apiprod.dol.gov/v4/get/WHD/enforcement/json"
#     r = requests.get(url, params={"X-API-KEY": api_key, "limit": 5})
#     print(r.status_code)
#     print(r.json())
#     # response = requests.get(url, params=params)
#     # if not response.ok:
#     #     body = response.text[:500] if response.text else "(empty)"
#     #     raise RuntimeError(
#     #         f"DOL API error {response.status_code}: {response.reason}\nResponse: {body}"
#     #     )
#     # data = response.json()
#     # if isinstance(data, dict) and "results" in data:
#     #     return pd.DataFrame(data["results"])
#     # if isinstance(data, list):
#     #     return pd.DataFrame(data)
#     # return pd.DataFrame(data)


# Rate limit: delay between paginated requests (seconds). DOL is strict; use 5–10s to avoid 429.
_WHD_REQUEST_DELAY = 6.0
# On 429, retry with long backoff; use Retry-After header if present
_WHD_429_MAX_RETRIES = 8
_WHD_429_BASE_WAIT = 60  # seconds before first retry


def _whd_enforcement_raw(
    api_key: Optional[str], limit: int, offset: int = 0, filter_object: Optional[dict] = None
):
    """Single request to WHD enforcement API. Retries on 429 with long backoff."""
    url = "https://apiprod.dol.gov/v4/get/WHD/enforcement/json"
    params = {"limit": limit, "offset": offset}
    if filter_object is not None:
        params["filter_object"] = json.dumps(filter_object)
    if api_key:
        params["X-API-KEY"] = api_key
    last_status, last_err = None, None
    for attempt in range(_WHD_429_MAX_RETRIES):
        response = requests.get(url, params=params)
        if response.status_code == 429:
            # Prefer Retry-After header (seconds or HTTP-date)
            wait = _WHD_429_BASE_WAIT * (attempt + 1)  # 60, 120, 180, ...
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = int(retry_after)
                except ValueError:
                    pass  # could be HTTP-date; keep our backoff
            print(
                "Rate limited (429). Waiting %ds before retry %d/%d..."
                % (wait, attempt + 1, _WHD_429_MAX_RETRIES),
                file=sys.stderr,
            )
            time.sleep(wait)
            last_status, last_err = 429, response.text[:500]
            continue
        if not response.ok:
            return None, response.status_code, response.text[:500]
        text = response.text.strip()
        if not text:
            return None, response.status_code, "(empty)"
        try:
            return response.json(), response.status_code, None
        except ValueError:
            return None, response.status_code, text[:500]
    return None, last_status or 429, last_err or "Too Many Requests"


# DOL API max response is 6 MB; use small pages to stay under.
_WHD_PAGE_SIZE = 500


def get_whd_enforcement_fl(
    api_key: Optional[str] = None,
    limit: int = 10000,
    findings_start_date: Optional[str] = None,
    findings_end_date: Optional[str] = None,
):
    """WHD enforcement filtered by act_id = FL (Fair Labor Standards Act).
    Optionally filter by findings date range in API to reduce payload (e.g. '2025-01-01', '2025-12-31').
    """
    # Pause before WHD so we don't hit rate limit right after datasets requests
    time.sleep(3)
    # Build API filter: act_id=fl and optionally date range (all lowercase per API)
    if findings_start_date and findings_end_date:
        filter_object = {
            "and": [
                {"field": "act_id", "operator": "eq", "value": "fl"},
                {"field": "findings_start_date", "operator": "lte", "value": findings_end_date},
                {"field": "findings_end_date", "operator": "gte", "value": findings_start_date},
            ]
        }
    else:
        filter_object = {"field": "act_id", "operator": "eq", "value": "fl"}
    data, status, err = _whd_enforcement_raw(api_key, limit=limit, filter_object=filter_object)
    _filter_dates_in_python = False
    if data is None and status == 500 and findings_start_date and findings_end_date:
        # API may reject combined filter; try act_id only, then filter dates in Python
        filter_object = {"field": "act_id", "operator": "eq", "value": "fl"}
        data, status, err = _whd_enforcement_raw(api_key, limit=limit, filter_object=filter_object)
        _filter_dates_in_python = True
    if data is None and status == 500:
        # Filter causes 500: paginate without filter (small pages to avoid 413), then filter in Python
        _filter_dates_in_python = bool(findings_start_date and findings_end_date)
        pages = []
        offset = 0
        page_size = _WHD_PAGE_SIZE
        while offset < limit:
            data, status, err = _whd_enforcement_raw(
                api_key, limit=page_size, offset=offset, filter_object=None
            )
            if data is None:
                if status == 413 and page_size > 100:
                    page_size = max(100, page_size // 2)
                    continue
                raise RuntimeError(f"DOL API error {status}: {err}")
            df_page = _parse_whd_response(data)
            if df_page.empty and offset == 0 and isinstance(data, dict):
                # Probe: show response shape so we can fix the parser
                print("DOL WHD response top-level keys:", list(data.keys()), file=sys.stderr)
                for k, v in data.items():
                    if isinstance(v, list) and v:
                        print("First item keys (under %r):" % k, list(v[0].keys())[:20], file=sys.stderr)
                        break
            if df_page.empty:
                break
            pages.append(df_page)
            if len(df_page) < page_size:
                break
            offset += len(df_page)
            time.sleep(_WHD_REQUEST_DELAY)  # avoid 429 rate limit
        df = pd.concat(pages, ignore_index=True) if pages else pd.DataFrame()
        if df.empty:
            return df
        act_col = next((c for c in ("act_id", "act", "actid") if c in df.columns), None)
        if act_col:
            df = df[df[act_col].astype(str).str.lower().str.strip() == "fl"].reset_index(drop=True)
        return df
    if data is None:
        raise RuntimeError(f"DOL API error {status}: {err}")
    df = _parse_whd_response(data)

    return df


def _parse_whd_response(data):
    """Turn API response into a DataFrame. Handles results/data/dataset/list."""
    if isinstance(data, list):
        return pd.DataFrame(data)
    if not isinstance(data, dict):
        return pd.DataFrame()
    for key in ("results", "data", "dataset", "records"):
        if key in data and isinstance(data[key], list):
            return pd.DataFrame(data[key])
    # Single key that is a list (e.g. {"enforcement": [...]})
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return pd.DataFrame(v)
    return pd.DataFrame()

# --- Datasets list ---
datasets = get_datasets()
# API uses 'name' for dataset name; show requested columns
df = datasets.rename(columns={"name": "dataset_name"})
cols = [c for c in ["agency", "dataset_name", "api_url", "category"] if c in df.columns]
# print("=== DOL datasets ===\n")
# print(df[cols].to_string())

# Columns useful for lead gen (company, contact, business) + violation details (order preserved)
_WHD_LEADGEN_COLUMNS = [
    # Company / employer
    "legal_name",
    "trade_nm",
    "trade_name",
    "trade_name_1",
    "name",
    "employer_name",
    "business_name",
    "estab_name",
    "company_name",
    # Address
    "street_addr_1_txt",
    "street_addr_1",
    "street_address",
    "addr_1",
    "street_1",
    "city_nm",
    "city",
    "st_cd",
    "state",
    "state_cd",
    "zip_cd",
    "zip_code",
    "zip",
    # Contact / identifier (including EIN)
    "ein",
    "ein_num",
    "employer_ein",
    "fein",
    "federal_ein",
    "tax_id",
    "ctrctr_ein",
    "case_id",
    "case_num",
    "case_number",
    "ref_no",
    "ctrctr_num",
    "contractor_num",
    # Business / industry
    "naics_cd",
    "naics_code",
    "naics",
    "sic_cd",
    "sic_code",
    "industry_cd",
    "industry",
    "bus_type_cd",
    "business_type",
    "act_id",
    "act",
    # Violation / finding details
    "find_start_dt",
    "find_end_dt",
    "finding_date",
    "find_dt",
    "violation_type",
    "viol_typ_cd",
    "bw_atp_amt",
    "back_wage_amt",
    "back_wages",
    "emp_due_bw_cnt",
    "employees_due_bw",
    "cmp_assessed_amt",
    "civil_penalty",
    "cmp_amt",
    "flsa_viol_cnt",
    "violation_cnt",
    "flsa_repeat_violator",
    "repeat_violator",
]

# --- WHD enforcement (Fair Labor Standards Act) ---
dol_api_key = os.environ.get("DOL_API_KEY") or None
# 2025 date filter applied in API to reduce payload; fallback filter in Python if API rejects it
whd_fl = get_whd_enforcement_fl(
    api_key=dol_api_key,
    limit=10,  # sample of 10; increase for full pull
    findings_start_date="2023-01-01",
    findings_end_date="2025-12-31",
)

# Pick lead-gen + violation columns that exist; add any remaining columns
if not whd_fl.empty:
    existing_preferred = [c for c in _WHD_LEADGEN_COLUMNS if c in whd_fl.columns]
    other_cols = [c for c in whd_fl.columns if c not in existing_preferred]
    whd_fl_out = whd_fl[existing_preferred + other_cols]
else:
    whd_fl_out = whd_fl

# Write CSV
_csv_path = Path(__file__).resolve().parent / "whd_fl_enforcement.csv"
whd_fl_out.to_csv(_csv_path, index=False, encoding="utf-8")
print("\n=== WHD enforcement (act_id=FL, Fair Labor Standards Act) ===\n")
print("CSV written: %s (%d rows, %d columns)" % (_csv_path, len(whd_fl_out), len(whd_fl_out.columns)))
if not whd_fl_out.empty:
    print("\nColumns included:", list(whd_fl_out.columns))
print(whd_fl_out.to_string())
