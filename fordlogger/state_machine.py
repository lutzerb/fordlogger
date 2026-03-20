import logging
from datetime import datetime, timezone
from enum import Enum

from .models import Position

log = logging.getLogger("fordlogger")


class VehicleState(str, Enum):
    DRIVING = "driving"
    CHARGING = "charging"
    PARKED = "parked"
    SLEEPING = "sleeping"


CHARGING_STATUSES = {"Charging", "ChargingAC", "ChargingDC", "CHARGING"}
PLUG_CONNECTED = {"CONNECTED", "Connected"}


class StateMachine:
    def __init__(self, vin: str, sleep_after_minutes: int = 30):
        self.vin = vin
        self.state = VehicleState.PARKED
        self.last_change_ts: datetime = datetime.now(timezone.utc)
        self._last_significant_change: datetime = datetime.now(timezone.utc)
        self.sleep_after_s = sleep_after_minutes * 60

    def transition(self, pos: Position) -> tuple[VehicleState, bool]:
        """Returns (new_state, changed). Updates internal state."""
        old = self.state
        now = pos.ts

        # Ford API reports tiny nonzero speeds (~0.09 km/h) when parked due to GPS noise
        speed = pos.speed_kmh or 0
        is_driving = speed > 1.0 or pos.ignition_status in ("Run", "RUN", "On", "ON", "START")
        is_charging = (
            (pos.charge_status in CHARGING_STATUSES)
            or ((pos.charge_power_kw or 0) > 0 and pos.plug_status in PLUG_CONNECTED)
        )

        if is_driving:
            new = VehicleState.DRIVING
        elif is_charging:
            new = VehicleState.CHARGING
        elif old == VehicleState.SLEEPING:
            # Stay sleeping unless something active happens
            new = VehicleState.SLEEPING
        else:
            new = VehicleState.PARKED

        # Check for sleep transition: parked for > sleep_after_s with no changes
        if new == VehicleState.PARKED and old == VehicleState.PARKED:
            if (now - self._last_significant_change).total_seconds() > self.sleep_after_s:
                new = VehicleState.SLEEPING

        changed = new != old
        if changed:
            log.info("State change %s: %s -> %s", self.vin, old.value, new.value)
            self.last_change_ts = now
            self._last_significant_change = now

        # Track significant data changes to delay sleep
        if self._has_significant_change(pos):
            self._last_significant_change = now

        self.state = new
        return new, changed

    def _has_significant_change(self, pos: Position) -> bool:
        """Detect if telemetry data changed significantly (delays sleep)."""
        return (
            (pos.speed_kmh or 0) > 1.0
            or pos.charge_status in CHARGING_STATUSES
            or (pos.charge_power_kw or 0) > 0
        )
