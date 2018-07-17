import os
import six

import traitlets
import itk
import numpy as np
try:
    import zstandard as zstd
except ImportError:
    import zstd
try:
    from functools import reduce
except ImportError:
    pass

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

class ITKImage(traitlets.TraitType):
    """A trait type holding an itk.Image object"""

    info_text = 'An N-dimensional, potentially multi-component, scientific ' + \
    'image with origin, spacing, and direction metadata'

    # Hold a reference to the source object to use with shallow views
    _source_object = None

    def validate(self, obj, value):
        if is_arraylike(value):
            array = np.asarray(value)
            self._source_object = array
            image_from_array = itk.GetImageViewFromArray(array)
            return image_from_array
        elif have_vtk and isinstance(value, vtk.vtkImageData):
            from vtk.util import numpy_support as vtk_numpy_support
            array = vtk_numpy_support.vtk_to_numpy(value.GetPointData().GetScalars())
            array.shape = tuple(value.GetDimensions())[::-1]
            self._source_object = array
            image_from_array = itk.GetImageViewFromArray(array)
            image_from_array.SetSpacing(value.GetSpacing())
            image_from_array.SetOrigin(value.GetOrigin())
            return image_from_array
        elif have_imglyb and isinstance(value,
                imglyb.util.ReferenceGuardingRandomAccessibleInterval):
            array = imglyb.to_numpy(value)
            self._source_object = array
            image_from_array = itk.GetImageViewFromArray(array)
            return image_from_array

        try:
            # an itk.Image or a filter that produces an Image
            # return itk.output(value)
            # Working around traitlets / ipywidgets update mechanism to
            # force an update. While the result of __eq__ can indicate it is
            # the same object, the actual contents may have changed, as
            # indicated by image.GetMTime()
            value = itk.output(value)
            self._source_object = value
            grafted = value.__New_orig__()
            grafted.Graft(value)
            return grafted
        except:
            self.error(obj, value)

def _image_to_type(itkimage):
    component_str = repr(itkimage).split('itkImagePython.')[1].split(';')[0][8:]
    if component_str[:2] == 'UL':
        if os.name == 'nt':
            return 'uint32_t',
        else:
            return 'uint64_t',
    mangle = None
    pixelType = 1
    if component_str[:2] == 'SL':
        if os.name == 'nt':
            return 'int32_t', 1,
        else:
            return 'int64_t', 1,
    if component_str[0] == 'V':
        # Vector
        mangle = component_str[1]
        pixelType = 5
    elif component_str[:2] == 'CF':
        # complex flot
        return 'float', 10
    elif component_str[:2] == 'CD':
        # complex flot
        return 'double', 10
    elif component_str[0] == 'C':
        # CovariantVector
        mangle = component_str[1]
        pixelType = 7
    elif component_str[0] == 'O':
        # Offset
        return 'int64_t', 4
    elif component_str[:2] == 'FA':
        # FixedArray
        mangle = component_str[2]
        pixelType = 11
    elif component_str[:4] == 'RGBA':
        # RGBA
        mangle = component_str[4:-1]
        pixelType = 3
    elif component_str[:3] == 'RGB':
        # RGB
        mangle = component_str[3:-1]
        pixelType = 2
    elif component_str[:4] == 'SSRT':
        # SymmetricSecondRankTensor
        mangle = component_str[4:-1]
        pixelType = 8
    else:
        mangle = component_str[:-1]
    _python_to_js = {
        'SC':'int8_t',
        'UC':'uint8_t',
        'SS':'int16_t',
        'US':'uint16_t',
        'SI':'int32_t',
        'UI':'uint32_t',
        'F':'float',
        'D':'double',
        'B':'uint8_t'
        }
    return _python_to_js[mangle], pixelType

