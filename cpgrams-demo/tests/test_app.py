from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DISCLAIMER = "EDUCATIONAL DEMO — UNOFFICIAL REPLICA. NOT CONNECTED TO THE GOVERNMENT OF INDIA. NO REAL GOVERNMENT GRIEVANCE IS FILED."
YEAR = datetime.now(timezone.utc).year
REF1 = f"CPGRAMS-DEMO-{YEAR}-00001"
REF2 = f"CPGRAMS-DEMO-{YEAR}-00002"


def login(client, next_path: str = "/grievance/new"):
    return client.post("/login", data={"next": next_path}, follow_redirects=False)


def form_token(html: str) -> str:
    match = re.search(r'name="form_token" value="([^"]+)"', html)
    assert match, "grievance form token missing"
    return match.group(1)


def complaint_payload(token: str, **overrides):
    payload = {
        "form_token": token,
        "complainant_ref": "DEMO-CITIZEN-001",
        "subject": "Fictional streetlight repair request",
        "category": "Municipal Services",
        "organisation": "Municipal Administration",
        "region": "Karnataka",
        "description": "This is a fictional demonstration complaint about a streetlight that has not worked for three weeks.",
        "declaration": "yes",
    }
    payload.update(overrides)
    return payload


def db_count() -> int:
    with sqlite3.connect(os.environ["CPGRAMS_DB_PATH"]) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM demo_complaints").fetchone()[0])


