import logging
import time

import requests

log = logging.getLogger("fordlogger")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_last_request_time = 0.0


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Reverse geocode lat/lon to a short address via Nominatim.

    Respects Nominatim's 1 request/second rate limit.
    Returns 'Street, City' or None on failure.
    """
    global _last_request_time

    if lat is None or lon is None:
        return None

    # Rate limit: 1 req/sec
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    try:
        r = requests.get(
            NOMINATIM_URL,
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 18,
                "addressdetails": 1,
            },
            headers={"User-Agent": "FordLogger/0.1 (https://github.com/lutzerb/fordlogger)"},
            timeout=10,
        )
        _last_request_time = time.time()
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("Geocoding failed for %.6f, %.6f: %s", lat, lon, e)
        return None

    addr = data.get("address", {})
    road = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or ""
    house = addr.get("house_number") or ""
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
    country = addr.get("country_code", "").upper()

    parts = []
    if road:
        parts.append(f"{road} {house}".strip())
    if city:
        parts.append(city)
    if country:
        parts.append(country)

    return ", ".join(parts) if parts else data.get("display_name", "")[:100]


def backfill_addresses(conn):
    """Geocode all trips and charge sessions that have coordinates but no address."""
    with conn.cursor() as cur:
        # Trips without start_address
        cur.execute("""
            SELECT id, start_lat, start_lon, end_lat, end_lon
            FROM trips
            WHERE (start_address IS NULL AND start_lat IS NOT NULL)
               OR (end_address IS NULL AND end_lat IS NOT NULL)
            ORDER BY id
        """)
        trips = cur.fetchall()

    log.info("Backfill: %d trip(s) without address", len(trips))
    for trip_id, start_lat, start_lon, end_lat, end_lon in trips:
        start_addr = reverse_geocode(start_lat, start_lon) if start_lat else None
        end_addr = reverse_geocode(end_lat, end_lon) if end_lat else None
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE trips SET start_address = COALESCE(start_address, %s), end_address = COALESCE(end_address, %s) WHERE id = %s",
                (start_addr, end_addr, trip_id),
            )
        log.info("  Trip #%d: %s -> %s", trip_id, start_addr, end_addr)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, lat, lon
            FROM charge_sessions
            WHERE address IS NULL AND lat IS NOT NULL
            ORDER BY id
        """)
        sessions = cur.fetchall()

    log.info("Backfill: %d charge session(s) without address", len(sessions))
    for cs_id, lat, lon in sessions:
        addr = reverse_geocode(lat, lon)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE charge_sessions SET address = %s WHERE id = %s",
                (addr, cs_id),
            )
        log.info("  Charge session #%d: %s", cs_id, addr)

    log.info("Backfill complete")
