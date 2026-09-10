from pathlib import Path

import pytest

from insideoutside.cli.main import main
from insideoutside.config import load_config
from insideoutside.notifications.mailer import EmailSendError
from insideoutside.notifications.orchestrator import run_notify
from insideoutside.storage.db import Database
from insideoutside.web.routes.signals import query_signals

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
    main(["classify"])
    return db_path


def test_smtp_failure_marks_failed_but_signal_stays_visible(seeded_db):
    def failing_send_email(config, *, to, subject, body):
        raise EmailSendError("smtp relay unreachable")

    db = Database(str(seeded_db))
    config = load_config()

    summary = run_notify(db, config, send_email_fn=failing_send_email)
    assert summary["sent"] == 0
    assert summary["failed"] == 1

    listing = query_signals(db, notable_only=True)
    assert listing["total"] == 1
    assert listing["items"][0]["notification_status"] == "failed"
