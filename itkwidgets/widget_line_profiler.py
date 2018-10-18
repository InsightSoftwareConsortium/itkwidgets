"""LineProfiler class

Image visualization with a line profile.
"""

from traitlets import Unicode

import numpy as np
import ipywidgets as widgets
from .widget_viewer import Viewer
from ipydatawidgets import NDArray, array_serialization, shape_constraints
from traitlets import CBool
import matplotlib.pyplot as plt
import matplotlib
import IPython

@widgets.register
class LineProfiler(Viewer):
    """LineProfiler widget class."""
    _view_name = Unicode('LineProfilerView').tag(sync=True)
    _model_name = Unicode('LineProfilerModel').tag(sync=True)
    _view_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _model_module = Unicode('itk-jupyter-widgets').tag(sync=True)
    _view_module_version = Unicode('^0.12.2').tag(sync=True)
    _model_module_version = Unicode('^0.12.2').tag(sync=True)
    point1 = NDArray(dtype=np.float64, default_value=np.zeros((3,), dtype=np.float64),
                help="First point in physical space that defines the line profile")\
            .tag(sync=True, **array_serialization)\
            .valid(shape_constraints(3,))
    point2 = NDArray(dtype=np.float64, default_value=np.ones((3,), dtype=np.float64),
                help="First point in physical space that defines the line profile")\
            .tag(sync=True, **array_serialization)\
            .valid(shape_constraints(3,))
    _select_initial_points = CBool(default_value=False, help="We will select the initial points for the line profile.").tag(sync=True)

    def __init__(self, **kwargs):
        if 'point1' not in kwargs or 'point2' not in kwargs:
            self._select_initial_points = True
            # Default to z-plane mode instead of the 3D volume if we need to
            # select points
            if 'mode' not in kwargs:
                kwargs['mode'] = 'z'
        super(LineProfiler, self).__init__(**kwargs)

def line_profile(image, **viewer_kwargs):
    """View the image with a line profile.

    Creates and returns an ipywidget to visualize the image along with a line
    profile.

    The image can be 2D or 3D.

    Parameters
    ----------
    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to visualize.

    viewer_kwargs :
        Keyword arguments for the viewer. See help(itkwidgets.view).

    """

    profiler = LineProfiler(image=image, **viewer_kwargs)

    ipython = IPython.get_ipython()
    ipython.enable_matplotlib('widget')

    is_interactive = matplotlib.is_interactive()
    matplotlib.interactive(False)

    x = np.linspace(0, 2*np.pi, 400)
    y = np.sin(x**2)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    fig.canvas.draw()
    fig.canvas.flush_events()

    widget = widgets.VBox([profiler, fig.canvas])

    matplotlib.interactive(is_interactive)

    return widget
