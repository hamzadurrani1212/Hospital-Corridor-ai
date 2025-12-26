# app/services/aggression_rules.py
"""
Simple aggression detection rules
Detects fast arm movement near another person
"""

import time
import math

# -----------------------------
# TUNABLE THRESHOLDS
# -----------------------------
ARM_SPEED_THRESHOLD = 110   # pixels per second (Increased from 100)
CLOSE_DISTANCE = 150        # pixels (Increased from 120)
MIN_DURATION = 0.5          # seconds (Decreased from 1.0)
MIN_HITS = 15               # repeated fast movements (Increased from 2 as requested)


# -----------------------------
# HELPERS
# -----------------------------
def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def wrist_speed(history):
    """
    Calculate wrist speed from history
    history = [(x, y, t), ...]
    """
    if len(history) < 2:
        return 0.0

    (x1, y1, t1) = history[-2]
    (x2, y2, t2) = history[-1]

    dt = max(t2 - t1, 0.01)
    return math.hypot(x2 - x1, y2 - y1) / dt


# -----------------------------
# MAIN RULE
# -----------------------------
def evaluate_aggression(track, nearby_tracks, now):
    """
    Returns aggression/fight event dict OR None
    """

    l_history = track.get("left_wrist_history", [])
    r_history = track.get("right_wrist_history", [])
    
    # Check both wrists and take the max speed
    l_speed = wrist_speed(l_history)
    r_speed = wrist_speed(r_history)
    speed = max(l_speed, r_speed)

    # 1️⃣ Fast arm movement
    if speed < ARM_SPEED_THRESHOLD:
        if speed > 20: # Log only significant movements
             print(f"[DEBUG] Track {track['id']} below aggression threshold: {int(speed)}px/s")
        track.pop("aggr_hits", None)
        track.pop("aggr_start", None)
        return None

    # Count repeated hits
    track["aggr_hits"] = track.get("aggr_hits", 0) + 1
    print(f"[DEBUG] Track {track['id']} AGGRESSION HIT {track['aggr_hits']}! Speed: {int(speed)}px/s")
    if "aggr_start" not in track:
        track["aggr_start"] = now

    # 2️⃣ Threshold check (15 hits)
    if track["aggr_hits"] < MIN_HITS:
        return None

    cx, cy = track["center"]
    active_nearby_count = 0
    
    # 3️⃣ Proximity and Mutual Movement Check
    for other in nearby_tracks:
        ox, oy = other["center"]
        dist = distance((cx, cy), (ox, oy))
        
        if dist < CLOSE_DISTANCE:
            # Check if this nearby person is ALSO moving fast
            # We look at their recent wrist history
            ol_speed = wrist_speed(other.get("left_wrist_history", []))
            or_speed = wrist_speed(other.get("right_wrist_history", []))
            o_speed = max(ol_speed, or_speed)
            
            if o_speed > ARM_SPEED_THRESHOLD * 0.7: # Lower threshold for mutual activity
                active_nearby_count += 1

    # 4️⃣ Classification: Fight vs Individual Aggression
    if active_nearby_count >= 1:
        # Multi-person fight detection
        return {
            "type": "FIGHT_DETECTED",
            "severity": "critical",
            "title": "Fight Detected",
            "description": f"Physical altercation involving {active_nearby_count + 1} people detected",
            "track_id": track["id"],
            "timestamp": now,
            "people_involved": active_nearby_count + 1
        }
    
    # Fallback to individual aggression
    if now - track["aggr_start"] >= MIN_DURATION:
        return {
            "type": "AGGRESSIVE_BEHAVIOR",
            "severity": "critical",
            "title": "Aggressive Behavior Detected",
            "description": f"Aggressive movement detected (Speed: {int(speed)}px/s) near another person",
            "track_id": track["id"],
            "timestamp": now
        }

    return None
