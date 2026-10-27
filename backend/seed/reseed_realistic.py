#!/usr/bin/env python3
"""Rewrite the seeded complaint corpus with realistic synthetic narratives.

The operation is in-place and idempotent for a given ``--seed`` and calendar
day: case IDs, institutions, users and bureaus are preserved, while narratives,
subjects, lifecycle actions, resolution flags and overlap alerts are rebuilt.
Hero demo cases (PG/RB/ML/REV) are never touched.
"""
from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.connectors.base import hash_identifier
from app.database import SessionLocal
from app.hash_chain import compute_hash
from app.schema_guard import ensure_columns
from app.database import engine
from app.services.overlap import OverlapService
from app.services.resolution import InstitutionResolver, normalize_name
from app.services.sla import SLAService
from seed.narratives.engine import (
    LONG,
    MEDIUM,
    SHORT,
    ULTRA,
    NarrativeEngine,
    length_buckets,
    validate_corpus,
    weighted_choice,
)
from seed.narratives.lifecycle import ActionSpec, Lifecycle, build_lifecycle
from seed.narratives.slots import LOCALITIES, Slots
from seed.narratives.taxonomy import (
    CATEGORY_SUBTYPES,
    CATEGORY_WEIGHTS,
    CHANNEL_WEIGHTS,
    SEASONALITY,
    STATUS_MIX,
)

HERO_IDS = {"PG-2026-4471", "RB-2026-0892", "ML-2026-0001", "REV-2026-0001"}
OPEN_STATUSES = {"PENDING", "UNDER_PROCESS", "ESCALATED"}

CATEGORY_TO_BUREAU = {
    "FEE": ["PGRC", "PGRC", "RB"],
    "FACULTY": ["RB", "RB", "PGRC"],
    "INFRASTRUCTURE": ["RO", "RO", "RB"],
    "APPROVAL_VIOLATION": ["APPROVAL", "RB", "APPROVAL"],
    "ACADEMIC_ADMINISTRATION": ["PGRC", "PGRC", "RB"],
    "RAGGING_DISCRIMINATION": ["PGRC", "PGRC", "RB"],
    "GOVERNANCE_MISCONDUCT": ["RB", "RB", "APPROVAL"],
    "OTHER": ["PGRC", "RB", "RO"],
}

MIN_AGE_BY_STATUS = {
    "PENDING": 2,
    "UNDER_PROCESS": 20,
    "DISPOSED": 45,
    "TRANSFERRED": 20,
    "ESCALATED": 25,
}

PLANTED_GROUPS = [
    ("FEE", "EXCESS_FEE"),
    ("FACULTY", "GHOST_FACULTY"),
    ("INFRASTRUCTURE", "NO_FIRE_NOC"),
    ("APPROVAL_VIOLATION", "BEYOND_INTAKE"),
    ("ACADEMIC_ADMINISTRATION", "EXAM_RESULT_DELAY"),
    ("GOVERNANCE_MISCONDUCT", "FUND_MISUSE"),
    ("RAGGING_DISCRIMINATION", "HARASSMENT_GENERAL"),
    ("FEE", "CASH_WITHOUT_RECEIPT"),
]

CONTRADICTION_SPECS = [
    ("FEE", "REFUND_NOT_GIVEN"),
    ("INFRASTRUCTURE", "HOSTEL_MESS_CONDITIONS"),
    ("ACADEMIC_ADMINISTRATION", "PLACEMENT_FALSE_CLAIM"),
]

AMBIGUOUS_CITIES = ["Delhi", "Lucknow", "Nagpur", "Indore", "Patna", "Surat", "Bhopal"]


@dataclass
class Meta:
    case: models.Case
    institution: models.Institution | None
    display_institution: models.Institution | None
    category: str
    subtype: str
    status: str
    bureau_id: int
    assigned_officer_id: int | None
    date_received: datetime
    review: bool = False
    unresolved: bool = False
    planted_group: int | None = None
    shared_values: dict[str, str] = field(default_factory=dict)
    persona: str | None = None
    channel: str | None = None
    forced_outcome: str | None = None
    raw_style: str = "full"
    generated: Any = None
    lifecycle: Lifecycle | None = None


def _anchor_now() -> datetime:
    # Rounding to midnight makes an immediate re-run byte-for-byte stable.
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


