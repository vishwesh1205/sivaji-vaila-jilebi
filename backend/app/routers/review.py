from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user
from ..hash_chain import compute_hash
from ..services.overlap import OverlapService

router = APIRouter()


class ConfirmReview(BaseModel):
    institution_id: int | None = None


class RejectReview(BaseModel):
    remarks: str = ""


@router.get("")
def get_review_queue(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    items = db.scalars(select(models.ReviewQueue).where(models.ReviewQueue.status == models.ReviewStatus.OPEN)).all()
    out = []
    for rq in items:
        c = rq.case
        out.append(
            {
                "id": rq.id,
                "case_id": c.id,
                "case_number": c.case_id,
                "raw_institution_text": c.raw_institution_text,
                "category": c.category.value,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "narrative": c.narrative,
                "bureau_code": c.bureau.code if c.bureau else None,
                "candidate_institutions": rq.candidate_institutions,
                "created_at": rq.created_at.isoformat(),
            }
        )
    return out


@router.post("/{id}/confirm")
def confirm_review(id: int, body: ConfirmReview, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    rq = db.get(models.ReviewQueue, id)
    if not rq or rq.status != models.ReviewStatus.OPEN:
        raise HTTPException(status_code=404, detail="Review item not found or already processed")
    inst_id = body.institution_id or rq.chosen_institution_id
    if not inst_id and rq.candidate_institutions:
        inst_id = rq.candidate_institutions[0].get("institution_id")
    if not inst_id:
        raise HTTPException(status_code=400, detail="No institution selected")
    inst = db.get(models.Institution, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    case = rq.case
    case.institution_id = inst.id
    case.resolution_status = models.ResolutionStatus.RESOLVED
    case.match_confidence = 0.9
    rq.status = models.ReviewStatus.CONFIRMED
    rq.reviewed_by = current.id
    rq.chosen_institution_id = inst.id
    rq.reviewed_at = datetime.utcnow()
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    payload = {"action": "INSTITUTION_RESOLVED", "institution_id": inst.id, "confirmed_by": current.id}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.INSTITUTION_RESOLVED,
        remarks=f"Resolved to {inst.name} ({inst.aicte_permanent_id}) by reviewer",
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    db.add(action)
    alias = case.raw_institution_text.strip()
    if alias and alias.lower() not in [a.lower() for a in (inst.aliases or [])]:
        if alias not in inst.aliases:
            inst.aliases = list(inst.aliases or []) + [alias]
        exists = db.scalar(select(models.InstitutionAlias).where(models.InstitutionAlias.institution_id == inst.id, models.InstitutionAlias.alias == alias))
        if not exists:
            db.add(models.InstitutionAlias(institution_id=inst.id, alias=alias, source="reviewer_confirmed"))
    db.commit()
    try:
        OverlapService(db).detect_for_case(case, current.id)
    except Exception:
        pass
    return {"ok": True}


@router.post("/{id}/reject")
def reject_review(id: int, body: RejectReview, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    rq = db.get(models.ReviewQueue, id)
    if not rq or rq.status != models.ReviewStatus.OPEN:
        raise HTTPException(status_code=404, detail="Review item not found or already processed")
    rq.status = models.ReviewStatus.REJECTED
    rq.reviewed_by = current.id
    rq.reviewed_at = datetime.utcnow()
    case = rq.case
    case.resolution_status = models.ResolutionStatus.UNRESOLVED
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.REMARK,
        remarks=f"Review rejected: {body.remarks}",
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, {"action": "REJECT_REVIEW"}),
    )
    db.add(action)
    db.commit()
    return {"ok": True}
