"""Viewer class

Visualization of an image.

In the future, will add optional segmentation mesh overlay.
"""

import colorcet
import matplotlib
import collections
import functools
import time

import itk
import numpy as np
import ipywidgets as widgets
from traitlets import CBool, CFloat, CInt, Unicode, CaselessStrEnum, List, validate, TraitError, Tuple
from ipydatawidgets import NDArray, array_serialization, shape_constraints
from .trait_types import ITKImage, ImagePointTrait, ImagePoint, PointSetList, PolyDataList, itkimage_serialization, image_point_serialization, polydata_list_serialization, Colormap, LookupTable, Camera

try:
    import ipywebrtc
    ViewerParent = ipywebrtc.MediaStream
except ImportError:
    ViewerParent = widgets.DOMWidget

have_vtk = False
try:
    import vtk
    have_vtk = True
except ImportError:
    pass

have_mayavi = False
try:
    from mayavi.core.pipeline_base import PipelineBase  # noqa: F401
    have_mayavi = True
except ImportError:
    pass


def get_ioloop():
    import IPython
    import zmq
    ipython = IPython.get_ipython()
    if ipython and hasattr(ipython, 'kernel'):
        return zmq.eventloop.ioloop.IOLoop.instance()


def debounced(delay_seconds=0.5, method=False):
    def wrapped(f):
        counters = collections.defaultdict(int)

        @functools.wraps(f)
        def execute(*args, **kwargs):
            if method:  # if it is a method, we want to have a counter per instance
                key = args[0]
            else:
                key = None
            counters[key] += 1

            def debounced_execute(counter=counters[key]):
                # only execute if the counter wasn't changed in the meantime
                if counter == counters[key]:
                    f(*args, **kwargs)
            ioloop = get_ioloop()

            def thread_safe():
                ioloop.add_timeout(
                    time.time() + delay_seconds,
                    debounced_execute)

            # we live outside of IPython (e.g. unittest), so execute directly
            if ioloop is None:
                debounced_execute()
            else:
                ioloop.add_callback(thread_safe)
        return execute
    return wrapped

# https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20Asynchronous.html


def yield_for_change(widget, attribute):
    """Pause a generator to wait for a widget change event.

    This is a decorator for a generator function which pauses the generator on yield
    until the given widget attribute changes. The new value of the attribute is
    sent to the generator and is the value of the yield.
    """
    def f(iterator):
        @functools.wraps(iterator)
        def inner():
            i = iterator()

            def next_i(change):
                try:
                    i.send(change.new)
                except StopIteration:
                    widget.unobserve(next_i, attribute)
            widget.observe(next_i, attribute)
            # start the generator
            next(i)
        return inner
    return f


