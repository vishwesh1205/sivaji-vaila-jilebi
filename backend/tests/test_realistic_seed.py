from __future__ import annotations

import random
from collections import Counter
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import select

from app import models
from seed.narratives.engine import NarrativeEngine, length_buckets, validate_corpus, validate_text
from seed.narratives.taxonomy import CATEGORY_SUBTYPES
from seed.reseed_realistic import rewrite_seeded_cases


def test_engine_produces_varied_valid_corpus():
    engine = NarrativeEngine(123)
    institution = SimpleNamespace(name="Deccan Institute of Engineering and Technology", city="Pune")
    rng = random.Random(123)
    buckets = length_buckets(210, rng)
    categories = list(CATEGORY_SUBTYPES)
    records = []
    for idx, bucket in enumerate(buckets):
        category = categories[idx % len(categories)]
        subtype = list(CATEGORY_SUBTYPES[category])[idx % len(CATEGORY_SUBTYPES[category])]
        generated = engine.build(
            case_id=f"TST-{idx:05d}",
            institution=institution,
            category=category,
            subtype=subtype,
            bucket=bucket,
        )
        assert generated.subject
        assert generated.narrative_original
        assert not validate_text(generated.narrative, restricted=category == "RAGGING_DISCRIMINATION")
        records.append(
            {
                "case_id": f"TST-{idx:05d}",
                "narrative": generated.narrative,
                "length_bucket": generated.length_bucket,
                "language": generated.language,
                "complainant_type": generated.complainant_type,
                "category": category,
            }
        )
    summary = validate_corpus(records)
    assert summary["count"] == 210
    assert summary["languages"].get("hi", 0) > 0
    assert set(summary["languages"]) - {"en"}
    assert len(set(r["narrative"] for r in records)) == len(records)


def _seed_cases(db, count=92):
    bureaus = {}
    for code, name in [
        ("RB", "Regulation Bureau"),
        ("PGRC", "Public Grievance Redressal Cell"),
        ("RO", "Regional Offices"),
        ("APPROVAL", "Approval Bureau"),
        ("EVC", "EVC Cell"),
    ]:
        bureau = models.Bureau(code=code, name=name)
        db.add(bureau)
        bureaus[code] = bureau
    db.commit()
    for bureau in bureaus.values():
        db.refresh(bureau)
    user = models.User(name="Admin", email="seed-admin@test.gov.in", password_hash="x", role=models.UserRole.ADMIN)
    db.add(user)
    db.commit()
    db.refresh(user)

    institutions = []
    for idx in range(14):
        inst = models.Institution(
            aicte_permanent_id=f"1-90{idx:05d}",
            name=f"Deccan Institute of Applied Sciences {idx}",
            normalized_name=f"deccan institute applied sciences {idx}",
            address=f"{idx + 1}, College Road, Pune",
            city="Pune",
            state="Maharashtra",
            region="Pune",
            approval_status="Approved",
            programme_mix=["B.Tech"],
            aliases=[],
            is_synthetic=True,
            source_type="SIMULATOR",
        )
        db.add(inst)
        institutions.append(inst)
    db.commit()
    for inst in institutions:
        db.refresh(inst)

    for idx in range(count):
        case = models.Case(
            case_id=f"TST-2026-{idx:04d}",
            source_channel=models.SourceChannel.CSS,
            institution_id=institutions[idx % len(institutions)].id,
            raw_institution_text=institutions[idx % len(institutions)].name,
            subject="old one-line subject",
            category=models.CaseCategory.FEE,
            narrative="Short legacy narrative.",
            status=models.CaseStatus.PENDING,
            bureau_id=bureaus["PGRC"].id,
            assigned_officer_id=user.id,
            date_received=datetime.utcnow() - timedelta(days=20 + idx),
            last_action_at=datetime.utcnow(),
            last_action_text="Case registered",
            resolution_status=models.ResolutionStatus.RESOLVED,
            match_confidence=0.99,
            idempotency_key=f"test:realistic:{idx}",
            source_type="SIMULATOR",
            source_name="seed",
            is_synthetic=True,
            language="en",
            narrative_original="Short legacy narrative.",
            narrative_translated="Short legacy narrative.",
        )
        db.add(case)
    db.commit()
    return user


def _snapshot(db):
    cases = db.scalars(select(models.Case).where(models.Case.source_name == "seed").order_by(models.Case.case_id)).all()
    out = []
    for case in cases:
        actions = db.scalars(select(models.CaseAction).where(models.CaseAction.case_id == case.id).order_by(models.CaseAction.created_at)).all()
        out.append(
            (
                case.case_id,
                case.subject,
                case.category.value,
                case.category_subtype,
                case.complainant_type,
                case.institution_id,
                case.raw_institution_text,
                case.narrative,
                case.status.value,
                case.outcome_tag.value if case.outcome_tag else None,
                case.last_action_at.isoformat(),
                case.last_action_text,
                case.date_received.isoformat(),
                case.language,
                case.resolution_status.value,
                tuple((a.action_type.value, a.remarks, a.created_at.isoformat(), a.hash) for a in actions),
            )
        )
    return out


def test_reseed_is_deterministic_and_preserves_ids(db):
    _seed_cases(db)
    original_ids = {c.case_id for c in db.scalars(select(models.Case)).all()}
    anchor = datetime(2026, 10, 25, 0, 0, 0)

    first = rewrite_seeded_cases(db, seed=321, anchor=anchor)
    snapshot_one = _snapshot(db)
    second = rewrite_seeded_cases(db, seed=321, anchor=anchor)
    snapshot_two = _snapshot(db)

    assert first["rewritten"] == second["rewritten"] == 92
    assert snapshot_one == snapshot_two
    assert {row[0] for row in snapshot_one} == original_ids

    cases = db.scalars(select(models.Case).where(models.Case.source_name == "seed")).all()
    assert all(c.is_synthetic for c in cases)
    assert all(c.subject for c in cases)
    assert all(c.category_subtype in CATEGORY_SUBTYPES[c.category.value] for c in cases)
    assert all(c.complainant_type for c in cases)
    assert all(c.resolution_status in {models.ResolutionStatus.RESOLVED, models.ResolutionStatus.NEEDS_REVIEW, models.ResolutionStatus.UNRESOLVED} for c in cases)
    assert Counter(c.status.value for c in cases).keys() >= {"PENDING", "UNDER_PROCESS", "DISPOSED", "TRANSFERRED", "ESCALATED"}
    assert db.query(models.ReviewQueue).count() >= 4
    assert db.query(models.OverlapAlert).count() > 0

    for case in cases:
        actions = db.scalars(select(models.CaseAction).where(models.CaseAction.case_id == case.id).order_by(models.CaseAction.created_at)).all()
        assert 3 <= len(actions) <= 12
        assert actions[0].prev_hash == "0" * 64
        for prev, current in zip(actions, actions[1:]):
            assert current.prev_hash == prev.hash

    contradictory = [
        case
        for case in cases
        if case.status == models.CaseStatus.DISPOSED and case.outcome_tag in {models.OutcomeTag.DEFICIENCY_CONFIRMED, models.OutcomeTag.NO_DEFICIENCY}
    ]
    assert contradictory
    grouped: dict[tuple, set[str]] = {}
    for case in contradictory:
        grouped.setdefault((case.institution_id, case.category, case.category_subtype), set()).add(case.outcome_tag.value)
    assert any({"DEFICIENCY_CONFIRMED", "NO_DEFICIENCY"} <= outcomes for outcomes in grouped.values())
