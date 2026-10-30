from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from . import db
from .services import STATUSES, normalise_complainant, normalise_reference


class InvalidFormToken(Exception):
    pass


def create_form_token(conn: sqlite3.Connection, purpose: str) -> str:
    token = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO form_tokens (token, purpose, created_at) VALUES (?, ?, ?)",
        (token, purpose, db.utcnow_iso()),
    )
    conn.commit()
    return token


def _allocate_reference(conn: sqlite3.Connection) -> str:
    year = db.utcnow().year
    row = conn.execute(
        "SELECT last_value FROM reference_sequences WHERE year = ?", (year,)
    ).fetchone()
    next_value = (row["last_value"] if row else 0) + 1
    conn.execute(
        "INSERT INTO reference_sequences (year, last_value) VALUES (?, ?) "
        "ON CONFLICT(year) DO UPDATE SET last_value = excluded.last_value",
        (year, next_value),
    )
    return f"CPGRAMS-DEMO-{year}-{next_value:05d}"


def create_complaint(
    conn: sqlite3.Connection,
    cleaned: dict[str, str],
    token: str,
    attachment_name: str | None = None,
    attachment_stored: str | None = None,
) -> tuple[dict[str, Any], bool]:
    now = db.utcnow_iso()
    with db.transaction(conn):
        token_row = conn.execute(
            "SELECT token, purpose, used, result_ref FROM form_tokens WHERE token = ?", (token,)
        ).fetchone()
        if token_row is None or token_row["purpose"] != "grievance":
            raise InvalidFormToken("This submission form has expired. Please open the form again.")

        if token_row["used"]:
            existing = conn.execute(
                "SELECT * FROM demo_complaints WHERE registration_number = ?",
                (token_row["result_ref"],),
            ).fetchone()
            if existing is None:
                raise InvalidFormToken("This submission has already been processed.")
            return dict(existing), False

        reference = _allocate_reference(conn)
        cur = conn.execute(
            """
            INSERT INTO demo_complaints (
                registration_number, complainant_ref, subject, category, organisation,
                region, description, status, attachment_name, attachment_stored,
                idempotency_key, is_seeded, created_at, updated_at, dashboard_sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 'pending')
            """,
            (
                reference,
                cleaned["complainant_ref"],
                cleaned["subject"],
                cleaned["category"],
                cleaned["organisation"],
                cleaned["region"],
                cleaned["description"],
                STATUSES["RECEIVED"],
                attachment_name,
                attachment_stored,
                f"form:{token}",
                now,
                now,
            ),
        )
        complaint_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO demo_complaint_events (complaint_id, event_type, description, created_at) "
            "VALUES (?, 'RECEIVED', ?, ?)",
            (
                complaint_id,
                "Grievance received by the local educational demo. No real government office was contacted.",
                now,
            ),
        )
        conn.execute(
            "INSERT INTO dashboard_outbox (complaint_id, status, attempt_count, created_at) VALUES (?, 'PENDING', 0, ?)",
            (complaint_id, now),
        )
        conn.execute(
            "UPDATE form_tokens SET used = 1, result_ref = ? WHERE token = ?", (reference, token)
        )
        row = conn.execute(
            "SELECT * FROM demo_complaints WHERE id = ?", (complaint_id,)
        ).fetchone()
        return dict(row), True


def get_complaint(conn: sqlite3.Connection, reference: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM demo_complaints WHERE registration_number = ?",
        (normalise_reference(reference),),
    ).fetchone()
    return dict(row) if row else None


