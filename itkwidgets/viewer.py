import asyncio
import functools
import numpy as np
from imjoy_rpc import api
from inspect import isawaitable
from typing import List, Union, Tuple
from IPython.display import display, HTML
import uuid

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
                    'renderedImageAssigned', self.update_viewer_status
                )
                if not defer_for_data_render(self.init_data):
                    # Once the viewer has been created any queued requests can be run
                    CellWatcher().update_viewer_status(self.parent, True)

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

    def update_viewer_status(self, name):
        if not CellWatcher().viewer_ready(self.parent):
            CellWatcher().update_viewer_status(self.parent, True)


class Viewer:
    """Pythonic Viewer class."""

    def __init__(
        self, ui_collapsed=True, rotate=False, ui="pydata-sphinx", **add_data_kwargs
    ):
        """Create a viewer."""
        self.name = self.__str__()
        input_data = parse_input_data(add_data_kwargs)
        data = build_init_data(input_data)
        if compare := input_data.get('compare'):
            data['compare'] = compare
        if ENVIRONMENT is not Env.HYPHA:
            self.viewer_rpc = ViewerRPC(
                ui_collapsed=ui_collapsed, rotate=rotate, ui=ui, init_data=data, parent=self.name, **add_data_kwargs
            )
            self.cw = CellWatcher()
            api.export(self.viewer_rpc)
        else:
            self._itk_viewer = add_data_kwargs.get('itk_viewer', None)
            self.server = add_data_kwargs.get('server', None)
            self.workspace = self.server.config.workspace

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

    def call_getter(self, future):
        name = uuid.uuid4()
        CellWatcher().results[name] = future
        future.add_done_callback(functools.partial(CellWatcher()._callback, name))

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
         self.viewer_rpc.itk_viewer.setAnnotationsEnabled(enabled)
    @fetch_value
    async def get_annotations_enabled(self):
        return await self.viewer_rpc.itk_viewer.getAnnotationsEnabled()

    @fetch_value
    def set_axes_enabled(self, enabled: bool):
         self.viewer_rpc.itk_viewer.setAxesEnabled(enabled)
    @fetch_value
    async def get_axes_enabled(self):
        return await self.viewer_rpc.itk_viewer.getAxesEnabled()

    @fetch_value
    def set_background_color(self, bgColor: List[float]):
         self.viewer_rpc.itk_viewer.setBackgroundColor(bgColor)
    @fetch_value
    async def get_background_color(self):
        return await self.viewer_rpc.itk_viewer.getBackgroundColor()

    @fetch_value
    def set_cropping_planes(self, cropping_planes):
        self.viewer_rpc.itk_viewer.setCroppingPlanes(cropping_planes)
    @fetch_value
    async def get_cropping_planes(self):
        return await self.viewer_rpc.itk_viewer.getCroppingPlanes()

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
                self.viewer_rpc.itk_viewer.setImage(image, name)
                CellWatcher().update_viewer_status(self.name, False)
        elif render_type is RenderType.POINT_SET:
            image = _get_viewer_point_set(image)
            self.viewer_rpc.itk_viewer.setPointSets(image)
    @fetch_value
    async def get_image(self):
        return await self.viewer_rpc.itk_viewer.getImage()

    @fetch_value
    def set_image_blend_mode(self, mode: str):
         self.viewer_rpc.itk_viewer.setImageBlendMode(mode)
    @fetch_value
    async def get_image_blend_mode(self):
        return await self.viewer_rpc.itk_viewer.getImageBlendMode()

    @fetch_value
    def set_image_color_map(self, colorMap: str):
         self.viewer_rpc.itk_viewer.setImageColorMap(colorMap)
    @fetch_value
    async def get_image_color_map(self):
        return await self.viewer_rpc.itk_viewer.getImageColorMap()

    @fetch_value
    def set_image_color_range(self, range: List[float]):
         self.viewer_rpc.itk_viewer.setImageColorRange(range)
    @fetch_value
    async def get_image_color_range(self):
        return await self.viewer_rpc.itk_viewer.getImageColorRange()

    @fetch_value
    def set_image_color_range_bounds(self, range: List[float]):
         self.viewer_rpc.itk_viewer.setImageColorRangeBounds(range)
    @fetch_value
    async def get_image_color_range_bounds(self):
        return await self.viewer_rpc.itk_viewer.getImageColorRangeBounds()

    @fetch_value
    def set_image_component_visibility(self, visibility: bool, component: int):
         self.viewer_rpc.itk_viewer.setImageComponentVisibility(visibility, component)
    @fetch_value
    async def get_image_component_visibility(self, component: int):
        return await self.viewer_rpc.itk_viewer.getImageComponentVisibility(component)

    @fetch_value
    def set_image_gradient_opacity(self, opacity: float):
         self.viewer_rpc.itk_viewer.setImageGradientOpacity(opacity)
    @fetch_value
    async def get_image_gradient_opacity(self):
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacity()

    @fetch_value
    def set_image_gradient_opacity_scale(self, min: float):
         self.viewer_rpc.itk_viewer.setImageGradientOpacityScale(min)
    @fetch_value
    async def get_image_gradient_opacity_scale(self):
        return await self.viewer_rpc.itk_viewer.getImageGradientOpacityScale()

    @fetch_value
    def set_image_interpolation_enabled(self, enabled: bool):
         self.viewer_rpc.itk_viewer.setImageInterpolationEnabled(enabled)
    @fetch_value
    async def get_image_interpolation_enabled(self):
        return await self.viewer_rpc.itk_viewer.getImageInterpolationEnabled()

    @fetch_value
    def set_image_piecewise_function_gaussians(self, gaussians: Gaussians):
         self.viewer_rpc.itk_viewer.setImagePiecewiseFunctionGaussians(gaussians)
    @fetch_value
    async def get_image_piecewise_function_gaussians(self):
        return await self.viewer_rpc.itk_viewer.getImagePiecewiseFunctionGaussians()

    @fetch_value
    def set_image_shadow_enabled(self, enabled: bool):
         self.viewer_rpc.itk_viewer.setImageShadowEnabled(enabled)
    @fetch_value
    async def get_image_shadow_enabled(self):
        return await self.viewer_rpc.itk_viewer.getImageShadowEnabled()

    @fetch_value
    def set_image_volume_sample_distance(self, distance: float):
         self.viewer_rpc.itk_viewer.setImageVolumeSampleDistance(distance)
    @fetch_value
    async def get_image_volume_sample_distance(self):
        return await self.viewer_rpc.itk_viewer.getImageVolumeSampleDistance()

    @fetch_value
    def set_image_volume_scattering_blend(self, scattering_blend: float):
         self.viewer_rpc.itk_viewer.setImageVolumeScatteringBlend(scattering_blend)
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
    async def get_roi_slice(self, scale=-1):
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
        idxs = await self.viewer_rpc.itk_viewer.getCroppedIndexBounds(scale)
        x0, x1 = idxs['x']
        y0, y1 = idxs['y']
        z0, z1 = idxs['z']
        return np.index_exp[z0:z1, y0:y1, x0:x1]

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
        self.viewer_rpc.itk_viewer.compareImages(fixed_name, moving_name, options)
        CellWatcher().update_viewer_status(self.name, False)

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
                self.viewer_rpc.itk_viewer.setLabelImage(label_image)
                CellWatcher().update_viewer_status(self.name, False)
        elif render_type is RenderType.POINT_SET:
            label_image = _get_viewer_point_set(label_image)
            self.viewer_rpc.itk_viewer.setPointSets(label_image)
    @fetch_value
    async def get_label_image(self):
        return await self.viewer_rpc.itk_viewer.getLabelImage()

    @fetch_value
    def set_label_image_blend(self, blend: float):
         self.viewer_rpc.itk_viewer.setLabelImageBlend(blend)
    @fetch_value
    async def get_label_image_blend(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageBlend()

    @fetch_value
    def set_label_image_label_names(self, names: List[str]):
         self.viewer_rpc.itk_viewer.setLabelImageLabelNames(names)
    @fetch_value
    async def get_label_image_label_names(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageLabelNames()

    @fetch_value
    def set_label_image_lookup_table(self, lookupTable: str):
         self.viewer_rpc.itk_viewer.setLabelImageLookupTable(lookupTable)
    @fetch_value
    async def get_label_image_lookup_table(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageLookupTable()

    @fetch_value
    def set_label_image_weights(self, weights: float):
         self.viewer_rpc.itk_viewer.setLabelImageWeights(weights)
    @fetch_value
    async def get_label_image_weights(self):
        return await self.viewer_rpc.itk_viewer.getLabelImageWeights()

    @fetch_value
    def select_layer(self, name: str):
        self.viewer_rpc.itk_viewer.selectLayer(name)
    @fetch_value
    async def get_layer_names(self):
        return await self.viewer_rpc.itk_viewer.getLayerNames()

    @fetch_value
    def set_layer_visibility(self, visible: bool, name: str):
         self.viewer_rpc.itk_viewer.setLayerVisibility(visible, name)
    @fetch_value
    async def get_layer_visibility(self, name: str):
        return await self.viewer_rpc.itk_viewer.getLayerVisibility(name)

    @fetch_value
    def add_point_set(self, pointSet: PointSet):
        pointSet = _get_viewer_point_set(pointSet)
        self.viewer_rpc.itk_viewer.addPointSet(pointSet)
    @fetch_value
    def set_point_set(self, pointSet: PointSet):
        pointSet = _get_viewer_point_set(pointSet)
        self.viewer_rpc.itk_viewer.setPointSets(pointSet)

    @fetch_value
    def set_rendering_view_container_style(self, containerStyle: Style):
         self.viewer_rpc.itk_viewer.setRenderingViewContainerStyle(containerStyle)
    @fetch_value
    async def get_rendering_view_container_style(self):
        return await self.viewer_rpc.itk_viewer.getRenderingViewStyle()

    @fetch_value
    def set_rotate(self, enabled: bool):
        self.viewer_rpc.itk_viewer.setRotateEnabled(enabled)
    @fetch_value
    async def get_rotate(self):
        return await self.viewer_rpc.itk_viewer.getRotateEnabled()

    @fetch_value
    def set_ui_collapsed(self, collapsed: bool):
         self.viewer_rpc.itk_viewer.setUICollapsed(collapsed)
    @fetch_value
    async def get_ui_collapsed(self):
        return await self.viewer_rpc.itk_viewer.getUICollapsed()

    @fetch_value
    def set_units(self, units: str):
         self.viewer_rpc.itk_viewer.setUnits(units)
    @fetch_value
    async def get_units(self):
        return await self.viewer_rpc.itk_viewer.getUnits()

    @fetch_value
    def set_view_mode(self, mode: str):
         self.viewer_rpc.itk_viewer.setViewMode(mode)
    @fetch_value
    async def get_view_mode(self):
        return await self.viewer_rpc.itk_viewer.getViewMode()

    @fetch_value
    def set_x_slice(self, position: float):
         self.viewer_rpc.itk_viewer.setXSlice(position)
    @fetch_value
    async def get_x_slice(self):
        return await self.viewer_rpc.itk_viewer.getXSlice()

    @fetch_value
    def set_y_slice(self, position: float):
         self.viewer_rpc.itk_viewer.setYSlice(position)
    @fetch_value
    async def get_y_slice(self):
        return await self.viewer_rpc.itk_viewer.getYSlice()

    @fetch_value
    def set_z_slice(self, position: float):
         self.viewer_rpc.itk_viewer.setZSlice(position)
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

