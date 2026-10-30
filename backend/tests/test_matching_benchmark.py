import csv
import json

import pytest
from fastapi.testclient import TestClient

from app import models
from app.benchmarks.runner import write_csv
from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.services.matching_benchmark import (
    evaluate_matching_benchmark,
    load_dataset,
    split_dataset,
)


@pytest.fixture(scope="module")
def report():
    return evaluate_matching_benchmark()


def _client(db, user):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_dataset_is_versioned_synthetic_and_grouped():
    dataset = load_dataset()
    assert dataset["version"] == "1.0.0"
    assert dataset["provenance"]["kind"] == "SYNTHETIC"
    assert dataset["provenance"]["human_annotation"] is False
    assert dataset["counts"]["pairs"] == 240
    assert dataset["counts"]["labels"] == {"DUPLICATE": 120, "RELATED": 60, "UNRELATED": 60}
    assert all(pair["annotator_labels"] for pair in dataset["pairs"])
    assert all(pair["adjudicated_label"] in {"DUPLICATE", "RELATED", "UNRELATED"} for pair in dataset["pairs"])


def test_split_is_deterministic_and_keeps_source_groups_together():
    dataset = load_dataset()
    first_dev, first_test, first_split = split_dataset(dataset, seed=20261025)
    second_dev, second_test, second_split = split_dataset(dataset, seed=20261025)
    assert [p["pair_id"] for p in first_dev] == [p["pair_id"] for p in second_dev]
    assert [p["pair_id"] for p in first_test] == [p["pair_id"] for p in second_test]
    assert first_split["source_group_overlap"] is False
    assert second_split["source_group_overlap"] is False
    assert {p["source_group_id"] for p in first_dev}.isdisjoint({p["source_group_id"] for p in first_test})


def test_report_has_five_methods_metrics_language_groups_and_ablation(report):
    assert len(report["methods"]) == 5
    assert {method["id"] for method in report["methods"]} == {
        "lexical_jaccard",
        "tfidf_word",
        "tfidf_char",
        "fuzzy_token_set",
        "hybrid_lexical",
    }
    for method in report["methods"]:
        assert method["available"] is True
        assert 0.0 <= method["test"]["binary"]["precision"] <= 1.0
        assert 0.0 <= method["test"]["binary"]["recall"] <= 1.0
        assert 0.0 <= method["test"]["binary"]["f1"] <= 1.0
        assert 0.0 <= method["test"]["three_class"]["macro_f1"] <= 1.0
        assert set(method["test"]["three_class"]["per_class"]) == {"DUPLICATE", "RELATED", "UNRELATED"}
        assert method["test"]["three_class"]["confusion_matrix"]["labels"] == ["DUPLICATE", "RELATED", "UNRELATED"]
        assert method["test"]["by_language"]
        assert method["thresholds"]["development_binary_f1"] >= 0.0
    assert report["ablation"]
    assert report["split"]["source_group_overlap"] is False
    assert report["dataset"]["provenance"]["human_annotation"] is False


def test_semantic_method_is_reported_unavailable_without_fabricated_scores(report):
    unavailable = report["unavailable_methods"]
    assert len(unavailable) == 1
    assert unavailable[0]["id"] == "multilingual_embedding"
    assert unavailable[0]["available"] is False
    assert unavailable[0]["metrics"] is None
    assert "not installed" in unavailable[0]["reason"] or "not configured" in unavailable[0]["reason"]


def test_matching_evaluation_api_and_csv_export(report, db, base_data, tmp_path):
    client = _client(db, base_data["user"])
    try:
        response = client.get("/matching/evaluation")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["methods"]) == 5
        assert payload["dataset"]["version"] == "1.0.0"
    finally:
        app.dependency_overrides.clear()

    output = tmp_path / "matching.csv"
    write_csv(report, output)
    with output.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["kind"] for row in rows} == {"method", "unavailable", "ablation"}
    assert any(row["id"] == "hybrid_lexical" for row in rows)
    json.dumps(report)
