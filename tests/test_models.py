from datetime import datetime, timezone
from fordlogger.models import Vehicle, Position, Trip, ChargeSession


def test_position_defaults():
    pos = Position(ts=datetime.now(timezone.utc), vin="TEST")
    assert pos.soc_pct is None
    assert pos.lat is None
    assert pos.raw_json is None
    assert pos.id is None


def test_vehicle_defaults():
    v = Vehicle(vin="TEST")
    assert v.make is None
    assert v.nickname is None


def test_trip_fields():
    t = Trip(
        vin="TEST",
        start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_ts=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
        duration_s=3600,
        distance_km=50.0,
        consumption_kwh_per_100km=15.5,
    )
    assert t.duration_s == 3600
    assert t.distance_km == 50.0


def test_charge_session_fields():
    cs = ChargeSession(
        vin="TEST",
        start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_ts=datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc),
        duration_s=7200,
        energy_added_kwh=30.0,
        charge_type="DC",
    )
    assert cs.charge_type == "DC"
    assert cs.energy_added_kwh == 30.0
