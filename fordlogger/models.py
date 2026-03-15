from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Vehicle:
    vin: str
    make: Optional[str] = None
    model: Optional[str] = None
    model_year: Optional[int] = None
    color: Optional[str] = None
    nickname: Optional[str] = None
    engine_type: Optional[str] = None
    first_seen: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Position:
    ts: datetime
    vin: str
    soc_pct: Optional[float] = None
    range_km: Optional[float] = None
    odometer_km: Optional[float] = None
    speed_kmh: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    heading: Optional[float] = None
    bat_temp_c: Optional[float] = None
    outside_temp_c: Optional[float] = None
    bat_voltage: Optional[float] = None
    bat_current_a: Optional[float] = None
    energy_remaining_kwh: Optional[float] = None
    bat_capacity_kwh: Optional[float] = None
    plug_status: Optional[str] = None
    charge_status: Optional[str] = None
    charge_power_kw: Optional[float] = None
    charger_voltage: Optional[float] = None
    charger_current_a: Optional[float] = None
    tire_pressure_fl: Optional[float] = None
    tire_pressure_fr: Optional[float] = None
    tire_pressure_rl: Optional[float] = None
    tire_pressure_rr: Optional[float] = None
    door_lock_status: Optional[str] = None
    ignition_status: Optional[str] = None
    state: Optional[str] = None
    raw_json: Optional[dict] = field(default=None, repr=False)
    id: Optional[int] = None


@dataclass
class Trip:
    vin: str
    start_ts: datetime
    end_ts: datetime
    duration_s: int
    start_pos_id: Optional[int] = None
    end_pos_id: Optional[int] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    start_odometer_km: Optional[float] = None
    end_odometer_km: Optional[float] = None
    distance_km: Optional[float] = None
    start_soc_pct: Optional[float] = None
    end_soc_pct: Optional[float] = None
    soc_used_pct: Optional[float] = None
    energy_used_kwh: Optional[float] = None
    consumption_kwh_per_100km: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    max_speed_kmh: Optional[float] = None
    outside_temp_c: Optional[float] = None
    id: Optional[int] = None


@dataclass
class ChargeSession:
    vin: str
    start_ts: datetime
    end_ts: datetime
    duration_s: int
    start_pos_id: Optional[int] = None
    end_pos_id: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None
    start_soc_pct: Optional[float] = None
    end_soc_pct: Optional[float] = None
    soc_added_pct: Optional[float] = None
    energy_added_kwh: Optional[float] = None
    max_power_kw: Optional[float] = None
    avg_power_kw: Optional[float] = None
    charge_type: Optional[str] = None
    outside_temp_c: Optional[float] = None
    id: Optional[int] = None
