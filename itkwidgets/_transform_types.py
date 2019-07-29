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

_itk_pixel_to_vtkjs_type_components = {
    itk.SC: ('Int8Array', 1),
    itk.UC: ('Uint8Array', 1),
    itk.SS: ('Int16Array', 1),
    itk.US: ('Uint16Array', 1),
    itk.SI: ('Int32Array', 1),
    itk.UI: ('Uint32Array', 1),
    itk.F: ('Float32Array', 1),
    itk.D: ('Float64Array', 1),
    }
def _vtk_to_vtkjs(data_array):
    from vtk.util.numpy_support import vtk_to_numpy
    # From vtkType.h
    _vtk_data_type_to_vtkjs_type = {
        2: 'Int8Array',
        15: 'Int8Array',
        3: 'Uint8Array',
        4: 'Int16Array',
        5: 'Uint16Array',
        6: 'Int32Array',
        7: 'Uint32Array',
        8: 'BigInt64Array',
        9: 'BigUint64Array',
        10: 'Float32Array',
        11: 'Float64Array',
        16: 'BigInt64Array',
        17: 'BigUint64Array',
        }
    vtk_data_type = data_array.GetDataType()
    data_type = _vtk_data_type_to_vtkjs_type[vtk_data_type]
    numpy_array = vtk_to_numpy(data_array)
    if vtk_data_type == 8 or vtk_data_type == 16:
        ii32 = np.iinfo(np.int32)
        value_range = data_array.GetValueRange()
        if value_range[0] < ii32.min or value_range[1] > ii32.max:
            raise ValueError('64 integers are not supported yet by WebGL / vtk.js')
        numpy_array = numpy_array.astype(np.int32)
        data_type = 'Int32Array'
    elif vtk_data_type == 9 or vtk_data_type == 17:
        ui32 = np.iinfo(np.uint32)
        value_range = data_array.GetValueRange()
        if value_range[0] < ui32.min or value_range[1] > ui32.max:
            raise ValueError('64 integers are not supported by WebGL / vtk.js yet')
        numpy_array = numpy_array.astype(np.uint32)
        data_type = 'Uint32Array'

    return data_type, numpy_array

