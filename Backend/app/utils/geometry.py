import cv2
import numpy as np

def point_in_zone(point, polygon) -> bool:
    poly = np.array(polygon, dtype=np.int32)
    return cv2.pointPolygonTest(poly, point, False) >= 0
