from pathlib import Path

import pytest

from openinsider_tracker.cli.main import main
from openinsider_tracker.config import load_config
from openinsider_tracker.notifications.orchestrator import run_notify
from openinsider_tracker.storage.db import Database
from openinsider_tracker.web.routes.signals import query_signals

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def db_env(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    main(["migrate"])
    capsys.readouterr()
    return db_path


def _ingest(fixture_name: str):
    main(["ingest", "--source", "sec_edgar", "--fixture", str(FIXTURES / fixture_name)])


def test_cluster_that_grows_after_being_sent_does_not_get_a_second_email(db_env, capsys):
    _ingest("sample_form4_cluster_filer_a.xml")
    _ingest("sample_form4_cluster_filer_b.xml")
    capsys.readouterr()
    main(["classify"])
    capsys.readouterr()

    db = Database(str(db_env))
    config = load_config()
    sent_emails = []
    summary = run_notify(
        db, config, send_email_fn=lambda config, **kw: sent_emails.append(kw)
    )
    assert summary["sent"] == 1
    assert len(sent_emails) == 1

    before = query_signals(db, signal_type="cluster_buy", notable_only=False)
    original_signal_id = before["items"][0]["id"]
    assert before["items"][0]["notification_status"] == "sent"

    # A third filer joins the same cluster's window.
    _ingest("sample_form4_cluster_filer_c.xml")
    capsys.readouterr()
    main(["classify"])
    capsys.readouterr()

    after = query_signals(db, signal_type="cluster_buy", notable_only=False)
    assert after["total"] == 1  # still the SAME cluster signal, not a duplicate
    assert after["items"][0]["id"] == original_signal_id

    summary2 = run_notify(
        db, config, send_email_fn=lambda config, **kw: sent_emails.append(kw)
    )
    assert summary2["sent"] == 0  # no second email for the same, already-sent cluster
    assert len(sent_emails) == 1
