# app/services/processing.py
"""
COMPLETE PROCESSING PIPELINE for Hospital Corridor AI
Integrates: Person Detection + Vehicle Detection + Authorization + Rules Engine
"""

import asyncio
import cv2
import time
import uuid
import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
import numpy as np
import math

from app.services.camera import camera_stream
from client.yolo_detector import YOLODetector
from client.tracker.simple_tracker import SimpleTracker
from app.utils.preprocessing import preprocess_for_yolo
from app.models.pose_detector import PoseDetector
from app.broadcast import broadcaster
from app.models.clip_embedder import embedder
from app.db.qdrant_client import search_staff, search_staff_hybrid
from app.services.face_service import face_service
from app.services.event_engine import event_engine
from app.services.alerts_store import alert_store
from app.services.stats_service import stats_service
from app.services.vehicle_rules import evaluate_vehicle_rules, get_vehicle_type
from app.utils.zones import ZONES
from app.utils.geometry import point_in_zone





logger = logging.getLogger(__name__)

# -----------------------------------
# CONSTANTS & CONFIGURATION
# -----------------------------------
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# COCO Class IDs
PERSON_CLASS_ID = 0
VEHICLE_CLASS_IDS = {1, 2, 3, 5, 7, 9}  # bicycle, car, bike, bus, truck, ambulance
# Detection thresholds
PERSON_CONF_THRESHOLD = 0.5
VEHICLE_CONF_THRESHOLD = 0.35

# Timing constants
BEHAVIOR_CHECK_INTERVAL = 0.2
AUTH_CHECK_INTERVAL = 1.0  # seconds between auth checks
RE_AUTH_INTERVAL = 3.0    # Reduced from 10.0 for faster DB sync reactivity

# Alert cooldowns (seconds)
ALERT_COOLDOWN_PERSON = 30.0
ALERT_COOLDOWN_VEHICLE = 60.0
ALERT_COOLDOWN_BEHAVIOR = 30.0

# Hospital zones configuration
HOSPITAL_ZONES = {
    "main_corridor": {"x": 0, "y": 0, "width": 1920, "height": 1080},
    "emergency_entrance": {"x": 100, "y": 100, "width": 500, "height": 400},
    "restricted_area": {"x": 600, "y": 300, "width": 300, "height": 300}
}

# -----------------------------------
# AUTHORIZATION FUNCTIONS
# -----------------------------------

# PRODUCTION THRESHOLDS - Set higher to prevent false positives
# ArcFace: 0.55+ for reliable match (0.70+ is very confident)
# CLIP: 0.90+ for reliable match (not a face model, general similarity)
ARCFACE_AUTH_THRESHOLD = 0.55
CLIP_AUTH_THRESHOLD = 0.90

def authorize_person_hybrid(clip_embedding: np.ndarray, arcface_embedding: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """
    Check if a person is authorized using hybrid identification (CLIP retrieval + ArcFace verification).
    Uses strict thresholds to prevent false positive matches.
    """
    results = search_staff_hybrid(clip_embedding, arcface_embedding, limit=5)
    
    if not results:
        return {
            "authorized": False,
            "score": 0,
            "name": "Unauthorized",
            "role": None,
            "department": None
        }
    
    top = results[0]
    
    arcface_score = top.get("arcface_score", 0)
    clip_score = top.get("clip_score", 0)
    
    is_authorized = False
    final_score = clip_score
    match_method = "none"
    
    # STRICT AUTHORIZATION LOGIC:
    # 1. If we have ArcFace embedding, use it as PRIMARY verification
    # 2. Require high threshold to prevent false positives
    # 3. Also check that CLIP score is reasonable (basic sanity check)
    
    if arcface_embedding is not None and arcface_score > 0:
        # We have face embedding - use strict ArcFace verification
        if arcface_score >= ARCFACE_AUTH_THRESHOLD:
            # Additional sanity check: CLIP shouldn't be too low
            if clip_score >= 0.75:  # Basic sanity threshold
                is_authorized = True
                final_score = arcface_score
                match_method = "arcface"
    else:
        # No face detected (profile/occluded) - use CLIP with VERY strict threshold
        if clip_score >= CLIP_AUTH_THRESHOLD:
            is_authorized = True
            final_score = clip_score
            match_method = "clip"
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Auth check: clip={clip_score:.3f}, arcface={arcface_score:.3f}, "
                 f"method={match_method}, authorized={is_authorized}")

    if is_authorized and top.get("authorized"):
        return {
            "authorized": True,
            "score": final_score,
            "name": top.get("name", "Staff"),
            "role": top.get("role", "Employee"),
            "department": top.get("department", "Hospital")
        }
    
    return {
        "authorized": False,
        "score": final_score,
        "name": "Unauthorized",
        "role": None,
        "department": None
    }

