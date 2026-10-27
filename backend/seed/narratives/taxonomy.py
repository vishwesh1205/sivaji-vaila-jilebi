from __future__ import annotations

from typing import Any

COMPLAINANT_TYPES = [
    "STUDENT",
    "PARENT",
    "FACULTY",
    "NON_TEACHING_STAFF",
    "ALUMNUS",
    "ANONYMOUS_WELLWISHER",
    "ADVOCATE_ON_BEHALF",
    "STUDENT_ASSOCIATION",
    "MINISTRY_REFERENCE",
    "MP_MLA_REFERENCE",
    "COURT_DIRECTION",
    "AICTE_INTERNAL",
    "REGIONAL_OFFICE_REPORT",
]

COMPLAINANT_LABELS = {
    "STUDENT": "Student",
    "PARENT": "Parent / guardian",
    "FACULTY": "Faculty member",
    "NON_TEACHING_STAFF": "Non-teaching staff",
    "ALUMNUS": "Alumnus",
    "ANONYMOUS_WELLWISHER": "Anonymous well-wisher",
    "ADVOCATE_ON_BEHALF": "Advocate on behalf",
    "STUDENT_ASSOCIATION": "Student association",
    "MINISTRY_REFERENCE": "Ministry reference",
    "MP_MLA_REFERENCE": "MP / MLA reference",
    "COURT_DIRECTION": "Court direction",
    "AICTE_INTERNAL": "AICTE internal / suo motu",
    "REGIONAL_OFFICE_REPORT": "Regional office report",
}

# The old flat taxonomy remains readable; every case is additionally assigned a
# concrete sub-type used by the template library.
CATEGORY_SUBTYPES: dict[str, dict[str, str]] = {
    "FEE": {
        "EXCESS_FEE": "excess fee beyond the FRC / notified fee structure",
        "REFUND_NOT_GIVEN": "refund not given after withdrawal or cancellation",
        "DOCUMENTS_WITHHELD": "certificates or original documents withheld until fee payment",
        "HIDDEN_CHARGES": "hidden development, caution or activity charges",
        "CASH_WITHOUT_RECEIPT": "fee collected in cash without a receipt",
    },
    "FACULTY": {
        "SALARY_UNPAID": "salary unpaid or underpaid",
        "GHOST_FACULTY": "faculty shown on the AICTE portal but not actually working",
        "FORCED_RESIGNATION": "forced resignation or pressure to resign",
        "QUALIFICATION_NOT_AS_PER_NORMS": "faculty qualification not as per AICTE norms",
        "FACULTY_STUDENT_RATIO": "faculty-student ratio violation",
    },
    "INFRASTRUCTURE": {
        "LAB_WITHOUT_EQUIPMENT": "laboratories without functioning equipment",
        "LIBRARY_DEFICIENT": "library with inadequate books and journals",
        "HOSTEL_MESS_CONDITIONS": "unsafe or unhygienic hostel and mess conditions",
        "BUILDING_SAFETY": "building safety or structural concerns",
        "NO_FIRE_NOC": "no valid fire NOC or fire safety arrangements",
        "NO_PLAYGROUND": "no playground or sports facility",
    },
    "APPROVAL_VIOLATION": {
        "BEYOND_INTAKE": "admission beyond the approved intake",
        "UNAPPROVED_PROGRAMME": "running an unapproved programme or course",
        "FALSE_APPROVAL_CLAIM": "wrong claim of AICTE approval in advertisements",
        "LAPSED_APPROVAL": "running after approval lapsed or closure was notified",
        "SECOND_SHIFT": "second shift without approval",
        "AFFILIATION_ISSUE": "affiliation or university recognition issue",
    },
    "ACADEMIC_ADMINISTRATION": {
        "EXAM_RESULT_DELAY": "exam or result delay",
        "INTERNAL_MARKS_MISUSE": "internal marks misuse or arbitrary changes",
        "ATTENDANCE_THREAT": "attendance shortage threats despite genuine absence",
        "PLACEMENT_FALSE_CLAIM": "placements falsely advertised",
        "MIGRATION_CERTIFICATE": "transfer or migration certificate refusal",
    },
    "RAGGING_DISCRIMINATION": {
        "RAGGING_HOSTEL": "ragging or harassment in the hostel",
        "DISCRIMINATION_CASTE_GENDER": "discrimination on caste, gender or regional grounds",
        "HARASSMENT_GENERAL": "harassment by seniors or staff, described in general terms",
    },
    "GOVERNANCE_MISCONDUCT": {
        "MANAGEMENT_DISPUTE": "management dispute affecting academic administration",
        "FUND_MISUSE": "misuse of institutional funds or fee collections",
        "FAKE_DOCUMENTS": "fake documents submitted to AICTE",
    },
    "OTHER": {
        "TRANSPORT": "transport or bus fee issue",
        "SCHOLARSHIP": "scholarship disbursement issue",
        "GENERAL_GRIEVANCE": "general grievance requiring institutional response",
    },
}

