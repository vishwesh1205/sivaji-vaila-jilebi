from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, can_see_all, apply_region_scope
from ..hash_chain import compute_hash
from ..services.overlap import OverlapService
from ..services.resolution import InstitutionResolver
from ..services.language import detect_language, translate_text
from ..services.ingestion import detect_cross_channel_duplicates
from ..services.outcome import find_conflicting_outcomes
from ..connectors.base import hash_identifier

router = APIRouter()


class CaseCreate(BaseModel):
    case_id: str
    source_channel: str
    raw_institution_text: str
    category: str
    narrative: str
    bureau_id: int
    assigned_officer_id: int | None = None
    date_received: datetime | None = None
    expected_disposal_date: datetime | None = None
    idempotency_key: str
    hints: dict[str, Any] | None = None
    complainant_identifier: str | None = None
    language: str | None = None


class StatusUpdate(BaseModel):
    status: str
    remarks: str = ""
    outcome_tag: str | None = None
    acknowledge_conflict: bool = False


class OutcomeUpdate(BaseModel):
    outcome_tag: str
    acknowledge_conflict: bool = False
    remarks: str = ""


class Transfer(BaseModel):
    to_bureau_id: int
    remarks: str = ""


class Escalate(BaseModel):
    remarks: str = ""


class Remark(BaseModel):
    remarks: str
    document_url: str | None = None


class LinkCase(BaseModel):
    other_case_id: int
    link_type: str = "MANUAL"
    similarity_score: float = 0.0


def _mask_narrative(c: models.Case, current: models.User) -> str:
    if c.category == models.CaseCategory.RAGGING_DISCRIMINATION and not can_see_all(current):
        if c.bureau_id != current.bureau_id and current.role != models.UserRole.ADMIN:
            return "[RESTRICTED - RAGGING/DISCRIMINATION] Access limited to owning bureau per policy. Details masked."
    return c.narrative


