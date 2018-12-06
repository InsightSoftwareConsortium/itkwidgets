"""Viewer class

Visualization of an image.

In the future, will add optional segmentation mesh overlay.
"""

import collections
import functools
import time

import itk
import numpy as np
import ipywidgets as widgets
from traitlets import CBool, CFloat, Unicode, CaselessStrEnum, Tuple, List, TraitError, validate
from ipydatawidgets import NDArray, array_serialization, shape_constraints
from .trait_types import ITKImage, itkimage_serialization
try:
    import ipywebrtc
    ViewerParent = ipywebrtc.MediaStream
except ImportError:
    ViewerParent = widgets.DOMWidget

from . import cm


COLORMAPS = ("2hot",
    "Asymmtrical Earth Tones (6_21b)",
    "Black, Blue and White",
    "Black, Orange and White",
    "Black-Body Radiation",
    "Blue to Red Rainbow",
    "Blue to Yellow",
    "Blues",
    "BrBG",
    "BrOrYl",
    "BuGn",
    "BuGnYl",
    "BuPu",
    "BuRd",
    "CIELab Blue to Red",
    "Cold and Hot",
    "Cool to Warm",
    "Cool to Warm (Extended)",
    "GBBr",
    "GYPi",
    "GnBu",
    "GnBuPu",
    "GnRP",
    "GnYlRd",
    "Grayscale",
    "Green-Blue Asymmetric Divergent (62Blbc)",
    "Greens",
    "GyRd",
    "Haze",
    "Haze_cyan",
    "Haze_green",
    "Haze_lime",
    "Inferno (matplotlib)",
    "Linear Blue (8_31f)",
    "Linear YGB 1211g",
    "Magma (matplotlib)",
    "Muted Blue-Green",
    "OrPu",
    "Oranges",
    "PRGn",
    "PiYG",
    "Plasma (matplotlib)",
    "PuBu",
    "PuOr",
    "PuRd",
    "Purples",
    "Rainbow Blended Black",
    "Rainbow Blended Grey",
    "Rainbow Blended White",
    "Rainbow Desaturated",
    "RdOr",
    "RdOrYl",
    "RdPu",
    "Red to Blue Rainbow",
    "Reds",
    "Spectral_lowBlue",
    "Viridis (matplotlib)",
    "Warm to Cool",
    "Warm to Cool (Extended)",
    "X Ray",
    "Yellow 15",
    "blot",
    "blue2cyan",
    "blue2yellow",
    "bone_Matlab",
    "coolwarm",
    "copper_Matlab",
    "gist_earth",
    "gray_Matlab",
    "heated_object",
    "hsv",
    "hue_L60",
    "jet",
    "magenta",
    "nic_CubicL",
    "nic_CubicYF",
    "nic_Edge",
    "pink_Matlab",
    "rainbow")


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
                if counter == counters[key]:  # only execute if the counter wasn't changed in the meantime
                    f(*args, **kwargs)
            ioloop = get_ioloop()

            def thread_safe():
                ioloop.add_timeout(time.time() + delay_seconds, debounced_execute)

            if ioloop is None:  # we live outside of IPython (e.g. unittest), so execute directly
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
                except StopIteration as e:
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
    _view_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _model_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _view_module_version = Unicode('^0.15.2').tag(sync=True)
    _model_module_version = Unicode('^0.15.2').tag(sync=True)
    image = ITKImage(default_value=None, allow_none=True, help="Image to visualize.").tag(sync=False, **itkimage_serialization)
    rendered_image = ITKImage(default_value=None, allow_none=True).tag(sync=True, **itkimage_serialization)
    _rendering_image = CBool(default_value=False, help="We are currently volume rendering the image.").tag(sync=True)
    ui_collapsed = CBool(default_value=False, help="Collapse the built in user interface.").tag(sync=True)
    annotations = CBool(default_value=True, help="Show annotations.").tag(sync=True)
    mode = CaselessStrEnum(('x', 'y', 'z', 'v'), default_value='v', help="View mode: x: x plane, y: y plane, z: z plane, v: volume rendering").tag(sync=True)
    interpolation = CBool(default_value=True, help="Use linear interpolation in slicing planes.").tag(sync=True)
    cmap = Unicode('Viridis (matplotlib)').tag(sync=True)
    shadow = CBool(default_value=True, help="Use shadowing in the volume rendering.").tag(sync=True)
    slicing_planes = CBool(default_value=False, help="Display the slicing planes in volume rendering view mode.").tag(sync=True)
    gradient_opacity = CFloat(default_value=0.2, help="Volume rendering gradient opacity, from (0.0, 1.0]").tag(sync=True)
    roi = NDArray(dtype=np.float64, default_value=np.zeros((2, 3), dtype=np.float64),
                help="Region of interest: ((lower_x, lower_y, lower_z), (upper_x, upper_y, upper_z))")\
            .tag(sync=True, **array_serialization)\
            .valid(shape_constraints(2, 3))
    _largest_roi = NDArray(dtype=np.float64, default_value=np.zeros((2, 3), dtype=np.float64),
                help="Largest possible region of interest: ((lower_x, lower_y, lower_z), (upper_x, upper_y, upper_z))")\
            .tag(sync=True, **array_serialization)\
            .valid(shape_constraints(2, 3))
    select_roi = CBool(default_value=False, help="Enable an interactive region of interest widget for the image.").tag(sync=True)
    size_limit_2d = NDArray(dtype=np.int64, default_value=np.array([1024, 1024], dtype=np.int64),
            help="Size limit for 2D image visualization.").tag(sync=False)
    size_limit_3d = NDArray(dtype=np.int64, default_value=np.array([192, 192, 192], dtype=np.int64),
            help="Size limit for 3D image visualization.").tag(sync=False)
    _downsampling = CBool(default_value=False,
            help="We are downsampling the image to meet the size limits.").tag(sync=True)
    _reset_crop_requested = CBool(default_value=False,
            help="The user requested a reset of the roi.").tag(sync=True)


    def __init__(self, **kwargs):
        super(Viewer, self).__init__(**kwargs)
        dimension = self.image.GetImageDimension()
        largest_region = self.image.GetLargestPossibleRegion()
        size = largest_region.GetSize()

        # Cache this so we do not need to recompute on it when resetting the roi
        self._largest_roi_rendered_image = None
        self._largest_roi = np.zeros((2, 3), dtype=np.float64)
        if not np.any(self.roi):
            largest_index = largest_region.GetIndex()
            self.roi[0][:dimension] = np.array(self.image.TransformIndexToPhysicalPoint(largest_index))
            largest_index_upper = largest_index + size
            self.roi[1][:dimension] = np.array(self.image.TransformIndexToPhysicalPoint(largest_index_upper))
            self._largest_roi = self.roi.copy()

        if dimension == 2:
            for dim in range(dimension):
                if size[dim] > self.size_limit_2d[dim]:
                    self._downsampling = True
        else:
            for dim in range(dimension):
                if size[dim] > self.size_limit_3d[dim]:
                    self._downsampling = True
        if self._downsampling:
            self.extractor = itk.ExtractImageFilter.New(self.image)
            self.extractor.InPlaceOn()
            self.shrinker = itk.BinShrinkImageFilter.New(self.extractor)
        self._update_rendered_image()
        if self._downsampling:
            self.observe(self._on_roi_changed, ['roi'])

        self.observe(self._on_reset_crop_requested, ['_reset_crop_requested'])
        self.observe(self.update_rendered_image, ['image'])

    @debounced(delay_seconds=1.5, method=True)
    def _on_roi_changed(self, change=None):
        if self._downsampling:
            self._update_rendered_image()

    def _on_reset_crop_requested(self, change=None):
        if change.new == True and self._downsampling:
            dimension = self.image.GetImageDimension()
            largest_region = self.image.GetLargestPossibleRegion()
            size = largest_region.GetSize()
            largest_index = largest_region.GetIndex()
            new_roi = self.roi.copy()
            new_roi[0][:dimension] = np.array(self.image.TransformIndexToPhysicalPoint(largest_index))
            largest_index_upper = largest_index + size
            new_roi[1][:dimension] = np.array(self.image.TransformIndexToPhysicalPoint(largest_index_upper))
            self._largest_roi = new_roi.copy()
            self.roi = new_roi
        if change.new == True:
            self._reset_crop_requested = False

    @debounced(delay_seconds=0.2, method=True)
    def update_rendered_image(self, change=None):
        self._largest_roi_rendered_image = None
        self._largest_roi = np.zeros((2, 3), dtype=np.float64)
        self._update_rendered_image()

    @staticmethod
    def _find_shrink_factors(limit, dimension, size):
        shrink_factors = [1,] * dimension
        for dim in range(dimension):
          while(int(np.floor(float(size[dim]) / shrink_factors[dim])) > limit[dim]):
            shrink_factors[dim] += 1
        return shrink_factors

    def _update_rendered_image(self):
        if self.image is None:
            return
        if self._rendering_image:
            @yield_for_change(self, '_rendering_image')
            def f():
                x = yield
                assert(x == False)
            f()
        self._rendering_image = True

        if self._downsampling:
            dimension = self.image.GetImageDimension()
            index = self.image.TransformPhysicalPointToIndex(self.roi[0][:dimension])
            upper_index = self.image.TransformPhysicalPointToIndex(self.roi[1][:dimension])
            size = upper_index - index

            if dimension == 2:
                shrink_factors = self._find_shrink_factors(self.size_limit_2d, dimension, size)
            else:
                shrink_factors = self._find_shrink_factors(self.size_limit_3d, dimension, size)
            self.shrinker.SetShrinkFactors(shrink_factors)

            region = itk.ImageRegion[dimension]()
            region.SetIndex(index)
            region.SetSize(tuple(size))
            # Account for rounding
            # truncation issues
            region.PadByRadius(1)
            region.Crop(self.image.GetLargestPossibleRegion())

            self.extractor.SetExtractionRegion(region)

            size = region.GetSize()

            is_largest = False
            if np.any(self._largest_roi) and np.all(self._largest_roi == self.roi):
                is_largest = True
                if self._largest_roi_rendered_image is not None:
                    self.rendered_image = self._largest_roi_rendered_image
                    return

            self.shrinker.UpdateLargestPossibleRegion()
            if is_largest:
                self._largest_roi_rendered_image = self.shrinker.GetOutput()
                self._largest_roi_rendered_image.DisconnectPipeline()
                self._largest_roi_rendered_image.SetOrigin(self.roi[0][:dimension])
                self.rendered_image = self._largest_roi_rendered_image
                return
            shrunk = self.shrinker.GetOutput()
            shrunk.DisconnectPipeline()
            shrunk.SetOrigin(self.roi[0][:dimension])
            self.rendered_image = shrunk
        else:
            self.rendered_image = self.image

    @validate('gradient_opacity')
    def _validate_gradient_opacity(self, proposal):
        """Enforce 0 < value <= 1.0."""
        value = proposal['value']
        if value <= 0.0:
            return 0.01
        if value > 1.0:
            return 1.0
        return value

    @validate('cmap')
    def _validate_cmap(self, proposal):
        value = proposal['value']
        if not value in COLORMAPS:
            raise TraitError('Invalid colormap')
        return value

    def roi_region(self):
        """Return the itk.ImageRegion corresponding to the roi."""
        dimension = self.image.GetImageDimension()
        index = self.image.TransformPhysicalPointToIndex(tuple(self.roi[0][:dimension]))
        upper_index = self.image.TransformPhysicalPointToIndex(tuple(self.roi[1][:dimension]))
        size = upper_index - index
        for dim in range(dimension):
            size[dim] += 1
        region = itk.ImageRegion[dimension]()
        region.SetIndex(index)
        region.SetSize(tuple(size))
        region.Crop(self.image.GetLargestPossibleRegion())
        return region

    def roi_slice(self):
        """Return the numpy array slice corresponding to the roi."""
        dimension = self.image.GetImageDimension()
        region = self.roi_region()
        index = region.GetIndex()
        upper_index = np.array(index) + np.array(region.GetSize())
        slices = []
        for dim in range(dimension):
            slices.insert(0, slice(index[dim], upper_index[dim] + 1))
        return tuple(slices)


