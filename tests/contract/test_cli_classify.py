import json
from pathlib import Path

import pytest

from openinsider_tracker.cli.main import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def seeded_db(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    main(["migrate"])
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
    capsys.readouterr()
    return db_path


def test_classify_marks_notable_vs_routine_per_default_thresholds(seeded_db, capsys):
    exit_code = main(["classify"])
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["evaluated"] == 2
    assert summary["notable"] == 1


def test_classify_summary_includes_cluster_counts(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    main(["migrate"])
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
    capsys.readouterr()

    exit_code = main(["classify"])
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["clusters_detected"] == 1
    assert summary["clusters_notable"] == 1
