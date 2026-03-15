-- FordLogger Schema

CREATE TABLE IF NOT EXISTS vehicles (
    vin             TEXT PRIMARY KEY,
    make            TEXT,
    model           TEXT,
    model_year      INTEGER,
    color           TEXT,
    nickname        TEXT,
    engine_type     TEXT,
    first_seen      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id                   SERIAL PRIMARY KEY,
    ts                   TIMESTAMPTZ NOT NULL,
    vin                  TEXT NOT NULL REFERENCES vehicles(vin),
    soc_pct              REAL,
    range_km             REAL,
    odometer_km          REAL,
    speed_kmh            REAL,
    lat                  DOUBLE PRECISION,
    lon                  DOUBLE PRECISION,
    heading              REAL,
    bat_temp_c           REAL,
    outside_temp_c       REAL,
    bat_voltage          REAL,
    bat_current_a        REAL,
    energy_remaining_kwh REAL,
    bat_capacity_kwh     REAL,
    plug_status          TEXT,
    charge_status        TEXT,
    charge_power_kw      REAL,
    charger_voltage      REAL,
    charger_current_a    REAL,
    tire_pressure_fl     REAL,
    tire_pressure_fr     REAL,
    tire_pressure_rl     REAL,
    tire_pressure_rr     REAL,
    door_lock_status     TEXT,
    ignition_status      TEXT,
    state                TEXT,
    raw_json             JSONB
);

CREATE INDEX IF NOT EXISTS idx_positions_ts ON positions(ts);
CREATE INDEX IF NOT EXISTS idx_positions_vin_ts ON positions(vin, ts);

CREATE TABLE IF NOT EXISTS trips (
    id                       SERIAL PRIMARY KEY,
    vin                      TEXT NOT NULL REFERENCES vehicles(vin),
    start_ts                 TIMESTAMPTZ NOT NULL,
    end_ts                   TIMESTAMPTZ NOT NULL,
    duration_s               INTEGER,
    start_pos_id             INTEGER REFERENCES positions(id),
    end_pos_id               INTEGER REFERENCES positions(id),
    start_lat                DOUBLE PRECISION,
    start_lon                DOUBLE PRECISION,
    end_lat                  DOUBLE PRECISION,
    end_lon                  DOUBLE PRECISION,
    start_address            TEXT,
    end_address              TEXT,
    start_odometer_km        REAL,
    end_odometer_km          REAL,
    distance_km              REAL,
    start_soc_pct            REAL,
    end_soc_pct              REAL,
    soc_used_pct             REAL,
    energy_used_kwh          REAL,
    consumption_kwh_per_100km REAL,
    avg_speed_kmh            REAL,
    max_speed_kmh            REAL,
    outside_temp_c           REAL
);

CREATE INDEX IF NOT EXISTS idx_trips_vin_start ON trips(vin, start_ts);

CREATE TABLE IF NOT EXISTS charge_sessions (
    id                SERIAL PRIMARY KEY,
    vin               TEXT NOT NULL REFERENCES vehicles(vin),
    start_ts          TIMESTAMPTZ NOT NULL,
    end_ts            TIMESTAMPTZ NOT NULL,
    duration_s        INTEGER,
    start_pos_id      INTEGER REFERENCES positions(id),
    end_pos_id        INTEGER REFERENCES positions(id),
    lat               DOUBLE PRECISION,
    lon               DOUBLE PRECISION,
    address           TEXT,
    start_soc_pct     REAL,
    end_soc_pct       REAL,
    soc_added_pct     REAL,
    energy_added_kwh  REAL,
    max_power_kw      REAL,
    avg_power_kw      REAL,
    charge_type       TEXT,
    outside_temp_c    REAL
);

CREATE INDEX IF NOT EXISTS idx_charge_sessions_vin_start ON charge_sessions(vin, start_ts);

CREATE TABLE IF NOT EXISTS states (
    id         SERIAL PRIMARY KEY,
    vin        TEXT NOT NULL REFERENCES vehicles(vin),
    ts         TIMESTAMPTZ NOT NULL,
    state      TEXT NOT NULL,
    prev_state TEXT
);

CREATE INDEX IF NOT EXISTS idx_states_vin_ts ON states(vin, ts);
