from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, can_see_all
from ..services.risk import top_risk_institutions
from ..services.emerging import compute_emerging_issues

router = APIRouter()


@router.get("/summary")
def summary(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    stmt = select(models.Case)
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
        elif current.bureau_id:
            stmt = stmt.where(models.Case.bureau_id == current.bureau_id)
        else:
            return {"total": 0}
    cases = db.scalars(stmt).all()
    total = len(cases)
    pending = sum(1 for c in cases if c.status == models.CaseStatus.PENDING)
    under = sum(1 for c in cases if c.status == models.CaseStatus.UNDER_PROCESS)
    disposed = sum(1 for c in cases if c.status == models.CaseStatus.DISPOSED)
    transferred = sum(1 for c in cases if c.status == models.CaseStatus.TRANSFERRED)
    escalated = sum(1 for c in cases if c.status == models.CaseStatus.ESCALATED)
    beyond = sum(1 for c in cases if c.status in [models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED] and (datetime.utcnow() - c.date_received).days >= 90)
    overlap_stmt = select(models.OverlapAlert).where(models.OverlapAlert.status.in_([models.AlertStatus.OPEN, models.AlertStatus.ACKNOWLEDGED]))
    if not can_see_all(current) and current.role == models.UserRole.REGIONAL_OFFICER and current.region:
        overlap_stmt = overlap_stmt.join(models.Institution).where(models.Institution.region == current.region)
    overlap_count = db.scalar(select(func.count()).select_from(overlap_stmt.subquery())) or 0
    disposal_rate = round((disposed / total * 100), 1) if total else 0.0
    return {
        "total": total,
        "pending": pending,
        "under_process": under,
        "disposed": disposed,
        "transferred": transferred,
        "escalated": escalated,
        "beyond_timeline": beyond,
        "overlap_alerts_active": overlap_count,
        "disposal_rate": disposal_rate,
    }


@router.get("/bureau-workload")
def bureau_workload(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    bureaus = db.scalars(select(models.Bureau)).all()
    res = []
    for b in bureaus:
        stmt = select(models.Case).where(models.Case.bureau_id == b.id)
        if not can_see_all(current):
            if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
                stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
            elif current.bureau_id and current.bureau_id != b.id and current.role != models.UserRole.ADMIN and current.role != models.UserRole.MANAGEMENT:
                continue
        cases = db.scalars(stmt).all()
        res.append({"bureau_code": b.code, "bureau_name": b.name, "total": len(cases), "pending": sum(1 for c in cases if c.status == models.CaseStatus.PENDING), "under_process": sum(1 for c in cases if c.status == models.CaseStatus.UNDER_PROCESS), "escalated": sum(1 for c in cases if c.status == models.CaseStatus.ESCALATED)})
    return res


@router.get("/ageing")
def ageing(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    stmt = select(models.Case).where(models.Case.status.in_([models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]))
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
        elif current.bureau_id:
            stmt = stmt.where(models.Case.bureau_id == current.bureau_id)
    cases = db.scalars(stmt).all()
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for c in cases:
        days = (datetime.utcnow() - c.date_received).days
        if days <= 30:
            buckets["0-30"] += 1
        elif days <= 60:
            buckets["31-60"] += 1
        elif days <= 90:
            buckets["61-90"] += 1
        else:
            buckets["90+"] += 1
    return buckets


@router.get("/trends")
def trends(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    stmt = select(models.Case)
    if not can_see_all(current):
        if current.role == models.UserRole.REGIONAL_OFFICER and current.region:
            stmt = stmt.join(models.Institution).where(models.Institution.region == current.region)
        elif current.bureau_id:
            stmt = stmt.where(models.Case.bureau_id == current.bureau_id)
    cases = db.scalars(stmt).all()
    months = {}
    for c in cases:
        key = c.date_received.strftime("%Y-%m")
        months[key] = months.get(key, 0) + 1
    out = sorted([{"month": k, "count": v} for k, v in months.items()])
    return out


@router.get("/institution-wise")
def institution_wise(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    stmt = select(models.Institution)
    if not can_see_all(current) and current.role == models.UserRole.REGIONAL_OFFICER and current.region:
        stmt = stmt.where(models.Institution.region == current.region)
    insts = db.scalars(stmt).all()
    res = []
    for inst in insts:
        cases = db.scalars(select(models.Case).where(models.Case.institution_id == inst.id)).all()
        if not cases:
            continue
        bureaus = sorted(set([c.bureau.code for c in cases if c.bureau]))
        statuses = sorted(set([c.status.value for c in cases]))
        res.append({"institution": inst.name, "aicte_permanent_id": inst.aicte_permanent_id, "bureaus": bureaus, "status": ", ".join(statuses), "case_count": len(cases), "active": sum(1 for c in cases if c.status in [models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED])})
    return res[:50]


@router.get("/region-wise")
def region_wise(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    stmt = select(models.Institution)
    insts = db.scalars(stmt).all()
    by_region = {}
    for inst in insts:
        r = inst.region
        by_region.setdefault(r, []).append(inst.id)
    res = []
    for r, ids in by_region.items():
        cases = db.scalars(select(models.Case).where(models.Case.institution_id.in_(ids))).all()
        res.append({"region": r, "institutions": len(ids), "cases": len(cases), "pending": sum(1 for c in cases if c.status == models.CaseStatus.PENDING), "disposed": sum(1 for c in cases if c.status == models.CaseStatus.DISPOSED)})
    return res


@router.get("/proof-summary")
def proof_summary(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    since = datetime.utcnow() - timedelta(hours=24)
    cases = db.scalars(select(models.Case).where(models.Case.created_at >= since)).all()
    counts = {"css": 0, "cpgrams": 0, "manual": 0, "file_upload": 0, "seed_simulator": 0}
    for c in cases:
        if c.source_name == "css":
            counts["css"] += 1
        elif c.source_name == "cpgrams":
            counts["cpgrams"] += 1
        elif c.source_type == models.SourceType.FILE_UPLOAD.value:
            counts["file_upload"] += 1
        elif c.source_type == models.SourceType.SIMULATOR.value:
            counts["seed_simulator"] += 1
        else:
            counts["manual"] += 1
    stats = db.scalars(select(models.PublicStat).order_by(models.PublicStat.fetched_at.desc()).limit(20)).all()
    snapshot = any(s.is_snapshot for s in stats)
    latest_stats_at = max([s.fetched_at for s in stats], default=None)
    return {
        "window_hours": 24,
        "css": counts["css"],
        "cpgrams": counts["cpgrams"],
        "manual": counts["manual"],
        "file_upload": counts["file_upload"],
        "seed_simulator": counts["seed_simulator"],
        "public_stats": len(stats),
        "public_stats_mode": "SNAPSHOT" if snapshot else ("LIVE" if stats else "NO_DATA"),
        "latest_public_stats_at": latest_stats_at.isoformat() if latest_stats_at else None,
        "note": "Source types are labeled honestly; simulator counts are not live public data.",
        "simulator_counts": {
            "css": db.scalar(select(func.count(models.Case.id)).where(models.Case.source_name == "css", models.Case.source_type == "SIMULATOR", models.Case.created_at >= since)) or 0,
            "cpgrams": db.scalar(select(func.count(models.Case.id)).where(models.Case.source_name == "cpgrams", models.Case.source_type == "SIMULATOR", models.Case.created_at >= since)) or 0,
        },
    }


@router.get("/top-risk")
def top_risk(limit: int = 8, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    rows = top_risk_institutions(db, limit)
    if not can_see_all(current) and current.role == models.UserRole.REGIONAL_OFFICER and current.region:
        for row in rows:
            inst = db.get(models.Institution, row["institution_id"])
            row["_visible"] = bool(inst and inst.region == current.region)
        rows = [r for r in rows if r.pop("_visible", True)]
    return rows


@router.get("/emerging-issues")
def emerging(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    return compute_emerging_issues(db)
