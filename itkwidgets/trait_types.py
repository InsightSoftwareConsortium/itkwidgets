import os
import six
import collections
from datetime import datetime

import traitlets
import itk
import numpy as np
import matplotlib.colors
try:
    import zstandard as zstd
except ImportError:
    import zstd
try:
    from functools import reduce
except ImportError:
    pass

from ._transform_types import to_itk_image, to_point_set, to_geometry
from ipydatawidgets import array_serialization

# from IPython.core.debugger import set_trace


class ITKImage(traitlets.TraitType):
    """A trait type holding an itk.Image object"""

    info_text = 'An N-dimensional, potentially multi-component, scientific ' + \
        'image with origin, spacing, and direction metadata'

    # Hold a reference to the source object to use with shallow views
    _source_object = None

    def validate(self, obj, value):
        self._source_object = value

        if not isinstance(value, itk.Image) and not isinstance(value,
                itk.ProcessObject):
            image_from_array = to_itk_image(value)
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
        except BaseException:
            self.error(obj, value)


def _image_to_type(itkimage):  # noqa: C901
    component = itk.template(itkimage)[1][0]
    if component == itk.UL:
        if os.name == 'nt':
            return 'uint32_t', 1
        else:
            return 'uint64_t', 1
    mangle = None
    pixelType = 1
    if component == itk.SL:
        if os.name == 'nt':
            return 'int32_t', 1,
        else:
            return 'int64_t', 1,
    if component in (itk.SC, itk.UC, itk.SS, itk.US, itk.SI, itk.UI, itk.F,
            itk.D, itk.B):
        mangle = component
    elif component in [i[1] for i in itk.Vector.iteritems()]:
        mangle = itk.template(component)[1][0]
        pixelType = 5
    elif component == itk.complex[itk.F]:
        # complex float
        return 'float', 10
    elif component == itk.complex[itk.D]:
        # complex float
        return 'double', 10
    elif component in [i[1] for i in itk.CovariantVector.iteritems()]:
        # CovariantVector
        mangle = itk.template(component)[1][0]
        pixelType = 7
    elif component in [i[1] for i in itk.Offset.iteritems()]:
        # Offset
        return 'int64_t', 4
    elif component in [i[1] for i in itk.FixedArray.iteritems()]:
        # FixedArray
        mangle = itk.template(component)[1][0]
        pixelType = 11
    elif component in [i[1] for i in itk.RGBAPixel.iteritems()]:
        # RGBA
        mangle = itk.template(component)[1][0]
        pixelType = 3
    elif component in [i[1] for i in itk.RGBPixel.iteritems()]:
        # RGB
        mangle = itk.template(component)[1][0]
        pixelType = 2
    elif component in [i[1] for i in itk.SymmetricSecondRankTensor.iteritems()]:
        # SymmetricSecondRankTensor
        mangle = itk.template(component)[1][0]
        pixelType = 8
    else:
        raise RuntimeError('Unrecognized component type: {0}'.format(str(component)))
    _python_to_js = {
        itk.SC: 'int8_t',
        itk.UC: 'uint8_t',
        itk.SS: 'int16_t',
        itk.US: 'uint16_t',
        itk.SI: 'int32_t',
        itk.UI: 'uint32_t',
        itk.F: 'float',
        itk.D: 'double',
        itk.B: 'uint8_t'
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
        pixel_arr = itk.array_view_from_image(itkimage)
        componentType, pixelType = _image_to_type(itkimage)
        if 'int64' in componentType:
            # JavaScript does not yet support 64-bit integers well
            if componentType == 'uint64_t':
                pixel_arr = pixel_arr.astype(np.uint32)
                componentType = 'uint32_t'
            else:
                pixel_arr = pixel_arr.astype(np.int32)
                componentType = 'int32_t'
        compressor = zstd.ZstdCompressor(level=3)
        compressed = compressor.compress(pixel_arr.data)
        pixel_arr_compressed = memoryview(compressed)
        for col in range(dimension):
            for row in range(dimension):
                directionList.append(directionMatrix.get(row, col))
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
            compressedData=pixel_arr_compressed
        )