@router.get("")
def list_cases(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
    q: str | None = Query(default=None),
    case_id: str | None = Query(default=None),
    aicte_id: str | None = Query(default=None),
    bureau_id: int | None = Query(default=None),
    bureaus: str | None = Query(default=None),
    region: str | None = Query(default=None),
    regions: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    min_age_days: int | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    overlap_only: bool | None = Query(default=None),
    sort: str = Query(default="date_received"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    stmt = select(models.Case)
    joined_inst = False

    def join_inst():
        nonlocal stmt, joined_inst
        if not joined_inst:
            stmt = stmt.join(models.Institution, models.Case.institution_id == models.Institution.id, isouter=True)
            joined_inst = True

    if case_id:
        stmt = stmt.where(models.Case.case_id.ilike(f"%{case_id}%"))
    if q:
        pattern = f"%{q}%"
        join_inst()
        stmt = stmt.where(or_(models.Case.raw_institution_text.ilike(pattern), models.Case.case_id.ilike(pattern), models.Institution.name.ilike(pattern), models.Institution.aicte_permanent_id.ilike(pattern)))
    if bureau_id:
        stmt = stmt.where(models.Case.bureau_id == bureau_id)
    if bureaus:
        codes = [b.strip().upper() for b in bureaus.split(",") if b.strip()]
        bureau_ids = db.scalars(select(models.Bureau.id).where(models.Bureau.code.in_(codes))).all()
        stmt = stmt.where(models.Case.bureau_id.in_(bureau_ids or [-1]))
    if category:
        stmt = stmt.where(models.Case.category == models.CaseCategory(category))
    if status:
        stmt = stmt.where(models.Case.status == models.CaseStatus(status))
    if source_type:
        stmt = stmt.where(models.Case.source_type == source_type)
    if date_from:
        stmt = stmt.where(models.Case.date_received >= date_from)
    if date_to:
        stmt = stmt.where(models.Case.date_received <= date_to)
    if min_age_days:
        stmt = stmt.where(models.Case.date_received <= datetime.utcnow() - timedelta(days=min_age_days))
    if aicte_id:
        join_inst()
        stmt = stmt.where(models.Institution.aicte_permanent_id.ilike(f"%{aicte_id}%"))
    region_list = []
    if region:
        region_list.append(region)
    if regions:
        region_list.extend([r.strip() for r in regions.split(",") if r.strip()])
    if region_list and can_see_all(current):
        join_inst()
        stmt = stmt.where(models.Institution.region.in_(region_list))
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            join_inst()
            stmt = stmt.where(models.Institution.region == current.region)
        elif current.bureau_id:
            stmt = stmt.where(models.Case.bureau_id == current.bureau_id)
        else:
            stmt = stmt.where(False)
    if overdue:
        cutoff = datetime.utcnow() - timedelta(days=90)
        stmt = stmt.where(models.Case.date_received <= cutoff)
        stmt = stmt.where(models.Case.status.in_([models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]))
    if overlap_only:
        alerts = db.scalars(select(models.OverlapAlert)).all()
        flat = {cid for a in alerts for cid in (a.case_ids or [])}
        inst_ids = {a.institution_id for a in alerts}
        conditions = [models.Case.id.in_(flat)] if flat else []
        if inst_ids:
            conditions.append(models.Case.institution_id.in_(inst_ids))
        stmt = stmt.where(or_(*conditions)) if conditions else stmt.where(False)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    sort_map = {
        "date_received": models.Case.date_received.desc(),
        "case_id": models.Case.case_id.asc(),
        "status": models.Case.status.asc(),
        "ageing": models.Case.date_received.asc(),
    }
    items = db.scalars(stmt.order_by(sort_map.get(sort, models.Case.date_received.desc())).offset((page - 1) * limit).limit(limit)).all()
    out = []
    for c in items:
        days = (datetime.utcnow() - c.date_received).days
        out.append(
            {
                "id": c.id,
                "case_id": c.case_id,
                "source_channel": c.source_channel.value,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "language": c.language,
                "raw_institution_text": c.raw_institution_text,
                "subject": c.subject,
                "category": c.category.value,
                "category_subtype": c.category_subtype,
                "complainant_type": c.complainant_type,
                "narrative_preview": " ".join((c.narrative or "").split())[:240],
                "status": c.status.value,
                "outcome_tag": c.outcome_tag.value if c.outcome_tag else None,
                "bureau_id": c.bureau_id,
                "bureau_code": c.bureau.code if c.bureau else None,
                "institution_id": c.institution_id,
                "institution_name": c.institution.name if c.institution else None,
                "aicte_permanent_id": c.institution.aicte_permanent_id if c.institution else None,
                "date_received": c.date_received.isoformat(),
                "days_open": days,
                "is_overdue": days >= 90,
                "resolution_status": c.resolution_status.value,
                "match_confidence": c.match_confidence,
                "last_action_text": c.last_action_text,
                "next_action_text": c.next_action_text,
                "is_synthetic": bool(c.is_synthetic),
            }
        )
    return {"items": out, "total": total, "page": page, "limit": limit}


@router.post("")
def create_case(body: CaseCreate, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    if db.scalar(select(models.Case).where(models.Case.idempotency_key == body.idempotency_key)):
        raise HTTPException(status_code=409, detail="Duplicate idempotency_key")
    if db.scalar(select(models.Case).where(models.Case.case_id == body.case_id)):
        raise HTTPException(status_code=409, detail="case_id already exists")
    resolver = InstitutionResolver(db)
    language = body.language or detect_language(body.narrative)
    translated = translate_text(body.narrative, language)
    inst, conf, candidates = resolver.resolve(translated + " " + body.raw_institution_text, body.hints or {})
    resolution_status = models.ResolutionStatus.RESOLVED if inst else models.ResolutionStatus.NEEDS_REVIEW if candidates else models.ResolutionStatus.UNRESOLVED
    if resolution_status == models.ResolutionStatus.RESOLVED and conf < 0.9:
        resolution_status = models.ResolutionStatus.NEEDS_REVIEW
    case = models.Case(
        case_id=body.case_id,
        source_channel=models.SourceChannel(body.source_channel),
        institution_id=inst.id if inst else None,
        raw_institution_text=body.raw_institution_text,
        category=models.CaseCategory(body.category),
        narrative=body.narrative,
        status=models.CaseStatus.PENDING,
        bureau_id=body.bureau_id,
        assigned_officer_id=body.assigned_officer_id,
        date_received=body.date_received or datetime.utcnow(),
        expected_disposal_date=body.expected_disposal_date,
        resolution_status=resolution_status,
        match_confidence=conf,
        idempotency_key=body.idempotency_key,
        source_type=models.SourceType.MANUAL.value,
        is_synthetic=False,
        source_name="manual",
        complainant_hash=hash_identifier(body.complainant_identifier),
        language=language,
        narrative_original=body.narrative,
        narrative_translated=translated,
        last_action_at=datetime.utcnow(),
        last_action_text="Case created",
    )
    db.add(case)
    db.flush()
    prev = "0" * 64
    payload = {"action": "CREATED", "case_id": case.case_id, "at": datetime.utcnow().isoformat()}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.CREATED,
        remarks="Case created",
        prev_hash=prev,
        hash=compute_hash(prev, payload),
    )
    db.add(action)
    if resolution_status == models.ResolutionStatus.RESOLVED and inst and conf < 0.9:
        payload2 = {"action": "INSTITUTION_RESOLVED", "conf": conf}
        action2 = models.CaseAction(
            case_id=case.id,
            actor_user_id=current.id,
            bureau_id=case.bureau_id,
            action_type=models.ActionType.INSTITUTION_RESOLVED,
            remarks=f"Auto-resolved with confidence {conf:.3f}",
            prev_hash=action.hash,
            hash=compute_hash(action.hash, payload2),
        )
        db.add(action2)
    if resolution_status == models.ResolutionStatus.NEEDS_REVIEW and candidates:
        cand_out = [{"institution_id": c.institution.id, "name": c.institution.name, "aicte_permanent_id": c.institution.aicte_permanent_id, "score": c.score, "reasons": c.reasons} for c in candidates]
        rq = models.ReviewQueue(case_id=case.id, candidate_institutions=cand_out, status=models.ReviewStatus.OPEN)
        db.add(rq)
    db.commit()
    db.refresh(case)
    if inst:
        try:
            OverlapService(db).detect_for_case(case, current.id)
        except Exception:
            pass
    try:
        detect_cross_channel_duplicates(db, case, current.id)
    except Exception:
        pass
    return {"id": case.id, "case_id": case.case_id, "resolution_status": case.resolution_status.value, "institution_id": case.institution_id, "match_confidence": case.match_confidence, "source_type": case.source_type}


@router.get("/{id}")
def get_case(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            if not case.institution or case.institution.region != current.region:
                raise HTTPException(status_code=403, detail="Region scope violation")
        elif current.bureau_id and case.bureau_id != current.bureau_id:
            raise HTTPException(status_code=403, detail="Bureau scope violation")
    actions = []
    for a in case.actions:
        actions.append(
            {
                "id": a.id,
                "action_type": a.action_type.value,
                "remarks": a.remarks,
                "document_url": a.document_url,
                "created_at": a.created_at.isoformat(),
                "actor": a.actor.name if a.actor else None,
                "bureau_code": a.bureau.code if a.bureau else None,
                "prev_hash": a.prev_hash,
                "hash": a.hash,
            }
        )
    links = []
    for l in db.scalars(select(models.CaseLink).where(or_(models.CaseLink.case_a_id == case.id, models.CaseLink.case_b_id == case.id))).all():
        other = l.case_b_id if l.case_a_id == case.id else l.case_a_id
        oc = db.get(models.Case, other)
        links.append({"id": l.id, "other_case_id": other, "other_case_number": oc.case_id if oc else None, "other_bureau": oc.bureau.code if oc and oc.bureau else None, "link_type": l.link_type.value, "similarity_score": l.similarity_score})
    if case.category == models.CaseCategory.RAGGING_DISCRIMINATION:
        db.add(models.AuditAccessLog(user_id=current.id, resource_type="case_sensitive", resource_id=str(case.id), reason="Sensitive narrative access on case detail"))
        db.commit()
    return {
        "id": case.id,
        "case_id": case.case_id,
        "source_channel": case.source_channel.value,
        "source_type": case.source_type,
        "source_name": case.source_name,
        "source_record_id": case.source_record_id,
        "raw_payload_id": case.raw_payload_id,
        "language": case.language,
        "narrative_original": case.narrative_original or case.narrative,
        "narrative_translated": case.narrative_translated,
        "raw_institution_text": case.raw_institution_text,
        "subject": case.subject,
        "institution": {"id": case.institution.id, "name": case.institution.name, "aicte_permanent_id": case.institution.aicte_permanent_id} if case.institution else None,
        "category": case.category.value,
        "category_subtype": case.category_subtype,
        "complainant_type": case.complainant_type,
        "is_synthetic": bool(case.is_synthetic),
        "narrative": _mask_narrative(case, current),
        "status": case.status.value,
        "outcome_tag": case.outcome_tag.value if case.outcome_tag else None,
        "bureau": {"id": case.bureau.id, "code": case.bureau.code, "name": case.bureau.name} if case.bureau else None,
        "assigned_officer_id": case.assigned_officer_id,
        "assigned_officer": case.assigned_officer.name if case.assigned_officer else None,
        "date_received": case.date_received.isoformat(),
        "last_action_at": case.last_action_at.isoformat(),
        "last_action_text": case.last_action_text,
        "next_action_text": case.next_action_text,
        "expected_disposal_date": case.expected_disposal_date.isoformat() if case.expected_disposal_date else None,
        "resolution_status": case.resolution_status.value,
        "match_confidence": case.match_confidence,
        "days_open": (datetime.utcnow() - case.date_received).days,
        "is_overdue": (datetime.utcnow() - case.date_received).days >= 90,
        "actions": actions,
        "links": links,
    }


@router.patch("/{id}/status")
def update_status(id: int, body: StatusUpdate, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if body.outcome_tag:
        conflicts = find_conflicting_outcomes(db, case, models.OutcomeTag(body.outcome_tag))
        if conflicts and not body.acknowledge_conflict:
            raise HTTPException(status_code=409, detail={"message": "Conflicting Outcome Warning", "conflicts": conflicts, "requires_acknowledgement": True})
        case.outcome_tag = models.OutcomeTag(body.outcome_tag)
    prev_status = case.status
    case.status = models.CaseStatus(body.status)
    case.last_action_at = datetime.utcnow()
    case.last_action_text = f"Status changed to {body.status}"
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    payload = {"action": "STATUS_CHANGED", "from": prev_status.value, "to": body.status, "at": datetime.utcnow().isoformat()}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.STATUS_CHANGED,
        remarks=body.remarks or f"Status changed from {prev_status.value} to {body.status}",
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    db.add(action)
    db.commit()
    try:
        OverlapService(db).detect_for_case(case, current.id)
    except Exception:
        pass
    return {"ok": True}


@router.post("/{id}/outcome")
def set_outcome(id: int, body: OutcomeUpdate, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    tag = models.OutcomeTag(body.outcome_tag)
    conflicts = find_conflicting_outcomes(db, case, tag)
    if conflicts and not body.acknowledge_conflict:
        raise HTTPException(status_code=409, detail={"message": "Conflicting Outcome Warning", "conflicts": conflicts, "requires_acknowledgement": True})
    if conflicts and not body.remarks.strip():
        raise HTTPException(status_code=400, detail="A remark is mandatory to acknowledge a conflicting outcome")
    case.outcome_tag = tag
    case.last_action_at = datetime.utcnow()
    case.last_action_text = f"Outcome tagged {tag.value}"
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    remarks = body.remarks or f"Outcome set to {tag.value}"
    if conflicts:
        remarks += " | Conflicting Outcome Warning acknowledged. Conflicts: " + "; ".join(f"{c['case_id']} ({c['outcome_tag']})" for c in conflicts)
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.OUTCOME_TAGGED,
        remarks=remarks,
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, {"action": "OUTCOME_TAGGED", "tag": tag.value, "conflicts": conflicts, "acknowledged": bool(conflicts)}),
    )
    db.add(action)
    db.commit()
    return {"ok": True, "outcome_tag": tag.value, "conflicts_acknowledged": conflicts}


@router.post("/{id}/transfer")
def transfer_case(id: int, body: Transfer, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    from_bureau = case.bureau_id
    case.bureau_id = body.to_bureau_id
    case.status = models.CaseStatus.TRANSFERRED
    case.last_action_at = datetime.utcnow()
    case.last_action_text = "Case transferred"
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    payload = {"action": "TRANSFERRED", "from_bureau": from_bureau, "to_bureau": body.to_bureau_id}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.TRANSFERRED,
        remarks=body.remarks or "Transferred to another bureau",
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    db.add(action)
    db.commit()
    try:
        OverlapService(db).detect_for_case(case, current.id)
    except Exception:
        pass
    return {"ok": True}


@router.post("/{id}/escalate")
def escalate_case(id: int, body: Escalate, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.status = models.CaseStatus.ESCALATED
    case.last_action_at = datetime.utcnow()
    case.last_action_text = "Case escalated"
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    payload = {"action": "ESCALATED", "at": datetime.utcnow().isoformat()}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.ESCALATED,
        remarks=body.remarks or "Escalated",
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    db.add(action)
    db.commit()
    try:
        OverlapService(db).detect_for_case(case, current.id)
    except Exception:
        pass
    return {"ok": True}


@router.post("/{id}/remarks")
def add_remark(id: int, body: Remark, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.last_action_at = datetime.utcnow()
    case.last_action_text = "Remark added"
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    action_type = models.ActionType.DOCUMENT_ADDED if body.document_url else models.ActionType.REMARK
    payload = {"action": action_type.value, "remarks": body.remarks[:100]}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=action_type,
        remarks=body.remarks,
        document_url=body.document_url,
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    db.add(action)
    db.commit()
    return {"ok": True}


@router.post("/{id}/link")
def link_case(id: int, body: LinkCase, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    case = db.get(models.Case, id)
    other = db.get(models.Case, body.other_case_id)
    if not case or not other:
        raise HTTPException(status_code=404, detail="Case not found")
    pair = (min(case.id, other.id), max(case.id, other.id))
    link = models.CaseLink(
        case_a_id=pair[0],
        case_b_id=pair[1],
        link_type=models.LinkType(body.link_type),
        similarity_score=body.similarity_score,
        created_by=current.id,
    )
    db.add(link)
    last = case.actions[-1] if case.actions else None
    prev_hash = last.hash if last else "0" * 64
    payload = {"action": "LINKED", "to": other.id}
    action = models.CaseAction(
        case_id=case.id,
        actor_user_id=current.id,
        bureau_id=case.bureau_id,
        action_type=models.ActionType.LINKED,
        remarks=f"Linked to case {other.case_id}",
        prev_hash=prev_hash,
        hash=compute_hash(prev_hash, payload),
    )
    db.add(action)
    db.commit()
    return {"ok": True}
