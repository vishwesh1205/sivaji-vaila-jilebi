from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .engine import NEXT_ACTIONS, REMARKS_POOL

OUTCOME_BY_CATEGORY: dict[str, dict[str, float]] = {
    "FEE": {
        "DEFICIENCY_CONFIRMED": 0.46,
        "NO_DEFICIENCY": 0.22,
        "PENALTY_PROPOSED": 0.14,
        "APPROVAL_ACTION_PROPOSED": 0.08,
        "CLOSED_NO_ACTION": 0.10,
    },
    "FACULTY": {
        "DEFICIENCY_CONFIRMED": 0.44,
        "NO_DEFICIENCY": 0.24,
        "PENALTY_PROPOSED": 0.12,
        "APPROVAL_ACTION_PROPOSED": 0.12,
        "CLOSED_NO_ACTION": 0.08,
    },
    "INFRASTRUCTURE": {
        "DEFICIENCY_CONFIRMED": 0.48,
        "NO_DEFICIENCY": 0.20,
        "PENALTY_PROPOSED": 0.08,
        "APPROVAL_ACTION_PROPOSED": 0.14,
        "CLOSED_NO_ACTION": 0.10,
    },
    "APPROVAL_VIOLATION": {
        "DEFICIENCY_CONFIRMED": 0.42,
        "NO_DEFICIENCY": 0.18,
        "PENALTY_PROPOSED": 0.16,
        "APPROVAL_ACTION_PROPOSED": 0.18,
        "CLOSED_NO_ACTION": 0.06,
    },
    "ACADEMIC_ADMINISTRATION": {
        "DEFICIENCY_CONFIRMED": 0.38,
        "NO_DEFICIENCY": 0.30,
        "PENALTY_PROPOSED": 0.06,
        "APPROVAL_ACTION_PROPOSED": 0.08,
        "CLOSED_NO_ACTION": 0.18,
    },
    "RAGGING_DISCRIMINATION": {
        "DEFICIENCY_CONFIRMED": 0.40,
        "NO_DEFICIENCY": 0.26,
        "PENALTY_PROPOSED": 0.16,
        "APPROVAL_ACTION_PROPOSED": 0.08,
        "CLOSED_NO_ACTION": 0.10,
    },
    "GOVERNANCE_MISCONDUCT": {
        "DEFICIENCY_CONFIRMED": 0.38,
        "NO_DEFICIENCY": 0.18,
        "PENALTY_PROPOSED": 0.22,
        "APPROVAL_ACTION_PROPOSED": 0.14,
        "CLOSED_NO_ACTION": 0.08,
    },
    "OTHER": {
        "DEFICIENCY_CONFIRMED": 0.26,
        "NO_DEFICIENCY": 0.30,
        "PENALTY_PROPOSED": 0.06,
        "APPROVAL_ACTION_PROPOSED": 0.08,
        "CLOSED_NO_ACTION": 0.30,
    },
}

OUTCOME_REMARKS = {
    "DEFICIENCY_CONFIRMED": "Deficiency confirmed on the basis of the institutional reply and records. The institution has been directed to rectify the same.",
    "NO_DEFICIENCY": "No deficiency was established after verification of the records and the institution's reply.",
    "PENALTY_PROPOSED": "A penalty has been proposed for consideration by the competent authority in view of the confirmed non-compliance.",
    "APPROVAL_ACTION_PROPOSED": "Action in respect of the institution's approval has been proposed and placed before the competent authority.",
    "CLOSED_NO_ACTION": "The complaint was closed as no further regulatory action was considered necessary on the available material.",
}

DOCUMENT_NAMES = [
    "fee_receipt.pdf",
    "bank_statement.pdf",
    "institution_reply.pdf",
    "attendance_register.jpg",
    "approval_letter.pdf",
    "admission_brochure.pdf",
    "representation_acknowledgement.pdf",
    "hostel_photographs.jpg",
    "salary_slip.pdf",
    "inspection_note.pdf",
]


@dataclass
class ActionSpec:
    action_type: str
    remarks: str
    created_at: datetime
    actor_user_id: int | None = None
    bureau_id: int | None = None
    document_url: str | None = None


@dataclass
class Lifecycle:
    status: str
    outcome_tag: str | None
    last_action_at: datetime
    last_action_text: str
    next_action_text: str | None
    expected_disposal_date: datetime
    actions: list[ActionSpec] = field(default_factory=list)


def weighted_outcome(rng: random.Random, category: str, status: str) -> str | None:
    if status != "DISPOSED":
        return None
    weights = OUTCOME_BY_CATEGORY.get(category, OUTCOME_BY_CATEGORY["OTHER"])
    pick = rng.random()
    upto = 0.0
    for outcome, weight in weights.items():
        upto += weight
        if pick <= upto:
            return outcome
    return "CLOSED_NO_ACTION"


def _remark(rng: random.Random, action_type: str, values: dict[str, str], outcome: str | None = None) -> str:
    pool = REMARKS_POOL.get(action_type, REMARKS_POOL["REMARK"])
    text = rng.choice(pool).format_map(values)
    if action_type == "OUTCOME_TAGGED" and outcome:
        text = f"{text} Outcome recorded: {OUTCOME_REMARKS[outcome]}"
    return text


