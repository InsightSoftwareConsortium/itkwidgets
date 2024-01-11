from __future__ import annotations

import asyncio
import functools
import queue
import threading
import numpy as np
from imjoy_rpc import api
from inspect import isawaitable
from typing import Callable, Dict, List, Union, Tuple
from IPython.display import display, HTML
from IPython.lib import backgroundjobs as bg
from ngff_zarr import from_ngff_zarr, to_ngff_image, Multiscales, NgffImage
import uuid

from ._method_types import deferred_methods
from ._type_aliases import Gaussians, Style, Image, PointSet, CroppingPlanes
from ._initialization_params import (
    init_params_dict,
    build_config,
    parse_input_data,
    build_init_data,
    defer_for_data_render,
)
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
_cell_watcher = None
if not ENVIRONMENT in (Env.HYPHA, Env.JUPYTERLITE):
    from .cell_watcher import CellWatcher
    _cell_watcher = CellWatcher() # Instantiate the singleton class right away


class ViewerRPC:
    """Viewer remote procedure interface."""

    def __init__(
        self,
        ui_collapsed: bool = True,
        rotate: bool = False,
        ui: str = "pydata-sphinx",
        init_data: dict = None,
        parent: str = None,
        **add_data_kwargs,
    ) -> None:
        global _codecs_registered, _cell_watcher
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
        if ENVIRONMENT is not Env.JUPYTERLITE:
            _cell_watcher and _cell_watcher.add_viewer(self.parent)
            if ENVIRONMENT is not Env.HYPHA:
                self.viewer_event = threading.Event()
                self.data_event = threading.Event()

    async def setup(self) -> None:
        pass

    async def run(self, ctx: dict) -> None:
        """ImJoy plugin setup function."""
        global _viewer_count, _cell_watcher
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

            self.set_default_ui_values(itk_viewer)
            self.itk_viewer = itk_viewer
            self.wid = self.itk_viewer.config.window_id

            if ENVIRONMENT is not Env.JUPYTERLITE:
                # Create the initial screenshot
                await self.create_screenshot()
                itk_viewer.registerEventListener(
                    'renderedImageAssigned', self.set_event
                )
                if not defer_for_data_render(self.init_data):
                    # Once the viewer has been created any queued requests can be run
                    _cell_watcher.update_viewer_status(self.parent, True)
                asyncio.get_running_loop().call_soon_threadsafe(self.viewer_event.set)

            # Wait and then update the screenshot in case rendered level changed
            await asyncio.sleep(10)
            await self.create_screenshot()
            # Set up an event listener so that the embedded
            # screenshot is updated when the user requests
            itk_viewer.registerEventListener('screenshotTaken', self.update_screenshot)

    def set_default_ui_values(self, itk_viewer: dict) -> None:
        """Set any UI values passed in on initialization.

        :param itk_viewer: The ImJoy plugin API to use
        :type itk_viewer:  dict
        """
        settings = init_params_dict(itk_viewer)
        for key, value in self._init_viewer_kwargs.items():
            if key in settings.keys():
                settings[key](value)

    async def create_screenshot(self) -> None:
        """Grab a screenshot of the current Viewer and embed it in the
        notebook cell.
        """
        base64_image = await self.itk_viewer.captureImage()
        self.update_screenshot(base64_image)

    def update_screenshot(self, base64_image: str) -> None:
        """Embed an image in the current notebook cell.

        :param base64_image: An encoded image to be embedded
        :type base64_image:  bstring
        """
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

    def update_viewer_status(self):
        """Update the CellWatcher class to indicate that the Viewer is ready"""
        global _cell_watcher
        if not _cell_watcher.viewer_ready(self.parent):
            _cell_watcher.update_viewer_status(self.parent, True)

    def set_event(self, event_data: str) -> None:
        """Set the event in the background thread to indicate that the plugin
        API is available so that queued setter requests are processed.

        :param event_data: The name of the image that has been rendered
        :type event_data:  string
        """
        if not self.data_event.is_set():
            # Once the data has been set the deferred queue requests can be run
            asyncio.get_running_loop().call_soon_threadsafe(self.data_event.set)
        if ENVIRONMENT is not Env.HYPHA:
            self.update_viewer_status()


