import itk
import numpy as np
import pytest

from itkwidgets._transform_types import to_point_set, to_geometry, to_itk_image


def test_mesh_to_geometry():
    # 3D
    Dimension = 3
    PixelType = itk.ctype('double')
    MeshType = itk.Mesh[PixelType, Dimension]
    mesh = MeshType.New()
    PointType = itk.Point[itk.F, Dimension]
    point0 = PointType()
    point0[0] = -1
    point0[1] = -1
    point0[2] = 0
    mesh.SetPoint(0, point0)
    mesh.SetPointData(0, 8.0)
    point1 = PointType()
    point1[0] = 1
    point1[1] = -1
    point1[2] = 0
    mesh.SetPointData(1, 9.0)
    mesh.SetPoint(1, point1)
    point2 = PointType()
    point2[0] = 1
    point2[1] = 1
    point2[2] = 0
    mesh.SetPoint(2, point2)
    mesh.SetPointData(2, 19.0)
    point3 = PointType()
    point3[0] = 1
    point3[1] = 1
    point3[2] = 0
    mesh.SetPoint(3, point3)
    mesh.SetPointData(3, 24.0)

    geometry = to_geometry(mesh)

    points = mesh.GetPoints()
    point_template = itk.template(points)
    element_type = point_template[1][1]
    point_values = itk.PyVectorContainer[element_type].array_from_vector_container(
        points)

    assert(geometry['vtkClass'] == 'vtkPolyData')
    assert(geometry['points']['vtkClass'] == 'vtkPoints')
    assert(geometry['points']['numberOfComponents'] == 3)
    assert(geometry['points']['dataType'] == 'Float32Array')
    assert(geometry['points']['size'] == 4 * 3)
    assert(np.array_equal(geometry['points']['values'],
                          point_values.astype(np.float32)))
    assert(geometry['pointData']['vtkClass'] == 'vtkDataSetAttributes')
    assert(geometry['pointData']['arrays'][0]
           ['data']['vtkClass'] == 'vtkDataArray')
    assert(geometry['pointData']['arrays'][0]['data']['name'] == 'Point Data')
    assert(geometry['pointData']['arrays'][0]
           ['data']['numberOfComponents'] == 1)
    assert(geometry['pointData']['arrays'][0]['data']['size'] == 4)
    assert(geometry['pointData']['arrays'][0]
           ['data']['dataType'] == 'Float64Array')
    assert(np.array_equal(geometry['pointData']['arrays'][0]['data']['values'],
                          np.array([8.0, 9.0, 19.0, 24.0], dtype=np.float64)))

    # todo: 2D test
    # geometry_array.resize((number_of_points, 2))
    # geometry = to_geometry(geometry_array)
    # assert(geometry['vtkClass'] == 'vtkPolyData')
    # assert(geometry['points']['vtkClass'] == 'vtkPoints')
    # assert(geometry['points']['numberOfComponents'] == 3)
    # assert(geometry['points']['dataType'] == 'Float32Array')
    # assert(geometry['points']['size'] == number_of_points * 3)

    # geometry_array.resize((number_of_points, 3))
    # geometry_array[:,2] = 0.0
    # assert(np.alltrue(geometry['points']['values'] ==
    # geometry_array.astype(np.float32)))


def test_vtkpolydata_to_geometry():
    vtk = pytest.importorskip("vtk")
    from vtk.util.numpy_support import vtk_to_numpy

    cone_source = vtk.vtkConeSource()
    cone_source.Update()
    cone = cone_source.GetOutput()

    points = cone.GetPoints()
    point_scalars = vtk.vtkFloatArray()
    for ii in range(points.GetNumberOfPoints()):
        point_scalars.InsertTuple1(ii, ii)
    cone.GetPointData().SetScalars(point_scalars)

    cell_scalars = vtk.vtkFloatArray()
    for ii in range(cone.GetNumberOfCells()):
        cell_scalars.InsertTuple1(ii, ii)
    cone.GetCellData().SetScalars(cell_scalars)

    geometry = to_geometry(cone)

    assert(geometry['vtkClass'] == 'vtkPolyData')

    assert(geometry['points']['vtkClass'] == 'vtkPoints')
    assert(geometry['points']['numberOfComponents'] == 3)
    assert(geometry['points']['dataType'] == 'Float32Array')
    assert(geometry['points']['size'] == points.GetNumberOfPoints() * 3)
    assert(np.array_equal(geometry['points']['values'],
                          vtk_to_numpy(points.GetData()).astype(np.float32).ravel()))

    polys = cone.GetPolys()
    assert(geometry['polys']['vtkClass'] == 'vtkCellArray')
    assert(geometry['polys']['numberOfComponents'] == 1)
    assert(geometry['polys']['dataType'] == 'Uint32Array')
    assert(geometry['polys']['size'] == polys.GetData().GetNumberOfValues())
    assert(np.array_equal(geometry['polys']['values'],
                          vtk_to_numpy(polys.GetData()).astype(np.uint32).ravel()))

    assert(geometry['pointData']['vtkClass'] == 'vtkDataSetAttributes')
    assert(geometry['pointData']['arrays'][0]
           ['data']['vtkClass'] == 'vtkDataArray')
    assert(geometry['pointData']['arrays'][0]
           ['data']['numberOfComponents'] == 1)
    assert(geometry['pointData']['arrays'][0]['data']['size'] == 7)
    assert(geometry['pointData']['arrays'][0]
           ['data']['dataType'] == 'Float32Array')
    assert(np.array_equal(geometry['pointData']['arrays'][0]['data']['values'],
                          np.arange(points.GetNumberOfPoints(), dtype=np.float32)))

    assert(geometry['cellData']['vtkClass'] == 'vtkDataSetAttributes')
    assert(geometry['cellData']['arrays'][0]
           ['data']['vtkClass'] == 'vtkDataArray')
    assert(geometry['cellData']['arrays'][0]
           ['data']['numberOfComponents'] == 1)
    assert(geometry['cellData']['arrays'][0]['data']['size'] == 7)
    assert(geometry['cellData']['arrays'][0]
           ['data']['dataType'] == 'Float32Array')
    assert(np.array_equal(geometry['cellData']['arrays'][0]['data']['values'],
                          np.arange(cone.GetNumberOfCells(), dtype=np.float32)))


