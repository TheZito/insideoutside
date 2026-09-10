import pytest
from fastapi.testclient import TestClient

from insideoutside.storage.db import Database
from insideoutside.storage.migrations import apply_migrations
from insideoutside.web.app import create_app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    apply_migrations(str(db_path))
    db = Database(str(db_path))
    return TestClient(create_app(db))


def test_get_thresholds_returns_defaults(client):
    response = client.get("/api/thresholds")
    assert response.status_code == 200
    body = response.json()
    assert body["min_insider_buy_value"] == 1000000.0
    assert body["min_notable_role_buy_value"] == 100000.0
    assert body["min_buyback_amount"] == 50000000.0
    assert set(body["notable_filer_roles"]) == {"officer", "director"}
    assert body["cluster_window_days"] == 14
    assert body["min_cluster_filer_count"] == 2


def test_put_thresholds_round_trips(client):
    response = client.put(
        "/api/thresholds",
        json={
            "min_insider_buy_value": 500000,
            "min_notable_role_buy_value": 150000,
            "notable_filer_roles": ["director"],
            "min_buyback_amount": 25000000,
            "cluster_window_days": 10,
            "min_cluster_filer_count": 3,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["min_insider_buy_value"] == 500000.0
    assert body["min_notable_role_buy_value"] == 150000.0
    assert body["notable_filer_roles"] == ["director"]
    assert body["cluster_window_days"] == 10
    assert body["min_cluster_filer_count"] == 3

    follow_up = client.get("/api/thresholds").json()
    assert follow_up["min_insider_buy_value"] == 500000.0
    assert follow_up["min_notable_role_buy_value"] == 150000.0
    assert follow_up["cluster_window_days"] == 10
    assert follow_up["min_cluster_filer_count"] == 3


def test_put_thresholds_rejects_negative_amount(client):
    response = client.put(
        "/api/thresholds",
        json={
            "min_insider_buy_value": -1,
            "min_notable_role_buy_value": 100000,
            "notable_filer_roles": ["director"],
            "min_buyback_amount": 25000000,
            "cluster_window_days": 14,
            "min_cluster_filer_count": 2,
        },
    )
    assert response.status_code == 422


def test_put_thresholds_rejects_negative_role_amount(client):
    response = client.put(
        "/api/thresholds",
        json={
            "min_insider_buy_value": 1000000,
            "min_notable_role_buy_value": -1,
            "notable_filer_roles": ["director"],
            "min_buyback_amount": 25000000,
            "cluster_window_days": 14,
            "min_cluster_filer_count": 2,
        },
    )
    assert response.status_code == 422


def test_put_thresholds_rejects_zero_cluster_window_days(client):
    response = client.put(
        "/api/thresholds",
        json={
            "min_insider_buy_value": 1000000,
            "min_notable_role_buy_value": 100000,
            "notable_filer_roles": ["director"],
            "min_buyback_amount": 25000000,
            "cluster_window_days": 0,
            "min_cluster_filer_count": 2,
        },
    )
    assert response.status_code == 422


def test_put_thresholds_rejects_min_cluster_filer_count_below_two(client):
    response = client.put(
        "/api/thresholds",
        json={
            "min_insider_buy_value": 1000000,
            "min_notable_role_buy_value": 100000,
            "notable_filer_roles": ["director"],
            "min_buyback_amount": 25000000,
            "cluster_window_days": 14,
            "min_cluster_filer_count": 1,
        },
    )
    assert response.status_code == 422