class Viewer:
    """Pythonic Viewer class."""

    def __init__(
        self,
        ui_collapsed: bool = True,
        rotate: bool = False,
        ui: bool = "pydata-sphinx",
        **add_data_kwargs,
    ) -> None:
        """Create a viewer."""
        self.stores = {}
        self.name = self.__str__()
        input_data = parse_input_data(add_data_kwargs)
        data = build_init_data(input_data, self.stores)
        if compare := input_data.get('compare'):
            data['compare'] = compare
        if ENVIRONMENT is not Env.HYPHA:
            self.viewer_rpc = ViewerRPC(
                ui_collapsed=ui_collapsed, rotate=rotate, ui=ui, init_data=data, parent=self.name, **add_data_kwargs
            )
            if ENVIRONMENT is not Env.JUPYTERLITE:
                self._setup_queueing()
            api.export(self.viewer_rpc)
        else:
            self._itk_viewer = add_data_kwargs.get('itk_viewer', None)
            self.server = add_data_kwargs.get('server', None)
            self.workspace = self.server.config.workspace

    def _setup_queueing(self) -> None:
        """Create a background thread and two queues of requests: one will hold
        requests that can be run as soon as the plugin API is available, the
        deferred queue will hold requests that need the data to be rendered
        before they are applied. Background requests will not return any
        results.
        """
        self.bg_jobs = bg.BackgroundJobManager()
        self.queue = queue.Queue()
        self.deferred_queue = queue.Queue()
        self.bg_thread = self.bg_jobs.new(self.queue_worker)

    @property
    def loop(self) -> asyncio.BaseEventLoop:
        """Return the running event loop in the current OS thread.

        :return: Current running event loop
        :rtype:  asyncio.BaseEventLoop
        """
        return asyncio.get_running_loop()

    @property
    def has_viewer(self) -> bool:
        """Whether or not the plugin API is available to call.

        :return: Availability of API
        :rtype:  bool
        """
        if hasattr(self, "viewer_rpc"):
            return hasattr(self.viewer_rpc, "itk_viewer")
        return self.itk_viewer is not None

    @property
    def itk_viewer(self) -> dict | None:
        """Return the plugin API if it is available.

        :return: The plugin API if available, else None
        :rtype:  dict | None
        """
        if hasattr(self, "viewer_rpc"):
            return self.viewer_rpc.itk_viewer
        return self._itk_viewer

    async def run_queued_requests(self) -> None:
        """Once the plugin API is available and the viewer_event is set, run
        all requests queued for the background thread that do not require the
        data to be available.
        Once the data has been rendered process any deferred requests.
        """
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

    def queue_worker(self) -> None:
        """Create a new event loop in the background thread and run until all
        queued tasks are complete.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self.run_queued_requests())
        loop.run_until_complete(task)

    def call_getter(self, future: asyncio.Future) -> None:
        """Create a future for requests that expect a response and set the
        callback to update the CellWatcher once resolved.

        :param future: A future for the awaitable request that we are waiting
        to resolve.
        :type future:  asyncio.Future
        """
        global _cell_watcher
        name = uuid.uuid4()
        _cell_watcher.results[name] = future
        future.add_done_callback(functools.partial(_cell_watcher._callback, name))

    def queue_request(self, method: Callable, *args, **kwargs) -> None:
        """Determine if a request should be run immeditately, queued to run
        once the plugin API is avaialable, or queued to run once the data has
        been rendered.

        :param method:  Function to either call or queue
        :type method:   Callable
        """
        if (
            ENVIRONMENT is Env.JUPYTERLITE or ENVIRONMENT is Env.HYPHA
        ) or self.has_viewer:
            fn = getattr(self.itk_viewer, method)
            fn(*args, **kwargs)
        elif method in deferred_methods():
            self.deferred_queue.put((method, args, kwargs))
        else:
            self.queue.put((method, args, kwargs))

    def fetch_value(func: Callable) -> Callable:
        """Decorator function that wraps the decorated function and returns the
        wrapper. In this case we decorate our API wrapper functions in order to
        determine if it needs to be managed by the CellWatcher class.

        :param func: Plugin API wrapper
        :type func:  Callable
        :return: wrapper function
        :rtype:  Callable
        """
        @functools.wraps(func)
        def _fetch_value(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            global _cell_watcher
            if isawaitable(result) and _cell_watcher:
                future = asyncio.ensure_future(result)
                self.call_getter(future)
                return future
            return result
        return _fetch_value

    @fetch_value
    def set_annotations_enabled(self, enabled: bool) -> None:
        """Set whether or not the annotations should be displayed. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param enabled: Should annotations be enabled
        :type enabled:  bool
        """
        self.queue_request('setAnnotationsEnabled', enabled)
    @fetch_value
    async def get_annotations_enabled(self) -> asyncio.Future | bool:
        """Determine if annotations are enabled.

        :return: The future for the coroutine, to be updated with the
        annotations visibility status.
        :rtype:  asyncio.Future | bool
        """
        return await self.viewer_rpc.itk_viewer.getAnnotationsEnabled()

    @fetch_value
    def set_axes_enabled(self, enabled: bool) -> None:
        """Set whether or not the axes should be displayed. Queue the function
        to be run in the background thread once the plugin API is available.

        :param enabled: If axes should be enabled
        :type enabled:  bool
        """
        self.queue_request('setAxesEnabled', enabled)
    @fetch_value
    async def get_axes_enabled(self) -> asyncio.Future | bool:
        """Determine if the axes are enabled.

        :return: The future for the coroutine, to be updated with the axes
        visibility status.
        :rtype:  asyncio.Future | bool
        """
        return await self.viewer_rpc.itk_viewer.getAxesEnabled()

    @fetch_value
    def set_background_color(self, bg_color: List[float]) -> None:
        """Set the background color for the viewer. Queue the function to be
        run in the background thread once the plugin API is available.

        :param bg_color: A list of floats [r, g, b, a]
        :type bg_color:  List[float]
        """
        self.queue_request('setBackgroundColor', bg_color)
    @fetch_value
    async def get_background_color(self) -> asyncio.Future | List[float]:
        """Get the current background color.

        :return: The future for the coroutine, to be updated with a list of
        floats representing the current color [r, g, b, a].
        :rtype:  asyncio.Future | List[float]
        """
        return await self.viewer_rpc.itk_viewer.getBackgroundColor()

    @fetch_value
    def set_cropping_planes(self, cropping_planes: CroppingPlanes) -> None:
        """Set the origins and normals for the current cropping planes. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param cropping_planes: A list of 6 dicts representing the 6 cropping
        planes. Each dict should contain an 'origin' key with the origin with a
        list of three floats and a 'normal' key with a list of three ints.
        :type cropping_planes:  CroppingPlanes
        """
        self.queue_request('setCroppingPlanes', cropping_planes)
    @fetch_value
    async def get_cropping_planes(self) -> asyncio.Future | CroppingPlanes:
        """Get the origins and normals for the current cropping planes.

        :return: The future for the coroutine, to be updated with a list of 6
        dicts representing the 6 cropping planes. Each dict should contain an
        'origin' key with the origin with a list of three floats and a 'normal'
        key with a list of three ints.
        :rtype:  asyncio.Future | CroppingPlanes
        """
        return await self.viewer_rpc.itk_viewer.getCroppingPlanes()

    @fetch_value
    def set_image(self, image: Image, name: str = 'Image') -> None:
        """Set the image to be rendered. Queue the function to be run in the
        background thread once the plugin API is available.

        :param image: Image data to render
        :type image:  Image
        :param name: Image name, defaults to 'Image'
        :type name:  str, optional
        """
        global _cell_watcher
        render_type = _detect_render_type(image, 'image')
        if render_type is RenderType.IMAGE:
            image = _get_viewer_image(image, label=False)
            # Keep a reference to stores that we create
            self.stores[name] = image
            if ENVIRONMENT is Env.HYPHA:
                self.image = image
                svc_name = f'{self.workspace}/itkwidgets-server:data-set'
                svc = self.server.get_service(svc_name)
                svc.set_label_or_image('image')
            else:
                self.queue_request('setImage', image, name)
                # Make sure future getters are deferred until render
                _cell_watcher and _cell_watcher.update_viewer_status(self.name, False)
        elif render_type is RenderType.POINT_SET:
            image = _get_viewer_point_set(image)
            self.queue_request('setPointSets', image)
    @fetch_value
    async def get_image(self, name: str = 'Image') -> NgffImage:
        """Get the full, highest resolution image.

        :param name: Name of the loaded image data to use. 'Image', the
        default, selects the first loaded image.
        :type name:  str

        :return: image
        :rtype:  NgffImage
        """
        if store := self.stores.get(name):
            multiscales = from_ngff_zarr(store)
            loaded_image = multiscales.images[0]
            roi_data = loaded_image.data
            return to_ngff_image(
                roi_data,
                dims=loaded_image.dims,
                scale=loaded_image.scale,
                name=name,
                axes_units=loaded_image.axes_units
            )
        raise ValueError(f'No image data found for {name}.')

    @fetch_value
    def set_image_blend_mode(self, mode: str) -> None:
        """Set the volume rendering blend mode. Queue the function to be run in
        the background thread once the plugin API is available.

        :param mode: Volume blend mode. Supported modes: 'Composite',
        'Maximum', 'Minimum', 'Average'. default: 'Composite'.
        :type mode:  str
        """
        self.queue_request('setImageBlendMode', mode)
    @fetch_value
    async def get_image_blend_mode(self) -> asyncio.Future | str:
        """Get the current volume rendering blend mode.

        :return: The future for the coroutine, to be updated with the current
        blend mode.
        :rtype:  asyncio.Future | str
        """
        return await self.viewer_rpc.itk_viewer.getImageBlendMode()

    @property
    @fetch_value
    async def color_map(self) -> asyncio.Future | str:
        """Get the color map for the current component/channel.

        :return: The future for the coroutine, to be updated with the current
        color map.
        :rtype:  asyncio.Future | str
        """
        return await self.viewer_rpc.itk_viewer.getImageColorMap()
    @color_map.setter
    @fetch_value
    async def color_map(self, color_map: str) -> None:
        """Set the color map for the current component/channel. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param color_map: Color map for the current image. default: 'Grayscale'
        :type color_map:  str
        """
        self.queue_request('setImageColorMap', color_map)

    @fetch_value
    def set_image_color_map(self, color_map: str) -> None:
        """Set the color map for the current component/channel. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param color_map: Color map for the current image. default: 'Grayscale'
        :type color_map:  str
        """
        self.queue_request('setImageColorMap', color_map)
    @fetch_value
    async def get_image_color_map(self) -> asyncio.Future | str:
        """Get the color map for the current component/channel.

        :return: The future for the coroutine, to be updated with the current
        color map.
        :rtype:  asyncio.Future | str
        """
        return await self.viewer_rpc.itk_viewer.getImageColorMap()

    @property
    @fetch_value
    async def color_range(self) -> asyncio.Future | List[float]:
        """Get the range of the data values mapped to colors for the given
        image.

        :return: _description_
        :rtype:  asyncio.Future | List[float]
        """
        return await self.viewer_rpc.itk_viewer.getImageColorRange()
    @color_range.setter
    @fetch_value
    async def color_range(self, range: List[float]) -> None:
        """The range of the data values mapped to colors for the given image.
        Queue the function to be run in the background thread once the plugin
        API is available.

        :param range: The [min, max] range of the data values
        :type range:  List[float]
        """
        self.queue_request('setImageColorRange', range)

    @fetch_value
    def set_image_color_range(self, range: List[float]) -> None:
        """The range of the data values mapped to colors for the given image.
        Queue the function to be run in the background thread once the plugin
        API is available.

        :param range: The [min, max] range of the data values
        :type range:  List[float]
        """
        self.queue_request('setImageColorRange', range)
    @fetch_value
    async def get_image_color_range(self) -> asyncio.Future | List[float]:
        """Get the range of the data values mapped to colors for the given
        image.

        :return: The future for the coroutine, to be updated with the
        [min, max] range of the data values.
        :rtype:  asyncio.Future | List[float]
        """
        return await self.viewer_rpc.itk_viewer.getImageColorRange()

    @property
    @fetch_value
    async def vmin(self) -> asyncio.Future | float:
        """Get the minimum data value mapped to colors for the current image.

        :return: The future for the coroutine, to be updated with the minimum
        value mapped to the color map.
        :rtype:  asyncio.Future | float
        """
        range = await self.get_image_color_range()
        return range[0]
    @vmin.setter
    @fetch_value
    async def vmin(self, vmin: float) -> None:
        """Set the minimum data value mapped to colors for the current image.
        Queue the function to be run in the background thread once the plugin
        API is available.

        :param vmin: The minimum value mapped to the color map.
        :type vmin:  float
        """
        self.queue_request('setImageColorRangeMin', vmin)

    @property
    @fetch_value
    async def vmax(self) -> asyncio.Future | float:
        """Get the maximum data value mapped to colors for the current image.

        :return: The future for the coroutine, to be updated with the maximum
        value mapped to the color map.
        :rtype:  asyncio.Future | float
        """
        range = await self.get_image_color_range()
        return range[1]
    @vmax.setter
    @fetch_value
    async def vmax(self, vmax: float) -> None:
        """Set the maximum data value mapped to colors for the current image.
        Queue the function to be run in the background thread once the plugin
        API is available.

        :param vmax: The maximum value mapped to the color map.
        :type vmax:  float
        """
        self.queue_request('setImageColorRangeMax', vmax)

    @property
    @fetch_value
    async def color_bounds(self) -> asyncio.Future | List[float]:
        """Get the range of the data values for color maps.

        :return: The future for the coroutine, to be updated with the
        [min, max] range of the data values.
        :rtype:  asyncio.Future | List[float]
        """
        return await self.viewer_rpc.itk_viewer.getImageColorRangeBounds()
    @color_bounds.setter
    @fetch_value
    async def color_bounds(self, range: List[float]) -> None:
        """Set the range of the data values for color maps. Queue the function
        to be run in the background thread once the plugin API is available.

        :param range: The [min, max] range of the data values.
        :type range:  List[float]
        """
        self.queue_request('setImageColorRangeBounds', range)

    @fetch_value
    def set_image_color_range_bounds(self, range: List[float]) -> None:
        """Set the range of the data values for color maps. Queue the function
        to be run in the background thread once the plugin API is available.

        :param range: The [min, max] range of the data values.
        :type range:  List[float]
        """
        self.queue_request('setImageColorRangeBounds', range)
    @fetch_value
    async def get_image_color_range_bounds(self) -> asyncio.Future | List[float]:
        """Get the range of the data values for color maps.

        :return: The future for the coroutine, to be updated with the
        [min, max] range of the data values.
        :rtype:  asyncio.Future | List[float]
        """
        return await self.viewer_rpc.itk_viewer.getImageColorRangeBounds()

    @fetch_value
    def set_image_component_visibility(self, visibility: bool, component: int) -> None:
        """Set the given image intensity component index's visibility. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param visibility: Whether or not the component should be visible.
        :type visibility:  bool
        :param component: The component to set the visibility for.
        :type component:  int
        """
        self.queue_request('setImageComponentVisibility', visibility, component)
    @fetch_value
    async def get_image_component_visibility(
        self, component: int
    ) -> asyncio.Future | int:
        """Get the given image intensity component index's visibility.

        :param component: The component to set the visibility for.
        :type component:  int
        :return: The future for the coroutine, to be updated with the
        component's visibility.
        :rtype:  asyncio.Future | int
        """
        return await self.viewer_rpc.itk_viewer.getImageComponentVisibility(component)

    @property
    @fetch_value
    async def gradient_opacity(self) -> asyncio.Future | float:
        """Get the gradient opacity for composite volume rendering.

        :return: The future for the coroutine, to be updated with the gradient
        opacity.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacity()
    @gradient_opacity.setter
    @fetch_value
    async def gradient_opacity(self, opacity: float) -> None:
        """Set the gradient opacity for composite volume rendering. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param opacity: Gradient opacity in the range (0.0, 1.0]. default: 0.5
        :type opacity:  float
        """
        self.queue_request('setImageGradientOpacity', opacity)

    @fetch_value
    def set_image_gradient_opacity(self, opacity: float) -> None:
        """Set the gradient opacity for composite volume rendering. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param opacity: Gradient opacity in the range (0.0, 1.0]. default: 0.5
        :type opacity:  float
        """
        self.queue_request('setImageGradientOpacity', opacity)
    @fetch_value
    async def get_image_gradient_opacity(self) -> asyncio.Future | float:
        """Get the gradient opacity for composite volume rendering.

        :return: The future for the coroutine, to be updated with the gradient
        opacity.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacity()

    @property
    @fetch_value
    async def gradient_opacity_scale(self) -> asyncio.Future | float:
        """Get the gradient opacity scale for composite volume rendering.

        :return: The future for the coroutine, to be updated with the current
        gradient opacity scale.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacityScale()
    @gradient_opacity_scale.setter
    @fetch_value
    async def gradient_opacity_scale(self, min: float) -> None:
        """Set the gradient opacity scale for composite volume rendering. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param min: Gradient opacity scale in the range (0.0, 1.0] default: 0.5
        :type min:  float
        """
        self.queue_request('setImageGradientOpacityScale', min)

    @fetch_value
    def set_image_gradient_opacity_scale(self, min: float) -> None:
        """Set the gradient opacity scale for composite volume rendering. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param min: Gradient opacity scale in the range (0.0, 1.0] default: 0.5
        :type min:  float
        """
        self.queue_request('setImageGradientOpacityScale', min)
    @fetch_value
    async def get_image_gradient_opacity_scale(self) -> asyncio.Future | float:
        """Get the gradient opacity scale for composite volume rendering.

        :return: The future for the coroutine, to be updated with the current
        gradient opacity scale.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacityScale()

    @fetch_value
    def set_image_interpolation_enabled(self, enabled: bool) -> None:
        """Set whether to use linear as opposed to nearest neighbor
        interpolation for image slices. Queue the function to be run in the
        background thread once the plugin API is available.

        :param enabled: Use linear interpolation. default: True
        :type enabled:  bool
        """
        self.queue_request('setImageInterpolationEnabled', enabled)
    @fetch_value
    async def get_image_interpolation_enabled(self) -> asyncio.Future | bool:
        """Get whether to use linear as opposed to nearest neighbor
        interpolation for image slices.

        :return: The future for the coroutine, to be updated with whether
        linear interpolation is used.
        :rtype:  asyncio.Future | bool
        """
        return await self.viewer_rpc.itk_viewer.getImageInterpolationEnabled()

    @fetch_value
    def set_image_piecewise_function_gaussians(self, gaussians: Gaussians) -> None:
        """Set the volume rendering opacity transfer function Gaussian
        parameters. For each image component, multiple Gaussians can be
        specified. Queue the function to be run in the background thread once
        the plugin API is available.

        :param gaussians: Opacity transfer function Gaussian
        parameters. Default Gaussian parameters:
        {'position': 0.5, 'height': 1, 'width': 0.5, 'xBias': 0.51, 'yBias': 0.4}
        :type gaussians:  Gaussians
        """
        self.queue_request('setImagePiecewiseFunctionGaussians', gaussians)
    @fetch_value
    async def get_image_piecewise_function_gaussians(
        self,
    ) -> asyncio.Future | Gaussians:
        """Get the volume rendering opacity transfer function Gaussian
        parameters.

        :return: The future for the coroutine, to be updated with the opacity
        transfer function Gaussian parameters.
        :rtype:  asyncio.Future | Gaussians
        """
        return await self.viewer_rpc.itk_viewer.getImagePiecewiseFunctionGaussians()

    @fetch_value
    def set_image_shadow_enabled(self, enabled: bool) -> None:
        """Set whether to used gradient-based shadows in the volume rendering.
        Queue the function to be run in the background thread once the plugin
        API is available.

        :param enabled: Apply shadows. default: True
        :type enabled:  bool
        """
        self.queue_request('setImageShadowEnabled', enabled)
    @fetch_value
    async def get_image_shadow_enabled(self) -> asyncio.Future | bool:
        """Get whether gradient-based shadows are used in the volume rendering.

        :return: The future for the coroutine, to be updated with whether
        gradient-based shadows are used.
        :rtype:  asyncio.Future | bool
        """
        return await self.viewer_rpc.itk_viewer.getImageShadowEnabled()

    @fetch_value
    def set_image_volume_sample_distance(self, distance: float) -> None:
        """Set the sampling distance for volume rendering, normalized from
        0.0 to 1.0. Lower values result in a higher quality rendering. High
        values improve the framerate. Queue the function to be run in the
        background thread once the plugin API is available.

        :param distance: Sampling distance for volume rendering. default: 0.2
        :type distance:  float
        """
        self.queue_request('setImageVolumeSampleDistance', distance)
    @fetch_value
    async def get_image_volume_sample_distance(self) -> asyncio.Future | float:
        """Get the normalized sampling distance for volume rendering.

        :return: The future for the coroutine, to be updated with the
        normalized sampling distance.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getImageVolumeSampleDistance()

    @fetch_value
    def set_image_volume_scattering_blend(self, scattering_blend: float) -> None:
        """Set the volumetric scattering blend. Queue the function to be run in
        the background thread once the plugin API is available.

        :param scattering_blend: Volumetric scattering blend in the range [0, 1]
        :type scattering_blend:  float
        """
        self.queue_request('setImageVolumeScatteringBlend', scattering_blend)
    @fetch_value
    async def get_image_volume_scattering_blend(self) -> asyncio.Future | float:
        """Get the volumetric scattering blend.

        :return: The future for the coroutine, to be updated with the current
        volumetric scattering blend.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getImageVolumeScatteringBlend()

    @fetch_value
    async def get_current_scale(self) -> asyncio.Future | int:
        """Get the current resolution scale of the primary image.

        0 is the highest resolution. Values increase for lower resolutions.

        :return: scale
        :rtype:  asyncio.Future | int
        """
        return await self.viewer_rpc.itk_viewer.getLoadedScale()

    @fetch_value
    async def get_roi_image(self, scale: int = -1, name: str = 'Image') -> NgffImage:
        """Get the image for the current ROI.

        :param scale: scale of the primary image to get the slices for the
        current roi. -1, the default, uses the current scale.
        :type scale: int
        :param name: Name of the loaded image data to use. 'Image', the
        default, selects the first loaded image.
        :type name:  str

        :return: roi_image
        :rtype:  NgffImage
        """
        if scale == -1:
            scale = await self.get_current_scale()
        roi_slices = await self.get_roi_slice(scale)
        roi_region = await self.get_roi_region()
        if store := self.stores.get(name):
            multiscales = from_ngff_zarr(store)
            loaded_image = multiscales.images[scale]
            roi_data = loaded_image.data[roi_slices]
            roi_data = roi_data.rechunk(loaded_image.data.chunksize)
            return to_ngff_image(
                roi_data,
                dims=loaded_image.dims,
                scale=loaded_image.scale,
                translation=roi_region[0],
                name=name,
                axes_units=loaded_image.axes_units
            )
        raise ValueError(f'No image data found for {name}.')

    @fetch_value
    async def get_roi_multiscale(self, name: str = 'Image') -> Multiscales:
        """Build and return a new Multiscales NgffImage for the ROI.

        :param name: Name of the loaded image data to use. 'Image', the
        default, selects the first loaded image.
        :type name:  str
                CellWatcher().update_viewer_status(self.name, False)

        :return: roi_multiscales
        :rtype:  Multiscales NgffImage
        """
        if store := self.stores.get(name):
            multiscales = from_ngff_zarr(store)
            scales = range(len(multiscales.images))
            images = [await self.get_roi_image(s) for s in scales]
            return Multiscales(
                images=images,
                metadata=multiscales.metadata,
                scale_factors=multiscales.scale_factors,
                method=multiscales.method,
                chunks=multiscales.chunks
            )
        raise ValueError(f'No image data found for {name}.')

    @fetch_value
    async def get_roi_region(self) -> asyncio.Future | List[Dict[str, float]]:
        """Get the current region of interest in world / physical space.

        Returns [lower_bounds, upper_bounds] in the form:

          [{ 'x': x0, 'y': y0, 'z': z0 }, { 'x': x1, 'y': y1, 'z': z1 }]

        :return: roi_region
        :rtype:  asyncio.Future | List[Dict[str, float]]
        """
        bounds = await self.viewer_rpc.itk_viewer.getCroppedImageWorldBounds()
        x0, x1, y0, y1, z0, z1 = bounds
        return [{ 'x': x0, 'y': y0, 'z': z0 }, { 'x': x1, 'y': y1, 'z': z1 }]

    @fetch_value
    async def get_roi_slice(self, scale: int = -1):
        """Get the current region of interest as Python slice objects for the
        current resolution of the primary image. The result is in the order:

          [z_slice, y_slice, x_slice]

        Not that for standard C-order NumPy arrays, this result can be used to
        directly extract the region of interest from the array. For example,

          roi_array = image.data[roi_slice]

        :param scale: scale of the primary image to get the slices for the
        current roi. -1, the default, uses the current scale.
        :type  scale: int

        :return: roi_slice
        :rtype:  List[slice]
        """
        if scale == -1:
            scale = await self.get_current_scale()
        idxs = await self.viewer_rpc.itk_viewer.getCroppedIndexBounds(scale)
        x0, x1 = idxs['x']
        y0, y1 = idxs['y']
        z0, z1 = idxs['z']
        return np.index_exp[int(z0):int(z1+1), int(y0):int(y1+1), int(x0):int(x1+1)]

    @fetch_value
    def compare_images(
        self,
        fixed_image: Union[str, Image],
        moving_image: Union[str, Image],
        method: str = None,
        image_mix: float = None,
        checkerboard: bool = None,
        pattern: Union[Tuple[int, int], Tuple[int, int, int]] = None,
        swap_image_order: bool = None,
    ) -> None:
        """Fuse 2 images with a checkerboard filter or as a 2 component image.
        The moving image is re-sampled to the fixed image space. Set a keyword
        argument to None to use defaults based on method. Queue the function to
        be run in the background thread once the plugin API is available.

        :param fixed_image: Static image the moving image is re-sampled to. For
        non-checkerboard methods ('blend', 'green-magenta', etc.), the fixed
        image is on the first component.
        :type  fixed_image: array_like, itk.Image, or vtk.vtkImageData
        :param moving_image: Image is re-sampled to the fixed_image. For
        non-checkerboard methods ('blend', 'green-magenta', etc.), the moving
        image is on the second component.
        :type  moving_image: array_like, itk.Image, or vtk.vtkImageData
        :param method: The checkerboard method picks pixels from the fixed and
        moving image to create a checkerboard pattern. Setting the method to
        checkerboard turns on the checkerboard flag. The non-checkerboard
        methods ('blend', 'green-magenta', etc.) put the fixed image on
        component 0, moving image on component 1. The 'green-magenta' and
        'red-cyan' change the color maps so matching images are grayish white.
        The 'cyan-magenta' color maps produce a purple if the images match.
        :type  method: string, default: None, possible values: 'green-magenta',
        'cyan-red', 'cyan-magenta', 'blend', 'checkerboard', 'disabled'
        :param image_mix: Changes the percent contribution the fixed vs moving
        image makes to the render by modifying the opacity transfer function.
        Value of 1 means max opacity for moving image, 0 for fixed image. If
        value is None and the method is not checkerboard, the image_mix is set
        to 0.5.  If the method is "checkerboard", the image_mix is set to 0.
        :type  image_mix: float, default: None
        :param checkerboard: Forces the checkerboard mixing of fixed and moving
        images for the cyan-magenta and blend methods. The rendered image has 2
        components, each component reverses which image is sampled for each
        checkerboard box.
        :type  checkerboard: bool, default: None
        :param pattern: The number of checkerboard boxes for each dimension.
        :type  pattern: tuple, default: None
        :param swap_image_order: Reverses which image is sampled for each
        checkerboard box.  This simply toggles image_mix between 0 and 1.
        :type  swap_image_order: bool, default: None
        """
        global _cell_watcher
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
        self.queue_request('compareImages', fixed_name, moving_name, options)
        _cell_watcher and _cell_watcher.update_viewer_status(self.name, False)

    @fetch_value
    def set_label_image(self, label_image: Image) -> None:
        """Set the label image to be rendered. Queue the function to be run in
        the background thread once the plugin API is available.

        :param label_image: The label map to visualize
        :type label_image:  Image
        """
        global _cell_watcher
        render_type = _detect_render_type(label_image, 'image')
        if render_type is RenderType.IMAGE:
            label_image = _get_viewer_image(label_image, label=True)
            self.stores['LabelImage'] = label_image
            if ENVIRONMENT is Env.HYPHA:
                self.label_image = label_image
                svc_name = f"{self.workspace}/itkwidgets-server:data-set"
                svc = self.server.get_service(svc_name)
                svc.set_label_or_image('label_image')
            else:
                self.queue_request('setLabelImage', label_image)
                _cell_watcher and _cell_watcher.update_viewer_status(self.name, False)
        elif render_type is RenderType.POINT_SET:
            label_image = _get_viewer_point_set(label_image)
            self.queue_request('setPointSets', label_image)
    @fetch_value
    async def get_label_image(self) -> NgffImage:
        """Get the full, highest resolution label image.

        :return: label_image
        :rtype:  NgffImage
        """
        if store := self.stores.get('LabelImage'):
            multiscales = from_ngff_zarr(store)
            loaded_image = multiscales.images[0]
            roi_data = loaded_image.data
            return to_ngff_image(
                roi_data,
                dims=loaded_image.dims,
                scale=loaded_image.scale,
                name='LabelImage',
                axes_units=loaded_image.axes_units
            )
        raise ValueError(f'No label image data found.')

    @fetch_value
    def set_label_image_blend(self, blend: float) -> None:
        """Set the label map blend with intensity image. Queue the function to
        be run in the background thread once the plugin API is available.

        :param blend: Blend with intensity image, from 0.0 to 1.0. default: 0.5
        :type blend:  float
        """
        self.queue_request('setLabelImageBlend', blend)
    @fetch_value
    async def get_label_image_blend(self) -> asyncio.Future | float:
        """Get the label map blend with intensity image.

        :return: The future for the coroutine, to be updated with the blend
        with the intensity image.
        :rtype: asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getLabelImageBlend()

    @fetch_value
    def set_label_image_label_names(self, names: List[str]) -> None:
        """Set the string names associated with the integer label values. Queue
        the function to be run in the background thread once the plugin API is
        available.

        :param names: A list of names for each label map.
        :type names:  List[str]
        """
        self.queue_request('setLabelImageLabelNames', names)
    @fetch_value
    async def get_label_image_label_names(self) -> asyncio.Future | List[str]:
        """Get the string names associated with the integer label values.

        :return: The future for the coroutine, to be updated with the list of
        names for each label map.
        :rtype:  asyncio.Future | List[str]
        """
        return await self.viewer_rpc.itk_viewer.getLabelImageLabelNames()

    @fetch_value
    def set_label_image_lookup_table(self, lookup_table: str) -> None:
        """Set the lookup table for the label map. Queue the function to be run
        in the background thread once the plugin API is available.

        :param lookup_table: Label map lookup table. default: 'glasbey'
        :type lookup_table:  str
        """
        self.queue_request('setLabelImageLookupTable', lookup_table)
    @fetch_value
    async def get_label_image_lookup_table(self) -> asyncio.Future | str:
        """Get the lookup table for the label map.

        :return: The future for the coroutine, to be updated with the current
        label map lookup table.
        :rtype:  asyncio.Future | str
        """
        return await self.viewer_rpc.itk_viewer.getLabelImageLookupTable()

    @fetch_value
    def set_label_image_weights(self, weights: float) -> None:
        """Set the rendering weight assigned to current label. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param weights: Assign the current label rendering weight between
        [0.0, 1.0].
        :type weights:  float
        """
        self.queue_request('setLabelImageWeights', weights)
    @fetch_value
    async def get_label_image_weights(self) -> asyncio.Future | float:
        """Get the rendering weight assigned to current label.

        :return: The future for the coroutine, to be updated with the current
        label rendering weight.
        :rtype:  asyncio.Future | float
        """
        return await self.viewer_rpc.itk_viewer.getLabelImageWeights()

    @fetch_value
    def select_layer(self, name: str) -> None:
        """Set the layer identified by `name` as the current layer. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param name: The name of thelayer to select.
        :type name:  str
        """
        self.queue_request('selectLayer', name)
    @fetch_value
    async def get_layer_names(self) -> asyncio.Future | List[str]:
        """Get the list of all layer names.

        :return: The future for the coroutine, to be updated with the list of
        layer names.
        :rtype:  asyncio.Future | List[str]
        """
        return await self.viewer_rpc.itk_viewer.getLayerNames()

    @fetch_value
    def set_layer_visibility(self, visible: bool, name: str) -> None:
        """Set whether the layer is visible. Queue the function to be run in
        the background thread once the plugin API is available.

        :param visible: Layer visibility. default: True
        :type visible:  bool
        :param name: The name of the layer.
        :type name:  str
        """
        self.queue_request('setLayerVisibility', visible, name)
    @fetch_value
    async def get_layer_visibility(self, name: str) -> asyncio.Future | bool:
        """Get whether the layer is visible.

        :param name: The name of the layer to fetch the visibility for.
        :type name:  str
        :return: The future for the coroutine, to be updated with the layer
        visibility.
        :rtype:  asyncio.Future | bool
        """
        return await self.viewer_rpc.itk_viewer.getLayerVisibility(name)

    @fetch_value
    def get_loaded_image_names(self) -> List[str]:
        """Get the list of loaded image names.

        :return: List of loaded images.
        :rtype:  List[str]
        """
        return list(self.stores.keys())

    @fetch_value
    def add_point_set(self, point_set: PointSet) -> None:
        """Add a point set to the visualization. Queue the function to be run
        in the background thread once the plugin API is available.

        :param point_set: An array of points to visualize.
        :type point_set:  PointSet
        """
        point_set = _get_viewer_point_set(point_set)
        self.queue_request('addPointSet', point_set)
    @fetch_value
    def set_point_set(self, point_set: PointSet) -> None:
        """Set the point set to the visualization. Queue the function to be run
        in the background thread once the plugin API is available.

        :param point_set: An array of points to visualize.
        :type point_set:  PointSet
        """
        point_set = _get_viewer_point_set(point_set)
        self.queue_request('setPointSets', point_set)

    @fetch_value
    def set_rendering_view_container_style(self, container_style: Style) -> None:
        """Set the CSS style for the rendering view `div`'s. Queue the function
        to be run in the background thread once the plugin API is available.

        :param container_style: A dict of string keys and sting values
        representing the desired CSS styling.
        :type container_style:  Style
        """
        self.queue_request('setRenderingViewContainerStyle', container_style)
    @fetch_value
    async def get_rendering_view_container_style(self) -> Style:
        """Get the CSS style for the rendering view `div`'s.

        :return: The future for the coroutine, to be updated with a dict of
        string keys and sting values representing the desired CSS styling.
        :rtype:  Style
        """
        return await self.viewer_rpc.itk_viewer.getRenderingViewStyle()

    @fetch_value
    def set_rotate(self, enabled: bool) -> None:
        """Set whether the camera should continuously rotate around the scene
        in volume rendering mode. Queue the function to be run in the
        background thread once the plugin API is available.

        :param enabled: Rotate the camera. default: False
        :type enabled:  bool
        """
        self.queue_request('setRotateEnabled', enabled)
    @fetch_value
    async def get_rotate(self) -> bool:
        """Get whether the camera is rotating.

        :return: The future for the coroutine, to be updated with the boolean
        status.
        :rtype:  bool
        """
        return await self.viewer_rpc.itk_viewer.getRotateEnabled()

    @fetch_value
    def set_ui_collapsed(self, collapsed: bool) -> None:
        """Collapse the native widget user interface. Queue the function to be
        run in the background thread once the plugin API is available.

        :param collapsed: If the UI interface should be collapsed. default: True
        :type collapsed:  bool
        """
        self.queue_request('setUICollapsed', collapsed)
    @fetch_value
    async def get_ui_collapsed(self) -> bool:
        """Get the collapsed status of the UI interface.

        :return: The future for the coroutine, to be updated with the collapsed
        state of the UI interface.
        :rtype:  bool
        """
        return await self.viewer_rpc.itk_viewer.getUICollapsed()

    @fetch_value
    def set_units(self, units: str) -> None:
        """Set the units to display in the scale bar. Queue the function to be
        run in the background thread once the plugin API is available.

        :param units: Units to use.
        :type units:  str
        """
        self.queue_request('setUnits', units)
    @fetch_value
    async def get_units(self) -> str:
        """Get the units to display in the scale bar.

        :return: The future for the coroutine, to be updated with the units
        used in the scale bar.
        :rtype:  str
        """
        return await self.viewer_rpc.itk_viewer.getUnits()

    @fetch_value
    def set_view_mode(self, mode: str) -> None:
        """Set the viewing mode. Queue the function to be run in the background
        thread once the plugin API is available.

        :param mode: View mode. One of the following: 'XPlane', 'YPlane',
        'ZPlane', or 'Volume'. default: 'Volume'
        :type mode:  str
        """
        self.queue_request('setViewMode', mode)
    @fetch_value
    async def get_view_mode(self) -> str:
        """Get the current view mode.

        :return: The future for the coroutine, to be updated with the view mode.
        :rtype:  str
        """
        return await self.viewer_rpc.itk_viewer.getViewMode()

    @fetch_value
    def set_x_slice(self, position: float) -> None:
        """Set the position in world space of the X slicing plane. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param position: Position in world space.
        :type position:  float
        """
        self.queue_request('setXSlice', position)
    @fetch_value
    async def get_x_slice(self) -> float:
        """Get the position in world space of the X slicing plane.

        :return: The future for the coroutine, to be updated with the position
        in world space.
        :rtype:  float
        """
        return await self.viewer_rpc.itk_viewer.getXSlice()

    @fetch_value
    def set_y_slice(self, position: float) -> None:
        """Set the position in world space of the Y slicing plane. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param position: Position in world space.
        :type position:  float
        """
        self.queue_request('setYSlice', position)
    @fetch_value
    async def get_y_slice(self) -> float:
        """Get the position in world space of the Y slicing plane.

        :return: The future for the coroutine, to be updated with the position
        in world space.
        :rtype:  float
        """
        return await self.viewer_rpc.itk_viewer.getYSlice()

    @fetch_value
    def set_z_slice(self, position: float) -> None:
        """Set the position in world space of the Z slicing plane. Queue the
        function to be run in the background thread once the plugin API is
        available.

        :param position: Position in world space.
        :type position:  float
        """
        self.queue_request('setZSlice', position)
    @fetch_value
    async def get_z_slice(self) -> float:
        """Get the position in world space of the Z slicing plane.

        :return: The future for the coroutine, to be updated with the position
        in world space.
        :rtype:  float
        """
        return await self.viewer_rpc.itk_viewer.getZSlice()


