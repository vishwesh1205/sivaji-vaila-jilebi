"""Initialise or reset the local educational demo database.

Usage:
    python -m app.seed
    python -m app.seed --reset
    python -m app.seed --reset --no-seed
"""
from __future__ import annotations

import argparse

from . import db


def complaint_count() -> int:
    with db.connect() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM demo_complaints").fetchone()["c"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed or reset CPGRAMS demo data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all local demo records and restore the three seeded examples.",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="With --reset, leave the database empty instead of restoring examples.",
    )
    args = parser.parse_args()

    if args.reset:
        created = db.reset_database(seed=not args.no_seed)
        action = "reset"
    else:
        db.init_database()
        created = 0
        action = "initialised"

    print(f"Database {action}: {db.db_path()}")
    print(f"Seeded records inserted: {created}")
    print(f"Complaint records now present: {complaint_count()}")
    print("This database is local and synthetic. No real grievance data is used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
