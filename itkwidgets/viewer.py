from imjoy import api

from typing import Optional

from .integrations import _detect_render_type, _set_viewer_image
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

    async def setup(self):
        """ImJoy plugin setup function."""
        global _viewer_count
        try:
            from google.colab import output
            running_in_colab = True
        except ModuleNotFoundError:
            running_in_colab = False
        if running_in_colab:
            itk_viewer = await api.showDialog(
                name =f'itkwidgets viewer {_viewer_count}',
                type='itk-vtk-viewer',
                src='https://kitware.github.io/itk-vtk-viewer/app',
            )
        else:
            itk_viewer = await api.createWindow(
                name =f'itkwidgets viewer {_viewer_count}',
                type='itk-vtk-viewer',
                # src='http://localhost:8082',
                src='https://kitware.github.io/itk-vtk-viewer/app',
            )
        _viewer_count += 1

        data = self._init_viewer_kwargs.get('data', None)
        if data is not None:
            render_type = _detect_render_type(data)
            if render_type is RenderType.IMAGE:
                await _set_viewer_image(itk_viewer, data)

            itk_viewer.setUICollapsed(self._init_viewer_kwargs['ui_collapsed'])
            itk_viewer.setRotateEnabled(self._init_viewer_kwargs['rotate'])

        self.itk_viewer = itk_viewer

class Viewer:
    """Pythonic Viewer class."""

    def __init__(self, ui_collapsed=True, rotate=False, **add_data_kwargs):
        """Create a viewer."""
        self.viewer_rpc = ViewerRPC(ui_collapsed=ui_collapsed, rotate=rotate, **add_data_kwargs)
        api.export(self.viewer_rpc)

    def set_ui_collapsed(self, collapsed: bool):
        self.viewer_rpc.itk_viewer.setUICollapsed(collapsed)

    def set_rotate(self, rotate: bool):
        self.viewer_rpc.itk_viewer.setRotateEnabled(rotate)

    def set_image_gradient_opacity(self, opacity:float):
        self.viewer_rpc.itk_viewer.setImageGradientOpacity(opacity)


def view(data=None, **kwargs):
    """View the data provided and return the resulting Viewer object."""
    viewer = Viewer(data=data, **kwargs)

    return viewer