import itkwasm
import numpy as np
import zarr
from .itk import HAVE_ITK, itk_image_to_wasm_image, itk_group_spatial_object_to_wasm_point_set
from ..render_types import RenderType

_image_count = 1

async def _set_viewer_image(itk_viewer, image, name=None):
    global _image_count
    if isinstance(image, itkwasm.Image):
        if not name:
            name = image.name
            if not name:
                name = f"image {_image_count}"
                _image_count += 1
        await itk_viewer.setImage(image, name)
    elif isinstance(image, np.ndarray):
        if not name:
            name = f"image {_image_count}"
            _image_count += 1
        await itk_viewer.setImage(image, name)
    elif isinstance(image, zarr.Group):
        if not name:
            name = f"image {_image_count}"
            _image_count += 1
        await itk_viewer.setImage(image, name)
    elif HAVE_ITK:
        import itk
        if isinstance(image, itk.Image):
            wasm_image = itk_image_to_wasm_image(image)
            name = image.GetObjectName()
            if not name:
                name = f"image {_image_count}"
                _image_count += 1
            await itk_viewer.setImage(wasm_image, name)


async def _set_viewer_point_sets(itk_viewer, point_sets):
    if isinstance(point_sets, itkwasm.PointSet):
        await itk_viewer.setPointSets(point_sets)
    elif isinstance(point_sets, np.ndarray):
        await itk_viewer.setPointSets(point_sets)
    elif isinstance(point_sets, zarr.Group):
        await itk_viewer.setPointSets(point_sets)
    elif HAVE_ITK:
        import itk
        if isinstance(point_sets, itk.GroupSpatialObject):
            wasm_point_sets = itk_group_spatial_object_to_wasm_point_set(point_sets)
            await itk_viewer.setPointSets(wasm_point_sets)


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
        elif isinstance(data, itk.GroupSpatialObject):
            return RenderType.POINT_SET
