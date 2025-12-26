# app/utils/draw.py
import cv2

def draw_boxes(frame, detections, labels=None):
    # frame: cv2 BGR
    for d in detections:
        x1,y1,x2,y2 = map(int, d["bbox"])
        conf = d.get("conf", 0)
        cls = d.get("class", -1)
        label = f"{labels[cls] if labels and cls>=0 else cls}:{conf:.2f}"
        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(frame, label, (x1, max(0,y1-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    return frame
