from datetime import datetime

from sqlalchemy import select

from app import models
from app.routers.ingest import IngestJSON, ingest_json


def test_json_ingest_preserves_demo_provenance(db, base_data):
    body = IngestJSON(
        items=[
            {
                "case_id": "CPGRAMS-DEMO-2026-00099",
                "source_channel": "CPGRAMS",
                "raw_institution_text": "Municipal Administration / Karnataka",
                "subject": "Fictional streetlight repair request",
                "category": "OTHER",
                "narrative": "This is a fictional demonstration complaint.",
                "date_received": datetime.utcnow().isoformat(),
                "idempotency_key": "cpgrams-demo:CPGRAMS-DEMO-2026-00099",
                "source_name": "CPGRAMS Simulator",
                "source_record_id": "CPGRAMS-DEMO-2026-00099",
                "source_type": "SIMULATOR",
                "is_synthetic": True,
                "language": "en",
            }
        ]
    )

    result = ingest_json(body=body, db=db, current=base_data["user"])

    assert result == {"created": 1, "duplicates_skipped": 0}
    case = db.scalar(select(models.Case).where(models.Case.case_id == "CPGRAMS-DEMO-2026-00099"))
    assert case is not None
    assert case.source_name == "CPGRAMS Simulator"
    assert case.source_type == "SIMULATOR"
    assert case.is_synthetic is True
    assert case.subject == "Fictional streetlight repair request"
    assert case.source_record_id == "CPGRAMS-DEMO-2026-00099"
    assert case.raw_payload_id is not None
    assert case.last_action_text == "Case created via JSON import from CPGRAMS Simulator"

    raw = db.get(models.RawPayload, case.raw_payload_id)
    assert raw is not None
    assert raw.source == "CPGRAMS Simulator"
    assert raw.source_type == "SIMULATOR"
    assert raw.payload_json["case_id"] == "CPGRAMS-DEMO-2026-00099"


def test_json_ingest_duplicate_is_skipped(db, base_data):
    payload = {
        "case_id": "CPGRAMS-DEMO-2026-00100",
        "source_channel": "CPGRAMS",
        "raw_institution_text": "Demo Department",
        "category": "OTHER",
        "narrative": "This is a fictional demonstration complaint.",
        "date_received": datetime.utcnow().isoformat(),
        "idempotency_key": "cpgrams-demo:CPGRAMS-DEMO-2026-00100",
        "source_name": "CPGRAMS Simulator",
        "source_type": "SIMULATOR",
        "is_synthetic": True,
    }
    first = ingest_json(body=IngestJSON(items=[payload]), db=db, current=base_data["user"])
    second = ingest_json(body=IngestJSON(items=[payload]), db=db, current=base_data["user"])
    assert first["created"] == 1
    assert second == {"created": 0, "duplicates_skipped": 1}
