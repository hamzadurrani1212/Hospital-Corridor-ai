from PIL import Image

def crop_box_from_pil(image: Image.Image, bbox):
    x1, y1, x2, y2 = bbox

    x1 = max(int(x1), 0)
    y1 = max(int(y1), 0)
    x2 = min(int(x2), image.width)
    y2 = min(int(y2), image.height)

    return image.crop((x1, y1, x2, y2))
