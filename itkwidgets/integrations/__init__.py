from collections.abc import MutableMapping
from re import S

import itkwasm
import numpy as np
import zarr
from multiscale_spatial_image import MultiscaleSpatialImage, to_multiscale, itk_image_to_multiscale, Methods
from spatial_image import to_spatial_image, is_spatial_image

import dask
import xarray as xr
from .itk import HAVE_ITK, itk_image_to_wasm_image, itk_group_spatial_object_to_wasm_point_set
from .pytorch import HAVE_TORCH
from .vtk import HAVE_VTK, vtk_image_to_spatial_image, vtk_polydata_to_vtkjs
from .xarray import xarray_data_array_to_numpy, xarray_data_set_to_numpy
from ..render_types import RenderType

def _spatial_image_scale_factors(spatial_image, min_length):
    sizes = dict(spatial_image.sizes)
    scale_factors = []
    dims = spatial_image.dims
    previous = { d: 1 for d in { 'x', 'y', 'z' }.intersection(dims) }
    while (np.array(list(sizes.values())) > min_length).any():
        max_size = np.array(list(sizes.values())).max()
        to_skip = { d: sizes[d] <= max_size / 2 for d in previous.keys() }
        scale_factor = {}
        for dim in previous.keys():
            if to_skip[dim]:
                scale_factor[dim] = previous[dim]
                continue
            scale_factor[dim] = 2 * previous[dim]

            sizes[dim] = int(sizes[dim] / 2)
        previous = scale_factor
        scale_factors.append(scale_factor)

    return scale_factors

def _make_multiscale_store(multiscale):
    # Todo: for very large images serialize to disk cache
    store = zarr.storage.MemoryStore(dimension_separator='/')
    multiscale.to_zarr(store, compute=True)
    return store

def _get_viewer_image(image, label=False):
    min_length = 64
    if label:
        method = Methods.DASK_IMAGE_NEAREST
    else:
        method = Methods.DASK_IMAGE_GAUSSIAN
    if isinstance(image, MultiscaleSpatialImage):
        return _make_multiscale_store(image)

    # Todo: support for itkwasm.Image
    if HAVE_ITK:
        import itk
        if isinstance(image, itk.Image):
            dimension = image.GetImageDimension()
            size = np.array(itk.size(image))
            scale_factors = []
            dims = ('x', 'y', 'z')
            previous = {'x': 1, 'y': 1, 'z': 1}
            while (size > min_length).any():
                to_skip = size <= size.max() / 2
                scale_factor = {}
                for dim in range(dimension):
                    if to_skip[dim]:
                        scale_factor[dims[dim]] = previous[dims[dim]]
                        continue
                    scale_factor[dims[dim]] = 2 * previous[dims[dim]]
                    size[dim] = int(size[dim] / 2)
                previous = scale_factor
                scale_factors.append(scale_factor)

            multiscale = itk_image_to_multiscale(image, scale_factors=scale_factors, method=method)
            return _make_multiscale_store(multiscale)

    if HAVE_VTK:
        import vtk
        if isinstance(image, vtk.vtkImageData):
            spatial_image = vtk_image_to_spatial_image(image)
            scale_factors = _spatial_image_scale_factors(spatial_image, min_length)
            multiscale = to_multiscale(spatial_image, scale_factors, method=method)
            return _make_multiscale_store(multiscale)

    if isinstance(image, dask.array.core.Array):
        spatial_image = to_spatial_image(image)
        scale_factors = _spatial_image_scale_factors(spatial_image, min_length)
        multiscale = to_multiscale(spatial_image, scale_factors, method=method)
        return _make_multiscale_store(multiscale)

    if isinstance(image, zarr.Array):
        spatial_image = to_spatial_image(image)
        scale_factors = _spatial_image_scale_factors(spatial_image, min_length)
        multiscale = to_multiscale(spatial_image, scale_factors, method=method)
        return _make_multiscale_store(multiscale)

    # NGFF Zarr
    if isinstance(image, zarr.Group) and 'multiscales' in image.attrs:
        return image.store

    if HAVE_TORCH:
        import torch
        if isinstance(image, torch.Tensor):
            spatial_image = to_spatial_image(image.numpy())
            scale_factors = _spatial_image_scale_factors(spatial_image, min_length)
            multiscale = to_multiscale(spatial_image, scale_factors, method=method)
            return _make_multiscale_store(multiscale)

    # Todo: preserve dask Array, if present, check if dims are NGFF -> use dims, coords
    # Check if coords are uniform, if not, resample
    if isinstance(image, xr.DataArray):
        if is_spatial_image(image):
            scale_factors = _spatial_image_scale_factors(image, min_length)
            multiscale = to_multiscale(image, scale_factors, method=method)
            return _make_multiscale_store(multiscale)

        return xarray_data_array_to_numpy(image)
    if isinstance(image, xr.Dataset):
        da = image[next(iter(image.variables.keys()))]
        if is_spatial_image(da):
            scale_factors = _spatial_image_scale_factors(da, min_length)
            multiscale = to_multiscale(da, scale_factors, method=method)
            return _make_multiscale_store(multiscale)
        return xarray_data_set_to_numpy(image)

    if isinstance(image, np.ndarray):
        spatial_image = to_spatial_image(image)
        scale_factors = _spatial_image_scale_factors(spatial_image, min_length)
        multiscale = to_multiscale(spatial_image, scale_factors, method=method)
        return _make_multiscale_store(multiscale)
    raise RuntimeError("Could not process the viewer image")


def _get_viewer_point_sets(point_sets):
    if HAVE_VTK:
        import vtk
        if isinstance(point_sets, vtk.vtkPolyData):
            return vtk_polydata_to_vtkjs(point_sets)
    if isinstance(point_sets, dask.array.core.Array):
        return np.asarray(point_sets)
    if HAVE_TORCH:
        import torch
        if isinstance(point_sets, torch.Tensor):
            return point_sets.numpy()
    if isinstance(point_sets, xr.DataArray):
        return xarray_data_array_to_numpy(point_sets)
    if isinstance(point_sets, xr.Dataset):
        return xarray_data_set_to_numpy(point_sets)
    return point_sets


def _detect_render_type(data, input_type) -> RenderType:
    if isinstance(data, itkwasm.Image):
        return RenderType.IMAGE
    elif isinstance(data, itkwasm.PointSet):
        return RenderType.POINT_SET
    elif isinstance(data, MultiscaleSpatialImage):
        return RenderType.IMAGE
    elif isinstance(data, (zarr.Array, zarr.Group)):
        # For now assume zarr.Group is an image
        # In the future, once NGFF supports point sets fully
        # We may need to do more introspection
        return RenderType.IMAGE
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
    if isinstance(data, xr.DataArray):
        if input_type == 'point_sets':
            return RenderType.POINT_SET
        else:
            return RenderType.IMAGE
    if isinstance(data, xr.Dataset):
        if input_type == 'point_sets':
            return RenderType.POINT_SET
        else:
            return RenderType.IMAGE
