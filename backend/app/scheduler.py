from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from . import models
from .config import settings
from .database import SessionLocal
from .services.ingestion import SyncService, ensure_data_sources
from .services.sla import SLAService

scheduler = BackgroundScheduler()


def sla_job():
    db = SessionLocal()
    try:
        SLAService(db).run_checks()
    finally:
        db.close()


def sync_job(name: str):
    db = SessionLocal()
    try:
        ds = db.query(models.DataSource).filter(models.DataSource.name == name).first()
        if ds and ds.enabled:
            SyncService(db).sync(name, triggered_by="scheduler")
    finally:
        db.close()


def escalate_overlaps(db, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=settings.overlap_escalate_days)
    alerts = db.query(models.OverlapAlert).filter(models.OverlapAlert.status == models.AlertStatus.OPEN, models.OverlapAlert.escalated_at.is_(None), models.OverlapAlert.created_at <= cutoff).all()
    for alert in alerts:
        alert.escalated_at = now
        users = db.query(models.User).filter(models.User.role.in_([models.UserRole.MANAGEMENT, models.UserRole.ADMIN])).all()
        for user in users:
            db.add(models.Notification(user_id=user.id, type=models.NotificationType.ESCALATION, payload={"kind": "overlap_escalation", "alert_id": alert.id, "message": f"Overlap alert {alert.id} unacknowledged for more than {settings.overlap_escalate_days} days"}))
    db.commit()
    return len(alerts)


def overlap_escalation_job():
    db = SessionLocal()
    try:
        escalate_overlaps(db)
    finally:
        db.close()


def start_scheduler():
    if scheduler.running:
        return
    db = SessionLocal()
    try:
        ensure_data_sources(db)
        sources = db.query(models.DataSource).all()
        for ds in sources:
            if not ds.enabled:
                continue
            if ds.name == "institution_master" and not settings.institution_master_url:
                continue
            scheduler.add_job(
                sync_job,
                "interval",
                seconds=max(5, ds.interval_seconds),
                id=f"sync_{ds.name}",
                args=[ds.name],
                next_run_time=datetime.now() + timedelta(seconds=5 if ds.name in {"css", "cpgrams"} else 20),
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
    finally:
        db.close()
    scheduler.add_job(sla_job, "cron", hour=0, minute=30, id="sla_daily", replace_existing=True)
    scheduler.add_job(overlap_escalation_job, "cron", hour=1, minute=0, id="overlap_escalation", replace_existing=True)
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
