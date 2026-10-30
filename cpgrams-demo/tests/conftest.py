from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CPGRAMS_DB_PATH", str(tmp_path / "demo.db"))
    monkeypatch.setenv("CPGRAMS_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("CPGRAMS_SESSION_SECRET", "test-secret")
    monkeypatch.delenv("DASHBOARD_INGEST_URL", raising=False)
    monkeypatch.delenv("DASHBOARD_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("CPGRAMS_ALLOW_RESET", raising=False)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
