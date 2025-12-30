# app/services/face_service.py
"""
Face analysis service using InsightFace with ArcFace for high-precision face recognition.
Supports both newer (buffalo models) and older (0.2.x) InsightFace versions.
"""

import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing insightface components
try:
    from insightface.app import FaceAnalysis
    import insightface
    INSIGHTFACE_VERSION = getattr(insightface, '__version__', '0.0.0')
    INSIGHTFACE_AVAILABLE = True
    logger.info(f"InsightFace version {INSIGHTFACE_VERSION} detected")
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    INSIGHTFACE_VERSION = None
    logger.warning("InsightFace not available - face recognition will be limited")


class FaceService:
    """
    Face detection and recognition service using InsightFace ArcFace.
    Uses MobileFaceNet-style embeddings for high-precision face verification.
    """
    _instance = None

    def __init__(self, ctx_id=0):
        self.ctx_id = ctx_id
        self.app = None
        self._initialized = False
        self._initialize()

    def _initialize(self):
        """Initialize face detection and recognition models"""
        if not INSIGHTFACE_AVAILABLE:
            logger.error("❌ InsightFace not available. Please install: pip install insightface onnxruntime")
            return
        
        try:
            logger.info("📡 Initializing InsightFace ArcFace models...")
            
            # InsightFace 0.2.x uses different API than newer versions
            # Try different initialization methods based on version
            
            # Method 1: Older API (0.2.x) - name is required positional arg
            # Prioritize buffalo_sc (MobileFaceNet) as requested by user for balance of speed/accuracy
            model_names = ['buffalo_sc', 'buffalo_l', 'arcface_r100_v1', 'antelopev2']
            
            
            for model_name in model_names:
                try:
                    logger.info(f"Trying model: {model_name}")
                    self.app = FaceAnalysis(name=model_name)
                    self.app.prepare(ctx_id=self.ctx_id, det_size=(640, 640))
                    self._initialized = True
                    logger.info(f"✅ InsightFace ArcFace initialized with model: {model_name}")
                    return
                except Exception as e:
                    logger.debug(f"Model {model_name} failed: {e}")
                    continue
            
            # Method 2: Try with allowed_modules for newer versions
            try:
                self.app = FaceAnalysis(allowed_modules=['detection', 'recognition'])
                self.app.prepare(ctx_id=self.ctx_id, det_size=(640, 640))
                self._initialized = True
                logger.info("✅ InsightFace ArcFace initialized with allowed_modules")
                return
            except Exception as e:
                logger.debug(f"allowed_modules method failed: {e}")
            
            # If all methods fail
            logger.warning("⚠️ InsightFace initialization failed. Using OpenCV fallback.")
            self._initialized = False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize InsightFace: {e}")
            self._initialized = False

    def get_face_details(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Detect faces in a frame and return details for the most prominent face.
        Returns embedding, bbox, keypoints, gender, age if available.
        """
        if not INSIGHTFACE_AVAILABLE or self.app is None or not self._initialized:
            return self._get_fallback_face_details(frame)

        try:
            # Get faces from the frame
            faces = self.app.get(frame)
            
            if not faces:
                return None
            
            # Sort by box area to get the largest face
            faces.sort(key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
            face = faces[0]
            
            embedding = face.embedding.astype(np.float32)
            normed_embedding = (embedding / (np.linalg.norm(embedding) + 1e-6)).astype(np.float32)
            
            return {
                "embedding": embedding,
                "bbox": face.bbox.tolist() if hasattr(face.bbox, 'tolist') else list(face.bbox),
                "kps": face.kps.tolist() if hasattr(face.kps, 'tolist') else list(face.kps) if face.kps is not None else None,
                "gender": getattr(face, 'gender', None),
                "age": getattr(face, 'age', None),
                "normed_embedding": normed_embedding
            }
            
        except Exception as e:
            logger.error(f"Error getting face details: {e}")
            return self._get_fallback_face_details(frame)
    
    def _get_fallback_face_details(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Fallback face detection using OpenCV Haar cascades.
        Returns a simple embedding based on face region features.
        """
        try:
            # Use OpenCV's built-in face detector as fallback
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            if len(faces) == 0:
                return None
            
            # Get largest face
            faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)
            x, y, w, h = faces[0]
            
            # Create a simple embedding from face region histogram
            face_roi = frame[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (112, 112))
            
            # Generate a simple feature vector using color histogram
            hist_b = cv2.calcHist([face_roi], [0], None, [64], [0, 256]).flatten()
            hist_g = cv2.calcHist([face_roi], [1], None, [64], [0, 256]).flatten()
            hist_r = cv2.calcHist([face_roi], [2], None, [64], [0, 256]).flatten()
            
            # Combine and normalize to create a 512-dim embedding
            combined = np.concatenate([hist_b, hist_g, hist_r])
            embedding = np.zeros(512, dtype=np.float32)
            embedding[:len(combined)] = combined
            embedding = embedding / (np.linalg.norm(embedding) + 1e-6)
            
            return {
                "embedding": embedding,
                "bbox": [x, y, x+w, y+h],
                "kps": None,
                "gender": None,
                "age": None,
                "normed_embedding": embedding,
                "fallback": True
            }
            
        except Exception as e:
            logger.error(f"Fallback face detection failed: {e}")
            return None

    @staticmethod
    def compute_similarity(feat1: np.ndarray, feat2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        return float(np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2) + 1e-6))
    
    def is_available(self) -> bool:
        """Check if face recognition is properly initialized"""
        return self._initialized and self.app is not None


# Singleton instance
face_service = FaceService()
