import json
from pathlib import Path

import pytest

from insideoutside.cli.main import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    main(["migrate"])
    return db_path


def test_ingest_form4_fixture_produces_json_summary_and_persists(db_env, capsys):
    exit_code = main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_form4_large_buy.xml"),
        ]
    )
    assert exit_code == 0

    output = capsys.readouterr().out.strip().splitlines()
    summary = json.loads(output[-1])
    assert summary["source"] == "sec_edgar"
    assert summary["new"] == 1
    assert summary["failed"] == 0


def test_ingest_buyback_fixture_produces_json_summary_and_persists(db_env, capsys):
    exit_code = main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_8k_buyback_100m.xml"),
        ]
    )
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["new"] == 1
    assert summary["failed"] == 0
