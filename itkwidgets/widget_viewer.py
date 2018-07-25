"""Viewer class

Visualization of an image.

In the future, will add optional segmentation mesh overlay.
"""

import collections
import functools
import time

import ipywidgets as widgets
from traitlets import Unicode, validate
from .trait_types import ITKImage, itkimage_serialization
import ipywebrtc

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
class Viewer(ipywebrtc.MediaStream):
    """Viewer widget class."""
    _view_name = Unicode('ViewerView').tag(sync=True)
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _view_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _model_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _view_module_version = Unicode('^0.10.2').tag(sync=True)
    _model_module_version = Unicode('^0.10.2').tag(sync=True)
    image = ITKImage(default_value=None, allow_none=True).tag(sync=False, **itkimage_serialization)
    _image_modified_time = 0
    rendered_image = ITKImage(default_value=None, allow_none=True).tag(sync=True, **itkimage_serialization)
    _rendered_image_modified_time = 0

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

def view(image):
    """View the provided image."""
    viewer = Viewer(image=image)
    return viewer
