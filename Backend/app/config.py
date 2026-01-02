# app/config.py
import os
import torch

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.YfrxMkEGnu7vTZ8RDVNRgDJyfXgRAzpHFrN6ugHtE_Y", None)
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "corridor-embeddings")

CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
EMBED_DIM = int(os.getenv("EMBED_DIM", 512))

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Camera Configuration
# Use 0 for local webcam, or "rtsp://..." for IP camera
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0") 

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("hospital_ai")
# -----------------------------------
# CAMERA ZONES (FOR VEHICLE & AREA LOGIC)
# -----------------------------------

ZONES = {
    #  Vehicles NOT allowed
    "corridor": [
        (0, 0),
        (1280, 0),
        (1280, 400),
        (0, 400)
    ],

    #  Vehicles allowed
    "parking": [
        (0, 400),
        (640, 400),
        (640, 720),
        (0, 720)
    ],

    #  Emergency vehicles allowed
    "emergency": [
        (640, 400),
        (1280, 400),
        (1280, 720),
        (640, 720)
    ]
}
