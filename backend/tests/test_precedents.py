from fastapi.testclient import TestClient

from app import models
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.services.precedents import find_precedents


def _client(db, user):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _set_resolved(case, outcome):
    case.status = models.CaseStatus.DISPOSED
    case.outcome_tag = models.OutcomeTag(outcome)
    case.last_action_at = case.date_received
    return case


def test_precedents_are_advisory_and_preserve_contradictory_outcomes(db, base_data):
    open_case = base_data["make_case"](
        "OPEN-PRECEDENT-1",
        base_data["rb"],
        models.SourceChannel.CSS,
        narrative="The institution charged excess semester fee beyond the approved structure and refused a refund.",
    )
    confirmed = _set_resolved(
        base_data["make_case"](
            "PRECEDENT-CONFIRMED",
            base_data["rb"],
            models.SourceChannel.CSS,
            tag=models.OutcomeTag.DEFICIENCY_CONFIRMED,
            narrative="Excess semester fee was charged beyond the approved structure; deficiency confirmed after verification.",
        ),
        "DEFICIENCY_CONFIRMED",
    )
    no_deficiency = _set_resolved(
        base_data["make_case"](
            "PRECEDENT-NO-DEFICIENCY",
            base_data["rb"],
            models.SourceChannel.CPGRAMS,
            tag=models.OutcomeTag.NO_DEFICIENCY,
            narrative="The institution collected additional semester fee but records showed it followed the approved fee structure.",
        ),
        "NO_DEFICIENCY",
    )
    db.commit()

    result = find_precedents(db, open_case, base_data["user"], limit=5, min_score=0.0)
    assert result["advisory_only"] is True
    assert result["automatic_action"] is False
    assert result["semantic_available"] is False
    assert result["candidates"]
    assert result["outcome_conflict"] is True
    assert result["outcome_conflict_note"]
    assert {item["outcome_tag"] for item in result["candidates"]} >= {"DEFICIENCY_CONFIRMED", "NO_DEFICIENCY"}
    assert {entry["outcome"] for entry in result["outcome_summary"]} >= {"DEFICIENCY_CONFIRMED", "NO_DEFICIENCY"}
    assert result["disclaimer"].startswith("Advisory only.")

    client = _client(db, base_data["user"])
    try:
        response = client.get(f"/cases/{open_case.id}/precedents", params={"limit": 5, "min_score": 0})
        assert response.status_code == 200
        payload = response.json()
        assert payload["advisory_only"] is True
        assert payload["automatic_action"] is False
        assert payload["outcome_conflict"] is True
        assert len(payload["candidates"]) >= 2
        assert {"case_id", "case_number", "score", "outcome_tag", "feedback"} <= set(payload["candidates"][0])
    finally:
        app.dependency_overrides.clear()


def test_precedent_filters_and_bureau_scope(db, base_data):
    open_case = base_data["make_case"](
        "OPEN-PRECEDENT-2",
        base_data["rb"],
        models.SourceChannel.CSS,
        narrative="Excess fee was charged for the semester and no receipt was issued.",
    )
    fee_precedent = _set_resolved(
        base_data["make_case"](
            "PRECEDENT-FEE",
            base_data["rb"],
            models.SourceChannel.CSS,
            tag=models.OutcomeTag.DEFICIENCY_CONFIRMED,
            narrative="Excess fee was charged for the semester and no receipt was issued.",
        ),
        "DEFICIENCY_CONFIRMED",
    )
    faculty_precedent = _set_resolved(
        base_data["make_case"](
            "PRECEDENT-FACULTY",
            base_data["rb"],
            models.SourceChannel.CSS,
            tag=models.OutcomeTag.PENALTY_PROPOSED,
            narrative="Faculty members were shown on the portal but were not attending classes.",
            category=models.CaseCategory.FACULTY,
        ),
        "PENALTY_PROPOSED",
    )
    db.commit()

    filtered = find_precedents(db, open_case, base_data["user"], same_category=True, min_score=0.0)
    assert {item["case_number"] for item in filtered["candidates"]} == {"PRECEDENT-FEE"}

    officer = models.User(
        name="RB Officer",
        email="rb.precedent@test.gov.in",
        password_hash="x",
        role=models.UserRole.RB_OFFICER,
        bureau_id=base_data["rb"].id,
        is_active=True,
    )
    db.add(officer)
    db.commit()
    other_bureau_precedent = _set_resolved(
        base_data["make_case"](
            "PRECEDENT-PGRC",
            base_data["pgrc"],
            models.SourceChannel.CSS,
            tag=models.OutcomeTag.DEFICIENCY_CONFIRMED,
            narrative="Excess fee was charged for the semester and no receipt was issued.",
        ),
        "DEFICIENCY_CONFIRMED",
    )
    db.commit()
    scoped = find_precedents(db, open_case, officer, min_score=0.0)
    case_numbers = {item["case_number"] for item in scoped["candidates"]}
    assert "PRECEDENT-PGRC" not in case_numbers
    assert other_bureau_precedent.case_id not in case_numbers


def test_precedent_feedback_is_persisted_and_audited(db, base_data):
    open_case = base_data["make_case"](
        "OPEN-PRECEDENT-3",
        base_data["rb"],
        models.SourceChannel.CSS,
        narrative="A refund was not processed after withdrawal from the programme.",
    )
    precedent = _set_resolved(
        base_data["make_case"](
            "PRECEDENT-FEEDBACK",
            base_data["rb"],
            models.SourceChannel.CSS,
            tag=models.OutcomeTag.CLOSED_NO_ACTION,
            narrative="Refund was delayed after withdrawal, but the institution processed it before disposal.",
        ),
        "CLOSED_NO_ACTION",
    )
    db.commit()
    client = _client(db, base_data["user"])
    try:
        response = client.post(
            f"/cases/{open_case.id}/precedents/{precedent.id}/feedback",
            json={"feedback": "HELPFUL", "note": "Useful comparable disposal"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["feedback"] == "HELPFUL"

        again = client.post(
            f"/cases/{open_case.id}/precedents/{precedent.id}/feedback",
            json={"feedback": "WRONG_MATCH", "note": "Different facts"},
        )
        assert again.status_code == 200
        assert again.json()["feedback"] == "WRONG_MATCH"

        row = db.query(models.PrecedentFeedback).filter_by(
            case_id=open_case.id,
            precedent_case_id=precedent.id,
            user_id=base_data["user"].id,
        ).one()
        assert row.feedback == "WRONG_MATCH"
        actions = db.query(models.CaseAction).filter_by(
            case_id=open_case.id, action_type=models.ActionType.REMARK
        ).all()
        assert len(actions) == 2
        assert any("Precedent feedback" in action.remarks for action in actions)
    finally:
        app.dependency_overrides.clear()