def view(data=None, **kwargs):
    """View the image and/or point set.

    Creates and returns an ImJoy plugin ipywidget to visualize an image, and/or
    point set.

    The image can be 2D or 3D. The type of the image can be an numpy.array,
    itkwasm.Image, itk.Image, additional NumPy-arraylike's, such as a dask.Array,
    or vtk.vtkImageData.

    A point set can be visualized. The type of the point set can be an
    numpy.array (Nx3 array of point positions).

    Parameters
    ----------

    ### General Interface

    :param ui_collapsed: Collapse the native widget user interface. default: True
    :type  ui_collapsed: bool

    :param rotate: Continuously rotate the camera around the scene in volume rendering mode. default: False
    :type  rotate: bool

    :param annotations: Display annotations describing orientation and the value of a mouse-position-based data probe. default: True
    :type  annotations: bool

    :param axes: Display axes. default: False
    :type  axes: bool

    :param bg_color: Background color. default: based on the current Jupyter theme
    :type  bg_color: (red, green, blue) tuple, components from 0.0 to 1.0

    :param container_style: The CSS style for the rendering view `div`'s.
    :type  container_style: dict

    ### Images

    :param image: The image to visualize.
    :type  image: array_like, itk.Image, or vtk.vtkImageData

    :param label_image: The label map to visualize. If an image is also provided, the label map must have the same size.
    :type  label_image: array_like, itk.Image, or vtk.vtkImageData

    :param label_blend: Label map blend with intensity image, from 0.0 to 1.0. default: 0.5
    :type  label_blend: float

    :param label_names: String names associated with the integer label values.
    :type  label_names: list of (label_value, label_name)

    :param label_lut: Lookup table for the label map. default: 'glasbey'
    :type  label_lut: string

    :param label_weights: The rendering weight assigned to current label. Values range from 0.0 to 1.0.
    :type  label_weights: float

    :param color_range: The [min, max] range of the data values mapped to colors for the given image component identified by name.
    :type  color_range: list, default: The [min, max] range of the data values

    :param vmin: Data values below vmin take the bottom color of the color map.
    :type  vmin: float

    :param vmax: Data values above vmax take the top color of the color map.
    :type  vmax: float

    :param color_bounds: The [min, max] range of the data values for color maps that provide a bounds for user inputs.
    :type  color_bounds: list, default: The [min, max] range of the data values

    :param cmap: The color map for the current component/channel. default: 'Grayscale'
    :type  cmap: string

    :param x_slice: The position in world space of the X slicing plane.
    :type  x_slice: float

    :param y_slice: The position in world space of the Y slicing plane.
    :type  y_slice: float

    :param z_slice: The position in world space of the Z slicing plane.
    :type  z_slice: float

    :param interpolation: Linear as opposed to nearest neighbor interpolation for image slices. Note: Interpolation is not currently supported with label maps. default: True
    :type  interpolation: bool

    :param gradient_opacity: Gradient opacity for composite volume rendering, in the range (0.0, 1.0]. default: 0.5
    :type  gradient_opacity: float

    :param gradient_opacity_scale: Gradient opacity scale for composite volume rendering, in the range (0.0, 1.0]. default: 0.5
    :type  gradient_opacity_scale: float

    :param gaussians: Volume rendering opacity transfer function Gaussian parameters. For each image component, multiple Gaussians can be specified. Default Gaussian parameters: {'position': 0.5, 'height': 1, 'width': 0.5, 'xBias': 0.51, 'yBias': 0.4}
    :type  gaussians: dict

    :param blend_mode: Volume rendering blend mode. Supported modes: 'Composite', 'Maximum', 'Minimum', 'Average'. default: 'Composite'
    :type  blend_mode: string

    :param component_visible: The given image intensity component index's visibility. default: True
    :type  component_visible: bool

    :param shadow_enabled: Whether to used gradient-based shadows in the volume rendering. default: True
    :type  shadow_enabled: bool

    :param view_mode: Only relevant for 3D scenes. Viewing mode: 'XPlane', 'YPlane', 'ZPlane', or 'Volume'. default: 'Volume'
    :type  view_mode: 'XPlane', 'YPlane', 'ZPlane', or 'Volume'

    :param layer: Select the layer identified by `name` in the user interface.
    :type  layer: string

    :param layer_visible: Whether the current layer is visible. default: True
    :type  layer_visible: bool

    ### Point Set

    :param point_set: The point set to visualize.
    :type  point_set: array_like

    Other Parameters
    ----------------

    :param sample_distance: Sampling distance for volume rendering, normalized from 0.0 to 1.0. Lower values result in a higher quality rendering. High values improve the framerate. default: 0.2
    :type  sample_distance: float

    :param units: Units to display in the scale bar.
    :type  units: string

    Returns
    -------

    :return: viewer, display by placing at the end of a Jupyter or Colab cell. Query or set properties on the object to change the visualization.
    :rtype:  Viewer
    """
    viewer = Viewer(data=data, **kwargs)

    return viewer


