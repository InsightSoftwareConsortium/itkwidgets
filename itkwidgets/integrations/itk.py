import itkwasm

from packaging import version
HAVE_ITK = False
try:
    import itk
    if not hasattr(itk, '__version__') or version.parse(itk.__version__) < version.parse('5.3.0'):
      raise RuntimeError('itk 5.3rc4 or newer is required. `pip install --upgrade --pre itk`')
    HAVE_ITK = True
except ImportError:
    pass
    

if HAVE_ITK:
    def itk_image_to_wasm_image(image):
        image_dict = itk.dict_from_image(image)
        wasm_image = itkwasm.Image(**image_dict)
        return wasm_image

    def itk_group_spatial_object_to_wasm_point_set(point_set):
        point_set_dict = itk.dict_from_pointset(point_set)
        wasm_point_set = itkwasm.PointSet(**point_set_dict)
        return wasm_point_set

else:
    def itk_image_to_wasm_image(image):
        raise RuntimeError('itk 5.3rc4 or newer is required. `pip install --upgrade --pre itk`')

    def itk_group_spatial_object_to_wasm_point_set(point_set):
        raise RuntimeError('itk 5.3rc4 or newer is required. `pip install --upgrade --pre itk`')
