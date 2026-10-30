import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session
from unidecode import unidecode

from .. import models
from ..config import settings


ABBREV = {
    "inst": "institute",
    "instt": "institute",
    "engg": "engineering",
    "tech": "technology",
    "coll": "college",
    "univ": "university",
    "poly": "polytechnic",
    "cet": "college of engineering and technology",
    "st": "saint",
}


@dataclass
class ResolutionCandidate:
    institution: models.Institution
    score: float
    reasons: list[str]


def normalize_name(text: str) -> str:
    if not text:
        return ""
    text = unidecode(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = []
    for t in text.split():
        if t in ABBREV:
            tokens.append(ABBREV[t])
            continue
        if t in {"the", "of", "and", "for"}:
            continue
        tokens.append(t)
    return " ".join(tokens)


def extract_aicte_id(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"(\b1-[0-9]{6,8}\b)", unidecode(text))
    return m.group(1) if m else None


class InstitutionResolver:
    def __init__(self, db: Session):
        self.db = db
        self.institutions = self.db.scalars(select(models.Institution)).all()
        self.alias_map: dict[str, models.Institution] = {}
        for inst in self.institutions:
            self.alias_map[normalize_name(inst.name)] = inst
            for a in inst.aliases or []:
                self.alias_map[normalize_name(a)] = inst
            for ar in inst.alias_rows:
                self.alias_map[normalize_name(ar.alias)] = inst
        self.city_names = sorted({i.city for i in self.institutions if i.city}, key=len, reverse=True)
        self.state_names = sorted({i.state for i in self.institutions if i.state}, key=len, reverse=True)

    def _infer_hints(self, raw_text: str, hints: dict[str, Any]) -> dict[str, Any]:
        text = unidecode(raw_text or "").lower()
        inferred = dict(hints)
        if not inferred.get("city"):
            for city in self.city_names:
                if re.search(rf"(?<![a-z]){re.escape(city.lower())}(?![a-z])", text):
                    inferred["city"] = city
                    break
        if not inferred.get("state"):
            for state in self.state_names:
                if re.search(rf"(?<![a-z]){re.escape(state.lower())}(?![a-z])", text):
                    inferred["state"] = state
                    break
        return inferred

    def resolve(self, raw_text: str, hints: dict[str, Any] | None = None) -> tuple[models.Institution | None, float, list[ResolutionCandidate]]:
        hints = self._infer_hints(raw_text, hints or {})
        aid = extract_aicte_id(raw_text) or hints.get("aicte_permanent_id")
        if aid:
            inst = self.db.scalar(select(models.Institution).where(models.Institution.aicte_permanent_id == aid))
            if inst:
                return inst, 1.0, [ResolutionCandidate(inst, 1.0, ["exact_aicte_id"])]

        norm = normalize_name(raw_text)
        if norm and norm in self.alias_map:
            inst = self.alias_map[norm]
            hinted_city = hints.get("city")
            if not hinted_city or not inst.city or hinted_city.lower() == inst.city.lower():
                return inst, 0.98, [ResolutionCandidate(inst, 0.98, ["exact_normalized_alias"])]

        candidates: list[ResolutionCandidate] = []
        for inst in self.institutions:
            in_norm = normalize_name(inst.name)
            score = 0.0
            reasons = []
            token_score = fuzz.token_set_ratio(norm, in_norm)
            score += 0.60 * (token_score / 100.0)
            reasons.append(f"token_set:{token_score:.0f}")
            if in_norm and f" {in_norm} " in f" {norm} ":
                score += 0.25
                reasons.append("exact_name_phrase")
            alias_phrase = any(a_norm and f" {a_norm} " in f" {norm} " for a_norm in (normalize_name(a) for a in (inst.aliases or [])))
            if alias_phrase:
                score += 0.20
                reasons.append("alias_phrase")
            addr_score = fuzz.partial_ratio(normalize_name(raw_text), normalize_name(inst.address))
            score += 0.1 * (addr_score / 100.0)
            if hints.get("city") and inst.city and hints["city"].lower() == inst.city.lower():
                score += 0.15
                reasons.append("city_match")
            if hints.get("state") and inst.state and hints["state"].lower() == inst.state.lower():
                score += 0.1
                reasons.append("state_match")
            if inst.region and hints.get("region") and inst.region.lower() == hints["region"].lower():
                score += 0.1
                reasons.append("region_match")
            if not alias_phrase and any(normalize_name(a) and normalize_name(a) in norm for a in (inst.aliases or [])):
                score += 0.05
                reasons.append("alias_token")
            score = min(score, 0.99)
            if score >= 0.2:
                candidates.append(ResolutionCandidate(inst, round(score, 4), reasons))
        candidates.sort(key=lambda c: c.score, reverse=True)
        top = candidates[:5]
        if not top:
            return None, 0.0, []
        best = top[0]
        if best.score >= settings.auto_link_threshold:
            return best.institution, best.score, top
        if best.score >= settings.review_threshold:
            return None, best.score, top
        return None, best.score, []
