from .integrations.itk import HAVE_ITK
import itkwasm
import numpy as np
from typing import Dict, List, Union
import zarr


Gaussian_Curve = Dict[str, float]
Gaussians = Dict[str, List[Gaussian_Curve]]

Style = Dict[str, str]

Image = Union[np.ndarray, itkwasm.Image, zarr.Group]
Point_Sets = Union[np.ndarray, itkwasm.PointSet, zarr.Group]
if HAVE_ITK:
    import itk
    Image = Union[Image, itk.Image]
    Point_Sets = Union[Point_Sets, itk.GroupSpatialObject]
