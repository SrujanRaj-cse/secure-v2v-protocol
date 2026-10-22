"""Educational event relevance and relative-motion estimates."""

import math
from typing import Any

EARTH_RADIUS_M = 6_371_000.0
_HEADINGS = {
    "N": 0.0, "NORTH": 0.0, "NE": 45.0, "NORTHEAST": 45.0,
    "E": 90.0, "EAST": 90.0, "SE": 135.0, "SOUTHEAST": 135.0,
    "S": 180.0, "SOUTH": 180.0, "SW": 225.0, "SOUTHWEST": 225.0,
    "W": 270.0, "WEST": 270.0, "NW": 315.0, "NORTHWEST": 315.0,
}


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between (latitude, longitude) points."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def _bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _angle_delta(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def evaluate_relevance(
    receiver: dict[str, Any], message: dict[str, Any], threshold_m: float = 500.0
) -> dict[str, Any]:
    """Evaluate relevance separately from authentication; TTC needs same-direction closure."""
    event_pos = message.get("position") or {}
    receiver_pos = receiver.get("position")
    base = {"relevant": False, "distance_m": None, "relative_speed_mps": None,
            "ttc_seconds": None, "reason": "Position unavailable", "warning": False}
    if not isinstance(receiver_pos, (tuple, list)) or len(receiver_pos) != 2:
        return base
    if not isinstance(event_pos, dict) or "latitude" not in event_pos or "longitude" not in event_pos:
        return base
    point = (float(receiver_pos[0]), float(receiver_pos[1]))
    target = (float(event_pos["latitude"]), float(event_pos["longitude"]))
    distance = haversine_m(point, target)
    base["distance_m"] = round(distance, 2)
    if distance > threshold_m:
        base["reason"] = "Event is beyond the relevance threshold"
        return base

    try:
        receiver_speed = float(receiver.get("speed", 0)) / 3.6
        event_speed = float(message.get("speed", 0)) / 3.6
    except (TypeError, ValueError):
        receiver_speed = event_speed = math.nan
    speeds_valid = (math.isfinite(receiver_speed) and math.isfinite(event_speed)
                    and receiver_speed >= 0 and event_speed >= 0)
    receiver_heading = _HEADINGS.get(str(receiver.get("direction", "")).upper())
    event_heading = _HEADINGS.get(str(message.get("direction", "")).upper())
    bearing = _bearing_deg(point, target)
    approaching = receiver_heading is not None and _angle_delta(receiver_heading, bearing) <= 60
    same_direction = (receiver_heading is not None and event_heading is not None
                      and _angle_delta(receiver_heading, event_heading) <= 30)
    if speeds_valid:
        # Positive means the receiver is gaining on the event vehicle.
        base["relative_speed_mps"] = round(receiver_speed - event_speed, 3)
    ttc = None
    if approaching and same_direction and speeds_valid and receiver_speed > event_speed:
        # Local east/north coordinates: compass heading 0° is north, 90° east.
        # Project the receiver-to-event vector onto the event vehicle's forward axis.
        # TTC is positive distance in metres divided by positive closing speed m/s.
        forward = (math.sin(math.radians(event_heading)), math.cos(math.radians(event_heading)))
        dlat_m = (target[0] - point[0]) * math.pi / 180 * EARTH_RADIUS_M
        dlon_m = (target[1] - point[1]) * math.pi / 180 * EARTH_RADIUS_M * math.cos(math.radians(point[0]))
        ahead = dlon_m * forward[0] + dlat_m * forward[1]
        if ahead > 0:
            ttc = ahead / (receiver_speed - event_speed)
            base["ttc_seconds"] = round(ttc, 2)
    proximity_hazard = message.get("event") in ("ROAD_HAZARD", "ACCIDENT_WARNING")
    relevant = approaching or proximity_hazard
    # Moving-vehicle warnings require a calculable TTC within 10 seconds.
    # Nearby fixed hazards use proximity as their warning criterion.
    warning = ((approaching and ttc is not None and math.isfinite(ttc) and ttc <= 10.0)
               or (proximity_hazard and distance <= threshold_m))
    base.update({"relevant": relevant,
                 "reason": "Vehicle is approaching the event area" if approaching else
                           "Hazard is nearby" if relevant else "Vehicle is travelling away from the event",
                 "warning": warning})
    return base
