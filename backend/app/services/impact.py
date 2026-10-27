import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


def simulate_impact(db: Session, discovery_delay_days: int = 14, seed: int = 42, duplicate_hours_saved: float = 6.0) -> dict[str, Any]:
    rng = random.Random(seed)
    cases = db.scalars(select(models.Case).order_by(models.Case.date_received.asc())).all()
    by_inst: dict[int, list[models.Case]] = defaultdict(list)
    for c in cases:
        if c.institution_id:
            by_inst[c.institution_id].append(c)

    opportunities = []
    for inst_id, items in by_inst.items():
        items = sorted(items, key=lambda c: c.date_received)
        seen_bureaus: set[int] = set()
        first_by_bureau: dict[int, models.Case] = {}
        triggered = False
        for c in items:
            if c.bureau_id not in first_by_bureau:
                first_by_bureau[c.bureau_id] = c
            if not triggered and len(first_by_bureau) >= 2:
                opportunity_at = c.date_received
                baseline_jitter = rng.uniform(-2, 8)
                baseline_detect = max(1, discovery_delay_days + round(baseline_jitter))
                system_detect = 0.2
                opportunities.append({
                    "institution_id": inst_id,
                    "institution_name": c.institution.name if c.institution else None,
                    "opportunity_at": opportunity_at.isoformat(),
                    "baseline_days_to_detect": baseline_detect,
                    "system_days_to_detect": system_detect,
                    "bureaus": sorted({x.bureau.code for x in first_by_bureau.values() if x.bureau}),
                })
                triggered = True

    open_cases = [c for c in cases if c.status in {models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED}]
    now = datetime.utcnow()
    early_warning = sum(1 for c in open_cases if 75 <= (now - c.date_received).days < 90)
    breached = sum(1 for c in open_cases if (now - c.date_received).days >= 90)
    dup_avoided = round(len(opportunities) * duplicate_hours_saved / 8.0, 1)
    avg_baseline = round(sum(o["baseline_days_to_detect"] for o in opportunities) / len(opportunities), 1) if opportunities else 0.0
    avg_system = round(sum(o["system_days_to_detect"] for o in opportunities) / len(opportunities), 1) if opportunities else 0.0
    return {
        "assumptions": {
            "discovery_delay_days": discovery_delay_days,
            "duplicate_hours_saved_per_overlap": duplicate_hours_saved,
            "seed": seed,
            "system_detection_days": 0.2,
            "note": "Model output, not a measured claim. Baseline discovery delay and duplicate effort are editable assumptions.",
        },
        "baseline": {
            "label": "Manual discovery (assumed baseline)",
            "overlaps_detected": len(opportunities),
            "avg_days_to_detect": avg_baseline,
            "estimated_duplicate_fact_finding_days_avoided": 0.0,
            "cases_with_early_warning": 0,
            "breached_90_days": breached,
        },
        "system": {
            "label": "With coordination layer",
            "overlaps_detected": len(opportunities),
            "avg_days_to_detect": avg_system,
            "estimated_duplicate_fact_finding_days_avoided": dup_avoided,
            "cases_with_early_warning": early_warning,
            "breached_90_days": breached,
        },
        "opportunities": opportunities[:100],
        "replay_case_count": len(cases),
        "deterministic": True,
    }
