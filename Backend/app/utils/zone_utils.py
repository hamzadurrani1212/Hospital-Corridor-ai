import cv2
import numpy as np


def point_in_zone(point, polygon):
    """
    Check if a point lies inside a polygon zone.

    Args:
        point (tuple): (x, y) center point
        polygon (list): list of (x, y) tuples defining the zone

    Returns:
        bool: True if inside or on edge, False otherwise
    """
    poly = np.array(polygon, dtype=np.int32)

    # OpenCV pointPolygonTest result:
    #  1  → inside
    #  0  → on edge
    # -1  → outside
    return cv2.pointPolygonTest(poly, point, False) >= 0
