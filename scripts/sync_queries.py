#!/usr/bin/env python3
"""Sync SOQL templates between Azure Table Storage and queries_snapshot.json.

Modes:
  --export   Table -> queries_snapshot.json (run before git push / deploy)
  --import   queries_snapshot.json -> Table (disaster recovery)
  --diff     Show pending changes without writing anywhere
  --check    Exit 1 if table and snapshot disagree (for CI / pre-push hook)

Requires env var: AZURE_STORAGE_CONNECTION_STRING
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "queries_snapshot.json"
TABLE_NAME = "queries"
PARTITION = "soql"


def _table_client():
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        sys.exit("ERROR: AZURE_STORAGE_CONNECTION_STRING not set")
    try:
        from azure.data.tables import TableServiceClient
    except ImportError:
        sys.exit("ERROR: pip install azure-data-tables")
    return TableServiceClient.from_connection_string(conn).get_table_client(TABLE_NAME)


def _read_table() -> dict[str, str]:
    client = _table_client()
    return {
        e["RowKey"]: e.get("Template", "")
        for e in client.query_entities(f"PartitionKey eq '{PARTITION}'")
    }


def _read_snapshot() -> dict[str, str]:
    if not SNAPSHOT_PATH.exists():
        return {}
    return json.loads(SNAPSHOT_PATH.read_text())


def _write_snapshot(data: dict[str, str]) -> None:
    ordered = {k: data[k] for k in sorted(data)}
    SNAPSHOT_PATH.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")


def _diff(a: dict[str, str], b: dict[str, str]) -> list[str]:
    lines = []
    for k in sorted(set(a) | set(b)):
        av, bv = a.get(k), b.get(k)
        if av == bv:
            continue
        if av is None:
            lines.append(f"  + {k}  (only in b)")
        elif bv is None:
            lines.append(f"  - {k}  (only in a)")
        else:
            lines.append(f"  ~ {k}  (differs)")
    return lines


def do_export() -> int:
    table = _read_table()
    snapshot = _read_snapshot()
    changes = _diff(snapshot, table)
    _write_snapshot(table)
    if changes:
        print(f"Updated {SNAPSHOT_PATH.name} ({len(changes)} change(s)):")
        print("\n".join(changes))
        return 0
    print(f"{SNAPSHOT_PATH.name} up to date ({len(table)} rows).")
    return 0


def do_import() -> int:
    snapshot = _read_snapshot()
    if not snapshot:
        sys.exit(f"ERROR: {SNAPSHOT_PATH.name} missing or empty")
    table = _read_table()
    client = _table_client()
    n_upsert = 0
    for col_id, template in snapshot.items():
        if table.get(col_id) == template:
            continue
        client.upsert_entity({
            "PartitionKey": PARTITION,
            "RowKey": col_id,
            "Template": template,
        })
        n_upsert += 1
    print(f"Upserted {n_upsert} row(s) into {TABLE_NAME}.")
    return 0


def do_diff() -> int:
    table = _read_table()
    snapshot = _read_snapshot()
    changes = _diff(snapshot, table)
    if not changes:
        print(f"No differences ({len(table)} rows).")
        return 0
    print(f"Differences (snapshot -> table):")
    print("\n".join(changes))
    return 0


def do_check() -> int:
    table = _read_table()
    snapshot = _read_snapshot()
    changes = _diff(snapshot, table)
    if changes:
        print("ERROR: queries_snapshot.json is out of sync with Table Storage:")
        print("\n".join(changes))
        print("\nRun: python scripts/sync_queries.py --export && git add queries_snapshot.json")
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--export", action="store_true", help="Table -> snapshot")
    g.add_argument("--import", dest="do_import_flag", action="store_true", help="Snapshot -> table")
    g.add_argument("--diff", action="store_true", help="Show differences")
    g.add_argument("--check", action="store_true", help="Exit 1 if out of sync (CI / hook)")
    args = p.parse_args()
    if args.export:
        return do_export()
    if args.do_import_flag:
        return do_import()
    if args.diff:
        return do_diff()
    if args.check:
        return do_check()
    return 1


if __name__ == "__main__":
    sys.exit(main())
