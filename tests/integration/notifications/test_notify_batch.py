from pathlib import Path

import pytest

from insideoutside.cli.main import main
from insideoutside.config import load_config
from insideoutside.notifications.orchestrator import run_notify
from insideoutside.storage.db import Database

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
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
            str(FIXTURES / "sample_8k_buyback_100m.xml"),
        ]
    )
    main(["classify"])
    return db_path


def test_multiple_notable_signals_each_get_one_correctly_addressed_email(seeded_db):
    sent = []

    def fake_send_email(config, *, to, subject, body):
        sent.append({"to": to, "subject": subject, "body": body})

    db = Database(str(seeded_db))
    config = load_config()

    summary = run_notify(db, config, send_email_fn=fake_send_email)
    assert summary["sent"] == 2
    assert summary["failed"] == 0
    assert len(sent) == 2
    assert all(message["to"] == config.notify_email_to for message in sent)

    subjects = " ".join(m["subject"] for m in sent)
    assert "insider buy" in subjects
    assert "buyback" in subjects
