from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import cv2
import time
from app.services.camera import camera_stream
from app.services.processing import processor

router = APIRouter()

import numpy as np

def gen_frames():
    """Generator for MJPEG stream."""
    while True:
        if not processor.running:
            # Create black frame for "Camera Off"
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(black_frame, "CAMERA OFF", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            ret, buffer = cv2.imencode('.jpg', black_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.5)
            continue

        # Use the annotated frame if available, otherwise raw frame
        if processor.latest_annotated_frame is not None:
            frame = processor.latest_annotated_frame
        else:
            frame = camera_stream.get_frame()
            
        if frame is None:
            time.sleep(0.1)
            continue
            
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Cap transmit framerate? Camera is driving it, but we can throttle if needed
        time.sleep(0.04) # ~25 FPS max

@router.get("/stream/{camera_id}")
async def video_feed(camera_id: str):
    # Do NOT auto-start camera here anymore, respect user control
    return StreamingResponse(
        gen_frames(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

from pydantic import BaseModel

class ControlRequest(BaseModel):
    active: bool

@router.post("/control")
async def control_camera(req: ControlRequest):
    if req.active:
        processor.start()
        return {"status": "started", "active": True}
    else:
        processor.stop()
        return {"status": "stopped", "active": False}

@router.get("/cameras")
async def get_cameras():
    """Return list of available cameras."""
    # Currently single source only
    status = "online" if processor.running else "offline"
    return [
        {
            "id": "0",
            "name": "Main Camera",
            "status": status,
            "stream_url": "/api/stream/0",
            "location": "Corridor 1"
        }
    ]


@router.get("/cameras/active")
async def get_active_cameras():
    """Return count of online cameras."""
    count = 1 if processor.running else 0
    return {"count": count}


@router.get("/cameras/streams")
async def get_camera_streams():
    """Return list of camera streams for dashboard display."""
    status = "online" if processor.running else "offline"
    return [
        {
            "id": "0",
            "title": "Main Entrance - CAM001",
            "url": "/api/stream/0",
            "status": status,
            "location": "Corridor 1"
        }
    ]
