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

@widgets.register
class Viewer(ViewerParent):
    """Viewer widget class."""
    _view_name = Unicode('ViewerView').tag(sync=True)
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _view_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _model_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _view_module_version = Unicode('^0.12.1').tag(sync=True)
    _model_module_version = Unicode('^0.12.1').tag(sync=True)
    image = ITKImage(default_value=None, allow_none=True, help="Image to visualize.").tag(sync=False, **itkimage_serialization)
    rendered_image = ITKImage(default_value=None, allow_none=True).tag(sync=True, **itkimage_serialization)
    ui_collapsed = CBool(default_value=False, help="Collapse the built in user interface.").tag(sync=True)
    annotations = CBool(default_value=True, help="Show annotations.").tag(sync=True)
    mode = CaselessStrEnum(('x', 'y', 'z', 'v'), default_value='v', help="View mode: x: x plane, y: y plane, z: z plane, v: volume rendering").tag(sync=True)
    interpolation = CBool(default_value=True, help="Use linear interpolation in slicing planes.").tag(sync=True)
    cmap = Unicode('Viridis (matplotlib)').tag(sync=True)
    shadow = CBool(default_value=True, help="Use shadowing in the volume rendering.").tag(sync=True)
    slicing_planes = CBool(default_value=False, help="Display the slicing planes in volume rendering view mode.").tag(sync=True)
    gradient_opacity = CFloat(default_value=0.2, help="Volume rendering gradient opacity, from (0.0, 1.0]").tag(sync=True)
    roi = List(List(CFloat()),
            default_value=[[0., 0., 0.], [0., 0., 0.]],
            help="Region of interest: ((lower_x, lower_y, lower_z), (upper_x, upper_y, upper_z))").tag(sync=True)

    def __init__(self, **kwargs):
        super(Viewer, self).__init__(**kwargs)
        self._update_rendered_image()
        self.observe(self.update_rendered_image, ['image'])

    @debounced(delay_seconds=0.4, method=True)
    def update_rendered_image(self, change=None):
        self._update_rendered_image()

    def _update_rendered_image(self):
        if self.image is None:
            return
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
        index = self.image.TransformPhysicalPointToIndex(self.roi[0][:dimension])
        upperIndex = self.image.TransformPhysicalPointToIndex(self.roi[1][:dimension])
        size = upperIndex - index
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
        upperIndex = np.array(index) + np.array(region.GetSize())
        slices = []
        for dim in range(dimension):
            slices.insert(0, slice(index[dim], upperIndex[dim] + 1))
        return tuple(slices)


def view(image, ui_collapsed=False, annotations=True, interpolation=True,
        cmap=cm.viridis, mode='v', shadow=True, slicing_planes=False, gradient_opacity=0.2):
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
            gradient_opacity=gradient_opacity)
    return viewer
