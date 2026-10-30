from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "cpgrams_demo.db"
DEFAULT_UPLOAD_DIR = ROOT / "data" / "uploads"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat(timespec="seconds")


def database_url() -> str:
    return os.environ.get("CPGRAMS_DB_URL", "").strip()


def db_path() -> Path:
    configured = os.environ.get("CPGRAMS_DB_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.environ.get("VERCEL"):
        return Path("/tmp/cpgrams_demo.db")
    return DEFAULT_DB_PATH


def upload_dir() -> Path:
    configured = os.environ.get("CPGRAMS_UPLOAD_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.environ.get("VERCEL"):
        return Path("/tmp/cpgrams-demo-uploads")
    return DEFAULT_UPLOAD_DIR


class _DictRow(dict):
    """dict row with sqlite3.Row-compatible numeric indexing."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _LibsqlCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def _row(self, row):
        if row is None:
            return None
        if isinstance(row, dict):
            return _DictRow(row)
        columns = [item[0] for item in (self._cursor.description or [])]
        return _DictRow(zip(columns, row))

    def fetchone(self):
        return self._row(self._cursor.fetchone())

    def fetchall(self):
        return [self._row(row) for row in self._cursor.fetchall()]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        return [self._row(row) for row in rows]

    def __iter__(self):
        return (self._row(row) for row in self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _LibsqlConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, parameters=()):
        return _LibsqlCursor(self._connection.execute(sql, parameters))

    def executemany(self, sql, parameters):
        return _LibsqlCursor(self._connection.executemany(sql, parameters))

    def executescript(self, script):
        self._connection.executescript(script)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False


def connect():
    url = database_url()
    if url:
        try:
            import libsql
        except ImportError as exc:
            raise RuntimeError(
                "CPGRAMS_DB_URL is set but the libsql package is not installed. "
                "Install it with: pip install libsql"
            ) from exc
        raw = libsql.connect(
            url,
            auth_token=os.environ.get("CPGRAMS_DB_AUTH_TOKEN", ""),
            timeout=30.0,
        )
        return _LibsqlConnection(raw)
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Use BEGIN IMMEDIATE to serialise reference-number allocation."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


SCHEMA = """
CREATE TABLE IF NOT EXISTS demo_complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_number TEXT NOT NULL UNIQUE,
    complainant_ref TEXT NOT NULL,
    subject TEXT NOT NULL,
    category TEXT NOT NULL,
    organisation TEXT NOT NULL,
    region TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    attachment_name TEXT,
    attachment_stored TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    is_seeded INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    dashboard_sync_status TEXT NOT NULL DEFAULT 'disabled',
    dashboard_sync_error TEXT,
    dashboard_case_ref TEXT
);

CREATE INDEX IF NOT EXISTS ix_demo_complaints_created ON demo_complaints(created_at);
CREATE INDEX IF NOT EXISTS ix_demo_complaints_status ON demo_complaints(status);

CREATE TABLE IF NOT EXISTS demo_complaint_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES demo_complaints(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_demo_events_complaint ON demo_complaint_events(complaint_id, created_at);

CREATE TABLE IF NOT EXISTS demo_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES demo_complaints(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS demo_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_ref TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email TEXT,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS form_tokens (
    token TEXT PRIMARY KEY,
    purpose TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    result_ref TEXT
);

CREATE TABLE IF NOT EXISTS reference_sequences (
    year INTEGER PRIMARY KEY,
    last_value INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dashboard_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL UNIQUE REFERENCES demo_complaints(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


SEED_COMPLAINTS = [
    {
        "registration_number": "CPGRAMS-DEMO-{year}-00001",
        "complainant_ref": "DEMO-CITIZEN-001",
        "subject": "Delay in issue of income certificate",
        "category": "Revenue & Certificates",
        "organisation": "Department of Revenue",
        "region": "Tamil Nadu",
        "description": (
            "This is a fictional demonstration record. An application for an income "
            "certificate was submitted at the local taluk office in August. The "
            "acknowledgement slip was issued, but the certificate has not been delivered "
            "and the online status still shows 'pending'. A written reminder was also "
            "submitted. The demo complainant is requesting an update and a clear next step."
        ),
        "status": "Closed — Demo",
        "created_at": "{year}-09-12T09:30:00+00:00",
        "updated_at": "{year}-09-27T11:10:00+00:00",
        "events": [
            ("RECEIVED", "Demo grievance received and acknowledged locally.", "{year}-09-12T09:30:00+00:00"),
            ("FORWARDED", "Assigned to the demo Department of Revenue desk.", "{year}-09-13T10:05:00+00:00"),
            ("UNDER_REVIEW", "Demo reviewing officer requested the application details.", "{year}-09-18T14:20:00+00:00"),
            ("CLOSED", "Demo response recorded: certificate marked ready for collection. No real certificate was issued.", "{year}-09-27T11:10:00+00:00"),
        ],
    },
    {
        "registration_number": "CPGRAMS-DEMO-{year}-00002",
        "complainant_ref": "DEMO-CITIZEN-002",
        "subject": "Pension papers not processed after retirement",
        "category": "Pension & Retirement",
        "organisation": "Department of Pension & Pensioners' Welfare",
        "region": "Delhi",
        "description": (
            "This is fictional demonstration data. A pension file was submitted after "
            "retirement with all sample documents. The complainant has received no "
            "acknowledgement and the demo status has not changed for several weeks. "
            "This record exists only to demonstrate how a pending grievance and its "
            "timeline appear in the portal."
        ),
        "status": "Under Process — Demo",
        "created_at": "{year}-10-02T08:45:00+00:00",
        "updated_at": "{year}-10-16T12:30:00+00:00",
        "events": [
            ("RECEIVED", "Demo grievance received and acknowledged locally.", "{year}-10-02T08:45:00+00:00"),
            ("FORWARDED", "Forwarded to the simulated pension processing desk.", "{year}-10-03T09:15:00+00:00"),
            ("UNDER_REVIEW", "Demo officer marked the file as under process.", "{year}-10-16T12:30:00+00:00"),
        ],
    },
    {
        "registration_number": "CPGRAMS-DEMO-{year}-00003",
        "complainant_ref": "DEMO-CITIZEN-003",
        "subject": "Streetlight repair request pending for three weeks",
        "category": "Municipal Services",
        "organisation": "Municipal Administration",
        "region": "Karnataka",
        "description": (
            "This is fictional demonstration data. A streetlight near a residential "
            "crossing stopped working three weeks ago. A demo request was logged with "
            "the municipal helpline and a photograph was described in the complaint. "
            "No repair has been recorded. This example shows a newly received grievance."
        ),
        "status": "Received — Demo",
        "created_at": "{year}-10-20T17:05:00+00:00",
        "updated_at": "{year}-10-20T17:05:00+00:00",
        "events": [
            ("RECEIVED", "Demo grievance received and acknowledged locally.", "{year}-10-20T17:05:00+00:00"),
        ],
    },
]


def seed_database(conn: sqlite3.Connection, force_year: int | None = None) -> int:
    """Insert demo records only when the complaints table is empty."""
    existing = conn.execute("SELECT COUNT(*) AS c FROM demo_complaints").fetchone()["c"]
    if existing:
        return 0

    year = force_year or utcnow().year
    created = 0
    for seed in SEED_COMPLAINTS:
        reg = seed["registration_number"].format(year=year)
        cur = conn.execute(
            """
            INSERT INTO demo_complaints (
                registration_number, complainant_ref, subject, category, organisation,
                region, description, status, idempotency_key, is_seeded, created_at,
                updated_at, dashboard_sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'disabled')
            """,
            (
                reg,
                seed["complainant_ref"],
                seed["subject"],
                seed["category"],
                seed["organisation"],
                seed["region"],
                seed["description"],
                seed["status"],
                f"seed:{reg}",
                seed["created_at"].format(year=year),
                seed["updated_at"].format(year=year),
            ),
        )
        complaint_id = cur.lastrowid
        for event_type, description, when in seed["events"]:
            conn.execute(
                "INSERT INTO demo_complaint_events (complaint_id, event_type, description, created_at) VALUES (?, ?, ?, ?)",
                (complaint_id, event_type, description, when.format(year=year)),
            )
        created += 1

    conn.execute(
        "INSERT INTO reference_sequences (year, last_value) VALUES (?, ?) "
        "ON CONFLICT(year) DO UPDATE SET last_value = MAX(last_value, excluded.last_value)",
        (year, created),
    )
    conn.commit()
    return created


def init_database() -> None:
    upload_dir().mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Remove stale, unused form tokens after two days; harmless housekeeping.
        cutoff = (utcnow() - timedelta(days=2)).isoformat(timespec="seconds")
        conn.execute("DELETE FROM form_tokens WHERE used = 0 AND created_at < ?", (cutoff,))
        seed_database(conn)


def reset_database(seed: bool = True) -> int:
    upload_dir().mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        stored_attachments = [
            row["attachment_stored"]
            for row in conn.execute(
                "SELECT attachment_stored FROM demo_complaints WHERE attachment_stored IS NOT NULL"
            ).fetchall()
        ]
        for table in (
            "demo_feedback",
            "demo_complaint_events",
            "dashboard_outbox",
            "demo_complaints",
            "demo_users",
            "form_tokens",
            "reference_sequences",
            "contact_messages",
        ):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
        for stored in stored_attachments:
            path = upload_dir() / Path(stored).name
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        return seed_database(conn) if seed else 0


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
