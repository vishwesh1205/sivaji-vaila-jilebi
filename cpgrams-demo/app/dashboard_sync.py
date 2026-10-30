"""Retry pending complaints against the existing local dashboard.

Usage:
    python -m app.dashboard_sync
    python -m app.dashboard_sync --limit 10

Requires DASHBOARD_INGEST_URL and usually DASHBOARD_BEARER_TOKEN.
"""
from __future__ import annotations

import argparse
import sys

from . import dashboard_adapter, db


def main() -> int:
    parser = argparse.ArgumentParser(description="Retry pending dashboard outbox records.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum records to retry (1-200).")
    args = parser.parse_args()
    limit = max(1, min(args.limit, 200))

    settings = dashboard_adapter.config()
    if not settings["enabled"]:
        print("Dashboard integration is disabled: set DASHBOARD_INGEST_URL first.", file=sys.stderr)
        return 2

    db.init_database()
    with db.connect() as conn:
        results = dashboard_adapter.sync_pending(conn, limit=limit)

    if not results:
        print("No pending dashboard records to retry.")
        return 0
    for result in results:
        line = f"{result['complaint']}: {result['status']}"
        if result.get("error"):
            line += f" ({result['error']})"
        print(line)
    failed = sum(1 for result in results if result["status"] != "synced")
    print(f"Synced {len(results) - failed} of {len(results)} pending records.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
