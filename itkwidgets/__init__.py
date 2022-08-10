"""itkwidgets: Interactive widgets to visualize images, point sets, and 3D geometry on the web."""

from imjoy_rpc import register_default_codecs
register_default_codecs()

from .imjoy import register_itkwasm_imjoy_codecs
register_itkwasm_imjoy_codecs()

from .viewer import Viewer, view

__all__ = [
  "Viewer",
  "view",
]