def build_lifecycle(
    *,
    seed: int,
    case_id: str,
    date_received: datetime,
    status: str,
    category: str,
    subtype: str,
    institution=None,
    bureau_id: int | None = None,
    assigned_officer_id: int | None = None,
    values: dict[str, str] | None = None,
    now: datetime | None = None,
) -> Lifecycle:
    rng = random.Random(f"{seed}:{case_id}:lifecycle")
    now = now or datetime.utcnow()
    values = dict(values or {})
    values.setdefault("aicte_id", getattr(institution, "aicte_permanent_id", "not available"))
    values.setdefault("channel_label", "the portal")
    values.setdefault("institution", getattr(institution, "name", "the institution"))

    action_ranges = {
        "PENDING": (3, 6),
        "UNDER_PROCESS": (4, 9),
        "DISPOSED": (5, 12),
        "TRANSFERRED": (4, 8),
        "ESCALATED": (5, 10),
    }
    lo, hi = action_ranges.get(status, (3, 7))
    count = rng.randint(lo, hi)
    if institution is None and status == "PENDING":
        count = max(3, count - 1)

    expected = date_received + timedelta(days=90)
    age_days = max(1.0, (now - date_received).total_seconds() / 86400)
    if status == "DISPOSED":
        end = min(now - timedelta(hours=rng.randint(6, 72)), date_received + timedelta(days=rng.uniform(35, 105)))
    elif status == "UNDER_PROCESS":
        end = now - timedelta(days=rng.uniform(1, min(18, max(2, age_days * 0.35))))
    elif status == "TRANSFERRED":
        end = now - timedelta(days=rng.uniform(2, min(30, max(3, age_days * 0.5))))
    elif status == "ESCALATED":
        end = now - timedelta(days=rng.uniform(1, min(25, max(2, age_days * 0.5))))
    else:
        end = now - timedelta(days=rng.uniform(0.5, min(12, max(1.5, age_days * 0.45))))

    if end <= date_received:
        end = date_received + timedelta(hours=6)
    end = min(end, now - timedelta(hours=2))
    if end <= date_received:
        end = date_received + timedelta(hours=1)

    # Choose a terminal/status flow with a minimum of three actions.
    terminal = {
        "DISPOSED": "OUTCOME_TAGGED",
        "UNDER_PROCESS": rng.choice(["STATUS_CHANGED", "REMARK"]),
        "PENDING": "REMARK",
        "TRANSFERRED": "TRANSFERRED",
        "ESCALATED": "ESCALATED",
    }[status]

    sequence: list[str] = ["CREATED"]
    if institution is not None and count > 3:
        sequence.append("INSTITUTION_RESOLVED")
    docs = 0
    if rng.random() < 0.65 and count > 4:
        docs = 1
        sequence.append("DOCUMENT_ADDED")
    fillers = ["REMARK", "STATUS_CHANGED", "DOCUMENT_ADDED", "REMARK", "STATUS_CHANGED"]
    while len(sequence) < count - 1:
        pick = rng.choice(fillers)
        sequence.append(pick)
    sequence.append(terminal)
    sequence = sequence[:count]
    if sequence[-1] != terminal:
        sequence[-1] = terminal

    # Ensure at least one document action in a healthy slice of cases.
    if docs == 0 and rng.random() < 0.30 and count >= 5:
        for idx in range(2, len(sequence) - 1):
            if sequence[idx] == "REMARK":
                sequence[idx] = "DOCUMENT_ADDED"
                docs = 1
                break

    outcome = weighted_outcome(rng, category, status)
    actions: list[ActionSpec] = []
    span = end - date_received
    for idx, action_type in enumerate(sequence):
        if len(sequence) == 1:
            at = date_received
        else:
            fraction = idx / (len(sequence) - 1)
            jitter = rng.uniform(-0.012, 0.012)
            at = date_received + span * max(0.0, min(1.0, fraction + jitter))
        at = min(max(at, date_received), now - timedelta(minutes=5))
        if actions and at <= actions[-1].created_at:
            at = actions[-1].created_at + timedelta(hours=rng.randint(2, 36))
            at = min(at, now - timedelta(minutes=5))
        action_type_enum = action_type
        if action_type == "OUTCOME_TAGGED" and outcome is None:
            action_type_enum = "REMARK"
        remarks = _remark(rng, action_type_enum, values, outcome)
        doc_url = None
        if action_type == "DOCUMENT_ADDED":
            doc_url = f"/static/synthetic/{case_id.lower()}/{rng.choice(DOCUMENT_NAMES)}"
        actions.append(
            ActionSpec(
                action_type=action_type_enum,
                remarks=remarks,
                created_at=at,
                actor_user_id=assigned_officer_id,
                bureau_id=bureau_id,
                document_url=doc_url,
            )
        )

    # FINAL action can be OUTCOME_TAGGED only after the outcome is known.
    if status == "DISPOSED" and actions[-1].action_type != "OUTCOME_TAGGED":
        actions[-1].action_type = "OUTCOME_TAGGED"
        actions[-1].remarks = _remark(rng, "OUTCOME_TAGGED", values, outcome)

    last = actions[-1]
    next_text = None if status in {"DISPOSED"} else rng.choice(NEXT_ACTIONS.get(status, ["Review case"]))
    return Lifecycle(
        status=status,
        outcome_tag=outcome,
        last_action_at=last.created_at,
        last_action_text=last.remarks,
        next_action_text=next_text,
        expected_disposal_date=expected,
        actions=actions,
    )
