import json

import pytest

from openinsider_tracker.cli.main import main


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    main(["migrate"])
    return db_path


def test_thresholds_show_returns_defaults(db_env, capsys):
    exit_code = main(["thresholds", "show"])
    assert exit_code == 0
    body = json.loads(capsys.readouterr().out.strip())
    assert body["min_insider_buy_value"] == "1000000"
    assert body["min_notable_role_buy_value"] == "100000"
    assert body["cluster_window_days"] == 14
    assert body["min_cluster_filer_count"] == 2


def test_thresholds_set_updates_and_persists(db_env, capsys):
    exit_code = main(["thresholds", "set", "--min-insider-buy-value", "250000"])
    assert exit_code == 0
    body = json.loads(capsys.readouterr().out.strip())
    assert body["min_insider_buy_value"] == "250000"

    main(["thresholds", "show"])
    follow_up = json.loads(capsys.readouterr().out.strip())
    assert follow_up["min_insider_buy_value"] == "250000"


def test_thresholds_set_updates_role_specific_value(db_env, capsys):
    exit_code = main(["thresholds", "set", "--min-notable-role-buy-value", "150000"])
    assert exit_code == 0
    body = json.loads(capsys.readouterr().out.strip())
    assert body["min_notable_role_buy_value"] == "150000"


def test_thresholds_set_updates_cluster_window_days(db_env, capsys):
    exit_code = main(["thresholds", "set", "--cluster-window-days", "10"])
    assert exit_code == 0
    body = json.loads(capsys.readouterr().out.strip())
    assert body["cluster_window_days"] == 10


def test_thresholds_set_updates_min_cluster_filer_count(db_env, capsys):
    exit_code = main(["thresholds", "set", "--min-cluster-filer-count", "3"])
    assert exit_code == 0
    body = json.loads(capsys.readouterr().out.strip())
    assert body["min_cluster_filer_count"] == 3