def _type_to_image(jstype):
    _pixelType_to_prefix = {
        1: '',
        2: 'RGB',
        3: 'RGBA',
        4: 'O',
        5: 'V',
        7: 'CV',
        8: 'SSRT',
        11: 'FA'
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
        'int8_t': 'SC',
        'uint8_t': 'UC',
        'int16_t': 'SS',
        'uint16_t': 'US',
        'int32_t': 'SI',
        'uint32_t': 'UI',
        'int64_t': 'S' + _long_type(),
        'uint64_t': 'U' + _long_type(),
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
        pixelCount = reduce(lambda x, y: x * y, js['size'], 1)
        numberOfBytes = pixelCount * \
            js['imageType']['components'] * np.dtype(dtype).itemsize
        pixelBufferArray = \
            np.frombuffer(decompressor.decompress(pixelBufferArrayCompressed,
                                                  numberOfBytes),
                          dtype=dtype)
        pixelBufferArray.shape = js['size'][::-1]
        # Workaround for GetImageFromArray required until 5.0.1
        # and https://github.com/numpy/numpy/pull/11739
        pixelBufferArrayCopyToBeRemoved = pixelBufferArray.copy()
        # image = itk.PyBuffer[ImageType].GetImageFromArray(pixelBufferArray)
        image = itk.PyBuffer[ImageType].GetImageFromArray(
            pixelBufferArrayCopyToBeRemoved)
        Dimension = image.GetImageDimension()
        image.SetOrigin(js['origin'])
        image.SetSpacing(js['spacing'])
        direction = image.GetDirection()
        directionMatrix = direction.GetVnlMatrix()
        directionJs = js['direction']['data']
        for col in range(Dimension):
            for row in range(Dimension):
                directionMatrix.put(
                    row, col, directionJs[col + row * Dimension])
        return image

itkimage_serialization = {
    'from_json': itkimage_from_json,
    'to_json': itkimage_to_json
}

class ImagePoint(object):
    """Data from a picked point on an image slice."""

    def __init__(self, index=None, position=None, value=None, label=None):
        self.index = index
        self.position = position
        self.value = value
        self.label = label

    def __str__(self):
        return 'index: {0}, position: {1}, value: {2}, label: {3}'.format(
            self.index,
            self.position,
            self.value,
            self.label)

class ImagePointTrait(traitlets.Instance):
    """A trait type holding an data from a picked point on an image slice."""

    info_text = 'Data from a picked point on an image'

    klass = ImagePoint

def image_point_from_json(js, manager=None):
    if js is None:
        return None
    else:
        label = None
        if js['label'] is not None:
            label = int(js['label'])
        return ImagePoint(
            index = array_serialization['from_json'](js['index'], manager),
            position = array_serialization['from_json'](js['position'], manager),
            value = array_serialization['from_json'](js['value'], manager),
            label = label,
        )

def image_point_to_json(image_point, manager=None):
    if image_point is None:
        return None
    else:
        label = None
        if image_point.label is not None:
            label = int(image_point.label)
        return {
            'index': array_serialization['to_json'](image_point.index, manager),
            'position': array_serialization['to_json'](image_point.position,
                manager),
            'value': array_serialization['to_json'](image_point.value, manager),
            'label': label,
        }

image_point_serialization = {
    'from_json': image_point_from_json,
    'to_json': image_point_to_json
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
        if not isinstance(geometries, dict) and not isinstance(
                geometries, collections.Sequence) and geometries is not None:
            geometries = [geometries]

        try:
            if isinstance(geometries, dict):
                geometries_list = []
                for name, geometry in geometries.items():
                    if not isinstance(
                            geometry, dict) or 'vtkClass' not in geometry:
                        geometry = to_geometry(geometry)
                    if 'metadata' not in geometry:
                        geometry['metadata'] = {'name': str(name)}
                    geometries_list.append(geometry)
                return geometries_list
            for index, geometry in enumerate(geometries):
                if not isinstance(
                        geometry, dict) or 'vtkClass' not in geometry:
                    geometries[index] = to_geometry(geometry)
                if 'metadata' not in geometries[index]:
                    geometries[index]['metadata'] = {'name': 'Geometry {0}'.format(index)}
            return geometries
        except BaseException:
            self.error(obj, value)


def polydata_list_to_json(polydata_list, manager=None):  # noqa: C901
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
                        compressed_arrays.append({'data': compressed_array})
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


def polydata_list_from_json(js, manager=None):  # noqa: C901
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
                    asBytes = json_polydata['points']['compressedValues'].tobytes(
                    )
                    valuesBufferArrayCompressed = np.frombuffer(
                        asBytes, dtype=np.uint8)
                else:
                    valuesBufferArrayCompressed = np.frombuffer(json_polydata['points']['compressedValues'],
                                                                dtype=np.uint8)
                numberOfBytes = json_polydata['points']['size'] * \
                    np.dtype(dtype).itemsize
                valuesBufferArray = \
                    np.frombuffer(decompressor.decompress(valuesBufferArrayCompressed,
                                                          numberOfBytes),
                                  dtype=dtype)
                valuesBufferArray.shape = (
                    int(json_polydata['points']['size'] / 3), 3)
                polydata['points']['values'] = valuesBufferArray

            for cell_type in ['verts', 'lines', 'polys', 'strips']:
                if cell_type in polydata:
                    dtype = _type_to_numpy(polydata[cell_type]['dataType'])
                    if six.PY2:
                        asBytes = json_polydata[cell_type]['compressedValues'].tobytes(
                        )
                        valuesBufferArrayCompressed = np.frombuffer(
                            asBytes, dtype=np.uint8)
                    else:
                        valuesBufferArrayCompressed = np.frombuffer(json_polydata[cell_type]['compressedValues'],
                                                                    dtype=np.uint8)
                    numberOfBytes = json_polydata[cell_type]['size'] * \
                        np.dtype(dtype).itemsize
                    valuesBufferArray = \
                        np.frombuffer(decompressor.decompress(valuesBufferArrayCompressed,
                                                              numberOfBytes),
                                      dtype=dtype)
                    valuesBufferArray.shape = (
                        json_polydata[cell_type]['size'],)
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
                            asBytes = array['data']['compressedValues'].tobytes(
                            )
                            valuesBufferArrayCompressed = np.frombuffer(
                                asBytes, dtype=np.uint8)
                        else:
                            valuesBufferArrayCompressed = np.frombuffer(array['data']['compressedValues'],
                                                                        dtype=np.uint8)
                        numberOfBytes = decompressed_array['size'] * \
                            np.dtype(dtype).itemsize
                        valuesBufferArray = \
                            np.frombuffer(decompressor.decompress(valuesBufferArrayCompressed,
                                                                  numberOfBytes),
                                          dtype=dtype)
                        valuesBufferArray.shape = (decompressed_array['size'],)
                        decompressed_array['values'] = valuesBufferArray
                        decompressed_arrays.append(
                            {'data': decompressed_array})
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
        if not isinstance(point_sets, dict) and not isinstance(
                point_sets, collections.Sequence) and point_sets is not None:
            point_sets = [point_sets]

        try:
            if isinstance(point_sets, dict):
                point_sets_list = []
                for name, point_set in point_sets.items():
                    if not isinstance(
                            point_set, dict) or 'vtkClass' not in point_set:
                        point_set = to_point_set(point_set)
                    if 'metadata' not in point_set:
                        point_set['metadata'] = {'name': str(name)}
                    point_sets_list.append(point_set)
                return point_sets_list
            else:
                for index, point_set in enumerate(point_sets):
                    if not isinstance(
                            point_set, dict) or 'vtkClass' not in point_set:
                        point_sets[index] = to_point_set(point_set)
                    if 'metadata' not in point_sets[index]:
                        point_sets[index]['metadata'] = {'name': 'Point Set {0}'.format(index)}
                return point_sets
        except BaseException:
            self.error(obj, value)


class Colormap(traitlets.Unicode):
    """A trait type holding a colormap"""

    info_text = 'A colormap, either a vtk.js colormap preset, np.ndarray of RGB points, or matplotlib colormap.'

    _colormap_presets = ('Viridis (matplotlib)',
                         'Plasma (matplotlib)',
                         'Inferno (matplotlib)',
                         'Magma (matplotlib)',
                         'Grayscale',
                         'X Ray',
                         'BkMa',
                         'BkCy',
                         'gray_Matlab',
                         'bone_Matlab',
                         'pink_Matlab',
                         '2hot',
                         'gist_earth',
                         'Haze',
                         'Haze_green',
                         'Haze_lime',
                         'Haze_cyan',
                         'Black, Blue and White',
                         'Black, Orange and White',
                         'Black-Body Radiation',

                         'Cool to Warm',
                         'Warm to Cool',
                         'Cool to Warm (Extended)',
                         'Warm to Cool (Extended)',
                         'Blue to Red Rainbow',
                         'Red to Blue Rainbow',
                         'jet',
                         'rainbow',
                         'hsv',
                         'Rainbow Desaturated',
                         'Cold and Hot',
                         'Rainbow Blended Black',
                         'Rainbow Blended Grey',
                         'Rainbow Blended White',
                         'nic_CubicL',
                         'Spectral_lowBlue',
                         'Yellow 15',
                         'Asymmtrical Earth Tones (6_21b)',
                         'Green-Blue Asymmetric Divergent (62Blbc)',
                         'Muted Blue-Green',

                         'BkRd',
                         'BkGn',
                         'BkBu',
                         'Purples',
                         'Oranges',
                         'PuBu',
                         'BuPu',
                         'BuGn',
                         'GnBu',
                         'PuRd',
                         'RdPu',
                         'RdOr',
                         'BuRd',
                         'GnRP',
                         'GYPi',
                         'GBBr',
                         'PRGn',
                         'PiYG',
                         'OrPu',
                         'BrBG'
                         )

    def validate(self, obj, value):
        if value is None:
            return None
        elif isinstance(value, np.ndarray):
            custom_cmap = value.astype(np.float32)
            custom_cmap = custom_cmap[:, :3]
            obj._custom_cmap = custom_cmap
            timestamp = str(datetime.timestamp(datetime.now()))
            return 'Custom NumPy ' + timestamp
        elif isinstance(value, matplotlib.colors.LinearSegmentedColormap):
            custom_cmap = value(np.linspace(0.0, 1.0, 64)).astype(np.float32)
            custom_cmap = custom_cmap[:, :3]
            obj._custom_cmap = custom_cmap
            timestamp = str(datetime.timestamp(datetime.now()))
            return 'Custom matplotlib ' + timestamp
        if value not in self._colormap_presets and not value.startswith(
                'Custom'):
            raise self.error('Invalid colormap')
        return super(Colormap, self).validate(obj, value)

class LookupTable(traitlets.Unicode):
    """A trait type holding a lookup table."""

    info_text = 'A lookup table, either a itk-vtk-viewer categorical colormap preset, todo: np.ndarray of RGB points, or matplotlib ListedColormap.'

    _lookup_table_presets = ('glasbey',
                             'glasbey_light',
                             'glasbey_warm',
                             'modulate',
                             'glasbey_bw',
                             'glasbey_dark',
                             'glasbey_cool',
                             'modulate_dark',
                             )

    def validate(self, obj, value):
        if value is None:
            return None
        # elif isinstance(value, np.ndarray):
            # custom_cmap = value.astype(np.float32)
            # custom_cmap = custom_cmap[:, :3]
            # obj._custom_cmap = custom_cmap
            # timestamp = str(datetime.timestamp(datetime.now()))
            # return 'Custom NumPy ' + timestamp
        # elif isinstance(value, matplotlib.colors.ListedColormap):
            # custom_cmap = value(np.linspace(0.0, 1.0, 64)).astype(np.float32)
            # custom_cmap = custom_cmap[:, :3]
            # obj._custom_cmap = custom_cmap
            # timestamp = str(datetime.timestamp(datetime.now()))
            # return 'Custom matplotlib ' + timestamp
        if value not in self._lookup_table_presets and not value.startswith(
                'Custom'):
            raise self.error('Invalid lookup table')
        return super(LookupTable, self).validate(obj, value)
