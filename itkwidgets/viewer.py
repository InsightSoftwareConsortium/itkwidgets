import asyncio
import queue
import threading
from imjoy_rpc import api
from typing import List
from IPython.display import display, HTML
from IPython.lib import backgroundjobs as bg
import uuid

from ._type_aliases import Gaussians, Style, Image, Point_Sets
from ._initialization_params import init_params_dict, init_key_aliases
from ._method_types import deferred_methods
from .integrations import _detect_render_type, _get_viewer_image, _get_viewer_point_sets
from .render_types import RenderType
from .viewer_config import ITK_VIEWER_SRC, PYDATA_SPHINX_HREF, MUI_HREF

__all__ = [
    "Viewer",
    "view",
]

_viewer_count = 1
_codecs_registered = False


class ViewerRPC:
    """Viewer remote procedure interface."""

    def __init__(
        self, ui_collapsed=True, rotate=False, ui="pydata-sphinx", **add_data_kwargs
    ):
        """Create a viewer."""
        self._init_viewer_kwargs = dict(ui_collapsed=ui_collapsed, rotate=rotate, ui=ui)
        self._init_viewer_kwargs.update(**add_data_kwargs)
        self.init_data = {}
        self.img = display(HTML(f'<div />'), display_id=str(uuid.uuid4()))
        self.wid = None
        self.viewer_event = threading.Event()
        self.data_event = threading.Event()

    def _get_input_data(self):
        input_options = ["data", "image", "label_image", "point_sets"]
        inputs = []
        for option in input_options:
            data = self._init_viewer_kwargs.get(option, None)
            if data is not None:
                inputs.append((option, data))
        return inputs

    async def setup(self):
        pass

    async def run(self, ctx):
        """ImJoy plugin setup function."""
        global _viewer_count
        ui = self._init_viewer_kwargs.get("ui", None)
        if ui == "pydata-sphinx":
            config = {
                "uiMachineOptions": {
                    "href": PYDATA_SPHINX_HREF,
                    "export": "default",
                }
            }
        elif ui == "mui":
            config = {
                "uiMachineOptions": {
                    "href": MUI_HREF,
                    "export": "default",
                }
            }
        elif ui != "reference":
            config = ui
        else:
            config = {}

        inputs = self._get_input_data()

        self.init_data.clear()
        result= None
        for (input_type, data) in inputs:
            render_type = _detect_render_type(data, input_type)
            key = init_key_aliases()[input_type]
            if render_type is RenderType.IMAGE:
                if input_type == 'label_image':
                    result = _get_viewer_image(data, label=True)
                else:
                    result = _get_viewer_image(data, label=False)
            elif render_type is RenderType.POINT_SET:
                result = _get_viewer_point_sets(data)
            if result is None:
                result = data
            self.init_data[key] = result

        itk_viewer = await api.createWindow(
            name=f"itkwidgets viewer {_viewer_count}",
            type="itk-vtk-viewer",
            src=ITK_VIEWER_SRC,
            fullscreen=True,
            data=self.init_data,
            # config should be a python data dictionary and can't be a string e.g. 'pydata-sphinx',
            config=config,
        )
        _viewer_count += 1
        itk_viewer.registerEventListener(
            'renderedImageAssigned', self.set_event
        )
        # Once the viewer has been created any queued requests can be run
        asyncio.get_running_loop().call_soon_threadsafe(self.viewer_event.set)

        self.set_default_ui_values(itk_viewer)
        self.itk_viewer = itk_viewer
        self.wid = self.itk_viewer.config.window_id

        # Create the initial screenshot
        await self.create_screenshot()
        # Wait and then update the screenshot in case rendered level changed
        await asyncio.sleep(10)
        await self.create_screenshot()
        # Set up an event listener so that the embedded
        # screenshot is updated when the user requests
        itk_viewer.registerEventListener(
            'screenshotTaken', self.update_screenshot
        )

    def set_default_ui_values(self, itk_viewer):
        settings = init_params_dict(itk_viewer)
        for key, value in self._init_viewer_kwargs.items():
            if key in settings.keys():
                settings[key](value)

    async def create_screenshot(self):
        base64_image = await self.itk_viewer.captureImage()
        self.update_screenshot(base64_image)

    def update_screenshot(self, base64_image):
        html = HTML(
            f'''
                <img id="screenshot_{self.wid}" src={base64_image}>
                <script type="text/javascript">
                    var image = document.getElementById("screenshot_{self.wid}");
                    image.src = "{base64_image}";
                    var viewer = document.getElementById("{self.wid}");
                    // Hide the static image if the Viewer is visible
                    image.style.display = viewer ? "none" : "block";
                </script>
            ''')
        self.img.display(html)

    def set_event(self, event_data):
        # Once the data has been set the deferred queue requests can be run
        asyncio.get_running_loop().call_soon_threadsafe(self.data_event.set)


