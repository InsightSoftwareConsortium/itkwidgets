import os
import six
import collections

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

from ._transform_types import to_itk_image, to_point_set, to_geometry

class ITKImage(traitlets.TraitType):
    """A trait type holding an itk.Image object"""

    info_text = 'An N-dimensional, potentially multi-component, scientific ' + \
    'image with origin, spacing, and direction metadata'

    # Hold a reference to the source object to use with shallow views
    _source_object = None

    def validate(self, obj, value):
        self._source_object = value

        image_from_array = to_itk_image(value)
        if image_from_array:
            return image_from_array

        try:
            # an itk.Image or a filter that produces an Image
            # return itk.output(value)
            # Working around traitlets / ipywidgets update mechanism to
            # force an update. While the result of __eq__ can indicate it is
            # the same object, the actual contents may have changed, as
            # indicated by image.GetMTime()
            value = itk.output(value)
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
        pixelArr = itk.array_view_from_image(itkimage)
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
            pixelBufferArrayCompressed = np.frombuffer(asBytes, dtype=np.uint8)
        else:
            pixelBufferArrayCompressed = np.frombuffer(js['compressedData'],
                    dtype=np.uint8)
        pixelCount = reduce(lambda x, y: x*y, js['size'], 1)
        numberOfBytes = pixelCount * js['imageType']['components'] * np.dtype(dtype).itemsize
        pixelBufferArray = \
            np.frombuffer(decompressor.decompress(pixelBufferArrayCompressed,
                numberOfBytes),
                    dtype=dtype)
        pixelBufferArray.shape = js['size'][::-1]
        # Workaround for GetImageFromArray required until 5.0.1
        # and https://github.com/numpy/numpy/pull/11739
        pixelBufferArrayCopyToBeRemoved = pixelBufferArray.copy()
        # image = itk.PyBuffer[ImageType].GetImageFromArray(pixelBufferArray)
        image = itk.PyBuffer[ImageType].GetImageFromArray(pixelBufferArrayCopyToBeRemoved)
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

class PolyDataList(traitlets.TraitType):
    """A trait type holding a list of Python data structures compatible with vtk.js.

    See: https://kitware.github.io/vtk-js/docs/structures_PolyData.html"""

    info_text = 'A data structure for rendering geometry in vtk.js ' + \
    'consisting of points, verts (vertices), lines, polys (polygons), ' + \
    'triangle strips, point data, and cell data.'

    # Hold a reference to the source object to use with shallow views
    _source_object = None

    def validate(self, obj, value):
        self._source_object = value

        # For convenience, support assigning a single geometry instead of a
        # list
        geometries = value
        if not isinstance(geometries, collections.Sequence) and not geometries is None:
            geometries = [geometries]

        try:
            for index, geometry in enumerate(geometries):
                if not isinstance(geometry, dict) or not 'vtkClass' in geometry:
                    geometries[index] = to_geometry(geometry)
            return geometries
        except:
            self.error(obj, value)

def polydata_list_to_json(polydata_list, manager=None):
    """Serialize a list of a Python object that represents vtk.js PolyData.

    The returned data is compatibile with vtk.js PolyData with compressed data
    buffers.
    """
    if polydata_list is None:
        return None
    else:
        compressor = zstd.ZstdCompressor(level=3)

        json = []
        for polydata in polydata_list:
            json_polydata = dict()
            for top_key, top_value in polydata.items():
                if isinstance(top_value, dict):
                    nested_value_copy = dict()
                    for nested_key, nested_value in top_value.items():
                        if not nested_key == 'values':
                            nested_value_copy[nested_key] = nested_value
                    json_polydata[top_key] = nested_value_copy
                else:
                    json_polydata[top_key] = top_value

            if 'points' in json_polydata:
                point_values = polydata['points']['values']
                compressed = compressor.compress(point_values.data)
                compressedView = memoryview(compressed)
                json_polydata['points']['compressedValues'] = compressedView

            for cell_type in ['verts', 'lines', 'polys', 'strips']:
                if cell_type in json_polydata:
                    values = polydata[cell_type]['values']
                    compressed = compressor.compress(values.data)
                    compressedView = memoryview(compressed)
                    json_polydata[cell_type]['compressedValues'] = compressedView

            for data_type in ['pointData', 'cellData']:
                if data_type in json_polydata:
                    data = polydata[data_type]
                    compressed_data = dict()
                    for nested_key, nested_value in data.items():
                        if not nested_key == 'arrays':
                            compressed_data[nested_key] = nested_value
                    compressed_arrays = []
                    for array in polydata[data_type]['arrays']:
                        compressed_array = dict()
                        for nested_key, nested_value in array['data'].items():
                            if not nested_key == 'values':
                                compressed_array[nested_key] = nested_value
                        values = array['data']['values']
                        compressed = compressor.compress(values.data)
                        compressedView = memoryview(compressed)
                        compressed_array['compressedValues'] = compressedView
                        compressed_arrays.append({ 'data': compressed_array })
                    compressed_data['arrays'] = compressed_arrays
                    json_polydata[data_type] = compressed_data

            json.append(json_polydata)
        return json

