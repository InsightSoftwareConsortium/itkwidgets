"""LineProfiler class

Image visualization with a line profile.
"""

from traitlets import Unicode

import ipywidgets as widgets
from .widget_viewer import Viewer

@widgets.register
class LineProfiler(Viewer):
    """LineProfiler widget class."""
    _view_name = Unicode('LineProfilerView').tag(sync=True)
    _model_name = Unicode('LineProfilerModel').tag(sync=True)
    _view_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _model_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _view_module_version = Unicode('^0.12.2').tag(sync=True)
    _model_module_version = Unicode('^0.12.2').tag(sync=True)

    def __init__(self, **kwargs):
        super(LineProfiler, self).__init__(**kwargs)

def line_profile(image):
    """View the image with a line profile.

    Creates and returns an ipywidget to visualize the image along with a line
    profile.

    The image can be 2D or 3D.

    Parameters
    ----------
    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to visualize.

    """

    viewer = LineProfiler(image=image)

    return viewer