def test_itkpolylineparametricpath_to_geometry():
    Dimension = 2
    polyline = itk.PolyLineParametricPath[Dimension].New()
    polyline.AddVertex([3.0, 3.0])
    polyline.AddVertex([4.0, 7.0])
    polyline.AddVertex([5.0, 5.0])

    geometry = to_geometry(polyline)

    assert(geometry['vtkClass'] == 'vtkPolyData')
    assert(geometry['points']['vtkClass'] == 'vtkPoints')
    assert(geometry['points']['numberOfComponents'] == 3)
    assert(geometry['points']['dataType'] == 'Float32Array')
    assert(geometry['points']['size'] == 3 * 3)
    assert(np.array_equal(geometry['points']['values'],
                          np.array([3.0, 3.0, -5.0e-6, 4.0, 7.0, -5e-6, 5.0, 5.0, -5e-6]).astype(np.float32)))

    assert(geometry['verts']['vtkClass'] == 'vtkCellArray')
    assert(geometry['verts']['numberOfComponents'] == 1)
    assert(geometry['verts']['dataType'] == 'Uint32Array')
    assert(geometry['verts']['size'] == 6)
    assert(np.array_equal(geometry['verts']['values'],
                          [1, 0, 1, 1, 1, 2]))
    assert(geometry['lines']['vtkClass'] == 'vtkCellArray')
    assert(geometry['lines']['numberOfComponents'] == 1)
    assert(geometry['lines']['dataType'] == 'Uint32Array')
    assert(geometry['lines']['size'] == 6)
    assert(np.array_equal(geometry['lines']['values'],
                          [2, 0, 1, 2, 1, 2]))


gaussian_1_mean = [0.0, 0.0, 0.0]
gaussian_1_cov = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 0.5]]
gaussian_2_mean = [4.0, 6.0, 7.0]
gaussian_2_cov = [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.5]]


def test_numpy_array_to_point_set():
    number_of_points = 10
    point_set_array = np.random.multivariate_normal(gaussian_1_mean, gaussian_1_cov,
                                                    number_of_points)

    # 3D
    point_set = to_point_set(point_set_array)
    assert(point_set['vtkClass'] == 'vtkPolyData')
    assert(point_set['points']['vtkClass'] == 'vtkPoints')
    assert(point_set['points']['numberOfComponents'] == 3)
    assert(point_set['points']['dataType'] == 'Float32Array')
    assert(point_set['points']['size'] == number_of_points * 3)
    assert(np.array_equal(point_set['points']['values'],
                          point_set_array.astype(np.float32)))

    # 2D
    point_set_array.resize((number_of_points, 2))
    point_set = to_point_set(point_set_array)
    assert(point_set['vtkClass'] == 'vtkPolyData')
    assert(point_set['points']['vtkClass'] == 'vtkPoints')
    assert(point_set['points']['numberOfComponents'] == 3)
    assert(point_set['points']['dataType'] == 'Float32Array')
    assert(point_set['points']['size'] == number_of_points * 3)

    point_set_array = np.hstack(
        (point_set_array, -5.0e-6 * np.ones((point_set_array.shape[0], 1)))).astype(np.float32)
    assert(np.alltrue(point_set['points']['values'] ==
                      point_set_array.astype(np.float32)))


def test_non_contiguous_array():
    "Check that a non-contiguous array raises the appropriate error"

    data = np.random.random((10, 10, 10))
    data = data[..., 0]   # slicing the array makes it non-contiguous
    output = to_itk_image(data)
    assert isinstance(output, itk.Image)
