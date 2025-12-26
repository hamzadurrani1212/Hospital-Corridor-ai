# app/models/yolo_detector.py
from ultralytics import YOLO
import cv2
import numpy as np

class YOLODetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.model = YOLO(model_path)

    def detect(self, frame):
        # frame: numpy array BGR
        results = self.model(frame)  # inference
        detections = []
        # iterate first result (batch size 1)
        for r in results:
            for box in r.boxes:
                # box.xyxy: tensor [x1,y1,x2,y2]
                x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detections.append({"bbox":[x1,y1,x2,y2], "conf":conf, "class":cls})
        return detections
