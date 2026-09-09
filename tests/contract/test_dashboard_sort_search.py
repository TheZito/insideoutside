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
    return TestClient(create_app(db))


def test_dashboard_has_sortable_headers_for_date_type_company_amount(client):
    html = client.get("/").text
    for key in ("date", "type", "company", "amount"):
        assert f'data-key="{key}"' in html
    assert 'class="sortable"' in html or "class=\"sortable\"" in html


def test_dashboard_rows_carry_sort_and_search_data_attributes(client):
    html = client.get("/").text
    assert 'data-date="2026-08-01"' in html
    assert 'data-company="toyota motor corp"' in html
    assert 'data-amount="150250.0"' in html
    assert 'data-search="toyota motor corp tm' in html.lower()


def test_dashboard_has_a_search_input(client):
    html = client.get("/").text
    assert 'id="search-box"' in html