class Viewer:
    """Pythonic Viewer class."""

    def __init__(
        self, ui_collapsed=True, rotate=False, ui="pydata-sphinx", **add_data_kwargs
    ):
        """Create a viewer."""
        self.bg_jobs = bg.BackgroundJobManager()
        self.viewer_rpc = ViewerRPC(
            ui_collapsed=ui_collapsed, rotate=rotate, ui=ui, **add_data_kwargs
        )
        self.queue = queue.Queue()
        self.deferred_queue = queue.Queue()
        self.bg_thread = self.bg_jobs.new(self.queue_worker)
        api.export(self.viewer_rpc)

    @property
    def loop(self):
        return asyncio.get_running_loop()

    async def run_queued_requests(self):
        def _run_queued_requests(queue):
            method_name, args = queue.get().values()
            fn = getattr(self.viewer_rpc.itk_viewer, method_name)
            self.loop.call_soon_threadsafe(asyncio.ensure_future, fn(*args))

        # Wait for the viewer to be created
        self.viewer_rpc.viewer_event.wait()
        while self.queue.qsize():
            _run_queued_requests(self.queue)
        # Wait for the data to be set
        self.viewer_rpc.data_event.wait()
        while self.deferred_queue.qsize():
            _run_queued_requests(self.deferred_queue)

    def queue_worker(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self.run_queued_requests())
        loop.run_until_complete(task)

    def queue_request(self, method, *args):
        if hasattr(self.viewer_rpc, 'itk_viewer'):
            fn = getattr(self.viewer_rpc.itk_viewer, method)
            fn(*args)
        elif method in deferred_methods():
            self.deferred_queue.put({'method': method, 'arg': args})
        else:
            self.queue.put({'method': method, 'arg': args})

    def set_annotations_enabled(self, enabled: bool):
        self.queue_request('setAnnotationsEnabled', enabled)

    def set_axes_enabled(self, enabled: bool):
        self.queue_request('setAxesEnabled', enabled)

    def set_background_color(self, bgColor: List[float]):
        self.queue_request('setBackgroundColor', bgColor)

    def set_image(self, image: Image):
        render_type = _detect_render_type(image, 'image')
        if render_type is RenderType.IMAGE:
            image = _get_viewer_image(image, label=False)
            self.queue_request('setImage', image)
        elif render_type is RenderType.POINT_SET:
            image = _get_viewer_point_sets(image)
            self.queue_request('setPointSets', image)

    def set_image_blend_mode(self, mode: str):
        self.queue_request('setImageBlendMode', mode)

    def set_image_color_map(self, colorMap: str):
        self.queue_request('setImageColorMap', colorMap)

    def set_image_color_range(self, range: List[float]):
        self.queue_request('setImageColorRange', range)

    def set_image_color_range_bounds(self, range: List[float]):
        self.queue_request('setImageColorRangeBounds', range)

    def set_image_component_visibility(self, visibility: bool):
        self.queue_request('setImageComponentVisibility', visibility)

    def set_image_gradient_opacity(self, opacity: float):
        self.queue_request('setImageGradientOpacity', opacity)

    def set_image_gradient_opacity_scale(self, min: float):
        self.queue_request('setImageGradientOpacityScale', min)

    def set_image_interpolation_enabled(self, enabled: bool):
        self.queue_request('setImageInterpolationEnabled', enabled)

    def set_image_piecewise_function_gaussians(self, gaussians: Gaussians):
        self.queue_request('setImagePiecewiseFunctionGaussians', gaussians)

    def set_image_shadow_enabled(self, enabled: bool):
        self.queue_request('setImageShadowEnabled', enabled)

    def set_image_volume_sample_distance(self, distance: float):
        self.queue_request('setImageVolumeSampleDistance', distance)

    def set_label_image(self, label_image: Image):
        render_type = _detect_render_type(label_image, 'image')
        if render_type is RenderType.IMAGE:
            label_image = _get_viewer_image(label_image, label=True)
            self.queue_request('setImage', label_image)
        elif render_type is RenderType.POINT_SET:
            label_image = _get_viewer_point_sets(label_image)
            self.queue_request('setPointSets', label_image)

    def set_label_image_blend(self, blend: float):
        self.queue_request('setLabelImageBlend', blend)

    def set_label_image_label_names(self, names: List[str]):
        self.queue_request('setLabelImageLabelNames', names)

    def set_label_image_lookup_table(self, lookupTable: str):
        self.queue_request('setLabelImageLookupTable', lookupTable)

    def set_label_image_weights(self, weights: float):
        self.queue_request('setLabelImageWeights', weights)

    def select_layer(self, name: str):
        self.queue_request('selectLayer', name)

    def set_layer_visibility(self, visible: bool):
        self.queue_request('setLayerVisibility', visible)

    def set_point_sets(self, pointSets: Point_Sets):
        self.queue_request('setPointSets', pointSets)

    def set_rendering_view_container_style(self, containerStyle: Style):
        self.queue_request('setRenderingViewContainerStyle', containerStyle)

    def set_rotate(self, enabled: bool):
        self.queue_request('setRotateEnabled', enabled)

    def set_ui_collapsed(self, collapsed: bool):
        self.queue_request('setUICollapsed', collapsed)

    def set_units(self, units: str):
        self.queue_request('setUnits', units)

    def set_view_mode(self, mode: str):
        self.queue_request('setViewMode', mode)

    def set_x_slice(self, position: float):
        self.queue_request('setXSlice', position)

    def set_y_slice(self, position: float):
        self.queue_request('setYSlice', position)

    def set_z_slice(self, position: float):
        self.queue_request('setZSlice', position)