@widgets.register
class Viewer(ViewerParent):
    """Viewer widget class."""
    _view_name = Unicode('ViewerView').tag(sync=True)
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _view_module = Unicode('itkwidgets').tag(sync=True)
    _model_module = Unicode('itkwidgets').tag(sync=True)
    _view_module_version = Unicode('^0.32.6').tag(sync=True)
    _model_module_version = Unicode('^0.32.6').tag(sync=True)
    image = ITKImage(
        default_value=None,
        allow_none=True,
        help="Image to visualize.").tag(
        sync=False,
        **itkimage_serialization)
    rendered_image = ITKImage(
        default_value=None,
        allow_none=True).tag(
        sync=True,
        **itkimage_serialization)
    _rendering_image = CBool(
        default_value=False,
        help="We are currently volume rendering the image.").tag(sync=True)
    label_image = ITKImage(
        default_value=None,
        allow_none=True,
        help="Label map for the image.").tag(
        sync=False,
        **itkimage_serialization)
    rendered_label_image = ITKImage(
        default_value=None,
        allow_none=True).tag(
        sync=True,
        **itkimage_serialization)
    label_image_names = List(
        allow_none=True,
        default_value=None,
        help="Names for labels in the label map.").tag(
        trait=Tuple(), sync=True)
    label_image_blend = CFloat(
        default_value=0.5,
        help="Blend of the label map with the intensity image.").tag(sync=True)
    label_image_weights = NDArray(dtype=np.float32, default_value=None, allow_none=True,
        help="Weights, from 0.0 to 1.0, for every label in the label map.")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None,))
    interpolation = CBool(
        default_value=True,
        help="Use linear interpolation in slicing planes.").tag(sync=True)
    cmap = List(
        default_value=None,
        allow_none=True,
        ).tag(trait=Colormap('Viridis (matplotlib)', allow_none=True), sync=True)
    _custom_cmap = NDArray(dtype=np.float32, default_value=None, allow_none=True,
                           help="RGB triples from 0.0 to 1.0 that define a custom linear, sequential colormap")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None, 3))
    lut = LookupTable('glasbey',
        help='Lookup table for the label map.').tag(sync=True)
    shadow = CBool(
        default_value=True,
        help="Use shadowing in the volume rendering.").tag(sync=True)
    slicing_planes = CBool(
        default_value=False,
        help="Display the slicing planes in volume rendering view mode.").tag(
        sync=True)
    x_slice = CFloat(
        default_value=None,
        allow_none=True,
        help="World-space position of the X slicing plane.").tag(sync=True)
    y_slice = CFloat(
        default_value=None,
        allow_none=True,
        help="World-space position of the Y slicing plane.").tag(sync=True)
    z_slice = CFloat(
        default_value=None,
        allow_none=True,
        help="World-space position of the Z slicing plane.").tag(sync=True)
    clicked_slice_point = ImagePointTrait(
        default_value=None,
        allow_none=True,
        help="Data for the point clicked on an image slice.").tag(
            sync=True,
            **image_point_serialization)
    gradient_opacity = CFloat(
        default_value=0.2,
        help="Volume rendering gradient opacity, from (0.0, 1.0]").tag(sync=True)
    opacity_gaussians = List(
        default_value=None,
        allow_none=True,
        help="Volume opacity transfer function Gaussians parameters.").tag(sync=True)
    channels = List(
        default_value=None,
        allow_none=True,
        help="Components or channels enabled in a multi-component image.").tag(trait=CBool(), sync=True)
    blend_mode = CaselessStrEnum(
        ('composite',
         'max',
         'min',
         'average'),
        default_value='composite',
        help="Volume rendering blend mode").tag(sync=True)
    roi = NDArray(dtype=np.float64, default_value=np.zeros((2, 3), dtype=np.float64),
                  help="Region of interest: [[lower_x, lower_y, lower_z), (upper_x, upper_y, upper_z]]")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(2, 3))
    vmin = List(
        default_value=None,
        allow_none=True,
        help="Value that maps to the minimum of image colormap.").tag(
        trait=CFloat(), sync=True)
    vmax = List(
        default_value=None,
        allow_none=True,
        help="Value that maps to the maximum of image colormap.").tag(
        trait=CFloat(), sync=True)
    _largest_roi = NDArray(dtype=np.float64, default_value=np.zeros((2, 3), dtype=np.float64),
                           help="Largest possible region of interest: "
                           "[[lower_x, lower_y, lower_z), (upper_x, upper_y, upper_z]]")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(2, 3))
    select_roi = CBool(
        default_value=False,
        help="Enable an interactive region of interest widget for the image.").tag(
        sync=True)
    size_limit_2d = NDArray(dtype=np.int64, default_value=np.array([1024, 1024], dtype=np.int64),
                            help="Size limit for 2D image visualization.").tag(sync=False)
    size_limit_3d = NDArray(dtype=np.int64, default_value=np.array([192, 192, 192], dtype=np.int64),
                            help="Size limit for 3D image visualization.").tag(sync=False)
    sample_distance = CFloat(default_value=0.25,
                            help="Normalized volume rendering sample distance.").tag(sync=True)
    _scale_factors = NDArray(dtype=np.uint8, default_value=np.array([1, 1, 1], dtype=np.uint8),
                             help="Image downscaling factors.").tag(sync=True, **array_serialization)
    _downsampling = CBool(default_value=False,
                          help="We are downsampling the image to meet the size limits.").tag(sync=True)
    _reset_crop_requested = CBool(default_value=False,
                                  help="The user requested a reset of the roi.").tag(sync=True)
    units = Unicode(
        '',
        help="Units to display in the scale bar.").tag(
        sync=True)
    point_set_representations = List(
        default_value=[],
        help="Point set representation").tag(
        trait=Unicode(), sync=True)
    point_sets = PointSetList(
        default_value=None,
        allow_none=True,
        help="Point sets to visualize").tag(
        sync=True,
        **polydata_list_serialization)
    point_set_colors = NDArray(dtype=np.float32, default_value=np.zeros((0, 3), dtype=np.float32),
                               help="RGB colors for the points sets")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None, 3))
    point_set_opacities = NDArray(dtype=np.float32, default_value=np.zeros((0,), dtype=np.float32),
                                  help="Opacities for the points sets")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None,))
    point_set_sizes = NDArray(dtype=np.uint8, default_value=np.zeros((0,), dtype=np.uint8),
                              help="Sizes for the points sets")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None,))
    point_set_representations = List(
        default_value=[],
        help="Point set representation").tag(
        trait=Unicode(), sync=True)
    geometries = PolyDataList(
        default_value=None,
        allow_none=True,
        help="Geometries to visualize").tag(
        sync=True,
        **polydata_list_serialization)
    geometry_colors = NDArray(dtype=np.float32, default_value=np.zeros((0, 3), dtype=np.float32),
                              help="RGB colors for the geometries")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None, 3))
    geometry_opacities = NDArray(dtype=np.float32, default_value=np.zeros((0,), dtype=np.float32),
                                 help="Opacities for the geometries")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(None,))
    ui_collapsed = CBool(
        default_value=False,
        help="Collapse the built in user interface.").tag(
        sync=True)
    rotate = CBool(
        default_value=False,
        help="Rotate the camera around the scene.").tag(
        sync=True)
    annotations = CBool(
        default_value=True,
        help="Show annotations.").tag(
        sync=True)
    axes = CBool(
        default_value=False,
        help="Display axes.").tag(
        sync=True)
    mode = CaselessStrEnum(
        ('x',
         'y',
         'z',
         'v'),
        default_value='v',
        help="View mode: x: x plane, y: y plane, z: z plane, v: volume rendering").tag(
        sync=True)
    camera = Camera(dtype=np.float32, default_value=np.zeros((3, 3), dtype=np.float32),
                     help="Camera parameters: [[position_x, position_y, position_z], "
                     "[focal_point_x, focal_point_y, focal_point_z], "
                     "[view_up_x, view_up_y, view_up_z]]")\
        .tag(sync=True, **array_serialization)\
        .valid(shape_constraints(3, 3))
    background = Tuple(
        allow_none=True,
        default_value=(),
        help="Background color.").tag(trait=CFloat(), sync=True)

    def __init__(self, **kwargs):  # noqa: C901
        if 'point_set_colors' in kwargs:
            proposal = {'value': kwargs['point_set_colors']}
            color_array = self._validate_point_set_colors(proposal)
            kwargs['point_set_colors'] = color_array
        if 'point_set_opacities' in kwargs:
            proposal = {'value': kwargs['point_set_opacities']}
            opacities_array = self._validate_point_set_opacities(proposal)
            kwargs['point_set_opacities'] = opacities_array
        if 'point_set_sizes' in kwargs:
            proposal = {'value': kwargs['point_set_sizes']}
            sizes_array = self._validate_point_set_sizes(proposal)
            kwargs['point_set_sizes'] = sizes_array
        if 'point_set_representations' in kwargs:
            proposal = {'value': kwargs['point_set_representations']}
            representations_list = self._validate_point_set_representations(
                proposal)
            kwargs['point_set_representations'] = representations_list
        self.observe(self._on_point_sets_changed, ['point_sets'])
        if 'geometry_colors' in kwargs:
            proposal = {'value': kwargs['geometry_colors']}
            color_array = self._validate_geometry_colors(proposal)
            kwargs['geometry_colors'] = color_array
        if 'geometry_opacities' in kwargs:
            proposal = {'value': kwargs['geometry_opacities']}
            opacities_array = self._validate_geometry_opacities(proposal)
            kwargs['geometry_opacities'] = opacities_array
        if 'cmap' in kwargs and kwargs['cmap'] is not None:
            proposal = {'value': kwargs['cmap']}
            cmap_list = self._validate_cmap(proposal)
            kwargs['cmap'] = cmap_list
        if 'vmin' in kwargs and kwargs['vmin'] is not None:
            proposal = {'value': kwargs['vmin']}
            vmin_list = self._validate_vmin(proposal)
            kwargs['vmin'] = vmin_list
        if 'vmax' in kwargs and kwargs['vmax'] is not None:
            proposal = {'value': kwargs['vmax']}
            vmax_list = self._validate_vmax(proposal)
            kwargs['vmax'] = vmax_list
        self.observe(self._on_geometries_changed, ['geometries'])
        have_label_image = 'label_image' in kwargs and kwargs['label_image'] is not None
        if have_label_image:
            # Interpolation is not currently supported with label maps
            kwargs['interpolation'] = False

        super(Viewer, self).__init__(**kwargs)

        if not self.image and not self.label_image:
            return
        if self.image:
            image = self.image
        else:
            image = self.label_image
        dimension = image.GetImageDimension()
        largest_region = image.GetLargestPossibleRegion()
        size = largest_region.GetSize()

        # Cache this so we do not need to recompute on it when resetting the
        # roi
        self._largest_roi_rendered_image = None
        self._largest_roi_rendered_label_image = None
        self._largest_roi = np.zeros((2, 3), dtype=np.float64)
        if not np.any(self.roi):
            largest_index = largest_region.GetIndex()
            self.roi[0][:dimension] = np.array(
                image.TransformIndexToPhysicalPoint(largest_index))
            largest_index_upper = largest_index + size
            self.roi[1][:dimension] = np.array(
                image.TransformIndexToPhysicalPoint(largest_index_upper))
            self._largest_roi = self.roi.copy()

        if dimension == 2:
            for dim in range(dimension):
                if size[dim] > self.size_limit_2d[dim]:
                    self._downsampling = True
        else:
            for dim in range(dimension):
                if size[dim] > self.size_limit_3d[dim]:
                    self._downsampling = True
        self._update_rendered_image()
        if self._downsampling:
            self.observe(self._on_roi_changed, ['roi'])

        self.observe(self._on_reset_crop_requested, ['_reset_crop_requested'])
        self.observe(self.update_rendered_image, ['image', 'label_image'])
        self.observe(self.update_rendered_image, ['image', 'label_image'])

    def _on_roi_changed(self, change=None):
        if self._downsampling:
            self._update_rendered_image()

    def _on_reset_crop_requested(self, change=None):
        if change.new is True and self._downsampling:
            if self.image:
                image = self.image
            else:
                image = self.label_image
            dimension = image.GetImageDimension()
            largest_region = image.GetLargestPossibleRegion()
            size = largest_region.GetSize()
            largest_index = largest_region.GetIndex()
            new_roi = self.roi.copy()
            new_roi[0][:dimension] = np.array(
                image.TransformIndexToPhysicalPoint(largest_index))
            largest_index_upper = largest_index + size
            new_roi[1][:dimension] = np.array(
                image.TransformIndexToPhysicalPoint(largest_index_upper))
            self._largest_roi = new_roi.copy()
            self.roi = new_roi
        if change.new is True:
            self._reset_crop_requested = False

    @debounced(delay_seconds=0.2, method=True)
    def update_rendered_image(self, change=None):
        self._largest_roi_rendered_image = None
        self._largest_roi_rendered_label_image = None
        self._largest_roi = np.zeros((2, 3), dtype=np.float64)
        self._update_rendered_image()

    @staticmethod
    def _find_scale_factors(limit, dimension, size):
        scale_factors = [1, ] * 3
        for dim in range(dimension):
            while(int(np.floor(float(size[dim]) / scale_factors[dim])) > limit[dim]):
                scale_factors[dim] += 1
        return scale_factors

    def _update_rendered_image(self):
        if self.image is None and self.label_image is None:
            return
        if self._rendering_image:
            @yield_for_change(self, '_rendering_image')
            def f():
                x = yield
                assert(x is False)
            f()
        self._rendering_image = True

        if self._downsampling:
            if self.image:
                image = self.image
            else:
                image = self.label_image
            dimension = image.GetImageDimension()
            index = image.TransformPhysicalPointToIndex(
                self.roi[0][:dimension])
            upper_index = image.TransformPhysicalPointToIndex(
                self.roi[1][:dimension])
            size = upper_index - index
            size = [max(s, 1) for s in size]

            if dimension == 2:
                scale_factors = self._find_scale_factors(
                    self.size_limit_2d, dimension, size)
            else:
                scale_factors = self._find_scale_factors(
                    self.size_limit_3d, dimension, size)
            self._scale_factors = np.array(scale_factors, dtype=np.uint8)
            if self.image:
                self.extractor = itk.ExtractImageFilter.New(self.image)
                self.shrinker = itk.ShrinkImageFilter.New(self.extractor)
                self.shrinker.SetShrinkFactors(scale_factors[:dimension])
            if self.label_image:
                self.label_image_extractor = itk.ExtractImageFilter.New(self.label_image)
                self.label_image_shrinker = itk.ShrinkImageFilter.New(self.label_image_extractor)
                self.label_image_shrinker.SetShrinkFactors(scale_factors[:dimension])

            region = itk.ImageRegion[dimension]()
            region.SetIndex(index)
            region.SetSize(tuple(size))
            # Account for rounding
            # truncation issues
            region.PadByRadius(1)
            region.Crop(image.GetLargestPossibleRegion())

            if self.image:
                self.extractor.SetInput(self.image)
                self.extractor.SetExtractionRegion(region)
            if self.label_image:
                self.label_image_extractor.SetInput(self.label_image)
                self.label_image_extractor.SetExtractionRegion(region)

            size = region.GetSize()

            is_largest = False
            if np.any(self._largest_roi) and np.all(
                    self._largest_roi == self.roi):
                is_largest = True
                if self._largest_roi_rendered_image is not None or self._largest_roi_rendered_label_image is not None:
                    if self.image:
                        self.rendered_image = self._largest_roi_rendered_image
                    if self.label_image:
                        self.rendered_label_image = self._largest_roi_rendered_label_image
                    return

            if self.image:
                self.shrinker.UpdateLargestPossibleRegion()
            if self.label_image:
                self.label_image_shrinker.UpdateLargestPossibleRegion()
            if is_largest:
                if self.image:
                    self._largest_roi_rendered_image = self.shrinker.GetOutput()
                    self._largest_roi_rendered_image.DisconnectPipeline()
                    self._largest_roi_rendered_image.SetOrigin(
                        self.roi[0][:dimension])
                    self.rendered_image = self._largest_roi_rendered_image
                if self.label_image:
                    self._largest_roi_rendered_label_image = self.label_image_shrinker.GetOutput()
                    self._largest_roi_rendered_label_image.DisconnectPipeline()
                    self._largest_roi_rendered_label_image.SetOrigin(
                        self.roi[0][:dimension])
                    self.rendered_label_image = self._largest_roi_rendered_label_image
                return
            if self.image:
                shrunk = self.shrinker.GetOutput()
                shrunk.DisconnectPipeline()
                shrunk.SetOrigin(self.roi[0][:dimension])
                self.rendered_image = shrunk
            if self.label_image:
                shrunk = self.label_image_shrinker.GetOutput()
                shrunk.DisconnectPipeline()
                shrunk.SetOrigin(self.roi[0][:dimension])
                self.rendered_label_image = shrunk
        else:
            if self.image:
                self.rendered_image = self.image
            if self.label_image:
                self.rendered_label_image = self.label_image

    @validate('label_image_weights')
    def _validate_label_image_weights(self, proposal):
        """Check the number of weights equals the number of labels."""
        value = proposal['value']
        value = np.array(value, dtype=np.float32)
        if self.rendered_label_image:
            labels = len(np.unique(itk.array_view_from_image(self.rendered_label_image)))
            if labels != len(value):
                raise TraitError('Number of labels, {0}, does not equal number of label weights, {1}'.format(labels, len(value)))
        return value

    @validate('label_image_blend')
    def _validate_label_image_blend(self, proposal):
        """Enforce 0 <= value <= 1.0."""
        value = proposal['value']
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    @validate('gradient_opacity')
    def _validate_gradient_opacity(self, proposal):
        """Enforce 0 < value <= 1.0."""
        value = proposal['value']
        if value <= 0.0:
            return 0.01
        if value > 1.0:
            return 1.0
        return value

    @validate('label_image_blend')
    def _validate_label_image_blend(self, proposal):
        """Enforce 0 <= value <= 1.0."""
        value = proposal['value']
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    @validate('cmap')
    def _validate_cmap(self, proposal):
        validator = Colormap()
        value = proposal['value']
        if value is None:
            return None
        elif isinstance(value, list):
            return [validator.validate(self, v) for v in value]
        else:
            return [validator.validate(self, value),]

    @validate('vmin')
    def _validate_vmin(self, proposal):
        value = proposal['value']
        if value is None:
            return None
        elif isinstance(value, list):
            return value
        else:
            return [value]

    @validate('vmax')
    def _validate_vmax(self, proposal):
        value = proposal['value']
        if value is None:
            return None
        elif isinstance(value, list):
            return value
        else:
            return [value]

    @validate('point_set_colors')
    def _validate_point_set_colors(self, proposal):
        value = proposal['value']
        n_colors = len(value)
        if self.point_sets:
            n_colors = len(self.point_sets)
        result = np.zeros((n_colors, 3), dtype=np.float32)
        for index, color in enumerate(value):
            result[index, :] = matplotlib.colors.to_rgb(color)
        if len(value) < n_colors:
            for index in range(len(value), n_colors):
                color = colorcet.glasbey[index % len(colorcet.glasbey)]
                result[index, :] = matplotlib.colors.to_rgb(color)
        return result

    @validate('point_set_opacities')
    def _validate_point_set_opacities(self, proposal):
        value = proposal['value']
        n_values = 0
        if isinstance(value, float):
            n_values = 1
        else:
            n_values = len(value)
        n_opacities = n_values
        if self.point_sets:
            n_opacities = len(self.point_sets)
        result = np.ones((n_opacities,), dtype=np.float32)
        result[:n_values] = value
        return result

    @validate('point_set_sizes')
    def _validate_point_set_sizes(self, proposal):
        value = proposal['value']
        n_values = 0
        if isinstance(value, float):
            n_values = 1
        else:
            n_values = len(value)
        n_sizes = n_values
        if self.point_sets:
            n_sizes = len(self.point_sets)
        result = 3 * np.ones((n_sizes,), dtype=np.uint8)
        result[:n_values] = value
        return result

    @validate('point_set_representations')
    def _validate_point_set_representations(self, proposal):
        value = proposal['value']
        n_values = 0
        if isinstance(value, str):
            n_values = 1
        else:
            n_values = len(value)
        n_representations = n_values
        if self.point_sets:
            n_representations = len(self.point_sets)
        result = ['points'] * n_representations
        result[:n_values] = value
        return result

    def _on_point_sets_changed(self, change=None):
        # Make sure we have a sufficient number of colors
        old_colors = self.point_set_colors
        self.point_set_colors = old_colors[:len(self.point_sets)]
        # Make sure we have a sufficient number of opacities
        old_opacities = self.point_set_opacities
        self.point_set_opacities = old_opacities[:len(self.point_sets)]
        # Make sure we have a sufficient number of sizes
        old_sizes = self.point_set_sizes
        self.point_set_sizes = old_sizes[:len(self.point_sets)]
        # Make sure we have a sufficient number of representations
        old_representations = self.point_set_representations
        self.point_set_representations = old_representations[:len(
            self.point_sets)]

    @validate('geometry_colors')
    def _validate_geometry_colors(self, proposal):
        value = proposal['value']
        n_colors = len(value)
        if self.geometries:
            n_colors = len(self.geometries)
        result = np.zeros((n_colors, 3), dtype=np.float32)
        for index, color in enumerate(value):
            result[index, :] = matplotlib.colors.to_rgb(color)
        if len(value) < n_colors:
            for index in range(len(value), n_colors):
                color = colorcet.glasbey[index % len(colorcet.glasbey)]
                result[index, :] = matplotlib.colors.to_rgb(color)
        return result

    @validate('geometry_opacities')
    def _validate_geometry_opacities(self, proposal):
        value = proposal['value']
        n_values = 0
        if isinstance(value, float):
            n_values = 1
        else:
            n_values = len(value)
        n_opacities = n_values
        if self.geometries:
            n_opacities = len(self.geometries)
        result = np.ones((n_opacities,), dtype=np.float32)
        result[:n_values] = value
        return result

    def _on_geometries_changed(self, change=None):
        # Make sure we have a sufficient number of colors
        old_colors = self.geometry_colors
        self.geometry_colors = old_colors[:len(self.geometries)]
        # Make sure we have a sufficient number of opacities
        old_opacities = self.geometry_opacities
        self.geometry_opacities = old_opacities[:len(self.geometries)]

    def roi_region(self):
        """Return the itk.ImageRegion corresponding to the roi."""
        if self.image:
            image = self.image
        else:
            image = self.label_image
        dimension = image.GetImageDimension()
        index = image.TransformPhysicalPointToIndex(
            tuple(self.roi[0][:dimension]))
        upper_index = image.TransformPhysicalPointToIndex(
            tuple(self.roi[1][:dimension]))
        size = upper_index - index
        for dim in range(dimension):
            size[dim] += 1
        region = itk.ImageRegion[dimension]()
        region.SetIndex(index)
        region.SetSize(tuple(size))
        region.Crop(image.GetLargestPossibleRegion())
        return region

    def roi_slice(self):
        """Return the numpy array slice corresponding to the roi."""
        if self.image:
            image = self.image
        else:
            image = self.label_image
        dimension = image.GetImageDimension()
        region = self.roi_region()
        index = region.GetIndex()
        upper_index = np.array(index) + np.array(region.GetSize())
        slices = []
        for dim in range(dimension):
            slices.insert(0, slice(index[dim], upper_index[dim] + 1))
        return tuple(slices)


