import os
from itkwidgets.integrations import _detect_render_type, _get_viewer_image, _get_viewer_point_set
from itkwidgets.render_types import RenderType
from itkwidgets.viewer_config import MUI_HREF, PYDATA_SPHINX_HREF


INPUT_OPTIONS = ["image", "label_image", "point_set", "data"]


def init_params_dict(itk_viewer):
    return {
        'annotations': itk_viewer.setAnnotationsEnabled,
        'axes': itk_viewer.setAxesEnabled,
        'bg_color': itk_viewer.setBackgroundColor,
        'blend_mode': itk_viewer.setImageBlendMode,
        'cmap': itk_viewer.setImageColorMap,
        'color_range': itk_viewer.setImageColorRange,
        'color_bounds': itk_viewer.setImageColorRangeBounds,
        'component_visible': itk_viewer.setImageComponentVisibility,
        'gradient_opacity': itk_viewer.setImageGradientOpacity,
        'gradient_opacity_scale': itk_viewer.setImageGradientOpacityScale,
        'interpolation': itk_viewer.setImageInterpolationEnabled,
        'gaussians': itk_viewer.setImagePiecewiseFunctionGaussians,
        'shadow_enabled': itk_viewer.setImageShadowEnabled,
        'sample_distance': itk_viewer.setImageVolumeSampleDistance,
        'label_blend': itk_viewer.setLabelImageBlend,
        'label_names': itk_viewer.setLabelImageLabelNames,
        'label_lut': itk_viewer.setLabelImageLookupTable,
        'label_weights': itk_viewer.setLabelImageWeights,
        'layer': itk_viewer.selectLayer,
        'layer_visible': itk_viewer.setLayerVisibility,
        'container_style': itk_viewer.setRenderingViewContainerStyle,
        'rotate': itk_viewer.setRotateEnabled,
        'ui_collapsed': itk_viewer.setUICollapsed,
        'units': itk_viewer.setUnits,
        'view_mode': itk_viewer.setViewMode,
        'x_slice': itk_viewer.setXSlice,
        'y_slice': itk_viewer.setYSlice,
        'z_slice': itk_viewer.setZSlice,
    }


def build_config(ui=None):
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
    config['maxConcurrency'] = os.cpu_count() * 2

    return config


def parse_input_data(init_data_kwargs):
    inputs = {}
    for option in INPUT_OPTIONS:
        data = init_data_kwargs.get(option, None)
        if data is not None:
            inputs[option] = data
    return inputs


def build_init_data(input_data):
    result= None
    for input_type in INPUT_OPTIONS:
        data = input_data.pop(input_type, None)
        if data is None:
            continue
        render_type = _detect_render_type(data, input_type)
        if render_type is RenderType.IMAGE:
            if input_type == 'label_image':
                result = _get_viewer_image(data, label=True)
                render_type = RenderType.LABELIMAGE
            else:
                result = _get_viewer_image(data, label=False)
        elif render_type is RenderType.POINT_SET:
            result = _get_viewer_point_set(data)
        if result is None:
            raise RuntimeError(f"Could not process the viewer {input_type}")
        input_data[render_type.value] = result
    return input_data
