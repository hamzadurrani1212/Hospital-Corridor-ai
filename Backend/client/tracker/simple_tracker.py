import uuid
import time
import math
from collections import deque
from typing import List, Dict
from client.utils.geometry import iou, bbox_center

TRACKER_MAX_AGE = 30  # seconds
IOU_MATCH_THRESHOLD = 0.3

class SimpleTracker:
    def __init__(self, max_distance: float = 150.0, max_age: float = 30.0, iou_threshold: float = 0.3):
        self.tracks = {}  # id -> {bbox, last_seen, history}
        self.max_distance = max_distance
        self.max_age = max_age
        self.iou_threshold = iou_threshold

    def update(self, detections: List[Dict], frame_time: float) -> List[Dict]:
        assigned = {}
        det_bboxes = [d['bbox'] for d in detections]

        # Match existing tracks
        for tid, t in list(self.tracks.items()):
            best_iou = 0
            best_idx = -1
            
            # Match using IOU first
            for i, db in enumerate(det_bboxes):
                if i in assigned.values():
                    continue
                
                # Try IOU matching
                val = iou(t['bbox'], db)
                if val >= self.iou_threshold and val > best_iou:
                    best_iou = val
                    best_idx = i
                
            # Fallback to distance matching if no good IOU match
            if best_idx == -1:
                best_dist = self.max_distance
                t_center = bbox_center(t['bbox'])
                for i, db in enumerate(det_bboxes):
                    if i in assigned.values():
                        continue
                    d_center = bbox_center(db)
                    dist = math.sqrt((t_center[0] - d_center[0])**2 + (t_center[1] - d_center[1])**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i

            if best_idx >= 0:
                det = detections[best_idx]
                self.tracks[tid]['bbox'] = det['bbox']
                self.tracks[tid]['last_seen'] = frame_time
                center = bbox_center(det['bbox'])
                self.tracks[tid]['history'].append((frame_time, center))
                assigned[tid] = best_idx

        # Create new tracks
        for i, det in enumerate(detections):
            if i in assigned.values():
                continue
            new_id = str(uuid.uuid4())
            center = bbox_center(det['bbox'])
            self.tracks[new_id] = {
                'bbox': det['bbox'],
                'first_seen': frame_time,
                'last_seen': frame_time,
                'history': deque([(frame_time, center)], maxlen=128)
            }
            assigned[new_id] = i

        # Remove old tracks
        to_delete = [tid for tid, t in self.tracks.items() if frame_time - t['last_seen'] > self.max_age]
        for tid in to_delete:
            del self.tracks[tid]

        # Attach track_id to detections
        idx_to_tid = {v: k for k, v in assigned.items()}
        out = []
        for idx, det in enumerate(detections):
            tid = idx_to_tid.get(idx)
            out.append({**det, 'track_id': tid})
        return out