def _allocate(count: int, weights: list[tuple[str, float]]) -> list[str]:
    raw = [(name, count * weight) for name, weight in weights]
    allocated = [(name, int(value)) for name, value in raw]
    remaining = count - sum(n for _, n in allocated)
    remainders = sorted(
        ((name, value - int(value)) for name, value in raw),
        key=lambda item: item[1],
        reverse=True,
    )
    result = [name for name, n in allocated for _ in range(n)]
    for name, _ in remainders[:remaining]:
        result.append(name)
    return result


def _weighted_month(rng: random.Random, category: str) -> int:
    weights = SEASONALITY.get(category, SEASONALITY["OTHER"])
    pick = rng.random() * sum(weights.values())
    upto = 0.0
    for month, weight in weights.items():
        upto += weight
        if pick <= upto:
            return month
    return 7


def _season_date(rng: random.Random, category: str, status: str, anchor: datetime) -> datetime:
    min_age = MIN_AGE_BY_STATUS.get(status, 7)
    year_weights = {str(anchor.year): 0.60, str(anchor.year - 1): 0.35, str(anchor.year - 2): 0.05}
    for _ in range(60):
        year = int(weighted_choice(rng, year_weights))
        month = _weighted_month(rng, category)
        day = rng.randint(1, 28)
        dt = datetime(year, month, day, rng.randint(9, 18), rng.randint(0, 59))
        age = (anchor - dt).days
        if dt < anchor and age >= min_age:
            return dt
    return anchor - timedelta(days=min_age + rng.randint(20, 120))


def _ambiguous_reference(rng: random.Random, inst: models.Institution | None) -> str:
    if inst is None:
        return "a private engineering college in the State"
    style = rng.choice(["city_type", "wrong_city", "partial_name", "generic"])
    locality = rng.choice(LOCALITIES.get(inst.city, ["Main Road"]))
    if style == "city_type":
        return f"the engineering college near {locality}, {inst.city}"
    if style == "wrong_city":
        return f"{inst.name}, {rng.choice([c for c in AMBIGUOUS_CITIES if c != inst.city])}"
    if style == "partial_name":
        words = inst.name.split()
        return f"{' '.join(words[:2])} college in {inst.city}"
    return f"a college in {inst.city} offering {rng.choice(['engineering', 'management', 'pharmacy'])} courses"


def _clear_reference(rng: random.Random, inst: models.Institution, style: str, *, force_id: bool = False) -> str:
    suffix = f" (AICTE ID {inst.aicte_permanent_id})" if force_id else ""
    if style == "abbrev":
        text = (
            inst.name.replace("Institute", "Inst").replace("College", "Coll")
            .replace("Technology", "Tech").replace("Engineering", "Engg")
        )
        return f"{text}, {inst.city}{suffix}"
    if style == "nickname":
        return " ".join(inst.name.split()[:3]) + f", {inst.city}{suffix}"
    if style == "typo":
        text = inst.name
        if len(text) > 12:
            pos = rng.randint(4, len(text) - 3)
            text = text[:pos] + text[pos + 1 :]
        return f"{text}, {inst.city}{suffix}"
    if style == "missing":
        return f"my college in {inst.city}{suffix}"
    return f"{inst.name}, {inst.city}{suffix}"


def _officers_by_bureau(users: list[models.User]) -> dict[int, list[models.User]]:
    result: dict[int, list[models.User]] = defaultdict(list)
    for user in users:
        if user.bureau_id:
            result[user.bureau_id].append(user)
    return result


def _officer_for(bureau_id: int, by_bureau: dict[int, list[models.User]], fallback: list[models.User], rng: random.Random) -> int | None:
    pool = by_bureau.get(bureau_id) or fallback
    return rng.choice(pool).id if pool else None


def _cleanup_derived(db: Session) -> None:
    db.query(models.CoordinationMessage).delete(synchronize_session=False)
    db.query(models.OverlapAlert).delete(synchronize_session=False)
    db.query(models.CaseLink).delete(synchronize_session=False)
    db.query(models.Notification).filter(
        models.Notification.type.in_(
            [
                models.NotificationType.OVERLAP,
                models.NotificationType.PENDING_REMINDER,
                models.NotificationType.ESCALATION,
                models.NotificationType.SLA,
            ]
        )
    ).delete(synchronize_session=False)
    db.commit()


