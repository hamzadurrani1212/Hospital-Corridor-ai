# app/services/event_engine.py
"""
Event Engine for behavior detection and analysis.
Detects: Loitering, Running, Falling, Crowd Gathering, Fighting
"""

import time
import math
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import threading
import numpy as np
from app.services.aggression_rules import evaluate_aggression


class PersonTracker:
    """Tracks individual person movements over time."""
    
    def __init__(self, track_id: str, initial_position: Tuple[float, float], timestamp: float):
        self.track_id = track_id
        self.positions: List[Tuple[float, float, float]] = [(initial_position[0], initial_position[1], timestamp)]
        self.left_wrist_history: List[Tuple[float, float, float]] = []
        self.right_wrist_history: List[Tuple[float, float, float]] = []
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.is_stationary = False
        self.velocity = 0.0
        self.current_bbox = None
    
    def update(self, position: Tuple[float, float], timestamp: float, bbox: Optional[Tuple[float, float, float, float]] = None, pose: Optional[Dict] = None):
        """Update tracker with new position and pose."""
        self.positions.append((position[0], position[1], timestamp))
        self.last_seen = timestamp
        if bbox:
            self.current_bbox = bbox
        
        if pose and pose.get("landmarks"):
            # Extract wrists (L:15, R:16)
            landmarks = pose["landmarks"]
            if len(landmarks) > 16:
                lw = landmarks[15]
                rw = landmarks[16]
                
                if lw.get("visibility", 0) > 0.3:
                    self.left_wrist_history.append((lw["x"], lw["y"], timestamp))
                if rw.get("visibility", 0) > 0.3:
                    self.right_wrist_history.append((rw["x"], rw["y"], timestamp))
                
        # Keep only last 30 positions (about 3 seconds at 10fps)
        if len(self.positions) > 30:
            self.positions = self.positions[-30:]
        
        if len(self.left_wrist_history) > 30:
            self.left_wrist_history = self.left_wrist_history[-30:]
        
        if len(self.right_wrist_history) > 30:
            self.right_wrist_history = self.right_wrist_history[-30:]
        
        # Calculate velocity if we have enough positions
        if len(self.positions) >= 2:
            self._calculate_velocity()
    
    def _calculate_velocity(self):
        """Calculate movement velocity (pixels per second)."""
        if len(self.positions) < 2:
            self.velocity = 0.0
            return
        
        # Use last 5 positions for velocity calculation
        recent = self.positions[-5:]
        if len(recent) < 2:
            return
        
        total_distance = 0.0
        for i in range(1, len(recent)):
            x1, y1, _ = recent[i - 1]
            x2, y2, _ = recent[i]
            total_distance += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        
        time_span = recent[-1][2] - recent[0][2]
        if time_span > 0:
            self.velocity = total_distance / time_span
        else:
            self.velocity = 0.0
    
    def get_stationary_time(self) -> float:
        """Get how long person has been relatively stationary."""
        if len(self.positions) < 2:
            return 0.0
        
        # Check if person has moved significantly in recent positions
        recent = self.positions[-10:]  # Last ~1 second
        if len(recent) < 2:
            return 0.0
        
        # Calculate total movement
        total_movement = 0.0
        for i in range(1, len(recent)):
            x1, y1, _ = recent[i - 1]
            x2, y2, _ = recent[i]
            total_movement += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        
        # If movement is minimal, calculate stationary time
        if total_movement < 30:  # Threshold in pixels
            # Find when stationarity started
            return self.last_seen - self.first_seen
        
        return 0.0
    
    def to_dict(self):
        """Convert tracker to dictionary format for aggression detection."""
        pos = self.positions[-1] if self.positions else (0, 0, 0)
        return {
            "id": self.track_id,
            "position": pos,
            "center": (pos[0], pos[1]),
            "velocity": self.velocity,
            "bbox": self.current_bbox,
            "left_wrist_history": self.left_wrist_history,
            "right_wrist_history": self.right_wrist_history,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen
        }