def is_authorized_vehicle(vehicle_type: str, zone: str) -> bool:
    """
    Check if vehicle is authorized in specific zone
    """
    # Ambulance always allowed in emergency zones
    if vehicle_type == "ambulance" and zone == "emergency_entrance":
        return True
    
    # Delivery trucks only in loading zones
    if vehicle_type == "truck" and zone == "loading_zone":
        return True
    
    # Cars not allowed in corridors
    if vehicle_type == "car" and "corridor" in zone:
        return False
    
    return False

# -----------------------------------
# HELPER FUNCTIONS
# -----------------------------------
def get_zone_for_position(x: int, y: int, frame_shape: Tuple[int, int]) -> str:
    """
    Determine which hospital zone a position is in
    """
    frame_height, frame_width = frame_shape[:2]
    
    # Simple zone detection (can be enhanced with actual coordinates)
    if x < frame_width * 0.3:
        return "left_corridor"
    elif x > frame_width * 0.7:
        return "right_corridor"
    elif y < frame_height * 0.3:
        return "emergency_entrance"
    else:
        return "main_corridor"

def calculate_speed(track_id: int, bbox: List[int], timestamp: float, 
                   track_history: Dict[int, List[Tuple[List[int], float]]]) -> float:
    """
    Calculate approximate speed in pixels per second
    """
    if track_id not in track_history:
        track_history[track_id] = []
    
    # Add current position to history
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    track_history[track_id].append(([center_x, center_y], timestamp))
    
    # Keep only last 5 positions
    if len(track_history[track_id]) > 5:
        track_history[track_id].pop(0)
    
    # Calculate speed if we have at least 2 positions
    if len(track_history[track_id]) >= 2:
        positions = track_history[track_id]
        total_distance = 0
        total_time = 0
        
        for i in range(1, len(positions)):
            (x1, y1), t1 = positions[i-1]
            (x2, y2), t2 = positions[i]
            distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            time_diff = t2 - t1
            
            total_distance += distance
            total_time += time_diff
        
        if total_time > 0:
            return total_distance / total_time
    
    return 0.0

