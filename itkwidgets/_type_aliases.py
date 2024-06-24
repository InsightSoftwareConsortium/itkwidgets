import itkwasm
import zarr
import numpy as np
import dask

from .integrations.itk import HAVE_ITK
from .integrations.pytorch import HAVE_TORCH
from .integrations.vtk import HAVE_VTK
from .integrations.xarray import HAVE_XARRAY
from typing import Dict, List, Literal, Union, Sequence

Points2d = Sequence[Sequence[float]]

Style = Dict[str, str]

Image = Union[np.ndarray, itkwasm.Image, zarr.Group]
PointSet = Union[np.ndarray, itkwasm.PointSet, zarr.Group]
CroppingPlanes = {Literal['origin']: List[float], Literal['normal']: List[int]}

if HAVE_ITK:
    import itk
    Image = Union[Image, itk.Image]
if HAVE_VTK:
    import vtk
    Image = Union[Image, vtk.vtkImageData]
    PointSet = Union[PointSet, vtk.vtkPolyData]
Image = Union[Image, dask.array.core.Array]
PointSet = Union[PointSet, dask.array.core.Array]
if HAVE_TORCH:
    import torch
    Image = Union[Image, torch.Tensor]
    PointSet = Union[PointSet, torch.Tensor]
if HAVE_XARRAY:
    import xarray
    Image = Union[Image, xarray.DataArray, xarray.Dataset]
    PointSet = Union[PointSet, xarray.DataArray, xarray.Dataset]