RESTRICTED_CATEGORIES = {"RAGGING_DISCRIMINATION"}

# Target share used by the life-cycle generator. The values sum to 100.
STATUS_MIX = [
    ("DISPOSED", 0.55),
    ("UNDER_PROCESS", 0.25),
    ("PENDING", 0.10),
    ("TRANSFERRED", 0.06),
    ("ESCALATED", 0.04),
]

CHANNEL_WEIGHTS = {
    "CSS": 0.27,
    "CPGRAMS": 0.27,
    "EMAIL": 0.14,
    "PHYSICAL": 0.12,
    "DIRECT": 0.08,
    "REGIONAL": 0.12,
}

CATEGORY_WEIGHTS = {
    "FEE": 0.30,
    "FACULTY": 0.17,
    "INFRASTRUCTURE": 0.15,
    "APPROVAL_VIOLATION": 0.14,
    "ACADEMIC_ADMINISTRATION": 0.12,
    "RAGGING_DISCRIMINATION": 0.05,
    "GOVERNANCE_MISCONDUCT": 0.04,
    "OTHER": 0.03,
}

# Seasonal weighting by calendar month. Values are relative multipliers.
SEASONALITY = {
    "FEE": {1: 0.4, 2: 0.4, 3: 0.5, 4: 0.6, 5: 0.7, 6: 0.9, 7: 2.0, 8: 2.2, 9: 1.6, 10: 0.8, 11: 0.5, 12: 0.5},
    "FACULTY": {1: 0.8, 2: 0.8, 3: 0.8, 4: 0.8, 5: 0.8, 6: 0.8, 7: 1.0, 8: 1.2, 9: 1.2, 10: 1.0, 11: 0.8, 12: 0.8},
    "INFRASTRUCTURE": {1: 0.7, 2: 0.7, 3: 0.7, 4: 0.8, 5: 0.9, 6: 1.2, 7: 1.4, 8: 1.4, 9: 1.0, 10: 0.8, 11: 0.7, 12: 0.7},
    "APPROVAL_VIOLATION": {1: 0.8, 2: 1.1, 3: 1.8, 4: 2.0, 5: 1.9, 6: 1.6, 7: 0.9, 8: 0.6, 9: 0.5, 10: 0.5, 11: 0.6, 12: 0.7},
    "ACADEMIC_ADMINISTRATION": {1: 0.7, 2: 0.6, 3: 0.7, 4: 0.8, 5: 1.4, 6: 1.8, 7: 1.2, 8: 0.8, 9: 0.7, 10: 0.8, 11: 1.2, 12: 1.6},
    "RAGGING_DISCRIMINATION": {1: 0.7, 2: 0.7, 3: 0.8, 4: 0.8, 5: 0.8, 6: 0.8, 7: 0.9, 8: 1.2, 9: 1.2, 10: 0.9, 11: 0.8, 12: 0.8},
    "GOVERNANCE_MISCONDUCT": {1: 0.8, 2: 0.8, 3: 0.8, 4: 0.8, 5: 0.8, 6: 0.8, 7: 0.8, 8: 0.8, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0},
    "OTHER": {m: 1.0 for m in range(1, 13)},
}

GRAPHIC_TERMS = [
    "rape",
    "sexual assault",
    "molest",
    "nude",
    "porn",
    "suicide",
    "self-harm",
    "blood",
    "beaten black and blue",
    "physical assault with",
]

DISPOSED_OUTCOMES = [
    "DEFICIENCY_CONFIRMED",
    "NO_DEFICIENCY",
    "PENALTY_PROPOSED",
    "APPROVAL_ACTION_PROPOSED",
    "CLOSED_NO_ACTION",
]


def old_category_to_new(category: Any) -> str:
    value = getattr(category, "value", str(category))
    if value in CATEGORY_SUBTYPES:
        return value
    return "OTHER"
