# app/services/processing.py
"""
Main processing pipeline for Hospital Corridor AI.
Integrates YOLO detection, CLIP embeddings, Event Engine, and authorization.
"""

import asyncio
import cv2
import time
import uuid
import os
import logging
from PIL import Image
import numpy as np

from app.services.camera import camera_stream
# Updated import from client
from client.yolo_detector import YOLODetector
from client.tracker.simple_tracker import SimpleTracker
from app.utils.preprocessing import preprocess_for_yolo
from app.models.pose_detector import PoseDetector
from app.broadcast import broadcaster
from app.models.clip_embedder import embedder
from app.db.qdrant_client import search_staff
from app.services.event_engine import event_engine
from app.services.alerts_store import alert_store
from app.services.stats_service import stats_service

logger = logging.getLogger(__name__)

# -----------------------------------
# CONSTANTS
# -----------------------------------
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

PERSON_CLASS_ID = 0
CONF_THRESHOLD = 0.5
ALERT_COOLDOWN = 5.0
BEHAVIOR_CHECK_INTERVAL = 0.5

# Tracking Configuration
TRACK_MAX_DISTANCE = 150  # pixels
TRACK_TIMEOUT = 2.0       # seconds to keep a lost track
MAX_SNAPSHOTS_PER_PERSON = 3


# -----------------------------------
# AUTHORIZATION LOGIC
# -----------------------------------
def authorize_person(embedding):
    """
    Check if a person is authorized by comparing CLIP embedding
    against the Qdrant staff database.
    """
    match = search_staff(embedding)

    if match:
        return {
            "authorized": True,
            "person": match,
            "score": match.get("score", 0)
        }

    return {
        "authorized": False,
        "person": None,
        "score": None
    }


# -----------------------------------
# PERSON TRACKER
# -----------------------------------
# -----------------------------------
# PERSON TRACKER
# -----------------------------------
# Using client.tracker.simple_tracker.SimpleTracker



