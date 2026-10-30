from __future__ import annotations

from collections import Counter, defaultdict

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import apply_region_scope, can_see_all
from .matching_benchmark import normalize_text, tokenize

FEEDBACK_VALUES = {"HELPFUL", "NOT_HELPFUL", "WRONG_MATCH"}
RESOLVED = or_(models.Case.outcome_tag.is_not(None), models.Case.status == models.CaseStatus.DISPOSED)


def _precedent_text(case: models.Case) -> str:
    return case.narrative_translated or case.narrative or ""


def _case_excerpt(case: models.Case, current: models.User) -> str:
    if (
        case.category == models.CaseCategory.RAGGING_DISCRIMINATION
        and not can_see_all(current)
        and case.bureau_id != current.bureau_id
    ):
        return "[RESTRICTED - RAGGING/DISCRIMINATION] Narrative masked by bureau scope."
    text = " ".join(_precedent_text(case).split())
    return text[:320] + ("…" if len(text) > 320 else "")


def _feedback_summary(db: Session, case_id: int, precedent_ids: list[int], user_id: int) -> dict[int, dict]:
    if not precedent_ids:
        return {}
    rows = db.scalars(
        select(models.PrecedentFeedback).where(
            models.PrecedentFeedback.case_id == case_id,
            models.PrecedentFeedback.precedent_case_id.in_(precedent_ids),
        )
    ).all()
    summary: dict[int, dict] = defaultdict(lambda: {"HELPFUL": 0, "NOT_HELPFUL": 0, "WRONG_MATCH": 0, "my_feedback": None})
    for row in rows:
        summary[row.precedent_case_id][row.feedback] = summary[row.precedent_case_id].get(row.feedback, 0) + 1
        if row.user_id == user_id:
            summary[row.precedent_case_id]["my_feedback"] = row.feedback
    return dict(summary)


def _outcome_conflict(candidates: list[dict]) -> tuple[bool, str | None]:
    outcomes = {candidate.get("outcome_tag") or "NOT_RECORDED" for candidate in candidates}
    if len(outcomes) > 1:
        return (
            True,
            "The retrieved precedents record different outcomes. They are shown together so that the officer can see the disagreement; no automatic outcome is inferred.",
        )
    return False, None


