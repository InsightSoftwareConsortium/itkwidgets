import itkwasm
import numpy as np
import zarr
from .itk import HAVE_ITK, itk_image_to_wasm_image
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


def _detect_render_type(data) -> RenderType:
    if isinstance(data, itkwasm.Image):
        return RenderType.IMAGE
    elif isinstance(data, np.ndarray):
        return RenderType.IMAGE
    elif isinstance(data, zarr.Group):
        return RenderType.IMAGE
    elif HAVE_ITK:
        import itk
        if isinstance(data, itk.Image):
            return RenderType.IMAGE