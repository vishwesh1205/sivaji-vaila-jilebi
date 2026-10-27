from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings


OPEN_STATUSES = {models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED}


class SLAService:
    def __init__(self, db: Session):
        self.db = db

    def compute_bucket(self, case: models.Case) -> str:
        days = (datetime.utcnow() - case.date_received).days
        if days <= 30:
            return "0-30"
        if days <= 60:
            return "31-60"
        if days <= 90:
            return "61-90"
        return "90+"

    def is_overdue(self, case: models.Case) -> bool:
        return (datetime.utcnow() - case.date_received).days >= settings.sla_outer_days

    def run_checks(self) -> int:
        count = 0
        cases = self.db.scalars(select(models.Case).where(models.Case.status.in_(OPEN_STATUSES))).all()
        for case in cases:
            days = (datetime.utcnow() - case.date_received).days
            if days >= 75:
                officer_id = case.assigned_officer_id
                if officer_id:
                    notif = models.Notification(
                        user_id=officer_id,
                        type=models.NotificationType.SLA,
                        payload={"case_id": case.case_id, "days_open": days, "bucket": self.compute_bucket(case)},
                        is_read=False,
                    )
                    self.db.add(notif)
                    count += 1
            if days >= 15 and (datetime.utcnow() - case.last_action_at).days >= 15:
                officer_id = case.assigned_officer_id
                if officer_id:
                    notif = models.Notification(
                        user_id=officer_id,
                        type=models.NotificationType.PENDING_REMINDER,
                        payload={"case_id": case.case_id, "days_since_action": (datetime.utcnow() - case.last_action_at).days},
                        is_read=False,
                    )
                    self.db.add(notif)
                    count += 1
        self.db.commit()
        return count
