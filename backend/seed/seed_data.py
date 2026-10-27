#!/usr/bin/env python3
import json
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, SessionLocal
from app.security import get_password_hash
from app.services.resolution import normalize_name
from app.schema_guard import ensure_columns
from app.config import settings
from app.connectors.base import hash_identifier
from app.services.overlap import OverlapService

STATES = [
    ("Tamil Nadu", "Chennai"),
    ("Madhya Pradesh", "Bhopal"),
    ("West Bengal", "Kolkata"),
    ("Punjab", "Chandigarh"),
    ("Uttar Pradesh", "Kanpur"),
    ("Maharashtra", "Pune"),
    ("Telangana", "Hyderabad"),
    ("Assam", "Guwahati"),
    ("Rajasthan", "Jaipur"),
    ("Karnataka", "Bengaluru"),
]
REGIONS = ["Chennai", "Bhopal", "Kolkata", "Chandigarh", "Kanpur", "Pune", "Hyderabad", "Guwahati", "Jaipur", "Bengaluru"]

COLLEGE_NAMES = [
    "Institute of Technology",
    "College of Engineering",
    "School of Engineering and Technology",
    "Institute of Engineering and Technology",
    "College of Technology",
    "Polytechnic College",
    "Institute of Management and Technology",
]


def ensure_part2_seed(db: Session):
    """Idempotent additions for Part 2: honest provenance + a visible demo spike."""
    from app.hash_chain import compute_hash

    # Existing databases predate provenance columns: label them honestly.
    db.query(models.Case).filter(models.Case.source_name.is_(None)).update({"source_name": "seed", "source_type": "SIMULATOR"}, synchronize_session=False)
    db.query(models.Institution).filter(models.Institution.is_synthetic.is_(None)).update({"is_synthetic": True}, synchronize_session=False)
    db.commit()
    rb_hero = db.query(models.Case).filter_by(case_id="RB-2026-0892").first()
    if rb_hero and rb_hero.outcome_tag is None:
        rb_hero.outcome_tag = models.OutcomeTag.NO_DEFICIENCY
        db.commit()
    pg_hero = db.query(models.Case).filter_by(case_id="PG-2026-4471").first()
    if pg_hero and pg_hero.institution_id:
        try:
            OverlapService(db).detect_for_case(pg_hero, None)
        except Exception:
            db.rollback()
    if not db.query(models.Case).filter_by(case_id="ML-2026-0001").first():
        hero = db.query(models.Institution).filter_by(aicte_permanent_id="1-3538633").first()
        pgrc = db.query(models.Bureau).filter_by(code="PGRC").first()
        admin = db.query(models.User).filter_by(email="admin@aicte.gov.in").first()
        if hero and pgrc and admin:
            ml = models.Case(
                case_id="ML-2026-0001",
                source_channel=models.SourceChannel.CPGRAMS,
                institution_id=hero.id,
                raw_institution_text=hero.name,
                category=models.CaseCategory.FEE,
                narrative="Excess fee was charged for the current academic year; the student requests an inquiry and refund.",
                status=models.CaseStatus.PENDING,
                bureau_id=pgrc.id,
                assigned_officer_id=admin.id,
                date_received=datetime.utcnow() - timedelta(days=3),
                last_action_at=datetime.utcnow(),
                last_action_text="Case registered",
                resolution_status=models.ResolutionStatus.RESOLVED,
                match_confidence=0.98,
                idempotency_key="seed:ML-2026-0001",
                source_type="SIMULATOR",
                source_name="seed",
                language="hi",
                narrative_original="वर्तमान शैक्षणिक वर्ष के लिए अधिक शुल्क लिया गया; छात्र जांच और धनवापसी का अनुरोध करता है।",
                narrative_translated="Excess fee was charged for the current academic year; the student requests an inquiry and refund.",
                complainant_hash=hash_identifier("multilingual-demo-ref"),
            )
            db.add(ml)
            db.flush()
            prev = "0" * 64
            db.add(models.CaseAction(case_id=ml.id, actor_user_id=admin.id, bureau_id=pgrc.id, action_type=models.ActionType.CREATED, remarks="Seeded multilingual demo case", prev_hash=prev, hash=compute_hash(prev, {"action": "CREATED", "case_id": ml.case_id})))
            db.commit()

    if not db.query(models.Case).filter_by(case_id="REV-2026-0001").first():
        hero = db.query(models.Institution).filter_by(aicte_permanent_id="1-3538633").first()
        rb = db.query(models.Bureau).filter_by(code="RB").first()
        admin = db.query(models.User).filter_by(email="admin@aicte.gov.in").first()
        if hero and rb and admin:
            review_case = models.Case(
                case_id="REV-2026-0001",
                source_channel=models.SourceChannel.CSS,
                institution_id=None,
                raw_institution_text="Xavier Institute of Technology and Management, Mumbai",
                category=models.CaseCategory.FEE,
                narrative="Fee collection above the approved structure; institution name requires manual confirmation.",
                status=models.CaseStatus.PENDING,
                bureau_id=rb.id,
                assigned_officer_id=admin.id,
                date_received=datetime.utcnow() - timedelta(days=8),
                last_action_at=datetime.utcnow(),
                last_action_text="Case registered",
                resolution_status=models.ResolutionStatus.NEEDS_REVIEW,
                match_confidence=0.78,
                idempotency_key="seed:REV-2026-0001",
                source_type="SIMULATOR",
                source_name="seed",
                language="en",
                narrative_original="Fee collection above the approved structure; institution name requires manual confirmation.",
                narrative_translated="Fee collection above the approved structure; institution name requires manual confirmation.",
                complainant_hash=hash_identifier("review-demo-ref"),
            )
            db.add(review_case)
            db.flush()
            prev = "0" * 64
            db.add(models.CaseAction(case_id=review_case.id, actor_user_id=admin.id, bureau_id=rb.id, action_type=models.ActionType.CREATED, remarks="Seeded ambiguous-resolution demo case", prev_hash=prev, hash=compute_hash(prev, {"action": "CREATED", "case_id": review_case.case_id})))
            db.add(models.ReviewQueue(
                case_id=review_case.id,
                candidate_institutions=[{"institution_id": hero.id, "name": hero.name, "aicte_permanent_id": hero.aicte_permanent_id, "score": 0.78, "reasons": ["token_set:82", "alias_token"]}],
                status=models.ReviewStatus.OPEN,
            ))
            db.commit()

    existing = db.query(models.Case).filter(models.Case.case_id.like("EMRG-2026-%")).count()
    if existing == 0:
        fee_cases = 32
        users = db.query(models.User).all()
        insts = db.query(models.Institution).filter(models.Institution.region == "Chennai").all()
        if not insts:
            insts = db.query(models.Institution).limit(3).all()
        bureaus = db.query(models.Bureau).all()
        for i in range(fee_cases):
            inst = insts[i % len(insts)]
            bureau = bureaus[i % max(1, len(bureaus))]
            case = models.Case(
                case_id=f"EMRG-2026-{i+1:04d}",
                source_channel=models.SourceChannel.CSS if i % 2 == 0 else models.SourceChannel.CPGRAMS,
                institution_id=inst.id,
                raw_institution_text=inst.name,
                category=models.CaseCategory.FEE,
                narrative="Sudden increase in fee complaints this week: multiple students report excess fee collection beyond the approved structure.",
                status=models.CaseStatus.PENDING,
                bureau_id=bureau.id,
                assigned_officer_id=users[i % len(users)].id,
                date_received=datetime.utcnow() - timedelta(days=(i % 6)),
                last_action_at=datetime.utcnow() - timedelta(days=1),
                last_action_text="Case registered",
                resolution_status=models.ResolutionStatus.RESOLVED,
                match_confidence=0.97,
                idempotency_key=f"seed:EMRG-2026-{i+1:04d}",
                source_type="SIMULATOR",
                source_name="seed",
                language="en",
                narrative_original="Sudden increase in fee complaints this week: multiple students report excess fee collection beyond the approved structure.",
                narrative_translated="Sudden increase in fee complaints this week: multiple students report excess fee collection beyond the approved structure.",
                complainant_hash=hash_identifier(f"emerging-ref-{i:04d}"),
            )
            db.add(case)
            db.flush()
            prev = "0" * 64
            db.add(models.CaseAction(case_id=case.id, actor_user_id=case.assigned_officer_id, bureau_id=case.bureau_id, action_type=models.ActionType.CREATED, remarks="Seeded emerging-issue demo case", prev_hash=prev, hash=compute_hash(prev, {"action": "CREATED", "case_id": case.case_id})))
        db.commit()



