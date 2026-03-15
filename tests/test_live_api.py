"""
Live API integration tests. These call the real Ford API.
Run with: pytest tests/test_live_api.py -v
Skip with: pytest --ignore=tests/test_live_api.py

NOTE: Ford API has aggressive rate limits (~1 req/min).
These tests cache API responses to minimize calls.
"""
import os
import pytest

from fordlogger.config import load_config
from fordlogger.api import FordAPI
from fordlogger.models import Vehicle
from fordlogger import db
from fordlogger.poller import Poller

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_LIVE_TESTS", "0") == "1",
    reason="Live API tests skipped",
)


@pytest.fixture(scope="module")
def live_cfg():
    os.environ["FORDLOGGER_DB_HOST"] = "localhost"
    return load_config("config.json")


@pytest.fixture(scope="module")
def live_api(live_cfg):
    return FordAPI(live_cfg)


@pytest.fixture(scope="module")
def live_conn(live_cfg):
    c = db.connect(live_cfg)
    db.ensure_schema(c)
    return c


@pytest.fixture(scope="module")
def garage_result(live_api):
    """Cache garage result across all tests in this module."""
    return live_api.get_garage()


@pytest.fixture(scope="module")
def telemetry_result(live_api):
    """Cache telemetry result across all tests in this module."""
    return live_api.get_telemetry()


class TestLiveGarage:
    def test_get_garage(self, garage_result):
        assert len(garage_result) >= 1
        v = garage_result[0]
        assert v.vin is not None
        assert len(v.vin) == 17
        assert v.make == "Ford"

    def test_garage_has_model(self, garage_result):
        v = garage_result[0]
        assert v.model is not None


class TestLiveTelemetry:
    def test_get_telemetry(self, telemetry_result):
        assert len(telemetry_result) >= 1
        pos = telemetry_result[0]
        assert pos.vin is not None
        assert pos.soc_pct is not None
        assert 0 <= pos.soc_pct <= 100

    def test_telemetry_has_gps(self, telemetry_result):
        pos = telemetry_result[0]
        assert pos.lat is not None
        assert pos.lon is not None
        assert 35 < pos.lat < 70
        assert -15 < pos.lon < 45

    def test_telemetry_has_battery_data(self, telemetry_result):
        pos = telemetry_result[0]
        assert pos.range_km is not None
        assert pos.bat_capacity_kwh is not None
        assert pos.energy_remaining_kwh is not None

    def test_telemetry_has_tire_pressure(self, telemetry_result):
        pos = telemetry_result[0]
        assert pos.tire_pressure_fl is not None
        assert pos.tire_pressure_fr is not None

    def test_telemetry_has_door_lock(self, telemetry_result):
        pos = telemetry_result[0]
        assert pos.door_lock_status is not None

    def test_telemetry_has_heading(self, telemetry_result):
        pos = telemetry_result[0]
        assert pos.heading is not None

    def test_telemetry_has_ignition(self, telemetry_result):
        pos = telemetry_result[0]
        assert pos.ignition_status is not None


class TestLiveFullPoll:
    def test_poll_once_stores_data(self, live_cfg, live_conn, live_api,
                                   garage_result, telemetry_result):
        """Use cached results via mocked API to avoid extra calls."""
        from unittest.mock import MagicMock
        mock_api = MagicMock(spec=FordAPI)
        mock_api.get_garage.return_value = garage_result
        mock_api.get_telemetry.return_value = telemetry_result

        poller = Poller(live_cfg, live_conn, mock_api)
        poller.poll_once()

        with live_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM vehicles")
            assert cur.fetchone()[0] >= 1
            cur.execute("SELECT COUNT(*) FROM positions")
            assert cur.fetchone()[0] >= 1
