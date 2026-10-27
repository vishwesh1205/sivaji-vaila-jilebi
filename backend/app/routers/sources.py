import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user
from ..events import bus, sse_format
from ..connectors.institution_master import InstitutionMasterImporter
from ..services.ingestion import SyncService, ensure_data_sources, get_connector, source_definition

router = APIRouter()


class ToggleBody(BaseModel):
    enabled: bool


@router.get("")
def list_sources(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    ensure_data_sources(db)
    sources = db.scalars(select(models.DataSource).order_by(models.DataSource.id)).all()
    out = []
    for s in sources:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.scalar(select(func.count(models.RawPayload.id)).where(models.RawPayload.source == s.name, models.RawPayload.fetched_at >= today)) or 0
        error_count = db.scalar(select(func.count(models.SyncRun.id)).where(models.SyncRun.source == s.name, models.SyncRun.status == "FAILED")) or 0
        next_sync = None
        if s.last_success_at and s.enabled:
            next_sync = (s.last_success_at + timedelta(seconds=s.interval_seconds)).isoformat()
        out.append({
            "id": s.id,
            "name": s.name,
            "kind": s.kind,
            "mode": s.mode,
            "source_type": s.source_type,
            "is_synthetic": s.source_type == "SIMULATOR",
            "base_url_masked": s.base_url_masked,
            "interval_seconds": s.interval_seconds,
            "enabled": s.enabled,
            "last_status": s.last_status,
            "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
            "last_error": s.last_error,
            "records_total": s.records_total,
            "records_today": today_count,
            "latency_ms_avg": s.latency_ms_avg,
            "error_count": error_count,
            "next_sync_at": next_sync,
        })
    return out


@router.post("/{name}/sync")
def sync_now(name: str, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    if current.role not in {models.UserRole.ADMIN, models.UserRole.MANAGEMENT}:
        raise HTTPException(status_code=403, detail="Only admin/management can trigger sync")
    if name == "institution_master":
        if settings.institution_master_url:
            try:
                result = InstitutionMasterImporter(db).import_from_url()
                return {"status": "SUCCESS", "source": name, **result}
            except Exception as e:
                raise HTTPException(status_code=502, detail=str(e))
        raise HTTPException(status_code=400, detail="Upload an institution master file or configure INSTITUTION_MASTER_URL")
    try:
        run = SyncService(db).sync(name, triggered_by=current.email)
        return {"id": run.id, "status": run.status, "fetched": run.fetched, "created": run.created, "duplicates_skipped": run.duplicates_skipped, "auto_linked": run.auto_linked, "sent_to_review": run.sent_to_review, "unresolved": run.unresolved, "latency_ms": run.latency_ms, "errors": run.errors_json}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{name}/enabled")
def toggle_source(name: str, body: ToggleBody, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    if current.role not in {models.UserRole.ADMIN, models.UserRole.MANAGEMENT}:
        raise HTTPException(status_code=403, detail="Only admin/management can change sources")
    s = db.scalar(select(models.DataSource).where(models.DataSource.name == name))
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    s.enabled = body.enabled
    db.commit()
    return {"ok": True, "enabled": s.enabled}


@router.get("/{name}/runs")
def runs(name: str, limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    rows = db.scalars(select(models.SyncRun).where(models.SyncRun.source == name).order_by(models.SyncRun.started_at.desc()).limit(limit)).all()
    return [{"id": r.id, "source": r.source, "started_at": r.started_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None, "status": r.status, "fetched": r.fetched, "created": r.created, "duplicates_skipped": r.duplicates_skipped, "auto_linked": r.auto_linked, "sent_to_review": r.sent_to_review, "unresolved": r.unresolved, "errors_json": r.errors_json, "latency_ms": r.latency_ms} for r in rows]


@router.get("/quality")
def quality(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    out = []
    for name in ["css", "cpgrams"]:
        cases = db.scalars(select(models.Case).where(models.Case.source_name == name)).all()
        total = len(cases)
        clean = sum(1 for c in cases if c.institution_id)
        auto = sum(1 for c in cases if c.resolution_status == models.ResolutionStatus.RESOLVED)
        review = sum(1 for c in cases if c.resolution_status == models.ResolutionStatus.NEEDS_REVIEW)
        raw = db.scalars(select(models.RawPayload).where(models.RawPayload.source == name)).all()
        latency = 0.0
        if cases and raw:
            diffs = []
            raw_by_id = {r.id: r for r in raw}
            for c in cases:
                if c.raw_payload_id and c.raw_payload_id in raw_by_id:
                    diffs.append((c.created_at - raw_by_id[c.raw_payload_id].fetched_at).total_seconds())
            latency = round(sum(diffs) / len(diffs), 2) if diffs else 0.0
        out.append({
            "source": name,
            "total": total,
            "clean_institution_pct": round(clean / total * 100, 1) if total else 0.0,
            "auto_resolved_pct": round(auto / total * 100, 1) if total else 0.0,
            "needs_review_pct": round(review / total * 100, 1) if total else 0.0,
            "avg_ingest_to_visible_seconds": latency,
        })
    return out


@router.get("/public-stats")
def public_stats(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    rows = db.scalars(select(models.PublicStat).order_by(models.PublicStat.fetched_at.desc())).all()
    latest: dict[tuple[str, str, str], models.PublicStat] = {}
    for r in rows:
        key = (r.source, r.dataset_key, r.period or "")
        if key not in latest:
            latest[key] = r
    return [{
        "id": r.id,
        "source": r.source,
        "dataset_key": r.dataset_key,
        "period": r.period,
        "dimension": r.dimension,
        "metrics": r.metrics_json,
        "fetched_at": r.fetched_at.isoformat(),
        "is_snapshot": r.is_snapshot,
    } for r in latest.values()]


@router.get("/raw")
def raw_payloads(source: str | None = None, limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    stmt = select(models.RawPayload).order_by(models.RawPayload.fetched_at.desc()).limit(limit)
    if source:
        stmt = select(models.RawPayload).where(models.RawPayload.source == source).order_by(models.RawPayload.fetched_at.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    return [{"id": r.id, "source": r.source, "source_record_id": r.source_record_id, "payload_sha256": r.payload_sha256, "source_type": r.source_type, "fetched_at": r.fetched_at.isoformat()} for r in rows]


@router.get("/raw/{id}")
def raw_payload(id: int, db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    r = db.get(models.RawPayload, id)
    if not r:
        raise HTTPException(status_code=404, detail="Raw payload not found")
    return {"id": r.id, "source": r.source, "source_record_id": r.source_record_id, "payload": r.payload_json, "payload_sha256": r.payload_sha256, "source_type": r.source_type, "fetched_at": r.fetched_at.isoformat()}


@router.post("/scenario-trigger")
def scenario_trigger(db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    if current.role not in {models.UserRole.ADMIN, models.UserRole.MANAGEMENT}:
        raise HTTPException(status_code=403, detail="Only admin/management can trigger demo scenario")
    results = {}
    with httpx.Client(timeout=settings.connector_timeout_seconds) as client:
        for name, url in [("cpgrams", settings.cpgrams_admin_url), ("css", settings.css_admin_url)]:
            try:
                r = client.post(f"{url.rstrip('/')}/admin/scenario")
                results[name] = r.json()
            except Exception as e:
                results[name] = {"error": str(e)}
    synced = {}
    for name in ["cpgrams", "css"]:
        try:
            run = SyncService(db).sync(name, triggered_by=current.email)
            synced[name] = {"created": run.created, "resolution": run.auto_linked, "review": run.sent_to_review, "status": run.status}
        except Exception as e:
            synced[name] = {"error": str(e)}
    return {"simulator": True, "banner": "SIMULATOR – synthetic scenario", "injections": results, "sync": synced}


@router.post("/institution_master/upload")
async def upload_master(file: UploadFile = File(...), db: Session = Depends(get_db), current: models.User = Depends(get_current_user)):
    if current.role not in {models.UserRole.ADMIN, models.UserRole.MANAGEMENT}:
        raise HTTPException(status_code=403, detail="Only admin/management can import institution master")
    content = await file.read()
    try:
        result = InstitutionMasterImporter(db).import_bytes(content, file.filename or "master.csv", source_type="FILE_UPLOAD")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    ds = db.scalar(select(models.DataSource).where(models.DataSource.name == "institution_master"))
    if ds:
        ds.last_status = "SUCCESS"
        ds.last_success_at = datetime.utcnow()
        ds.records_total += result.get("created", 0) + result.get("updated", 0)
        db.commit()
    bus.publish("MASTER_IMPORTED", {"message": f"Institution master imported: {result}", "source": "institution_master", "source_type": "FILE_UPLOAD", "source_name": "institution_master"})
    return {"status": "SUCCESS", **result}


@router.get("/events/recent")
def recent_events(current: models.User = Depends(get_current_user)):
    return bus.snapshot()[-50:]


@router.get("/events/stream")
async def event_stream(request: Request, token: str | None = Query(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    from ..security import decode_token
    try:
        decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    q = bus.subscribe()

    async def gen():
        try:
            for e in bus.snapshot()[-20:]:
                yield sse_format(e)
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=20)
                    yield sse_format(event)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