def run():
    Base.metadata.create_all(bind=engine)
    ensure_columns(engine)
    db: Session = SessionLocal()
    try:
        if db.query(models.Bureau).count() == 0:
            bureaus = [
                models.Bureau(code="RB", name="Regulation Bureau"),
                models.Bureau(code="PGRC", name="Public Grievance Redressal Cell"),
                models.Bureau(code="RO", name="Regional Offices"),
                models.Bureau(code="APPROVAL", name="Approval Bureau"),
                models.Bureau(code="EVC", name="EVC Cell"),
            ]
            db.add_all(bureaus)
            db.commit()
            for b in bureaus:
                db.refresh(b)

        if db.query(models.User).count() == 0:
            bureaus = {b.code: b for b in db.query(models.Bureau).all()}
            users = [
                ("Admin User", "admin@aicte.gov.in", "admin123", models.UserRole.ADMIN, None, None),
                ("Management Lead", "mgmt@aicte.gov.in", "mgmt123", models.UserRole.MANAGEMENT, None, None),
                ("RB Officer", "rb.officer@aicte.gov.in", "rb123", models.UserRole.RB_OFFICER, bureaus["RB"].id, None),
                ("PGRC Officer", "pgrc.officer@aicte.gov.in", "pgrc123", models.UserRole.PGRC_OFFICER, bureaus["PGRC"].id, None),
                ("Approval Bureau Officer", "approval.officer@aicte.gov.in", "approval123", models.UserRole.BUREAU_OFFICER, bureaus["APPROVAL"].id, None),
                ("EVC Officer", "evc.officer@aicte.gov.in", "evc123", models.UserRole.BUREAU_OFFICER, bureaus["EVC"].id, None),
                ("RO Chennai", "ro.chennai@aicte.gov.in", "ro123", models.UserRole.REGIONAL_OFFICER, bureaus["RO"].id, "Chennai"),
                ("RO Bhopal", "ro.bhopal@aicte.gov.in", "ro123", models.UserRole.REGIONAL_OFFICER, bureaus["RO"].id, "Bhopal"),
                ("RO Kolkata", "ro.kolkata@aicte.gov.in", "ro123", models.UserRole.REGIONAL_OFFICER, bureaus["RO"].id, "Kolkata"),
                ("RO Pune", "ro.pune@aicte.gov.in", "ro123", models.UserRole.REGIONAL_OFFICER, bureaus["RO"].id, "Pune"),
                ("RO Hyderabad", "ro.hyderabad@aicte.gov.in", "ro123", models.UserRole.REGIONAL_OFFICER, bureaus["RO"].id, "Hyderabad"),
                ("RO Chandigarh", "ro.chandigarh@aicte.gov.in", "ro123", models.UserRole.REGIONAL_OFFICER, bureaus["RO"].id, "Chandigarh"),
            ]
            for name, email, pwd, role, bid, region in users:
                db.add(models.User(name=name, email=email, password_hash=get_password_hash(pwd), role=role, bureau_id=bid, region=region, is_active=True))
            db.commit()

        if db.query(models.Institution).count() == 0:
            bureaus_all = db.query(models.Bureau).all()
            random.seed(12345)
            insts = []
            # Create hero institution
            hero = models.Institution(
                aicte_permanent_id="1-3538633",
                name="St. Xavier Institute of Technology",
                normalized_name=normalize_name("St. Xavier Institute of Technology"),
                address="123 MG Road, Mumbai, Maharashtra",
                city="Mumbai",
                state="Maharashtra",
                region="Pune",
                university_affiliation="Mumbai University",
                approval_status="Approved",
                programme_mix=["B.Tech", "M.Tech"],
                aliases=["St Xavier Institute of Technology", "St. Xaviers Institute of Technology", "Xavier Institute of Technology"],
                is_synthetic=True,
                source_type="SIMULATOR",
            )
            insts.append(hero)
            for i in range(1, 301):
                state, city = random.choice(STATES)
                region = city if city in REGIONS else random.choice(REGIONS)
                prefix = random.choice(["National", "Govt", "Modern", "Global", "Saraswati", "Shri", "Sri"])
                cname = f"{prefix} {random.choice(['College', 'Institute'])} of {random.choice(COLLEGE_NAMES).replace('Institute of ', '')}" if random.random() > 0.5 else f"{prefix} {random.choice(COLLEGE_NAMES)}"
                aid = f"1-{random.randint(1000000, 9999999)}"
                inst = models.Institution(
                    aicte_permanent_id=aid,
                    name=cname,
                    normalized_name=normalize_name(cname),
                    address=f"{random.randint(1,200)}, {random.choice(['Main Road','Station Road','Gandhi Marg'])}, {city}",
                    city=city,
                    state=state,
                    region=region,
                    university_affiliation=f"{state} Technical University" if random.random() > 0.3 else None,
                    approval_status=random.choice(["Approved", "Approved", "Approved", "Provisional"]),
                    programme_mix=random.sample(["B.Tech", "M.Tech", "MBA", "B.Arch", "Diploma"], k=random.randint(1, 3)),
                    aliases=[],
                    is_synthetic=True,
                    source_type="SIMULATOR",
                )
                insts.append(inst)
            db.add_all(insts)
            db.commit()
            for inst in insts:
                db.refresh(inst)
            # add some aliases
            for inst in insts[1:20]:
                alt = inst.name.replace("Institute", "Inst.").replace("College", "Coll.")
                inst.aliases = [alt]
                db.add(models.InstitutionAlias(institution_id=inst.id, alias=alt, source="seed"))
            db.commit()

        if db.query(models.Case).count() == 0:
            bureaus = {b.code: b for b in db.query(models.Bureau).all()}
            users = db.query(models.User).all()
            insts = db.query(models.Institution).all()
            hero = db.query(models.Institution).filter_by(aicte_permanent_id="1-3538633").first()
            random.seed(54321)
            cases = []
            # Hero cases - deliberate overlap
            pgrc = bureaus["PGRC"]
            rb = bureaus["RB"]
            pg_off = next((u for u in users if u.role == models.UserRole.PGRC_OFFICER), None)
            rb_off = next((u for u in users if u.role == models.UserRole.RB_OFFICER), None)
            c1 = models.Case(
                case_id="PG-2026-4471",
                source_channel=models.SourceChannel.CPGRAMS,
                institution_id=hero.id,
                raw_institution_text="St. Xavier Institute of Technology, Mumbai",
                category=models.CaseCategory.FEE,
                narrative="Excessive fee charged beyond approved structure for the academic year 2025-26 despite AICTE fee fixation guidelines. Student has submitted fee receipts and demand notices.",
                status=models.CaseStatus.UNDER_PROCESS,
                bureau_id=pgrc.id,
                assigned_officer_id=pg_off.id if pg_off else None,
                date_received=datetime.utcnow() - timedelta(days=45),
                last_action_at=datetime.utcnow() - timedelta(days=10),
                last_action_text="Fee details sought from institution",
                next_action_text="Review institution response",
                resolution_status=models.ResolutionStatus.RESOLVED,
                match_confidence=1.0,
                idempotency_key="seed:PG-2026-4471",
                source_type="SIMULATOR",
                source_name="seed",
                language="en",
                narrative_original="Excessive fee charged beyond approved structure for the academic year 2025-26 despite AICTE fee fixation guidelines. Student has submitted fee receipts and demand notices.",
                narrative_translated="Excessive fee charged beyond approved structure for the academic year 2025-26 despite AICTE fee fixation guidelines. Student has submitted fee receipts and demand notices.",
                complainant_hash="a" * 64,
            )
            cases.append(c1)
            c2 = models.Case(
                case_id="RB-2026-0892",
                source_channel=models.SourceChannel.CSS,
                institution_id=hero.id,
                raw_institution_text="St Xaviers Inst of Tech",
                category=models.CaseCategory.APPROVAL_VIOLATION,
                narrative="Alleged unauthorized intake beyond approved seats in multiple engineering branches. Inspection report references violation of approval conditions and needs verification.",
                status=models.CaseStatus.PENDING,
                bureau_id=rb.id,
                assigned_officer_id=rb_off.id if rb_off else None,
                date_received=datetime.utcnow() - timedelta(days=60),
                last_action_at=datetime.utcnow() - timedelta(days=20),
                last_action_text="Case registered",
                next_action_text="Assign for inspection",
                resolution_status=models.ResolutionStatus.RESOLVED,
                match_confidence=0.95,
                idempotency_key="seed:RB-2026-0892",
                source_type="SIMULATOR",
                source_name="seed",
                language="en",
                narrative_original="Alleged unauthorized intake beyond approved seats in multiple engineering branches. Inspection report references violation of approval conditions and needs verification.",
                narrative_translated="Alleged unauthorized intake beyond approved seats in multiple engineering branches. Inspection report references violation of approval conditions and needs verification.",
                outcome_tag=models.OutcomeTag.NO_DEFICIENCY,
                complainant_hash="b" * 64,
            )
            cases.append(c2)
            categories = list(models.CaseCategory)
            sources = list(models.SourceChannel)
            statuses = [models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.DISPOSED, models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS]
            for i in range(1498):
                inst = random.choice(insts)
                bureau = random.choice(list(bureaus.values()))
                off = next((u for u in users if u.bureau_id == bureau.id), random.choice(users))
                days_ago = random.randint(5, 400)
                status = random.choice(statuses)
                if random.random() < 0.15:
                    raw = inst.name.replace("Institute", "Inst").replace("College", "Coll") + " " + random.choice(["Bangalore", "Delhi", "Chennai"])
                else:
                    raw = inst.name
                cat = random.choice(categories)
                cid = f"CASE-2026-{10000 + i}"
                case = models.Case(
                    case_id=cid,
                    source_channel=random.choice(sources),
                    institution_id=inst.id,
                    raw_institution_text=raw,
                    category=cat,
                    narrative=f"Complaint regarding {cat.value.lower().replace('_', ' ')} at the institution. Details provided by complainant for necessary action.",
                    status=status,
                    bureau_id=bureau.id,
                    assigned_officer_id=off.id,
                    date_received=datetime.utcnow() - timedelta(days=days_ago),
                    last_action_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                    last_action_text=random.choice(["Case registered", "Query raised", "Response awaited", "Document received", "Under examination"]),
                    next_action_text=random.choice(["Review reply", "Seek clarification", "Forward to RO", "Prepare report"]),
                    resolution_status=models.ResolutionStatus.RESOLVED,
                    match_confidence=random.uniform(0.9, 1.0),
                    idempotency_key=f"seed:{cid}",
                    source_type="SIMULATOR",
                    source_name="seed",
                    language="en",
                    narrative_original=f"Complaint regarding {cat.value.lower().replace('_', ' ')} at the institution. Details provided by complainant for necessary action.",
                    narrative_translated=f"Complaint regarding {cat.value.lower().replace('_', ' ')} at the institution. Details provided by complainant for necessary action.",
                    complainant_hash=hash_identifier(f"seed-ref-{i:08d}"),
                )
                cases.append(case)
            db.add_all(cases)
            db.commit()
            # Add actions for all
            for case in cases:
                prev = "0" * 64
                payload = {"action": "CREATED", "case_id": case.case_id}
                from app.hash_chain import compute_hash
                action = models.CaseAction(case_id=case.id, actor_user_id=case.assigned_officer_id, bureau_id=case.bureau_id, action_type=models.ActionType.CREATED, remarks="Case created", prev_hash=prev, hash=compute_hash(prev, payload))
                db.add(action)
            db.commit()
        ensure_part2_seed(db)
        from seed.reseed_realistic import rewrite_seeded_cases
        rewrite_seeded_cases(db, seed=settings.seed_random_seed)
        print("Seed completed")
    finally:
        db.close()


if __name__ == "__main__":
    run()
