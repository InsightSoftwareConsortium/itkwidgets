import itkwasm
import numpy as np
import zarr

from .dask import HAVE_DASK, dask_array_to_ndarray
from .itk import HAVE_ITK, itk_image_to_wasm_image, itk_group_spatial_object_to_wasm_point_set
from .pytorch import HAVE_TORCH
from .vtk import HAVE_VTK, vtk_image_to_ndarray, vtk_polydata_to_vtkjs
from .xarray import HAVE_XARRAY, xarray_data_array_to_numpy, xarray_data_set_to_numpy
from ..render_types import RenderType


async def _get_viewer_image(image):
    if HAVE_ITK:
        import itk
        if isinstance(image, itk.Image):
            return itk_image_to_wasm_image(image)
    if HAVE_VTK:
        import vtk
        if isinstance(image, vtk.vtkImageData):
            return vtk_image_to_ndarray(image)
    if HAVE_DASK:
        import dask
        if isinstance(image, dask.array.core.Array):
            return dask_array_to_ndarray(image)
    if HAVE_TORCH:
        import torch
        if isinstance(image, torch.Tensor):
            return image.numpy()
    if HAVE_XARRAY:
        import xarray
        if isinstance(image, xarray.DataArray):
            return xarray_data_array_to_numpy(image)
        if isinstance(image, xarray.Dataset):
            return xarray_data_set_to_numpy(image)


async def _get_viewer_point_sets(point_sets):
    if HAVE_VTK:
        import vtk
        if isinstance(point_sets, vtk.vtkPolyData):
            return vtk_polydata_to_vtkjs(point_sets)
    if HAVE_DASK:
        import dask
        if isinstance(point_sets, dask.array.core.Array):
            return dask_array_to_ndarray(point_sets)
    if HAVE_TORCH:
        import torch
        if isinstance(point_sets, torch.Tensor):
            return point_sets.numpy()
    if HAVE_XARRAY:
        import xarray
        if isinstance(point_sets, xarray.DataArray):
            return xarray_data_array_to_numpy(point_sets)
        if isinstance(point_sets, xarray.Dataset):
            return xarray_data_set_to_numpy(point_sets)


def _detect_render_type(data, input_type) -> RenderType:
    if isinstance(data, itkwasm.Image):
        return RenderType.IMAGE
    elif isinstance(data, itkwasm.PointSet):
        return RenderType.POINT_SET
    elif isinstance(data, np.ndarray):
        if input_type == 'point_sets':
            return RenderType.POINT_SET
        else:
            return RenderType.IMAGE
    elif isinstance(data, zarr.Group):
        if input_type == 'point_sets':
            return RenderType.POINT_SET
        else:
            return RenderType.IMAGE
    elif HAVE_ITK:
        import itk
        if isinstance(data, itk.Image):
            return RenderType.IMAGE
    if HAVE_VTK:
        import vtk
        if isinstance(data, vtk.vtkImageData):
            return RenderType.IMAGE
        elif isinstance(data, vtk.vtkPolyData):
            return RenderType.POINT_SET
    if HAVE_DASK:
        import dask
        if isinstance(data, dask.array.core.Array):
            if input_type == 'point_sets':
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
    if HAVE_TORCH:
        import torch
        if isinstance(data, torch.Tensor):
            if input_type == 'point_sets':
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
    if HAVE_XARRAY:
        import xarray
        if isinstance(data, xarray.DataArray):
            if input_type == 'point_sets':
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
        if isinstance(data, xarray.Dataset):
            if input_type == 'point_sets':
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