# -----------------------------------
# MAIN PROCESSING SERVICE
# -----------------------------------
class ProcessingService:
    """
    Complete processing pipeline with:
    1. Person detection + authorization
    2. Vehicle detection + rules enforcement
    3. Behavior analysis
    4. Alert generation
    5. Real-time broadcasting
    """
    
    def __init__(self):
        # Models
        self.yolo = None
        self.pose = None
        self.running = False
        
        # Trackers
        self.person_tracker = SimpleTracker(max_distance=150, max_age=30)
        self.vehicle_tracker = SimpleTracker(max_distance=200, max_age=60)
        
        # State management
        self.person_states = {}  # track_id -> person info
        self.vehicle_states = {}  # track_id -> vehicle info
        self.stranger_embeddings = []  # known unauthorized persons
        
        # History for speed calculation
        self.person_positions = {}
        self.vehicle_positions = {}
        
        # Alert cooldowns
        self.alert_cooldowns = {
            "person": {},
            "vehicle": {},
            "behavior": {}
        }
        
        # Performance tracking
        self.frame_count = 0
        self.processing_times = []
        self.last_behavior_check = 0.0
        self.latest_annotated_frame = None
        self.frame_skip = 1  # Process every frame by default
        
        # Statistics
        self.stats = {
            "persons_detected": 0,
            "vehicles_detected": 0,
            "alerts_generated": 0,
            "authorized_count": 0,
            "unauthorized_count": 0
        }
        
        # UI Display helpers
        self.next_person_id = 1
        self.person_id_map = {} # track_uuid -> sequential_id
    
    # -----------------------------------
    # START/STOP METHODS
    # -----------------------------------
    async def start(self) -> None:
        """Start the processing pipeline asynchronously"""
        if self.running:
            return
        
        # Set running flag immediately so the system health check shows we are starting
        self.running = True
        logger.info("🚀 Starting Hospital Corridor AI Processing Service (Background)")
        
        # Start background initialization and loop
        asyncio.create_task(self._initialize_and_run())

    async def _initialize_and_run(self) -> None:
        """Background task to load models and start the loop"""
        try:
            logger.info("📡 Initializing AI models (YOLO, Pose)...")
            
            # Initialize models effectively in background
            if self.yolo is None:
                self.yolo = await asyncio.to_thread(YOLODetector)
            if self.pose is None:
                self.pose = await asyncio.to_thread(PoseDetector)
            
            # Start camera stream
            logger.info(f" Starting camera stream from: {camera_stream.src}")
            camera_stream.start()
            
            logger.info(" Models loaded and camera started. Entering main loop.")
            await self._main_loop()
            
        except Exception as e:
            self.running = False
            logger.error(f"❌ Failed to initialize or run processing service: {e}")
            # Broadcast failure if needed
    
    def stop(self) -> None:
        """Stop the processing pipeline"""
        self.running = False
        camera_stream.stop()
        
        if self.pose:
            self.pose.close()
        
        # Save statistics
        self._save_statistics()
        
        logger.info(" Processing service stopped")
    
    # -----------------------------------
    # MAIN PROCESSING LOOP
    # -----------------------------------
    async def _main_loop(self) -> None:
        """
        Main processing loop following the complete workflow:
        1. Frame capture
        2. Preprocessing
        3. YOLO detection
        4. Person/Vehicle separation
        5. Tracking
        6. Authorization (Person)
        7. Rules checking (Vehicle)
        8. Behavior analysis
        9. Alert generation
        10. Visualization
        """
        while self.running:
            try:
                start_time = time.time()
                
                # STEP 1: Get frame
                frame = camera_stream.get_frame()
                if frame is None:
                    await asyncio.sleep(0.05)
                    continue
                
                self.frame_count += 1
                if self.frame_count % self.frame_skip != 0:
                    await asyncio.sleep(0.01)
                    continue
                
                # STEP 2: Preprocessing
                processed_frame, ratio, (dw, dh) = await asyncio.to_thread(
                    preprocess_for_yolo, frame, (640, 640)
                )
                
                # STEP 3: YOLO Detection
                raw_detections = await asyncio.to_thread(self.yolo.detect, processed_frame)
                
                # STEP 4: Map detections to original frame
                detections = self._map_detections_to_original(
                    raw_detections, ratio, dw, dh, frame.shape
                )
                
                # STEP 5: Separate persons and vehicles
                persons, vehicles = self._separate_detections(detections)
                
                # STEP 6: Tracking
                tracked_persons = self.person_tracker.update(persons, time.time())
                tracked_vehicles = self.vehicle_tracker.update(vehicles, time.time())
                
                # STEP 7: Update states
                person_states = self._update_person_states(tracked_persons)
                vehicle_states = self._update_vehicle_states(tracked_vehicles)
                
                # STEP 8: Process persons (authorization)
                await self._process_persons(frame, person_states)
                
                # STEP 9: Process vehicles (rules)
                await self._process_vehicles(frame, vehicle_states)
                
                # STEP 10: Behavior analysis (Optimize frequency)
                current_time = time.time()
                if current_time - self.last_behavior_check >= BEHAVIOR_CHECK_INTERVAL:
                    # Run on a sample of frames instead of every frame to save CPU
                    await self._analyze_behaviors(frame, person_states)
                    self.last_behavior_check = current_time
                
                # STEP 11: Update statistics
                self._update_statistics(person_states, vehicle_states)
                
                # STEP 12: Annotate frame (Offload to thread as it can be slow)
                await asyncio.to_thread(self._annotate_frame, frame, person_states, vehicle_states)
                
                # STEP 13: Performance monitoring
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)
                if len(self.processing_times) > 100:
                    self.processing_times.pop(0)
                
                # Maintain target FPS
                await asyncio.sleep(max(0.001, 0.033 - processing_time))  # ~30 FPS
                
            except Exception as e:
                logger.error(f"❌ Error in processing loop: {e}")
                await asyncio.sleep(1.0)
    
    # -----------------------------------
    # CORE PROCESSING METHODS
    # -----------------------------------
    def _map_detections_to_original(self, detections: List[Dict], ratio: float, 
                                   dw: int, dh: int, frame_shape: Tuple) -> List[Dict]:
        """Map detections from processed frame to original frame coordinates"""
        mapped = []
        frame_height, frame_width = frame_shape[:2]
        
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            
            # Reverse preprocessing
            x1 = (x1 - dw) / ratio
            x2 = (x2 - dw) / ratio
            y1 = (y1 - dh) / ratio
            y2 = (y2 - dh) / ratio
            
            # Clamp to frame boundaries
            x1 = max(0, min(int(x1), frame_width))
            x2 = max(0, min(int(x2), frame_width))
            y1 = max(0, min(int(y1), frame_height))
            y2 = max(0, min(int(y2), frame_height))
            
            # Skip invalid boxes
            if x2 <= x1 or y2 <= y1:
                continue
            
            det_copy = det.copy()
            det_copy["bbox"] = [x1, y1, x2, y2]
            mapped.append(det_copy)
        
        return mapped
    
    def _separate_detections(self, detections: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Separate detections into persons and vehicles"""
        persons = []
        vehicles = []
        
        for det in detections:
            class_id = det["class"]
            confidence = det["conf"]
            
            if class_id == PERSON_CLASS_ID and confidence >= PERSON_CONF_THRESHOLD:
                persons.append(det)
            elif class_id in VEHICLE_CLASS_IDS and confidence >= VEHICLE_CONF_THRESHOLD:
                vehicles.append(det)
        
        return persons, vehicles
    
    def _update_person_states(self, tracked_persons: List[Dict]) -> List[Dict]:
        """Update person tracking states"""
        current_time = time.time()
        updated_states = []
        active_ids = set()
        
        for track in tracked_persons:
            track_id = track["track_id"]
            active_ids.add(track_id)
            
            # Initialize new track
            if track_id not in self.person_states:
                if track_id not in self.person_id_map:
                    self.person_id_map[track_id] = self.next_person_id
                    self.next_person_id += 1
                
                display_id = self.person_id_map[track_id]
                self.person_states[track_id] = {
                    "id": track_id,
                    "display_id": display_id,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "authorized": None,  # None = scanning, True = authorized, False = unauthorized
                    "name": "Scanning...",
                    "role": None,
                    "department": None,
                    "embedding": None,
                    "last_auth_check": 0,
                    "snapshots_taken": 0,
                    "alert_cooldown": 0,
                    "is_returning_stranger": False
                }
            
            # Update existing track
            state = self.person_states[track_id]
            state.update({
                "last_seen": current_time,
                "bbox": track["bbox"],
                "confidence": track.get("conf", 0)
            })
            
            # Update state with tracking data directly to avoid copy issues
            state.update(track)
            updated_states.append(state)
        
        # Clean up old tracks
        for track_id in list(self.person_states.keys()):
            if track_id not in active_ids:
                # Keep for a while in case of temporary occlusion
                if current_time - self.person_states[track_id]["last_seen"] > 5.0:
                    del self.person_states[track_id]
        
        return updated_states
    
    def _update_vehicle_states(self, tracked_vehicles: List[Dict]) -> List[Dict]:
        """Update vehicle tracking states"""
        current_time = time.time()
        updated_states = []
        active_ids = set()
        
        for track in tracked_vehicles:
            track_id = track["track_id"]
            active_ids.add(track_id)
            
            # Initialize new track
            if track_id not in self.vehicle_states:
                vehicle_type = get_vehicle_type(track["class"])
                self.vehicle_states[track_id] = {
                    "id": track_id,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "type": vehicle_type,
                    "alerts_generated": 0,
                    "last_alert_time": 0,
                    "speed": 0.0
                }
            
            # Update existing track
            state = self.vehicle_states[track_id]
            state.update({
                "last_seen": current_time,
                "bbox": track["bbox"],
                "confidence": track.get("conf", 0),
                "class": track["class"]
            })
            
            # Update state with tracking data directly
            state.update(track)
            updated_states.append(state)
        
        # Clean up old tracks
        for track_id in list(self.vehicle_states.keys()):
            if track_id not in active_ids:
                if current_time - self.vehicle_states[track_id]["last_seen"] > 10.0:
                    del self.vehicle_states[track_id]
        
        return updated_states
    
    # -----------------------------------
    # PERSON PROCESSING
    # -----------------------------------
    async def _process_persons(self, frame: np.ndarray, persons: List[Dict]) -> None:
        """Process person detections: authorization, alerts, etc."""
        current_time = time.time()
        
        tasks = []
        for person in persons:
            # Check if authorization is needed
            needs_auth = False
            
            if person["authorized"] is None:  # Instant auth check on first detection
                needs_auth = True
            elif person["authorized"] is False:  # Unauthorized - periodic recheck
                needs_auth = current_time - person["last_auth_check"] >= 2.0  # Faster recheck for unauthorized (was 5.0s)
            else:  # Authorized - less frequent recheck
                needs_auth = current_time - person["last_auth_check"] >= RE_AUTH_INTERVAL * 2
            
            if needs_auth:
                tasks.append(self._check_authorization(frame, person, current_time))
            
            # Check for suspicious behavior
            tasks.append(self._check_person_behavior(frame, person, current_time))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _check_authorization(self, frame: np.ndarray, person: Dict, current_time: float) -> None:
        """Check if person is authorized staff"""
        person["last_auth_check"] = current_time
        
        # Extract person crop
        x1, y1, x2, y2 = map(int, person["bbox"])
        crop = frame[y1:y2, x1:x2]
        
        if crop.size == 0 or crop.shape[0] < 50 or crop.shape[1] < 50:
            return  # Too small for reliable identification
        
        try:
            # Step 1: CLIP embedding for retrieval
            pil_image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            clip_embedding = await asyncio.to_thread(embedder.image_embedding, pil_image)
            
            # Step 2: ArcFace embedding for high-precision verification
            face_details = await asyncio.to_thread(face_service.get_face_details, crop)
            
            # IMPORTANT: Only use ArcFace embedding if it's from real InsightFace, not fallback
            arcface_embedding = None
            if face_details and not face_details.get("fallback", False):
                # Real ArcFace embedding from InsightFace
                arcface_embedding = face_details["embedding"]
            elif face_details and face_details.get("fallback", False):
                # Fallback embedding (OpenCV histogram) - DO NOT use for authorization
                # These give unreliable matches
                logger.debug(f"Person {person['id']}: Using fallback face detection - skipping ArcFace")
            
            # Step 3: Hybrid search and verification (Offload to thread)
            auth_result = await asyncio.to_thread(authorize_person_hybrid, clip_embedding, arcface_embedding)
            
            # Update person state
            previous_status = person["authorized"]
            person["authorized"] = auth_result["authorized"]
            person["embedding"] = clip_embedding
            person["auth_score"] = auth_result.get("score", 0)
            
            if auth_result["authorized"]:
                # Format: Authorized Name Role
                person["name"] = f"{auth_result['name']} ({auth_result['role']})"
                person["role"] = auth_result["role"]
                person["department"] = auth_result.get("department")
                
                # Log authorization event
                if previous_status is not True:
                    logger.info(f" Person {person['id']} authorized: {person['name']}")
                    await asyncio.to_thread(stats_service.log_event, "STAFF_AUTHORIZED", {
                        "person_id": person["id"],
                        "name": person["name"],
                        "role": person["role"],
                        "confidence": auth_result["score"]
                    })
            else:
                # Check if this is a known stranger
                is_known_stranger = False
                for stranger in self.stranger_embeddings:
                    if np.dot(clip_embedding, stranger["embedding"]) > 0.85:  # High similarity
                        is_known_stranger = True
                        person["is_returning_stranger"] = True
                        stranger["timestamp"] = current_time
                        break
                
                if not is_known_stranger:
                    self.stranger_embeddings.append({
                        "embedding": clip_embedding,
                        "timestamp": current_time
                    })
                    # Keep only recent strangers
                    self.stranger_embeddings = [
                        s for s in self.stranger_embeddings 
                        if current_time - s["timestamp"] < 3600  # 1 hour
                    ]
                
                # Determine label
                display_id = person.get("display_id", "?")
                if person.get("is_returning_stranger"):
                    person["name"] = f"Unknown {display_id} (Returning)"
                else:
                    person["name"] = f"Unknown {display_id}"
                
                # Generate alert for new unauthorized person
                if previous_status is not False and not person.get("is_returning_stranger"):
                    if current_time - person["first_seen"] >= 0.5:  # Reduced grace period for instant detection
                        await self._generate_person_alert(frame, person, "UNAUTHORIZED_PERSON")
        
        except Exception as e:
            logger.error(f"❌ Authorization error for person {person['id']}: {e}")
    
    async def _check_person_behavior(self, frame: np.ndarray, person: Dict, current_time: float) -> None:
        """Check for suspicious person behavior"""
        # Calculate speed
        speed = calculate_speed(person["id"], person["bbox"], current_time, self.person_positions)
        
        # Check for running (high speed)
        if speed > 50.0:  # pixels per second threshold
            if current_time - person.get("last_behavior_alert", 0) > ALERT_COOLDOWN_BEHAVIOR:
                await self._generate_person_alert(frame, person, "RUNNING_DETECTED")
                person["last_behavior_alert"] = current_time
        
        # Check for loitering (staying in one area too long)
        zone = get_zone_for_position(
            (person["bbox"][0] + person["bbox"][2]) / 2,
            (person["bbox"][1] + person["bbox"][3]) / 2,
            frame.shape
        )
        
        if zone == "restricted_area" and person["authorized"] is False:
            if current_time - person.get("last_zone_alert", 0) > ALERT_COOLDOWN_BEHAVIOR:
                await self._generate_person_alert(frame, person, "RESTRICTED_AREA_ENTRY")
                person["last_zone_alert"] = current_time
    
    # -----------------------------------
    # VEHICLE PROCESSING
    # -----------------------------------
    async def _process_vehicles(self, frame: np.ndarray, vehicles: List[Dict]) -> None:
        """Process vehicle detections using rules engine"""
        current_time = time.time()
        
        for vehicle in vehicles:
            # Determine vehicle zone
            center_x = (vehicle["bbox"][0] + vehicle["bbox"][2]) / 2
            center_y = (vehicle["bbox"][1] + vehicle["bbox"][3]) / 2
            zone = get_zone_for_position(center_x, center_y, frame.shape)
            
            # Update speed tracking
            speed = calculate_speed(vehicle["id"], vehicle["bbox"], current_time, self.vehicle_positions)
            vehicle["speed"] = speed  # Store speed in the vehicle object for alerts

            # Use vehicle_rules.py for rule evaluation
            vehicle_payload = {
                "id": vehicle["id"],
                "class": vehicle["class"],
                "conf": vehicle.get("confidence", 0) or vehicle.get("conf", 0),
                "bbox": vehicle["bbox"],
                "history": self.vehicle_positions.get(vehicle["id"], []),
                "speed": speed
            }

            # evaluate_vehicle_rules returns a list of events
            rules_events = evaluate_vehicle_rules(vehicle_payload, frame.shape)
            
            for event in rules_events:
                # Check cooldown per event type
                event_type = event["type"]
                vehicle_id = vehicle["id"]
                
                if vehicle_id not in self.alert_cooldowns["vehicle"]:
                    self.alert_cooldowns["vehicle"][vehicle_id] = {}
                
                last_alert = self.alert_cooldowns["vehicle"][vehicle_id].get(event_type, 0)
                
                if current_time - last_alert >= ALERT_COOLDOWN_VEHICLE:
                    await self._generate_vehicle_alert(frame, vehicle, event)
                    self.alert_cooldowns["vehicle"][vehicle_id][event_type] = current_time
            # Cleanup: removed old/broken logic

                    
    
    # -----------------------------------
    # BEHAVIOR ANALYSIS
    # -----------------------------------
    async def _analyze_behaviors(self, frame: np.ndarray, persons: List[Dict]) -> None:
        """Analyze behaviors using event engine"""
        try:
            # Prepare detections and capture pose tasks
            detections = []
            pose_tasks = []
            
            for person in persons:
                # Create detection dict
                det = {
                    "bbox": person["bbox"],
                    "confidence": person.get("confidence", 0),
                    "track_id": person["id"]
                }
                detections.append(det)
                
                # Extract pose parallel task
                x1, y1, x2, y2 = map(int, person["bbox"])
                crop = frame[y1:y2, x1:x2]
                
                if crop.size > 0:
                    # Offload each detection to its own thread task
                    pose_tasks.append(asyncio.to_thread(
                        self.pose.detect, cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    ))
                else:
                    pose_tasks.append(asyncio.sleep(0, result=None))
            
            # Execute all pose detections in parallel
            poses = await asyncio.gather(*pose_tasks)
            
            # Run event engine
            events = event_engine.analyze_frame(
                detections=detections,
                poses=poses,
                frame_shape=frame.shape[:2]
            )
            
            # Process events
            for event in events:
                # Mark person as aggressive if detected
                event_type = event.get("type")
                if event_type in ["AGGRESSIVE_BEHAVIOR", "FIGHT_DETECTED"]:
                    track_id = event.get("track_id")
                    if track_id in self.person_states:
                        self.person_states[track_id]["is_aggressive"] = True
                        self.person_states[track_id]["last_aggression_time"] = time.time()
                
                await self._generate_behavior_alert(frame, event)
                
        except Exception as e:
            logger.error(f"❌ Behavior analysis error: {e}")
    
    # -----------------------------------
    # ALERT GENERATION
    # -----------------------------------
    async def _generate_person_alert(self, frame: np.ndarray, person: Dict, alert_type: str) -> None:
        """Generate alert for person-related events"""
        snapshot_id = str(uuid.uuid4())
        snapshot_path = os.path.join(SNAPSHOT_DIR, f"{snapshot_id}.jpg")
        
        # Save snapshot in thread
        await asyncio.to_thread(cv2.imwrite, snapshot_path, frame)
        
        alert_data = {
            "id": snapshot_id,
            "type": alert_type,
            "severity": "high" if alert_type == "UNAUTHORIZED_PERSON" else "medium",
            "title": self._get_alert_title(alert_type),
            "description": self._get_alert_description(alert_type, person),
            "location": "Hospital Corridor",
            "confidence": float(person.get("confidence", 0)),
            "snapshot": f"/snapshots/{snapshot_id}.jpg",
            "timestamp": time.time(),
            "person_id": person["id"],
            "person_name": person.get("name", "Unknown"),
            "person_role": person.get("role", "Unknown")
        }
        
        # Store and broadcast alert
        stored_alert = alert_store.add_alert(alert_data)
        await broadcaster.broadcast_json(stored_alert)
        
        self.stats["alerts_generated"] += 1
        logger.warning(f"🚨 Person Alert: {alert_type} - {person['name']}")
    
    async def _generate_vehicle_alert(self, frame: np.ndarray, vehicle: Dict, rules_result: Dict) -> None:
        """Generate alert for vehicle-related events"""
        snapshot_id = str(uuid.uuid4())
        snapshot_path = os.path.join(SNAPSHOT_DIR, f"{snapshot_id}.jpg")
        
        # Save snapshot in thread
        await asyncio.to_thread(cv2.imwrite, snapshot_path, frame)
        
        alert_data = {
            "id": snapshot_id,
            "type": rules_result.get("type", "VEHICLE_ALERT"),
            "severity": rules_result.get("severity", "medium"),
            "title": rules_result.get("title", "Vehicle Alert"),
            "description": rules_result.get("description", "Vehicle violation detected"),
            "location": "Hospital Corridor",
            "vehicle_type": vehicle.get("type", "Unknown"),
            "vehicle_speed": vehicle.get("speed", 0),
            "snapshot": f"/snapshots/{snapshot_id}.jpg",
            "timestamp": time.time(),
            "vehicle_id": vehicle["id"]
        }
        
        # Store and broadcast alert
        stored_alert = alert_store.add_alert(alert_data)
        await broadcaster.broadcast_json(stored_alert)
        
        self.stats["alerts_generated"] += 1
        logger.warning(f"🚨 Vehicle Alert: {rules_result.get('type', 'UNKNOWN')}")
    
    async def _generate_behavior_alert(self, frame: np.ndarray, event: Dict) -> None:
        """Generate alert for behavior events"""
        snapshot_id = str(uuid.uuid4())
        snapshot_path = os.path.join(SNAPSHOT_DIR, f"{snapshot_id}.jpg")
        
        # Save snapshot in thread
        await asyncio.to_thread(cv2.imwrite, snapshot_path, frame)
        
        alert_data = {
            "id": snapshot_id,
            "type": event.get("type", "BEHAVIOR_ALERT"),
            "severity": event.get("severity", "medium"),
            "title": event.get("title", "Behavior Alert"),
            "description": event.get("description", "Suspicious behavior detected"),
            "location": "Hospital Corridor",
            "snapshot": f"/snapshots/{snapshot_id}.jpg",
            "timestamp": time.time(),
            "behavior_data": event
        }
        
        # Store and broadcast alert
        stored_alert = alert_store.add_alert(alert_data)
        await broadcaster.broadcast_json(stored_alert)
        
        self.stats["alerts_generated"] += 1
        logger.warning(f"🚨 Behavior Alert: {event.get('type', 'UNKNOWN')}")
    
    def _get_alert_title(self, alert_type: str) -> str:
        """Get human-readable alert title"""
        titles = {
            "UNAUTHORIZED_PERSON": "Unauthorized Person Detected",
            "RUNNING_DETECTED": "Running Detected in Corridor",
            "RESTRICTED_AREA_ENTRY": "Restricted Area Entry",
            "FALL_DETECTED": "Person Fall Detected",
            "LOITERING": "Suspicious Loitering Detected"
        }
        return titles.get(alert_type, "Security Alert")
    
    def _get_alert_description(self, alert_type: str, person: Dict) -> str:
        """Get alert description"""
        name = person.get("name", "Unknown")
        role = person.get("role", "")
        role_str = f" ({role})" if role else ""
        
        descriptions = {
            "UNAUTHORIZED_PERSON": f"Unauthorized person detected in hospital corridor. Person ID: {str(person['id'])[:4]}",
            "RUNNING_DETECTED": f"Person detected running in corridor. Person: {name}{role_str}",
            "RESTRICTED_AREA_ENTRY": f"Unauthorized entry into restricted area. Person: {name}{role_str}",
            "FALL_DETECTED": f"Potential fall detected for {name}{role_str}. Immediate assistance may be required.",
            "LOITERING": f"Suspicious loitering behavior detected. Person: {name}{role_str}"
        }
        return descriptions.get(alert_type, "Security event detected")
    
    # -----------------------------------
    # VISUALIZATION
    # -----------------------------------
    def _annotate_frame(self, frame: np.ndarray, persons: List[Dict], vehicles: List[Dict]) -> None:
        """Annotate frame with bounding boxes and labels"""
        annotated = frame.copy()
        
        # Draw persons
        for person in persons:
            x1, y1, x2, y2 = map(int, person["bbox"])
            
            # Choose color and label based on authorization
            if person["authorized"] is True:
                color = (0, 255, 0)    # Green - Authorized
                name = person.get('name', 'Staff')
                role = person.get('role', '')
                score = person.get('auth_score', 0)
                label = f"AUTHORIZED ID:{str(person['id'])[:4]} {name}"
                if role:
                    label += f" ({role})"
                if score > 0:
                    label += f" {score:.2f}"
            elif person["authorized"] is False:
                color = (0, 0, 255)    # Red - Unauthorized
                score = person.get('auth_score', 0)
                label = f"UNAUTHORIZED ID:{str(person['id'])[:4]}"
                if score > 0:
                    label += f" {score:.2f}"
            else:
                # Still scanning - Yellow
                color = (0, 255, 255)
                label = f"SCANNING ID:{str(person['id'])[:4]}"
            
            # Highlight if aggressive
            is_aggressive = person.get("is_aggressive", False)
            if is_aggressive:
                # Check for aggression timeout (reset after 5 seconds of no aggression)
                if time.time() - person.get("last_aggression_time", 0) > 5.0:
                    person["is_aggressive"] = False
                else:
                    color = (0, 0, 255) # Keep Red or use Pulsing Red if we had a timer
                    label = f" AGGRESSIVE  {label}"
                    # Make box thicker
                    thickness = 4
                
            if not is_aggressive:
                thickness = 2
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label background
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                annotated, 
                (x1, y1 - text_height - 10), 
                (x1 + text_width, y1), 
                color, 
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated, 
                label, 
                (x1, y1 - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                (255, 255, 255), 
                2
            )
        
        # Draw vehicles
        for vehicle in vehicles:
            x1, y1, x2, y2 = map(int, vehicle["bbox"])
            color = (255, 128, 0)  # Orange for vehicles
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{vehicle.get('type', 'Vehicle')} ID:{vehicle['id']}"
            cv2.putText(
                annotated, 
                label, 
                (x1, y1 - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                color, 
                2
            )
            
            # Draw speed if available
            if vehicle.get("speed", 0) > 0:
                speed_text = f"Speed: {vehicle['speed']:.1f}"
                cv2.putText(
                    annotated,
                    speed_text,
                    (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1
                )
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            annotated,
            timestamp,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        # Add statistics with crowd count
        crowd_count = len(persons)
        crowd_warning = " [CROWD]" if crowd_count >= 3 else ""
        stats_text = f"Persons: {crowd_count}{crowd_warning} | Vehicles: {len(vehicles)} | Alerts: {self.stats['alerts_generated']}"
        stats_color = (0, 255, 255) if crowd_count >= 3 else (255, 255, 255)  # Yellow for crowd warning
        cv2.putText(
            annotated,
            stats_text,
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            stats_color,
            2
        )
        
        self.latest_annotated_frame = annotated
    
    # -----------------------------------
    # STATISTICS & MONITORING
    # -----------------------------------
    def _update_statistics(self, persons: List[Dict], vehicles: List[Dict]) -> None:
        """Update system statistics"""
        self.stats["persons_detected"] = len(persons)
        self.stats["vehicles_detected"] = len(vehicles)
        
        # Count authorized vs unauthorized
        authorized_count = sum(1 for p in persons if p.get("authorized") is True)
        unauthorized_count = sum(1 for p in persons if p.get("authorized") is False)
        
        self.stats["authorized_count"] = authorized_count
        self.stats["unauthorized_count"] = unauthorized_count
        self.stats["crowd_count"] = len(persons)  # Explicit crowd count
        
        # Check for crowd alert threshold
        if len(persons) >= 5:
            self.stats["crowd_status"] = "crowded"
        else:
            self.stats["crowd_status"] = "normal"

    def _save_statistics(self) -> None:
        """Save performance and operational statistics to disk"""
        try:
            stats_path = "system_stats.json"
            avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            
            output = {
                "timestamp": datetime.now().isoformat(),
                "operational_stats": self.stats,
                "performance": {
                    "avg_processing_time": avg_processing_time,
                    "frame_count": self.frame_count
                }
            }
            
            with open(stats_path, "w") as f:
                json.dump(output, f, indent=4)
                
            logger.info(" System statistics saved")
        except Exception as e:
            logger.error(f"❌ Failed to save statistics: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Returns current operational statistics"""
        return self.stats

# -----------------------------------
# GLOBAL INSTANCE
# -----------------------------------
processor = ProcessingService()
