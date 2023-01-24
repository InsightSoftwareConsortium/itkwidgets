import itkwasm
import zarr
import numpy as np
import dask

from .integrations.itk import HAVE_ITK
from .integrations.pytorch import HAVE_TORCH
from .integrations.vtk import HAVE_VTK
from .integrations.xarray import HAVE_XARRAY
from typing import Dict, List, Union

Gaussian_Curve = Dict[str, float]
Gaussians = Dict[str, List[Gaussian_Curve]]

Style = Dict[str, str]

Image = Union[np.ndarray, itkwasm.Image, zarr.Group]
Point_Set = Union[np.ndarray, itkwasm.PointSet, zarr.Group]
if HAVE_ITK:
    import itk
    Image = Union[Image, itk.Image]
if HAVE_VTK:
    import vtk
    Image = Union[Image, vtk.vtkImageData]
    Point_Set = Union[Point_Set, vtk.vtkPolyData]
Image = Union[Image, dask.array.core.Array]
Point_Set = Union[Point_Set, dask.array.core.Array]
if HAVE_TORCH:
    import torch
    Image = Union[Image, torch.Tensor]
    Point_Set = Union[Point_Set, torch.Tensor]
if HAVE_XARRAY:
    import xarray
    Image = Union[Image, xarray.DataArray, xarray.Dataset]
    Point_Set = Union[Point_Set, xarray.DataArray, xarray.Dataset]