def itkimage_to_json(itkimage, manager=None):
    """Serialize a Python itk.Image object.

    Attributes of this dictionary are to be passed to the JavaScript itkimage
    constructor.
    """
    if itkimage is None:
        return None
    else:
        direction = itkimage.GetDirection()
        directionMatrix = direction.GetVnlMatrix()
        directionList = []
        dimension = itkimage.GetImageDimension()
        pixelArr = itk.GetArrayViewFromImage(itkimage)
        compressor = zstd.ZstdCompressor(level=3)
        compressed = compressor.compress(pixelArr.data)
        pixelArrCompressed = memoryview(compressed)
        for col in range(dimension):
            for row in range(dimension):
                directionList.append(directionMatrix.get(row, col))
        componentType, pixelType = _image_to_type(itkimage)
        imageType = dict(
                dimension=dimension,
                componentType=componentType,
                pixelType=pixelType,
                components=itkimage.GetNumberOfComponentsPerPixel()
                )
        return dict(
            imageType=imageType,
            origin=tuple(itkimage.GetOrigin()),
            spacing=tuple(itkimage.GetSpacing()),
            size=tuple(itkimage.GetBufferedRegion().GetSize()),
            direction={'data': directionList,
                'rows': dimension,
                'columns': dimension},
            compressedData=pixelArrCompressed
        )


def _type_to_image(jstype):
    _pixelType_to_prefix = {
        1:'',
        2:'RGB',
        3:'RGBA',
        4:'O',
        5:'V',
        7:'CV',
        8:'SSRT',
        11:'FA'
        }
    pixelType = jstype['pixelType']
    dimension = jstype['dimension']
    if pixelType == 10:
        if jstype['componentType'] == 'float':
            return itk.Image[itk.complex, itk.F], np.float32
        else:
            return itk.Image[itk.complex, itk.D], np.float64

    def _long_type():
        if os.name == 'nt':
            return 'LL'
        else:
            return 'L'
    prefix = _pixelType_to_prefix[pixelType]
    _js_to_python = {
        'int8_t':'SC',
        'uint8_t':'UC',
        'int16_t':'SS',
        'uint16_t':'US',
        'int32_t':'SI',
        'uint32_t':'UI',
        'int64_t':'S' + _long_type(),
        'uint64_t':'U' + _long_type(),
        'float': 'F',
        'double': 'D'
        }
    _js_to_numpy_dtype = {
        'int8_t': np.int8,
        'uint8_t': np.uint8,
        'int16_t': np.int16,
        'uint16_t': np.uint16,
        'int32_t': np.int32,
        'uint32_t': np.uint32,
        'int64_t': np.int64,
        'uint64_t': np.uint64,
        'float': np.float32,
        'double': np.float64
        }
    dtype = _js_to_numpy_dtype[jstype['componentType']]
    if pixelType != 4:
        prefix += _js_to_python[jstype['componentType']]
    if pixelType not in (1, 2, 3, 10):
        prefix += str(dimension)
    prefix += str(dimension)
    return getattr(itk.Image, prefix), dtype

def itkimage_from_json(js, manager=None):
    """Deserialize a Javascript itk.js Image object."""
    if js is None:
        return None
    else:
        ImageType, dtype = _type_to_image(js['imageType'])
        decompressor = zstd.ZstdDecompressor()
        if six.PY2:
            asBytes = js['compressedData'].tobytes()
            pixelBufferArrayCompressed = np.frombuffer(asBytes, dtype=dtype)
        else:
            pixelBufferArrayCompressed = np.frombuffer(js['compressedData'], dtype=dtype)
        pixelCount = reduce(lambda x, y: x*y, js['size'], 1)
        numberOfBytes = pixelCount * js['imageType']['components'] * np.dtype(dtype).itemsize
        pixelBufferArray = \
            np.frombuffer(decompressor.decompress(pixelBufferArrayCompressed,
                numberOfBytes),
                    dtype=dtype)
        pixelBufferArray.shape = js['size'][::-1]
        image = itk.PyBuffer[ImageType].GetImageFromArray(pixelBufferArray)
        Dimension = image.GetImageDimension()
        image.SetOrigin(js['origin'])
        image.SetSpacing(js['spacing'])
        direction = image.GetDirection()
        directionMatrix = direction.GetVnlMatrix()
        directionJs = js['direction']['data']
        for col in range(Dimension):
            for row in range(Dimension):
                directionMatrix.put(row, col, directionJs[col + row * Dimension])
        return image

itkimage_serialization = {
    'from_json': itkimage_from_json,
    'to_json': itkimage_to_json
}
