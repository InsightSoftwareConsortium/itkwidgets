"""itkwidgets: Interactive widgets to visualize images, point sets, and 3D geometry on the web."""

__version__ = "1.0a1"

from .viewer import Viewer, view

__all__ = [
  "Viewer",
  "view",
]