def _vtk_data_attributes_to_vtkjs(attributes):
    vtkjs_attributes = { "vtkClass": "vtkDataSetAttributes" }
    arrays = []
    for array_index in range(attributes.GetNumberOfArrays()):
        vtk_array = attributes.GetArray(array_index)
        data_type, values = _vtk_to_vtkjs(vtk_array)
        array = { "data": {
            'vtkClass': 'vtkDataArray',
            'name': vtk_array.GetName(),
            'numberOfComponents': vtk_array.GetNumberOfComponents(),
            'size': vtk_array.GetSize(),
            'dataType': data_type,
            'values': values } }
        scalars = attributes.GetScalars()
        if scalars and scalars.GetName() == vtk_array.GetName():
            vtkjs_attributes['activeScalars'] = array_index
        globalIds = attributes.GetGlobalIds()
        if globalIds and globalIds.GetName() == vtk_array.GetName():
            vtkjs_attributes['activeGlobalIds'] = array_index
        normals = attributes.GetNormals()
        if normals and normals.GetName() == vtk_array.GetName():
            vtkjs_attributes['activeNormals'] = array_index
        pedigreeIds = attributes.GetPedigreeIds()
        if pedigreeIds and pedigreeIds.GetName() == vtk_array.GetName():
            vtkjs_attributes['activePedigreeIds'] = array_index
        tCoords = attributes.GetTCoords()
        if tCoords and tCoords.GetName() == vtk_array.GetName():
            vtkjs_attributes['activeTCoords'] = array_index
        vectors = attributes.GetVectors()
        if vectors and vectors.GetName() == vtk_array.GetName():
            vtkjs_attributes['activeVectors'] = array_index
        arrays.append(array)
    vtkjs_attributes["arrays"] = arrays
    return vtkjs_attributes

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
    elif have_vtk and isinstance(point_set_like, vtk.vtkPolyData):
        from vtk.util.numpy_support import vtk_to_numpy
        point_set = { 'vtkClass': 'vtkPolyData' }

        points_data = vtk_to_numpy(point_set_like.GetPoints().GetData())
        points_data = points_data.astype(np.float32).ravel()
        points = { 'vtkClass': 'vtkPoints',
                   'name': '_points',
                   'numberOfComponents': 3,
                   'dataType': 'Float32Array',
                   'size': points_data.size,
                   'values': points_data }
        point_set['points'] = points

        vtk_verts = point_set_like.GetVerts()
        if vtk_verts.GetNumberOfCells():
            data = vtk_to_numpy(vtk_verts.GetData())
            data = data.astype(np.uint32).ravel()
            cells = { 'vtkClass': 'vtkCellArray',
                      'name': '_' + 'verts',
                      'numberOfComponents': 1,
                      'size': data.size,
                      'dataType': 'Uint32Array',
                      'values': data }
            point_set['verts'] = cells
        vtk_point_data = point_set_like.GetPointData()
        if vtk_point_data and vtk_point_data.GetNumberOfArrays():
            vtkjs_point_data = _vtk_data_attributes_to_vtkjs(vtk_point_data)
            point_set['pointData'] = vtkjs_point_data

        vtk_cell_data = point_set_like.GetCellData()
        if vtk_cell_data and vtk_cell_data.GetNumberOfArrays():
            vtkjs_cell_data = _vtk_data_attributes_to_vtkjs(vtk_cell_data)
            point_set['cellData'] = vtkjs_cell_data

        return point_set

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

        itk_point_data = itk_polydata.GetPointData()
        if itk_point_data and itk_point_data.Size():
            pixel_type = itk.template(itk_polydata)[1][0]
            data_type, number_of_components = _itk_pixel_to_vtkjs_type_components[pixel_type]
            data = itk.PyVectorContainer[pixel_type].array_from_vector_container(itk_point_data)
            point_data = {
                "vtkClass": "vtkDataSetAttributes",
                "activeScalars": 0,
                "arrays": [
                    { "data": {
                        'vtkClass': 'vtkDataArray',
                        'name': 'Point Data',
                        'numberOfComponents': number_of_components,
                        'size': data.size,
                        'dataType': data_type,
                        'values': data }
                    } ],
                  }
            geometry['pointData'] = point_data
        itk_cell_data = itk_polydata.GetCellData()
        if itk_cell_data and itk_cell_data.Size():
            pixel_type = itk.template(itk_polydata)[1][0]
            data_type, number_of_components = _itk_pixel_to_vtkjs_type_components[pixel_type]
            data = itk.PyVectorContainer[pixel_type].array_from_vector_container(itk_cell_data)
            cell_data = {
                "vtkClass": "vtkDataSetAttributes",
                "activeScalars": 0,
                "arrays": [
                    { "data": {
                        'vtkClass': 'vtkDataArray',
                        'name': 'Cell Data',
                        'numberOfComponents': number_of_components,
                        'size': data.size,
                        'dataType': data_type,
                        'values': data }
                    } ],
                  }
            geometry['cellData'] = cell_data

        return geometry
    elif have_vtk and isinstance(geometry_like, vtk.vtkPolyData):
        from vtk.util.numpy_support import vtk_to_numpy

        geometry = { 'vtkClass': 'vtkPolyData' }

        points_data = vtk_to_numpy(geometry_like.GetPoints().GetData())
        points_data = points_data.astype(np.float32).ravel()
        points = { 'vtkClass': 'vtkPoints',
                   'name': '_points',
                   'numberOfComponents': 3,
                   'dataType': 'Float32Array',
                   'size': points_data.size,
                   'values': points_data }
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
        vtk_point_data = geometry_like.GetPointData()
        if vtk_point_data and vtk_point_data.GetNumberOfArrays():
            vtkjs_point_data = _vtk_data_attributes_to_vtkjs(vtk_point_data)
            geometry['pointData'] = vtkjs_point_data

        vtk_cell_data = geometry_like.GetCellData()
        if vtk_cell_data and vtk_cell_data.GetNumberOfArrays():
            vtkjs_cell_data = _vtk_data_attributes_to_vtkjs(vtk_cell_data)
            geometry['cellData'] = vtkjs_cell_data

        return geometry
    elif have_vtk and isinstance(geometry_like, (vtk.vtkUnstructuredGrid,
                                                 vtk.vtkStructuredGrid,
                                                 vtk.vtkRectilinearGrid,
                                                 vtk.vtkImageData)):
        geometry_filter = vtk.vtkGeometryFilter()
        geometry_filter.SetInputData(geometry_like)
        geometry_filter.Update()
        geometry = to_geometry(geometry_filter.GetOutput())
        return geometry

    return None
