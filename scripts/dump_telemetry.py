#!/usr/bin/env python3
"""Diagnostic script: dump raw FordConnect API telemetry to stdout.

Usage (from the fordlogger directory):
    python scripts/dump_telemetry.py
    python scripts/dump_telemetry.py --garage
    python scripts/dump_telemetry.py --pretty

Requires config.json and tokens.json in the current directory (or use --config / --tokens).
"""
import argparse
import json
import sys
from pathlib import Path

# Allow running from the repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from fordlogger.auth import get_valid_token
from fordlogger.config import load_config

import requests


def main():
    parser = argparse.ArgumentParser(description="Dump raw FordConnect API responses to stdout")
    parser.add_argument("--config", default="config.json", help="Path to config.json (default: config.json)")
    parser.add_argument("--tokens", default="tokens.json", help="Path to tokens.json (default: tokens.json)")
    parser.add_argument("--garage", action="store_true", help="Dump /garage instead of /telemetry")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    cfg["token_file"] = args.tokens

    try:
        token = get_valid_token(cfg)
    except Exception as e:
        print(f"Error getting token: {e}", file=sys.stderr)
        print("Run --auth first: docker compose run -p 8080:8080 fordlogger python -m fordlogger --auth", file=sys.stderr)
        sys.exit(1)

    endpoint = "garage" if args.garage else "telemetry"
    url = f"{cfg['api_base']}/{endpoint}"

    print(f"Calling: GET {url}", file=sys.stderr)

    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {r.status_code}", file=sys.stderr)

    if r.status_code == 429:
        print("Rate limited (429). Ford allows ~1 request/minute. Wait a moment and retry.", file=sys.stderr)
        sys.exit(1)

    try:
        data = r.json()
    except Exception:
        print(f"Non-JSON response: {r.text[:500]}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(data, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
