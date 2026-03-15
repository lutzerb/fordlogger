import copy
from fordlogger.api import FordAPI
from tests.conftest import SAMPLE_TELEMETRY, SAMPLE_GARAGE


def _make_api():
    """Create API instance without needing real credentials for parsing tests."""
    return FordAPI({
        "client_id": "test", "client_secret": "test",
        "api_base": "https://example.com",
        "redirect_uri": "http://localhost:8080/callback",
        "token_url": "https://example.com/token",
        "token_file": "/dev/null",
    })


class TestTelemetryParser:
    def test_parse_basic_fields(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos is not None
        assert pos.vin == "WF02XXERK1SM24006"
        assert pos.soc_pct == 67.5
        assert pos.range_km == 162.0
        assert pos.odometer_km == 4804.0
        assert pos.speed_kmh == 0.0

    def test_parse_gps(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.lat == 47.812982
        assert pos.lon == 16.219209
        assert pos.heading == 99.1

    def test_parse_battery(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.bat_temp_c == 6.0
        assert pos.bat_voltage == 340.5
        assert pos.bat_current_a == 0.080078125
        assert pos.bat_capacity_kwh == 48.65
        assert pos.energy_remaining_kwh == 25.1

    def test_parse_temperatures(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.outside_temp_c == 7.0
        assert pos.bat_temp_c == 6.0

    def test_parse_charge_status(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.plug_status == "DISCONNECTED"
        assert pos.charge_status == "NOT_READY"
        assert pos.charger_voltage == 5.0
        assert pos.charger_current_a == 0.0

    def test_parse_door_lock_list(self):
        """doorLockStatus is a list — should extract ALL_DOORS value."""
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.door_lock_status == "UNLOCKED"

    def test_parse_tire_pressure_list(self):
        """tirePressure is a list with vehicleWheel tags."""
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.tire_pressure_fl == 253.0
        assert pos.tire_pressure_fr == 255.0
        assert pos.tire_pressure_rl == 250.0
        assert pos.tire_pressure_rr == 248.0

    def test_parse_heading_nested(self):
        """heading.value is a dict with heading key."""
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.heading == 99.1

    def test_parse_ignition(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.ignition_status == "OFF"

    def test_parse_missing_vin(self):
        api = _make_api()
        data = {"metrics": {}}
        pos = api._parse_telemetry(data)
        assert pos is None

    def test_parse_charging_vehicle(self):
        """Simulate a charging vehicle with power flowing."""
        api = _make_api()
        data = copy.deepcopy(SAMPLE_TELEMETRY)
        data["metrics"]["xevBatteryChargerVoltageOutput"]["value"] = 230.0
        data["metrics"]["xevBatteryChargerCurrentOutput"]["value"] = 16.0
        data["metrics"]["xevPlugChargerStatus"]["value"] = "CONNECTED"
        data["metrics"]["xevBatteryChargeDisplayStatus"]["value"] = "ChargingAC"
        pos = api._parse_telemetry(data)
        assert pos.charge_power_kw == 3.68  # 230 * 16 / 1000
        assert pos.plug_status == "CONNECTED"
        assert pos.charge_status == "ChargingAC"

    def test_parse_driving_vehicle(self):
        """Simulate a driving vehicle."""
        api = _make_api()
        data = copy.deepcopy(SAMPLE_TELEMETRY)
        data["metrics"]["speed"]["value"] = 85.0
        data["metrics"]["ignitionStatus"]["value"] = "Run"
        pos = api._parse_telemetry(data)
        assert pos.speed_kmh == 85.0
        assert pos.ignition_status == "Run"

    def test_raw_json_stored(self):
        api = _make_api()
        pos = api._parse_telemetry(SAMPLE_TELEMETRY)
        assert pos.raw_json is not None
        assert pos.raw_json["vin"] == "WF02XXERK1SM24006"

    def test_missing_metric_returns_none(self):
        """Metrics not present in response should return None."""
        api = _make_api()
        data = {
            "vin": "TEST",
            "metrics": {
                "speed": {"value": 0.0},
            },
        }
        pos = api._parse_telemetry(data)
        assert pos.soc_pct is None
        assert pos.lat is None
        assert pos.bat_temp_c is None
