import logging
import time
from datetime import datetime, timezone

from .api import FordAPI
from .config import INTERVALS
from .state_machine import StateMachine, VehicleState
from . import db
from .trip_detector import finalize_trip
from .charge_detector import finalize_charge_session

log = logging.getLogger("fordlogger")


class Poller:
    def __init__(self, cfg: dict, conn, api: FordAPI):
        self.cfg = cfg
        self.conn = conn
        self.api = api
        self._db_failures = 0
        self.machines: dict[str, StateMachine] = {}
        self._drive_start: dict[str, datetime] = {}
        self._charge_start: dict[str, datetime] = {}
        self._last_ts: dict[str, datetime] = {}  # last API updateTime per VIN
        self._last_garage_update: float = 0
        self.garage_interval_s = 3600  # update garage every hour

    def _get_machine(self, vin: str) -> StateMachine:
        if vin not in self.machines:
            sleep_min = self.cfg.get("sleep_after_minutes", 30)
            sm = StateMachine(vin, sleep_after_minutes=sleep_min)
            # Restore state from DB
            saved_state = db.get_latest_state(self.conn, vin)
            if saved_state and saved_state in VehicleState.__members__.values():
                sm.state = VehicleState(saved_state)
                log.info("Restored state for %s from DB: %s", vin, saved_state)
            self.machines[vin] = sm
        return self.machines[vin]

    def _ensure_db(self):
        """Reconnect to PostgreSQL if the connection is broken."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            self._db_failures = 0
            return True
        except Exception:
            self._db_failures += 1
            log.warning("DB connection lost — attempting reconnect (%d)", self._db_failures)
            try:
                self.conn.close()
            except Exception:
                pass
            try:
                self.conn = db.connect(self.cfg)
                db.ensure_schema(self.conn)
                log.info("DB reconnected successfully")
                self._db_failures = 0
                return True
            except Exception as e:
                log.error("DB reconnect failed: %s", e)
                return False

    def poll_once(self):
        """Execute a single poll cycle: garage (periodic) + telemetry."""
        if not self._ensure_db():
            return

        now = time.time()

        # Periodic garage update
        if now - self._last_garage_update > self.garage_interval_s:
            try:
                vehicles = self.api.get_garage()
                for v in vehicles:
                    db.upsert_vehicle(self.conn, v)
                log.info("Garage updated: %d vehicle(s)", len(vehicles))
                self._last_garage_update = now
            except Exception as e:
                log.error("Garage error: %s", e)

        # Telemetry
        try:
            positions = self.api.get_telemetry()
        except Exception as e:
            log.error("Telemetry error: %s", e, exc_info=True)
            return

        for pos in positions:
            self._process_position(pos)

    def _process_position(self, pos):
        vin = pos.vin

        # Skip if API data hasn't changed (Ford returns stale data when car is off)
        if vin in self._last_ts and pos.ts == self._last_ts[vin]:
            log.debug("Skipping %s — API data unchanged (updateTime=%s)", vin, pos.ts)
            return
        self._last_ts[vin] = pos.ts

        # Clear raw JSON if storage is disabled
        if not self.cfg.get("store_raw_json", True):
            pos.raw_json = None

        sm = self._get_machine(vin)
        old_state = sm.state

        # Run state machine
        new_state, changed = sm.transition(pos)
        pos.state = new_state.value

        # Insert position
        pos_id = db.insert_position(self.conn, pos)
        log.info(
            "Position #%d – %s | SoC=%s%% | Range=%skm | Odo=%skm | State=%s",
            pos_id, vin, pos.soc_pct, pos.range_km, pos.odometer_km, new_state.value,
        )

        if changed:
            db.insert_state(self.conn, vin, pos.ts, new_state.value, old_state.value)
            self._handle_transition(vin, old_state, new_state, pos.ts)

    def _handle_transition(self, vin: str, old: VehicleState, new: VehicleState, ts: datetime):
        # Track drive start/end
        if new == VehicleState.DRIVING:
            self._drive_start[vin] = ts
        elif old == VehicleState.DRIVING and vin in self._drive_start:
            try:
                finalize_trip(self.conn, vin, self._drive_start.pop(vin), ts,
                             geocoding=self.cfg.get("geocoding", True))
            except Exception as e:
                log.error("Trip finalization failed: %s", e, exc_info=True)

        # Track charge start/end
        if new == VehicleState.CHARGING:
            self._charge_start[vin] = ts
        elif old == VehicleState.CHARGING and vin in self._charge_start:
            try:
                finalize_charge_session(self.conn, vin, self._charge_start.pop(vin), ts,
                                       geocoding=self.cfg.get("geocoding", True))
            except Exception as e:
                log.error("Charge session finalization failed: %s", e, exc_info=True)

    def get_interval(self) -> int:
        """Return the shortest polling interval across all vehicles."""
        if not self.machines:
            return INTERVALS["parked"]
        return min(INTERVALS[sm.state.value] for sm in self.machines.values())

    def run_forever(self):
        """Main polling loop with adaptive intervals."""
        log.info("Polling-Daemon gestartet")
        # Initial garage fetch
        self._last_garage_update = 0

        while True:
            self.poll_once()
            interval = self.get_interval()
            log.info("Naechster Poll in %ds", interval)
            time.sleep(interval)
