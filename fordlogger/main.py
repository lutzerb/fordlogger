import argparse
import logging
import sys

from .config import load_config
from .auth import do_auth_flow
from .api import FordAPI
from . import db
from .poller import Poller
from .geocoder import backfill_addresses

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("fordlogger")


def main():
    parser = argparse.ArgumentParser(description="FordLogger – Ford vehicle data logger")
    parser.add_argument("--auth", action="store_true", help="Run OAuth login flow")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--backfill-addresses", action="store_true", help="Reverse-geocode addresses for existing trips and charge sessions")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        sys.exit(1)

    if args.auth:
        do_auth_flow(cfg)
        return

    # Connect to database
    conn = db.connect(cfg)
    db.ensure_schema(conn)

    if args.backfill_addresses:
        backfill_addresses(conn)
        return

    api = FordAPI(cfg)
    poller = Poller(cfg, conn, api)

    if args.once:
        poller.poll_once()
        return

    # Daemon mode
    poller.run_forever()


if __name__ == "__main__":
    main()
