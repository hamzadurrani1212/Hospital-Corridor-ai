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


class PersonTracker:
    """Tracks individual person movements over time."""
    
    def __init__(self, track_id: str, initial_position: Tuple[float, float], timestamp: float):
        self.track_id = track_id
        self.positions: List[Tuple[float, float, float]] = [(initial_position[0], initial_position[1], timestamp)]
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.is_stationary = False
        self.velocity = 0.0
    
    def update(self, position: Tuple[float, float], timestamp: float):
        """Update tracker with new position."""
        self.positions.append((position[0], position[1], timestamp))
        self.last_seen = timestamp
        
        # Keep only last 30 positions (about 3 seconds at 10fps)
        if len(self.positions) > 30:
            self.positions = self.positions[-30:]
        
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


class EventEngine:
    """
    Analyzes detected persons for suspicious/unsafe behaviors.
    """
    
    # Thresholds (configurable)
    LOITERING_THRESHOLD_SECS = 300  # 5 minutes
    RUNNING_VELOCITY_THRESHOLD = 200  # pixels per second
    CROWD_PERSON_THRESHOLD = 8  # Number of people
    CROWD_DISTANCE_THRESHOLD = 150  # Maximum distance between crowd members
    FALL_VERTICAL_RATIO_THRESHOLD = 0.5  # Height/Width ratio for fall detection
    
    def __init__(self):
        self._trackers: Dict[str, PersonTracker] = {}
        self._lock = threading.Lock()
        self._pose_history: Dict[str, List[Dict]] = defaultdict(list)
        self._last_cleanup = time.time()
    
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
                        self._trackers[external_track_id].update((center_x, center_y), current_time)
                        track_id = external_track_id
                    else:
                        # Register new tracker for this ID
                        self._trackers[external_track_id] = PersonTracker(external_track_id, (center_x, center_y), current_time)
                        track_id = external_track_id
                else:
                    # Internal tracking logic fallback
                    track_id = self._find_or_create_tracker(center_x, center_y, current_time)
                
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
            
            # Analyze behaviors
            
            # 1. Loitering Detection
            for track_id, tracker in self._trackers.items():
                if track_id in active_ids:
                    stationary_time = tracker.get_stationary_time()
                    if stationary_time >= self.LOITERING_THRESHOLD_SECS:
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
            
            # 3. Crowd Detection
            if len(detections) >= self.CROWD_PERSON_THRESHOLD:
                # Check if people are clustered
                centers = []
                for det in detections:
                    bbox = det.get("bbox", [])
                    if len(bbox) >= 4:
                        centers.append(((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2))
                
                if self._detect_clustering(centers):
                    events.append({
                        "type": "CROWD_GATHERING",
                        "severity": "warning",
                        "title": "Unusual Crowd Gathering",
                        "description": f"Abnormal congregation of {len(detections)}+ individuals detected.",
                        "person_count": len(detections)
                    })
            
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
            
            # 5. Fighting Detection (aggressive motion between nearby persons)
            if len(detections) >= 2:
                fighting = self._detect_fighting(detections)
                if fighting:
                    events.append({
                        "type": "FIGHTING",
                        "severity": "critical",
                        "title": "Possible Altercation Detected",
                        "description": "Aggressive motion patterns detected between individuals.",
                        "person_count": len(fighting)
                    })
        
        return events
    
    def _find_or_create_tracker(self, x: float, y: float, timestamp: float) -> str:
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
            self._trackers[closest_id].update((x, y), timestamp)
            return closest_id
        else:
            # Create new tracker
            new_id = f"person_{int(timestamp * 1000)}"
            self._trackers[new_id] = PersonTracker(new_id, (x, y), timestamp)
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
    
    def _detect_fighting(self, detections: List[Dict]) -> List[str]:
        """Detect potential fighting by analyzing motion patterns."""
        fighting_ids = []
        
        # Get trackers with high velocity that are close to each other
        high_velocity_trackers = []
        for track_id, tracker in self._trackers.items():
            if tracker.velocity > 100:  # Moderate velocity threshold
                if tracker.positions:
                    high_velocity_trackers.append((track_id, tracker.positions[-1]))
        
        # Check if high-velocity trackers are close to each other
        for i in range(len(high_velocity_trackers)):
            for j in range(i + 1, len(high_velocity_trackers)):
                id1, pos1 = high_velocity_trackers[i]
                id2, pos2 = high_velocity_trackers[j]
                
                distance = math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)
                if distance < 100:  # Close proximity
                    fighting_ids.extend([id1, id2])
        
        return list(set(fighting_ids))
    
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