def _type_to_numpy(jstype):
    _js_to_numpy_dtype = {
            'Int8Array': np.int8,
            'Uint8Array': np.uint8,
            'Int16Array': np.int16,
            'Uint16Array': np.uint16,
            'Int32Array': np.int32,
            'Uint32Array': np.uint32,
            'BigInt64Array': np.int64,
            'BigUint64Array': np.uint64,
            'Float32Array': np.float32,
            'Float64Array': np.float64
            }
    return _js_to_numpy_dtype[jstype]

def polydata_list_from_json(js, manager=None):
    """Deserialize a Javascript vtk.js PolyData object.

    Decompresses data buffers.
    """
    if js is None:
        return None
    else:
        decompressor = zstd.ZstdDecompressor()

        polydata_list = []
        for json_polydata in js:
            polydata = dict()
            for top_key, top_value in json_polydata.items():
                if isinstance(top_value, dict):
                    nested_value_copy = dict()
                    for nested_key, nested_value in top_value.items():
                        if not nested_key == 'compressedValues':
                            nested_value_copy[nested_key] = nested_value
                    polydata[top_key] = nested_value_copy
                else:
                    polydata[top_key] = top_value

            if 'points' in polydata:
                dtype = _type_to_numpy(polydata['points']['dataType'])
                if six.PY2:
                    asBytes = json_polydata['points']['compressedValues'].tobytes()
                    valuesBufferArrayCompressed = np.frombuffer(asBytes, dtype=np.uint8)
                else:
                    valuesBufferArrayCompressed = np.frombuffer(json_polydata['points']['compressedValues'],
                            dtype=np.uint8)
                numberOfBytes = json_polydata['points']['size'] * np.dtype(dtype).itemsize
                valuesBufferArray = \
                    np.frombuffer(decompressor.decompress(valuesBufferArrayCompressed,
                        numberOfBytes),
                            dtype=dtype)
                valuesBufferArray.shape = (int(json_polydata['points']['size'] / 3), 3)
                polydata['points']['values'] = valuesBufferArray

            for cell_type in ['verts', 'lines', 'polys', 'strips']:
                if cell_type in polydata:
                    dtype = _type_to_numpy(polydata[cell_type]['dataType'])
                    if six.PY2:
                        asBytes = json_polydata[cell_type]['compressedValues'].tobytes()
                        valuesBufferArrayCompressed = np.frombuffer(asBytes, dtype=np.uint8)
                    else:
                        valuesBufferArrayCompressed = np.frombuffer(json_polydata[cell_type]['compressedValues'],
                                dtype=np.uint8)
                    numberOfBytes = json_polydata[cell_type]['size'] * np.dtype(dtype).itemsize
                    valuesBufferArray = \
                        np.frombuffer(decompressor.decompress(valuesBufferArrayCompressed,
                            numberOfBytes),
                                dtype=dtype)
                    valuesBufferArray.shape = (json_polydata[cell_type]['size'],)
                    polydata[cell_type]['values'] = valuesBufferArray

            for data_type in ['pointData', 'cellData']:
                if data_type in polydata:
                    data = json_polydata[data_type]
                    decompressed_data = dict()
                    for nested_key, nested_value in data.items():
                        if not nested_key == 'arrays':
                            decompressed_data[nested_key] = nested_value
                    decompressed_arrays = []
                    for array in json_polydata[data_type]['arrays']:
                        decompressed_array = dict()
                        for nested_key, nested_value in array['data'].items():
                            if not nested_key == 'compressedValues':
                                decompressed_array[nested_key] = nested_value
                        dtype = _type_to_numpy(decompressed_array['dataType'])
                        if six.PY2:
                            asBytes = array['data']['compressedValues'].tobytes()
                            valuesBufferArrayCompressed = np.frombuffer(asBytes, dtype=np.uint8)
                        else:
                            valuesBufferArrayCompressed = np.frombuffer(array['data']['compressedValues'],
                                    dtype=np.uint8)
                        numberOfBytes = decompressed_array['size'] * np.dtype(dtype).itemsize
                        valuesBufferArray = \
                            np.frombuffer(decompressor.decompress(valuesBufferArrayCompressed,
                                numberOfBytes),
                                    dtype=dtype)
                        valuesBufferArray.shape = (decompressed_array['size'],)
                        decompressed_array['values'] = valuesBufferArray
                        decompressed_arrays.append({ 'data': decompressed_array })
                    decompressed_data['arrays'] = decompressed_arrays
                    polydata[data_type] = decompressed_data

            polydata_list.append(polydata)
        return polydata_list

polydata_list_serialization = {
    'from_json': polydata_list_from_json,
    'to_json': polydata_list_to_json
}

class PointSetList(PolyDataList):
    """A trait type holding a list of Python data structures compatible with vtk.js that
    is coerced from point set-like data structures."""

    info_text = 'Point set representation for rendering geometry in vtk.js.'

    # Hold a reference to the source object to use with shallow views
    _source_object = None

    def validate(self, obj, value):
        self._source_object = value

        # For convenience, support assigning a single point set instead of a
        # list
        point_sets = value
        if not isinstance(point_sets, collections.Sequence) and not point_sets is None:
            point_sets = [point_sets]

        try:
            for index, point_set in enumerate(point_sets):
                if not isinstance(point_set, dict) or not 'vtkClass' in point_set:
                    point_sets[index] = to_point_set(point_set)
            return point_sets
        except:
            self.error(obj, value)
