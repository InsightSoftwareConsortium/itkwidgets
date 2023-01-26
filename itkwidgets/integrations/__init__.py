import itkwasm
import numpy as np
import zarr
from ngff_zarr import to_multiscales, to_ngff_zarr, to_ngff_image, itk_image_to_ngff_image, Methods

import dask
from .itk import HAVE_ITK, itk_group_spatial_object_to_wasm_point_set
from .pytorch import HAVE_TORCH
from .vtk import HAVE_VTK, vtk_image_to_ngff_image, vtk_polydata_to_vtkjs
from .xarray import HAVE_XARRAY, HAVE_MULTISCALE_SPATIAL_IMAGE, xarray_data_array_to_numpy, xarray_data_set_to_numpy
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

def _make_multiscale_store():
    # Todo: for very large images serialize to disk cache
    # -> create DirectoryStore in cache directory and return as the chunk_store
    store = zarr.storage.MemoryStore(dimension_separator='/')
    return store, None

def _get_viewer_image(image, label=False):
    # NGFF Zarr
    if isinstance(image, zarr.Group) and 'multiscales' in image.attrs:
        return image.store

    min_length = 64
    if label:
        method = Methods.DASK_IMAGE_NEAREST
    else:
        method = Methods.DASK_IMAGE_GAUSSIAN

    store, chunk_store = _make_multiscale_store()

    if HAVE_MULTISCALE_SPATIAL_IMAGE:
        from multiscale_spatial_image import MultiscaleSpatialImage
        if isinstance(image, MultiscaleSpatialImage):
            image.to_zarr(store, compute=True)
            return store

    if isinstance(image, itkwasm.Image):
        ngff_image = itk_image_to_ngff_image(image)
        multiscales = to_multiscales(ngff_image, method=method)
        to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
        return store

    if HAVE_ITK:
        import itk
        if isinstance(image, itk.Image):
            ngff_image = itk_image_to_ngff_image(image)
            multiscales = to_multiscales(ngff_image, method=method)
            to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
            return store

    if HAVE_VTK:
        import vtk
        if isinstance(image, vtk.vtkImageData):
            ngff_image = vtk_image_to_ngff_image(image)
            multiscales = to_multiscales(ngff_image, method=method)
            to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
            return store

    if isinstance(image, dask.array.core.Array):
        ngff_image = to_ngff_image(image)
        multiscales = to_multiscales(ngff_image, method=method)
        to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
        return store

    if isinstance(image, zarr.Array):
        ngff_image = to_ngff_image(image)
        multiscales = to_multiscales(ngff_image, method=method)
        to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
        return store

    if HAVE_TORCH:
        import torch
        if isinstance(image, torch.Tensor):
            ngff_image = to_ngff_image(image.numpy())
            multiscales = to_multiscales(ngff_image, method=method)
            to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
            return store

    # Todo: preserve dask Array, if present, check if dims are NGFF -> use dims, coords
    # Check if coords are uniform, if not, resample
    if HAVE_XARRAY:
        import xarray as xr
        if isinstance(image, xr.DataArray):
            # if HAVE_MULTISCALE_SPATIAL_IMAGE:
            #     from spatial_image import is_spatial_image
            #     if is_spatial_image(image):
            #         from multiscale_spatial_image import to_multiscale
            #         scale_factors = _spatial_image_scale_factors(image, min_length)
            #         multiscale = to_multiscale(image, scale_factors, method=method)
            #         return _make_multiscale_store(multiscale)

            return xarray_data_array_to_numpy(image)
        if isinstance(image, xr.Dataset):
            # da = image[next(iter(image.variables.keys()))]
            # if is_spatial_image(da):
            #     scale_factors = _spatial_image_scale_factors(da, min_length)
            #     multiscale = to_multiscale(da, scale_factors, method=method)
            #     return _make_multiscale_store(multiscale)
            return xarray_data_set_to_numpy(image)

    if isinstance(image, np.ndarray):
        ngff_image = to_ngff_image(image)
        multiscales = to_multiscales(ngff_image, method=method)
        to_ngff_zarr(store, multiscales, chunk_store=chunk_store)
        return store

    raise RuntimeError("Could not process the viewer image")


def _get_viewer_point_set(point_set):
    if HAVE_VTK:
        import vtk
        if isinstance(point_set, vtk.vtkPolyData):
            return vtk_polydata_to_vtkjs(point_set)
    if isinstance(point_set, dask.array.core.Array):
        return np.asarray(point_set)
    if HAVE_TORCH:
        import torch
        if isinstance(point_set, torch.Tensor):
            return point_set.numpy()
    if HAVE_XARRAY:
        import xarray as xr
        if isinstance(point_set, xr.DataArray):
            return xarray_data_array_to_numpy(point_set)
        if isinstance(point_set, xr.Dataset):
            return xarray_data_set_to_numpy(point_set)
    if HAVE_ITK:
        import itk
        if isinstance(point_set, itk.PointSet):
            return itk.array_from_vector_container(point_set.GetPoints())
    return point_set


def _detect_render_type(data, input_type) -> RenderType:
    if input_type == 'image' or input_type == 'label_image':
        return RenderType.IMAGE
    elif input_type == 'point_set':
        return RenderType.POINT_SET
    if isinstance(data, itkwasm.Image):
        return RenderType.IMAGE
    elif isinstance(data, itkwasm.PointSet):
        return RenderType.POINT_SET
    elif isinstance(data, (zarr.Array, zarr.Group)):
        # For now assume zarr.Group is an image
        # In the future, once NGFF supports point sets fully
        # We may need to do more introspection
        return RenderType.IMAGE
    elif isinstance(data, np.ndarray):
        if data.ndim == 2 and data.shape[1] < 4:
            return RenderType.POINT_SET
        else:
            return RenderType.IMAGE
    elif HAVE_ITK:
        import itk
        if isinstance(data, itk.Image):
            return RenderType.IMAGE
        elif isinstance(data, itk.PointSet):
            return RenderType.POINT_SET
    if HAVE_MULTISCALE_SPATIAL_IMAGE:
        from multiscale_spatial_image import MultiscaleSpatialImage
        if isinstance(data, MultiscaleSpatialImage):
            return RenderType.IMAGE
    if HAVE_VTK:
        import vtk
        if isinstance(data, vtk.vtkImageData):
            return RenderType.IMAGE
        elif isinstance(data, vtk.vtkPolyData):
            return RenderType.POINT_SET
    if isinstance(data, dask.array.core.Array):
        if data.ndim ==2 and data.shape[1] < 4:
            return RenderType.POINT_SET
        else:
            return RenderType.IMAGE
    if HAVE_TORCH:
        import torch
        if isinstance(data, torch.Tensor):
            if data.dim == 2 and data.shape[1] < 4:
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
    if HAVE_XARRAY:
        import xarray as xr
        if isinstance(data, xr.DataArray):
            if data.dims == 2 and data.shape[1] < 4:
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
        if isinstance(data, xr.Dataset):
            if data.dims == 2 and data.shape[1] < 4:
                return RenderType.POINT_SET
            else:
                return RenderType.IMAGE
