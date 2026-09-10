from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insideoutside.cli.main import main
from insideoutside.storage.db import Database
from insideoutside.storage.migrations import apply_migrations
from insideoutside.web.app import create_app

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
    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_form4_routine_10b5-1.xml"),
        ]
    )
    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_8k_buyback_100m.xml"),
        ]
    )
    main(["classify"])

    db = Database(str(db_path))
    app = create_app(db)
    return TestClient(app)


def test_default_view_returns_only_notable_signals_most_recent_first(client):
    response = client.get("/api/signals")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["signal_type"] for item in body["items"]} == {"insider_transaction", "buyback"}
    for item in body["items"]:
        assert item["is_notable"] is True


def test_routine_transaction_excluded_from_default_view(client):
    response = client.get("/api/signals")
    body = response.json()
    summaries = [item["summary"] for item in body["items"]]
    assert not any("John Smith" in s for s in summaries)


def test_notable_only_false_includes_routine_transaction(client):
    response = client.get("/api/signals", params={"notable_only": False})
    body = response.json()
    assert body["total"] == 3


def test_filter_by_signal_type(client):
    response = client.get("/api/signals", params={"signal_type": "buyback"})
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["signal_type"] == "buyback"


def test_response_includes_is_discretionary_field(client):
    response = client.get("/api/signals")
    body = response.json()
    insider_item = next(i for i in body["items"] if i["signal_type"] == "insider_transaction")
    assert insider_item["is_discretionary"] is True
    buyback_item = next(i for i in body["items"] if i["signal_type"] == "buyback")
    assert buyback_item["is_discretionary"] is None


@pytest.fixture
def cluster_client(tmp_path, monkeypatch):
    db_path = tmp_path / "cluster_test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    apply_migrations(str(db_path))

    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_form4_cluster_filer_a.xml"),
        ]
    )
    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_form4_cluster_filer_b.xml"),
        ]
    )
    main(["classify"])

    db = Database(str(db_path))
    return TestClient(create_app(db))


def test_cluster_buy_signal_shape_per_contract(cluster_client):
    response = cluster_client.get("/api/signals", params={"signal_type": "cluster_buy"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["signal_type"] == "cluster_buy"
    assert item["is_notable"] is True
    assert item["is_discretionary"] is None
    assert item["source_url"] is None
    assert item["event_date"] == "2026-08-04"  # window_end
    assert item["amount"] == 110000.0
    assert "2" in item["summary"] or "two" in item["summary"].lower()