def _action_enum(value: str) -> models.ActionType:
    return models.ActionType[value]


def _write_lifecycle(db: Session, case: models.Case, lifecycle: Lifecycle) -> None:
    prev = "0" * 64
    for index, action in enumerate(lifecycle.actions):
        payload = {
            "action": action.action_type,
            "case_id": case.case_id,
            "index": index,
            "at": action.created_at.isoformat(),
            "remarks": action.remarks,
        }
        current = compute_hash(prev, payload)
        db.add(
            models.CaseAction(
                case_id=case.id,
                actor_user_id=action.actor_user_id,
                bureau_id=action.bureau_id,
                action_type=_action_enum(action.action_type),
                remarks=action.remarks,
                document_url=action.document_url,
                created_at=action.created_at,
                prev_hash=prev,
                hash=current,
            )
        )
        prev = current


def _candidate_payload(resolver: InstitutionResolver, raw: str, inst: models.Institution | None) -> list[dict[str, Any]]:
    hints = {"city": inst.city, "state": inst.state} if inst else {}
    _, _, candidates = resolver.resolve(raw, hints)
    result = [
        {
            "institution_id": c.institution.id,
            "name": c.institution.name,
            "aicte_permanent_id": c.institution.aicte_permanent_id,
            "score": c.score,
            "reasons": c.reasons,
        }
        for c in candidates[:5]
    ]
    if inst and not any(c["institution_id"] == inst.id for c in result):
        result.insert(
            0,
            {
                "institution_id": inst.id,
                "name": inst.name,
                "aicte_permanent_id": inst.aicte_permanent_id,
                "score": 0.72,
                "reasons": ["partial_name", "city_area"],
            },
        )
    return result[:5]


