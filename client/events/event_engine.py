# client/events/event_engine.py

import time
import asyncio
from typing import Optional, List
from PIL import Image

from client.tracker.simple_tracker import SimpleTracker
from client.utils.geometry import bbox_center
from client.utils.image_utils import crop_box_from_pil

# ------------------------------
# Configuration
# ------------------------------
CROWD_THRESHOLD = 4
NO_MOVE_SECONDS = 20
MOVEMENT_PIXEL_THRESHOLD = 10


# ------------------------------
# Async CLIP Embed Queue
# ------------------------------
class AsyncEmbedEngine:
    """
    Async non-blocking background engine which:
      - Accepts cropped person images
      - Sends them to /api/embed (FastAPI endpoint)
      - Upserts vectors to Qdrant on server side
    """

    def __init__(self, embed_endpoint: str):
        self.embed_endpoint = embed_endpoint
        self.queue = asyncio.Queue()
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self.worker())

    async def stop(self):
        self.running = False
        await self.queue.join()

    async def enqueue(self, crop: Image.Image, person_id: str):
        """Add cropped image to background queue"""
        await self.queue.put((crop, person_id))

    async def worker(self):
        import httpx
        import io

        async with httpx.AsyncClient(timeout=10) as client:
            while self.running:
                crop, person_id = await self.queue.get()
                try:
                    buf = io.BytesIO()
                    crop.save(buf, format="JPEG")
                    buf.seek(0)

                    files = {"file": ("crop.jpg", buf.getvalue(), "image/jpeg")}
                    data = {"person_id": person_id}

                    await client.post(self.embed_endpoint, files=files, data=data)

                except Exception as e:
                    print(" Embedding failed:", e)

                self.queue.task_done()


# ------------------------------
# Event Engine
# ------------------------------
class EventEngine:
    """
    Main logic layer:
    - Runs tracker
    - Crops detected people
    - Submits async embedding tasks
    - Performs basic anomaly detection
    """

    def __init__(
        self,
        alert_sender = None,
        embed_engine: Optional[AsyncEmbedEngine] = None,
    ):
        self.tracker = SimpleTracker()
        self.alert_sender = alert_sender
        self.embed_engine = embed_engine

        self.alerted_no_move = set()
        self.alerted_crowd = False


    async def process_frame(self, detections: List[dict], frame_pil: Image.Image, frame_time: float):
        """
        Called from RTSP client loop

        detections:
          [
            {
              "bbox": [x1,y1,x2,y2],
              "conf": float,
            }
          ]
        """

        # 1. Track people
        tracked = self.tracker.update(detections, frame_time)

        # -------------------------------------------------
        # 2. Crop people and enqueue embedding async
        # -------------------------------------------------

        for person in tracked:
            tid = person["track_id"]
            bbox = person["bbox"]

            crop = crop_box_from_pil(frame_pil, bbox)
            person["crop_image"] = crop

            if self.embed_engine:
                await self.embed_engine.enqueue(crop, tid)


        # -------------------------------------------------
        # 3. Crowd detection
        # -------------------------------------------------

        person_count = len(tracked)

        if person_count >= CROWD_THRESHOLD and not self.alerted_crowd:
            self.alerted_crowd = True
            self._alert({
                "type": "crowd_detected",
                "count": person_count,
                "time": frame_time,
            })

        if person_count < CROWD_THRESHOLD:
            self.alerted_crowd = False


        # -------------------------------------------------
        # 4. Movement / Lying detection
        # -------------------------------------------------

        for t in tracked:
            tid = t["track_id"]
            track = self.tracker.tracks.get(tid)
            if not track:
                continue

            history = list(track["history"])
            if len(history) < 2:
                continue

            now = frame_time
            recent = [c for c in history if now - c[0] <= NO_MOVE_SECONDS]

            if not recent:
                continue

            earliest = recent[0][1]
            latest = recent[-1][1]

            dx = latest[0] - earliest[0]
            dy = latest[1] - earliest[1]

            dist = (dx**2 + dy**2)**0.5

            x1,y1,x2,y2 = track["bbox"]
            w = x2 - x1
            h = y2 - y1
            aspect = (w / h) if h > 0 else 0


            # Heuristic detection

            if dist < MOVEMENT_PIXEL_THRESHOLD:
                if tid not in self.alerted_no_move:

                    event_type = "no_movement"

                    if aspect > 1.2:
                        event_type = "possible_lying"

                    self._alert({
                        "type": event_type,
                        "track_id": tid,
                        "movement_px": dist,
                        "aspect": aspect,
                        "bbox": track["bbox"],
                        "time": now,
                    })

                    self.alerted_no_move.add(tid)

            else:
                self.alerted_no_move.discard(tid)



    # -------------------------
    def _alert(self, payload):

        print(" ALERT:", payload)

        if self.alert_sender:
            try:
                self.alert_sender.send(payload)
            except Exception as e:
                print("Failed to send alert:", e)
