from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import models
from app.connectors.institution_master import InstitutionMasterImporter
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.scheduler import escalate_overlaps
from app.services.evaluation import evaluate_resolution


def _client(db, user):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_resolution_benchmark_is_deterministic_and_measured(db, base_data):
    first = evaluate_resolution(db)
    second = evaluate_resolution(db)
    assert first["sample_size"] == 240
    assert first["seed"] == second["seed"]
    assert first["true_positive"] == second["true_positive"]
    assert first["precision"] == second["precision"]
    assert first["recall"] == second["recall"]
    assert 0.0 <= first["precision"] <= 1.0
    assert 0.0 <= first["recall"] <= 1.0
    assert first["f1"] > 0.5
    assert first["generated_at"]


def test_overlap_escalation_notifies_management_once(db, base_data):
    management = models.User(name="Management", email="mgmt@test.gov.in", password_hash="x", role=models.UserRole.MANAGEMENT, is_active=True)
    officer = models.User(name="Officer", email="officer@test.gov.in", password_hash="x", role=models.UserRole.PGRC_OFFICER, is_active=True)
    db.add_all([management, officer])
    db.commit()
    old = datetime.utcnow() - timedelta(days=5)
    alert = models.OverlapAlert(
        institution_id=base_data["inst"].id,
        case_ids=[],
        bureaus_involved=["PGRC", "RB"],
        status=models.AlertStatus.OPEN,
        why_flagged="Unacknowledged cross-bureau overlap",
        created_at=old,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    now = datetime.utcnow()
    assert escalate_overlaps(db, now=now) == 1
    db.refresh(alert)
    assert alert.escalated_at is not None
    notifications = db.query(models.Notification).all()
    assert {n.user_id for n in notifications} == {base_data["user"].id, management.id}
    assert all(n.type == models.NotificationType.ESCALATION for n in notifications)
    assert all(n.payload.get("kind") == "overlap_escalation" for n in notifications)
    assert escalate_overlaps(db, now=now + timedelta(days=1)) == 0
    assert db.query(models.Notification).count() == len(notifications)


def test_institution_master_imports_first_grc_resolution_and_handles_unknown(db, base_data):
    importer = InstitutionMasterImporter(db)
    content = (
        "AICTE Permanent ID,Institute Name,Address,City,State,Region,First Resolution at Institution GRC (Days)\n"
        "1-9000001,First Resolution College,1 Main Road,Pune,Maharashtra,Pune,14\n"
        "1-9000002,Unknown Resolution College,2 Main Road,Pune,Maharashtra,Pune,unknown\n"
    ).encode()
    result = importer.import_bytes(content, "master.csv")
    assert result["created"] == 2
    known = db.query(models.Institution).filter_by(aicte_permanent_id="1-9000001").one()
    unknown = db.query(models.Institution).filter_by(aicte_permanent_id="1-9000002").one()
    assert known.grc_first_resolution_days == 14
    assert unknown.grc_first_resolution_days is None

    client = _client(db, base_data["user"])
    detail = client.get(f"/institutions/{unknown.id}/360").json()
    assert detail["institution"]["grc_first_resolution_days"] is None
    app.dependency_overrides.clear()


def test_overlap_xlsx_export_handles_list_columns(db, base_data):
    client = _client(db, base_data["user"])
    alert = models.OverlapAlert(
        institution_id=base_data["inst"].id,
        case_ids=[],
        bureaus_involved=["PGRC", "RB"],
        status=models.AlertStatus.OPEN,
        why_flagged="Export serialization check",
    )
    db.add(alert)
    db.commit()
    response = client.get("/reports/overlaps", params={"format": "xlsx"})
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    app.dependency_overrides.clear()
