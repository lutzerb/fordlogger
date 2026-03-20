import json
import logging
from pathlib import Path

import psycopg2
import psycopg2.extras

from .models import Vehicle, Position, Trip, ChargeSession

log = logging.getLogger("fordlogger")

SCHEMA_FILE = Path(__file__).parent.parent / "sql" / "schema.sql"


def connect(cfg: dict):
    conn = psycopg2.connect(
        host=cfg["db_host"],
        port=cfg["db_port"],
        dbname=cfg["db_name"],
        user=cfg["db_user"],
        password=cfg["db_password"],
    )
    conn.autocommit = True
    return conn


def ensure_schema(conn):
    schema_sql = SCHEMA_FILE.read_text()
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    log.info("Database schema created/verified")


def upsert_vehicle(conn, v: Vehicle):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO vehicles (vin, make, model, model_year, color, nickname, engine_type, first_seen, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (vin) DO UPDATE SET
                nickname = COALESCE(EXCLUDED.nickname, vehicles.nickname),
                model = COALESCE(EXCLUDED.model, vehicles.model),
                updated_at = NOW()
        """, (v.vin, v.make, v.model, v.model_year, v.color, v.nickname, v.engine_type))


def insert_position(conn, p: Position) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO positions (
                ts, vin, soc_pct, range_km, odometer_km, speed_kmh,
                lat, lon, heading, bat_temp_c, outside_temp_c,
                bat_voltage, bat_current_a, energy_remaining_kwh, bat_capacity_kwh,
                plug_status, charge_status, charge_power_kw,
                charger_voltage, charger_current_a,
                tire_pressure_fl, tire_pressure_fr, tire_pressure_rl, tire_pressure_rr,
                door_lock_status, ignition_status, state, raw_json
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            ) RETURNING id
        """, (
            p.ts, p.vin, p.soc_pct, p.range_km, p.odometer_km, p.speed_kmh,
            p.lat, p.lon, p.heading, p.bat_temp_c, p.outside_temp_c,
            p.bat_voltage, p.bat_current_a, p.energy_remaining_kwh, p.bat_capacity_kwh,
            p.plug_status, p.charge_status, p.charge_power_kw,
            p.charger_voltage, p.charger_current_a,
            p.tire_pressure_fl, p.tire_pressure_fr, p.tire_pressure_rl, p.tire_pressure_rr,
            p.door_lock_status, p.ignition_status, p.state,
            json.dumps(p.raw_json) if p.raw_json else None,
        ))
        return cur.fetchone()[0]


def insert_state(conn, vin: str, ts, state: str, prev_state: str = None):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO states (vin, ts, state, prev_state) VALUES (%s, %s, %s, %s)",
            (vin, ts, state, prev_state),
        )


def insert_trip(conn, t: Trip) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO trips (
                vin, start_ts, end_ts, duration_s,
                start_pos_id, end_pos_id,
                start_lat, start_lon, end_lat, end_lon,
                start_address, end_address,
                start_odometer_km, end_odometer_km, distance_km,
                start_soc_pct, end_soc_pct, soc_used_pct,
                energy_used_kwh, consumption_kwh_per_100km,
                avg_speed_kmh, max_speed_kmh, outside_temp_c
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s
            ) RETURNING id
        """, (
            t.vin, t.start_ts, t.end_ts, t.duration_s,
            t.start_pos_id, t.end_pos_id,
            t.start_lat, t.start_lon, t.end_lat, t.end_lon,
            t.start_address, t.end_address,
            t.start_odometer_km, t.end_odometer_km, t.distance_km,
            t.start_soc_pct, t.end_soc_pct, t.soc_used_pct,
            t.energy_used_kwh, t.consumption_kwh_per_100km,
            t.avg_speed_kmh, t.max_speed_kmh, t.outside_temp_c,
        ))
        return cur.fetchone()[0]


def insert_charge_session(conn, cs: ChargeSession) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO charge_sessions (
                vin, start_ts, end_ts, duration_s,
                start_pos_id, end_pos_id,
                lat, lon, address,
                start_soc_pct, end_soc_pct, soc_added_pct,
                energy_added_kwh, max_power_kw, avg_power_kw,
                charge_type, outside_temp_c
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            ) RETURNING id
        """, (
            cs.vin, cs.start_ts, cs.end_ts, cs.duration_s,
            cs.start_pos_id, cs.end_pos_id,
            cs.lat, cs.lon, cs.address,
            cs.start_soc_pct, cs.end_soc_pct, cs.soc_added_pct,
            cs.energy_added_kwh, cs.max_power_kw, cs.avg_power_kw,
            cs.charge_type, cs.outside_temp_c,
        ))
        return cur.fetchone()[0]


def get_latest_position(conn, vin: str) -> dict | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM positions WHERE vin = %s ORDER BY ts DESC LIMIT 1",
            (vin,),
        )
        return cur.fetchone()


def get_latest_state(conn, vin: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT state FROM states WHERE vin = %s ORDER BY ts DESC LIMIT 1",
            (vin,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def get_positions_since(conn, vin: str, since_ts) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM positions WHERE vin = %s AND ts >= %s ORDER BY ts",
            (vin, since_ts),
        )
        return cur.fetchall()
