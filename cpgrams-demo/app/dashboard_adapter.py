"""Optional adapter for the local AICTE complaint-intelligence dashboard.

The adapter targets the dashboard's existing, authenticated JSON ingestion
contract: POST /ingest/json with {"items": [...]} and a bearer token. It is
disabled unless DASHBOARD_INGEST_URL is configured. No request is ever sent to
the real CPGRAMS portal.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from . import repository
from .services import dashboard_category

_cached_tokens: dict[tuple[str, str], str] = {}


def _default_login_url(ingest_url: str) -> str:
    parts = urlsplit(ingest_url)
    path = parts.path
    suffix = "/ingest/json"
    if path.endswith(suffix):
        path = path[: -len(suffix)]
    path = f"{path.rstrip('/')}/auth/login"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def config() -> dict[str, Any]:
    url = os.environ.get("DASHBOARD_INGEST_URL", "").strip()
    token = os.environ.get("DASHBOARD_BEARER_TOKEN", "").strip()
    username = os.environ.get("DASHBOARD_USERNAME", "").strip()
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    login_url = os.environ.get("DASHBOARD_LOGIN_URL", "").strip()
    if not login_url and url:
        login_url = _default_login_url(url)
    try:
        timeout = float(os.environ.get("DASHBOARD_TIMEOUT_SECONDS", "4"))
    except ValueError:
        timeout = 4.0
    return {
        "url": url,
        "token": token,
        "login_url": login_url,
        "username": username,
        "password": password,
        "enabled": bool(url),
        "timeout": max(1.0, min(timeout, 15.0)),
    }


def build_payload(complaint: dict[str, Any]) -> dict[str, Any]:
    reference = complaint["registration_number"]
    narrative = f"{complaint['subject']}\n\n{complaint['description']}"
    return {
        "items": [
            {
                "case_id": reference,
                "source_channel": "CPGRAMS",
                "raw_institution_text": f"{complaint['organisation']} / {complaint['region']}",
                "subject": complaint["subject"],
                "category": dashboard_category(complaint["category"]),
                "narrative": narrative,
                "narrative_original": narrative,
                "narrative_translated": narrative,
                "date_received": complaint["created_at"],
                "idempotency_key": f"cpgrams-demo:{reference}",
                "hints": {"region": complaint["region"]},
                "source_name": "CPGRAMS Simulator",
                "source_record_id": reference,
                "source_type": "SIMULATOR",
                "is_synthetic": True,
                "language": "en",
            }
        ]
    }


def _post(url: str, token: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"status": "accepted"}


def _login(settings: dict[str, Any]) -> str:
    if not settings["login_url"] or not settings["username"] or not settings["password"]:
        raise RuntimeError(
            "Dashboard credentials are required. Set DASHBOARD_USERNAME and DASHBOARD_PASSWORD "
            "or provide a fresh DASHBOARD_BEARER_TOKEN."
        )
    with httpx.Client(timeout=settings["timeout"]) as client:
        response = client.post(
            settings["login_url"],
            data={"username": settings["username"], "password": settings["password"]},
        )
        response.raise_for_status()
        token = response.json().get("access_token", "")
    if not token:
        raise RuntimeError("Dashboard login did not return an access token")
    _cached_tokens[(settings["login_url"], settings["username"])] = token
    return token


def _initial_token(settings: dict[str, Any]) -> str:
    if settings["token"]:
        return settings["token"]
    key = (settings["login_url"], settings["username"])
    if settings["username"] and settings["password"] and key in _cached_tokens:
        return _cached_tokens[key]
    return _login(settings)


def _post_authorized(settings: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    token = _initial_token(settings)
    try:
        return _post(settings["url"], token, payload, settings["timeout"])
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 401 or not (settings["username"] and settings["password"]):
            raise
        token = _login(settings)
        return _post(settings["url"], token, payload, settings["timeout"])


def sync_complaint(conn: sqlite3.Connection, complaint: dict[str, Any]) -> dict[str, Any]:
    settings = config()
    if not settings["enabled"]:
        repository.set_dashboard_result(
            conn,
            complaint["id"],
            "disabled",
            "DASHBOARD_INGEST_URL is not configured. Local record retained.",
        )
        return {"status": "disabled", "complaint": complaint["registration_number"]}

    try:
        result = _post_authorized(settings, build_payload(complaint))
        repository.set_dashboard_result(
            conn,
            complaint["id"],
            "synced",
            None,
            complaint["registration_number"],
        )
        return {"status": "synced", "complaint": complaint["registration_number"], "remote": result}
    except Exception as exc:  # network errors must never lose the local record
        error = f"{type(exc).__name__}: {exc}"[:500]
        repository.set_dashboard_result(conn, complaint["id"], "pending", error)
        return {
            "status": "pending",
            "complaint": complaint["registration_number"],
            "error": error,
        }


def sync_pending(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    results = []
    for item in repository.pending_dashboard_outbox(conn, limit=limit):
        complaint = repository.get_complaint_by_id(conn, item["complaint_id"])
        if complaint:
            results.append(sync_complaint(conn, complaint))
    return results