def _process_mayavi_actors(objects):
    from tvtk.api import tvtk
    from mayavi.core.scene import Scene
    from tvtk.pyface.tvtk_scene import TVTKScene
    actors = []
    for a in objects:
        if isinstance(a, Scene) and a.scene is not None:
            actors.extend([tvtk.to_vtk(x) for x in a.scene.renderer.actors])
        elif isinstance(a, TVTKScene):
            actors.extend([tvtk.to_vtk(x) for x in a.renderer.actors])
        elif isinstance(a, PipelineBase):
            actors.extend([tvtk.to_vtk(x) for x in a.actors])
            if hasattr(a, 'actor'):
                actors.extend([tvtk.to_vtk(x) for x in a.actor.actors])
        else:
            actors.append(a)
    return actors


def view(image=None,  # noqa: C901
         label_image=None,  # noqa: C901
         label_image_names=None,  # noqa: C901
         label_image_weights=None,  # noqa: C901
         label_image_blend=0.5,
         cmap=None,
         lut='glasbey',
         select_roi=False,
         interpolation=True,
         gradient_opacity=0.22, opacity_gaussians=None, channels=None,
         slicing_planes=False, shadow=True, blend_mode='composite',
         point_sets=None,
         point_set_colors=None, point_set_opacities=None,
         point_set_representations=None, point_set_sizes=None,
         geometries=None,
         geometry_colors=None, geometry_opacities=None,
         ui_collapsed=False, rotate=False, annotations=True, axes=False, mode='v',
         **kwargs):
    """View the image and/or point sets and/or geometries.

    Creates and returns an ipywidget to visualize an image, and/or point sets
    and/or geometries .

    The image can be 2D or 3D. A label map that corresponds to the image can
    also be provided. The image and label map must have the same size.

    The type of the image can be an numpy.array, itk.Image,
    vtk.vtkImageData, pyvista.UniformGrid, imglyb.ReferenceGuardingRandomAccessibleInterval,
    or a NumPy array-like, e.g. a Dask array.

    A point set or a sequence of points sets can be visualized. The type of the
    point set can be an numpy.array (Nx3 array of point positions).

    A geometry or a sequence of geometries can be visualized. The type of the
    geometry can be an itk.Mesh.

    Parameters
    ----------

    General Interface
    ^^^^^^^^^^^^^^^^^

    ui_collapsed : bool, default: False
        Collapse the native widget user interface.

    rotate : bool, default: False
        Continuously rotate the camera around the scene in volume rendering
        mode.

    annotations : bool, default: True
        Display annotations describing orientation and the value of a
        mouse-position-based data probe.

    axes : bool, default: False
        Display axes.

    mode: 'x', 'y', 'z', or 'v', default: 'v'
        Only relevant for 3D scenes.
        Viewing mode:
            'x': x-plane
            'y': y-plane
            'z': z-plane
            'v': volume rendering

    camera: 3x3 numpy float32 array, or vtk.vtkCamera
        Camera parameters:
            [[position_x,    position_y,    position_z],
             [focal_point_x, focal_point_y, focal_point_z],
             [view_up_x,     view_up_y,     view_up_z]]

    background: (red, green, blue) tuple, components from 0.0 to 1.0
        Background color. Default is based on the current Jupyter theme.


    Images
    ^^^^^^

    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to visualize.

    label_image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D label map to visualize. If an image is also provided, the
        label map must have the same size.

    label_image_names : OrderedDict of (label_value, label_name)
        String names associated with the integer label values.

    label_image_weights : 1D numpy float32 array, default: None
        Rendering weights, from 0.0 to 1.0, associated labels in the label map.

    label_image_blend : float, default: 0.5
        Label map blend with intensity image, from 0.0 to 1.0.

    vmin: list of floats, default: Minimum of the image pixel buffer
        Value that maps to the minimum of image colormap. A single value
        can be provided or a list for multi-component images.

    vmax: list of floats, default: Maximum of the image pixel buffer
        Value that maps to the minimum of image colormap.  A single value can
        be provided or a list for multi-component images.

    cmap: list of colormaps
            default:
                - single component: 'viridis', 'grayscale' with a label map,
                - two components: 'BkCy', 'BkMa'
                - three components: 'BkRd', 'BkGn', 'BkBu'
        Colormap for each image component. Some valid values available at
        itkwidgets.cm.*
        Colormaps can also be Nx3 float NumPy arrays from 0.0 to 1.0 for the
        red, green, blue points on the map or a
        matplotlib.colors.LinearSegmentedColormap.

    lut: lookup table, default: 'glasbey'
        Lookup table for the label map. Some valid values available at
        itkwidgets.lut.*

    select_roi: bool, default: False
        Enable an interactive region of interest widget for the image.

    slicing_planes: bool, default: False
        Enable slicing planes on the volume rendering.

    x_slice: float, default: None
        World-space position of the X slicing plane.

    y_slice: float, default: None
        World-space position of the Y slicing plane.

    z_slice: float, default: None
        World-space position of the Z slicing plane.

    interpolation: bool, default: True
        Linear as opposed to nearest neighbor interpolation for image slices.
        Note: Interpolation is not currently supported with label maps.

    gradient_opacity: float, default: 0.22
        Gradient opacity for composite volume rendering, in the range (0.0, 1.0].

    opacity_gaussians: list of list of dict
        Volume rendering opacity transfer function Gaussian parameters. For each
        image component, multiple Gaussians can be specified.
        Default Gaussian parameters:
          {'position': 0.5, 'height': 1, 'width': 0.5, 'xBias': 0.51, 'yBias': 0.4}

    channels: list of booleans
        For multi-component images, the components or channels that are enabled.

    shadow: bool, default: True
        Use shadowing with composite volume rendering.

    blend_mode: 'composite', 'max', 'min', or 'average', default: 'composite'
        Volume rendering blend mode.

    Point Sets
    ^^^^^^^^^^

    point_sets: point set, or sequence of point sets
        The point sets to visualize.

    point_set_colors: list of (r, g, b) colors
        Colors for the N points. See help(matplotlib.colors) for
        specification. Defaults to the Glasbey series of categorical colors.

    point_set_opacities: array of floats, default: [1.0,]*n
        Opacity for the point sets, in the range (0.0, 1.0].

    point_set_sizes: array of unsigned integers, default: [3,]*n
        Sizes for the point sets, in pixel size units.

    point_set_representations: list of strings, default: ['points',]*n
        How to represent the point set. One of 'hidden', 'points', or 'spheres'.

    Geometries
    ^^^^^^^^^^

    geometries: geometries, or sequence of geometries
        The geometries to visualize.

    geometry_colors: list of RGB colors
        Colors for the N geometries. See help(matplotlib.colors) for
        specification. Defaults to the Glasbey series of categorical colors.

    geometry_opacities: list of floats, default: [1.0,]*n
        Opacity for the point sets, in the range (0.0, 1.0].


    Other Parameters
    ----------------

    units: string, default: ''
        Units to display in the scale bar.

    actors: vtkActor, vtkAssembly, vtkVolume, default: None
        List of standard vtk objects, colors are extracted from their properties

    size_limit_2d: 2x1 numpy int64 array, default: [1024, 1024]
        Size limit for 2D image visualization. If the roi is larger than this
        size, it will be downsampled for visualization

    size_limit_3d: 3x1 numpy int64 array, default: [192, 192, 192]
        Size limit for 3D image visualization. If the roi is larger than this
        size, it will be downsampled for visualization.

    sample_distance: float, default: 0.25
        Sampling distance for volume rendering, normalized from 0.0 to 1.0.
        Lower values result in a higher quality rendering. High values improve
        the framerate.

    Returns
    -------
    viewer : ipywidget
        Display by placing at the end of a Jupyter cell or calling
        IPython.display.display. Query or set properties on the object to change
        the visualization or retrieve values created by interacting with the
        widget.
    """

    if point_sets is None:
        point_sets = []
    if point_set_colors is None:
        point_set_colors = []
    if point_set_opacities is None:
        point_set_opacities = []
    if point_set_representations is None:
        point_set_representations = []
    if point_set_sizes is None:
        point_set_sizes = []
    if geometries is None:
        geometries = []
    if geometry_colors is None:
        geometry_colors = []
    if geometry_opacities is None:
        geometry_opacities = []

    # this block allows the user to pass already formed vtkActor vtkVolume
    # objects
    actors = kwargs.pop("actors", None)
    if have_vtk and actors is not None:
        if not isinstance(actors, (list, tuple)
                          ):  # passing the object directly, so make it a list
            actors = [actors]

        images = []
        if have_mayavi:
            actors = _process_mayavi_actors(actors)

        for a in actors:
            if isinstance(a, vtk.vtkAssembly):  # unpack assemblies
                cl = vtk.vtkPropCollection()
                a.GetActors(cl)
                cl.InitTraversal()
                for i in range(a.GetNumberOfPaths()):
                    ac = vtk.vtkActor.SafeDownCast(cl.GetNextProp())
                    apoly = ac.GetMapper().GetInput()
                    prop = ac.GetProperty()
                    transform = vtk.vtkTransform()
                    transform.SetMatrix(ac.GetMatrix())
                    tp = vtk.vtkTransformPolyDataFilter()
                    tp.SetTransform(transform)
                    tp.SetInputData(apoly)
                    tp.Update()
                    poly = tp.GetOutput()
                    if poly.GetNumberOfPolys():
                        geometries.insert(0, poly)
                        geometry_colors.insert(0, prop.GetColor())
                        geometry_opacities.insert(0, prop.GetOpacity())
                    else:
                        point_sets.insert(0, poly)
                        point_set_colors.insert(0, prop.GetColor())
                        point_set_opacities.insert(0, prop.GetOpacity())

            elif isinstance(a, vtk.vtkActor):
                apoly = a.GetMapper().GetInput()
                transform = vtk.vtkTransform()
                transform.SetMatrix(a.GetMatrix())
                tp = vtk.vtkTransformPolyDataFilter()
                tp.SetTransform(transform)
                tp.SetInputData(apoly)
                tp.Update()
                poly = tp.GetOutput()
                prop = a.GetProperty()
                if (poly.GetNumberOfPolys() or poly.GetNumberOfStrips()
                   or poly.GetNumberOfLines()):
                    geometries.insert(0, poly)
                    geometry_colors.insert(0, prop.GetColor())
                    geometry_opacities.insert(0, prop.GetOpacity())
                else:
                    point_sets.insert(0, poly)
                    point_set_colors.insert(0, prop.GetColor())
                    point_set_opacities.insert(0, prop.GetOpacity())

            elif isinstance(a, vtk.vtkVolume):
                images.append(a.GetMapper().GetInput())

        if image is None and len(images):  # only one image is rendered
            image = images[0]

    viewer = Viewer(image=image,
                    label_image=label_image,
                    label_image_names=label_image_names,
                    label_image_blend=label_image_blend,
                    label_image_weights=label_image_weights,
                    cmap=cmap,
                    lut=lut,
                    select_roi=select_roi,
                    interpolation=interpolation,
                    gradient_opacity=gradient_opacity,
                    opacity_gaussians=opacity_gaussians,
                    slicing_planes=slicing_planes,
                    shadow=shadow, blend_mode=blend_mode,
                    point_sets=point_sets,
                    point_set_colors=point_set_colors,
                    point_set_opacities=point_set_opacities,
                    point_set_representations=point_set_representations,
                    point_set_sizes=point_set_sizes,
                    geometries=geometries, geometry_colors=geometry_colors,
                    geometry_opacities=geometry_opacities,
                    rotate=rotate, ui_collapsed=ui_collapsed,
                    annotations=annotations, axes=axes, mode=mode,
                    **kwargs)
    return viewer
