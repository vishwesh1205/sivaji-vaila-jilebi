from __future__ import annotations

import re
from datetime import datetime
from typing import Any

CATEGORIES = [
    "Revenue & Certificates",
    "Pension & Retirement",
    "Municipal Services",
    "Public Distribution",
    "Health & Hospitals",
    "Education",
    "Transport & Roads",
    "Electricity & Water",
    "Police & Public Safety",
    "Other Public Service",
]

ORGANISATIONS = [
    "Department of Administrative Reforms & Public Grievances",
    "Department of Revenue",
    "Department of Pension & Pensioners' Welfare",
    "Ministry of Health & Family Welfare",
    "Ministry of Education",
    "Ministry of Housing & Urban Affairs",
    "Ministry of Road Transport & Highways",
    "Municipal Administration",
    "State Public Grievance Cell",
    "Other (Demo)",
]

REGIONS = [
    "All India / Not applicable",
    "Andhra Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Tamil Nadu",
    "Telangana",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Other State / UT (Demo)",
]

STATUSES = {
    "RECEIVED": "Received — Demo",
    "UNDER_PROCESS": "Under Process — Demo",
    "CLARIFICATION": "Clarification Received — Demo",
    "REOPENED": "Reopened — Demo",
    "CLOSED": "Closed — Demo",
}

STATUS_TONES = {
    "Received — Demo": "received",
    "Under Process — Demo": "progress",
    "Clarification Received — Demo": "clarification",
    "Reopened — Demo": "reopened",
    "Closed — Demo": "closed",
}

EVENT_LABELS = {
    "RECEIVED": "Grievance received",
    "FORWARDED": "Forwarded",
    "UNDER_REVIEW": "Under review",
    "UNDER_PROCESS": "Under process",
    "REMINDER": "Reminder / clarification",
    "CLARIFICATION": "Clarification received",
    "REOPENED": "Reopened",
    "FEEDBACK": "Feedback recorded",
    "CLOSED": "Closed",
}

REFERENCE_RE = re.compile(r"^CPGRAMS-DEMO-\d{4}-\d{5,}$")
COMPLAINANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{2,49}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_reference(value: Any) -> str:
    return clean(value).upper()


def normalise_complainant(value: Any) -> str:
    return clean(value).upper()


