import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app import models
from app.database import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def base_data(db):
    rb = models.Bureau(code="RB", name="Regulation Bureau")
    pgrc = models.Bureau(code="PGRC", name="Public Grievance Redressal Cell")
    db.add_all([rb, pgrc])
    db.commit()
    db.refresh(rb)
    db.refresh(pgrc)
    user = models.User(name="Admin", email="admin@test.gov.in", password_hash="x", role=models.UserRole.ADMIN, is_active=True)
    db.add(user)
    inst = models.Institution(
        aicte_permanent_id="1-3538633",
        name="St. Xavier Institute of Technology",
        normalized_name="saint xavier institute technology",
        address="123 MG Road, Mumbai",
        city="Mumbai",
        state="Maharashtra",
        region="Pune",
        approval_status="Approved",
        programme_mix=["B.Tech"],
        aliases=["St Xaviers Inst of Tech"],
        is_synthetic=True,
        source_type="SIMULATOR",
    )
    db.add(inst)
    db.commit()
    db.refresh(user)
    db.refresh(inst)

    def make_case(case_id, bureau, channel, tag=None, narrative=None, date=None, category=models.CaseCategory.FEE, source_name="css"):
        c = models.Case(
            case_id=case_id,
            source_channel=channel,
            institution_id=inst.id,
            raw_institution_text=inst.name,
            category=category,
            narrative=narrative or "Excessive fee was charged beyond the approved fee structure for the current year.",
            status=models.CaseStatus.PENDING,
            bureau_id=bureau.id,
            assigned_officer_id=user.id,
            date_received=date or datetime.utcnow() - timedelta(days=10),
            last_action_at=datetime.utcnow(),
            last_action_text="Created",
            resolution_status=models.ResolutionStatus.RESOLVED,
            match_confidence=0.98,
            idempotency_key=f"test:{case_id}",
            source_type="SIMULATOR",
            source_name=source_name,
            source_record_id=case_id,
            outcome_tag=tag,
            language="en",
            narrative_original=narrative or "Excessive fee was charged beyond the approved fee structure for the current year.",
            narrative_translated=narrative or "Excessive fee was charged beyond the approved fee structure for the current year.",
            complainant_hash=None,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    return {"rb": rb, "pgrc": pgrc, "user": user, "inst": inst, "make_case": make_case}