# -----------------------------------
# PROCESSING SERVICE
# -----------------------------------
class ProcessingService:
    """
    Main processing pipeline with Tracking and Optimization.
    """
    
    def __init__(self):
        self.yolo = None
        self.pose = None
        self.running = False
        
        # STEP 4: Person Tracking
        self.tracker = SimpleTracker()
        
        # Application State for Tracks (Auth, Name, etc.)
        self.track_states = {} # {track_id: {authorized, name, snapshots_taken...}}

        self.last_behavior_check = 0.0
        self._frame_count = 0
        
        # State for visual overlays
        self.latest_annotated_frame = None
        
        # Memory for Unauthorized People (to prevent re-snaping returing strangers)
        # List of {embedding: np.array, timestamp: float}
        self.known_strangers = []

    def start(self):
        """Start the processing pipeline."""
        if self.running:
            return

        logger.info("🚀 Initializing Processing Service...")
        
        # Initialize models
        self.yolo = YOLODetector()  # From client.yolo_detector
        self.pose = PoseDetector()
        
        self.running = True
        camera_stream.start()
        
        asyncio.create_task(self._loop())
        logger.info("✅ Processing loop started")

    def stop(self):
        """Stop the processing pipeline."""
        self.running = False
        camera_stream.stop()
        if self.pose:
            self.pose.close()
        logger.info("⏹️ Processing stopped")

    async def _loop(self):
        """Main processing loop explicitly following the 13-step workflow."""
        while self.running:
            # STEP 1: Camera Input (Video Stream)
            frame = camera_stream.get_frame()

            if frame is None:
                await asyncio.sleep(0.05)
                continue

            start = time.time()
            self._frame_count += 1
            
            # STEP 2: Frame Preprocessing
            # Explicitly use the requested component
            preprocessed_frame, ratio, (dw, dh) = preprocess_for_yolo(frame, target_size=(640, 640))

            # STEP 3: Person Detection (YOLO)
            # Pass preprocessed frame to model
            raw_detections = self.yolo.detect(preprocessed_frame)
            
            # Map coordinates back to original frame
            detections = []
            for d in raw_detections:
                x1, y1, x2, y2 = d["bbox"]
                
                # Reverse preprocessing (Letterbox removal)
                x1 = (x1 - dw) / ratio
                x2 = (x2 - dw) / ratio
                y1 = (y1 - dh) / ratio
                y2 = (y2 - dh) / ratio
                
                # Clamp to frame
                x1 = max(0, min(x1, frame.shape[1]))
                x2 = max(0, min(x2, frame.shape[1]))
                y1 = max(0, min(y1, frame.shape[0]))
                y2 = max(0, min(y2, frame.shape[0]))
                
                d["bbox"] = [x1, y1, x2, y2]
                detections.append(d)
            
            # Filter for Person class
            person_detections = [
                d for d in detections
                if d["class"] == PERSON_CLASS_ID and d["conf"] >= CONF_THRESHOLD
            ]
            
            # STEP 4: Person Tracking
            # SimpleTracker returns list of dicts with 'track_id' added
            tracked_items = self.tracker.update(person_detections, time.time())
            
            # Sync Track State (Maintain Auth status across frames)
            tracks = self._sync_track_state(tracked_items)
            
            # STEP 5 & 6, 7, 8: Crop, Embedding, Auth
            # Authorization (OPTMIZED: Only for new tracks)
            await self._check_authorization(frame, tracks)
            
            # STEP 11: Alert Creation (Snapshot)
            # Snapshots (OPTIMIZED: Max 3)
            await self._capture_snapshots(frame, tracks)

            # STEP 9: Event & Behavior Analysis
            now = time.time()
            if tracks and now - self.last_behavior_check >= BEHAVIOR_CHECK_INTERVAL:
                # Map tracks back to detection format for event engine
                # Event Engine expects detections but we specifically modified it to accept 'track_id'
                # so we can sustain the IDs from SimpleTracker.
                mapped_dets = []
                for t in tracks:
                    d = {
                        "bbox": t["bbox"], 
                        "conf": t.get("conf", 0.0), 
                        "track_id": t["id"] # Important: Pass ID
                    }
                    mapped_dets.append(d)

                # Step 9/10 Logic inside EventEngine
                await self._analyze_behavior(frame, mapped_dets)
                self.last_behavior_check = now
            
            # STEP 13: Frontend Dashboard (Visuals)
            self._annotate_frame(frame, tracks)

            elapsed = time.time() - start
            await asyncio.sleep(max(0.01, 0.05 - elapsed))

    def _sync_track_state(self, tracked_items):
        """
        Merge stateless tracker output with application state (auth, name, etc).
        """
        now = time.time()
        active_ids = set()
        enhanced_tracks = []
        
        for item in tracked_items:
            tid = item["track_id"]
            active_ids.add(tid)
            
            # Initialize state if new
            if tid not in self.track_states:
                self.track_states[tid] = {
                    "id": tid,
                    "first_seen": now,
                    "authorized": None,
                    "name": "Scanning...",
                    "role": None,
                    "snapshots_taken": 0,
                    "embedding": None,
                    "last_auth_check": 0
                }
            
            # Merge
            state = self.track_states[tid]
            # Create a rich object for downstream usage
            rich_track = item.copy()
            rich_track.update(state)
            # Ensure ID is top level
            rich_track["id"] = tid 
            
            enhanced_tracks.append(rich_track)
            
        # Cleanup old states
        for tid in list(self.track_states.keys()):
            if tid not in active_ids:
                # Optional: Keep history for a bit? No, SimpleTracker handles hysteresis
                # If SimpleTracker drops it, we drop it.
                # UNLESS SimpleTracker keeps it in 'history' but doesn't return it?
                # SimpleTracker returns currently matched/active tracks.
                # We can keep state for a few seconds to handle flicker if needed,
                # but SimpleTracker has TRACKER_MAX_AGE.
                del self.track_states[tid]
                
        return enhanced_tracks

    def _process_auth(self, crop):
        """Helper to run synchronous embedding logic in thread."""
        try:
            pil_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            start_embed = time.time()
            embedding = embedder.image_embedding(pil_img)
            return authorize_person(embedding), embedding
        except Exception as e:
            logger.error(f"Auth processing error: {e}")
            return {"authorized": False, "person": None, "score": 0}, None

    async def _check_authorization(self, frame, tracks):
        """
        Run Authorization on tracks.
        1. New tracks (authorized is None).
        2. Periodic re-check for authorized tracks (to handle deleted staff).
        """
        now = time.time()
        
        for track in tracks:
            # Condition 1: New Track (Scanning) - Throttle to 1.0s (More optimized)
            # needs_auth = (track["authorized"] is None) and (now - track.get("last_auth_check", 0) > 1.0)
            # DEBUG: Try faster check for new tracks to see if it works
            needs_auth = (track["authorized"] is None) and (now - track.get("last_auth_check", 0) > 0.5)
            
            # Condition 2: Period Re-check (every 10 seconds) - Scalable, less frequent
            if track.get("authorized") and (now - track.get("last_auth_check", 0) > 10.0):
                needs_auth = True

            # Condition 3: Unauthorized retry (slower, every 5s)
            if (track.get("authorized") is False) and (now - track.get("last_auth_check", 0) > 5.0):
                needs_auth = True

            if needs_auth:
                track["last_auth_check"] = now
                x1, y1, x2, y2 = map(int, track["bbox"])
                
                # OPTIMIZATION: Skip tiny crops (too far away for reliable ID)
                if (x2 - x1) < 50 or (y2 - y1) < 50:
                    continue
                    
                crop = frame[y1:y2, x1:x2]
                
                if crop.size == 0:
                    continue
                
                # SCALABILITY: Run heavy embedding in thread
                loop = asyncio.get_running_loop()
                auth, embedding = await loop.run_in_executor(None, self._process_auth, crop)
                
                # Check for State Change
                previous_status = track.get("authorized")
                current_status = auth["authorized"]
                
                # Update Track State
                track["authorized"] = current_status
                if embedding is not None:
                    track["embedding"] = embedding  # Keep embedding for re-ID
                
                if current_status:
                    track["name"] = auth["person"].get("name")
                    track["role"] = auth["person"].get("role")
                    
                    # Log Event only if status changed or it's new
                    if previous_status is not True:
                        logger.info(f"✅ Track {track['id']} Authorized: {track['name']}")
                        stats_service.log_event("AUTHORIZED_ENTRY", {
                            "name": track["name"],
                            "role": track["role"],
                            "track_id": track["id"],
                            "confidence": auth["score"]
                        })

                else:
                    # AUTH FAILED
                    
                    # RE-ID CHECK: Have we seen this unauthorized person before?
                    is_known_stranger = False
                    for stranger in self.known_strangers:
                        # Cosine similarity
                        sim = np.dot(embedding, stranger["embedding"]) 
                        # Use high threshold for re-id
                        if sim > 0.85:
                            is_known_stranger = True
                            # Restore their snapshot state (assume they had 3 if they are in this list)
                            track["snapshots_taken"] = 3 
                            track["is_returning_stranger"] = True
                            
                            # Refresh timestamp
                            stranger["timestamp"] = now
                            break
                    
                    if not is_known_stranger:
                        # Add to known strangers
                        self.known_strangers.append({
                            "embedding": embedding,
                            "timestamp": now
                        })
                        # Keep list small (last 20 strangers)
                        if len(self.known_strangers) > 20:
                            self.known_strangers.pop(0)

                    # Check Grace Period (2.0 seconds)
                    # If track is new (< 2s old), keep "Scanning" (None) instead of "Unauthorized"
                    if (now - track["first_seen"]) < 2.0 and previous_status is None:
                        track["authorized"] = None
                        track["name"] = "Scanning..."
                        # Do NOT log unauthorized yet
                    else:
                        if track.get("is_returning_stranger"):
                             track["name"] = "Unauthorized (Returning)"
                        else:
                             track["name"] = "Unauthorized"
                        
                        # If they were previously authorized, this is a distinct event (Revoked/Deleted)
                        if previous_status is True:
                            logger.warning(f"🚫 Track {track['id']} Authorization REVOKED (Staff Deleted?)")
                        
                        # If it's a new person or just confirmed unauthorized
                        # AND we haven't already logged/snapped them fully
                        if previous_status is not False and not track.get("is_returning_stranger"):
                            logger.warning(f"🚨 Track {track['id']} UNAUTHORIZED")
                            
                            # Generate snapshot for the event log (First one)
                            snapshot_id = str(uuid.uuid4())
                            snapshot_path = f"{SNAPSHOT_DIR}/{snapshot_id}.jpg"
                            cv2.imwrite(snapshot_path, frame)
                            
                            stats_service.log_event("UNAUTHORIZED_ENTRY", {
                                "name": "Unknown Person",
                                "track_id": track["id"],
                                "snapshot": f"/snapshots/{snapshot_id}.jpg"
                            })
                            
                            await self._send_alert(frame, track, "UNAUTHORIZED_PERSON", "Unauthorized Person Detected")

    async def _capture_snapshots(self, frame, tracks):
        """
        Capture up to 3 snapshots per person.
        - Authorized: NO snapshots.
        - Unauthorized: Max 3 snapshots total (persisted across returns).
        """
        for track in tracks:
            # RULE 1: Never snapshot authorized people or those still scanning
            if track["authorized"] is not False: 
                continue

            # RULE 2: Max 3 snapshots
            if track["snapshots_taken"] < 3:
                snapshot_id = str(uuid.uuid4())
                snapshot_path = f"{SNAPSHOT_DIR}/{snapshot_id}.jpg"
                cv2.imwrite(snapshot_path, frame)
                
                track["snapshots_taken"] += 1
                logger.info(f"📸 Captured Snapshot {track['snapshots_taken']}/3 for Track {track['id']}")

    async def _send_alert(self, frame, track, type_code, title):
        """Send generic alert with throttling."""
        # Check cooldown
        track_id = track["id"]
        now = time.time()
        
        # Initialize cooldown dict for this track if needed
        if not hasattr(self, "alert_cooldowns"):
            self.alert_cooldowns = {} # {track_id: {type: timestamp}}
            
        if track_id not in self.alert_cooldowns:
            self.alert_cooldowns[track_id] = {}
            
        last_time = self.alert_cooldowns[track_id].get(type_code, 0)
        if now - last_time < 30.0: # 30 seconds cooldown per type
            return

        # Update cooldown
        self.alert_cooldowns[track_id][type_code] = now

        snapshot_id = str(uuid.uuid4())
        snapshot_path = f"{SNAPSHOT_DIR}/{snapshot_id}.jpg"
        cv2.imwrite(snapshot_path, frame)

        alert_data = {
            "id": snapshot_id,
            "type": type_code,
            "severity": "warning",
            "title": title,
            "description": f"{title} (ID: {track['id']})",
            "location": "Hospital Corridor",
            "confidence": float(track.get("conf", 0)),
            "snapshot": f"/snapshots/{snapshot_id}.jpg",
            "timestamp": now,
        }
        stored_alert = alert_store.add_alert(alert_data)
        await broadcaster.broadcast_json(stored_alert)


    def _annotate_frame(self, frame, tracks):
        """Draw tracks with consistent IDs and names"""
        annotated = frame.copy()
        
        for track in tracks:
            x1, y1, x2, y2 = map(int, track["bbox"])
            
            # Determine color
            if track["authorized"] is None:
                color = (0, 255, 255) # Yellow - Scanning
                label = f"ID:{track['id']} Scanning..."
            elif track["authorized"]:
                color = (0, 255, 0) # Green
                label = f"{track['name']} ({track.get('role', 'Staff')})"
            else:
                color = (0, 0, 255) # Red
                label = "Unauthorized"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Label
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - 20), (x1 + w, y1), color, -1)
            cv2.putText(annotated, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        self.latest_annotated_frame = annotated

    async def _analyze_behavior(self, frame, mapped_detections):
        """
        Analyze frame for suspicious behaviors using Event Engine.
        """
        h, w = frame.shape[:2]
        
        # Get poses for each person
        poses = []
        for det in mapped_detections:
            bbox = det.get("bbox", [])
            if len(bbox) >= 4:
                x1, y1, x2, y2 = map(int, bbox)
                # Clamp coordinates
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                crop = frame[y1:y2, x1:x2]
                
                if crop.size > 0:
                    # Convert to RGB for pose detection
                    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    pose_result = self.pose.detect(crop_rgb)
                    poses.append(pose_result)
                else:
                    poses.append(None)
            else:
                poses.append(None)
        
        # Run event engine analysis
        events = event_engine.analyze_frame(
            detections=mapped_detections,
            poses=poses,
            frame_shape=(h, w)
        )
        
        # Process each detected event
        for event in events:
            await self._create_behavior_alert(frame, event)

    async def _create_behavior_alert(self, frame, event):
        """
        Create and broadcast an alert for a detected behavior event.
        """
        type_code = event.get("type", "BEHAVIOR")
        track_id = event.get("track_id")
        
        # Throttling Logic
        now = time.time()
        if not hasattr(self, "alert_cooldowns"):
            self.alert_cooldowns = {}
            
        # Use track_id for key if available, otherwise "global" for crowd events
        key = track_id if track_id else "global"
        
        if key not in self.alert_cooldowns:
            self.alert_cooldowns[key] = {}
            
        last_time = self.alert_cooldowns[key].get(type_code, 0)
        
        # 30s cooldown for same event type on same person
        if now - last_time < 30.0:
            return

        # Update cooldown
        self.alert_cooldowns[key][type_code] = now
        
        snapshot_id = str(uuid.uuid4())
        snapshot_path = f"{SNAPSHOT_DIR}/{snapshot_id}.jpg"
        cv2.imwrite(snapshot_path, frame)
        
        alert_data = {
            "id": snapshot_id,
            "type": type_code,
            "severity": event.get("severity", "warning"),
            "title": event.get("title", "Behavior Alert"),
            "description": event.get("description", "Suspicious behavior detected"),
            "location": "Hospital Corridor",
            "snapshot": f"/snapshots/{snapshot_id}.jpg",
            "timestamp": now,
            "behavior": event
        }
        
        logger.warning(f"🚨 Behavior detected: {type_code}")
        stored_alert = alert_store.add_alert(alert_data)
        await broadcaster.broadcast_json(stored_alert)


# Global singleton instance
processor = ProcessingService()

