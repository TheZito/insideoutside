import json
from pathlib import Path

import pytest

from openinsider_tracker.cli.main import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def seeded_and_classified(tmp_path, monkeypatch, capsys):
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
    capsys.readouterr()


def test_notify_sends_one_email_per_pending_signal_and_marks_sent(
    seeded_and_classified, capsys, monkeypatch
):
    sent_messages = []

    def fake_send_email(config, *, to, subject, body):
        sent_messages.append((to, subject, body))

    import openinsider_tracker.cli.commands.notify as notify_module
    from openinsider_tracker.notifications.orchestrator import run_notify

    monkeypatch.setattr(
        notify_module,
        "_run_notify_orchestrator",
        lambda db, config: run_notify(db, config, send_email_fn=fake_send_email),
    )

    exit_code = main(["notify"])
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["sent"] == 1
    assert summary["failed"] == 0
    assert len(sent_messages) == 1

    # Re-running notify sends no duplicate for the same signal.
    exit_code = main(["notify"])
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["sent"] == 0
    assert len(sent_messages) == 1