def get_complaint_by_id(conn: sqlite3.Connection, complaint_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM demo_complaints WHERE id = ?", (complaint_id,)).fetchone()
    return dict(row) if row else None


def get_verified_complaint(
    conn: sqlite3.Connection, reference: str, verification: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM demo_complaints WHERE registration_number = ? AND UPPER(complainant_ref) = ?",
        (normalise_reference(reference), normalise_complainant(verification)),
    ).fetchone()
    return dict(row) if row else None


def get_events(conn: sqlite3.Connection, complaint_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM demo_complaint_events WHERE complaint_id = ? ORDER BY created_at ASC, id ASC",
        (complaint_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_feedback(conn: sqlite3.Connection, complaint_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM demo_feedback WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()
    return dict(row) if row else None


def get_complaint_full(
    conn: sqlite3.Connection, reference: str, verification: str
) -> dict[str, Any] | None:
    complaint = get_verified_complaint(conn, reference, verification)
    if not complaint:
        return None
    complaint["events"] = get_events(conn, complaint["id"])
    complaint["feedback"] = get_feedback(conn, complaint["id"])
    return complaint


def add_event(
    conn: sqlite3.Connection,
    complaint_id: int,
    event_type: str,
    description: str,
    new_status: str | None = None,
) -> None:
    now = db.utcnow_iso()
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO demo_complaint_events (complaint_id, event_type, description, created_at) VALUES (?, ?, ?, ?)",
            (complaint_id, event_type, description, now),
        )
        if new_status:
            conn.execute(
                "UPDATE demo_complaints SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now, complaint_id),
            )
        else:
            conn.execute(
                "UPDATE demo_complaints SET updated_at = ? WHERE id = ?", (now, complaint_id)
            )


def add_reminder(conn: sqlite3.Connection, complaint: dict[str, Any], message: str) -> str:
    new_status = (
        STATUSES["REOPENED"] if complaint["status"] == STATUSES["CLOSED"] else STATUSES["CLARIFICATION"]
    )
    add_event(
        conn,
        complaint["id"],
        "REMINDER",
        f"Citizen reminder/clarification: {message}",
        new_status=new_status,
    )
    return new_status


def save_feedback(
    conn: sqlite3.Connection, complaint: dict[str, Any], rating: int, feedback_text: str
) -> None:
    now = db.utcnow_iso()
    with db.transaction(conn):
        conn.execute(
            """
            INSERT INTO demo_feedback (complaint_id, rating, feedback_text, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(complaint_id) DO UPDATE SET
                rating = excluded.rating,
                feedback_text = excluded.feedback_text,
                created_at = excluded.created_at
            """,
            (complaint["id"], rating, feedback_text or None, now),
        )
        conn.execute(
            "INSERT INTO demo_complaint_events (complaint_id, event_type, description, created_at) "
            "VALUES (?, 'FEEDBACK', ?, ?)",
            (
                complaint["id"],
                f"Citizen submitted a demo satisfaction rating of {rating}/5. "
                "This feedback is stored locally and is not sent to any government officer.",
                now,
            ),
        )
        conn.execute(
            "UPDATE demo_complaints SET updated_at = ? WHERE id = ?", (now, complaint["id"])
        )


def create_demo_user(
    conn: sqlite3.Connection, display_name: str, email: str, state: str
) -> dict[str, Any]:
    account_ref = f"DEMO-CITIZEN-{uuid.uuid4().hex[:6].upper()}"
    now = db.utcnow_iso()
    conn.execute(
        "INSERT INTO demo_users (account_ref, display_name, email, state, created_at) VALUES (?, ?, ?, ?, ?)",
        (account_ref, display_name, email, state, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM demo_users WHERE account_ref = ?", (account_ref,)
    ).fetchone()
    return dict(row)


def save_contact_message(conn: sqlite3.Connection, cleaned: dict[str, str]) -> None:
    conn.execute(
        "INSERT INTO contact_messages (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (cleaned["name"], cleaned["email"], cleaned["subject"], cleaned["message"], db.utcnow_iso()),
    )
    conn.commit()


def list_complaints(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM demo_complaints ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def complaint_export_row(complaint: dict[str, Any]) -> dict[str, Any]:
    return {
        "registration_number": complaint["registration_number"],
        "subject": complaint["subject"],
        "category": complaint["category"],
        "organisation": complaint["organisation"],
        "region": complaint["region"],
        "description": complaint["description"],
        "status": complaint["status"],
        "created_at": complaint["created_at"],
        "updated_at": complaint["updated_at"],
        "is_seeded": bool(complaint["is_seeded"]),
        "source": "CPGRAMS Simulator",
        "is_synthetic": True,
    }


def set_dashboard_result(
    conn: sqlite3.Connection,
    complaint_id: int,
    status: str,
    error: str | None = None,
    case_ref: str | None = None,
) -> None:
    now = db.utcnow_iso()
    with db.transaction(conn):
        conn.execute(
            "UPDATE demo_complaints SET dashboard_sync_status = ?, dashboard_sync_error = ?, "
            "dashboard_case_ref = COALESCE(?, dashboard_case_ref) WHERE id = ?",
            (status, error, case_ref, complaint_id),
        )
        conn.execute(
            "UPDATE dashboard_outbox SET status = ?, attempt_count = attempt_count + 1, "
            "last_attempt_at = ?, last_error = ? WHERE complaint_id = ?",
            (status, now, error, complaint_id),
        )


def pending_dashboard_outbox(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT o.*, c.registration_number FROM dashboard_outbox o "
        "JOIN demo_complaints c ON c.id = o.complaint_id "
        "WHERE o.status = 'PENDING' ORDER BY o.id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def reset_sequence_cache() -> None:
    """Placeholder for callers that want to ensure fresh reads on a new connection."""
    return None
