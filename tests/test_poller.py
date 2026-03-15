from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import copy

from fordlogger.poller import Poller
from fordlogger.api import FordAPI
from fordlogger.config import INTERVALS
from fordlogger.models import Vehicle, Position
from fordlogger.state_machine import VehicleState
from fordlogger import db
from tests.conftest import SAMPLE_TELEMETRY


class TestPoller:
    def _make_poller(self, conn, cfg):
        api = MagicMock(spec=FordAPI)
        api.get_garage.return_value = [
            Vehicle(vin="TEST001", make="Ford", model="Puma"),
        ]
        poller = Poller(cfg, conn, api)
        return poller, api

    def _make_position(self, **kwargs):
        defaults = dict(
            ts=datetime.now(timezone.utc),
            vin="TEST001",
            soc_pct=67.5,
            range_km=162.0,
            odometer_km=4804.0,
            speed_kmh=0.0,
            lat=47.81,
            lon=16.22,
            plug_status="DISCONNECTED",
            charge_status="NOT_READY",
            ignition_status="OFF",
        )
        defaults.update(kwargs)
        return Position(**defaults)

    def test_poll_once_inserts_position(self, conn, cfg):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        poller, api = self._make_poller(conn, cfg)
        api.get_telemetry.return_value = [self._make_position()]
        poller.poll_once()
        latest = db.get_latest_position(conn, "TEST001")
        assert latest is not None
        assert latest["soc_pct"] == 67.5

    def test_poll_once_updates_garage(self, conn, cfg):
        poller, api = self._make_poller(conn, cfg)
        api.get_telemetry.return_value = []
        poller.poll_once()
        with conn.cursor() as cur:
            cur.execute("SELECT make, model FROM vehicles WHERE vin = 'TEST001'")
            row = cur.fetchone()
        assert row == ("Ford", "Puma")

    def test_state_transition_logged(self, conn, cfg):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        poller, api = self._make_poller(conn, cfg)
        now = datetime.now(timezone.utc)

        # First: parked
        api.get_telemetry.return_value = [self._make_position(ts=now)]
        poller.poll_once()
        assert poller.machines["TEST001"].state == VehicleState.PARKED

        # Second: driving
        api.get_telemetry.return_value = [self._make_position(
            ts=now + timedelta(seconds=30), speed_kmh=60.0,
        )]
        poller.poll_once()
        assert poller.machines["TEST001"].state == VehicleState.DRIVING

        state = db.get_latest_state(conn, "TEST001")
        assert state == "driving"

    def test_trip_finalized_on_stop(self, conn, cfg):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        poller, api = self._make_poller(conn, cfg)
        now = datetime.now(timezone.utc)

        # Drive start
        api.get_telemetry.return_value = [self._make_position(
            ts=now, speed_kmh=60.0, odometer_km=1000.0, soc_pct=80.0,
            energy_remaining_kwh=35.0,
        )]
        poller.poll_once()

        # Mid drive
        api.get_telemetry.return_value = [self._make_position(
            ts=now + timedelta(minutes=5), speed_kmh=80.0, odometer_km=1010.0,
            soc_pct=77.0, energy_remaining_kwh=33.5,
        )]
        poller.poll_once()

        # Drive end (parked)
        api.get_telemetry.return_value = [self._make_position(
            ts=now + timedelta(minutes=10), speed_kmh=0.0, odometer_km=1020.0,
            soc_pct=74.0, energy_remaining_kwh=32.0,
        )]
        poller.poll_once()

        # Check trip was created
        with conn.cursor() as cur:
            cur.execute("SELECT distance_km, start_soc_pct, end_soc_pct FROM trips WHERE vin = 'TEST001'")
            trip = cur.fetchone()
        assert trip is not None
        assert trip[0] == 20.0  # distance
        assert trip[1] == 80.0  # start soc
        assert trip[2] == 74.0  # end soc

    def test_charge_session_finalized(self, conn, cfg):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        poller, api = self._make_poller(conn, cfg)
        now = datetime.now(timezone.utc)

        # Charge start
        api.get_telemetry.return_value = [self._make_position(
            ts=now, charge_status="ChargingAC", plug_status="CONNECTED",
            charge_power_kw=7.4, soc_pct=20.0, energy_remaining_kwh=10.0,
        )]
        poller.poll_once()
        assert poller.machines["TEST001"].state == VehicleState.CHARGING

        # Mid charge
        api.get_telemetry.return_value = [self._make_position(
            ts=now + timedelta(minutes=30), charge_status="ChargingAC",
            plug_status="CONNECTED", charge_power_kw=7.4, soc_pct=50.0,
            energy_remaining_kwh=24.0,
        )]
        poller.poll_once()

        # Charge done (parked)
        api.get_telemetry.return_value = [self._make_position(
            ts=now + timedelta(minutes=60), charge_status="NOT_READY",
            plug_status="DISCONNECTED", charge_power_kw=0.0, soc_pct=80.0,
            energy_remaining_kwh=37.0,
        )]
        poller.poll_once()

        # Check charge session was created
        with conn.cursor() as cur:
            cur.execute("SELECT start_soc_pct, end_soc_pct, energy_added_kwh FROM charge_sessions WHERE vin = 'TEST001'")
            cs = cur.fetchone()
        assert cs is not None
        assert cs[0] == 20.0
        assert cs[1] == 80.0
        assert cs[2] == 27.0

    def test_get_interval_adaptive(self, conn, cfg):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        poller, api = self._make_poller(conn, cfg)

        # No machines yet — default parked
        assert poller.get_interval() == INTERVALS["parked"]

        # After driving
        api.get_telemetry.return_value = [self._make_position(speed_kmh=60.0)]
        poller.poll_once()
        assert poller.get_interval() == INTERVALS["driving"]

    def test_skip_duplicate_api_data(self, conn, cfg):
        """Should not insert a new row if API updateTime hasn't changed."""
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        poller, api = self._make_poller(conn, cfg)
        ts = datetime(2026, 3, 13, 12, 0, 0, tzinfo=timezone.utc)

        api.get_telemetry.return_value = [self._make_position(ts=ts)]
        poller.poll_once()

        # Same timestamp again — should be skipped
        api.get_telemetry.return_value = [self._make_position(ts=ts)]
        poller.poll_once()

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM positions WHERE vin = 'TEST001'")
            count = cur.fetchone()[0]
        assert count == 1

    def test_api_error_handling(self, conn, cfg):
        """Poller should not crash on API errors."""
        poller, api = self._make_poller(conn, cfg)
        api.get_telemetry.side_effect = Exception("API down")
        poller.poll_once()  # Should not raise