def find_precedents(
    db: Session,
    case: models.Case,
    current: models.User,
    *,
    limit: int = 5,
    min_score: float = 0.15,
    category: str | None = None,
    institution_id: int | None = None,
    language: str | None = None,
    outcome_tag: str | None = None,
    same_category: bool = False,
    same_institution: bool = False,
) -> dict:
    query_text = _precedent_text(case)
    stmt = select(models.Case).where(
        models.Case.id != case.id,
        RESOLVED,
    )
    stmt = apply_region_scope(stmt, current, models.Case)
    if same_category or category:
        selected_category = category or case.category.value
        try:
            stmt = stmt.where(models.Case.category == models.CaseCategory(selected_category))
        except ValueError:
            pass
    if same_institution or institution_id:
        selected_institution = institution_id or case.institution_id
        if selected_institution:
            stmt = stmt.where(models.Case.institution_id == selected_institution)
    if language:
        stmt = stmt.where(models.Case.language == language)
    if outcome_tag:
        try:
            stmt = stmt.where(models.Case.outcome_tag == models.OutcomeTag(outcome_tag))
        except ValueError:
            pass
    candidates = db.scalars(stmt.order_by(models.Case.last_action_at.desc()).limit(1500)).all()
    if not candidates or not query_text.strip():
        return _empty_response(case, current, limit, min_score)

    candidate_texts = [_precedent_text(candidate) for candidate in candidates]
    try:
        char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
        word_vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        char_matrix = char_vectorizer.fit_transform(candidate_texts)
        word_matrix = word_vectorizer.fit_transform(candidate_texts)
        char_scores = cosine_similarity(char_vectorizer.transform([query_text]), char_matrix)[0]
        word_scores = cosine_similarity(word_vectorizer.transform([query_text]), word_matrix)[0]
    except Exception:
        return _empty_response(case, current, limit, min_score, note="The TF-IDF fallback could not be fitted for this corpus.")

    query_tokens = set(tokenize(query_text))
    scored = []
    for index, candidate in enumerate(candidates):
        candidate_text = candidate_texts[index]
        token_set = fuzz.token_set_ratio(normalize_text(query_text), normalize_text(candidate_text)) / 100.0
        base_score = 0.45 * float(char_scores[index]) + 0.40 * float(word_scores[index]) + 0.15 * token_set
        same_category_value = candidate.category == case.category
        same_subtype_value = bool(case.category_subtype and candidate.category_subtype == case.category_subtype)
        same_institution_value = bool(case.institution_id and candidate.institution_id == case.institution_id)
        same_language_value = bool(case.language and candidate.language == case.language)
        boost = (
            (0.05 if same_category_value else 0.0)
            + (0.05 if same_subtype_value else 0.0)
            + (0.03 if same_institution_value else 0.0)
            + (0.01 if same_language_value else 0.0)
        )
        score = round(min(1.0, base_score + boost), 4)
        if score < min_score:
            continue
        shared = sorted(query_tokens & set(tokenize(candidate_text)))
        scored.append(
            {
                "score": score,
                "components": {
                    "char_tfidf": round(float(char_scores[index]), 4),
                    "word_tfidf": round(float(word_scores[index]), 4),
                    "fuzzy_token_set": round(token_set, 4),
                    "metadata_boost": round(boost, 4),
                },
                "candidate": candidate,
                "same_category": same_category_value,
                "same_subtype": same_subtype_value,
                "same_institution": same_institution_value,
                "cross_language": bool(case.language and candidate.language and case.language != candidate.language),
                "why_similar": shared[:8],
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["candidate"].date_received, item["candidate"].id))
    selected = scored[:limit]
    feedback = _feedback_summary(db, case.id, [item["candidate"].id for item in selected], current.id)
    candidates_out = []
    for item in selected:
        candidate = item["candidate"]
        outcomes = feedback.get(candidate.id, {"HELPFUL": 0, "NOT_HELPFUL": 0, "WRONG_MATCH": 0, "my_feedback": None})
        candidates_out.append(
            {
                "case_id": candidate.id,
                "case_number": candidate.case_id,
                "subject": candidate.subject,
                "category": candidate.category.value,
                "category_subtype": candidate.category_subtype,
                "institution": (
                    {"id": candidate.institution.id, "name": candidate.institution.name}
                    if candidate.institution
                    else None
                ),
                "outcome_tag": candidate.outcome_tag.value if candidate.outcome_tag else None,
                "status": candidate.status.value,
                "date_received": candidate.date_received.isoformat(),
                "language": candidate.language,
                "score": item["score"],
                "components": item["components"],
                "why_similar": item["why_similar"],
                "same_category": item["same_category"],
                "same_subtype": item["same_subtype"],
                "same_institution": item["same_institution"],
                "cross_language": item["cross_language"],
                "narrative_excerpt": _case_excerpt(candidate, current),
                "feedback": outcomes,
            }
        )
    conflict, conflict_note = _outcome_conflict(candidates_out)
    return {
        "advisory_only": True,
        "automatic_action": False,
        "method": "tfidf_char_word_hybrid_with_fuzzy_token_set",
        "semantic_available": False,
        "semantic_note": (
            "No multilingual sentence-embedding model was loaded. Retrieval uses the honest "
            "TF-IDF/fuzzy fallback over the English narrative translation where available."
        ),
        "query": {
            "case_id": case.id,
            "case_number": case.case_id,
            "category": case.category.value,
            "institution_id": case.institution_id,
            "language": case.language,
            "filters": {
                "category": category,
                "institution_id": institution_id,
                "language": language,
                "outcome_tag": outcome_tag,
                "same_category": same_category,
                "same_institution": same_institution,
            },
        },
        "candidates": candidates_out,
        "outcome_summary": [
            {"outcome": outcome, "count": count}
            for outcome, count in Counter(
                candidate["outcome_tag"] or "NOT_RECORDED" for candidate in candidates_out
            ).most_common()
        ],
        "outcome_conflict": conflict,
        "outcome_conflict_note": conflict_note,
        "disclaimer": (
            "Advisory only. Precedents are similar resolved complaints for context; they do not "
            "determine the outcome of this case. Contradictory outcomes are shown together and must "
            "not be concealed or treated as an automatic recommendation."
        ),
    }


def _empty_response(
    case: models.Case,
    current: models.User,
    limit: int,
    min_score: float,
    note: str | None = None,
) -> dict:
    return {
        "advisory_only": True,
        "automatic_action": False,
        "method": "tfidf_char_word_hybrid_with_fuzzy_token_set",
        "semantic_available": False,
        "semantic_note": (
            "No multilingual sentence-embedding model was loaded. Retrieval uses the honest "
            "TF-IDF/fuzzy fallback over the English narrative translation where available."
        ),
        "query": {
            "case_id": case.id,
            "case_number": case.case_id,
            "category": case.category.value,
            "institution_id": case.institution_id,
            "language": case.language,
            "filters": {},
        },
        "candidates": [],
        "outcome_summary": [],
        "outcome_conflict": False,
        "outcome_conflict_note": None,
        "disclaimer": (
            "Advisory only. Precedents are similar resolved complaints for context; they do not "
            "determine the outcome of this case. Contradictory outcomes are shown together and must "
            "not be concealed or treated as an automatic recommendation."
        ),
        "note": note or "No resolved precedents matched this case.",
    }
