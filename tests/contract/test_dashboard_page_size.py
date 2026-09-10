import re
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


def test_dashboard_has_a_page_size_control_with_the_documented_options(client):
    html = client.get("/").text
    assert 'id="page-size-select"' in html
    for value in ("10", "25", "50", "infinite"):
        assert f'value="{value}"' in html


def test_dashboard_renders_all_notable_signals_regardless_of_page_size(client):
    html = client.get("/").text
    total = int(re.search(r'id="visible-count">(\d+)<', html).group(1))
    row_count = html.count("data-search=")
    assert total == row_count
    assert row_count >= 2