def rewrite_seeded_cases(db: Session, *, seed: int | None = None, anchor: datetime | None = None) -> dict[str, Any]:
    seed = settings.seed_random_seed if seed is None else seed
    anchor = anchor or _anchor_now()
    rng = random.Random(seed)
    engine_ = NarrativeEngine(seed)

    cases = (
        db.scalars(
            select(models.Case)
            .where(
                models.Case.source_type == models.SourceType.SIMULATOR.value,
                models.Case.source_name == "seed",
                models.Case.case_id.notin_(HERO_IDS),
            )
            .order_by(models.Case.id)
        )
        .all()
    )
    if not cases:
        return {"rewritten": 0, "reason": "no seeded cases"}

    institutions = db.scalars(select(models.Institution)).all()
    institutions_by_id = {i.id: i for i in institutions}
    collision_ids: set[int] = set()
    by_city: dict[str, list[models.Institution]] = defaultdict(list)
    for inst in institutions:
        by_city[inst.city.lower()].append(inst)
    for group in by_city.values():
        for first_idx, first in enumerate(group):
            for second in group[first_idx + 1 :]:
                if fuzz.token_set_ratio(normalize_name(first.name), normalize_name(second.name)) >= 90:
                    collision_ids.add(first.id)
                    collision_ids.add(second.id)
    bureaus = {b.code: b for b in db.scalars(select(models.Bureau)).all()}
    users = db.scalars(select(models.User)).all()
    by_bureau = _officers_by_bureau(users)
    resolver = InstitutionResolver(db)

    non_emergency = [c for c in cases if not c.case_id.startswith("EMRG-")]
    statuses = _allocate(len(non_emergency), STATUS_MIX)
    rng.shuffle(statuses)
    status_iter = iter(statuses)

    metas: list[Meta] = []
    for case in cases:
        emergency = case.case_id.startswith("EMRG-")
        if emergency:
            status = "PENDING"
            category = "FEE"
            subtype = "EXCESS_FEE"
            date_received = anchor - timedelta(days=rng.randint(0, 6), hours=rng.randint(1, 20))
            inst = institutions_by_id.get(case.institution_id)
        else:
            status = next(status_iter)
            category = weighted_choice(rng, CATEGORY_WEIGHTS)
            subtype = rng.choice(list(CATEGORY_SUBTYPES[category].keys()))
            date_received = _season_date(rng, category, status, anchor)
            # Institution assignment is deterministic from the case ID rather
            # than from the previous run's state, which makes the first and all
            # subsequent reseeds identical.
            inst = random.Random(f"{seed}:{case.case_id}:institution").choice(institutions) if institutions else None

        bureau_code = rng.choice(CATEGORY_TO_BUREAU.get(category, ["PGRC"]))
        bureau = bureaus.get(bureau_code) or next(iter(bureaus.values()))
        assigned = _officer_for(bureau.id, by_bureau, users, rng)
        metas.append(
            Meta(
                case=case,
                institution=inst,
                display_institution=inst,
                category=category,
                subtype=subtype,
                status=status,
                bureau_id=bureau.id,
                assigned_officer_id=assigned,
                date_received=date_received,
            )
        )

    # Roughly 5% ambiguous references and 1.5% unresolved references.
    candidate_indices = [idx for idx, m in enumerate(metas) if not m.case.case_id.startswith("EMRG-")]
    rng.shuffle(candidate_indices)
    review_count = round(len(candidate_indices) * 0.05)
    unresolved_count = round(len(candidate_indices) * 0.015)
    review_indices = set(candidate_indices[:review_count])
    unresolved_indices = set(candidate_indices[review_count : review_count + unresolved_count])
    for idx in review_indices:
        m = metas[idx]
        m.review = True
        m.display_institution = random.Random(f"{seed}:{m.case.case_id}:ambiguous-institution").choice(institutions)
        m.institution = None
    for idx in unresolved_indices:
        m = metas[idx]
        m.unresolved = True
        m.display_institution = random.Random(f"{seed}:{m.case.case_id}:ambiguous-institution").choice(institutions)
        m.institution = None

    available = [
        idx
        for idx, m in enumerate(metas)
        if idx not in review_indices and idx not in unresolved_indices and not m.case.case_id.startswith("EMRG-")
    ]
    rng.shuffle(available)
    available_iter = iter(available)

    # Planted overlap groups: same institution/subtype, active cases in three
    # different bureaus, with shared facts but different voices and channels.
    group_personas = ["STUDENT", "PARENT", "ANONYMOUS_WELLWISHER"]
    group_channels = ["CSS", "CPGRAMS", "EMAIL"]
    bureau_codes = ["PGRC", "RB", "RO", "APPROVAL", "EVC"]
    audit_insts = rng.sample([i for i in institutions if i.aicte_permanent_id != "1-3538633"], k=min(len(PLANTED_GROUPS), len(institutions)))
    for group_no, (category, subtype) in enumerate(PLANTED_GROUPS):
        if group_no >= len(audit_insts):
            break
        inst = audit_insts[group_no]
        shared = Slots(rng).values(f"GROUP-{group_no}", institution=inst.name, city=inst.city)
        shared.pop("ref", None)
        shared.pop("case_id", None)
        chosen_bureaus = rng.sample(bureau_codes, k=3)
        for member in range(3):
            try:
                idx = next(available_iter)
            except StopIteration:
                break
            m = metas[idx]
            m.institution = inst
            m.display_institution = inst
            m.category = category
            m.subtype = subtype
            m.status = "UNDER_PROCESS"
            m.bureau_id = bureaus[chosen_bureaus[member]].id
            m.assigned_officer_id = _officer_for(m.bureau_id, by_bureau, users, rng)
            m.date_received = anchor - timedelta(days=rng.randint(22, 72))
            m.planted_group = group_no
            m.shared_values = dict(shared)
            m.persona = group_personas[member % len(group_personas)]
            m.channel = group_channels[member % len(group_channels)]
            m.raw_style = ["full", "abbrev", "nickname"][member % 3]

    # Contradictory dispositions for the same institution and sub-type.
    contradiction_insts = rng.sample(
        [i for i in institutions if i.aicte_permanent_id != "1-3538633"], k=min(len(CONTRADICTION_SPECS), len(institutions))
    )
    for spec_no, (category, subtype) in enumerate(CONTRADICTION_SPECS):
        if spec_no >= len(contradiction_insts):
            break
        inst = contradiction_insts[spec_no]
        for member in range(2):
            try:
                idx = next(available_iter)
            except StopIteration:
                break
            m = metas[idx]
            m.institution = inst
            m.display_institution = inst
            m.category = category
            m.subtype = subtype
            m.status = "DISPOSED"
            m.bureau_id = bureaus["RB" if member == 0 else "PGRC"].id
            m.assigned_officer_id = _officer_for(m.bureau_id, by_bureau, users, rng)
            m.date_received = anchor - timedelta(days=rng.randint(90, 240))
            m.forced_outcome = "DEFICIENCY_CONFIRMED" if member == 0 else "NO_DEFICIENCY"
            m.raw_style = "full"

    buckets = length_buckets(len(metas), rng)
    for idx, m in enumerate(metas):
        style_pool = ["full"] * 8 + ["abbrev", "nickname", "typo"]
        if not m.review and not m.unresolved:
            m.raw_style = m.raw_style if m.raw_style != "full" else rng.choice(style_pool)
        gen_inst = m.display_institution or m.institution
        if gen_inst is None:
            gen_inst = next(iter(institutions))
        m.generated = engine_.build(
            case_id=m.case.case_id,
            institution=gen_inst,
            category=m.category,
            subtype=m.subtype,
            persona=m.persona,
            channel=m.channel,
            bucket=buckets[idx],
            channel_weights=CHANNEL_WEIGHTS,
            shared_values=m.shared_values or None,
            ref_style=m.raw_style,
        )

        if m.review:
            raw = _ambiguous_reference(rng, m.display_institution)
            m.display_institution = m.display_institution
        elif m.unresolved:
            raw = _ambiguous_reference(rng, None)
        else:
            raw = _clear_reference(rng, gen_inst, m.raw_style, force_id=gen_inst.id in collision_ids)

        if m.unresolved:
            confidence = 0.0
        elif m.review:
            confidence = round(rng.uniform(0.66, 0.82), 2)
        else:
            hints = {"city": gen_inst.city, "state": gen_inst.state, "region": gen_inst.region}
            resolved, score, _ = resolver.resolve(raw, hints)
            if resolved is None or resolved.id != gen_inst.id:
                # Some abbreviations and one-character typos are genuinely too
                # fuzzy for the resolver. Keep the case resolved but fall back to
                # an unambiguous reference rather than mislabelling it.
                raw = f"{gen_inst.name}, {gen_inst.city}"
                if gen_inst.id in collision_ids:
                    raw += f" (AICTE ID {gen_inst.aicte_permanent_id})"
                resolved, score, _ = resolver.resolve(raw, hints)
            if resolved is not None and resolved.id == gen_inst.id:
                confidence = max(0.91, round(score, 2))
            else:
                confidence = round(rng.uniform(0.91, 0.98), 2)
        setattr(m, "raw_text", raw)
        setattr(m, "confidence", confidence)

        lifecycle = build_lifecycle(
            seed=seed,
            case_id=m.case.case_id,
            date_received=m.date_received,
            status=m.status,
            category=m.category,
            subtype=m.subtype,
            institution=m.institution,
            bureau_id=m.bureau_id,
            assigned_officer_id=m.assigned_officer_id,
            values=m.generated.metadata["values"],
            now=anchor,
        )
        if m.forced_outcome:
            lifecycle.outcome_tag = m.forced_outcome
            final = lifecycle.actions[-1]
            final.action_type = "OUTCOME_TAGGED"
            final.remarks = (
                "Final outcome recorded after verification of the institution's reply and records. "
                + ("Deficiency confirmed." if m.forced_outcome == "DEFICIENCY_CONFIRMED" else "No deficiency established.")
            )
            lifecycle.last_action_at = final.created_at
            lifecycle.last_action_text = final.remarks
        m.lifecycle = lifecycle

    records = [
        {
            "case_id": m.case.case_id,
            "narrative": m.generated.narrative,
            "length_bucket": m.generated.length_bucket,
            "language": m.generated.language,
            "complainant_type": m.generated.complainant_type,
            "category": m.category,
        }
        for m in metas
    ]
    validation = validate_corpus(records)

    # Rebuild the lifecycle/actions and overwrite case fields in place.
    _cleanup_derived(db)
    target_ids = [m.case.id for m in metas]
    db.query(models.CaseAction).filter(models.CaseAction.case_id.in_(target_ids)).delete(synchronize_session=False)
    db.query(models.ReviewQueue).filter(models.ReviewQueue.case_id.in_(target_ids)).delete(synchronize_session=False)
    db.flush()

    resolver_for_review = InstitutionResolver(db)
    for m in metas:
        case = m.case
        gen = m.generated
        lc = m.lifecycle
        assert lc is not None
        case.subject = gen.subject[:240]
        case.category = models.CaseCategory(m.category)
        case.category_subtype = m.subtype
        case.complainant_type = gen.complainant_type
        case.institution_id = m.institution.id if m.institution else None
        case.raw_institution_text = getattr(m, "raw_text")
        case.bureau_id = m.bureau_id
        case.assigned_officer_id = m.assigned_officer_id
        case.date_received = m.date_received
        case.narrative = gen.narrative
        case.narrative_original = gen.narrative_original
        case.narrative_translated = gen.narrative if gen.language != "en" else gen.narrative
        case.language = gen.language
        case.status = models.CaseStatus(m.status)
        case.outcome_tag = models.OutcomeTag(lc.outcome_tag) if lc.outcome_tag else None
        case.last_action_at = lc.last_action_at
        case.last_action_text = lc.last_action_text
        case.next_action_text = lc.next_action_text
        case.expected_disposal_date = lc.expected_disposal_date
        if m.unresolved:
            case.resolution_status = models.ResolutionStatus.UNRESOLVED
        elif m.review:
            case.resolution_status = models.ResolutionStatus.NEEDS_REVIEW
        else:
            case.resolution_status = models.ResolutionStatus.RESOLVED
        case.match_confidence = float(getattr(m, "confidence"))
        case.source_name = "seed"
        case.source_type = models.SourceType.SIMULATOR.value
        case.is_synthetic = True
        case.idempotency_key = f"seed:{case.case_id}"
        case.complainant_hash = hash_identifier(f"realistic-seed-{case.case_id}")
        _write_lifecycle(db, case, lc)

        if m.review:
            raw = getattr(m, "raw_text")
            candidates = _candidate_payload(resolver_for_review, raw, m.display_institution)
            db.add(
                models.ReviewQueue(
                    case_id=case.id,
                    candidate_institutions=candidates,
                    status=models.ReviewStatus.OPEN,
                )
            )
    db.commit()

    # Recompute overlap alerts from the rewritten active case population.
    active = db.scalars(
        select(models.Case).where(
            models.Case.institution_id.is_not(None),
            models.Case.status.in_([models.CaseStatus.PENDING, models.CaseStatus.UNDER_PROCESS, models.CaseStatus.ESCALATED]),
        )
    ).all()
    by_inst: dict[int, models.Case] = {}
    for case in active:
        by_inst.setdefault(case.institution_id, case)
    overlap_count = 0
    for case in by_inst.values():
        before = db.query(models.OverlapAlert).count()
        OverlapService(db).detect_for_case(case, None)
        after = db.query(models.OverlapAlert).count()
        if after > before:
            overlap_count += 1

    # Rebuild SLA/reminder notifications from the same case dates.
    db.query(models.Notification).filter(
        models.Notification.type.in_([models.NotificationType.PENDING_REMINDER, models.NotificationType.SLA])
    ).delete(synchronize_session=False)
    db.commit()
    SLAService(db).run_checks()

    stats = {
        "rewritten": len(metas),
        "review": sum(1 for m in metas if m.review),
        "unresolved": sum(1 for m in metas if m.unresolved),
        "planted_overlap_groups": len({m.planted_group for m in metas if m.planted_group is not None}),
        "overlap_alerts": db.query(models.OverlapAlert).count(),
        "contradictory_institutions": len([s for s in CONTRADICTION_SPECS]),
        "lengths": validation["lengths"],
        "languages": validation["languages"],
        "personas": validation["personas"],
        "categories": validation["categories"],
        "statuses": dict(Counter(m.status for m in metas)),
    }
    print(
        "Realistic reseed complete: "
        f"{stats['rewritten']} cases | review {stats['review']} | unresolved {stats['unresolved']} | "
        f"overlap alerts {stats['overlap_alerts']} | languages {stats['languages']}"
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=settings.seed_random_seed)
    args = parser.parse_args()
    ensure_columns(engine)
    db = SessionLocal()
    try:
        rewrite_seeded_cases(db, seed=args.seed)
    finally:
        db.close()


if __name__ == "__main__":
    main()