def view(data=None, **kwargs):
    """View the image and/or point sets.

    Creates and returns an ImJoy plugin ipywidget to visualize an image, and/or
    point sets.

    The image can be 2D or 3D. The type of the image can be an numpy.array,
    itk.Image, or vtk.vtkImageData.

    A point set or a sequence of points sets can be visualized. The type of the
    point set can be an numpy.array (Nx3 array of point positions).

    Parameters
    ----------
    General Interface
    ^^^^^^^^^^^^^^^^^
    ui_collapsed : bool, default: True
        Collapse the native widget user interface.
    rotate : bool, default: False
        Continuously rotate the camera around the scene in volume rendering
        mode.
    annotations: bool, default: True
        Display annotations describing orientation and the value of a
        mouse-position-based data probe.
    axes: bool, default: False
        Display axes.
    bg_color: (red, green, blue) tuple, components from 0.0 to 1.0
        Background color. Default is based on the current Jupyter theme.
    container_style: dict
        The CSS style for the rendering view `div`'s.

    Images
    ^^^^^^
    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to visualize.
    label_image: array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D label map to visualize. If an image is also provided, the
        label map must have the same size.
    label_blend: float, default: 0.5
        Label map blend with intensity image, from 0.0 to 1.0.
    label_names: list of (label_value, label_name)
        String names associated with the integer label values.
    label_lut: string, default: 'glasbey'
        Lookup table for the label map.
    label_weights: float
        The rendering weight assigned to current label. Values range from 0.0
        to 1.0.
    color_range: list, default: The [min, max] range of the data values
        The [min, max] range of intensity values mapped to colors for the given
        image component identified by name.
    color_bounds: list, default: The [min, max] range of the data values
        The [min, max] range of intensity values for color maps that provide a
        bounds for user inputs.
    cmap: string, default: 'Grayscale'
        The color map for the current component/channel.
    x_slice: float, default: None
        The position in world space of the X slicing plane.
    y_slice: float, default: None
        The position in world space of the Y slicing plane.
    z_slice: float, default: None
        The position in world space of the Z slicing plane.
    interpolation: bool, deafult: True
        Linear as opposed to nearest neighbor interpolation for image slices.
        Note: Interpolation is not currently supported with label maps.
    gradient_opacity: float, default: 0.5
        Gradient opacity for composite volume rendering, in the range
        (0.0, 1.0].
    gradient_opacity_scale: float, default: 0.5
        Gradient opacity scale for composite volume rendering, in the range
        (0.0, 1.0].
    gaussians: dict
        Volume rendering opacity transfer function Gaussian parameters. For
        each image component, multiple Gaussians can be specified.
        Default Gaussian parameters:
          {'position': 0.5, 'height': 1, 'width': 0.5, 'xBias': 0.51, 'yBias': 0.4}
    blend_mode: string, default: 'Composite'
        Volume rendering blend mode. Supported modes: 'Composite', 'Maximum',
        'Minimum', 'Average'.
    component_visible: bool, default: True
        The given image intensity component index's visibility.
    shadow_enabled: bool, default: True
        Whether to used gradient-based shadows in the volume rendering.
    view_mode: 'XPlane', 'YPlane', 'ZPlane', or 'Volume', default: 'Volume'
        Only relevant for 3D scenes.
        Viewing mode:
            'XPlane': x-plane
            'YPlane': y-plane
            'ZPlane': z-plane
            'Volume': volume rendering
    layer: string
        Select the layer identified by `name` in the user interface.
    layer_visible: bool, deafult: True
        Whether the current layer is visible.

    Point Sets
    ^^^^^^^^^^
    point_sets: point set
        The point sets to visualize.

    Other Parameters
    ----------------
    sample_distance: float, default: 0.2
        Sampling distance for volume rendering, normalized from 0.0 to 1.0.
        Lower values result in a higher quality rendering. High values improve
        the framerate.
    units: string, default: ''
        Units to display in the scale bar.

    Returns
    -------
    viewer : ipywidget
        Display by placing at the end of a Jupyter or Colab cell. Query or set
        properties on the object to change the visualization.
    """
    viewer = Viewer(data=data, **kwargs)

    return viewer
