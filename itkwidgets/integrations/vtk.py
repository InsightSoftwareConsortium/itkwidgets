HAVE_VTK = False
try:
    import vtk
    HAVE_VTK = True
    from vtk.util.numpy_support import vtk_to_numpy
except ImportError:
    pass

from spatial_image import to_spatial_image


def vtk_image_to_spatial_image(image):
    array = vtk_to_numpy(image.GetPointData().GetScalars())
    dimensions = list(image.GetDimensions())
    array.shape = dimensions[::-1]

    origin = image.GetOrigin()
    translation = { 'x': origin[0], 'y': origin[1], 'z': origin[2] }

    spacing = image.GetSpacing()
    scale = { 'x': spacing[0], 'y': spacing[1], 'z': spacing[2] }

    spatial_image = to_spatial_image(array, scale=scale, translation=translation)

    return spatial_image

def vtk_polydata_to_vtkjs(point_set):
    array = vtk_to_numpy(point_set.GetPoints().GetData())
    return array
