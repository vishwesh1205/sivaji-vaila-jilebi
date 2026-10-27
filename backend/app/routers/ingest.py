import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user
from ..hash_chain import compute_hash
from ..services.overlap import OverlapService
from ..services.resolution import InstitutionResolver

router = APIRouter()


class IngestJSON(BaseModel):
    items: list[dict]


@router.post("/csv")
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except Exception:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    resolver = InstitutionResolver(db)
    created = 0
    duplicates = 0
    auto_linked = 0
    review = 0
    unresolved = 0
    for row in reader:
        case_id = row.get("case_id") or row.get("Case ID") or row.get("Complaint No") or row.get("Registration No")
        if not case_id:
            continue
        idempotency_key = f"csv:{file.filename}:{case_id}:{row.get('Date') or row.get('date_received') or ''}"
        if db.scalar(select(models.Case).where(models.Case.idempotency_key == idempotency_key)) or db.scalar(select(models.Case).where(models.Case.case_id == case_id)):
            duplicates += 1
            continue
        raw_inst = row.get("institution") or row.get("Institution") or row.get("college_name") or row.get("Name of Institution") or ""
        narrative = row.get("narrative") or row.get("Narrative") or row.get("Grievance") or row.get("Description") or raw_inst
        category = (row.get("category") or row.get("Category") or "OTHER").upper().replace(" ", "_")
        if category not in [c.value for c in models.CaseCategory]:
            category = "OTHER"
        source = (row.get("source_channel") or row.get("Source") or "CSS").upper()
        if source not in [s.value for s in models.SourceChannel]:
            source = "CSS"
        bureau_code = (row.get("bureau") or row.get("Bureau") or row.get("Cell") or "RB").upper()
        bureau = db.scalar(select(models.Bureau).where(models.Bureau.code == bureau_code)) or db.scalar(select(models.Bureau))
        if not bureau:
            raise HTTPException(status_code=400, detail="No bureaus found")
        inst, conf, candidates = resolver.resolve(raw_inst, {"region": row.get("Region") or row.get("region")})
        resolution_status = models.ResolutionStatus.RESOLVED if inst else (models.ResolutionStatus.NEEDS_REVIEW if candidates else models.ResolutionStatus.UNRESOLVED)
        if resolution_status == models.ResolutionStatus.RESOLVED and conf >= 0.9:
            auto_linked += 1
        elif resolution_status == models.ResolutionStatus.NEEDS_REVIEW:
            review += 1
        else:
            unresolved += 1
        try:
            date_recv = datetime.fromisoformat(row.get("date_received") or row.get("Date Received") or row.get("Date") or "") if (row.get("date_received") or row.get("Date Received") or row.get("Date")) else datetime.utcnow()
        except Exception:
            date_recv = datetime.utcnow()
        case = models.Case(
            case_id=str(case_id),
            source_channel=models.SourceChannel(source),
            institution_id=inst.id if inst else None,
            raw_institution_text=raw_inst,
            category=models.CaseCategory(category),
            narrative=narrative,
            status=models.CaseStatus.PENDING,
            bureau_id=bureau.id,
            date_received=date_recv,
            resolution_status=resolution_status,
            match_confidence=conf,
            idempotency_key=idempotency_key,
            last_action_at=datetime.utcnow(),
            last_action_text="Case created via CSV import",
        )
        db.add(case)
        db.flush()
        prev = "0" * 64
        action = models.CaseAction(
            case_id=case.id,
            actor_user_id=current.id,
            bureau_id=case.bureau_id,
            action_type=models.ActionType.CREATED,
            remarks="Ingested via CSV",
            prev_hash=prev,
            hash=compute_hash(prev, {"action": "CREATED", "case_id": case.case_id}),
        )
        db.add(action)
        if resolution_status == models.ResolutionStatus.NEEDS_REVIEW and candidates:
            cand_out = [{"institution_id": c.institution.id, "name": c.institution.name, "aicte_permanent_id": c.institution.aicte_permanent_id, "score": c.score, "reasons": c.reasons} for c in candidates]
            rq = models.ReviewQueue(case_id=case.id, candidate_institutions=cand_out, status=models.ReviewStatus.OPEN)
            db.add(rq)
        created += 1
        if inst:
            try:
                OverlapService(db).detect_for_case(case, current.id)
            except Exception:
                pass
    db.commit()
    return {"created": created, "duplicates_skipped": duplicates, "auto_linked": auto_linked, "sent_to_review": review, "unresolved": unresolved}


@router.post("/json")
def ingest_json(body: IngestJSON, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    resolver = InstitutionResolver(db)
    created = 0
    duplicates = 0
    for item in body.items:
        case_id = item.get("case_id")
        if not case_id:
            continue
        idempotency_key = item.get("idempotency_key") or f"json:{case_id}"
        if db.scalar(select(models.Case).where(models.Case.idempotency_key == idempotency_key)) or db.scalar(select(models.Case).where(models.Case.case_id == case_id)):
            duplicates += 1
            continue
        raw_inst = item.get("raw_institution_text") or item.get("institution") or ""
        narrative = item.get("narrative") or raw_inst
        bureau = db.get(models.Bureau, item.get("bureau_id")) or db.scalar(select(models.Bureau))
        inst, conf, candidates = resolver.resolve(raw_inst, item.get("hints") or {})
        resolution_status = models.ResolutionStatus.RESOLVED if inst else (models.ResolutionStatus.NEEDS_REVIEW if candidates else models.ResolutionStatus.UNRESOLVED)
        case = models.Case(
            case_id=str(case_id),
            source_channel=models.SourceChannel(item.get("source_channel") or "DIRECT"),
            institution_id=inst.id if inst else None,
            raw_institution_text=raw_inst,
            category=models.CaseCategory(item.get("category") or "OTHER"),
            narrative=narrative,
            status=models.CaseStatus.PENDING,
            bureau_id=bureau.id,
            date_received=datetime.fromisoformat(item["date_received"]) if item.get("date_received") else datetime.utcnow(),
            resolution_status=resolution_status,
            match_confidence=conf,
            idempotency_key=idempotency_key,
            last_action_at=datetime.utcnow(),
            last_action_text="Case created via JSON import",
        )
        db.add(case)
        db.flush()
        prev = "0" * 64
        action = models.CaseAction(case_id=case.id, actor_user_id=current.id, bureau_id=case.bureau_id, action_type=models.ActionType.CREATED, remarks="Ingested via JSON", prev_hash=prev, hash=compute_hash(prev, {"action": "CREATED"}))
        db.add(action)
        if resolution_status == models.ResolutionStatus.NEEDS_REVIEW and candidates:
            cand_out = [{"institution_id": c.institution.id, "name": c.institution.name, "aicte_permanent_id": c.institution.aicte_permanent_id, "score": c.score, "reasons": c.reasons} for c in candidates]
            rq = models.ReviewQueue(case_id=case.id, candidate_institutions=cand_out, status=models.ReviewStatus.OPEN)
            db.add(rq)
        created += 1
        if inst:
            try:
                OverlapService(db).detect_for_case(case, current.id)
            except Exception:
                pass
    db.commit()
    return {"created": created, "duplicates_skipped": duplicates}
