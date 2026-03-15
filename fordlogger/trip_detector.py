import logging
from .models import Trip
from . import db
from .geocoder import reverse_geocode

log = logging.getLogger("fordlogger")


def finalize_trip(conn, vin: str, drive_start_ts, drive_end_ts, geocoding: bool = True) -> Trip | None:
    """Create a trip summary from positions between start and end timestamps."""
    positions = db.get_positions_since(conn, vin, drive_start_ts)
    drive_positions = [p for p in positions if p["ts"] <= drive_end_ts]

    if len(drive_positions) < 2:
        log.warning("Zu wenige Positionen fuer Trip: %d", len(drive_positions))
        return None

    first = drive_positions[0]
    last = drive_positions[-1]

    duration_s = int((last["ts"] - first["ts"]).total_seconds())
    if duration_s < 60:
        log.debug("Trip zu kurz (%ds), uebersprungen", duration_s)
        return None

    start_odo = first.get("odometer_km")
    end_odo = last.get("odometer_km")
    distance = None
    if start_odo is not None and end_odo is not None:
        distance = round(end_odo - start_odo, 2)

    start_soc = first.get("soc_pct")
    end_soc = last.get("soc_pct")
    soc_used = None
    if start_soc is not None and end_soc is not None:
        soc_used = round(start_soc - end_soc, 1)

    energy_rem_start = first.get("energy_remaining_kwh")
    energy_rem_end = last.get("energy_remaining_kwh")
    energy_used = None
    if energy_rem_start is not None and energy_rem_end is not None:
        energy_used = round(energy_rem_start - energy_rem_end, 3)

    consumption = None
    if energy_used and distance and distance > 0:
        consumption = round(energy_used / distance * 100, 2)

    speeds = [p["speed_kmh"] for p in drive_positions if p.get("speed_kmh") is not None]
    avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else None
    max_speed = round(max(speeds), 1) if speeds else None

    temps = [p["outside_temp_c"] for p in drive_positions if p.get("outside_temp_c") is not None]
    outside_temp = round(sum(temps) / len(temps), 1) if temps else None

    # Reverse geocode start/end positions
    start_addr = None
    end_addr = None
    if geocoding:
        try:
            start_addr = reverse_geocode(first.get("lat"), first.get("lon"))
            end_addr = reverse_geocode(last.get("lat"), last.get("lon"))
        except Exception as e:
            log.warning("Geocoding fuer Trip fehlgeschlagen: %s", e)

    trip = Trip(
        vin=vin,
        start_ts=first["ts"],
        end_ts=last["ts"],
        duration_s=duration_s,
        start_pos_id=first.get("id"),
        end_pos_id=last.get("id"),
        start_lat=first.get("lat"),
        start_lon=first.get("lon"),
        end_lat=last.get("lat"),
        end_lon=last.get("lon"),
        start_address=start_addr,
        end_address=end_addr,
        start_odometer_km=start_odo,
        end_odometer_km=end_odo,
        distance_km=distance,
        start_soc_pct=start_soc,
        end_soc_pct=end_soc,
        soc_used_pct=soc_used,
        energy_used_kwh=energy_used,
        consumption_kwh_per_100km=consumption,
        avg_speed_kmh=avg_speed,
        max_speed_kmh=max_speed,
        outside_temp_c=outside_temp,
    )

    trip_id = db.insert_trip(conn, trip)
    log.info(
        "Trip gespeichert #%d: %.1fkm, %dmin, %.1f kWh/100km",
        trip_id,
        distance or 0,
        duration_s // 60,
        consumption or 0,
    )
    return trip
