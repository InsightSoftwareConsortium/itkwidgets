import asyncio
import functools
import queue
import threading
import numpy as np
from imjoy_rpc import api
from inspect import isawaitable
from typing import List, Union, Tuple
from IPython.display import display, HTML
from IPython.lib import backgroundjobs as bg
from ngff_zarr import (
    from_ngff_zarr,
    to_ngff_image,
    Multiscales,
    NgffImage
)
import uuid

from ._method_types import deferred_methods
from ._type_aliases import Gaussians, Style, Image, PointSet
from ._initialization_params import (
    init_params_dict,
    build_config,
    parse_input_data,
    build_init_data,
    defer_for_data_render,
)
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
        if ENVIRONMENT is not Env.JUPYTERLITE:
            CellWatcher().add_viewer(self.parent)
            if ENVIRONMENT is not Env.HYPHA:
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
                    CellWatcher().update_viewer_status(self.parent, True)
                asyncio.get_running_loop().call_soon_threadsafe(self.viewer_event.set)

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

    def update_viewer_status(self):
        if not CellWatcher().viewer_ready(self.parent):
            CellWatcher().update_viewer_status(self.parent, True)

    def set_event(self, event_data):
        if not self.data_event.is_set():
            # Once the data has been set the deferred queue requests can be run
            asyncio.get_running_loop().call_soon_threadsafe(self.data_event.set)
        self.update_viewer_status()


