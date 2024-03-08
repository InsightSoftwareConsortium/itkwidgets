import itkwasm

from packaging import version
import importlib_metadata
HAVE_ITK = False
try:
    itk_version = importlib_metadata.version('itk-core')
    if version.parse(itk_version) < version.parse('5.3.0'):
        raise RuntimeError('itk 5.3 or newer is required. `pip install itk>=5.3.0`')
    HAVE_ITK = True
except importlib_metadata.PackageNotFoundError:
    pass


if HAVE_ITK:
    def itk_group_spatial_object_to_wasm_point_set(point_set):
        import itk
        point_set_dict = itk.dict_from_pointset(point_set)
        wasm_point_set = itkwasm.PointSet(**point_set_dict)
        return wasm_point_set

else:
    def itk_group_spatial_object_to_wasm_point_set(point_set):
        raise RuntimeError('itk 5.3 or newer is required. `pip install itk>=5.3.0`')
