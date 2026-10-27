from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, can_see_all
from ..services.emerging import compute_emerging_issues
from ..services.impact import simulate_impact
from ..services.query_parser import parse_query
from ..services.risk import top_risk_institutions

router = APIRouter()


class QueryBody(BaseModel):
    query: str


@router.post("/query/parse")
def query_parse(body: QueryBody):
    return parse_query(body.query)


@router.post("/query/execute")
def query_execute(body: QueryBody, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    parsed = parse_query(body.query)
    f = parsed["filters"]
    stmt = select(models.Case)
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
        elif current.bureau_id:
            stmt = stmt.where(models.Case.bureau_id == current.bureau_id)
    if f.get("bureaus"):
        bureaus = db.scalars(select(models.Bureau).where(models.Bureau.code.in_(f["bureaus"]))).all()
        stmt = stmt.where(models.Case.bureau_id.in_([b.id for b in bureaus]))
    if f.get("category"):
        stmt = stmt.where(models.Case.category == models.CaseCategory(f["category"]))
    if f.get("status"):
        stmt = stmt.where(models.Case.status == models.CaseStatus(f["status"]))
    if f.get("aicte_id") or f.get("regions"):
        stmt = stmt.join(models.Institution, models.Case.institution_id == models.Institution.id, isouter=True)
        if f.get("aicte_id"):
            stmt = stmt.where(models.Institution.aicte_permanent_id == f["aicte_id"])
        if f.get("regions"):
            stmt = stmt.where(models.Institution.region.in_(f["regions"]))
    if f.get("min_age_days"):
        stmt = stmt.where(models.Case.date_received <= datetime.utcnow() - timedelta(days=f["min_age_days"]))
    if f.get("case_id"):
        stmt = stmt.where(models.Case.case_id.ilike(f"%{f['case_id']}%"))
    if f.get("q"):
        stmt = stmt.where(or_(models.Case.raw_institution_text.ilike(f"%{f['q']}%"), models.Case.case_id.ilike(f"%{f['q']}%")))
    cases = db.scalars(stmt.order_by(models.Case.date_received.desc()).limit(100)).all()
    if f.get("overlap_only"):
        alerts = db.scalars(select(models.OverlapAlert)).all()
        allowed = {cid for a in alerts for cid in a.case_ids}
        # overlap at institution level: include all cases for institutions with alerts
        allowed_inst = {a.institution_id for a in alerts}
        cases = [c for c in cases if c.id in allowed or c.institution_id in allowed_inst]
    target = "institutions" if "institution" in body.query.lower() else "cases"
    if target == "institutions":
        inst_ids = sorted({c.institution_id for c in cases if c.institution_id})
        insts = db.scalars(select(models.Institution).where(models.Institution.id.in_(inst_ids))).all() if inst_ids else []
        results = [{"id": i.id, "name": i.name, "aicte_permanent_id": i.aicte_permanent_id, "region": i.region, "source_type": i.source_type, "is_synthetic": i.is_synthetic} for i in insts]
    else:
        results = [{"id": c.id, "case_id": c.case_id, "source_type": c.source_type, "source_name": c.source_name, "bureau_code": c.bureau.code if c.bureau else None, "subject": c.subject, "category": c.category.value, "category_subtype": c.category_subtype, "complainant_type": c.complainant_type, "narrative_preview": " ".join((c.narrative or "").split())[:240], "status": c.status.value, "institution_name": c.institution.name if c.institution else c.raw_institution_text, "date_received": c.date_received.isoformat(), "is_synthetic": bool(c.is_synthetic)} for c in cases]
    return {**parsed, "target": target, "result_count": len(results), "results": results}


@router.get("/emerging-issues")
def emerging_issues(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    return compute_emerging_issues(db)


@router.get("/risk/top")
def risk_top(limit: int = Query(default=8, ge=1, le=50), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    return top_risk_institutions(db, limit)


@router.get("/impact-simulator")
def impact_simulator(discovery_delay_days: int = Query(default=14, ge=1, le=90), seed: int = Query(default=42), duplicate_hours_saved: float = Query(default=6.0, ge=0, le=40), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    return simulate_impact(db, discovery_delay_days=discovery_delay_days, seed=seed, duplicate_hours_saved=duplicate_hours_saved)
