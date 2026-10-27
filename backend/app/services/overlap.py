from collections import defaultdict
from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings


ACTIVE = {models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED}


class OverlapService:
    def __init__(self, db: Session):
        self.db = db

    def detect_for_case(self, case: models.Case, actor_user_id: int | None = None) -> models.OverlapAlert | None:
        if not case.institution_id:
            return None
        inst = case.institution
        active_cases = self.db.scalars(
            select(models.Case).where(
                models.Case.institution_id == case.institution_id,
                models.Case.status.in_(ACTIVE),
            )
        ).all()
        bureaus = {c.bureau_id for c in active_cases}
        if len(bureaus) < 2:
            return self._enrich_near_duplicates(active_cases, actor_user_id)
        existing = self.db.scalar(
            select(models.OverlapAlert).where(
                models.OverlapAlert.institution_id == case.institution_id,
                models.OverlapAlert.status.in_([models.AlertStatus.OPEN, models.AlertStatus.ACKNOWLEDGED]),
            )
        )
        bureau_codes = []
        for bid in bureaus:
            b = self.db.get(models.Bureau, bid)
            if b:
                bureau_codes.append(b.code)
        bureau_codes = sorted(set(bureau_codes))
        case_ids = [c.id for c in active_cases]
        why = f"Same institution ({inst.aicte_permanent_id if inst else ''}) has active cases in {', '.join(bureau_codes)}."
        if existing:
            existing.case_ids = sorted(set(existing.case_ids + case_ids))
            existing.bureaus_involved = sorted(set(existing.bureaus_involved + bureau_codes))
            existing.why_flagged = why
            self.db.add(existing)
            self._ensure_cross_links(active_cases)
            self.db.flush()
            self._notify(active_cases, existing.id)
            self.db.commit()
            self.db.refresh(existing)
            self._enrich_near_duplicates(active_cases, actor_user_id)
            return existing
        alert = models.OverlapAlert(
            institution_id=case.institution_id,
            case_ids=sorted(set(case_ids)),
            bureaus_involved=bureau_codes,
            status=models.AlertStatus.OPEN,
            acknowledged_by_json=[],
            why_flagged=why,
        )
        self.db.add(alert)
        self.db.flush()
        self._ensure_cross_links(active_cases)
        self._notify(active_cases, alert.id)
        self.db.commit()
        self.db.refresh(alert)
        self._enrich_near_duplicates(active_cases, actor_user_id)
        return alert

    def _ensure_cross_links(self, cases: list[models.Case]):
        by_bureau = defaultdict(list)
        for c in cases:
            by_bureau[c.bureau_id].append(c)
        bureau_ids = list(by_bureau.keys())
        for i in range(len(bureau_ids)):
            for j in range(i + 1, len(bureau_ids)):
                for ca in by_bureau[bureau_ids[i]]:
                    for cb in by_bureau[bureau_ids[j]]:
                        pair = (min(ca.id, cb.id), max(ca.id, cb.id))
                        existing = self.db.scalar(
                            select(models.CaseLink).where(
                                models.CaseLink.case_a_id == pair[0],
                                models.CaseLink.case_b_id == pair[1],
                                models.CaseLink.link_type == models.LinkType.OVERLAP_CROSS_BUREAU,
                            )
                        )
                        if not existing:
                            link = models.CaseLink(
                                case_a_id=pair[0],
                                case_b_id=pair[1],
                                link_type=models.LinkType.OVERLAP_CROSS_BUREAU,
                                similarity_score=1.0,
                            )
                            self.db.add(link)

    def _notify(self, cases: list[models.Case], alert_id: int):
        officer_ids = {c.assigned_officer_id for c in cases if c.assigned_officer_id}
        for oid in officer_ids:
            notif = models.Notification(
                user_id=oid,
                type=models.NotificationType.OVERLAP,
                payload={"alert_id": alert_id, "message": "Potential Overlapping Cases – Coordination Required"},
                is_read=False,
            )
            self.db.add(notif)
        self.db.flush()

    def _enrich_near_duplicates(self, cases: list[models.Case], actor_user_id: int | None):
        if len(cases) < 2:
            return
        texts = [c.narrative for c in cases]
        try:
            vectorizer = TfidfVectorizer(max_features=2000, stop_words="english")
            X = vectorizer.fit_transform(texts)
            sim = cosine_similarity(X)
        except Exception:
            return
        for i in range(len(cases)):
            for j in range(i + 1, len(cases)):
                score = float(sim[i][j])
                if score >= settings.near_duplicate_threshold:
                    pair = (min(cases[i].id, cases[j].id), max(cases[i].id, cases[j].id))
                    existing = self.db.scalar(
                        select(models.CaseLink).where(
                            models.CaseLink.case_a_id == pair[0],
                            models.CaseLink.case_b_id == pair[1],
                            models.CaseLink.link_type == models.LinkType.NEAR_DUPLICATE,
                        )
                    )
                    if not existing:
                        link = models.CaseLink(
                            case_a_id=pair[0],
                            case_b_id=pair[1],
                            link_type=models.LinkType.NEAR_DUPLICATE,
                            similarity_score=round(score, 4),
                            created_by=actor_user_id,
                        )
                        self.db.add(link)
        self.db.commit()
