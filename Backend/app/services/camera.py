import cv2
import time
import threading
import logging
import os
from app.config import CAMERA_SOURCE

logger = logging.getLogger(__name__)

class CameraStream:
    def __init__(self, src=None):
        self.src = src if src is not None else CAMERA_SOURCE
        
        # If source is a digit, convert to int (local webcam)
        if isinstance(self.src, str) and self.src.isdigit():
            self.src = int(self.src)

        self.cap = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.last_frame_time = 0
        self.reconnect_delay = 5  # seconds

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        logger.info(f"Camera stream started on source: {self.src}")

    def stop(self):
        self.running = False
        # Release immediately to kill hardware light and unblock read()
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if self.thread:
            # We don't join/wait endlessly, just let it detach if needed
            # self.thread.join() 
            pass
        
        logger.info("Camera stopped and released.")

    def _connect(self):
        if self.cap:
            self.cap.release()
        
        # Try DirectShow first on Windows (fixes MSMF errors)
        if isinstance(self.src, int) and os.name == 'nt':
            logger.info(f"Connecting to camera {self.src} with CAP_DSHOW...")
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(self.src)
        
        # Optimize for low latency if RTSP
        if isinstance(self.src, str) and self.src.startswith("rtsp"):
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Keep buffer small
        
        if not self.cap.isOpened():
            logger.warning("Failed to open with preferred backend, trying default...")
            self.cap = cv2.VideoCapture(self.src)
            
            if not self.cap.isOpened():
                logger.error("Failed to open camera source.")
                return False
        return True

    def _update(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                if not self._connect():
                    time.sleep(self.reconnect_delay)
                    continue

            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame, reconnecting...")
                self.cap.release()
                time.sleep(self.reconnect_delay)
                continue

            with self.lock:
                self.frame = frame
                self.last_frame_time = time.time()
            
            # Match target FPS (e.g. 30 FPS)
            elapsed = time.time() - self.last_frame_time
            sleep_time = max(0.001, (1/30) - elapsed)
            time.sleep(sleep_time)
    
    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

# Global instance
camera_stream = CameraStream()
