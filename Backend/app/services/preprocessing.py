from PIL import Image
import io
import numpy as np

def load_image_from_bytes(data: bytes):
    return Image.open(io.BytesIO(data)).convert("RGB")

def pil_to_cv2(pil_image):
    arr = np.array(pil_image)
    # RGB to BGR
    return arr[:, :, ::-1].copy()

def cv2_to_pil(cv2_img):
    # BGR to RGB
    import PIL.Image
    return PIL.Image.fromarray(cv2_img[:, :, ::-1])

def crop_box_from_pil(pil_img, bbox):
    # bbox = [x1,y1,x2,y2] in pixel coordinates
    x1,y1,x2,y2 = map(int, bbox)
    return pil_img.crop((x1,y1,x2,y2))
