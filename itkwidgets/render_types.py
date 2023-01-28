from enum import Enum

class RenderType(Enum):
    """Rendered data types"""
    IMAGE = "image"
    LABELIMAGE = "labelImage"
    GEOMETRY = "geometry"
    POINT_SET = "pointSets"
