"""itkwidgets: Interactive widgets to visualize images, point sets, and 3D geometry on the web."""

__version__ = "1.0a2"

from .imjoy import register_itkwasm_imjoy_codecs
register_itkwasm_imjoy_codecs()

from .viewer import Viewer, view

__all__ = [
  "Viewer",
  "view",
]
