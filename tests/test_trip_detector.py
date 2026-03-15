from datetime import datetime, timezone, timedelta

from fordlogger.models import Vehicle, Position
from fordlogger import db
from fordlogger.trip_detector import finalize_trip


class TestTripDetector:
    def _setup_driving(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        now = datetime.now(timezone.utc)
        positions = [
            Position(ts=now, vin="TEST001", soc_pct=80.0, range_km=200.0,
                     odometer_km=1000.0, speed_kmh=0.0, lat=47.0, lon=16.0,
                     energy_remaining_kwh=35.0, outside_temp_c=10.0, state="driving"),
            Position(ts=now + timedelta(minutes=5), vin="TEST001", soc_pct=78.0,
                     range_km=195.0, odometer_km=1005.0, speed_kmh=60.0,
                     lat=47.01, lon=16.01, energy_remaining_kwh=34.0,
                     outside_temp_c=10.0, state="driving"),
            Position(ts=now + timedelta(minutes=10), vin="TEST001", soc_pct=76.0,
                     range_km=190.0, odometer_km=1010.0, speed_kmh=80.0,
                     lat=47.02, lon=16.02, energy_remaining_kwh=33.0,
                     outside_temp_c=11.0, state="driving"),
            Position(ts=now + timedelta(minutes=20), vin="TEST001", soc_pct=72.0,
                     range_km=180.0, odometer_km=1025.0, speed_kmh=0.0,
                     lat=47.05, lon=16.05, energy_remaining_kwh=31.0,
                     outside_temp_c=10.0, state="parked"),
        ]
        for p in positions:
            db.insert_position(conn, p)
        return now, now + timedelta(minutes=20)

    def test_finalize_trip_basic(self, conn):
        start, end = self._setup_driving(conn)
        trip = finalize_trip(conn, "TEST001", start, end)
        assert trip is not None
        assert trip.distance_km == 25.0
        assert trip.start_soc_pct == 80.0
        assert trip.end_soc_pct == 72.0
        assert trip.soc_used_pct == 8.0
        assert trip.energy_used_kwh == 4.0
        assert trip.start_lat == 47.0
        assert trip.end_lat == 47.05

    def test_finalize_trip_consumption(self, conn):
        start, end = self._setup_driving(conn)
        trip = finalize_trip(conn, "TEST001", start, end)
        # 4 kWh / 25 km * 100 = 16.0 kWh/100km
        assert trip.consumption_kwh_per_100km == 16.0

    def test_finalize_trip_speeds(self, conn):
        start, end = self._setup_driving(conn)
        trip = finalize_trip(conn, "TEST001", start, end)
        assert trip.max_speed_kmh == 80.0
        assert trip.avg_speed_kmh is not None

    def test_finalize_trip_outside_temp(self, conn):
        start, end = self._setup_driving(conn)
        trip = finalize_trip(conn, "TEST001", start, end)
        assert trip.outside_temp_c is not None

    def test_finalize_trip_too_few_positions(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        now = datetime.now(timezone.utc)
        db.insert_position(conn, Position(ts=now, vin="TEST001", speed_kmh=60.0))
        trip = finalize_trip(conn, "TEST001", now, now + timedelta(minutes=1))
        assert trip is None

    def test_finalize_trip_too_short(self, conn):
        db.upsert_vehicle(conn, Vehicle(vin="TEST001"))
        now = datetime.now(timezone.utc)
        db.insert_position(conn, Position(ts=now, vin="TEST001", speed_kmh=60.0))
        db.insert_position(conn, Position(
            ts=now + timedelta(seconds=30), vin="TEST001", speed_kmh=0.0))
        trip = finalize_trip(conn, "TEST001", now, now + timedelta(seconds=30))
        assert trip is None