class Viewer:
    """Pythonic Viewer class."""

    def __init__(
        self, ui_collapsed=True, rotate=False, ui="pydata-sphinx", **add_data_kwargs
    ):
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
            result = func(self, *args, **kwargs)
            if isawaitable(result):
                future = asyncio.ensure_future(result)
                self.call_getter(future)
                return future
            return result
        return _fetch_value

    @fetch_value
    def set_annotations_enabled(self, enabled: bool):
        self.queue_request('setAnnotationsEnabled', enabled)
    @fetch_value
    async def get_annotations_enabled(self):
        return await self.viewer_rpc.itk_viewer.getAnnotationsEnabled()

    @fetch_value
    def set_axes_enabled(self, enabled: bool):
        self.queue_request('setAxesEnabled', enabled)
    @fetch_value
    async def get_axes_enabled(self):
        return await self.viewer_rpc.itk_viewer.getAxesEnabled()

    @fetch_value
    def set_background_color(self, bgColor: List[float]):
        self.queue_request('setBackgroundColor', bgColor)
    @fetch_value
    async def get_background_color(self):
        return await self.viewer_rpc.itk_viewer.getBackgroundColor()

    @fetch_value
    def set_cropping_planes(self, cropping_planes):
        self.queue_request('setCroppingPlanes', cropping_planes)
    @fetch_value
    async def get_cropping_planes(self):
        return await self.viewer_rpc.itk_viewer.getCroppingPlanes()

    @fetch_value
    def set_image(self, image: Image, name: str = 'Image'):
        render_type = _detect_render_type(image, 'image')
        if render_type is RenderType.IMAGE:
            image = _get_viewer_image(image, label=False)
            self.stores[name] = image
            if ENVIRONMENT is Env.HYPHA:
                self.image = image
                svc_name = f'{self.workspace}/itkwidgets-server:data-set'
                svc = self.server.get_service(svc_name)
                svc.set_label_or_image('image')
            else:
                self.queue_request('setImage', image, name)
                CellWatcher().update_viewer_status(self.name, False)
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
    def set_image_blend_mode(self, mode: str):
        self.queue_request('setImageBlendMode', mode)
    @fetch_value
    async def get_image_blend_mode(self):
        return await self.viewer_rpc.itk_viewer.getImageBlendMode()

    @fetch_value
    def set_image_color_map(self, colorMap: str):
        self.queue_request('setImageColorMap', colorMap)
    @fetch_value
    async def get_image_color_map(self):
        return await self.viewer_rpc.itk_viewer.getImageColorMap()

    @fetch_value
    def set_image_color_range(self, range: List[float]):
        self.queue_request('setImageColorRange', range)
    @fetch_value
    async def get_image_color_range(self):
        return await self.viewer_rpc.itk_viewer.getImageColorRange()

    @property
    @fetch_value
    async def vmin(self):
        range = await self.get_image_color_range()
        return range[0]
    @vmin.setter
    @fetch_value
    async def vmin(self, vmin: float):
        self.queue_request('setImageColorRangeMin', vmin)

    @property
    @fetch_value
    async def vmax(self):
        range = await self.get_image_color_range()
        return range[1]
    @vmax.setter
    @fetch_value
    async def vmax(self, vmax: float):
        self.queue_request('setImageColorRangeMax', vmax)


    @fetch_value
    def set_image_color_range_bounds(self, range: List[float]):
        self.queue_request('setImageColorRangeBounds', range)
    @fetch_value
    async def get_image_color_range_bounds(self):
        return await self.viewer_rpc.itk_viewer.getImageColorRangeBounds()

    @fetch_value
    def set_image_component_visibility(self, visibility: bool, component: int):
        self.queue_request('setImageComponentVisibility', visibility, component)
    @fetch_value
    async def get_image_component_visibility(self, component: int):
        return await self.viewer_rpc.itk_viewer.getImageComponentVisibility(component)

    @fetch_value
    def set_image_gradient_opacity(self, opacity: float):
        self.queue_request('setImageGradientOpacity', opacity)
    @fetch_value
    async def get_image_gradient_opacity(self):
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacity()

    @fetch_value
    def set_image_gradient_opacity_scale(self, min: float):
        self.queue_request('setImageGradientOpacityScale', min)
    @fetch_value
    async def get_image_gradient_opacity_scale(self):
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacityScale()

    @fetch_value
    def set_image_interpolation_enabled(self, enabled: bool):
        self.queue_request('setImageInterpolationEnabled', enabled)
    @fetch_value
    async def get_image_interpolation_enabled(self):
        return await self.viewer_rpc.itk_viewer.getImageInterpolationEnabled()

    @fetch_value
    def set_image_piecewise_function_gaussians(self, gaussians: Gaussians):
        self.queue_request('setImagePiecewiseFunctionGaussians', gaussians)
    @fetch_value
    async def get_image_piecewise_function_gaussians(self):
        return await self.viewer_rpc.itk_viewer.getImagePiecewiseFunctionGaussians()

    @fetch_value
    def set_image_shadow_enabled(self, enabled: bool):
        self.queue_request('setImageShadowEnabled', enabled)
    @fetch_value
    async def get_image_shadow_enabled(self):
        return await self.viewer_rpc.itk_viewer.getImageShadowEnabled()

    @fetch_value
    def set_image_volume_sample_distance(self, distance: float):
        self.queue_request('setImageVolumeSampleDistance', distance)
    @fetch_value
    async def get_image_volume_sample_distance(self):
        return await self.viewer_rpc.itk_viewer.getImageVolumeSampleDistance()

    @fetch_value
    def set_image_volume_scattering_blend(self, scattering_blend: float):
        self.queue_request('setImageVolumeScatteringBlend', scattering_blend)
    @fetch_value
    async def get_image_volume_scattering_blend(self):
        return await self.viewer_rpc.itk_viewer.getImageVolumeScatteringBlend()

    @fetch_value
    async def get_current_scale(self):
        """Get the current resolution scale of the primary image.

        0 is the highest resolution. Values increase for lower resolutions.

        :return: scale
        :rtype:  int
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
    async def get_roi_region(self):
        """Get the current region of interest in world / physical space.

        Returns [lower_bounds, upper_bounds] in the form:

          [{ 'x': x0, 'y': y0, 'z': z0 }, { 'x': x1, 'y': y1, 'z': z1 }]

        :return: roi_region
        :rtype:  List[Dict[str, float]]
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
        self.queue_request('compareImages', fixed_name, moving_name, options)
        CellWatcher().update_viewer_status(self.name, False)

    @fetch_value
    def set_label_image(self, label_image: Image):
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
                CellWatcher().update_viewer_status(self.name, False)
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
    def set_label_image_blend(self, blend: float):
        self.queue_request('setLabelImageBlend', blend)
    @fetch_value
    async def get_label_image_blend(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageBlend()

    @fetch_value
    def set_label_image_label_names(self, names: List[str]):
        self.queue_request('setLabelImageLabelNames', names)
    @fetch_value
    async def get_label_image_label_names(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageLabelNames()

    @fetch_value
    def set_label_image_lookup_table(self, lookupTable: str):
        self.queue_request('setLabelImageLookupTable', lookupTable)
    @fetch_value
    async def get_label_image_lookup_table(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageLookupTable()

    @fetch_value
    def set_label_image_weights(self, weights: float):
        self.queue_request('setLabelImageWeights', weights)
    @fetch_value
    async def get_label_image_weights(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageWeights()

    @fetch_value
    def select_layer(self, name: str):
        self.queue_request('selectLayer', name)
    @fetch_value
    async def get_layer_names(self):
        return await self.viewer_rpc.itk_viewer.getLayerNames()

    @fetch_value
    def set_layer_visibility(self, visible: bool, name: str):
        self.queue_request('setLayerVisibility', visible, name)
    @fetch_value
    async def get_layer_visibility(self, name: str):
        return await self.viewer_rpc.itk_viewer.getLayerVisibility(name)

    @fetch_value
    def get_loaded_image_names(self):
        return list(self.stores.keys())

    @fetch_value
    def add_point_set(self, pointSet: PointSet):
        pointSet = _get_viewer_point_set(pointSet)
        self.queue_request('addPointSet', pointSet)
    @fetch_value
    def set_point_set(self, pointSet: PointSet):
        pointSet = _get_viewer_point_set(pointSet)
        self.queue_request('setPointSets', pointSet)

    @fetch_value
    def set_rendering_view_container_style(self, containerStyle: Style):
        self.queue_request('setRenderingViewContainerStyle', containerStyle)
    @fetch_value
    async def get_rendering_view_container_style(self):
        return await self.viewer_rpc.itk_viewer.getRenderingViewStyle()

    @fetch_value
    def set_rotate(self, enabled: bool):
        self.queue_request('setRotateEnabled', enabled)
    @fetch_value
    async def get_rotate(self):
        return await self.viewer_rpc.itk_viewer.getRotateEnabled()

    @fetch_value
    def set_ui_collapsed(self, collapsed: bool):
        self.queue_request('setUICollapsed', collapsed)
    @fetch_value
    async def get_ui_collapsed(self):
        return await self.viewer_rpc.itk_viewer.getUICollapsed()

    @fetch_value
    def set_units(self, units: str):
        self.queue_request('setUnits', units)
    @fetch_value
    async def get_units(self):
        return await self.viewer_rpc.itk_viewer.getUnits()

    @fetch_value
    def set_view_mode(self, mode: str):
        self.queue_request('setViewMode', mode)
    @fetch_value
    async def get_view_mode(self):
        return await self.viewer_rpc.itk_viewer.getViewMode()

    @fetch_value
    def set_x_slice(self, position: float):
        self.queue_request('setXSlice', position)
    @fetch_value
    async def get_x_slice(self):
        return await self.viewer_rpc.itk_viewer.getXSlice()

    @fetch_value
    def set_y_slice(self, position: float):
        self.queue_request('setYSlice', position)
    @fetch_value
    async def get_y_slice(self):
        return await self.viewer_rpc.itk_viewer.getYSlice()

    @fetch_value
    def set_z_slice(self, position: float):
        self.queue_request('setZSlice', position)
    @fetch_value
    async def get_z_slice(self):
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

def compare_images(fixed_image: Union[str, Image], moving_image: Union[str, Image], method: str = None, image_mix: float = None, checkerboard: bool = None, pattern: Union[Tuple[int, int], Tuple[int, int, int]] = None, swap_image_order: bool = None, **kwargs):
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

