from datetime import datetime

from fastapi.testclient import TestClient

from app import models
from app.database import get_db
from app.dependencies import get_current_user
from app.hash_chain import compute_hash
from app.main import app


def test_provenance_endpoint_and_conflict_ack(db, base_data, monkeypatch):
    user = base_data["user"]

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    raw = models.RawPayload(source="css", source_record_id="CSS-API-1", payload_json={"ticket_no": "CSS-API-1", "institution_name": "St Xaviers Inst of Tech"}, payload_sha256="c" * 64, source_type="SIMULATOR", fetched_at=datetime.utcnow())
    db.add(raw)
    db.commit()
    case = base_data["make_case"]("PG-2026-9501", base_data["pgrc"], models.SourceChannel.CPGRAMS)
    case.raw_payload_id = raw.id
    prev = "0" * 64
    db.add(models.CaseAction(case_id=case.id, actor_user_id=user.id, bureau_id=case.bureau_id, action_type=models.ActionType.CREATED, remarks="created", prev_hash=prev, hash=compute_hash(prev, {"action": "CREATED"})))
    db.commit()

    response = client.get(f"/provenance/case/{case.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["stage_1_raw_payload"]["payload_sha256"] == "c" * 64
    assert data["stage_2_normalized"]["case_id"] == "PG-2026-9501"
    assert "candidates" in data["stage_3_resolution"]
    assert "rule_fired" in data["stage_4_overlap"]

    other = base_data["make_case"]("RB-2026-9502", base_data["rb"], models.SourceChannel.CSS, tag=models.OutcomeTag.NO_DEFICIENCY)
    db.add(models.CaseLink(case_a_id=case.id, case_b_id=other.id, link_type=models.LinkType.MANUAL))
    db.commit()
    blocked = client.post(f"/cases/{case.id}/outcome", json={"outcome_tag": "DEFICIENCY_CONFIRMED"})
    assert blocked.status_code == 409
    accepted = client.post(f"/cases/{case.id}/outcome", json={"outcome_tag": "DEFICIENCY_CONFIRMED", "acknowledge_conflict": True, "remarks": "Reviewed both bureau findings; proceeding with joint note."})
    assert accepted.status_code == 200
    action = db.query(models.CaseAction).filter(models.CaseAction.action_type == models.ActionType.OUTCOME_TAGGED).first()
    assert action is not None
    assert "Conflicting Outcome Warning acknowledged" in action.remarks
    app.dependency_overrides.clear()
