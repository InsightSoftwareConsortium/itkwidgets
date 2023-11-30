import asyncio
import functools
import queue
import threading
from imjoy_rpc import api
from typing import List, Union, Tuple
from IPython.display import display, HTML
from IPython.lib import backgroundjobs as bg
import uuid

from ._type_aliases import Gaussians, Style, Image, PointSet
from ._initialization_params import (
    init_params_dict,
    build_config,
    parse_input_data,
    build_init_data,
)
from ._method_types import deferred_methods
from .cell_watcher import CellWatcher
from .imjoy import register_itkwasm_imjoy_codecs
from .integrations import _detect_render_type, _get_viewer_image, _get_viewer_point_set
from .integrations.environment import ENVIRONMENT, Env
from .render_types import RenderType
from .viewer_config import ITK_VIEWER_SRC
from imjoy_rpc import register_default_codecs

__all__ = [
    "Viewer",
    "view",
]

_viewer_count = 1
_codecs_registered = False
CellWatcher() # Instantiate the singleton class right away


class ViewerRPC:
    """Viewer remote procedure interface."""

    def __init__(
        self, ui_collapsed=True, rotate=False, ui="pydata-sphinx", init_data=None, parent=None, **add_data_kwargs
    ):
        global _codecs_registered
        """Create a viewer."""
        # Register codecs if they haven't been already
        if not _codecs_registered and ENVIRONMENT is not Env.HYPHA:
            register_default_codecs()
            register_itkwasm_imjoy_codecs()
            _codecs_registered = True

        self._init_viewer_kwargs = dict(ui_collapsed=ui_collapsed, rotate=rotate, ui=ui)
        self._init_viewer_kwargs.update(**add_data_kwargs)
        self.init_data = init_data
        self.img = display(HTML(f'<div />'), display_id=str(uuid.uuid4()))
        self.wid = None
        self.parent = parent
        if ENVIRONMENT is not Env.JUPYTERLITE and ENVIRONMENT is not Env.HYPHA:
            self.viewer_event = threading.Event()
            self.data_event = threading.Event()

    async def setup(self):
        pass

    async def run(self, ctx):
        """ImJoy plugin setup function."""
        global _viewer_count
        ui = self._init_viewer_kwargs.get("ui", None)
        config = build_config(ui)

        if ENVIRONMENT is not Env.HYPHA:
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
            if ENVIRONMENT is not Env.JUPYTERLITE:
                itk_viewer.registerEventListener(
                    'screenshotTaken', self.update_screenshot
                )
                # Once the viewer has been created any queued requests can be run
                CellWatcher().update_viewer_status(self.parent)
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
        self.name = self.__str__()
        input_data = parse_input_data(add_data_kwargs)
        data = build_init_data(input_data)
        if ENVIRONMENT is not Env.HYPHA:
            self.viewer_rpc = ViewerRPC(
                ui_collapsed=ui_collapsed, rotate=rotate, ui=ui, init_data=data, **add_data_kwargs
            )
            self.cw = CellWatcher()
            if ENVIRONMENT is not Env.JUPYTERLITE:
                self._setup_queueing()
            api.export(self.viewer_rpc)
        else:
            self._itk_viewer = add_data_kwargs.get('itk_viewer', None)
            self.server = add_data_kwargs.get('server', None)
            self.workspace = self.server.config.workspace

    def _setup_queueing(self):
        self.bg_jobs = bg.BackgroundJobManager()
        self.queue = queue.Queue()
        self.deferred_queue = queue.Queue()
        self.bg_thread = self.bg_jobs.new(self.queue_worker)

    @property
    def loop(self):
        return asyncio.get_running_loop()

    @property
    def has_viewer(self):
        if hasattr(self, "viewer_rpc"):
            return hasattr(self.viewer_rpc, "itk_viewer")
        return self.itk_viewer

    @property
    def itk_viewer(self):
        if hasattr(self, "viewer_rpc"):
            return self.viewer_rpc.itk_viewer
        return self._itk_viewer

    async def run_queued_requests(self):
        def _run_queued_requests(queue):
            method_name, args, kwargs = queue.get()
            fn = getattr(self.itk_viewer, method_name)
            self.loop.call_soon_threadsafe(asyncio.ensure_future, fn(*args, **kwargs))

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

    def call_getter(self, future):
        name = uuid.uuid4()
        CellWatcher().results[name] = future
        future.add_done_callback(functools.partial(CellWatcher()._callback, name))

    def queue_request(self, method, *args, **kwargs):
        if (
            ENVIRONMENT is Env.JUPYTERLITE or ENVIRONMENT is Env.HYPHA
        ) or self.has_viewer:
            fn = getattr(self.itk_viewer, method)
            fn(*args, **kwargs)
        elif method in deferred_methods():
            self.deferred_queue.put((method, args, kwargs))
        else:
            self.queue.put((method, args, kwargs))

    def fetch_value(func):
        @functools.wraps(func)
        def _fetch_value(self, *args, **kwargs):
            future = func(self, *args, **kwargs)
            self.call_getter(future)
            return future
        return _fetch_value

    @fetch_value
    def set_annotations_enabled(self, enabled: bool):
        return self.viewer_rpc.itk_viewer.setAnnotationsEnabled(enabled)
    @fetch_value
    def get_annotations_enabled(self):
        return self.viewer_rpc.itk_viewer.getAnnotationsEnabled()

    @fetch_value
    def set_axes_enabled(self, enabled: bool):
        return self.viewer_rpc.itk_viewer.setAxesEnabled(enabled)
    @fetch_value
    def get_axes_enabled(self):
        return self.viewer_rpc.itk_viewer.getAxesEnabled()

    @fetch_value
    def set_background_color(self, bgColor: List[float]):
        return self.viewer_rpc.itk_viewer.setBackgroundColor(bgColor)
    @fetch_value
    def get_background_color(self):
        return self.viewer_rpc.itk_viewer.getBackgroundColor()

    @fetch_value
    def set_image(self, image: Image, name: str = 'Image'):
        render_type = _detect_render_type(image, 'image')
        if render_type is RenderType.IMAGE:
            image = _get_viewer_image(image, label=False)
            if ENVIRONMENT is Env.HYPHA:
                self.image = image
                svc_name = f'{self.workspace}/itkwidgets-server:data-set'
                svc = self.server.get_service(svc_name)
                svc.set_label_or_image('image')
            else:
                return self.viewer_rpc.itk_viewer.setImage(image, name)
        elif render_type is RenderType.POINT_SET:
            image = _get_viewer_point_set(image)
            return self.viewer_rpc.itk_viewer.setPointSets(image)
    @fetch_value
    def get_image(self):
        return self.viewer_rpc.itk_viewer.getImage()

    @fetch_value
    def set_image_blend_mode(self, mode: str):
        return self.viewer_rpc.itk_viewer.setImageBlendMode(mode)
    @fetch_value
    def get_image_blend_mode(self):
        return self.viewer_rpc.itk_viewer.getImageBlendMode()

    @fetch_value
    def set_image_color_map(self, colorMap: str):
        return self.viewer_rpc.itk_viewer.setImageColorMap(colorMap)
    @fetch_value
    def get_image_color_map(self):
        return self.viewer_rpc.itk_viewer.getImageColorMap()

    @fetch_value
    def set_image_color_range(self, range: List[float]):
        return self.viewer_rpc.itk_viewer.setImageColorRange(range)
    @fetch_value
    def get_image_color_range(self):
        return self.viewer_rpc.itk_viewer.getImageColorRange()

    @fetch_value
    def set_image_color_range_bounds(self, range: List[float]):
        return self.viewer_rpc.itk_viewer.setImageColorRangeBounds(range)
    @fetch_value
    def get_image_color_range_bounds(self):
        return self.viewer_rpc.itk_viewer.getImageColorRangeBounds()

    @fetch_value
    def set_image_component_visibility(self, visibility: bool):
        return self.viewer_rpc.itk_viewer.setImageComponentVisibility(visibility)
    @fetch_value
    def get_image_component_visibility(self, component: int):
        return self.viewer_rpc.itk_viewer.getImageComponentVisibility(component)

    @fetch_value
    def set_image_gradient_opacity(self, opacity: float):
        return self.viewer_rpc.itk_viewer.setImageGradientOpacity(opacity)
    @fetch_value
    def get_image_gradient_opacity(self):
        return self.viewer_rpc.itk_viewer.getImageGradientOpacity()

    @fetch_value
    def set_image_gradient_opacity_scale(self, min: float):
        return self.viewer_rpc.itk_viewer.setImageGradientOpacityScale(min)
    @fetch_value
    def get_image_gradient_opacity_scale(self):
        return self.viewer_rpc.itk_viewer.getImageGradientOpacityScale()

    @fetch_value
    def set_image_interpolation_enabled(self, enabled: bool):
        return self.viewer_rpc.itk_viewer.setImageInterpolationEnabled(enabled)
    @fetch_value
    def get_image_interpolation_enabled(self):
        return self.viewer_rpc.itk_viewer.getImageInterpolationEnabled()

    @fetch_value
    def set_image_piecewise_function_gaussians(self, gaussians: Gaussians):
        return self.viewer_rpc.itk_viewer.setImagePiecewiseFunctionGaussians(gaussians)
    @fetch_value
    def get_image_piecewise_function_gaussians(self):
        return self.viewer_rpc.itk_viewer.getImagePiecewiseFunctionGaussians()

    @fetch_value
    def set_image_shadow_enabled(self, enabled: bool):
        return self.viewer_rpc.itk_viewer.setImageShadowEnabled(enabled)
    @fetch_value
    def get_image_shadow_enabled(self):
        return self.viewer_rpc.itk_viewer.getImageShadowEnabled()

    @fetch_value
    def set_image_volume_sample_distance(self, distance: float):
        return self.viewer_rpc.itk_viewer.setImageVolumeSampleDistance(distance)
    @fetch_value
    def get_image_volume_sample_distance(self):
        return self.viewer_rpc.itk_viewer.getImageVolumeSampleDistance()

    @fetch_value
    def set_image_volume_scattering_blend(self, scattering_blend: float):
        return self.viewer_rpc.itk_viewer.setImageVolumeScatteringBlend(scattering_blend)
    @fetch_value
    def get_image_volume_scattering_blend(self):
        return self.viewer_rpc.itk_viewer.getImageVolumeScatteringBlend()

    def compare_images(self, fixed_image: Union[str, Image], moving_image: Union[str, Image], method: str = None, image_mix: float = None, checkerboard: bool = None, pattern: Union[Tuple[int, int], Tuple[int, int, int]] = None, swap_image_order: bool = None):
        # image args may be image name or image object
        fixed_name = 'Fixed'
        if isinstance(fixed_image, str): 
            fixed_name = fixed_image
        else:
            self.set_image(fixed_image, fixed_name)
        moving_name = 'Moving'
        if isinstance(moving_image, str): 
            moving_name = moving_image
        else:
            self.set_image(moving_image, moving_name)
        options = {}
        # if None let viewer use defaults or last value.
        if method is not None:
            options['method'] = method
        if image_mix is not None:
            options['imageMix'] = image_mix
        if checkerboard is not None:
            options['checkerboard'] = checkerboard
        if pattern is not None:
            options['pattern'] = pattern
        if swap_image_order is not None:
            options['swapImageOrder'] = swap_image_order
        return self.viewer_rpc.itk_viewer.compareImages(fixed_name, moving_name, options)

    @fetch_value
    def set_label_image(self, label_image: Image):
        render_type = _detect_render_type(label_image, 'image')
        if render_type is RenderType.IMAGE:
            label_image = _get_viewer_image(label_image, label=True)
            if ENVIRONMENT is Env.HYPHA:
                self.label_image = label_image
                svc_name = f"{self.workspace}/itkwidgets-server:data-set"
                svc = self.server.get_service(svc_name)
                svc.set_label_or_image('label_image')
            else:
                return self.viewer_rpc.itk_viewer.setLabelImage(label_image)
        elif render_type is RenderType.POINT_SET:
            label_image = _get_viewer_point_set(label_image)
            return self.viewer_rpc.itk_viewer.setPointSets(label_image)
    @fetch_value
    def get_label_image(self):
        return self.viewer_rpc.itk_viewer.getLabelImage()

    @fetch_value
    def set_label_image_blend(self, blend: float):
        return self.viewer_rpc.itk_viewer.setLabelImageBlend(blend)
    @fetch_value
    def get_label_image_blend(self):
        return self.viewer_rpc.itk_viewer.getLabelImageBlend()

    @fetch_value
    def set_label_image_label_names(self, names: List[str]):
        return self.viewer_rpc.itk_viewer.setLabelImageLabelNames(names)
    @fetch_value
    def get_label_image_label_names(self):
        return self.viewer_rpc.itk_viewer.getLabelImageLabelNames()

    @fetch_value
    def set_label_image_lookup_table(self, lookupTable: str):
        return self.viewer_rpc.itk_viewer.setLabelImageLookupTable(lookupTable)
    @fetch_value
    def get_label_image_lookup_table(self):
        return self.viewer_rpc.itk_viewer.getLabelImageLookupTable()

    @fetch_value
    def set_label_image_weights(self, weights: float):
        return self.viewer_rpc.itk_viewer.setLabelImageWeights(weights)
    @fetch_value
    def get_label_image_weights(self):
        return self.viewer_rpc.itk_viewer.getLabelImageWeights()

    @fetch_value
    def select_layer(self, name: str):
        return self.viewer_rpc.itk_viewer.selectLayer(name)
    @fetch_value
    def get_layer_names(self):
        return self.viewer_rpc.itk_viewer.getLayerNames()

    @fetch_value
    def set_layer_visibility(self, visible: bool):
        return self.viewer_rpc.itk_viewer.setLayerVisibility(visible)
    @fetch_value
    def get_layer_visibility(self, name: str):
        return self.viewer_rpc.itk_viewer.getLayerVisibility(name)

    @fetch_value
    def add_point_set(self, pointSet: PointSet):
        pointSet = _get_viewer_point_set(pointSet)
        return self.viewer_rpc.itk_viewer.addPointSet(pointSet)
    @fetch_value
    def set_point_set(self, pointSet: PointSet):
        pointSet = _get_viewer_point_set(pointSet)
        return self.viewer_rpc.itk_viewer.setPointSets(pointSet)

    @fetch_value
    def set_rendering_view_container_style(self, containerStyle: Style):
        return self.viewer_rpc.itk_viewer.setRenderingViewContainerStyle(containerStyle)
    @fetch_value
    def get_rendering_view_container_style(self):
        return self.viewer_rpc.itk_viewer.getRenderingViewStyle()

    @fetch_value
    def set_rotate(self, enabled: bool):
        return self.viewer_rpc.itk_viewer.setRotateEnabled(enabled)
    @fetch_value
    def get_rotate(self):
        return self.viewer_rpc.itk_viewer.getRotateEnabled()

    @fetch_value
    def set_ui_collapsed(self, collapsed: bool):
        return self.viewer_rpc.itk_viewer.setUICollapsed(collapsed)
    @fetch_value
    def get_ui_collapsed(self):
        return self.viewer_rpc.itk_viewer.getUICollapsed()

    @fetch_value
    def set_units(self, units: str):
        return self.viewer_rpc.itk_viewer.setUnits(units)
    @fetch_value
    def get_units(self):
        return self.viewer_rpc.itk_viewer.getUnits()

    @fetch_value
    def set_view_mode(self, mode: str):
        return self.viewer_rpc.itk_viewer.setViewMode(mode)
    @fetch_value
    def get_view_mode(self):
        return self.viewer_rpc.itk_viewer.getViewMode()

    @fetch_value
    def set_x_slice(self, position: float):
        return self.viewer_rpc.itk_viewer.setXSlice(position)
    @fetch_value
    def get_x_slice(self):
        return self.viewer_rpc.itk_viewer.getXSlice()

    @fetch_value
    def set_y_slice(self, position: float):
        return self.viewer_rpc.itk_viewer.setYSlice(position)
    @fetch_value
    def get_y_slice(self):
        return self.viewer_rpc.itk_viewer.getYSlice()

    @fetch_value
    def set_z_slice(self, position: float):
        return self.viewer_rpc.itk_viewer.setZSlice(position)
    @fetch_value
    def get_z_slice(self):
        return self.viewer_rpc.itk_viewer.getZSlice()


