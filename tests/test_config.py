import os
import json
import tempfile
import pytest

from fordlogger.config import load_config, INTERVALS, DEFAULT_CONFIG


def test_load_config_valid(tmp_path, monkeypatch):
    monkeypatch.delenv("FORDLOGGER_DB_HOST", raising=False)
    monkeypatch.delenv("FORDLOGGER_DB_PORT", raising=False)
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "client_id": "test-id",
        "client_secret": "test-secret",
    }))
    cfg = load_config(str(cfg_file))
    assert cfg["client_id"] == "test-id"
    assert cfg["client_secret"] == "test-secret"
    # Defaults should be merged
    assert cfg["db_host"] == "db"
    assert cfg["db_port"] == 5432


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.json")


def test_load_config_missing_credentials(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"client_id": "", "client_secret": ""}))
    with pytest.raises(ValueError, match="client_id"):
        load_config(str(cfg_file))


def test_env_override(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "client_id": "test-id",
        "client_secret": "test-secret",
    }))
    os.environ["FORDLOGGER_DB_HOST"] = "myhost"
    os.environ["FORDLOGGER_DB_PORT"] = "9999"
    try:
        cfg = load_config(str(cfg_file))
        assert cfg["db_host"] == "myhost"
        assert cfg["db_port"] == 9999
    finally:
        os.environ["FORDLOGGER_DB_HOST"] = "localhost"
        os.environ.pop("FORDLOGGER_DB_PORT", None)


def test_intervals_defined():
    assert set(INTERVALS.keys()) == {"driving", "charging", "parked", "sleeping"}
    assert INTERVALS["driving"] <= INTERVALS["charging"] <= INTERVALS["parked"] <= INTERVALS["sleeping"]
