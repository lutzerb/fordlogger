from datetime import datetime, timezone, timedelta

from fordlogger.models import Vehicle, Position
from fordlogger import db
from fordlogger.charge_detector import finalize_charge_session


class TestChargeDetector:
    def _setup_charging(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        now = datetime.now(timezone.utc)
        positions = [
            Position(ts=now, vin="TEST001", soc_pct=20.0,
                     energy_remaining_kwh=10.0, charge_power_kw=7.4,
                     plug_status="CONNECTED", charge_status="ChargingAC",
                     outside_temp_c=8.0, lat=47.0, lon=16.0, state="charging"),
            Position(ts=now + timedelta(minutes=30), vin="TEST001", soc_pct=40.0,
                     energy_remaining_kwh=19.0, charge_power_kw=7.4,
                     plug_status="CONNECTED", charge_status="ChargingAC",
                     outside_temp_c=8.0, state="charging"),
            Position(ts=now + timedelta(minutes=60), vin="TEST001", soc_pct=60.0,
                     energy_remaining_kwh=28.0, charge_power_kw=7.0,
                     plug_status="CONNECTED", charge_status="ChargingAC",
                     outside_temp_c=7.0, state="charging"),
            Position(ts=now + timedelta(minutes=90), vin="TEST001", soc_pct=80.0,
                     energy_remaining_kwh=37.0, charge_power_kw=0.0,
                     plug_status="CONNECTED", charge_status="NOT_READY",
                     outside_temp_c=7.0, state="parked"),
        ]
        for p in positions:
            db.insert_position(conn, p)
        return now, now + timedelta(minutes=90)

    def test_finalize_charge_session_basic(self, conn):
        start, end = self._setup_charging(conn)
        cs = finalize_charge_session(conn, "TEST001", start, end)
        assert cs is not None
        assert cs.start_soc_pct == 20.0
        assert cs.end_soc_pct == 80.0
        assert cs.soc_added_pct == 60.0
        assert cs.energy_added_kwh == 27.0

    def test_finalize_charge_session_power(self, conn):
        start, end = self._setup_charging(conn)
        cs = finalize_charge_session(conn, "TEST001", start, end)
        assert cs.max_power_kw == 7.4
        assert cs.avg_power_kw is not None

    def test_finalize_charge_session_type_ac(self, conn):
        start, end = self._setup_charging(conn)
        cs = finalize_charge_session(conn, "TEST001", start, end)
        assert cs.charge_type == "AC"

    def test_finalize_charge_session_type_dc(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        now = datetime.now(timezone.utc)
        positions = [
            Position(ts=now, vin="TEST001", soc_pct=10.0,
                     energy_remaining_kwh=5.0, charge_power_kw=50.0,
                     state="charging"),
            Position(ts=now + timedelta(minutes=30), vin="TEST001", soc_pct=50.0,
                     energy_remaining_kwh=24.0, charge_power_kw=45.0,
                     state="charging"),
        ]
        for p in positions:
            db.insert_position(conn, p)
        cs = finalize_charge_session(conn, "TEST001", now, now + timedelta(minutes=30))
        assert cs.charge_type == "DC"

    def test_finalize_charge_session_location(self, conn):
        start, end = self._setup_charging(conn)
        cs = finalize_charge_session(conn, "TEST001", start, end)
        assert cs.lat == 47.0
        assert cs.lon == 16.0

    def test_finalize_charge_too_few_positions(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        now = datetime.now(timezone.utc)
        db.insert_position(conn, Position(ts=now, vin="TEST001", soc_pct=20.0, state="charging"))
        cs = finalize_charge_session(conn, "TEST001", now, now + timedelta(minutes=30))
        assert cs is None
