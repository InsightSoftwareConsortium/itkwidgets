"""Viewer class

Visualization of an image.

In the future, will add optional segmentation mesh overlay.
"""

import collections
import functools
import time

import ipywidgets as widgets
from traitlets import CBool, Unicode, CaselessStrEnum, validate
from .trait_types import ITKImage, itkimage_serialization
try:
    import ipywebrtc
    ViewerParent = ipywebrtc.MediaStream
except ImportError:
    ViewerParent = widgets.DOMWidget

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
    _view_module_version = Unicode('^0.11.0').tag(sync=True)
    _model_module_version = Unicode('^0.11.0').tag(sync=True)
    image = ITKImage(default_value=None, allow_none=True).tag(sync=False, **itkimage_serialization)
    _image_modified_time = 0
    rendered_image = ITKImage(default_value=None, allow_none=True).tag(sync=True, **itkimage_serialization)
    _rendered_image_modified_time = 0
    ui_collapsed = CBool(default_value=False).tag(sync=True)
    annotations = CBool(default_value=True).tag(sync=True)
    interpolation = CBool(default_value=True).tag(sync=True)
    mode = CaselessStrEnum(('x', 'y', 'z', 'v'), default_value='v').tag(sync=True)
    shadow = CBool(default_value=True).tag(sync=True)
    slicing_planes = CBool(default_value=False).tag(sync=True)

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

def view(image, ui_collapsed=False, annotations=True, interpolation=True,
        mode='v', shadow=True, slicing_planes=False):
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

    Returns
    -------
    viewer : ipywidget
        Display by placing at the end of a Jupyter cell or calling
        IPython.display.display. Query or set properties on the object to change
        the visualization or retrieve values created by interacting with the
        widget.
    """
    viewer = Viewer(image=image, ui_collapsed=ui_collapsed,
            annotations=annotations, interpolation=interpolation, mode=mode,
            shadow=shadow, slicing_planes=slicing_planes)
    return viewer
