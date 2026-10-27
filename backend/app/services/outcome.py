from collections import defaultdict
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import models


CONTRADICTORY_PAIRS = {
    frozenset({models.OutcomeTag.DEFICIENCY_CONFIRMED, models.OutcomeTag.NO_DEFICIENCY}),
    frozenset({models.OutcomeTag.PENALTY_PROPOSED, models.OutcomeTag.CLOSED_NO_ACTION}),
    frozenset({models.OutcomeTag.APPROVAL_ACTION_PROPOSED, models.OutcomeTag.NO_DEFICIENCY}),
    frozenset({models.OutcomeTag.DEFICIENCY_CONFIRMED, models.OutcomeTag.CLOSED_NO_ACTION}),
}


def is_contradictory(a: models.OutcomeTag, b: models.OutcomeTag) -> bool:
    return frozenset({a, b}) in CONTRADICTORY_PAIRS


def find_conflicting_outcomes(db: Session, case: models.Case, new_tag: models.OutcomeTag) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    other_ids: set[int] = set()
    for link in db.scalars(select(models.CaseLink).where(or_(models.CaseLink.case_a_id == case.id, models.CaseLink.case_b_id == case.id))).all():
        other_ids.add(link.case_b_id if link.case_a_id == case.id else link.case_a_id)
    alerts = db.scalars(select(models.OverlapAlert).where(models.OverlapAlert.institution_id == case.institution_id)).all() if case.institution_id else []
    for alert in alerts:
        for cid in alert.case_ids:
            if cid != case.id:
                other_ids.add(cid)
    for cid in other_ids:
        other = db.get(models.Case, cid)
        if not other or not other.outcome_tag or other.bureau_id == case.bureau_id:
            continue
        if is_contradictory(new_tag, other.outcome_tag):
            conflicts.append({
                "case_id": other.case_id,
                "database_id": other.id,
                "bureau_code": other.bureau.code if other.bureau else None,
                "outcome_tag": other.outcome_tag.value,
                "date_received": other.date_received.isoformat(),
            })
    return conflicts
