# app/routes/detect.py
from fastapi import APIRouter, UploadFile, File
from client.yolo_detector import YOLODetector
from app.models.pose_detector import PoseDetector
from app.models.clip_embedder import embedder
from app.db.qdrant_client import get_client as get_qdrant, QDRANT_COLLECTION
from app.utils.preprocessing import load_image_from_bytes, pil_to_cv2, crop_box_from_pil
from app.utils.draw import draw_boxes
import uuid
import io
import numpy as np
from PIL import Image
import cv2

router = APIRouter()

yolo = YOLODetector()
pose = PoseDetector()

@router.post("/detect")
async def detect(file: UploadFile = File(...), store_embeddings: bool = True):
    # READ IMAGE
    contents = await file.read()
    pil = load_image_from_bytes(contents)
    frame = pil_to_cv2(pil)

    # 1. RUN DETECTIONS
    detections = yolo.detect(frame)
    person_dets = [d for d in detections if d.get("class") == 0 and d.get("conf") > 0.5]

    if not person_dets:
        return {"status": "no_persons_found", "count": 0}

    # 2. SAVE SNAPSHOT
    import os
    import time
    from app.broadcast import broadcaster

    filename = f"{uuid.uuid4().hex}.jpg"
    snapshot_path = os.path.join("snapshots", filename)
    os.makedirs("snapshots", exist_ok=True)
    
    # Annotate and save
    annotated = frame.copy()
    qdrant_ids = []

    for det in person_dets:
        bbox = det["bbox"]
        x1, y1, x2, y2 = map(int, bbox)
        
        # Crop & Embed
        try:
            crop = crop_box_from_pil(pil, bbox)
            vec = embedder.image_embedding(crop)
            uid = str(uuid.uuid4())
            
            # Upsert to Qdrant
            # Upsert to Qdrant
            get_qdrant().upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=uid,
                        vector=vec.tolist(),
                        payload={
                            "source": "api_detect", 
                            "timestamp": time.time(),
                            "confidence": det["conf"],
                            "snapshot": filename
                        }
                    )
                ]
            )
            qdrant_ids.append(uid)
            
            # Draw
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated, f"Person {det['conf']:.2f}", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
        except Exception as e:
            print(f"Error processing person: {e}")

    cv2.imwrite(snapshot_path, annotated)
    snapshot_url = f"/snapshots/{filename}"

    # 3. BROADCAST ALERT
    payload = {
        "id": int(time.time()), 
        "title": "Person Detected via API",
        "description": f"Backend API processed {len(person_dets)} person(s).",
        "severity": "warning", 
        "location": "Backend API",
        "time": "Just now",
        "timestamp": time.time(),
        "snapshot_url": snapshot_url,
        "qdrant_ids": qdrant_ids
    }
    
    await broadcaster.broadcast_json(payload)

    return {
        "status": "processed", 
        "count": len(person_dets), 
        "snapshot": snapshot_url, 
        "qdrant_ids": qdrant_ids
    }


