__all__ = ['to_itk_image', 'to_point_set', 'to_geometry']

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
        array = np.ascontiguousarray(array)
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
                       'name': '_points',
                       'numberOfComponents': 3,
                       'dataType': 'Float32Array',
                       'size': point_values.size,
                       'values': point_values }
            point_set['points'] = points
            vert_values = np.ones((point_values.size * 2,), dtype=np.uint32)
            vert_values[1::2] = np.arange(point_values.size)
            verts = { 'vtkClass': 'vtkCellArray',
                       'name': '_verts',
                       'numberOfComponents': 1,
                       'dataType': 'Uint32Array',
                       'size': vert_values.size,
                       'values': vert_values }
            point_set['verts'] = verts
            return point_set
        else:
            return None

    return None

def to_geometry(geometry_like):
    if isinstance(geometry_like, itk.Mesh):
        if not hasattr(itk, 'PyVectorContainer'):
            raise ModuleNotFoundError('itk.MeshToPolyDataFilter is not available -- install the itk-meshtopolydata package')
        itk_polydata = itk.mesh_to_poly_data_filter(geometry_like)

        geometry = { 'vtkClass': 'vtkPolyData' }

        points = itk_polydata.GetPoints()
        point_template = itk.template(points)
        element_type = point_template[1][1]
        # todo: test array_view here and below
        point_values = itk.PyVectorContainer[element_type].array_from_vector_container(points)
        if len(point_values.shape) > 1 and point_values.shape[1] == 2 or point_values.shape[1] == 3:
            if point_values.shape[1] == 2:
                point_values.resize((point_values.shape[0], 3))
                point_values[:,2] = 0.0
            points = { 'vtkClass': 'vtkPoints',
                       'numberOfComponents': 3,
                       'dataType': 'Float32Array',
                       'size': point_values.size,
                       'values': point_values }
            geometry['points'] = points
        else:
            return None

        itk_verts = itk_polydata.GetVertices()
        itk_lines = itk_polydata.GetLines()
        itk_polys = itk_polydata.GetPolygons()
        itk_strips = itk_polydata.GetTriangleStrips()
        for cell_type, itk_cells in [('verts', itk_verts), ('lines', itk_lines),
                ('polys', itk_polys), ('strips', itk_strips)]:
            if itk_cells.Size():
                data = itk.PyVectorContainer[itk.UI].array_from_vector_container(itk_cells)
                cells = { 'vtkClass': 'vtkCellArray',
                          'name': '_' + cell_type,
                          'numberOfComponents': 1,
                          'size': data.size,
                          'dataType': 'Uint32Array',
                          'values': data }
                geometry[cell_type] = cells

        return geometry
    elif have_vtk and isinstance(geometry_like, vtk.vtkPolyData):
        from vtk.util.numpy_support import vtk_to_numpy

        geometry = { 'vtkClass': 'vtkPolyData' }

        point_data = vtk_to_numpy(geometry_like.GetPoints().GetData())
        point_data = point_data.astype(np.float32).ravel()
        points = { 'vtkClass': 'vtkPoints',
                   'name': '_points',
                   'numberOfComponents': 3,
                   'dataType': 'Float32Array',
                   'size': point_data.size,
                   'values': point_data }
        geometry['points'] = points

        vtk_verts = geometry_like.GetVerts()
        vtk_lines = geometry_like.GetLines()
        vtk_polys = geometry_like.GetPolys()
        vtk_strips = geometry_like.GetStrips()
        for cell_type, vtk_cells in [('verts', vtk_verts), ('lines', vtk_lines),
                ('polys', vtk_polys), ('strips', vtk_strips)]:
            if vtk_cells.GetNumberOfCells():
                data = vtk_to_numpy(vtk_cells.GetData())
                data = data.astype(np.uint32).ravel()
                cells = { 'vtkClass': 'vtkCellArray',
                          'name': '_' + cell_type,
                          'numberOfComponents': 1,
                          'size': data.size,
                          'dataType': 'Uint32Array',
                          'values': data }
                geometry[cell_type] = cells

        return geometry

    return None
