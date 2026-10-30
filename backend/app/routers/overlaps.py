from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user, can_see_all
from ..services.pdf import build_evidence_pack
from ..services.provenance import verify_audit_chain

router = APIRouter()


class Ack(BaseModel):
    remarks: str = ""


class ReviewNoAction(BaseModel):
    reason: str


class Message(BaseModel):
    message: str


@router.get("")
def list_overlaps(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
    status: str | None = None,
):
    stmt = select(models.OverlapAlert).order_by(models.OverlapAlert.created_at.desc())
    if status:
        stmt = stmt.where(models.OverlapAlert.status == models.AlertStatus(status))
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
        elif current.bureau_id:
            # include alerts involving cases in this bureau
            alerts = db.scalars(stmt).all()
            filtered = []
            for a in alerts:
                cases = db.scalars(select(models.Case).where(models.Case.id.in_(a.case_ids))).all()
                if any(c.bureau_id == current.bureau_id for c in cases):
                    filtered.append(a)
            return [{"id": a.id, "institution_id": a.institution_id, "institution": {"name": a.institution.name, "aicte_permanent_id": a.institution.aicte_permanent_id} if a.institution else None, "case_ids": a.case_ids, "bureaus_involved": a.bureaus_involved, "status": a.status.value, "why_flagged": a.why_flagged, "created_at": a.created_at.isoformat(), "escalated_at": a.escalated_at.isoformat() if a.escalated_at else None, "acknowledged_by_json": a.acknowledged_by_json} for a in filtered]
        else:
            return []
    alerts = db.scalars(stmt).all()
    return [
        {
            "id": a.id,
            "institution_id": a.institution_id,
            "institution": {"name": a.institution.name, "aicte_permanent_id": a.institution.aicte_permanent_id} if a.institution else None,
            "case_ids": a.case_ids,
            "bureaus_involved": a.bureaus_involved,
            "status": a.status.value,
            "why_flagged": a.why_flagged,
            "created_at": a.created_at.isoformat(),
            "escalated_at": a.escalated_at.isoformat() if a.escalated_at else None,
            "acknowledged_by_json": a.acknowledged_by_json,
        }
        for a in alerts
    ]


@router.get("/{id}")
def get_overlap(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    a = db.get(models.OverlapAlert, id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    cases = db.scalars(select(models.Case).where(models.Case.id.in_(a.case_ids))).all()
    links = []
    for c in cases:
        for l in db.scalars(select(models.CaseLink).where((models.CaseLink.case_a_id == c.id) | (models.CaseLink.case_b_id == c.id))).all():
            links.append({"id": l.id, "case_a_id": l.case_a_id, "case_b_id": l.case_b_id, "link_type": l.link_type.value, "similarity_score": l.similarity_score})
    msgs = db.scalars(select(models.CoordinationMessage).where(models.CoordinationMessage.alert_id == a.id).order_by(models.CoordinationMessage.created_at.asc())).all()
    return {
        "id": a.id,
        "institution": {"id": a.institution.id, "name": a.institution.name, "aicte_permanent_id": a.institution.aicte_permanent_id} if a.institution else None,
        "case_ids": a.case_ids,
        "bureaus_involved": a.bureaus_involved,
        "status": a.status.value,
        "why_flagged": a.why_flagged,
        "acknowledged_by_json": a.acknowledged_by_json,
        "reviewer_reason": a.reviewer_reason,
        "created_at": a.created_at.isoformat(),
        "escalated_at": a.escalated_at.isoformat() if a.escalated_at else None,
        "cases": [
            {
                "id": c.id,
                "case_id": c.case_id,
                "bureau_code": c.bureau.code if c.bureau else None,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "source_record_id": c.source_record_id,
                "raw_payload_id": c.raw_payload_id,
                "language": c.language,
                "subject": c.subject,
                "category": c.category.value,
                "category_subtype": c.category_subtype,
                "complainant_type": c.complainant_type,
                "status": c.status.value,
                "outcome_tag": c.outcome_tag.value if c.outcome_tag else None,
                "narrative": c.narrative,
                "date_received": c.date_received.isoformat(),
                "raw_institution_text": c.raw_institution_text,
            }
            for c in cases
        ],
        "links": links,
        "audit_chain_valid": all(verify_audit_chain(db, cid) for cid in a.case_ids),
        "thread": [{"id": m.id, "author": m.author.name if m.author else None, "bureau_code": m.bureau.code if m.bureau else None, "message": m.message, "created_at": m.created_at.isoformat()} for m in msgs],
    }


@router.post("/{id}/acknowledge")
def acknowledge(id: int, body: Ack, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    a = db.get(models.OverlapAlert, id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    acks = list(a.acknowledged_by_json or [])
    acks.append({"user_id": current.id, "name": current.name, "bureau_id": current.bureau_id, "at": datetime.utcnow().isoformat(), "remarks": body.remarks})
    a.acknowledged_by_json = acks
    a.status = models.AlertStatus.ACKNOWLEDGED
    a.acknowledged_at = datetime.utcnow()
    # add overlap ack actions to involved cases
    for cid in a.case_ids:
        c = db.get(models.Case, cid)
        if c:
            last = c.actions[-1] if c.actions else None
            prev_hash = last.hash if last else "0" * 64
            from ..hash_chain import compute_hash
            action = models.CaseAction(case_id=c.id, actor_user_id=current.id, bureau_id=current.bureau_id, action_type=models.ActionType.OVERLAP_ACK, remarks="Overlap alert acknowledged", prev_hash=prev_hash, hash=compute_hash(prev_hash, {"ack": current.id}))
            db.add(action)
    db.commit()
    return {"ok": True}


@router.post("/{id}/review-no-action")
def review_no_action(id: int, body: ReviewNoAction, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    a = db.get(models.OverlapAlert, id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not body.reason or len(body.reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Mandatory reason required")
    a.status = models.AlertStatus.REVIEWED_NO_ACTION
    a.reviewer_reason = body.reason
    db.commit()
    return {"ok": True}


@router.get("/{id}/thread")
def get_thread(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    msgs = db.scalars(select(models.CoordinationMessage).where(models.CoordinationMessage.alert_id == id).order_by(models.CoordinationMessage.created_at.asc())).all()
    return [{"id": m.id, "author": m.author.name if m.author else None, "bureau_code": m.bureau.code if m.bureau else None, "message": m.message, "created_at": m.created_at.isoformat()} for m in msgs]


@router.post("/{id}/thread")
def post_thread(id: int, body: Message, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    a = db.get(models.OverlapAlert, id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Coordination message cannot be empty")
    msg = models.CoordinationMessage(alert_id=a.id, author_id=current.id, bureau_id=current.bureau_id, message=body.message.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "author": current.name, "bureau_code": current.bureau.code if current.bureau else None, "message": msg.message, "created_at": msg.created_at.isoformat()}


@router.get("/{id}/evidence-pack")
def evidence_pack(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    a = db.get(models.OverlapAlert, id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    pdf = build_evidence_pack(db, a)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=evidence-pack-alert-{id}.pdf"})
