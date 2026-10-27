from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings


def compute_institution_risk(db: Session, institution_id: int) -> dict[str, Any]:
    inst = db.get(models.Institution, institution_id)
    if not inst:
        return {"institution_id": institution_id, "score": 0.0, "breakdown": []}
    cases = db.scalars(select(models.Case).where(models.Case.institution_id == institution_id)).all()
    active = [c for c in cases if c.status in {models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED}]
    now = datetime.utcnow()
    overdue = [c for c in active if (now - c.date_received).days >= settings.sla_outer_days]
    escalations = [c for c in cases if c.status == models.CaseStatus.ESCALATED]
    bureaus = {c.bureau_id for c in active}
    unack = db.scalars(
        select(models.OverlapAlert).where(
            models.OverlapAlert.institution_id == institution_id,
            models.OverlapAlert.status == models.AlertStatus.OPEN,
        )
    ).all()
    recent = [c for c in cases if c.date_received >= now - timedelta(days=365)]
    category_counts: dict[str, int] = {}
    for c in recent:
        category_counts[c.category.value] = category_counts.get(c.category.value, 0) + 1
    repeat_count = max(category_counts.values(), default=0)
    latest_days = min([(now - c.date_received).days for c in cases], default=9999)

    components = [
        ("Active cases", len(active), settings.risk_weight_active_cases),
        ("Distinct bureaus involved", len(bureaus), settings.risk_weight_distinct_bureaus),
        ("Overdue open cases (90+ days)", len(overdue), settings.risk_weight_overdue_cases),
        ("Escalated cases", len(escalations), settings.risk_weight_escalations),
        ("Repeat category in last 12 months", max(0, repeat_count - 1), settings.risk_weight_repeat_category),
        ("Case recency (latest within 30 days)", 1 if latest_days <= 30 else 0, settings.risk_weight_recency),
        ("Unacknowledged overlap alerts", len(unack), settings.risk_weight_unack_overlap),
    ]
    breakdown = []
    raw_total = 0.0
    for label, raw, weight in components:
        points = round(float(raw) * float(weight), 2)
        raw_total += points
        breakdown.append({"component": label, "raw_value": raw, "weight": weight, "points": points, "explanation": f"{raw} × {weight}"})
    if raw_total > settings.risk_cap and raw_total > 0:
        scale = settings.risk_cap / raw_total
        running = 0.0
        for i, row in enumerate(breakdown):
            if i == len(breakdown) - 1:
                row["points"] = round(settings.risk_cap - running, 2)
            else:
                row["points"] = round(row["points"] * scale, 2)
                running += row["points"]
    score = round(sum(r["points"] for r in breakdown), 2)
    return {
        "institution_id": institution_id,
        "institution_name": inst.name,
        "aicte_permanent_id": inst.aicte_permanent_id,
        "score": score,
        "max_score": 100,
        "breakdown": breakdown,
        "note": "Transparent weighted score. Weights are configurable and shown per component.",
    }


def top_risk_institutions(db: Session, limit: int = 8) -> list[dict[str, Any]]:
    insts = db.scalars(select(models.Institution)).all()
    rows = [compute_institution_risk(db, i.id) for i in insts if i.cases]
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:limit]
