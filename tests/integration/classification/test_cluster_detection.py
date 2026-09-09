from pathlib import Path

import pytest

from openinsider_tracker.cli.main import main
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
    main(
        [
            "ingest",
            "--source",
            "sec_edgar",
            "--fixture",
            str(FIXTURES / fixture_name),
        ]
    )


def test_two_filers_below_individual_threshold_form_a_notable_cluster(db_env, capsys):
    _ingest("sample_form4_cluster_filer_a.xml")
    _ingest("sample_form4_cluster_filer_b.xml")
    capsys.readouterr()

    main(["classify"])
    capsys.readouterr()

    db = Database(str(db_env))
    listing = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["is_notable"] is True
    assert item["amount"] == 110000.0  # $30,000 + $80,000, neither notable alone
    assert item["event_date"] == "2026-08-04"  # window_end

    # Re-running classify on unchanged data must not create a duplicate.
    main(["classify"])
    capsys.readouterr()
    listing_again = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert listing_again["total"] == 1
    assert listing_again["items"][0]["id"] == item["id"]


def test_buyback_and_routine_transaction_never_join_a_cluster(db_env, capsys):
    _ingest("sample_form4_cluster_filer_a.xml")
    _ingest("sample_8k_buyback_100m.xml")
    _ingest("sample_form4_routine_10b5-1.xml")
    capsys.readouterr()

    main(["classify"])
    capsys.readouterr()

    db = Database(str(db_env))
    listing = query_signals(db, signal_type="cluster_buy", notable_only=False)
    # Only one discretionary buy exists (filer_a); the buyback and the routine
    # sale must never count toward a cluster, so no cluster forms at all.
    assert listing["total"] == 0


def test_raising_min_filer_count_makes_cluster_not_notable_and_lowering_restores_it(
    db_env, capsys
):
    _ingest("sample_form4_cluster_filer_a.xml")
    _ingest("sample_form4_cluster_filer_b.xml")
    capsys.readouterr()
    main(["classify"])
    capsys.readouterr()

    db = Database(str(db_env))
    before = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert before["total"] == 1

    main(["thresholds", "set", "--min-cluster-filer-count", "3"])
    capsys.readouterr()
    main(["classify", "--reclassify"])
    capsys.readouterr()

    after_raise = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert after_raise["total"] == 0

    main(["thresholds", "set", "--min-cluster-filer-count", "2"])
    capsys.readouterr()
    main(["classify", "--reclassify"])
    capsys.readouterr()

    after_lower = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert after_lower["total"] == 1


def test_narrowing_window_splits_an_already_sent_cluster_without_erasing_its_history(
    db_env, capsys
):
    from openinsider_tracker.config import load_config
    from openinsider_tracker.notifications.orchestrator import run_notify

    _ingest("sample_form4_cluster_filer_a.xml")  # 2026-08-01
    _ingest("sample_form4_cluster_filer_b.xml")  # 2026-08-04
    _ingest("sample_form4_cluster_filer_c.xml")  # 2026-08-11
    capsys.readouterr()
    main(["classify"])  # default window=14 -> all three group together
    capsys.readouterr()

    db = Database(str(db_env))
    before = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert before["total"] == 1
    original = before["items"][0]
    assert original["amount"] == 200000.0  # 30,000 + 80,000 + 90,000

    config = load_config()
    run_notify(db, config, send_email_fn=lambda config, **kw: None)
    sent_state = query_signals(db, signal_type="cluster_buy", notable_only=True)
    assert sent_state["items"][0]["notification_status"] == "sent"

    # Narrow the window (splits [a,b,c] into [a,b] + lone c) AND raise the
    # minimum filer count to 3, so the majority piece [a,b] (2 filers) now
    # falls below the new minimum -- but its notification_status must NOT be
    # erased, since it was already delivered (research.md §5).
    main(["thresholds", "set", "--cluster-window-days", "5", "--min-cluster-filer-count", "3"])
    capsys.readouterr()
    main(["classify", "--reclassify"])
    capsys.readouterr()

    after = query_signals(db, signal_type="cluster_buy", notable_only=False)
    matching = [item for item in after["items"] if item["id"] == original["id"]]
    assert len(matching) == 1
    assert matching[0]["is_notable"] is False  # [a,b] = 2 filers, now below min of 3
    assert matching[0]["notification_status"] == "sent"  # history preserved, not reset
