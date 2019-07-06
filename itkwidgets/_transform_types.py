__all__ = ['to_itk_image', 'to_point_set']

import itk
import numpy as np

def is_arraylike(arr):
    return hasattr(arr, 'shape') and \
        hasattr(arr, 'dtype') and \
        hasattr(arr, '__array__') and \
        hasattr(arr, 'ndim')

have_imagej = False
try:
    import imagej
    have_imagej = True
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

def to_itk_image(image_like):
    if is_arraylike(image_like):
        array = np.asarray(image_like)
        case_use_view = array.flags['OWNDATA']
        if have_dask and isinstance(image_like, dask.array.core.Array):
            case_use_view = False
        if case_use_view:
            image_from_array = itk.image_view_from_array(array)
        else:
            image_from_array = itk.image_from_array(array)
        return image_from_array
    elif have_vtk and isinstance(image_like, vtk.vtkImageData):
        from vtk.util import numpy_support as vtk_numpy_support
        array = vtk_numpy_support.vtk_to_numpy(image_like.GetPointData().GetScalars())
        array.shape = tuple(image_like.GetDimensions())[::-1]
        image_from_array = itk.image_view_from_array(array)
        image_from_array.SetSpacing(image_like.GetSpacing())
        image_from_array.SetOrigin(image_like.GetOrigin())
        return image_from_array
    elif have_imagej:
        import imglyb
        if isinstance(image_like, imglyb.util.ReferenceGuardingRandomAccessibleInterval):
            array = imglyb.to_numpy(image_like)
            image_from_array = itk.image_view_from_array(array)
            return image_from_array

    return None

def to_point_set(point_set_like):
    if is_arraylike(point_set_like):
        point_values = np.asarray(point_set_like).astype(np.float32)
        if len(point_values.shape) > 1 and point_values.shape[1] == 2 or point_values.shape[1] == 3:
            if point_values.shape[1] == 2:
                point_values.resize((point_values.shape[0], 3))
                point_values[:,2] = 0.0
            point_set = { 'vtkClass': 'vtkPolyData' }
            points = { 'vtkClass': 'vtkPoints',
                       'numberOfComponents': 3,
                       'dataType': 'Float32Array',
                       'size': point_values.size,
                       'values': point_values }
            point_set['points'] = points
            return point_set
        else:
            return None

    return None
