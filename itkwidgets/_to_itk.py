__all__ = ['to_itk_image']

import itk
import numpy as np

def is_arraylike(arr):
    return hasattr(arr, 'shape') and \
        hasattr(arr, 'dtype') and \
        hasattr(arr, '__array__') and \
        hasattr(arr, 'ndim')

have_imglyb = False
try:
    import imglyb
    have_imglyb = True
except ImportError:
    pass
have_vtk = False
try:
    import vtk
    have_vtk = True
except ImportError:
    pass
have_dask = False
try:
    import dask.array
    have_dask = True
except ImportError:
    pass

def to_itk_image(other_image_datatype):
    if is_arraylike(other_image_datatype):
        array = np.asarray(other_image_datatype)
        case_use_view = array.flags['OWNDATA']
        if have_dask and isinstance(other_image_datatype, dask.array.core.Array):
            case_use_view = False
        if case_use_view:
            image_from_array = itk.GetImageViewFromArray(array)
        else:
            image_from_array = itk.GetImageFromArray(array)
        return image_from_array
    elif have_vtk and isinstance(other_image_datatype, vtk.vtkImageData):
        from vtk.util import numpy_support as vtk_numpy_support
        array = vtk_numpy_support.vtk_to_numpy(other_image_datatype.GetPointData().GetScalars())
        array.shape = tuple(other_image_datatype.GetDimensions())[::-1]
        image_from_array = itk.GetImageViewFromArray(array)
        image_from_array.SetSpacing(other_image_datatype.GetSpacing())
        image_from_array.SetOrigin(other_image_datatype.GetOrigin())
        return image_from_array
    elif have_imglyb and isinstance(other_image_datatype,
            imglyb.util.ReferenceGuardingRandomAccessibleInterval):
        array = imglyb.to_numpy(other_image_datatype)
        image_from_array = itk.GetImageViewFromArray(array)
        return image_from_array

    return None
