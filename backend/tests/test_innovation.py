from datetime import datetime, timedelta

from app import models
from app.services.emerging import detect_spikes
from app.services.impact import simulate_impact
from app.services.outcome import find_conflicting_outcomes, is_contradictory
from app.services.provenance import case_lineage
from app.services.query_parser import parse_query
from app.services.risk import compute_institution_risk
from app.services.ingestion import detect_cross_channel_duplicates


def test_lineage_has_four_stages(db, base_data):
    c = base_data["make_case"]("PG-2026-0001", base_data["pgrc"], models.SourceChannel.CPGRAMS)
    lineage = case_lineage(db, c)
    assert set(lineage.keys()) >= {"stage_1_raw_payload", "stage_2_normalized", "stage_3_resolution", "stage_4_overlap"}
    assert lineage["stage_3_resolution"]["thresholds"]["auto_link"] == 0.9


def test_risk_breakdown_sums_to_score(db, base_data):
    inst = base_data["inst"]
    base_data["make_case"]("RB-2026-9001", base_data["rb"], models.SourceChannel.CSS)
    base_data["make_case"]("PG-2026-9002", base_data["pgrc"], models.SourceChannel.CPGRAMS)
    risk = compute_institution_risk(db, inst.id)
    assert round(sum(row["points"] for row in risk["breakdown"]), 2) == risk["score"]
    assert 0 <= risk["score"] <= 100


def test_conflicting_outcome_pairs_and_guard(db, base_data):
    assert is_contradictory(models.OutcomeTag.DEFICIENCY_CONFIRMED, models.OutcomeTag.NO_DEFICIENCY)
    a = base_data["make_case"]("RB-2026-9101", base_data["rb"], models.SourceChannel.CSS, tag=models.OutcomeTag.NO_DEFICIENCY)
    b = base_data["make_case"]("PG-2026-9102", base_data["pgrc"], models.SourceChannel.CPGRAMS)
    db.add(models.CaseLink(case_a_id=a.id, case_b_id=b.id, link_type=models.LinkType.MANUAL))
    db.commit()
    conflicts = find_conflicting_outcomes(db, b, models.OutcomeTag.DEFICIENCY_CONFIRMED)
    assert len(conflicts) == 1
    assert conflicts[0]["case_id"] == "RB-2026-9101"


def test_cross_channel_duplicate_detected(db, base_data):
    narrative = "Excessive fee charged beyond approved structure and no receipts were issued to students."
    a = base_data["make_case"]("CSS-2026-9201", base_data["rb"], models.SourceChannel.CSS, narrative=narrative)
    b = base_data["make_case"]("PG-2026-9202", base_data["pgrc"], models.SourceChannel.CPGRAMS, narrative=narrative)
    a.complainant_hash = "same-hash-64"
    b.complainant_hash = "same-hash-64"
    db.commit()
    links = detect_cross_channel_duplicates(db, b)
    assert links
    assert links[0].link_type == models.LinkType.CROSS_CHANNEL_DUPLICATE


def test_spike_threshold_and_minimum_count():
    assert detect_spikes(11, [2, 3, 2, 1, 2, 3, 2, 2], min_count=5, z_threshold=2.0) is not None
    assert detect_spikes(4, [2, 3, 2, 1, 2, 3, 2, 2], min_count=5, z_threshold=2.0) is None
    assert detect_spikes(6, [5, 6, 5, 6, 5, 6, 5, 6], min_count=5, z_threshold=2.0) is None


def test_nl_query_parser_sample():
    parsed = parse_query("institutions with RB and PGRC overlap in southern region older than 60 days")
    assert parsed["filters"]["bureaus"] == ["RB", "PGRC"]
    assert parsed["filters"]["overlap_only"] is True
    assert parsed["filters"]["min_age_days"] == 60
    assert "Chennai" in parsed["filters"]["regions"]
    assert parsed["chips"]
    assert "Interpreted as" in parsed["interpreted_as"]


def test_impact_simulator_deterministic(db, base_data):
    base_data["make_case"]("RB-2026-9301", base_data["rb"], models.SourceChannel.CSS, date=datetime.utcnow() - timedelta(days=200))
    base_data["make_case"]("PG-2026-9302", base_data["pgrc"], models.SourceChannel.CPGRAMS, date=datetime.utcnow() - timedelta(days=180))
    first = simulate_impact(db, discovery_delay_days=14, seed=7)
    second = simulate_impact(db, discovery_delay_days=14, seed=7)
    assert first["baseline"] == second["baseline"]
    assert first["system"] == second["system"]
    assert first["assumptions"]["note"].startswith("Model output")
