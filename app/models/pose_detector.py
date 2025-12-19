# app/models/pose_detector.py
"""
Pose detection using MediaPipe for behavior analysis.
Detects 33 body landmarks for fall detection and pose estimation.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple

# Try to import MediaPipe, fallback to stub if not available
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("[WARNING] MediaPipe not installed. Pose detection will be disabled.")


class PoseDetector:
    """
    MediaPipe-based pose detector for human body landmark detection.
    Used for fall detection and behavior analysis.
    """
    
    # Key landmark indices
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    
    def __init__(
        self,
        static_image_mode: bool = False,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
        self.static_image_mode = static_image_mode
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        
        self.pose = None
        if MEDIAPIPE_AVAILABLE:
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=static_image_mode,
                model_complexity=1,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
    
    def detect(self, image_rgb: np.ndarray) -> Dict:
        """
        Detect pose landmarks in an RGB image.
        
        Args:
            image_rgb: RGB image as numpy array
            
        Returns:
            Dictionary with landmarks and analysis results
        """
        if not MEDIAPIPE_AVAILABLE or self.pose is None:
            return {"landmarks": None, "is_fallen": False, "body_angle": None}
        
        try:
            results = self.pose.process(image_rgb)
            
            if results.pose_landmarks is None:
                return {"landmarks": None, "is_fallen": False, "body_angle": None}
            
            # Extract landmarks
            landmarks = []
            h, w = image_rgb.shape[:2]
            
            for lm in results.pose_landmarks.landmark:
                landmarks.append({
                    "x": lm.x * w,
                    "y": lm.y * h,
                    "z": lm.z,
                    "visibility": lm.visibility
                })
            
            # Analyze pose for fall detection
            is_fallen, body_angle = self._analyze_pose(landmarks, h)
            
            return {
                "landmarks": landmarks,
                "is_fallen": is_fallen,
                "body_angle": body_angle
            }
            
        except Exception as e:
            print(f"[PoseDetector] Error: {e}")
            return {"landmarks": None, "is_fallen": False, "body_angle": None}
    
    def _analyze_pose(self, landmarks: List[Dict], frame_height: int) -> Tuple[bool, Optional[float]]:
        """
        Analyze pose landmarks for fall detection.
        
        Returns:
            (is_fallen, body_angle) tuple
        """
        if not landmarks or len(landmarks) < 29:
            return False, None
        
        try:
            # Get key points
            left_shoulder = landmarks[self.LEFT_SHOULDER]
            right_shoulder = landmarks[self.RIGHT_SHOULDER]
            left_hip = landmarks[self.LEFT_HIP]
            right_hip = landmarks[self.RIGHT_HIP]
            
            # Calculate torso center points
            shoulder_center_y = (left_shoulder["y"] + right_shoulder["y"]) / 2
            hip_center_y = (left_hip["y"] + right_hip["y"]) / 2
            shoulder_center_x = (left_shoulder["x"] + right_shoulder["x"]) / 2
            hip_center_x = (left_hip["x"] + right_hip["x"]) / 2
            
            # Calculate body angle (angle of torso from vertical)
            dx = hip_center_x - shoulder_center_x
            dy = hip_center_y - shoulder_center_y
            
            if dy != 0:
                body_angle = np.degrees(np.arctan2(abs(dx), dy))
            else:
                body_angle = 90.0 if dx != 0 else 0.0
            
            # Fall detection heuristics:
            # 1. Body angle too horizontal (> 60 degrees from vertical)
            # 2. Hip center is close to shoulder center vertically (person lying down)
            
            torso_height = abs(hip_center_y - shoulder_center_y)
            relative_torso = torso_height / frame_height if frame_height > 0 else 0
            
            is_fallen = (
                body_angle > 60 or  # Body is more horizontal than vertical
                relative_torso < 0.1  # Torso is very compressed (lying flat)
            )
            
            return is_fallen, body_angle
            
        except Exception:
            return False, None
    
    def get_body_keypoints(self, landmarks: List[Dict]) -> Dict:
        """
        Extract key body points for analysis.
        """
        if not landmarks or len(landmarks) < 29:
            return {}
        
        return {
            "nose": landmarks[self.NOSE],
            "left_shoulder": landmarks[self.LEFT_SHOULDER],
            "right_shoulder": landmarks[self.RIGHT_SHOULDER],
            "left_hip": landmarks[self.LEFT_HIP],
            "right_hip": landmarks[self.RIGHT_HIP],
            "left_knee": landmarks[self.LEFT_KNEE],
            "right_knee": landmarks[self.RIGHT_KNEE],
            "left_ankle": landmarks[self.LEFT_ANKLE],
            "right_ankle": landmarks[self.RIGHT_ANKLE]
        }
    
    def draw_landmarks(self, image: np.ndarray, landmarks: List[Dict]) -> np.ndarray:
        """
        Draw pose landmarks on image for visualization.
        """
        if not landmarks:
            return image
        
        output = image.copy()
        
        # Draw key points
        for lm in landmarks:
            x, y = int(lm["x"]), int(lm["y"])
            cv2.circle(output, (x, y), 4, (0, 255, 0), -1)
        
        # Draw skeleton connections
        connections = [
            (self.LEFT_SHOULDER, self.RIGHT_SHOULDER),
            (self.LEFT_SHOULDER, self.LEFT_HIP),
            (self.RIGHT_SHOULDER, self.RIGHT_HIP),
            (self.LEFT_HIP, self.RIGHT_HIP),
            (self.LEFT_HIP, self.LEFT_KNEE),
            (self.RIGHT_HIP, self.RIGHT_KNEE),
            (self.LEFT_KNEE, self.LEFT_ANKLE),
            (self.RIGHT_KNEE, self.RIGHT_ANKLE)
        ]
        
        for start_idx, end_idx in connections:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                cv2.line(
                    output,
                    (int(start["x"]), int(start["y"])),
                    (int(end["x"]), int(end["y"])),
                    (0, 255, 255),
                    2
                )
        
        return output
    
    def close(self):
        """Release resources."""
        if self.pose:
            self.pose.close()