def view(image, ui_collapsed=False, annotations=True, interpolation=True,
        cmap=cm.viridis, mode='v', shadow=True, slicing_planes=False,
        gradient_opacity=0.22, **kwargs):
    """View the image.

    Creates and returns an ipywidget to visualize the image.

    The image can be 2D or 3D.

    The type of the image can be an numpy.array, itk.Image,
    vtk.vtkImageData, imglyb.ReferenceGuardingRandomAccessibleInterval, or
    something that is NumPy array-like, e.g. a Dask array.

    Parameters
    ----------
    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to visualize.

    ui_collapsed : bool, optional, default: False
        Collapse the native widget user interface.

    annotations : bool, optional, default: True
        Display annotations describing orientation and the value of a
        mouse-position-based data probe.

    interpolation: bool, optional, default: True
        Linear as opposed to nearest neighbor interpolation for image slices.

    cmap: string, optional, default: 'Viridis (matplotlib)'
        Colormap. Some valid values available at itkwidgets.cm.*

    mode: 'x', 'y', 'z', or 'v', optional, default: 'v'
        Only relevant for 3D images.
        Viewing mode:
            'x': x-plane
            'y': y-plane
            'z': z-plane
            'v': volume rendering

    shadow: bool, optional, default: True
        Use shadowing in the volume rendering.

    slicing_planes: bool, optional, default: False
        Enable slicing planes on the volume rendering.

    gradient_opacity: float, optional, default: 0.2
        Gradient opacity for the volume rendering, in the range (0.0, 1.0].

    select_roi: bool, optional, default: False
        Enable an interactive region of interest widget for the image.

    Other Parameters
    ----------------

    size_limit_2d: 2x1 numpy int64 array, optional, default: [1024, 1024]
        Size limit for 2D image visualization. If the roi is larger than this
        size, it will be downsampled for visualization

    size_limit_3d: 3x1 numpy int64 array, optional, default: [192, 192, 192]
        Size limit for 3D image visualization. If the roi is larger than this
        size, it will be downsampled for visualization.

    Returns
    -------
    viewer : ipywidget
        Display by placing at the end of a Jupyter cell or calling
        IPython.display.display. Query or set properties on the object to change
        the visualization or retrieve values created by interacting with the
        widget.
    """
    viewer = Viewer(image=image, ui_collapsed=ui_collapsed,
            annotations=annotations, interpolation=interpolation, cmap=cmap,
            mode=mode, shadow=shadow, slicing_planes=slicing_planes,
            gradient_opacity=gradient_opacity, **kwargs)
    return viewer
