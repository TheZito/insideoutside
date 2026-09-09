from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openinsider_tracker.cli.main import main
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.migrations import apply_migrations
from openinsider_tracker.web.app import create_app

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    apply_migrations(str(db_path))
    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_form4_large_buy.xml"),
        ]
    )
    main(["classify"])

    db = Database(str(db_path))
    return TestClient(create_app(db))


def test_signal_detail_includes_full_record_and_provenance(client):
    listing = client.get("/api/signals").json()
    signal_id = listing["items"][0]["id"]

    response = client.get(f"/api/signals/{signal_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == signal_id
    assert body["is_superseded"] is False
    assert body["record"]["source"] == "sec_edgar"
    assert body["record"]["source_ref"]
    assert body["record"]["fetched_at"]


def test_signal_detail_404_when_not_found(client):
    response = client.get("/api/signals/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
