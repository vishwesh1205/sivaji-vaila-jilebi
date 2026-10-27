from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..services.resolution import InstitutionResolver


def verify_audit_chain(db: Session, case_pk: int) -> bool:
    actions = db.scalars(select(models.CaseAction).where(models.CaseAction.case_id == case_pk).order_by(models.CaseAction.created_at.asc())).all()
    prev = "0" * 64
    for a in actions:
        if a.prev_hash != prev:
            return False
        prev = a.hash
    return True


def case_lineage(db: Session, case: models.Case) -> dict[str, Any]:
    raw = db.get(models.RawPayload, case.raw_payload_id) if case.raw_payload_id else None
    rq = db.scalar(select(models.ReviewQueue).where(models.ReviewQueue.case_id == case.id).order_by(models.ReviewQueue.id.desc()))
    candidates = list(rq.candidate_institutions or []) if rq else []
    if not candidates and case.raw_institution_text:
        try:
            _, conf, cands = InstitutionResolver(db).resolve(case.raw_institution_text, {})
            candidates = [{"institution_id": c.institution.id, "name": c.institution.name, "aicte_permanent_id": c.institution.aicte_permanent_id, "score": c.score, "reasons": c.reasons} for c in cands]
        except Exception:
            candidates = []
    alerts = []
    if case.institution_id:
        alerts = db.scalars(select(models.OverlapAlert).where(models.OverlapAlert.institution_id == case.institution_id)).all()
    links = db.scalars(select(models.CaseLink).where((models.CaseLink.case_a_id == case.id) | (models.CaseLink.case_b_id == case.id))).all()
    similarity = max([l.similarity_score for l in links if l.link_type == models.LinkType.NEAR_DUPLICATE] or [0.0])
    return {
        "stage_1_raw_payload": {
            "available": bool(raw),
            "source_name": raw.source if raw else case.source_name,
            "source_type": raw.source_type if raw else case.source_type,
            "source_record_id": raw.source_record_id if raw else case.source_record_id,
            "fetched_at": raw.fetched_at.isoformat() if raw else None,
            "payload": raw.payload_json if raw else None,
            "payload_sha256": raw.payload_sha256 if raw else None,
            "note": "Original payload as received. Immutable and hash-addressed." if raw else "No raw payload retained for this record (manual/legacy seed).",
        },
        "stage_2_normalized": {
            "case_id": case.case_id,
            "institution_text": case.raw_institution_text,
            "category": case.category.value,
            "narrative": case.narrative,
            "language": case.language,
            "date_received": case.date_received.isoformat(),
            "source_channel": case.source_channel.value,
            "bureau": case.bureau.code if case.bureau else None,
            "mapping_note": "Mapped via connector YAML where applicable. Manual records bypass field mapping.",
        },
        "stage_3_resolution": {
            "decision": case.resolution_status.value,
            "institution": {"id": case.institution.id, "name": case.institution.name, "aicte_permanent_id": case.institution.aicte_permanent_id} if case.institution else None,
            "match_confidence": case.match_confidence,
            "candidates": candidates,
            "thresholds": {"auto_link": settings.auto_link_threshold, "review": settings.review_threshold},
            "human_confirmed": bool(rq and rq.status == models.ReviewStatus.CONFIRMED),
        },
        "stage_4_overlap": {
            "rule_fired": any(a.status in {models.AlertStatus.OPEN, models.AlertStatus.ACKNOWLEDGED, models.AlertStatus.REVIEWED_NO_ACTION, models.AlertStatus.RESOLVED} for a in alerts),
            "alerts": [{"id": a.id, "status": a.status.value, "bureaus_involved": a.bureaus_involved, "why_flagged": a.why_flagged, "case_ids": a.case_ids} for a in alerts],
            "similarity_score": round(similarity, 4),
            "links": [{"id": l.id, "type": l.link_type.value, "similarity": l.similarity_score, "case_a_id": l.case_a_id, "case_b_id": l.case_b_id} for l in links],
        },
        "audit_chain_valid": verify_audit_chain(db, case.id),
        "generated_at": datetime.utcnow().isoformat(),
    }