class EventEngine:
    """
    Analyzes detected persons for suspicious/unsafe behaviors.
    Sends alerts to administration for crowd gathering and other events.
    """
    
    # Thresholds (configurable)
    LOITERING_THRESHOLD_SECS = 300  # 5 minutes
    RUNNING_VELOCITY_THRESHOLD = 200  # pixels per second
    CROWD_PERSON_THRESHOLD = 3  # Alert when 3+ people detected
    CROWD_DISTANCE_THRESHOLD = 150  # Maximum distance between crowd members
    FALL_VERTICAL_RATIO_THRESHOLD = 0.5  # Height/Width ratio for fall detection
    POSE_CONFIDENCE_THRESHOLD = 0.4  # Lowered from 0.6 to handle occlusions
    
    # Alert cooldowns (prevent spam)
    CROWD_ALERT_COOLDOWN = 60.0  # seconds between crowd alerts
    
    def __init__(self):
        self._trackers: Dict[str, PersonTracker] = {}
        self._lock = threading.Lock()
        self._pose_history: Dict[str, List[Dict]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._last_crowd_alert_time = 0.0  # Track last crowd alert
    
    def analyze_frame(
        self,
        detections: List[Dict],
        poses: Optional[List[Dict]] = None,
        frame_shape: Optional[Tuple[int, int]] = None
    ) -> List[Dict]:
        """
        Analyze a frame for behavior events.
        
        Args:
            detections: List of YOLO detections with bbox and class
            poses: Optional list of pose data for each detection
            frame_shape: (height, width) of the frame
            
        Returns:
            List of detected events
        """
        events = []
        current_time = time.time()
        
        with self._lock:
            # Clean up old trackers periodically
            if current_time - self._last_cleanup > 10.0:
                self._cleanup_old_trackers(current_time)
                self._last_cleanup = current_time
            
            # Update trackers with new detections
            active_ids = set()
            for i, det in enumerate(detections):
                bbox = det.get("bbox", [])
                if len(bbox) < 4:
                    continue
                
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                # Check if track_id is already assigned (e.g. by SimpleTracker)
                external_track_id = det.get("track_id")
                
                if external_track_id:
                    # Use external ID directly
                    if external_track_id in self._trackers:
                        p = poses[i] if poses and i < len(poses) else None
                        self._trackers[external_track_id].update((center_x, center_y), current_time, bbox, p)
                        track_id = external_track_id
                    else:
                        # Register new tracker for this ID
                        self._trackers[external_track_id] = PersonTracker(external_track_id, (center_x, center_y), current_time)
                        self._trackers[external_track_id].current_bbox = bbox
                        track_id = external_track_id
                else:
                    # Internal tracking logic fallback
                    track_id = self._find_or_create_tracker(center_x, center_y, current_time, bbox)
                
                active_ids.add(track_id)
                
                # Store pose if available
                if poses and i < len(poses):
                    self._pose_history[track_id].append({
                        "pose": poses[i],
                        "bbox": bbox,
                        "timestamp": current_time
                    })
                    # Keep only recent pose history
                    if len(self._pose_history[track_id]) > 30:
                        self._pose_history[track_id] = self._pose_history[track_id][-30:]
            
            # 1. Loitering Detection
            for track_id, tracker in self._trackers.items():
                if track_id in active_ids:
                    stationary_time = tracker.get_stationary_time()
                    if stationary_time >= self.LOITERING_THRESHOLD_SECS:
                        # Only report loitering if it's sustained (temporal smoothing)
                        if tracker.last_seen - tracker.first_seen >= self.LOITERING_THRESHOLD_SECS:
                            events.append({
                                "type": "LOITERING",
                                "severity": "warning",
                                "title": "Person Loitering Detected",
                                "description": f"Individual has been stationary for {int(stationary_time / 60)} minutes.",
                                "track_id": track_id,
                                "duration_seconds": stationary_time
                            })
            
            # 2. Running Detection
            for track_id, tracker in self._trackers.items():
                if track_id in active_ids and tracker.velocity > self.RUNNING_VELOCITY_THRESHOLD:
                    events.append({
                        "type": "RUNNING",
                        "severity": "info",
                        "title": "Running Detected",
                        "description": "Fast movement detected in corridor.",
                        "track_id": track_id,
                        "velocity": tracker.velocity
                    })
            
            # 3. Crowd Detection - Alert administration when 3+ people detected
            person_count = len(detections)
            if person_count >= self.CROWD_PERSON_THRESHOLD:
                # Check cooldown to prevent alert spam
                if current_time - self._last_crowd_alert_time >= self.CROWD_ALERT_COOLDOWN:
                    # Check if people are clustered (indicates gathering)
                    centers = []
                    for det in detections:
                        bbox = det.get("bbox", [])
                        if len(bbox) >= 4:
                            centers.append(((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2))
                    
                    is_clustered = self._detect_clustering(centers) if len(centers) >= 2 else False
                    
                    # Generate crowd alert
                    severity = "high" if person_count >= 5 else "warning"
                    title = "Crowd Gathering Detected" if is_clustered else "High Foot Traffic Alert"
                    
                    events.append({
                        "type": "CROWD_ALERT",
                        "severity": severity,
                        "title": title,
                        "description": f"⚠️ {person_count} people detected in camera frame. Administration notified.",
                        "person_count": person_count,
                        "is_clustered": is_clustered,
                        "location": "Hospital Corridor"
                    })
                    
                    self._last_crowd_alert_time = current_time
            
            # 4. Fall Detection (using poses or bbox aspect ratio)
            for i, det in enumerate(detections):
                bbox = det.get("bbox", [])
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox
                    width = x2 - x1
                    height = y2 - y1
                    
                    if width > 0 and height / width < self.FALL_VERTICAL_RATIO_THRESHOLD:
                        # Person bbox is more horizontal than vertical - possible fall
                        events.append({
                            "type": "FALL_DETECTED",
                            "severity": "critical",
                            "title": "Possible Fall Detected",
                            "description": "Person may have fallen. Immediate attention required.",
                            "bbox": bbox
                        })
            
            # 5. Aggression/Fighting Detection
            active_trackers = [tracker for track_id, tracker in self._trackers.items() if track_id in active_ids]
            if len(active_trackers) >= 2:
                aggression_events = self._detect_aggression(active_trackers, current_time)
                events.extend(aggression_events)
        
        return events
    
    def _find_or_create_tracker(self, x: float, y: float, timestamp: float, bbox: Optional[Tuple[float, float, float, float]] = None) -> str:
        """Find existing tracker or create new one."""
        min_distance = float('inf')
        closest_id = None
        
        for track_id, tracker in self._trackers.items():
            if tracker.positions:
                last_x, last_y, last_t = tracker.positions[-1]
                # Only match if recent
                if timestamp - last_t < 1.0:
                    distance = math.sqrt((x - last_x) ** 2 + (y - last_y) ** 2)
                    if distance < min_distance and distance < 100:  # Max 100 pixels movement
                        min_distance = distance
                        closest_id = track_id
        
        if closest_id:
            self._trackers[closest_id].update((x, y), timestamp, bbox)
            return closest_id
        else:
            # Create new tracker
            new_id = f"person_{int(timestamp * 1000)}"
            self._trackers[new_id] = PersonTracker(new_id, (x, y), timestamp)
            self._trackers[new_id].current_bbox = bbox
            return new_id
    
    def _cleanup_old_trackers(self, current_time: float, max_age: float = 30.0):
        """Remove trackers that haven't been updated recently."""
        to_remove = []
        for track_id, tracker in self._trackers.items():
            if current_time - tracker.last_seen > max_age:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self._trackers[track_id]
            if track_id in self._pose_history:
                del self._pose_history[track_id]
    
    def _detect_clustering(self, centers: List[Tuple[float, float]]) -> bool:
        """Detect if people are clustered together."""
        if len(centers) < self.CROWD_PERSON_THRESHOLD:
            return False
        
        # Calculate average distance between all pairs
        total_distance = 0
        count = 0
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                distance = math.sqrt(
                    (centers[i][0] - centers[j][0]) ** 2 +
                    (centers[i][1] - centers[j][1]) ** 2
                )
                total_distance += distance
                count += 1
        
        if count > 0:
            avg_distance = total_distance / count
            return avg_distance < self.CROWD_DISTANCE_THRESHOLD
        
        return False
    
    def _detect_aggression(self, trackers: List[PersonTracker], current_time: float) -> List[Dict]:
        """Detect potential aggression using aggression_rules module."""
        events = []
        
        # Convert trackers to dictionary format for aggression detection
        tracks = [tracker.to_dict() for tracker in trackers]
        
        # Evaluate aggression only if posed landmarks are reliable
        for track in tracks:
            track_id = track["id"]
            pose_reliable = False
            
            if track_id in self._pose_history and self._pose_history[track_id]:
                latest_pose = self._pose_history[track_id][-1]["pose"]
                if latest_pose and latest_pose.get("landmarks"):
                    # Check logic: average visibility of key joints
                    v = [l.get("visibility", 0) for l in latest_pose["landmarks"]]
                    if v and (sum(v)/len(v)) > self.POSE_CONFIDENCE_THRESHOLD:
                        pose_reliable = True

            if not pose_reliable:
                continue

            # Find nearby trackers (excluding self)
            nearby = [t for t in tracks if t["id"] != track_id]
            
            # Evaluate aggression
            event = evaluate_aggression(track, nearby, current_time)
            if event:
                events.append(event)
        
        return events
    
    def update_thresholds(
        self,
        loitering_secs: Optional[int] = None,
        running_velocity: Optional[int] = None,
        crowd_count: Optional[int] = None
    ):
        """Update detection thresholds."""
        if loitering_secs is not None:
            self.LOITERING_THRESHOLD_SECS = loitering_secs
        if running_velocity is not None:
            self.RUNNING_VELOCITY_THRESHOLD = running_velocity
        if crowd_count is not None:
            self.CROWD_PERSON_THRESHOLD = crowd_count


# Global singleton instance
event_engine = EventEngine()