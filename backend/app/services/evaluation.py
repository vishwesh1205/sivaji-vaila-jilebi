from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from .resolution import InstitutionResolver, normalize_name


@dataclass(frozen=True)
class EvaluationReference:
    raw_text: str
    expected_institution_id: int
    style: str


def _unique_institutions(db: Session) -> list[models.Institution]:
    institutions = db.scalars(select(models.Institution).order_by(models.Institution.id)).all()
    seen: set[str] = set()
    unique = []
    for inst in institutions:
        key = normalize_name(inst.name)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(inst)
    return unique


def _abbreviate(name: str) -> str:
    return (
        name.replace("Institute", "Inst")
        .replace("College", "Coll")
        .replace("Technology", "Tech")
        .replace("Engineering", "Engg")
    )


def _typo(name: str, rng: random.Random) -> str:
    if len(name) < 8:
        return name
    pos = rng.randint(4, len(name) - 2)
    return name[:pos] + name[pos + 1 :]


def build_evaluation_set(db: Session, count: int = 240, seed: int = settings.seed_random_seed) -> list[EvaluationReference]:
    institutions = _unique_institutions(db)
    if not institutions:
        return []
    rng = random.Random(seed)
    rng.shuffle(institutions)
    references: list[EvaluationReference] = []
    for index in range(count):
        inst = institutions[index % len(institutions)]
        style = index % 6
        if style == 0:
            raw = f"{inst.name}, {inst.city}"
            label = "name_with_city"
        elif style == 1:
            raw = f"{_abbreviate(inst.name)}, {inst.city}"
            label = "abbreviated_name"
        elif style == 2:
            raw = f"{_typo(inst.name, rng)}, {inst.city}"
            label = "typo_name"
        elif style == 3:
            words = [w for w in inst.name.split() if w.lower() not in {"of", "and", "the", "for", "in"}]
            raw = f"{' '.join(words[:2])}, {inst.city}"
            label = "partial_name"
        elif style == 4:
            alias = (inst.aliases or [None])[0]
            raw = f"{alias or inst.name}, {inst.city}"
            label = "alias_reference"
        else:
            raw = f"{inst.name} (AICTE ID {inst.aicte_permanent_id})"
            label = "aicte_id"
        references.append(EvaluationReference(raw_text=raw, expected_institution_id=inst.id, style=label))
    return references


def evaluate_resolution(db: Session, count: int = 240, seed: int = settings.seed_random_seed) -> dict:
    references = build_evaluation_set(db, count=count, seed=seed)
    resolver = InstitutionResolver(db)
    true_positive = false_positive = false_negative = 0
    by_style: dict[str, dict[str, int]] = {}
    failures = []
    for reference in references:
        predicted, confidence, _ = resolver.resolve(reference.raw_text, {})
        style = by_style.setdefault(reference.style, {"total": 0, "correct": 0})
        style["total"] += 1
        if predicted and predicted.id == reference.expected_institution_id:
            true_positive += 1
            style["correct"] += 1
        elif predicted:
            false_positive += 1
            if len(failures) < 8:
                failures.append({"raw_text": reference.raw_text, "expected_id": reference.expected_institution_id, "predicted_id": predicted.id, "confidence": confidence, "style": reference.style})
        else:
            false_negative += 1
            if len(failures) < 8:
                failures.append({"raw_text": reference.raw_text, "expected_id": reference.expected_institution_id, "predicted_id": None, "confidence": confidence, "style": reference.style})
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "seed": seed,
        "sample_size": len(references),
        "institution_pool": len(_unique_institutions(db)),
        "thresholds": {"auto_link": settings.auto_link_threshold, "review": settings.review_threshold},
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "coverage": round((true_positive + false_positive) / len(references), 4) if references else 0.0,
        "by_style": [{"style": key, **value, "accuracy": round(value["correct"] / value["total"], 4) if value["total"] else 0.0} for key, value in sorted(by_style.items())],
        "failures": failures,
        "note": "Deterministic offline benchmark over messy synthetic references. Unresolved references count as false negatives; wrong auto-links count as false positives.",
    }