def view(data=None, **kwargs):
    """View the image and/or point set.

    Creates and returns an ImJoy plugin ipywidget to visualize an image, and/or
    point set.

    The image can be 2D or 3D. The type of the image can be an numpy.array,
    itk.Image, or vtk.vtkImageData.

    A point set can be visualized. The type of the point set can be an
    numpy.array (Nx3 array of point positions).

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

    Point Set
    ^^^^^^^^^^
    point_set: point set
        The point set to visualize.

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

def compare_images(fixed_image: Union[str, Image], moving_image: Union[str, Image], method: str = None, image_mix: float = None, checkerboard: bool = None, pattern: Union[Tuple[int, int], Tuple[int, int, int]] = None, swap_image_order: bool = None):
    """Fuse 2 images with a checkerboard filter or as a 2 component image.  

    The moving image is re-sampled to the fixed image space. Set a keyword argument to None to use defaults based on method.
    
    Parameters
    ----------
    fixed_image: array_like, itk.Image, or vtk.vtkImageData
        Static image the moving image is re-sampled to. For non-checkerboard methods ('blend', 'green-magenta', etc.), the fixed image is on the first component.

    moving_image: array_like, itk.Image, or vtk.vtkImageData
        Image is re-sampled to the fixed_image. For non-checkerboard methods ('blend', 'green-magenta', etc.), the moving image is on the second component.

    method: string, default: None, possible values: 'green-magenta', 'cyan-red', 'cyan-magenta', 'blend', 'checkerboard', 'disabled'
        The checkerboard method picks pixels from the fixed and moving image to create a
        checkerboard pattern. Setting the method to checkerboard turns on the checkerboard flag. 
        The non-checkerboard methods ('blend', 'green-magenta', etc.) put the fixed image on component 0, moving image on component 1.
        The 'green-magenta' and 'red-cyan' change the color maps so matching images are grayish white.  
        The 'cyan-magenta' color maps produce a purple if the images match.  

    image_mix: float, default: None
        Changes the percent contribution the fixed vs moving image makes to the
        render by modifying the opacity transfer function. Value of 1 means max opacity for
        moving image, 0 for fixed image. If value is None and the method is not checkerboard,
        the image_mix is set to 0.5.  If the method is "checkerboard", the image_mix is set to 0.
    
    checkerboard: bool, default: None
        Forces the checkerboard mixing of fixed and moving images for the cyan-magenta and blend methods.
        The rendered image has 2 components, each component reverses which image is sampled for each
        checkerboard box.

    pattern: Union[Tuple[int, int], Tuple[int, int, int]], default: None
        The number of checkerboard boxes for each dimension.

    swap_image_order: bool, default: None
        Reverses which image is sampled for each checkerboard box.  This simply toggles
        image_mix between 0 and 1.
    """
    viewer = view()
    viewer.compare_images(fixed_image=fixed_image, moving_image=moving_image, method=method, image_mix=image_mix, checkerboard=checkerboard, pattern=pattern, swap_image_order=swap_image_order)
    return viewer

