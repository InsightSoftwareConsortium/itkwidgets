HAVE_VTK = False
try:
    import vtk
    HAVE_VTK = True
    from vtk.util.numpy_support import vtk_to_numpy
except ImportError:
    pass


def vtk_image_to_ndarray(image):
    array = vtk_to_numpy(image.GetPointData().GetScalars())
    dims = list(image.GetDimensions())
    array.shape = dims[::-1]
    return array

def vtk_polydata_to_vtkjs(point_set):
    array = vtk_to_numpy(point_set.GetPoints().GetData())
    return array
