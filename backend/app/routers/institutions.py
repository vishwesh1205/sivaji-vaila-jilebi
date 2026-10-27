from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, can_see_all, apply_region_scope
from ..services.risk import compute_institution_risk, top_risk_institutions
from ..services.pdf import build_institution_brief

router = APIRouter()


@router.get("")
def list_institutions(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
    q: str | None = Query(default=None),
    state: str | None = Query(default=None),
    region: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    stmt = select(models.Institution)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where((models.Institution.name.ilike(pattern)) | (models.Institution.aicte_permanent_id.ilike(pattern)))
    if state:
        stmt = stmt.where(models.Institution.state == state)
    if region and can_see_all(current):
        stmt = stmt.where(models.Institution.region == region)
    if current.role == models.UserRole.REGIONAL_OFFICER and current.region and not can_see_all(current):
        stmt = stmt.where(models.Institution.region == current.region)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    result = []
    for inst in items:
        case_count = db.scalar(select(func.count(models.Case.id)).where(models.Case.institution_id == inst.id)) or 0
        active = db.scalar(
            select(func.count(models.Case.id)).where(
                models.Case.institution_id == inst.id,
                models.Case.status.in_([models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]),
            )
        ) or 0
        overlap = db.scalar(select(func.count(models.OverlapAlert.id)).where(models.OverlapAlert.institution_id == inst.id, models.OverlapAlert.status.in_([models.AlertStatus.OPEN, models.AlertStatus.ACKNOWLEDGED]))) or 0
        risk = compute_institution_risk(db, inst.id)
        result.append(
            {
                "id": inst.id,
                "aicte_permanent_id": inst.aicte_permanent_id,
                "name": inst.name,
                "address": inst.address,
                "city": inst.city,
                "state": inst.state,
                "region": inst.region,
                "approval_status": inst.approval_status,
                "programme_mix": inst.programme_mix,
                "source_type": inst.source_type,
                "is_synthetic": inst.is_synthetic,
                "risk_score": risk["score"],
                "risk_breakdown": risk["breakdown"],
                "case_count": case_count,
                "active_count": active,
                "has_overlap": overlap > 0,
            }
        )
    return {"items": result, "total": total, "page": page, "limit": limit}


@router.get("/{id}")
def get_institution(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    inst = db.get(models.Institution, id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    if current.role == models.UserRole.REGIONAL_OFFICER and current.region and inst.region != current.region and not can_see_all(current):
        raise HTTPException(status_code=403, detail="Region scope violation")
    return {
        "id": inst.id,
        "aicte_permanent_id": inst.aicte_permanent_id,
        "name": inst.name,
        "normalized_name": inst.normalized_name,
        "address": inst.address,
        "city": inst.city,
        "state": inst.state,
        "region": inst.region,
        "university_affiliation": inst.university_affiliation,
        "approval_status": inst.approval_status,
        "programme_mix": inst.programme_mix,
        "aliases": inst.aliases,
        "source_type": inst.source_type,
        "is_synthetic": inst.is_synthetic,
    }


@router.get("/{id}/risk")
def institution_risk(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    inst = db.get(models.Institution, id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    if current.role == models.UserRole.REGIONAL_OFFICER and current.region and inst.region != current.region and not can_see_all(current):
        raise HTTPException(status_code=403, detail="Region scope violation")
    return compute_institution_risk(db, id)


@router.get("/{id}/brief")
def institution_brief(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    inst = db.get(models.Institution, id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    if current.role == models.UserRole.REGIONAL_OFFICER and current.region and inst.region != current.region and not can_see_all(current):
        raise HTTPException(status_code=403, detail="Region scope violation")
    pdf = build_institution_brief(db, inst)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=institution-brief-{inst.aicte_permanent_id}.pdf"})


@router.get("/{id}/360")
def institution_360(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    inst = db.get(models.Institution, id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    if current.role == models.UserRole.REGIONAL_OFFICER and current.region and inst.region != current.region and not can_see_all(current):
        raise HTTPException(status_code=403, detail="Region scope violation")
    cases = db.scalars(select(models.Case).where(models.Case.institution_id == id).order_by(models.Case.date_received.desc())).all()
    alerts = db.scalars(select(models.OverlapAlert).where(models.OverlapAlert.institution_id == id).order_by(models.OverlapAlert.created_at.desc())).all()
    timeline = []
    for c in cases:
        for a in c.actions:
            timeline.append(
                {
                    "type": "action",
                    "case_id": c.case_id,
                    "action_type": a.action_type.value,
                    "remarks": a.remarks,
                    "created_at": a.created_at.isoformat(),
                    "actor": a.actor.name if a.actor else None,
                    "bureau": a.bureau.code if a.bureau else (c.bureau.code if c.bureau else None),
                }
            )
    timeline.sort(key=lambda x: x["created_at"])
    return {
        "institution": {
            "id": inst.id,
            "aicte_permanent_id": inst.aicte_permanent_id,
            "name": inst.name,
            "address": inst.address,
            "city": inst.city,
            "state": inst.state,
            "region": inst.region,
            "university_affiliation": inst.university_affiliation,
            "approval_status": inst.approval_status,
            "programme_mix": inst.programme_mix,
            "source_type": inst.source_type,
            "is_synthetic": inst.is_synthetic,
        },
        "risk": compute_institution_risk(db, inst.id),
        "regulatory_posture": {
            "total_cases": len(cases),
            "active": sum(1 for c in cases if c.status in [models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]),
            "disposed": sum(1 for c in cases if c.status == models.CaseStatus.DISPOSED),
            "overlap_alerts": len(alerts),
            "risk_score": compute_institution_risk(db, inst.id)["score"],
        },
        "cases": [
            {
                "id": c.id,
                "case_id": c.case_id,
                "source_channel": c.source_channel.value,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "language": c.language,
                "category": c.category.value,
                "status": c.status.value,
                "bureau_id": c.bureau_id,
                "bureau_code": c.bureau.code if c.bureau else None,
                "date_received": c.date_received.isoformat(),
                "last_action_at": c.last_action_at.isoformat(),
                "last_action_text": c.last_action_text,
                "next_action_text": c.next_action_text,
                "resolution_status": c.resolution_status.value,
                "match_confidence": c.match_confidence,
            }
            for c in cases
        ],
        "alerts": [
            {"id": a.id, "status": a.status.value, "bureaus_involved": a.bureaus_involved, "why_flagged": a.why_flagged, "created_at": a.created_at.isoformat()}
            for a in alerts
        ],
        "timeline": timeline,
    }