def compare_images(
    fixed_image: Union[str, Image],
    moving_image: Union[str, Image],
    method: str = None,
    image_mix: float = None,
    checkerboard: bool = None,
    pattern: Union[Tuple[int, int], Tuple[int, int, int]] = None,
    swap_image_order: bool = None,
    **kwargs,
):
    """Fuse 2 images with a checkerboard filter or as a 2 component image.

    The moving image is re-sampled to the fixed image space. Set a keyword argument to None to use defaults based on method.

    :param fixed_image: Static image the moving image is re-sampled to. For non-checkerboard methods ('blend', 'green-magenta', etc.), the fixed image is on the first component.
    :type  fixed_image: array_like, itk.Image, or vtk.vtkImageData

    :param moving_image: Image is re-sampled to the fixed_image. For non-checkerboard methods ('blend', 'green-magenta', etc.), the moving image is on the second component.
    :type  moving_image: array_like, itk.Image, or vtk.vtkImageData

    :param method: The checkerboard method picks pixels from the fixed and moving image to create a checkerboard pattern. Setting the method to checkerboard turns on the checkerboard flag. The non-checkerboard methods ('blend', 'green-magenta', etc.) put the fixed image on component 0, moving image on component 1. The 'green-magenta' and 'red-cyan' change the color maps so matching images are grayish white. The 'cyan-magenta' color maps produce a purple if the images match.
    :type  method: string, default: None, possible values: 'green-magenta', 'cyan-red', 'cyan-magenta', 'blend', 'checkerboard', 'disabled'

    :param image_mix: Changes the percent contribution the fixed vs moving image makes to the render by modifying the opacity transfer function. Value of 1 means max opacity for moving image, 0 for fixed image. If value is None and the method is not checkerboard, the image_mix is set to 0.5.  If the method is "checkerboard", the image_mix is set to 0.
    :type  image_mix: float, default: None

    :param checkerboard: Forces the checkerboard mixing of fixed and moving images for the cyan-magenta and blend methods. The rendered image has 2 components, each component reverses which image is sampled for each checkerboard box.
    :type  checkerboard: bool, default: None

    :param pattern: The number of checkerboard boxes for each dimension.
    :type  pattern: tuple, default: None

    :param swap_image_order: Reverses which image is sampled for each checkerboard box.  This simply toggles image_mix between 0 and 1.
    :type  swap_image_order: bool, default: None

    :return: viewer, display by placing at the end of a Jupyter or Colab cell. Query or set properties on the object to change the visualization.
    :rtype:  Viewer
    """
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

    viewer = Viewer(data=None, image=moving_image, fixed_image=fixed_image, compare=options, **kwargs)
    return viewer

