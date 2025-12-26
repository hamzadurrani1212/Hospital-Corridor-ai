# app/models/clip_embedder.py

import torch
import numpy as np
from transformers import CLIPModel, CLIPProcessor
from app.config import DEVICE

#  Explicit OpenAI CLIP model
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"


class CLIPEmbedder:
    _instance = None
    _loading = False

    def __init__(self, model_name: str = CLIP_MODEL_NAME, device: str = DEVICE):
        self.device = device
        self.model = None
        self.processor = None
        self.model_name = model_name

    def _ensure_loaded(self):
        if self.model is None:
            import logging
            logger = logging.getLogger("hospital_ai")
            logger.info(f"💾 Loading CLIP model '{self.model_name}' to {self.device}...")
            
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info("✅ CLIP model loaded successfully")

    def image_embedding(self, pil_image):
        self._ensure_loaded()
        inputs = self.processor(images=pil_image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.cpu().numpy().flatten().astype(np.float32)

    def text_embedding(self, text: str):
        self._ensure_loaded()
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        return text_features.cpu().numpy().flatten().astype(np.float32)

# Singleton instance
embedder = CLIPEmbedder()
