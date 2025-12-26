from io import BytesIO
from PIL import Image
import numpy as np
import cv2

def load_image_from_bytes(data: bytes) -> Image.Image:
    """Load image from bytes and convert to RGB PIL Image."""
    return Image.open(BytesIO(data)).convert("RGB")

def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR format."""
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def crop_box_from_pil(pil_image: Image.Image, box) -> Image.Image:
    """
    Crop a box from PIL image.
    box: [x1, y1, x2, y2]
    """
    return pil_image.crop(tuple(map(int, box)))

def preprocess_for_yolo(frame, target_size=(640, 640)):
    """
    Resize and pad image to target size while maintaining aspect ratio.
    Returns: (preprocessed_image, ratio, (dw, dh))
    """
    h, w = frame.shape[:2]
    r = min(target_size[0] / h, target_size[1] / w)
    
    new_unpad = (int(w * r), int(h * r))
    dw, dh = target_size[1] - new_unpad[0], target_size[0] - new_unpad[1]
    
    dw /= 2
    dh /= 2
    
    if (w, h) != new_unpad:
        frame = cv2.resize(frame, new_unpad, interpolation=cv2.INTER_LINEAR)
        
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    
    frame = cv2.copyMakeBorder(frame, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    
    return frame, r, (dw, dh)
