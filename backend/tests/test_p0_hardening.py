from fastapi.testclient import TestClient

from app import models
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from seed.seed_data import backfill_hero_case_details


def _client(db, user):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_hero_backfill_adds_realistic_detail_without_overwriting(db, base_data):
    case = base_data["make_case"]("PG-2026-4471", base_data["pgrc"], models.SourceChannel.CPGRAMS)
    case.subject = None
    case.category_subtype = None
    case.complainant_type = None
    db.commit()

    backfill_hero_case_details(db)
    db.refresh(case)
    assert case.subject == "Excess semester fee charged beyond the approved structure"
    assert case.category_subtype == "EXCESS_FEE"
    assert case.complainant_type == "STUDENT"

    case.subject = "Officer-edited subject"
    db.commit()
    backfill_hero_case_details(db)
    db.refresh(case)
    assert case.subject == "Officer-edited subject"


def test_case_pagination_and_coordination_thread(db, base_data):
    user = base_data["user"]
    client = _client(db, user)

    for idx in range(55):
        base_data["make_case"](f"PAGE-{idx:04d}", base_data["pgrc"], models.SourceChannel.CSS)

    page_one = client.get("/cases", params={"page": 1, "limit": 50}).json()
    page_two = client.get("/cases", params={"page": 2, "limit": 50}).json()
    assert page_one["total"] == 55
    assert len(page_one["items"]) == 50
    assert len(page_two["items"]) == 5
    assert page_one["page"] == 1 and page_two["page"] == 2

    alert = models.OverlapAlert(
        institution_id=base_data["inst"].id,
        case_ids=[page_one["items"][0]["id"], page_one["items"][1]["id"]],
        bureaus_involved=["PGRC", "RB"],
        status=models.AlertStatus.OPEN,
        why_flagged="Shared fee narrative",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    empty = client.post(f"/overlaps/{alert.id}/thread", json={"message": "   "})
    assert empty.status_code == 400
    posted = client.post(f"/overlaps/{alert.id}/thread", json={"message": "PGRC has requested the fee ledger."})
    assert posted.status_code == 200
    thread = client.get(f"/overlaps/{alert.id}/thread").json()
    assert thread[0]["message"] == "PGRC has requested the fee ledger."
    assert thread[0]["author"] == user.name

    app.dependency_overrides.clear()
