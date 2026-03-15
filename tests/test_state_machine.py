from datetime import datetime, timezone, timedelta
from fordlogger.state_machine import StateMachine, VehicleState
from fordlogger.models import Position


def _pos(speed=0.0, charge_status=None, plug_status=None, charge_power=None,
         ignition="OFF", ts=None):
    return Position(
        ts=ts or datetime.now(timezone.utc),
        vin="TEST",
        speed_kmh=speed,
        charge_status=charge_status,
        plug_status=plug_status,
        charge_power_kw=charge_power,
        ignition_status=ignition,
    )


class TestStateMachine:
    def test_initial_state_parked(self):
        sm = StateMachine("TEST")
        assert sm.state == VehicleState.PARKED

    def test_driving_from_speed(self):
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos(speed=60.0))
        assert state == VehicleState.DRIVING
        assert changed is True

    def test_driving_from_ignition(self):
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos(ignition="Run"))
        assert state == VehicleState.DRIVING
        assert changed is True

    def test_driving_from_ignition_on(self):
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos(ignition="ON"))
        assert state == VehicleState.DRIVING
        assert changed is True

    def test_charging_from_status(self):
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos(charge_status="ChargingAC"))
        assert state == VehicleState.CHARGING
        assert changed is True

    def test_charging_from_power_and_plug(self):
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos(
            charge_power=7.0, plug_status="CONNECTED"
        ))
        assert state == VehicleState.CHARGING
        assert changed is True

    def test_parked_no_change(self):
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos())
        assert state == VehicleState.PARKED
        assert changed is False

    def test_driving_to_parked(self):
        sm = StateMachine("TEST")
        sm.transition(_pos(speed=60.0))
        assert sm.state == VehicleState.DRIVING
        state, changed = sm.transition(_pos(speed=0.0))
        assert state == VehicleState.PARKED
        assert changed is True

    def test_charging_to_parked(self):
        sm = StateMachine("TEST")
        sm.transition(_pos(charge_status="ChargingAC"))
        assert sm.state == VehicleState.CHARGING
        state, changed = sm.transition(_pos(charge_status="NOT_READY"))
        assert state == VehicleState.PARKED
        assert changed is True

    def test_sleep_after_timeout(self):
        sm = StateMachine("TEST", sleep_after_minutes=1)
        now = datetime.now(timezone.utc)
        # First poll at t=0 — parked
        sm.transition(_pos(ts=now))
        assert sm.state == VehicleState.PARKED
        # Second poll 2 minutes later — should sleep
        state, changed = sm.transition(_pos(ts=now + timedelta(minutes=2)))
        assert state == VehicleState.SLEEPING
        assert changed is True

    def test_sleep_stays_sleeping(self):
        sm = StateMachine("TEST", sleep_after_minutes=1)
        now = datetime.now(timezone.utc)
        sm.transition(_pos(ts=now))
        sm.transition(_pos(ts=now + timedelta(minutes=2)))
        assert sm.state == VehicleState.SLEEPING
        # Another parked poll — stays sleeping
        state, changed = sm.transition(_pos(ts=now + timedelta(minutes=3)))
        assert state == VehicleState.SLEEPING
        assert changed is False

    def test_wake_from_sleep_driving(self):
        sm = StateMachine("TEST", sleep_after_minutes=1)
        now = datetime.now(timezone.utc)
        sm.transition(_pos(ts=now))
        sm.transition(_pos(ts=now + timedelta(minutes=2)))
        assert sm.state == VehicleState.SLEEPING
        # Start driving — wakes up
        state, changed = sm.transition(_pos(speed=50.0, ts=now + timedelta(minutes=3)))
        assert state == VehicleState.DRIVING
        assert changed is True

    def test_wake_from_sleep_charging(self):
        sm = StateMachine("TEST", sleep_after_minutes=1)
        now = datetime.now(timezone.utc)
        sm.transition(_pos(ts=now))
        sm.transition(_pos(ts=now + timedelta(minutes=2)))
        assert sm.state == VehicleState.SLEEPING
        # Start charging — wakes up
        state, changed = sm.transition(_pos(
            charge_status="ChargingAC", ts=now + timedelta(minutes=3),
        ))
        assert state == VehicleState.CHARGING
        assert changed is True

    def test_gps_noise_speed_stays_parked(self):
        """Ford API reports ~0.09 km/h when parked — should not trigger driving."""
        sm = StateMachine("TEST")
        state, changed = sm.transition(_pos(speed=0.09))
        assert state == VehicleState.PARKED
        assert changed is False

    def test_driving_priority_over_charging(self):
        """If both speed > 0 and charging, driving takes priority."""
        sm = StateMachine("TEST")
        state, _ = sm.transition(_pos(speed=30.0, charge_status="ChargingAC"))
        assert state == VehicleState.DRIVING

    def test_significant_change_delays_sleep(self):
        sm = StateMachine("TEST", sleep_after_minutes=1)
        now = datetime.now(timezone.utc)
        sm.transition(_pos(ts=now))
        # At 30s, charging briefly — resets the sleep timer
        sm.transition(_pos(charge_status="CHARGING", ts=now + timedelta(seconds=30)))
        assert sm.state == VehicleState.CHARGING
        # Back to parked
        sm.transition(_pos(ts=now + timedelta(seconds=45)))
        assert sm.state == VehicleState.PARKED
        # At 90s after last significant change (45s) — not enough time
        state, _ = sm.transition(_pos(ts=now + timedelta(seconds=90)))
        assert state == VehicleState.PARKED  # not sleeping yet
