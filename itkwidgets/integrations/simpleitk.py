import importlib_metadata

HAVE_SIMPLEITK = False
try:
    importlib_metadata.metadata("SimpleITK")
    HAVE_SIMPLEITK = True
except importlib_metadata.PackageNotFoundError:
    pass

from ngff_zarr import to_ngff_image


def simpleitk_image_to_ngff_image(image):
    """Convert a SimpleITK image to an NGFF image.
    
    Parameters
    ----------
    image : sitk.Image
        The SimpleITK image to convert
        
    Returns
    -------
    NgffImage
        The converted NGFF image with proper spacing and origin
    """
    import SimpleITK as sitk
    
    # Get the numpy array from SimpleITK image
    # Note: SimpleITK has XYZ ordering, numpy has ZYX ordering
    array = sitk.GetArrayFromImage(image)
    
    # Get origin
    origin = image.GetOrigin()
    translation = {}
    if len(origin) >= 1:
        translation['x'] = origin[0]
    if len(origin) >= 2:
        translation['y'] = origin[1]
    if len(origin) >= 3:
        translation['z'] = origin[2]
    
    # Get spacing
    spacing = image.GetSpacing()
    scale = {}
    if len(spacing) >= 1:
        scale['x'] = spacing[0]
    if len(spacing) >= 2:
        scale['y'] = spacing[1]
    if len(spacing) >= 3:
        scale['z'] = spacing[2]
    
    # Create NGFF image with metadata
    ngff_image = to_ngff_image(array, scale=scale, translation=translation)
    
    return ngff_image
