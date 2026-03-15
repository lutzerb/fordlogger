import json
import logging
import os
from pathlib import Path

log = logging.getLogger("fordlogger")

DEFAULT_CONFIG = {
    "client_id": "",
    "client_secret": "",
    "redirect_uri": "http://localhost:8080/callback",
    "poll_interval_minutes": 15,
    "auth_url": "https://api.vehicle.ford.com/fcon-public/v1/auth/init",
    "token_url": "https://api.vehicle.ford.com/dah2vb2cprod.onmicrosoft.com/oauth2/v2.0/token?p=B2C_1A_FCON_AUTHORIZE",
    "api_base": "https://api.vehicle.ford.com/fcon-query/v1",
    "db_host": "db",
    "db_port": 5432,
    "db_name": "fordlogger",
    "db_user": "fordlogger",
    "db_password": "fordlogger",
    "sleep_after_minutes": 30,
    "token_file": "tokens.json",
}

INTERVALS = {
    "driving": 60,
    "charging": 60,
    "parked": 120,
    "sleeping": 300,
}


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config-Datei nicht gefunden: {p}")
    cfg = {**DEFAULT_CONFIG, **json.loads(p.read_text())}
    # Allow env var overrides for Docker vs local dev
    if os.environ.get("FORDLOGGER_DB_HOST"):
        cfg["db_host"] = os.environ["FORDLOGGER_DB_HOST"]
    if os.environ.get("FORDLOGGER_DB_PORT"):
        cfg["db_port"] = int(os.environ["FORDLOGGER_DB_PORT"])
    cfg["store_raw_json"] = os.environ.get("FORDLOGGER_STORE_RAW_JSON", "true").lower() in ("true", "1", "yes")
    cfg["geocoding"] = os.environ.get("FORDLOGGER_GEOCODING", "true").lower() in ("true", "1", "yes")
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise ValueError("client_id und client_secret muessen in config.json gesetzt sein")
    return cfg
