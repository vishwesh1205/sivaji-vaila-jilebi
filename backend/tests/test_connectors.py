from datetime import datetime

from app.connectors import CpgramsConnector, CpgramsPublicStatsConnector, CssConnector, OgdConnector


def test_css_mapping_and_date_format():
    connector = CssConnector()
    raw = {
        "ticket_no": "CSS-88231",
        "institution_name": "St Xaviers Inst of Tech",
        "grievance": "Fees charged above approved structure.",
        "grievance_category": "Fees",
        "received_date": "05/07/2026",
        "current_status": "Pending",
        "bureau_code": "RB",
        "language": "en",
        "complainant_ref": "demo-ref-1",
    }
    ticket = connector.normalize(raw)
    assert ticket.source_record_id == "CSS-88231"
    assert ticket.category == "FEE"
    assert ticket.date_received == datetime(2026, 7, 5)
    assert ticket.bureau_code == "RB"
    assert ticket.complainant_hash and len(ticket.complainant_hash) == 64
    assert ticket.complainant_hash != "demo-ref-1"


def test_cpgrams_mapping_differs_from_css():
    connector = CpgramsConnector()
    raw = {
        "registration_number": "CPGRAMS/2026/400123",
        "institution_name": "St. Xaviers Institute of Technology",
        "grievance_text": "Unauthorized intake beyond sanctioned seats.",
        "category": "Approval Violation",
        "registration_date": "2026-07-06T10:30:00",
        "current_status": "Received",
        "department": "Public Grievance Redressal Cell",
        "language": "en",
        "applicant_ref": "demo-ref-2",
    }
    ticket = connector.normalize(raw)
    assert ticket.source_record_id == "CPGRAMS/2026/400123"
    assert ticket.category == "APPROVAL_VIOLATION"
    assert ticket.date_received == datetime(2026, 7, 6, 10, 30)
    assert ticket.bureau_code == "PGRC"
    assert ticket.source_name == "cpgrams"


def test_public_connectors_fallback_to_labelled_snapshot(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "cpgrams_public_stats_url", "")
    rows = CpgramsPublicStatsConnector().fetch()
    assert rows
    assert all(row["__snapshot"] is True for row in rows)

    monkeypatch.setattr(settings, "ogd_resource_ids", "")
    ogd = OgdConnector().fetch()
    assert ogd
    assert all(row["__snapshot"] is True for row in ogd)


def test_file_adapter_resolves_sample_data(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "source_mode_css", "file")
    monkeypatch.setattr(settings, "css_file_path", "sample_data/css_tickets.csv")
    rows = CssConnector().fetch()
    assert rows
    ticket = CssConnector().normalize(rows[0])
    assert ticket.source_record_id
