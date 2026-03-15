import os
import pytest
import psycopg2

from fordlogger.config import load_config
from fordlogger import db

TEST_DB_NAME = "fordlogger_test"


@pytest.fixture(scope="session")
def cfg():
    os.environ["FORDLOGGER_DB_HOST"] = os.environ.get("FORDLOGGER_DB_HOST", "localhost")
    config = load_config("config.json")
    config["db_name"] = TEST_DB_NAME
    return config


@pytest.fixture(scope="session")
def conn(cfg):
    # Connect to default DB to create the test database
    admin_conn = psycopg2.connect(
        host=cfg["db_host"],
        port=cfg["db_port"],
        dbname="fordlogger",
        user=cfg["db_user"],
        password=cfg["db_password"],
    )
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    admin_conn.close()

    # Connect to the test database
    c = db.connect(cfg)
    db.ensure_schema(c)
    return c


@pytest.fixture(autouse=True)
def _clean_tables(conn):
    """Clean test data before each test (keep schema)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM states")
        cur.execute("DELETE FROM charge_sessions")
        cur.execute("DELETE FROM trips")
        cur.execute("DELETE FROM positions")
        cur.execute("DELETE FROM vehicles")
    yield


# Real telemetry response captured from Ford API
SAMPLE_TELEMETRY = {
    "updateTime": "2026-03-11T08:25:03.405Z",
    "vehicleId": "1372bcdd-b262-463e-91f3-1210bd4db3f6",
    "vin": "WF02XXERK1SM24006",
    "metrics": {
        "speed": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 0.0,
        },
        "odometer": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 4804.0,
        },
        "position": {
            "updateTime": "2026-03-11T07:55:12Z",
            "value": {
                "location": {"lat": 47.812982, "lon": 16.219209, "alt": 270.0},
                "gpsDimension": "3D_FIX",
            },
        },
        "heading": {
            "updateTime": "2026-03-11T07:55:12Z",
            "value": {
                "heading": 99.1,
                "uncertainty": 0.0,
                "detectionType": "HEADING_RAW_GNSS",
            },
        },
        "xevBatteryStateOfCharge": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 67.5,
        },
        "xevBatteryActualStateOfCharge": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 57.93,
        },
        "xevBatteryRange": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 162.0,
        },
        "xevBatteryCapacity": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 48.65,
        },
        "xevBatteryEnergyRemaining": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 25.1,
        },
        "xevBatteryTemperature": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 6.0,
        },
        "xevBatteryVoltage": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 340.5,
        },
        "xevBatteryIoCurrent": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 0.080078125,
        },
        "outsideTemperature": {
            "updateTime": "2026-03-11T07:55:12Z",
            "value": 7.0,
        },
        "xevPlugChargerStatus": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": "DISCONNECTED",
        },
        "xevBatteryChargeDisplayStatus": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": "NOT_READY",
        },
        "xevBatteryChargerVoltageOutput": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 5.0,
        },
        "xevBatteryChargerCurrentOutput": {
            "updateTime": "2026-03-11T07:55:07Z",
            "value": 0.0,
        },
        "ignitionStatus": {
            "updateTime": "2026-03-11T07:55:12Z",
            "value": "OFF",
        },
        "doorLockStatus": [
            {
                "updateTime": "2026-03-11T07:55:07Z",
                "value": "UNLOCKED",
                "vehicleDoor": "ALL_DOORS",
            },
            {
                "updateTime": "2026-03-11T07:55:07Z",
                "value": "UNLOCKED",
                "vehicleDoor": "UNSPECIFIED_FRONT",
                "vehicleSide": "DRIVER",
            },
        ],
        "tirePressure": [
            {"value": 253.0, "vehicleWheel": "FRONT_LEFT"},
            {"value": 255.0, "vehicleWheel": "FRONT_RIGHT"},
            {"value": 250.0, "vehicleWheel": "REAR_LEFT"},
            {"value": 248.0, "vehicleWheel": "REAR_RIGHT"},
        ],
    },
}

SAMPLE_GARAGE = {
    "vehicles": [
        {
            "vin": "WF02XXERK1SM24006",
            "make": "Ford",
            "modelName": "Puma",
            "modelYear": 2025,
            "color": "Grey",
            "nickName": "Puma",
            "engineType": "BEV",
        }
    ]
}
