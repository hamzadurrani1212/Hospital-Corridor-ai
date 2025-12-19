# app/models/clip_embedder.py

import torch
import numpy as np
from transformers import CLIPModel, CLIPProcessor
from app.config import DEVICE

#  Explicit OpenAI CLIP model
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"


class CLIPEmbedder:
    def __init__(self, model_name: str = CLIP_MODEL_NAME, device: str = DEVICE):
        self.device = device

        # Load model + processor
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)

        self.model.to(self.device)
        self.model.eval()  #  important for inference

    def image_embedding(self, pil_image):
        """
        Returns: np.ndarray (512,)
        """
        inputs = self.processor(
            images=pil_image,
            return_tensors="pt"
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)

        # 🔒 L2 normalization (VERY IMPORTANT for vector DB)
        image_features = image_features / image_features.norm(
            p=2, dim=-1, keepdim=True
        )

        return image_features.cpu().numpy().flatten().astype(np.float32)

    def text_embedding(self, text: str):
        """
        Returns: np.ndarray (512,)
        """
        inputs = self.processor(
            text=[text],
            return_tensors="pt",
            padding=True
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)

        # 🔒 L2 normalization
        text_features = text_features / text_features.norm(
            p=2, dim=-1, keepdim=True
        )

        return text_features.cpu().numpy().flatten().astype(np.float32)


#  Singleton instance (best for FastAPI)
embedder = CLIPEmbedder()