def test_homepage_and_disclaimer(client):
    response = client.get("/")
    assert response.status_code == 200
    assert DISCLAIMER in response.text
    assert REF1 in response.text
    assert "No real government grievance is filed" in response.text
    assert "noindex, nofollow" in response.text
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_public_pages_render(client):
    paths = [
        "/login", "/register", "/status", "/reminder", "/feedback", "/about",
        "/contact", "/faq", "/sitemap", "/privacy", "/disclaimer",
        "/grievance/process", "/grievance/pension",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        assert DISCLAIMER in response.text, path


def test_demo_login_honours_hidden_next(client):
    response = login(client, "/grievance/new")
    assert response.status_code == 303
    assert response.headers["location"] == "/grievance/new"
    page = client.get("/grievance/new")
    assert page.status_code == 200
    assert "Demo Citizen" in page.text
    assert 'name="form_token"' in page.text


def test_login_rejects_external_redirect(client):
    response = login(client, "https://example.com/steal")
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_registration_creates_local_profile(client):
    response = client.post(
        "/register",
        data={"display_name": "Fictional User", "email": "user@example.test", "state": "Tamil Nadu"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get("/")
    assert "Fictional User" in page.text
    assert "Sign Out" in page.text


def test_protected_form_redirects_with_next(client):
    response = client.get("/grievance/new", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")
    assert parse_qs(urlparse(response.headers["location"]).query)["next"] == ["/grievance/new"]


def test_invalid_complaint_is_rejected_without_saving(client):
    login(client)
    token = form_token(client.get("/grievance/new").text)
    response = client.post(
        "/grievance/new",
        data=complaint_payload(token, description="too short", declaration="no"),
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "at least 30 characters" in response.text
    assert db_count() == 3


def test_full_submission_and_status_lookup(client):
    login(client)
    token = form_token(client.get("/grievance/new").text)
    response = client.post(
        "/grievance/new",
        data=complaint_payload(token),
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/grievance/success?")
    query = parse_qs(urlparse(location).query)
    reference = query["ref"][0]
    verification = query["verification"][0]
    assert reference.startswith(f"CPGRAMS-DEMO-{YEAR}-")
    assert verification == "DEMO-CITIZEN-001"

    receipt = client.get(location)
    assert receipt.status_code == 200
    assert reference in receipt.text
    assert "Demo Citizen" in receipt.text

    lookup = client.post(
        "/status",
        data={"registration": reference.lower(), "verification": verification.lower()},
        follow_redirects=False,
    )
    assert lookup.status_code == 303
    detail = client.get(lookup.headers["location"])
    assert detail.status_code == 200
    assert reference in detail.text
    assert "Received — Demo" in detail.text
    assert db_count() == 4


def test_submission_token_is_idempotent(client):
    login(client)
    token = form_token(client.get("/grievance/new").text)
    first = client.post("/grievance/new", data=complaint_payload(token), follow_redirects=False)
    second = client.post("/grievance/new", data=complaint_payload(token), follow_redirects=False)
    assert first.status_code == second.status_code == 303
    assert first.headers["location"] == second.headers["location"]
    assert db_count() == 4


def test_unknown_form_token_is_rejected(client):
    login(client)
    response = client.post(
        "/grievance/new",
        data=complaint_payload("not-a-real-token"),
        follow_redirects=False,
    )
    assert response.status_code == 409
    assert "expired" in response.text
    assert db_count() == 3


def test_reminder_reopens_closed_record(client):
    response = client.post(
        "/reminder",
        data={
            "reference": REF1,
            "verification": "DEMO-CITIZEN-001",
            "message": "Please record a fictional follow-up on this closed example.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get(response.headers["location"])
    assert "Reopened — Demo" in page.text
    assert "Citizen reminder/clarification" in page.text


def test_feedback_accepted_only_for_closed_record(client):
    response = client.post(
        "/feedback",
        data={
            "reference": REF1,
            "verification": "DEMO-CITIZEN-001",
            "rating": "4",
            "feedback_text": "Fictional feedback for testing.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get(response.headers["location"])
    assert "4/5" in page.text
    assert "Fictional feedback for testing." in page.text

    rejected = client.post(
        "/feedback",
        data={
            "reference": REF2,
            "verification": "DEMO-CITIZEN-002",
            "rating": "5",
            "feedback_text": "Should not be accepted while open.",
        },
        follow_redirects=False,
    )
    assert rejected.status_code == 422
    assert "Only a closed demo grievance can be rated" in rejected.text


def test_contact_message_is_stored(client):
    response = client.post(
        "/contact",
        data={
            "name": "Demo Tester",
            "email": "tester@example.test",
            "subject": "Demo question",
            "message": "This is a fictional test message for the local contact form.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with sqlite3.connect(os.environ["CPGRAMS_DB_PATH"]) as conn:
        count = conn.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
    assert count == 1


def test_exports_are_labeled_synthetic(client):
    payload = client.get("/api/complaints").json()
    assert payload["demo"] is True
    assert payload["source"] == "CPGRAMS Simulator"
    assert payload["count"] == 3
    assert all(item["is_synthetic"] for item in payload["items"])

    csv_response = client.get("/export/complaints.csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "is_synthetic" in csv_response.text
    assert "CPGRAMS Simulator" in csv_response.text


def test_health_reports_local_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["complaint_records"] == 3
    assert payload["real_government"] is False


def test_language_switch_and_fallback_note(client):
    hindi = client.get("/?lang=hi")
    assert hindi.status_code == 200
    assert 'lang="hi"' in hindi.text
    assert "नमस्ते" in hindi.text or "CPGRAMS" in hindi.text

    fallback = client.get("/?lang=bn")
    assert fallback.status_code == 200
    assert 'lang="bn"' in fallback.text
    assert "English is shown for the selected language" in fallback.text


def test_reset_is_gated_and_requires_confirmation(client, monkeypatch):
    assert client.post("/demo/reset").status_code == 404
    monkeypatch.setenv("CPGRAMS_ALLOW_RESET", "1")
    assert client.post("/demo/reset", json={}).status_code == 400
    reset = client.post("/demo/reset", json={"confirm": "RESET-DEMO-DATA"})
    assert reset.status_code == 200
    assert reset.json()["status"] == "reset"
    assert db_count() == 3


def test_dashboard_failure_keeps_local_record(client, monkeypatch):
    monkeypatch.setenv("DASHBOARD_INGEST_URL", "http://127.0.0.1:1/ingest/json")
    monkeypatch.setenv("DASHBOARD_TIMEOUT_SECONDS", "1")
    login(client)
    token = form_token(client.get("/grievance/new").text)
    response = client.post("/grievance/new", data=complaint_payload(token), follow_redirects=False)
    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert db_count() == 4
    with sqlite3.connect(os.environ["CPGRAMS_DB_PATH"]) as conn:
        status = conn.execute(
            "SELECT dashboard_sync_status FROM demo_complaints WHERE registration_number = ?",
            (query["ref"][0],),
        ).fetchone()[0]
    assert status == "pending"


def test_attachment_rejected_and_reset_removes_accepted_upload(client, monkeypatch):
    login(client)
    token = form_token(client.get("/grievance/new").text)
    rejected = client.post(
        "/grievance/new",
        data=complaint_payload(token),
        files={"attachment": ("fake.pdf", b"not a pdf", "application/pdf")},
        follow_redirects=False,
    )
    assert rejected.status_code == 422
    assert "does not look like a valid PDF" in rejected.text

    token = form_token(rejected.text)
    accepted = client.post(
        "/grievance/new",
        data=complaint_payload(token),
        files={"attachment": ("note.txt", b"A fictional attachment.\n", "text/plain")},
        follow_redirects=False,
    )
    assert accepted.status_code == 303
    reference = parse_qs(urlparse(accepted.headers["location"]).query)["ref"][0]
    with sqlite3.connect(os.environ["CPGRAMS_DB_PATH"]) as conn:
        stored = conn.execute(
            "SELECT attachment_stored FROM demo_complaints WHERE registration_number = ?",
            (reference,),
        ).fetchone()[0]
    path = Path(os.environ["CPGRAMS_UPLOAD_DIR"]) / stored
    assert path.is_file()

    monkeypatch.setenv("CPGRAMS_ALLOW_RESET", "1")
    assert client.post("/demo/reset", json={"confirm": "RESET-DEMO-DATA"}).status_code == 200
    assert not path.exists()


def test_dashboard_success_is_marked_synthetic(client, monkeypatch):
    from app import dashboard_adapter, db, repository

    with db.connect() as conn:
        complaint = repository.get_complaint(conn, REF1)
        assert complaint is not None
        payload = dashboard_adapter.build_payload(complaint)
        item = payload["items"][0]
        assert item["source_name"] == "CPGRAMS Simulator"
        assert item["source_type"] == "SIMULATOR"
        assert item["is_synthetic"] is True
        assert item["case_id"] == REF1

        monkeypatch.setenv("DASHBOARD_INGEST_URL", "http://dashboard.test/ingest/json")
        monkeypatch.setenv("DASHBOARD_BEARER_TOKEN", "test-token")
        monkeypatch.setattr(dashboard_adapter, "_post", lambda *args, **kwargs: {"created": 1})
        result = dashboard_adapter.sync_complaint(conn, complaint)
        assert result["status"] == "synced"
        refreshed = repository.get_complaint(conn, REF1)
        assert refreshed["dashboard_sync_status"] == "synced"


def test_dashboard_401_refreshes_with_credentials(monkeypatch):
    import httpx
    from app import dashboard_adapter

    settings = {
        "url": "http://dashboard.test/ingest/json",
        "token": "expired",
        "login_url": "http://dashboard.test/auth/login",
        "username": "demo",
        "password": "secret",
        "enabled": True,
        "timeout": 2.0,
    }
    tokens = []

    def fake_post(url, token, payload, timeout):
        tokens.append(token)
        if token == "expired":
            request = httpx.Request("POST", url)
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError("unauthorized", request=request, response=response)
        return {"created": 1}

    monkeypatch.setattr(dashboard_adapter, "_post", fake_post)
    monkeypatch.setattr(dashboard_adapter, "_login", lambda _settings: "fresh")
    result = dashboard_adapter._post_authorized(settings, {"items": []})
    assert result == {"created": 1}
    assert tokens == ["expired", "fresh"]


def test_dashboard_payload_marks_cpgrams_as_synthetic():
    from app import dashboard_adapter

    complaint = {
        "registration_number": "CPGRAMS-DEMO-2026-00001",
        "subject": "Fictional subject",
        "description": "Fictional description",
        "organisation": "Demo Department",
        "region": "Karnataka",
        "category": "Municipal Services",
        "created_at": "2026-10-29T00:00:00+00:00",
    }
    item = dashboard_adapter.build_payload(complaint)["items"][0]
    assert item["source_channel"] == "CPGRAMS"
    assert item["source_record_id"] == "CPGRAMS-DEMO-2026-00001"
    assert item["source_name"] == "CPGRAMS Simulator"
    assert item["source_type"] == "SIMULATOR"
    assert item["is_synthetic"] is True