def validate_complaint(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    cleaned = {
        "complainant_ref": clean(data.get("complainant_ref")),
        "subject": clean(data.get("subject")),
        "category": clean(data.get("category")),
        "organisation": clean(data.get("organisation")),
        "region": clean(data.get("region")),
        "description": clean(data.get("description")),
    }
    errors: dict[str, str] = {}

    if not cleaned["complainant_ref"]:
        errors["complainant_ref"] = "A demo complainant reference is required."
    elif not COMPLAINANT_RE.match(cleaned["complainant_ref"]):
        errors["complainant_ref"] = (
            "Use 3–50 letters, numbers, spaces, dots, dashes or underscores. "
            "Do not enter Aadhaar, PAN or government credentials."
        )
    if not cleaned["subject"]:
        errors["subject"] = "A grievance subject is required."
    elif len(cleaned["subject"]) < 5:
        errors["subject"] = "The subject must be at least 5 characters."
    elif len(cleaned["subject"]) > 150:
        errors["subject"] = "The subject must be 150 characters or fewer."

    if cleaned["category"] not in CATEGORIES:
        errors["category"] = "Choose a demo grievance category."
    if cleaned["organisation"] not in ORGANISATIONS:
        errors["organisation"] = "Choose a demo organisation or department."
    if cleaned["region"] not in REGIONS:
        errors["region"] = "Choose a demo state or region."
    if not cleaned["description"]:
        errors["description"] = "A detailed grievance description is required."
    elif len(cleaned["description"]) < 30:
        errors["description"] = "Please provide at least 30 characters of description."
    elif len(cleaned["description"]) > 5000:
        errors["description"] = "The description must be 5,000 characters or fewer."
    if clean(data.get("declaration")) != "yes":
        errors["declaration"] = "Please confirm that this is a fictional demonstration submission."
    return cleaned, errors


def validate_reminder(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    cleaned = {
        "reference": normalise_reference(data.get("reference")),
        "verification": normalise_complainant(data.get("verification")),
        "message": clean(data.get("message")),
    }
    errors: dict[str, str] = {}
    if not cleaned["reference"]:
        errors["reference"] = "Enter the demo registration number."
    elif not REFERENCE_RE.match(cleaned["reference"]):
        errors["reference"] = "Demo references look like CPGRAMS-DEMO-2026-00001."
    if not cleaned["verification"]:
        errors["verification"] = "Enter the demo verification code (complainant reference)."
    if not cleaned["message"]:
        errors["message"] = "Write a clarification or reminder message."
    elif len(cleaned["message"]) < 10:
        errors["message"] = "Please write at least 10 characters."
    elif len(cleaned["message"]) > 2000:
        errors["message"] = "The message must be 2,000 characters or fewer."
    return cleaned, errors


def validate_feedback(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    cleaned: dict[str, Any] = {
        "reference": normalise_reference(data.get("reference")),
        "verification": normalise_complainant(data.get("verification")),
        "rating": clean(data.get("rating")),
        "feedback_text": clean(data.get("feedback_text")),
    }
    errors: dict[str, str] = {}
    if not cleaned["reference"]:
        errors["reference"] = "Enter the demo registration number."
    elif not REFERENCE_RE.match(cleaned["reference"]):
        errors["reference"] = "Demo references look like CPGRAMS-DEMO-2026-00001."
    if not cleaned["verification"]:
        errors["verification"] = "Enter the demo verification code (complainant reference)."
    if cleaned["rating"] not in {"1", "2", "3", "4", "5"}:
        errors["rating"] = "Choose a rating from 1 to 5."
    else:
        cleaned["rating"] = int(cleaned["rating"])
    if len(cleaned["feedback_text"]) > 1000:
        errors["feedback_text"] = "Feedback must be 1,000 characters or fewer."
    return cleaned, errors


def validate_contact(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    cleaned = {
        "name": clean(data.get("name")),
        "email": clean(data.get("email")),
        "subject": clean(data.get("subject")),
        "message": clean(data.get("message")),
    }
    errors: dict[str, str] = {}
    if len(cleaned["name"]) < 2:
        errors["name"] = "Please enter a name of at least 2 characters."
    if not EMAIL_RE.match(cleaned["email"]):
        errors["email"] = "Please enter a valid demo email address."
    if len(cleaned["subject"]) < 3:
        errors["subject"] = "Please enter a short subject."
    if len(cleaned["message"]) < 10:
        errors["message"] = "Please write at least 10 characters."
    if len(cleaned["message"]) > 2000:
        errors["message"] = "Please keep the message under 2,000 characters."
    return cleaned, errors


def format_datetime(value: str | None, with_time: bool = True) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if with_time:
        return dt.strftime("%d %b %Y, %H:%M UTC")
    return dt.strftime("%d %b %Y")


def status_tone(status: str) -> str:
    return STATUS_TONES.get(status, "received")


def event_label(event_type: str) -> str:
    return EVENT_LABELS.get(event_type, event_type.replace("_", " ").title())


def is_closed(status: str) -> bool:
    return status == STATUSES["CLOSED"]


def dashboard_category(category: str) -> str:
    mapping = {
        "Revenue & Certificates": "OTHER",
        "Pension & Retirement": "OTHER",
        "Municipal Services": "INFRASTRUCTURE",
        "Public Distribution": "OTHER",
        "Health & Hospitals": "OTHER",
        "Education": "ACADEMIC_ADMINISTRATION",
        "Transport & Roads": "INFRASTRUCTURE",
        "Electricity & Water": "INFRASTRUCTURE",
        "Police & Public Safety": "GOVERNANCE_MISCONDUCT",
        "Other Public Service": "OTHER",
    }
    return mapping.get(category, "OTHER")
