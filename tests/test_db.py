from datetime import datetime, timezone, timedelta
import json

from fordlogger.models import Vehicle, Position, Trip, ChargeSession
from fordlogger import db


class TestVehicle:
    def test_upsert_vehicle(self, conn):
        v = Vehicle(vin="TEST001", make="Ford", model="Puma", model_year=2025, nickname="TestCar")
        db.upsert_vehicle(conn, v)
        with conn.cursor() as cur:
            cur.execute("SELECT vin, make, model, nickname FROM vehicles WHERE vin = 'TEST001'")
            row = cur.fetchone()
        assert row == ("TEST001", "Ford", "Puma", "TestCar")

    def test_upsert_vehicle_update(self, conn):
        v1 = Vehicle(vin="TEST001", make="Ford", model="Puma", nickname="OldName")
        db.upsert_vehicle(conn, v1)
        v2 = Vehicle(vin="TEST001", make="Ford", model="Puma", nickname="NewName")
        db.upsert_vehicle(conn, v2)
        with conn.cursor() as cur:
            cur.execute("SELECT nickname FROM vehicles WHERE vin = 'TEST001'")
            assert cur.fetchone()[0] == "NewName"


class TestPosition:
    def _insert_vehicle(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001", make="Ford", model="Puma"))

    def test_insert_position(self, conn):
        self._insert_vehicle(conn)
        pos = Position(
            ts=datetime.now(timezone.utc),
            vin="TEST001",
            soc_pct=67.5,
            range_km=162.0,
            odometer_km=4804.0,
            speed_kmh=0.0,
            lat=47.81,
            lon=16.22,
            state="parked",
        )
        pos_id = db.insert_position(conn, pos)
        assert pos_id > 0

    def test_insert_position_with_raw_json(self, conn):
        self._insert_vehicle(conn)
        pos = Position(
            ts=datetime.now(timezone.utc),
            vin="TEST001",
            soc_pct=50.0,
            raw_json={"test": "data"},
        )
        pos_id = db.insert_position(conn, pos)
        with conn.cursor() as cur:
            cur.execute("SELECT raw_json FROM positions WHERE id = %s", (pos_id,))
            raw = cur.fetchone()[0]
        assert raw["test"] == "data"

    def test_get_latest_position(self, conn):
        self._insert_vehicle(conn)
        now = datetime.now(timezone.utc)
        db.insert_position(conn, Position(ts=now - timedelta(minutes=5), vin="TEST001", soc_pct=60.0))
        db.insert_position(conn, Position(ts=now, vin="TEST001", soc_pct=65.0))
        latest = db.get_latest_position(conn, "TEST001")
        assert latest["soc_pct"] == 65.0

    def test_get_positions_since(self, conn):
        self._insert_vehicle(conn)
        now = datetime.now(timezone.utc)
        db.insert_position(conn, Position(ts=now - timedelta(minutes=10), vin="TEST001", soc_pct=50.0))
        db.insert_position(conn, Position(ts=now - timedelta(minutes=5), vin="TEST001", soc_pct=55.0))
        db.insert_position(conn, Position(ts=now, vin="TEST001", soc_pct=60.0))
        positions = db.get_positions_since(conn, "TEST001", now - timedelta(minutes=6))
        assert len(positions) == 2
        assert positions[0]["soc_pct"] == 55.0
        assert positions[1]["soc_pct"] == 60.0


class TestState:
    def test_insert_state(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        db.insert_state(conn, "TEST001", datetime.now(timezone.utc), "driving", "parked")
        state = db.get_latest_state(conn, "TEST001")
        assert state == "driving"

    def test_get_latest_state_empty(self, conn):
        assert db.get_latest_state(conn, "NONEXISTENT") is None


class TestTrip:
    def test_insert_trip(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        trip = Trip(
            vin="TEST001",
            start_ts=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc),
            duration_s=1800,
            distance_km=25.5,
            consumption_kwh_per_100km=14.2,
        )
        trip_id = db.insert_trip(conn, trip)
        assert trip_id > 0


class TestChargeSession:
    def test_insert_charge_session(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        cs = ChargeSession(
            vin="TEST001",
            start_ts=datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 1, 1, 22, 0, tzinfo=timezone.utc),
            duration_s=7200,
            start_soc_pct=20.0,
            end_soc_pct=80.0,
            soc_added_pct=60.0,
            energy_added_kwh=29.0,
            charge_type="AC",
        )
        cs_id = db.insert_charge_session(conn, cs)
        assert cs_id > 0
