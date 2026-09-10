from pathlib import Path

import pytest

from insideoutside.cli.main import main
from insideoutside.storage.db import Database
from insideoutside.web.routes.signals import query_signals

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


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
            str(FIXTURES / "sample_form4_routine_10b5-1.xml"),
        ]
    )
    capsys.readouterr()
    return db_path


def test_lowering_threshold_and_reclassifying_surfaces_previously_excluded_signal(
    seeded_db, capsys
):
    # The routine fixture is a $29,600 SALE by an officer -- never notable
    # regardless of threshold (sells are excluded per classification rules), so
    # use a small discretionary buy instead by re-ingesting the large-buy fixture
    # with a threshold high enough to exclude it, then lowering it.
    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / "sample_form4_large_buy.xml"),
        ]
    )
    capsys.readouterr()

    main(["thresholds", "set", "--min-insider-buy-value", "999999999", "--notable-filer-roles", ""])
    capsys.readouterr()
    main(["classify"])
    capsys.readouterr()

    db = Database(str(seeded_db))
    before = query_signals(db, notable_only=True)
    assert before["total"] == 0

    main(["thresholds", "set", "--min-insider-buy-value", "1000"])
    capsys.readouterr()
    main(["classify", "--reclassify"])
    capsys.readouterr()

    after = query_signals(db, notable_only=True)
    assert after["total"] == 1
