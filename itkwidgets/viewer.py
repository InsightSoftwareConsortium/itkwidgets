from imjoy import api
from typing import List

from ._type_aliases import Gaussians, Style, Image, Point_Sets
from ._initialization_params import init_params_dict
from .integrations import _detect_render_type, _set_viewer_image, _set_viewer_point_sets
from .render_types import RenderType

__all__ = [
  "Viewer",
  "view",
]

_viewer_count = 1

class ViewerRPC:
    """Viewer remote procedure interface."""

    def __init__(self, ui_collapsed=True, rotate=False, **add_data_kwargs):
        """Create a viewer."""
        self._init_viewer_kwargs = dict(ui_collapsed=ui_collapsed, rotate=rotate)
        self._init_viewer_kwargs.update(**add_data_kwargs)

    def _get_input_data(self):
        input_options = ['data', 'image', 'point_sets']
        for option in input_options:
            data = self._init_viewer_kwargs.get(option, None)
            if data is not None:
                break
        return data, option

    async def setup(self):
        """ImJoy plugin setup function."""
        global _viewer_count
        itk_viewer = await api.createWindow(
            name =f'itkwidgets viewer {_viewer_count}',
            type='itk-vtk-viewer',
            src='https://kitware.github.io/itk-vtk-viewer/app',
            fullscreen=True,
        )
        _viewer_count += 1

        data, input_type = self._get_input_data()
        if data is not None:
            render_type = _detect_render_type(data, input_type)
            if render_type is RenderType.IMAGE:
                await _set_viewer_image(itk_viewer, data)
            elif render_type is RenderType.POINT_SET:
                await _set_viewer_point_sets(itk_viewer, data)

            self.set_default_ui_values(itk_viewer)

        self.itk_viewer = itk_viewer

    def set_default_ui_values(self, itk_viewer):
        settings = init_params_dict(itk_viewer)
        for key, value in self._init_viewer_kwargs.items():
            if key in settings.keys():
                settings[key](value)


class Viewer:
    """Pythonic Viewer class."""

    def __init__(self, ui_collapsed=True, rotate=False, **add_data_kwargs):
        """Create a viewer."""
        self.viewer_rpc = ViewerRPC(ui_collapsed=ui_collapsed, rotate=rotate, **add_data_kwargs)
        api.export(self.viewer_rpc)

    def set_annotations_enabled(self, enabled: bool):
        self.viewer_rpc.itk_viewer.setAnnotationsEnabled(enabled)

    def set_axes_enabled(self, enabled: bool):
        self.viewer_rpc.itk_viewer.setAxesEnabled(enabled)

    def set_background_color(self, bgColor: List[float]):
        self.viewer_rpc.itk_viewer.setBackgroundColor(bgColor)

    def set_image(self, image: Image):
        self.viewer_rpc.itk_viewer.setImage(image)

    def set_image_blend_mode(self, mode: str):
        self.viewer_rpc.itk_viewer.setImageBlendMode(mode)

    def set_image_color_map(self, colorMap: str):
        self.viewer_rpc.itk_viewer.setImageColorMap(colorMap)

    def set_image_color_range(self, range: List[float]):
        self.viewer_rpc.itk_viewer.setImageColorRange(range)

    def set_image_color_range_bounds(self, range: List[float]):
        self.viewer_rpc.itk_viewer.setImageColorRangeBounds(range)

    def set_image_component_visibility(self, visibility: bool):
        self.viewer_rpc.itk_viewer.setImageComponentVisibility(visibility)

    def set_image_gradient_opacity(self, opacity: float):
        self.viewer_rpc.itk_viewer.setImageGradientOpacity(opacity)

    def set_image_gradient_opacity_scale(self, min: float):
        self.viewer_rpc.itk_viewer.setImageGradientOpacityScale(min)

    def set_image_interpolation_enabled(self, enabled: bool):
        self.viewer_rpc.itk_viewer.setImageInterpolationEnabled(enabled)

    def set_image_piecewise_function_gaussians(self, gaussians: Gaussians):
        self.viewer_rpc.itk_viewer.setImagePiecewiseFunctionGaussians(gaussians)

    def set_image_shadow_enabled(self, enabled: bool):
        self.viewer_rpc.itk_viewer.setImageShadowEnabled(enabled)

    def set_image_volume_sample_distance(self, distance: float):
        self.viewer_rpc.itk_viewer.setImageVolumeSampleDistance(distance)

    def set_label_image_blend(self, blend: float):
        self.viewer_rpc.itk_viewer.setLabelImageBlend(blend)

    def set_label_image_label_names(self, names: List[str]):
        self.viewer_rpc.itk_viewer.setLabelImageLabelNames(names)

    def set_label_image_lookup_table(self, lookupTable: str):
        self.viewer_rpc.itk_viewer.setLabelImageLookupTable(lookupTable)

    def set_label_image_weights(self, weights: float):
        self.viewer_rpc.itk_viewer.setLabelImageWeights(weights)

    def select_layer(self, name: str):
        self.viewer_rpc.itk_viewer.selectLayer(name)

    def set_layer_visibility(self, visible: bool):
        self.viewer_rpc.itk_viewer.setLayerVisibility(visible)

    def set_point_sets(self, pointSets: Point_Sets):
        self.viewer_rpc.itk_viewer.setPointSets(pointSets)

    def set_rendering_view_container_style(self, containerStyle: Style):
        self.viewer_rpc.itk_viewer.setRenderingViewContainerStyle(
            containerStyle
        )

    def set_rotate(self, enabled: bool):
        self.viewer_rpc.itk_viewer.setRotateEnabled(enabled)

    def set_ui_collapsed(self, collapsed: bool):
        self.viewer_rpc.itk_viewer.setUICollapsed(collapsed)

    def set_units(self, units: str):
        self.viewer_rpc.itk_viewer.setUnits(units)

    def set_view_mode(self, mode: str):
        self.viewer_rpc.itk_viewer.setViewMode(mode)

    def set_x_slice(self, position: float):
        self.viewer_rpc.itk_viewer.setXSlice(position)

    def set_y_slice(self, position: float):
        self.viewer_rpc.itk_viewer.setYSlice(position)

    def set_z_slice(self, position: float):
        self.viewer_rpc.itk_viewer.setZSlice(position)

def view(data=None, **kwargs):
    """View the data provided and return the resulting Viewer object."""
    viewer = Viewer(data=data, **kwargs)

    return viewer
