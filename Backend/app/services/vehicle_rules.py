# app/services/vehicle_rules.py

from typing import Dict, List, Tuple
import time
import math

# -----------------------------------
# YOLO COCO / CUSTOM CLASS IDS
# -----------------------------------
VEHICLE_CLASSES = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    9: "ambulance",   # only if custom model
}

# -----------------------------------
# HOSPITAL ZONES
# -----------------------------------
RESTRICTED_ZONES = {"corridor", "ward"}
ALLOWED_ZONES = {"parking", "emergency"}

# -----------------------------------
# HELPERS
# -----------------------------------
def get_vehicle_type(class_id: int) -> str:
    return VEHICLE_CLASSES.get(class_id, "unknown")


def infer_zone_from_position(bbox, frame_shape) -> str:
    """
    TEMP heuristic (until polygon zones added)
    """
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = bbox

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    if cy < h * 0.5:
        return "corridor"
    elif cx < w * 0.5:
        return "parking"
    else:
        return "emergency"


def estimate_speed(track) -> float:
    """
    Estimate speed using bbox center movement (pixels/sec)
    """
    history = track.get("history", [])

    if len(history) < 2:
        return 0.0

    x1p, y1p, x2p, y2p, t1 = history[-2]
    x1, y1, x2, y2, t2 = history[-1]

    cx1 = (x1p + x2p) / 2
    cy1 = (y1p + y2p) / 2
    cx2 = (x1 + x2) / 2
    cy2 = (y1 + y2) / 2

    dist = math.sqrt((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2)
    dt = max(t2 - t1, 0.01)

    return dist / dt


# -----------------------------------
# MAIN RULE ENGINE
# -----------------------------------
def evaluate_vehicle_rules(
    vehicle: Dict,
    frame_shape: Tuple[int, int, int]
) -> List[Dict]:
    """
    Apply hospital vehicle rules
    Returns list of alert events
    """

    events = []

    class_id = vehicle.get("class")
    conf = vehicle.get("conf", 0)
    bbox = vehicle.get("bbox")
    track_id = vehicle.get("id")

    # Ignore weak detections
    if conf < 0.5 or not bbox:
        return events

    vehicle_type = get_vehicle_type(class_id)
    zone = infer_zone_from_position(bbox, frame_shape)
    speed = estimate_speed(vehicle)

    # -----------------------------------
    # RULE 1: Vehicle in restricted zone
    # -----------------------------------
    if zone in RESTRICTED_ZONES:
        if not (vehicle_type == "ambulance" and zone == "emergency"):
            events.append({
                "type": "VEHICLE_RESTRICTED_AREA",
                "severity": "warning",
                "title": "Vehicle in Restricted Area",
                "description": f"{vehicle_type.title()} detected in {zone}",
                "vehicle_type": vehicle_type,
                "zone": zone,
                "track_id": track_id,
                "timestamp": time.time()
            })

    # -----------------------------------
    # RULE 2: Heavy vehicle in corridor
    # -----------------------------------
    if vehicle_type in {"bus", "truck"} and zone == "corridor":
        events.append({
            "type": "HEAVY_VEHICLE_CORRIDOR",
            "severity": "critical",
            "title": "Heavy Vehicle Detected",
            "description": f"{vehicle_type.title()} not allowed in corridor",
            "vehicle_type": vehicle_type,
            "zone": zone,
            "track_id": track_id,
            "timestamp": time.time()
        })

    # -----------------------------------
    # RULE 3: Unauthorized parking
    # -----------------------------------
    if vehicle_type == "car" and zone == "corridor":
        events.append({
            "type": "UNAUTHORIZED_PARKING",
            "severity": "warning",
            "title": "Unauthorized Parking",
            "description": "Car parked inside hospital corridor",
            "vehicle_type": vehicle_type,
            "zone": zone,
            "track_id": track_id,
            "timestamp": time.time()
        })

    # -----------------------------------
    # RULE 4: Overspeed vehicle
    # -----------------------------------
    if speed > 120 and zone == "corridor":
        events.append({
            "type": "OVER_SPEED_VEHICLE",
            "severity": "critical",
            "title": "Overspeed Vehicle",
            "description": f"{vehicle_type.title()} moving too fast",
            "speed": round(speed, 2),
            "zone": zone,
            "track_id": track_id,
            "timestamp": time.time()
        })
        
    # -----------------------------------
    # RULE 5: General Vehicle Detection (Visibility)
    # -----------------------------------
    if not events: # If no violation, still alert that we saw a vehicle (per user request)
        events.append({
            "type": "VEHICLE_DETECTED",
            "severity": "info",
            "title": "Vehicle Detected",
            "description": f"{vehicle_type.title()} detected in {zone}",
            "vehicle_type": vehicle_type,
            "zone": zone,
            "track_id": track_id,
            "timestamp": time.time()
        })

    return events
