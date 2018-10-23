"""LineProfiler class

Image visualization with a line profile.
"""

from traitlets import Unicode

import numpy as np
import scipy.ndimage
import ipywidgets as widgets
from .widget_viewer import Viewer
from ipydatawidgets import NDArray, array_serialization, shape_constraints
from traitlets import CBool
import matplotlib.pyplot as plt
import matplotlib
import IPython
import itk
from ._to_itk import to_itk_image

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

def line_profile(image, order=2, plotter=None, comparisons=None, **viewer_kwargs):
    """View the image with a line profile.

    Creates and returns an ipywidget to visualize the image along with a line
    profile.

    The image can be 2D or 3D.

    Parameters
    ----------
    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to visualize.

    order : int, optional
        Spline order for line profile interpolation. The order has to be in the
        range 0-5.

    plotter : 'plotly', 'bqplot', or 'ipympl', optional
        Plotting library to use. If not defined, use plotly if available,
        otherwise bqplot if available, otherwise ipympl.

    comparisons: dict, optional
        A dictionary whose keys are legend labels and whose values are other
        images whose intensities to plot over the same line.

    viewer_kwargs : optional
        Keyword arguments for the viewer. See help(itkwidgets.view).

    """

    profiler = LineProfiler(image=image, **viewer_kwargs)

    if not plotter:
        try:
            import plotly.graph_objs as go
            plotter = 'plotly'
        except ImportError:
            pass
    if not plotter:
        try:
            import bqplot
            plotter = 'bqplot'
        except ImportError:
            pass
    if not plotter:
        plotter = 'ipympl'


    def get_profile(image_or_array):
        image_from_array = to_itk_image(image_or_array)
        if image_from_array:
            image_ = image_from_array
        else:
            image_ = image_or_array
        image_array = itk.GetArrayViewFromImage(image_)
        dimension = image_.GetImageDimension()
        distance = np.sqrt(sum([(profiler.point1[ii] - profiler.point2[ii])**2 for ii in range(dimension)]))
        index1 = tuple(image_.TransformPhysicalPointToIndex(tuple(profiler.point1[:dimension])))
        index2 = tuple(image_.TransformPhysicalPointToIndex(tuple(profiler.point2[:dimension])))
        num_points = int(np.round(np.sqrt(sum([(index1[ii] - index2[ii])**2 for ii in range(dimension)])) * 2.1))
        coords = [np.linspace(index1[ii], index2[ii], num_points) for ii in range(dimension)]
        mapped = scipy.ndimage.map_coordinates(image_array, np.vstack(coords[::-1]),
                                               order=order, mode='nearest')
        return np.linspace(0.0, distance, num_points), mapped

    if plotter == 'plotly':
        import plotly.graph_objs as go
        layout = go.Layout(
            xaxis=dict(title='Distance'),
            yaxis=dict(title='Intensity')
            )
        fig = go.FigureWidget(layout=layout)
    elif plotter == 'bqplot':
        import bqplot
        x_scale = bqplot.LinearScale()
        y_scale = bqplot.LinearScale()
        x_axis = bqplot.Axis(scale=x_scale, grid_lines='solid', label='Distance')
        y_axis = bqplot.Axis(scale=y_scale, orientation='vertical', grid_lines='solid', label='Intensity')
        labels = ['Reference']
        display_legend = False
        if comparisons:
            display_legend=True
            labels += [label for label in comparisons.keys()]
        lines = [bqplot.Lines(scales={'x': x_scale, 'y': y_scale},
            labels=labels, display_legend=display_legend, enable_hover=True)]
        fig = bqplot.Figure(marks=lines, axes=[x_axis, y_axis])
    elif plotter == 'ipympl':
        ipython = IPython.get_ipython()
        ipython.enable_matplotlib('widget')

        is_interactive = matplotlib.is_interactive()
        matplotlib.interactive(False)

        fig, ax = plt.subplots()
    else:
        raise ValueError('Invalid plotter: ' + plotter)

    def update_plot():
        if plotter == 'plotly':
            distance, intensity = get_profile(image)
            fig.data[0]['x'] = distance
            fig.data[0]['y'] = intensity
            if comparisons:
                for ii, image_ in enumerate(comparisons.values()):
                    distance, intensity = get_profile(image_)
                    fig.data[ii+1]['x'] = distance
                    fig.data[ii+1]['y'] = intensity
        elif plotter == 'bqplot':
            distance, intensity = get_profile(image)
            if comparisons:
                for image_ in comparisons.values():
                    distance_, intensity_ = get_profile(image_)
                    distance = np.vstack((distance, distance_))
                    intensity = np.vstack((intensity, intensity_))
            fig.marks[0].x = distance
            fig.marks[0].y = intensity
        elif plotter == 'ipympl':
            ax.plot(*get_profile(image))
            if comparisons:
                ax.plot(*get_profile(image), label='Reference')
                for label, image_ in comparisons.items():
                    ax.plot(*get_profile(image_), label=label)
                ax.legend()
            else:
                ax.plot(*get_profile(image))

            ax.set_xlabel('Distance')
            ax.set_ylabel('Intensity')
            fig.canvas.draw()
            fig.canvas.flush_events()

    def update_profile(change):
        if plotter == 'plotly':
            update_plot()
        elif plotter == 'bqplot':
            update_plot()
        elif plotter == 'ipympl':
            is_interactive = matplotlib.is_interactive()
            matplotlib.interactive(False)
            ax.clear()
            update_plot()
            matplotlib.interactive(is_interactive)

    if plotter == 'plotly':
        distance, intensity = get_profile(image)
        trace = go.Scattergl(x=distance, y=intensity, name='Reference')
        fig.add_trace(trace)
        if comparisons:
            for label, image_ in comparisons.items():
                distance, intensity = get_profile(image_)
                trace = go.Scattergl(x=distance, y=intensity, name=label)
                fig.add_trace(trace)
        widget = widgets.VBox([profiler, fig])
    elif plotter == 'bqplot':
        update_plot()
        widget = widgets.VBox([profiler, fig])
    elif plotter == 'ipympl':
        update_plot()
        widget = widgets.VBox([profiler, fig.canvas])

    profiler.observe(update_profile, names=['point1', 'point2'])

    return widget
