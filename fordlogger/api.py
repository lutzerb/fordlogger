import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from .auth import get_valid_token
from .models import Vehicle, Position

log = logging.getLogger("fordlogger")

MAX_RETRIES = 3
RETRY_BACKOFF = [30, 60, 120]  # seconds between retries


class FordAPI:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base = cfg["api_base"]

    def _get(self, path: str) -> dict:
        for attempt in range(MAX_RETRIES + 1):
            token = get_valid_token(self.cfg)
            r = requests.get(
                f"{self.base}/{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 429:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF[attempt]
                    log.warning("429 Rate Limited on /%s — retrying in %ds (attempt %d/%d)",
                                path, wait, attempt + 1, MAX_RETRIES)
                    time.sleep(wait)
                    continue
                log.error("429 Rate Limited on /%s — exhausted %d retries", path, MAX_RETRIES)
            r.raise_for_status()
            return r.json()
        return {}

    def get_garage(self) -> list[Vehicle]:
        data = self._get("garage")
        items = data if isinstance(data, list) else data.get("vehicles", [data])
        vehicles = []
        for v in items:
            vin = v.get("vin") or v.get("vehicleId")
            if not vin:
                continue
            vehicles.append(Vehicle(
                vin=vin,
                make=v.get("make"),
                model=v.get("modelName") or v.get("model"),
                model_year=v.get("modelYear"),
                color=v.get("color"),
                nickname=v.get("nickName") or v.get("nickname"),
                engine_type=v.get("engineType"),
            ))
        return vehicles

    def get_telemetry(self) -> list[Position]:
        data = self._get("telemetry")
        # API returns a single vehicle dict (not a list)
        items = data if isinstance(data, list) else [data]
        positions = []
        for t in items:
            if "metrics" not in t:
                log.warning("Telemetrie ohne metrics-Key: %s", list(t.keys()))
                continue
            pos = self._parse_telemetry(t)
            if pos:
                positions.append(pos)
        return positions

    @staticmethod
    def _extract_latest_update_time(metrics: dict) -> Optional[datetime]:
        """Find the most recent updateTime across all metrics."""
        latest = None
        for entry in metrics.values():
            items = entry if isinstance(entry, list) else [entry]
            for item in items:
                if not isinstance(item, dict):
                    continue
                ut = item.get("updateTime")
                if not ut:
                    continue
                try:
                    parsed = datetime.fromisoformat(ut.replace("Z", "+00:00"))
                    if latest is None or parsed > latest:
                        latest = parsed
                except (ValueError, TypeError):
                    continue
        return latest

    def _parse_telemetry(self, t: dict) -> Optional[Position]:
        metrics = t.get("metrics", {})

        def m(key):
            """Get scalar metric value. Returns None for list-type metrics."""
            entry = metrics.get(key)
            if entry is None:
                return None
            if isinstance(entry, list):
                # List metrics (doorLockStatus, tirePressure, etc.) — take first item
                return entry[0].get("value") if entry else None
            if isinstance(entry, dict):
                return entry.get("value")
            return None

        def m_list(key):
            """Get list-type metric entries."""
            entry = metrics.get(key)
            if isinstance(entry, list):
                return entry
            return []

        vin = t.get("vin") or t.get("vehicleId")
        if not vin:
            return None

        # Use the most recent updateTime from the API as the position timestamp
        ts = self._extract_latest_update_time(metrics) or datetime.now(timezone.utc)

        soc = m("xevBatteryStateOfCharge") or m("xevBatteryActualStateOfCharge")
        rng = m("xevBatteryRange")
        odo = m("odometer")
        speed = m("speed")

        # Position: nested dict with location.lat/lon
        pos_data = m("position")
        lat = lon = None
        if isinstance(pos_data, dict):
            loc = pos_data.get("location", {})
            lat = loc.get("lat")
            lon = loc.get("lon")

        # Heading: nested dict with heading.heading
        heading_data = m("heading")
        heading = None
        if isinstance(heading_data, dict):
            heading = heading_data.get("heading")
        elif isinstance(heading_data, (int, float)):
            heading = heading_data

        bat_temp = m("xevBatteryTemperature")
        outside_temp = m("outsideTemperature")
        bat_voltage = m("xevBatteryVoltage")
        bat_current = m("xevBatteryIoCurrent")
        energy_rem = m("xevBatteryEnergyRemaining")
        bat_cap = m("xevBatteryCapacity")

        plug_status = m("xevPlugChargerStatus")
        charge_status = m("xevBatteryChargeDisplayStatus")
        charger_voltage = m("xevBatteryChargerVoltageOutput")
        charger_current = m("xevBatteryChargerCurrentOutput")

        charge_power = None
        try:
            if charger_voltage and charger_current:
                charge_power = round(charger_current * charger_voltage / 1000, 3)
        except Exception:
            pass

        # Tire pressures: list with vehicleWheel tags
        tire_fl = tire_fr = tire_rl = tire_rr = None
        for tp in m_list("tirePressure"):
            wheel = tp.get("vehicleWheel", "")
            val = tp.get("value")
            if "FRONT_LEFT" in wheel:
                tire_fl = val
            elif "FRONT_RIGHT" in wheel:
                tire_fr = val
            elif "REAR_LEFT" in wheel:
                tire_rl = val
            elif "REAR_RIGHT" in wheel:
                tire_rr = val

        # Door lock status: list, take ALL_DOORS entry
        door_lock = None
        door_entries = m_list("doorLockStatus")
        for d in door_entries:
            if d.get("vehicleDoor") == "ALL_DOORS":
                door_lock = d.get("value")
                break
        if door_lock is None and door_entries:
            door_lock = door_entries[0].get("value")

        ignition = m("ignitionStatus")

        return Position(
            ts=ts,
            vin=vin,
            soc_pct=soc,
            range_km=rng,
            odometer_km=odo,
            speed_kmh=speed,
            lat=lat,
            lon=lon,
            heading=heading,
            bat_temp_c=bat_temp,
            outside_temp_c=outside_temp,
            bat_voltage=bat_voltage,
            bat_current_a=bat_current,
            energy_remaining_kwh=energy_rem,
            bat_capacity_kwh=bat_cap,
            plug_status=plug_status,
            charge_status=charge_status,
            charge_power_kw=charge_power,
            charger_voltage=charger_voltage,
            charger_current_a=charger_current,
            tire_pressure_fl=tire_fl,
            tire_pressure_fr=tire_fr,
            tire_pressure_rl=tire_rl,
            tire_pressure_rr=tire_rr,
            door_lock_status=door_lock,
            ignition_status=ignition,
            raw_json=t,
        )
