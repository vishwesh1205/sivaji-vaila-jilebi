from app import models
from app.connectors import CssConnector
from app.services.ingestion import SyncService, ensure_data_sources


def test_idempotent_resync(db, base_data, monkeypatch):
    ensure_data_sources(db)
    raw = {
        "ticket_no": "CSS-TEST-1",
        "institution_name": "St Xaviers Inst of Tech",
        "grievance": "Excessive fee charged beyond the approved structure.",
        "grievance_category": "FEE",
        "received_date": "05/07/2026",
        "current_status": "Pending",
        "bureau_code": "RB",
        "language": "en",
        "complainant_ref": "dedupe-ref",
    }
    css = CssConnector()

    class FakeConnector:
        def fetch(self, since=None):
            return [raw]

        def normalize(self, item):
            return css.normalize(item)

    import app.services.ingestion as ingestion

    monkeypatch.setattr(ingestion, "get_connector", lambda name: FakeConnector())
    first = SyncService(db).sync("css")
    second = SyncService(db).sync("css")
    assert first.created == 1
    assert second.created == 0
    assert second.duplicates_skipped == 1
    assert db.query(models.Case).filter(models.Case.source_record_id == "CSS-TEST-1").count() == 1


def test_raw_payload_retained(db, base_data, monkeypatch):
    ensure_data_sources(db)
    raw = {
        "ticket_no": "CSS-RAW-1", "institution_name": "St Xaviers Inst of Tech",
        "grievance": "Excessive fee", "grievance_category": "FEE", "received_date": "05/07/2026",
        "current_status": "Pending", "bureau_code": "RB", "language": "en", "complainant_ref": "raw-ref",
    }
    css = CssConnector()
    class FakeConnector:
        def fetch(self, since=None): return [raw]
        def normalize(self, item): return css.normalize(item)
    import app.services.ingestion as ingestion
    monkeypatch.setattr(ingestion, "get_connector", lambda name: FakeConnector())
    SyncService(db).sync("css")
    payload = db.query(models.RawPayload).first()
    assert payload is not None
    assert len(payload.payload_sha256) == 64
    assert payload.payload_json["ticket_no"] == "CSS-RAW-1"
